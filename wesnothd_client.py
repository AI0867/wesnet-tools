#!/usr/bin/python

import collections
import gzip_connection
import random
import simplewml

class VersionRefused(Exception):
    pass

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type("Enum", (), enums)

Modes = enum("CONNECTING", "LOBBY", "SETUP", "GAME", "TEST")

def get_or_create(dictionary, key):
    if key not in dictionary:
        dictionary[key] = []
    return dictionary[key]

class Client(object):
    def __init__(self, server="server.wesnoth.org", version="1.11.1", name="lobbybot"):
        self.con = gzip_connection.GzipClient(server)
        self.version = version
        self.basename = name
        self.wml = simplewml.SimpleWML()
        self.mode = Modes.CONNECTING
        while not self.poll(block=True):
            pass
    def read_wml(self):
        raw = self.con.nextfragment()
        return self.wml.parse(raw)
    def write_wml(self, wml):
        self.con.sendfragment(str(wml))
    def poll(self, block=False):
        if block or self.con.poll():
            data = self.read_wml()
            if self.mode == Modes.CONNECTING:
                return self.process_connecting(data) # False or True
            elif self.mode == Modes.LOBBY:
                return self.process_lobby(data) # False or OrderedDict
            elif self.mode == Modes.SETUP:
                return self.process_setup(data) # False or list
            elif self.mode == Modes.GAME:
                return self.process_game(data) # False or dict
            elif self.mode == Modes.TEST:
                return data # simplewml.RootTag
            else:
                assert False
        return False
    def pollall(self, block=False):
        response = collections.OrderedDict()
        lastpoll = self.poll()
        while lastpoll is not False:
            if not lastpoll:
                lastpoll = {}
            # Huge hack
            elif isinstance(lastpoll, list):
                lastpoll = {"list": lastpoll}
            elif isinstance(lastpoll, simplewml.Tag):
                lastpoll = {"list": [lastpoll]}
            for key, value in lastpoll.items():
                if key not in response:
                    response[key] = value
                elif key == "ping": #Or a better way to check for scalars
                    response[key] = value
                else:
                    response[key].extend(value)
            lastpoll = self.poll()
        return response
    def process_connecting(self, data):
        #TODO: make this return a dict or something
        for tag in data.tags:
            if tag.name == "version":
                t = simplewml.Tag("version")
                t.keys["version"] = self.version
                self.write_wml(t)
            elif tag.name == "reject":
                raise VersionRefused("Failed to connect: we are version {0} and the server accepts clients of types {1}".format(self.version, tag.keys["accepted_versions"]))
            elif tag.name == "redirect":
                self.con = gzip_connection.GzipClient(tag.keys["host"], tag.keys["port"])
            elif tag.name == "mustlogin":
                t = simplewml.Tag("login")
                self.name = self.basename
                t.keys["username"] = self.name
                self.write_wml(t)
            elif tag.name == "join_lobby":
                self.enter_lobby()
            elif tag.name == "error":
                if tag.keys.get("error_code") == "101":
                    t = simplewml.Tag("login")
                    self.name = "{0}{1:03}".format(self.basename, random.randint(0,999))
                    t.keys["username"] = self.name
                    self.write_wml(t)
                else:
                    raise Exception("Received [error] with code {0} and message: {1}".format(tag.keys["error_code"], tag.keys["message"]))
            else:
                raise Exception("Unknown tag received:\n{0}\n".format(tag.name))
        if "version" in data.keys:
            # This is the backwards compatibility thing, we should really do it after the [reject]
            raise VersionRefused("Failed to connect: we are version {0} and the server only accepts {1}".format(self.version, data.keys["version"]))
        return self.mode != Modes.CONNECTING
    def enter_lobby(self):
        self.last_ping = 0
        self.users = []
        self.games = []
        self.chatlog = collections.deque([], 100)
        self.mode = Modes.LOBBY
    def process_lobby(self, data):
        response = collections.OrderedDict()
        replaced_users = False
        if "ping" in data.keys:
            self.last_ping = data.keys["ping"]
            response["ping"] = data.keys["ping"]
        for tag in data.tags:
            if tag.name == "message":
                # message, sender
                get_or_create(response, "message").append((tag.keys["sender"], tag.keys["message"]))
                self.chatlog.append(tag)
            elif tag.name == "whisper":
                # message, sender, receiver
                get_or_create(response, "whisper").append((tag.keys["sender"], tag.keys["message"]))
                self.chatlog.append(tag)
            elif tag.name == "user":
                # available, status, name, registered, location, game_id
                get_or_create(response, "user").append(tag.keys["name"])
                if not replaced_users:
                    self.users = []
                    replaced_users = True
                self.users.append(tag)
            elif tag.name == "gamelist":
                # [game]
                games = []
                for game in tag.tags:
                    assert game.name == "game", "Foreign tag in [gamelist]: {0}".format(game.name)
                    games.append(game.keys["name"])
                self.games = tag.tags
                response["game"] = games
            elif tag.name == "gamelist_diff":
                # [insert_child], [change_child], [delete_child]
                # Each of these apply to [gamelist] or [user]
                # [gamelist] then contains more of the same to apply to [game]
                # [insert_child]: index, tag
                # [change_child]: index, tag (only applied to [gamelist] ?)
                # [delete_child]: index, empty tag
                assert not tag.keys, "[gamelist_diff] contains keys"
                assert len(tag.tags) <= 3, "[gamelist_diff] contains more than 3 tags"
                users_add = []
                users_del = []
                games_add = []
                games_del = []
                for item in tag.tags:
                    if item.name == "insert_child":
                        assert len(item.tags) == 1
                        users_add.append((int(item.keys["index"]), item.tags[0]))
                    elif item.name == "change_child":
                        assert len(item.keys) == 1
                        assert item.keys["index"] == "0", "index is actually {0}".format(item.keys["index"])
                        assert len(item.tags) == 1
                        assert item.tags[0].name == "gamelist"

                        for mod in item.tags[0].tags:
                            assert len(mod.tags) == 1
                            assert mod.tags[0].name == "game"
                            if mod.name == "insert_child":
                                games_add.append((int(mod.keys["index"]), mod.tags[0]))
                            elif mod.name == "delete_child":
                                games_del.append((int(mod.keys["index"]), mod.tags[0]))
                            else:
                                assert False, "Unknown [gamelist_diff][gamelist] member {0}".format(mod.name)
                    elif item.name == "delete_child":
                        assert len(item.tags) == 1
                        users_del.append((int(item.keys["index"]), item.tags[0]))
                    else:
                        assert False, "Unknown [gamelist_diff] member {0}".format(item.name)
                for pair in users_add:
                    self.users.insert(pair[0], pair[1])
                    get_or_create(response, "user_added").append(pair[1].keys["name"])
                for pair in users_del:
                    assert self.users[pair[0]].name == pair[1].name
                    get_or_create(response, "user_deleted").append(self.users[pair[0]].keys["name"])
                    try:
                        del self.users[pair[0]]
                    except IndexError:
                        # TODO: this can happen after leaving (or only getting kicked?)
                        # The update arrives before the new list
                        raise IndexError("Attempted to delete a non-existent user")
                if "user_added" in response and "user_deleted" in response:
                    response["user_modified"] = [user for user in response["user_added"] if user in response["user_deleted"]]
                    response["user_added"] = [user for user in response["user_added"] if user not in response["user_modified"]]
                    response["user_deleted"] = [user for user in response["user_deleted"] if user not in response["user_modified"]]
                for pair in games_add:
                    self.games.insert(pair[0], pair[1])
                    get_or_create(response, "game_added").append(pair[1].keys["name"])
                for pair in games_del:
                    assert self.games[pair[0]].name == pair[1].name
                    get_or_create(response, "game_deleted").append(self.games[pair[0]].keys["name"])
                    try:
                        del self.games[pair[0]]
                    except IndexError:
                        # TODO: this can happen after leaving (or only getting kicked?)
                        # The update arrives before the new list
                        raise IndexError("Attempted to delete a non-existent user")
                if "game_added" in response and "game_deleted" in response:
                    response["game_modified"] = [game for game in response["game_added"] if game in response["game_deleted"]]
                    response["game_added"] = [game for game in response["game_added"] if game not in response["game_modified"]]
                    response["game_deleted"] = [game for game in response["game_deleted"] if game not in response["game_modified"]]
            elif tag.name == "turn":
                # TODO: This doesn't happen much (anymore?) Did we fix it?
                raise Exception("Got stray [turn]. Did we just exit a game?\n{0}".format(str(tag)))
            else:
                assert False, "Got unknown tag {0}".format(tag.name)

        # Filter out empty lists and such
        filtered_response = collections.OrderedDict()
        for key in response:
            if response[key]:
                filtered_response[key] = response[key]
        return filtered_response
    def enter_setup(self):
        self.raws = []
        self.mode = Modes.SETUP
    def process_setup(self, data):
        response = []
        if len(data.keys):
            self.raws.append(simplewml.Tag("FAKE: loose keys"))
            self.raws[-1].keys = data.keys
        for key, value in data.keys.items():
            pass
        for tag in data.tags:
            self.raws.append(tag)
            response.append(str(tag))
            if tag.name == "gamelist_diff":
                print "[gamelist_diff] encountered during setup"
            elif tag.name in ["user", "gamelist"]:
                pass
            elif tag.name == "start_game":
                self.enter_game()
            elif tag.name == "leave_game":
                self.enter_lobby()
            else:
                pass
        return response
    def enter_game(self):
        self.mode = Modes.GAME
    def process_game(self, data):
        response = {}
        if len(data.keys):
            self.raws.append(simplewml.Tag("FAKE: loose keys"))
            self.raws[-1].keys = data.keys
        for tag in data.tags:
            self.raws.append(tag)
            if tag.name == "leave_game":
                self.enter_lobby()
            elif tag.name == "host_transfer":
                get_or_create(response, "host_transfer").append((tag.keys["name"], tag.keys["value"]))
            elif tag.name == "change_controller":
                get_or_create(response, "change_controller").append((int(tag.keys["side"]), tag.keys["player"], tag.keys["controller"]))
            elif tag.name == "observer":
                get_or_create(response, "observer_added").append(tag.keys["name"])
            elif tag.name == "observer_quit":
                get_or_create(response, "observer_deleted").append(tag.keys["name"])
            elif tag.name == "turn":
                if len(tag.tags) == 1 and tag.tags[0].name == "command" and\
                    len(tag.tags[0].tags) == 1 and tag.tags[0].tags[0].name == "speak":
                    speak = tag.tags[0].tags[0]
                    speaker = speak.keys["id"]
                    message = speak.keys["message"]
                    get_or_create(response, "message").append((speaker, message))
                    self.chatlog.append(speak)
            else:
                get_or_create(response, "loose_tags").append(tag)
        return response
    def join_game(self, game_id, observe=True):
        join = simplewml.Tag("join")
        join.keys["observe"] = "yes" if observe else "no"
        join.keys["id"] = game_id
        self.write_wml(join)
        self.enter_setup()
    def leave_game(self):
        leave = simplewml.Tag("leave_game")
        self.write_wml(leave)
        # We do this ourselves as we do not always get a [leave_game] in return, though sometimes, we do.
        self.enter_lobby()
    def speak(self, message, target=None):
        if self.mode == Modes.GAME:
            speak = simplewml.Tag("speak")
            speak.keys["message"] = message
            if target:
                speak.keys["team_name"] = target
            command = simplewml.Tag("command")
            command.tags.append(speak)
            tag = simplewml.Tag("turn")
            tag.tags.append(command)
        elif self.mode == Modes.LOBBY:
            if target:
                tag = simplewml.Tag("whisper")
                tag.keys["receiver"] = target
            else:
                tag = simplewml.Tag("message")
            tag.keys["message"] = message
        self.write_wml(tag)
    def end_turn(self):
        end_turn = simplewml.Tag("end_turn")
        command = simplewml.Tag("command")
        command.tags.append(end_turn)
        turn = simplewml.Tag("turn")
        turn.tags.append(command)
        self.write_wml(turn)
    def give_control(self, side, player):
        control = simplewml.Tag("change_controller")
        control.keys["side"] = side
        control.keys["player"] = player
        self.write_wml(control)

if __name__ == "__main__":
    import optparse
    import time

    op = optparse.OptionParser("%prog [options]")

    op.add_option("-n", "--nick",
        help = "Nickname to use on the server")
    op.add_option("-s", "--server",
        help = "Server to connect to")
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

    c = Client(**client_options)
    while True:
        data = c.pollall()
        if not data:
            time.sleep(1)
        else:
            for k,v in data.items():
                print "{0}: {1}".format(k, str(v))
