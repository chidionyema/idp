"""A Redis that exists only for the tests.

The estate's gate has to run offline -- no docker daemon, no cluster, no
network -- and the L1/L2 layers talk RESP to Redis. So the tests speak RESP
to this: a real socket, a real protocol, a real thread. What it proves is the
client's protocol handling and the wrapper's behaviour, not Redis itself.

The subset is the one the store uses: PING, SET (with EX), GET, KEYS, DEL.
"""

from __future__ import annotations

import fnmatch
import socket
import threading


class FakeRedisServer:
    def __init__(self, host="127.0.0.1", port=0):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((host, port))
        self._socket.listen(8)
        self.host, self.port = self._socket.getsockname()
        self.data = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    # -- lifecycle -------------------------------------------------------
    def stop(self):
        self._stop.set()
        try:
            self._socket.close()
        except OSError:
            pass

    def _serve(self):
        while not self._stop.is_set():
            try:
                client, _ = self._socket.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(client,), daemon=True).start()

    # -- protocol --------------------------------------------------------
    def _handle(self, client):
        buffer = b""
        try:
            while not self._stop.is_set():
                chunk = client.recv(65536)
                if not chunk:
                    return
                buffer += chunk
                while True:
                    command, buffer = self._parse(buffer)
                    if command is None:
                        break
                    self._reply(client, command)
        except OSError:
            return
        finally:
            try:
                client.close()
            except OSError:
                pass

    def _parse(self, buffer):
        if not buffer.startswith(b"*"):
            return None, buffer
        try:
            header, rest = buffer.split(b"\r\n", 1)
        except ValueError:
            return None, buffer
        count = int(header[1:])
        args = []
        for _ in range(count):
            if not rest.startswith(b"$"):
                return None, buffer
            length_line, rest = rest.split(b"\r\n", 1)
            length = int(length_line[1:])
            if len(rest) < length + 2:
                return None, buffer
            args.append(rest[:length].decode())
            rest = rest[length + 2 :]
        return args, rest

    def _reply(self, client, command):
        name = command[0].upper()
        if name == "PING":
            self._send(client, b"+PONG\r\n")
        elif name == "SET":
            self.data[command[1]] = command[2]
            self._send(client, b"+OK\r\n")
        elif name == "GET":
            value = self.data.get(command[1])
            if value is None:
                self._send(client, b"$-1\r\n")
            else:
                payload = value.encode()
                self._send(client, b"$%d\r\n%s\r\n" % (len(payload), payload))
        elif name == "KEYS":
            pattern = command[1] if len(command) > 1 else "*"
            matched = sorted(key for key in self.data if fnmatch.fnmatch(key, pattern))
            payload = ("\r\n".join(matched)).encode()
            self._send(
                client, b"*%d\r\n$%d\r\n%s\r\n" % (len(matched), len(payload), payload)
            )
        elif name == "DEL":
            removed = 0
            for key in command[1:]:
                if key in self.data:
                    del self.data[key]
                    removed += 1
            self._send(client, b":%d\r\n" % removed)
        else:
            self._send(client, b"-ERR unknown command\r\n")

    @staticmethod
    def _send(client, payload):
        client.sendall(payload)
