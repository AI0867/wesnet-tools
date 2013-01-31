#!/usr/bin/python

import collections
import gzip_client
import random
import simplewml

class VersionRefused(Exception):
    pass

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type("Enum", (), enums)

Modes = enum("CONNECTING", "LOBBY", "GAME")

class Client(object):
    def __init__(self, server="server.wesnoth.org", version="1.11.1", name="lobbybot"):
        self.con = gzip_client.Connection(server)
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
                return self.process_connecting(data)
            elif self.mode == Modes.LOBBY:
                return self.process_lobby(data)
            else:
                assert False
        return False
    def pollall(self, block=False):
        response = collections.OrderedDict()
        lastpoll = self.poll()
        while lastpoll:
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
                self.con = gzip_client.Connection(tag.keys["host"], tag.keys["port"])
            elif tag.name == "mustlogin":
                t = simplewml.Tag("login")
                self.name = self.basename
                t.keys["username"] = self.name
                self.write_wml(t)
            elif tag.name == "join_lobby":
                self.last_ping = 0
                self.users = []
                self.games = []
                self.chatlog = collections.deque([], 100)
                self.mode = Modes.LOBBY
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
    def process_lobby(self, data):
        response = collections.OrderedDict()
        replaced_users = False
        def get_or_create(dictionary, key):
            if key not in dictionary:
                dictionary[key] = []
            return dictionary[key]
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
                    del self.users[pair[0]]
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
                    del self.games[pair[0]]
                if "game_added" in response and "game_deleted" in response:
                    response["game_modified"] = [game for game in response["game_added"] if game in response["game_deleted"]]
                    response["game_added"] = [game for game in response["game_added"] if game not in response["game_modified"]]
                    response["game_deleted"] = [game for game in response["game_deleted"] if game not in response["game_modified"]]
            else:
                assert False, "Got unknown tag {0}".format(tag.name)

        # Filter out empty lists and such
        filtered_response = collections.OrderedDict()
        for key in response:
            if response[key]:
                filtered_response[key] = response[key]
        return filtered_response

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

    c = Client(**client_options)
    while True:
        data = c.pollall()
        if not data:
            time.sleep(1)
        else:
            for k,v in data.items():
                print "{0}: {1}".format(k, str(v))
