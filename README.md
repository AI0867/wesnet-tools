wesnothd\_client
================

A no longer correctly-named set of python tools that function as clients or servers using wesnoth's gzip-compressed WML protocol.

Programs
--------

### addond.py
Addon server. Compatible (though not as fully featured) with all campaignd verbs and its index.
### controlbot.py
Wesnothd client. Can be controlled through chat commands to join games, end its turn and give control to other players.
### portmap.py
Maps the wesnothd ports for the product of a list of servers and versions.
### server\_redirector.py
Wesnothd that solely redirects to other wesnothds. Uses [valen](https://github.com/shikadilord/valen)'s report to select servers that are actually up.
### test.py
Wesnothd client. Connects to a server and optionally announces its presence.
### wesnothd\_probe.py
Probes wesnothds with various versions to see whether they are up. Intended as a [valen](https://github.com/shikadilord/valen) component, as shown in the [wesnothd\_client branch](https://github.com/AI0867/valen/tree/wesnothd_client).

Modules
-------

### gzip\_connection.py
Provides GzipClient and GzipServer. The server can be configured to provide non-blocking sockets.
### simplewml.py
Basic WML library. Makes the same assumptions wesnothd's simplewml does.
### wesnothd\_client.py
Wesnothd client. Provides a base for clients that actually do stuff to build on.
### wmlserver.py
Base WML-speaking server. Provides WMLServer and WMLClient to subclass.
