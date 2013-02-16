#!/usr/bin/python

import simplewml
import wmlserver

class Client(wmlserver.WMLClient):
    def __init__(self, sock, config):
        wmlserver.WMLClient.__init__(self, sock)
        self.config = config
    def process(self, data):
        for tag in data.tags:
            if tag.name == "request_campaign_list":
                campaigns = simplewml.Tag("campaigns")
                # We could do filtering here, but the client never asks for it
                campaigns.tags = [campaign for campaign in self.config.tags[0].tags]
                self.sock.sendfragment(str(campaigns))

class Server(wmlserver.WMLServer):
    def __init__(self, config):
        wmlserver.WMLServer.__init__(self, Client, port=int(config.keys["port"]))
        self.config = config
    def accept(self, sock):
        self.clients.append(self.clientclass(sock, self.config))
        print "Accepted a client"

if __name__ == "__main__":
    # We read the entire file into a string, then iterate over it in the parser
    # It's probably more efficient (especially memory-wise) to use the stream instead
    config = simplewml.SimpleWML().parse(open("addond.cfg").read())

    server = Server(config)

    server.loop()
