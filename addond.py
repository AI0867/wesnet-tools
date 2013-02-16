#!/usr/bin/python

import gzip_connection
import simplewml
import traceback

class Client(object):
    def __init__(self, sock, config):
        self.sock = sock
        self.config = config
    def poll(self):
        if self.sock.poll():
            self.process()
            return True
        return False
    def process(self):
        raw = self.sock.nextfragment()
        if raw == None:
            raise StopIteration
        data = simplewml.SimpleWML().parse(raw)
        for tag in data.tags:
            if tag.name == "request_campaign_list":
                campaigns = simplewml.Tag("campaigns")
                # We could do filtering here, but the client never asks for it
                campaigns.tags = [campaign for campaign in self.config.tags[0].tags]
                self.sock.sendfragment(str(campaigns))

if __name__ == "__main__":
    import time

    # We read the entire file into a string, then iterate over it in the parser
    # It's probably more efficient (especially memory-wise) to use the stream instead
    config = simplewml.SimpleWML().parse(open("addond.cfg").read())

    server = gzip_connection.GzipServer(port=int(config.keys["port"]))
    clients = []

    while True:
        acted = False
        if server.poll():
            clients.append(Client(server.accept(), config))
            print "Accepted a client"
            acted = True
        for client in clients:
            try:
                if client.poll():
                    acted = True
            except StopIteration:
                clients.remove(client)
            except Exception as e:
                print "A client died:"
                traceback.print_exc()
                clients.remove(client)
        if not acted:
            time.sleep(1)

