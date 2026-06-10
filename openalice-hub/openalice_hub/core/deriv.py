"""
Deriv synthetics feed (Volatility 75, Boom/Crash 500...) — minimal RFC6455
websocket client over stdlib ssl sockets. Token read from <hub>/.env
(DERIV_TOKEN=...), which is gitignored — never committed.

Symbols: R_75 (Vol 75), R_100, R_50, R_25, R_10, 1HZ75V (Vol 75 1s),
BOOM500, BOOM1000, CRASH500, CRASH1000, stpRNG (Step) ...
"""
from __future__ import annotations
import os, ssl, json, socket, base64, struct

HUB = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOST = "ws.derivws.com"
PATH = "/websockets/v3?app_id=1089"   # public app id; token (if any) sent via authorize


def _token() -> str:
    try:
        for line in open(os.path.join(HUB, ".env")):
            if line.startswith("DERIV_TOKEN="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get("DERIV_TOKEN", "")


class _WS:
    def __init__(self, host=HOST, path=PATH, timeout=20):
        raw = socket.create_connection((host, 443), timeout=timeout)
        self.s = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.send((f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
                     f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                     f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
        hdr = b""
        while b"\r\n\r\n" not in hdr:
            hdr += self.s.recv(1024)
        if b"101" not in hdr.split(b"\r\n", 1)[0]:
            raise ConnectionError("websocket handshake failed")

    def _read_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("socket closed")
            buf += chunk
        return buf

    def send_json(self, obj):
        payload = json.dumps(obj).encode()
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        n = len(payload)
        if n < 126:
            head = struct.pack("!BB", 0x81, 0x80 | n)
        elif n < 65536:
            head = struct.pack("!BBH", 0x81, 0x80 | 126, n)
        else:
            head = struct.pack("!BBQ", 0x81, 0x80 | 127, n)
        self.s.send(head + mask + masked)

    def recv_json(self):
        while True:
            b1, b2 = self._read_exact(2)
            opcode = b1 & 0x0F
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack("!H", self._read_exact(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", self._read_exact(8))[0]
            payload = self._read_exact(n) if n else b""
            if opcode == 9:                      # ping -> pong
                mask = os.urandom(4)
                self.s.send(struct.pack("!BB", 0x8A, 0x80 | len(payload)) + mask +
                            bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
                continue
            if opcode == 8:
                raise ConnectionError("server closed")
            if opcode in (1, 2):
                return json.loads(payload.decode())

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


def get_candles(symbol="R_75", granularity=86400, count=1000) -> list[dict]:
    ws = _WS()
    try:
        tok = _token()
        if tok:
            ws.send_json({"authorize": tok})
            auth = ws.recv_json()
            if auth.get("error"):
                pass  # data for synthetics is public; continue unauthorized
        ws.send_json({"ticks_history": symbol, "style": "candles",
                      "granularity": granularity, "count": min(count, 5000),
                      "end": "latest"})
        while True:
            msg = ws.recv_json()
            if msg.get("error"):
                raise RuntimeError(f"deriv: {msg['error'].get('message')}")
            if "candles" in msg:
                return [{"t": int(c["epoch"]), "o": float(c["open"]), "h": float(c["high"]),
                         "l": float(c["low"]), "c": float(c["close"]), "v": 0.0}
                        for c in msg["candles"]]
    finally:
        ws.close()
