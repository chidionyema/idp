"""A loopback listener the api-port-guard falsifier declares protected.

It accepts and drops every connection, so liveness probes never fill the backlog. The test
runs it under a copy of the interpreter named `estatedecoy`, so pgrep -x, killall and pkill -f
all see that name and a guard bug can only ever reach this process.
"""

import socket
import sys

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", int(sys.argv[1])))
s.listen(16)
while True:
    conn, _ = s.accept()
    conn.close()
