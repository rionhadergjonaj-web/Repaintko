"""Authoritative rooms; shared with the desktop's existing transaction engine."""
import hashlib
import hmac
import secrets
import time
import asyncio
from dataclasses import dataclass, field

from draw_state import SharedDrawing, integer, name


@dataclass
class Room:
    title: str
    maximum: int
    owner: str
    state: SharedDrawing
    salt: bytes
    password_hash: bytes
    private: bool
    identifier: str = field(default_factory=lambda: secrets.token_hex(8))
    users: dict = field(default_factory=dict)
    peers: dict = field(default_factory=dict)
    banned: set = field(default_factory=set)
    touched: float = field(default_factory=time.monotonic)
    lock: object = field(default_factory=asyncio.Lock)

    def description(self):
        return dict(id=self.identifier, name=self.title, players=len(self.peers),
                    maximum=self.maximum, locked=self.private)

    def roster(self):
        return [dict(id=key, name=self.users[key]["name"], host=key == self.owner)
                for key in self.peers]

    def authenticate(self, identity, secret, username, password):
        if identity in self.banned:
            raise ValueError("Du wurdest aus diesem Raum entfernt.")
        expected = hashlib.scrypt(password.encode(), salt=self.salt, n=16384, r=8, p=1)
        if not hmac.compare_digest(expected, self.password_hash):
            raise ValueError("Das Passwort ist falsch.")
        old = self.users.get(identity)
        secret_hash = hashlib.sha256(secret.encode()).digest()
        if old and not hmac.compare_digest(old["secret"], secret_hash):
            raise ValueError("Wiederverbindung abgelehnt.")
        if identity not in self.peers and len(self.peers) >= self.maximum:
            raise ValueError("Der Raum ist voll.")
        if not old:
            if len(self.users) >= 256:
                raise ValueError("Teilnehmerlimit dieser Sitzung erreicht.")
            self.users[identity] = dict(name=name(username), secret=secret_hash, last=0)
        self.touched = time.monotonic()

    def operation(self, identity, seq, op):
        user = self.users[identity]
        integer(seq, 1, 2**53)
        if seq <= user["last"]:
            return dict(type="ack", seq=seq)
        if seq != user["last"] + 1:
            raise ValueError("Aktionsreihenfolge unterbrochen.")
        try:
            def bounded(operation):
                if not isinstance(operation, dict):
                    raise ValueError("Ungültige Aktion.")
                if operation.get("kind") == "batch":
                    operations = operation.get("ops")
                    if not isinstance(operations, list) or len(operations) > 64:
                        raise ValueError("Verlauf zu groß.")
                    for child in operations:
                        if not isinstance(child, dict) or child.get("kind") != "edit":
                            raise ValueError("Ungültiger Verlauf.")
                        bounded(child)
                if "replacement" in operation:
                    snapshot = operation["replacement"]["after"]
                    w, h = snapshot["size"]
                    integer(w, 1, 16384)
                    integer(h, 1, 16384)
                    if w*h*len(snapshot["layers"]) > 16_000_000:
                        raise ValueError("Online-Ebenenlimit erreicht.")
                if operation.get("kind") == "add":
                    if self.state.size[0]*self.state.size[1]*(len(self.state.ids)+1) > 16_000_000:
                        raise ValueError("Online-Ebenenlimit erreicht.")
            bounded(op)
            normalized = self.state.normalize(op)
            self.state.apply(normalized)
            result = dict(type="op", revision=self.state.revision,
                          identity=identity, seq=seq, op=normalized)
        except (ValueError, KeyError, TypeError, IndexError):
            result = dict(type="rejected", seq=seq,
                          message="Änderung konnte nicht übernommen werden. Dein Entwurf bleibt erhalten; bitte neu synchronisieren.")
        user["last"] = seq
        self.touched = time.monotonic()
        return result


class Rooms:
    def __init__(self, maximum=8):
        self.maximum = maximum
        self.rooms = {}

    def create(self, title, password, maximum, identity, snapshot):
        self.expire()
        for room in self.rooms.values():
            if room.owner == identity:
                # Retry after losing the initial snapshot; authenticate afterwards.
                return room
        if len(self.rooms) >= self.maximum:
            raise ValueError("Der Server hat seine Raumkapazität erreicht.")
        integer(maximum, 2, 32)
        state = SharedDrawing.restore(snapshot)
        # A bounded server allocation, independently of the LAN's larger limits.
        if state.size[0] * state.size[1] * len(state.ids) > 16_000_000:
            raise ValueError("Online: maximal 16 Millionen Ebenenpixel pro Raum.")
        salt = secrets.token_bytes(16)
        room = Room(name(title), maximum, identity, state, salt,
                    hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1),
                    bool(password))
        self.rooms[room.identifier] = room
        return room

    def public(self):
        self.expire()
        return [r.description() for r in self.rooms.values() if not r.private]

    def expire(self):
        for key, room in list(self.rooms.items()):
            if not room.peers and time.monotonic() - room.touched > 600:
                del self.rooms[key]
