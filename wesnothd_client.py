#!/usr/bin/python

import gzip_client
import random
import simplewml

class VersionRefused(Exception):
    pass

class Client(object):
    def __init__(self, server="server.wesnoth.org", version="1.11", name="lobbybot"):
        self.con = gzip_client.Connection(server)
        self.basename = name
        self.wml = simplewml.SimpleWML()
        while True:
            data = self.read_wml()
            for tag in data.tags:
                if tag.name == "version":
                    t = simplewml.Tag("version")
                    t.keys["version"] = version
                    self.con.sendfragment(str(t))
                elif tag.name == "reject":
                    raise VersionRefused("Failed to connect: we are version {0} and the server accepts clients of types {1}".format(version, tag.keys["accepted_versions"]))
                elif tag.name == "redirect":
                    self.con = gzip_client.Connection(tag.keys["host"], tag.keys["port"])
                elif tag.name == "mustlogin":
                    t = simplewml.Tag("login")
                    self.name = self.basename
                    t.keys["username"] = self.name
                    self.con.sendfragment(str(t))
                elif tag.name == "join_lobby":
                    return
                elif tag.name == "error":
                    if tag.keys.get("error_code") == "101":
                        t = simplewml.Tag("login")
                        self.name = "{0}{1:03}".format(self.basename, random.randint(0,999))
                        t.keys["username"] = self.name
                        self.con.sendfragment(str(t))
                    else:
                        raise Exception("Received [error] with code {0} and message: {1}".format(tag.keys["error_code"], tag.keys["message"]))
                else:
                    sys.stderr.write("Unknown tag received:\n{0}\n".format(str(tag)))
            if "version" in data.keys:
                # This is the backwards compatibility thing, we should really do it after the [reject]
                raise VersionRefused("Failed to connect: we are version {0} and the server only accepts {1}".format(version, data.keys["version"]))
    def read_wml(self):
        raw = self.con.nextfragment()
        return self.wml.parse(raw)
    def poll(self):
        if self.con.poll():
            data = self.read_wml()
            return data

if __name__ == "__main__":
    import time
    c = Client()
    while True:
        data = c.poll()
        if not data:
            time.sleep(1)
        else:
            print data
