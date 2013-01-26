#!/usr/bin/python

import json
import socket

import wesnothd_client

UNKNOWN = -1
BAD = 0
GOOD = 1
WEIRD = 2

config = json.load(open("probes.json","r"))

servers = config["servers"]
versions = config["versions"]

for server, url in servers.items():
    for vname, vstring in versions.items():
        try:
            client = wesnothd_client.Client(server=url, version=vstring, name="valen")
            result = GOOD
        except (socket.error, wesnothd_client.VersionRefused):
            result = BAD
        except Exception:
            result = WEIRD
        print "{0}-{1}={2:g}".format(server, vname, result)

