import gzip_connection
import simplewml
import time
import traceback

class WMLClient(object):
    def __init__(self, sock):
        self.sock = sock
        self.wml = simplewml.SimpleWML()
    def poll(self):
        if self.sock.poll():
            frag = self.sock.nextfragment()
            if frag == None:
                raise StopIteration
            data = self.wml.parse(frag)
            self.process(data)
            return True
        return self.sock.process()
    def process(self, data):
        raise NotImplementedError
    def write_wml(self, wml):
        self.sock.sendfragment(str(wml))

class WMLServer(object):
    def __init__(self, clientclass, **kwargs):
        self.clientclass = clientclass
        self.sock = gzip_connection.GzipServer(clientclass=gzip_connection.GzipSocketNonBlocking, **kwargs)
        self.clients = []
    def poll(self):
        acted = False
        if self.sock.poll():
            self.accept(self.sock.accept())
            acted = True
        for client in self.clients:
            try:
                if client.poll():
                    acted = True
            except StopIteration:
                self.clients.remove(client)
            except Exception as e:
                print "A client died:"
                traceback.print_exc()
                self.clients.remove(client)
        return acted
    def accept(self, sock):
        self.clients.append(self.clientclass(sock))
    def loop(self):
        while True:
            if not self.poll():
                time.sleep(.02)
