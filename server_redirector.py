#!/usr/bin/python

import fnmatch
import gzip_connection
import simplewml
import traceback

class Config(object):
    _borg = {}
    def __new__(cls):
        self = object.__new__(cls)
        self.__dict__ = cls._borg
        return self
    def read(self, filename):
        self.config = json.load(open(filename))
        self.valen = self.config["valen"]
        self.versions = self.config["versions"]
        self.servers = self.config["servers"]
    def version_by_filter(self, versionstr):
        for release in self.versions:
            if fnmatch.fnmatch(versionstr, release["filter"]):
                return release
        return None
    def version_by_name(self, versionname):
        for release in self.versions:
            if release["name"] == versionname:
                return release
        return None

class Valen(object):
    def __init__(self):
        # Format: (servername, versionname, status)
        self.servers = []
        for line in open(Config().valen).readlines():
            if not line.startswith("mp-"):
                continue
            k,v = line.split("=")
            ks = k.split("-")
            if len(ks) == 3:
                self.servers.append((ks[1], ks[2], int(v)))
    def active_servers(self):
        return [server for server in self.servers if server[2] == 1]
    def active_versionnames(self):
        return set([server[1] for server in self.active_servers()])

# REFACTOR
def find_valid_servernames(versionname):
    return [server[0] for server in Valen().active_servers() if server[1] == versionname]

# REFACTOR
def versions_up():
    versions_up = set([server[1] for server in Valen().active_servers()])
    return [version["filter"] for version in Config().versions if version["name"] in versions_up]
    #return [Config().version_by_name(version)["filter"] for version in versions_up]

# REFACTOR
def direct_version(version):
    releaseobj = Config().version_by_filter(version)
    if releaseobj:
        servers_up = find_valid_servernames(releaseobj["name"])
        server_objs = Config().servers
        server_objs.sort(key=lambda x: x["order"])
        candidates = [s["host"] for s in server_objs if s["name"] in servers_up]
    else:
        candidates = []
    if len(candidates):
        redir = simplewml.Tag("redirect")
        redir.keys["host"] = candidates[0]
        redir.keys["port"] = releaseobj["port"]
        return redir
    else:
        reject = simplewml.Tag("reject")
        reject.keys["accepted_versions"] = ",".join(versions_up())
        if "." not in version or int(version.split(".")[1]) < 11:
            root = simplewml.RootTag()
            root.tags.append(reject)
            root.keys["version"] = reject.keys["accepted_versions"]
            reject = root
        return reject

# Some of this class should be factored out
class Client(object):
    def __init__(self, sock):
        self.sock = sock
        self.sock.sendfragment(str(simplewml.Tag("version")))
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
            if tag.name == "version":
                redir_tag = direct_version(tag.keys["version"])
                self.sock.sendfragment(str(redir_tag))

if __name__ == "__main__":
    import json
    import optparse
    import time

    op = optparse.OptionParser("%prog [options]")

    op.add_option("-c", "--config",
        default = "server_redirector.json",
        help = "Path to config file")

    options, args = op.parse_args()

    Config().read(options.config)

    server = gzip_connection.GzipServer()
    clients = []

    while True:
        acted = False
        if server.poll():
            clients.append(Client(server.accept()))
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
