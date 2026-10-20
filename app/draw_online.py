"""Online transport using the same desktop state and pending-operation interface."""
import json
import threading
from urllib.parse import urlparse
from websockets.sync.client import connect
from draw_network import DrawClient
from draw_state import SharedDrawing

ENDPOINT = "wss://server.repaintko.com"
MAX_MESSAGE = 32 * 1024 * 1024


def connection(endpoint=ENDPOINT):
    url = urlparse(endpoint)
    if url.scheme != "wss" and not (url.scheme == "ws" and url.hostname in ("127.0.0.1", "::1", "localhost")):
        raise ValueError("Online-Verbindungen benötigen WSS.")
    return connect(endpoint, legacy=True, open_timeout=10, max_size=MAX_MESSAGE, compression=None,
                   proxy=None, ping_interval=20, ping_timeout=20)


def send(ws, msg):
    raw = json.dumps(msg, ensure_ascii=False, allow_nan=False)
    if len(raw.encode()) > MAX_MESSAGE:
        raise ValueError("Online-Aktion ist zu groß. Bitte kleinere Bereiche bearbeiten.")
    ws.send(raw)


def list_rooms(endpoint=ENDPOINT):
    with connection(endpoint) as ws:
        send(ws, dict(type="list"))
        msg = json.loads(ws.recv(timeout=15))
        if msg.get("type") != "rooms":
            raise ValueError("Raumliste konnte nicht geladen werden.")
        return [dict(r, online=True, endpoint=endpoint) for r in msg["rooms"]]


class OnlineClient(DrawClient):
    def writer(self, sock, dead):
        sent = 0
        try:
            while not self.stop_event.is_set() and not dead.wait(.016):
                with self.lock:
                    out = [(seq, op) for seq, op in self.pending.items() if seq > sent]
                for seq, op in out:
                    send(sock, dict(type="op", seq=seq, op=op))
                    sent = seq
                with self.lock:
                    cursor=self.cursor_pending;self.cursor_pending=None
                if cursor:send(sock,dict(type="cursor",x=cursor[0],y=cursor[1]))
        except Exception:
            sock.close()

    def run(self):
        while not self.stop_event.is_set() and not self.terminal:
            sock = None
            dead = threading.Event()
            try:
                self.on_status("Verbinde mit Online-Raum …", False)
                sock = connection(self.server.get("endpoint", ENDPOINT))
                self.socket = sock
                request = dict(type="join", room=self.server.get("id"), identity=self.identity,
                               secret=self.secret, username=self.username, password=self.password)
                if self.server.get("create"):
                    request.update(type="create", state=self.server["state"], name=self.server["name"],
                                   maximum=self.server["maximum"])
                send(sock, request)
                first = json.loads(sock.recv(timeout=30))
                if first.get("type") == "denied":
                    self.terminal = True
                    raise ValueError(first["message"])
                if first.get("type") != "snapshot":
                    raise ValueError("Keine vollständige Zeichnung empfangen.")
                self.server.update(first["room"])
                self.server.pop("create", None)
                self.server.pop("state", None)
                state = SharedDrawing.restore(first["state"])
                with self.lock:
                    self.state = state
                    self.changed = True
                    self.pending = {n: op for n, op in self.pending.items() if n > first["ack"]}
                    self.connected = True
                self.on_status("Online · " + self.server["name"] + " · Raum-ID: " + self.server["id"], True)
                threading.Thread(target=self.writer, args=(sock, dead), daemon=True).start()
                for raw in sock:
                    msg = json.loads(raw)
                    kind = msg.get("type")
                    if kind in ("ended", "denied"):
                        self.terminal = True
                        self.on_status(msg.get("message", "Die Sitzung wurde beendet. Die Zeichnung kann gespeichert werden."), False)
                        break
                    if kind == "users":
                        self.on_users(msg["users"])
                    elif kind == "cursor":
                        if msg["identity"] != self.identity:self.on_cursor(msg)
                    elif kind in ("ack", "rejected"):
                        with self.lock:
                            self.pending.pop(msg["seq"], None)
                            self.changed = True
                            if kind == "rejected":
                                self.last_rejection = msg["message"]
                        if kind == "rejected":
                            self.on_error(msg["message"])
                    elif kind == "op":
                        with self.lock:
                            if msg["revision"] != self.state.revision + 1:
                                raise ValueError("Zeichnung wird neu synchronisiert.")
                            self.state.apply(msg["op"])
                            self.changed = True
                            if msg["identity"] == self.identity:
                                self.pending.pop(msg["seq"], None)
                        if msg["identity"] != self.identity:
                            self.on_operation(msg["op"])
            except Exception as exc:
                if not self.stop_event.is_set():
                    self.on_status(str(exc) if self.terminal else "Online-Verbindung unterbrochen · erneuter Versuch …", False)
            finally:
                dead.set()
                if sock:
                    sock.close()
                self.socket = None
                with self.lock:
                    self.connected = False
            if not self.terminal:
                self.stop_event.wait(2)

    def administer(self, kind, identity=None):
        if not self.connected or not self.socket:
            raise ConnectionError("Keine Verbindung.")
        send(self.socket, dict(type=kind, identity=identity))

    def stop(self):
        self.stop_event.set()
        self.connected = False
        if self.socket:
            self.socket.close()
