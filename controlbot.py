#!/usr/bin/python

import wesnothd_client


if __name__ == "__main__":
    import optparse
    import time

    op = optparse.OptionParser("%prog [options]")

    op.add_option("-n", "--nick",
        help = "Nickname to use on the server")
    op.add_option("-s", "--server",
        help = "Speak after joining the server")
    op.add_option("-v", "--version",
        help = "Wesnoth version we pretend to be")

    options, args = op.parse_args()
    client_options = {}
    if options.nick:
        client_options["name"] = options.nick
    if options.server:
        client_options["server"] = options.server
    if options.version:
        client_options["version"] = options.version

    client = wesnothd_client.Client(**client_options)
    while True:
        data = client.pollall()
        if not data:
            time.sleep(1)
        else:
            # This needs to be refactored. A lot.
            if client.mode == wesnothd_client.Modes.LOBBY:
                if "whisper" in data:
                    for nick, message in data["whisper"]:
                        if message == "join":
                            try:
                                user = [user for user in client.users if user.keys["name"] == nick][0]
                                if user.keys["game_id"] != "0":
                                    # FIXME: This is way too deep.
                                    print "Joining game {0}".format(user.keys["game_id"])
                                    client.join_game(user.keys["game_id"])
                                else:
                                    print "User {0} is not in a game".format(nick)
                            except:
                                print "Failed something for user {0}".format(nick)
                if "message" in data:
                    for nick, message in data["message"]:
                        print "<{0}> {1}".format(nick,message)
            elif client.mode == wesnothd_client.Modes.GAME:
                if "host_transfer" in data:
                    for host, value in data["host_transfer"]:
                        if client.name == host and value == "1":
                            client.speak("I am now the host")
                        else:
                            print "Host transfer to someone else? We shouldn't receive this"
                elif "change_controller" in data:
                    for side, player, controller in data["change_controller"]:
                        print "Side {0} is now controlled by player {1}'s {2}".format(side, player, controller)
                elif "message" in data:
                    for speaker, message in data["message"]:
                        # TODO: Do we have any way to determine that we are up-to-date, rather than replaying?
                        if message.startswith("{0}: ".format(client.name)):
                            payload = message[len(client.name)+2:]
                        else:
                            continue
                        if payload.startswith("control "):
                            try:
                                side = int(payload[8:])
                                client.give_control(side, speaker)
                            except:
                                print "Failed to give user {0} control of a side: {1}".format(speaker, payload)
                        elif payload == "end turn":
                            print "Ending turn by command of {0}".format(speaker)
                            client.end_turn()
                        elif payload == "help":
                            print "Help request received"
                            client.speak("{0}: HELP NOT AVAILABLE".format(speaker))
                        else:
                            print "Unknown command received: {0}".format(payload)
                            client.speak("{0}: Unknown command '{1}'".format(speaker, payload))
                elif "observer_added" in data:
                    print "New observers: {0}".format(str(data["observer_added"]))
                elif "observer_deleted" in data:
                    print "Gone observers: {0}".format(str(data["observer_deleted"]))
                elif "leave_game" in data:
                    print "We exited the game"
                elif "loose_tags" in data:
                    print data["loose_tags"]
                else:
                    print "Did we receive anything?"
