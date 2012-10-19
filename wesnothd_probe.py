#!/usr/bin/python

import optparse

import wesnothd_client

op = optparse.OptionParser("%prog [-s server] <versions>")

op.add_option("-s", "--server", action = "append",
    help = "Server(s) to probe")

options, args = op.parse_args()

servers = options.server
if not servers:
    servers = ["server.wesnoth.org"]
versions = args
if not versions:
    versions = ["test"]

for s in servers:
    for v in versions:
        try:
            client = wesnothd_client.Client(server=s, version=v)
            alive = True
        except Exception as e:
            alive = False
        print "{0}-{1}={2:g}".format(s, v, alive)

