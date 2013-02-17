#!/usr/bin/python

import errno
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
        self.sock.sendall(struct.pack("!I", i))
    def sendfragment(self, data):
        # Force gzip format. UNDOCUMENTED?! (and unreachable in zlib.compress)
        compressor = zlib.compressobj(9, zlib.DEFLATED, 16+zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
        buf = compressor.compress(data) + compressor.flush()
        res = self.sendint(len(buf))
        self.sock.sendall(buf)
    def getpeername(self):
        return self.sock.getpeername()

class GzipSocketNonBlocking(GzipSocket):
    def __init__(self, *args, **kwargs):
        GzipSocket.__init__(self, *args, **kwargs)
        self.sock.setblocking(0)
        self.readbuf = ""
        self.writebuf = ""
    def process(self, getpoll=False):
        result = self.pollobj.poll(0)
        if len(result):
            result = result[0][1]
        else:
            result = 0
        acted = False
        if result & select.POLLOUT and self.writebuf:
            sent = self.sock.send(self.writebuf)
            self.writebuf = self.writebuf[sent:]
            acted = True
        if result & select.POLLIN:
            self.readbuf += self.sock.recv(2**16)
            acted = True
        if result & (select.POLLERR | select.POLLNVAL):
            raise socket.Error("poll returned POLLERR or POLLNVAL")
        return result if getpoll else acted
    def poll(self):
        pollresult = self.process(True)
        if pollresult & select.POLLHUP:
            # You're not getting any more, so get the information to the caller
            return True
        if len(self.readbuf) < 4:
            return False
        length = struct.unpack("!I", self.readbuf[:4])[0]
        return len(self.readbuf) >= 4 + length
    def nextint(self):
        pollresult = self.process(True)
        if not self.readbuf and pollresult & select.POLLHUP:
            return None
        if len(self.readbuf) < 4:
            raise socket.Error(errno.EWOULDBLOCK, "Not enough bytes read")
        integer = struct.unpack("!I", self.readbuf[:4])[0]
        self.readbuf = self.readbuf[4:]
        return integer
    def nextfragment(self):
        length = self.nextint()
        if length == None:
            return None
        if len(self.readbuf) < length:
            raise socket.Error(errno.EWOULDBLOCK, "Not enough bytes read")
        # Force gzip format. UNDOCUMENTED?!
        data = zlib.decompress(self.readbuf[:length], 16+zlib.MAX_WBITS)
        self.readbuf = self.readbuf[length:]
        return data
    def sendint(self, i):
        self.writebuf += struct.pack("!I", i)
        self.process()
    def sendfragment(self, data):
        # Force gzip format. UNDOCUMENTED?! (and unreachable in zlib.compress)
        compressor = zlib.compressobj(9, zlib.DEFLATED, 16+zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
        buf = compressor.compress(data) + compressor.flush()
        res = self.sendint(len(buf))
        self.writebuf += buf
        self.process()

class GzipServer(object):
    def __init__(self, server="", port=15000, clientclass=GzipSocket):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((server, port))
        self.sock.listen(1)
        self.pollobj = select.poll()
        self.pollobj.register(self.sock.fileno())
        self.clients = weakref.WeakValueDictionary()
        self.next_id = 1
        self.clientclass = clientclass
    def poll(self):
        result = self.pollobj.poll(0)
        return len(result) > 0 and result[0][1] & select.EPOLLIN
    def accept(self):
        base_sock, _ = self.sock.accept()
        request = GzipSocket(base_sock).nextint() # We need to block for this one
        wrapped_sock = self.clientclass(base_sock)
        if request != 0:
            raise NotImplementedError("connection recovering not supported")
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

