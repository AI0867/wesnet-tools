#!/usr/bin/python

import select
import socket
import struct
import zlib

class Connection(object):
    def __init__(self, server="server.wesnoth.org", port=15000):
        self.sock = socket.create_connection((server, port))
        self.sendempty()
        self.connectionnum = self.nextint()
        self.pollobj = select.poll()
        self.pollobj.register(self.sock.fileno())

    def nextint(self):
        return struct.unpack("!I", self.sock.recv(4, socket.MSG_WAITALL))[0]
    def nextfragment(self):
        length = self.nextint()
        buf = self.sock.recv(length, socket.MSG_WAITALL)
        # Force gzip format. UNDOCUMENTED?!
        data = zlib.decompress(buf, 16+zlib.MAX_WBITS)
        return data
    def poll(self):
        return self.pollobj.poll()[0][1] & select.EPOLLIN

    def sendint(self, i):
        return self.sock.send(struct.pack("!I", i))
    def sendempty(self):
        return self.sendint(0)
    def sendfragment(self, data):
        # Force gzip format. UNDOCUMENTED?! (and unreachable in zlib.compress)
        compressor = zlib.compressobj(9, zlib.DEFLATED, 16+zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
        buf = compressor.compress(data) + compressor.flush()
        res = self.sendint(len(buf))
        return res + self.sock.send(buf)

