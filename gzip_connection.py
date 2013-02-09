#!/usr/bin/python

import select
import socket
import struct
import weakref
import zlib

class GzipSocket(object):
    def __init__(self, socket):
        self.sock = socket
        self.pollobj = select.poll()
        self.pollobj.register(self.sock.fileno())
    def poll(self):
        result = self.pollobj.poll(0)
        return len(result) > 0 and result[0][1] & select.EPOLLIN
    def nextint(self):
        packed = self.sock.recv(4, socket.MSG_WAITALL)
        if len(packed) == 4:
            return struct.unpack("!I", packed)[0]
        elif len(packed) == 0:
            return None
        else:
            raise Exception("Incomplete packetlength received")
    def nextfragment(self):
        length = self.nextint()
        if length == None:
            return None
        buf = self.sock.recv(length, socket.MSG_WAITALL)
        # Force gzip format. UNDOCUMENTED?!
        data = zlib.decompress(buf, 16+zlib.MAX_WBITS)
        return data
    def sendint(self, i):
        return self.sock.send(struct.pack("!I", i))
    def sendfragment(self, data):
        # Force gzip format. UNDOCUMENTED?! (and unreachable in zlib.compress)
        compressor = zlib.compressobj(9, zlib.DEFLATED, 16+zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
        buf = compressor.compress(data) + compressor.flush()
        res = self.sendint(len(buf))
        return res + self.sock.send(buf)
    def getpeername(self):
        return self.sock.getpeername()

class GzipServer(object):
    def __init__(self, server="", port=15000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((server, port))
        self.sock.listen(1)
        self.pollobj = select.poll()
        self.pollobj.register(self.sock.fileno())
        self.clients = weakref.WeakValueDictionary()
        self.next_id = 1

    def poll(self):
        result = self.pollobj.poll(0)
        return len(result) > 0 and result[0][1] & select.EPOLLIN
    def accept(self):
        base_sock, _ = self.sock.accept()
        wrapped_sock = GzipSocket(base_sock)
        request = wrapped_sock.nextint()
        if request != 0:
            raise NotImplementedError("connection recovering not supported")
        # synchronize?
        wrapped_sock.connection_num = self.next_id
        self.next_id += 1
        wrapped_sock.sendint(wrapped_sock.connection_num)
        self.clients[wrapped_sock.connection_num] = wrapped_sock
        return wrapped_sock

def GzipClient(server="server.wesnoth.org", port=15000):
    base_sock = socket.create_connection((server, port))
    wrapped_sock = GzipSocket(base_sock)
    wrapped_sock.sendint(0)
    wrapped_sock.connectionnum = wrapped_sock.nextint()
    return wrapped_sock

__all__ = ['GzipServer', 'GzipClient']

