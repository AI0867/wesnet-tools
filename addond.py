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
                self.write_wml(campaigns)
            elif tag.name == "request_terms":
                self.send_message("All add-ons uploaded to this server must be licensed under the terms of the GNU General Public License (GPL). By uploading content to this server, you certify that you have the right to place the content under the conditions of the GPL, and choose to do so.")
    def send_message(self, message):
        msg = simplewml.Tag("message")
        msg.keys["message"] = message
        self.write_wml(msg)

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
