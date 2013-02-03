#!/usr/bin/python

import optparse
import sys

import simplewml
import wesnothd_client

op = optparse.OptionParser("%prog [options] [server]")

#op.add_option("-p", "--port",
#    help = "Port to connect to initially")
op.add_option("-s", "--speak", action = "store_true",
    help = "Speak after joining the server")
op.add_option("-v", "--version",
    help = "Wesnoth version we pretend to be")

options, args = op.parse_args()

client_args = {}

if len(args) > 0:
    print "Connecting to {0}".format(args[0])
    client_args["server"] = args[0]
if options.version:
    print "Simulating wesnoth version {0}".format(options.version)
    client_args["version"] = options.version

try:
    client = wesnothd_client.Client(**client_args)
    if options.speak:
        msg = simplewml.Tag("message")
        msg.keys["message"] = "Hello, World!"
        client.con.sendfragment(str(msg))
    result = True
    while result:
        result = client.poll()
        if True and result:
            print result
except Exception as e:
    print str(e)
    sys.exit(1)
else:
    conn_to = client.con.sock.getpeername()
    print "Connected to {0} on port {1} with version {2}".format(conn_to[0], conn_to[1], options.version)

