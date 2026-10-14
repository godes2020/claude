import os, socket, struct, sys
from urllib.parse import urlparse
HOST = os.environ.get("MC_RCON_HOST", "31.57.34.167")
PORT = int(os.environ.get("MC_RCON_PORT", "30190"))

def connect():
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not proxy:
        return socket.create_connection((HOST, PORT), timeout=15)
    p = urlparse(proxy)
    s = socket.create_connection((p.hostname, p.port), timeout=15)
    s.sendall(f"CONNECT {HOST}:{PORT} HTTP/1.1\r\nHost: {HOST}:{PORT}\r\n\r\n".encode())
    hdr = b""
    while b"\r\n\r\n" not in hdr:
        c = s.recv(1)
        if not c: raise ConnectionError("proxy closed")
        hdr += c
    if b" 200 " not in hdr.split(b"\r\n")[0]:
        raise ConnectionError(hdr.split(b"\r\n")[0].decode())
    return s

def send(s, i, t, body):
    p = struct.pack("<ii", i, t) + body.encode() + b"\x00\x00"
    s.sendall(struct.pack("<i", len(p)) + p)

def recv(s):
    def ex(n):
        d = b""
        while len(d) < n:
            c = s.recv(n - len(d))
            if not c: raise ConnectionError("closed")
            d += c
        return d
    (n,) = struct.unpack("<i", ex(4)); d = ex(n)
    return struct.unpack("<ii", d[:8])[0], d[8:-2].decode("utf-8", "replace")

with connect() as s:
    send(s, 1, 3, os.environ["MC_RCON_PASSWORD"])
    if recv(s)[0] == -1: sys.exit("wrong RCON password")
    for i, cmd in enumerate(sys.argv[1:] or ["list"], 2):
        send(s, i, 2, cmd); print(">", cmd); print(recv(s)[1])
