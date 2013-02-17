#!/usr/bin/python

import os
import simplewml
import time
import weakref
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
                for campaign in self.config.tags[0].tags:
                    camp = simplewml.Tag("campaign")
                    camp.keys = campaign.keys.copy()
                    camp.tags = campaign.tags
                    del camp.keys["passphrase"]
                    del camp.keys["upload_ip"]
                    camp.keys.pop("email", None)
                    campaigns.tags.append(camp)
                self.write_wml(campaigns)
            elif tag.name == "request_terms":
                self.send_message("All add-ons uploaded to this server must be licensed under the terms of the GNU General Public License (GPL). By uploading content to this server, you certify that you have the right to place the content under the conditions of the GPL, and choose to do so.")
            elif tag.name == "request_campaign":
                addons = [addon for addon in self.config.tags[0].tags if addon.keys["name"] == tag.keys["name"]]
                if not addons:
                    self.send_error("Add-on '{0}' not found.".format(tag.keys["name"]))
                    continue
                else:
                    filename = addons[0].keys["filename"]
                    self.sock.sendfragment(open(filename).read()) # or self.write_wml(self.wml.parse(open(filename).read()))
                    addons[0].keys["downloads"] = int(addons[0].keys["downloads"]) + 1 # TODO: we should create a better way to do this
            elif tag.name == "upload":
                if not tag.tags or tag.tags[0].name != "data":
                    self.send_error("Add-on rejected: No add-on data was supplied.")
                    continue
                data = tag.tags[0]
                lcname = tag.keys["name"].lower()
                # TODO: check whether important keys are present
                # TODO: check legality of filename
                addon = [addon for addon in self.config.tags[0].tags if addon.keys["name"].lower() == lcname]
                if addon:
                    addon = addon[0]
                    if addon.keys["passphrase"] != tag.keys["passphrase"]:
                        self.send_error("Add-on rejected: The add-on already exists, and your passphrase was incorrect.")
                        continue
                else:
                    addon = simplewml.Tag("campaign")
                    self.config.tags[0].tags.append(addon)
                downloads = addon.keys["downloads"] if "downloads" in addon.keys else 0
                addon.keys = tag.keys.copy() # TODO: be more careful about which keys to copy
                addon.keys["downloads"] = downloads
                filename = "data/{0}".format(tag.keys["name"])
                addon.keys["filename"] = filename
                addon.keys["timestamp"] = int(time.time())
                addon.keys["upload_ip"] = self.sock.getpeername()[0]
                # TODO: translation tags
                roottag = simplewml.RootTag()
                roottag.tags = data.tags
                open(filename, "w").write(str(roottag))
                self.send_message("Add-on accepted.")
    def send_message(self, message):
        msg = simplewml.Tag("message")
        msg.keys["message"] = message
        self.write_wml(msg)
    def send_error(self, message):
        err = simplewml.Tag("error")
        err.keys["message"] = "#Error: {0}".format(message)
        self.write_wml(err)

def save(config):
    open("addond.cfg.new", "w").write(str(config))
    os.rename("addond.cfg.new", "addond.cfg")

class Server(wmlserver.WMLServer):
    def __init__(self, config):
        wmlserver.WMLServer.__init__(self, Client, port=int(config.keys["port"]))
        self.config = config
        # The second argument gets called when the object is finalized
        # It cannot use self though, as that would be a reference
        self._wr = weakref.ref(self, lambda wr, cfg=self.config: save(cfg))
    def accept(self, sock):
        self.clients.append(self.clientclass(sock, self.config))
        print "Accepted a client"
    def loop(self):
        lastsave = time.time()
        while True:
            if lastsave + 60 < time.time():
                save(self.config)
                lastsave = time.time()
            if not self.poll():
                time.sleep(.02)

if __name__ == "__main__":
    # We read the entire file into a string, then iterate over it in the parser
    # It's probably more efficient (especially memory-wise) to use the stream instead
    config = simplewml.SimpleWML().parse(open("addond.cfg").read())

    server = Server(config)

    server.loop()
