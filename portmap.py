#!/usr/bin/python

import optparse
import pprint
import sys

import wesnothd_client

op = optparse.OptionParser("%prog <version>[,version]* [server[,server]*]")

options, args = op.parse_args()

if len(args) == 0 or len(args) > 2:
    op.print_usage()
    sys.exit(1)
elif len(args) == 1:
    servers = ["server.wesnoth.org"]
else:
    servers = args[1].split(",")
versions = args[0].split(",")

portmap = {}

for server in servers:
    for version in versions:
        try:
            client = wesnothd_client.Client(server=server, version=version)
            peer = client.con.sock.getpeername()
            if not peer in portmap: portmap[peer] = []
            portmap[peer].append(version)
        except:
            pass

pprint.pprint(portmap)
