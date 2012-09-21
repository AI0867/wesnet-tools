#!/usr/bin/python

import select
import socket
import string
import struct
import zlib

class Tag(object):
    def __init__(self, name):
        self.name = name
        self.keys = {}
        self.tags = []
    def __str__(self):
        parts = []
        parts.append('[{0}]'.format(self.name))
        for key in self.keys:
            parts.append('{0}="{1}"'.format(str(key), str(self.keys[key])))
        for tag in self.tags:
            parts.append(str(tag))
        parts.append('[/{0}]'.format(self.name))
        return '\n'.join(parts)
class RootTag(Tag):
    def __init__(self):
        Tag.__init__(self, "ROOT")
    def __str__(self):
        parts = []
        for key in self.keys:
            parts.append('{0}="{1}"'.format(str(key), str(self.keys[key])))
        for tag in self.tags:
            parts.append(str(tag))
        return '\n'.join(parts)

class SimpleWML(object):
    def parse(self, wmlstring):
        root = RootTag()
        self.wmlstring = wmlstring
        self.pos = 0
        self.parse_internal(root)
        if self.pos < len(self.wmlstring):
            print "Only parsed {0} out of {1} characters".format(self.pos, len(self.wmlstring))
        return root

    def next_char(self):
        c = self.wmlstring[self.pos]
        self.pos += 1
        return c
    def next_until(self, endchar):
        newpos = self.wmlstring.find(endchar, self.pos)
        val = self.wmlstring[self.pos:newpos]
        self.pos = newpos + 1
        return val
    def next_tag(self):
        return self.next_until(']')
    def next_key(self):
        return self.next_until('=')
    def next_value(self):
        buf = ""
        c = self.next_char()
        if c == '"':
            endchar = '"'
        else:
            buf += c
            endchar = '\n'
        buf += self.next_until(endchar)
        return buf
    def parse_internal(self, tag):
        while True:
            try:
                c = self.next_char()
            except IndexError:
                break
            if c in string.whitespace:
                continue
            if c == '[':
                tagname = self.next_tag()
                if tagname[0] == '/':
                    if tagname[1:] != tag.name:
                        print "ERROR: incorrect closing tag [{0}] for [{1}]".format(tagname, tag.name)
                    break
                else:
                    newtag = Tag(tagname)
                    tag.tags.append(newtag)
                    self.parse_internal(newtag)
            else:
                name = c + self.next_key()
                value = self.next_value()
                tag.keys[name] = value

class Connection(object):
    def __init__(self, server="server.wesnoth.org", port=15000):
        self.sock = socket.create_connection((server, port))
        self.sendempty()
        self.connectionnum = self.nextint()
        self.pollobj = select.poll()
        self.pollobj.register(self.sock.fileno())

    def nextint(self):
        return struct.unpack(">I", self.sock.recv(4))[0]
    def nextfragment(self):
        length = self.nextint()
        buf = self.sock.recv(length)
        # Force gzip format. UNDOCUMENTED?!
        data = zlib.decompress(buf, 16+zlib.MAX_WBITS)
        return data
    def poll(self):
        return self.pollobj.poll()[0][1] & select.EPOLLIN

    def sendint(self, i):
        return self.sock.send(struct.pack(">I", i))
    def sendempty(self):
        return self.sendint(0)
    def sendfragment(self, data):
        # Force gzip format. UNDOCUMENTED?! (and unreachable in zlib.compress)
        compressor = zlib.compressobj(9, zlib.DEFLATED, 16+zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
        buf = compressor.compress(data) + compressor.flush()
        res = self.sendint(len(buf))
        return res + self.sock.send(buf)

class Client(object):
    def __init__(self, server="server.wesnoth.org", version="1.11", name="lobbybot"):
        self.con = Connection(server)
        self.name = name
        self.wml = SimpleWML()
        while True:
            data = self.read_wml()
            for tag in data.tags:
                if tag.name == "version":
                    t = Tag("version")
                    t.keys["version"] = version
                    self.con.sendfragment(str(t))
                elif tag.name == "reject":
                    raise Exception("Failed to connect: we are version {0} and the server accepts clients of types {1}".format(version, tag.keys["accepted_versions"]))
                elif tag.name == "redirect":
                    self.con = Connection(tag.keys["host"], tag.keys["port"])
                elif tag.name == "mustlogin":
                    t = Tag("login")
                    t.keys["username"] = self.name
                    self.con.sendfragment(str(t))
                elif tag.name == "join_lobby":
                    return
                elif tag.name == "error":
                    raise Exception("Received [error] with code {0} and message: {1}".format(tag.keys["error_code"], tag.keys["message"]))
                else:
                    print "Unknown tag received:\n{0}".format(str(tag))
            if "version" in data.keys:
                # This is the backwards compatibility thing, we should really do it after the [reject]
                raise Exception("Failed to connect: we are version {0} and the server only accepts {1}".format(version, data.keys["version"]))
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
