"""WSS room service. TLS is terminated by the configured reverse proxy."""
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from websockets.asyncio.server import serve
from server.rooms import Rooms

MAX_MESSAGE = 32 * 1024 * 1024


def decode(raw):
    if not isinstance(raw, str) or len(raw) > MAX_MESSAGE:
        raise ValueError("Ungültige Nachricht.")
    obj = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Ungültige Zahl")))
    if not isinstance(obj, dict):
        raise ValueError("Ungültige Nachricht.")
    return obj


def credentials(msg):
    identity, secret = msg.get("identity", ""), msg.get("secret", "")
    if not isinstance(identity, str) or not re.fullmatch("[0-9a-f]{32}", identity):
        raise ValueError("Ungültige Teilnehmerkennung.")
    if not isinstance(secret, str) or not re.fullmatch("[0-9a-f]{64}", secret):
        raise ValueError("Ungültige Wiederverbindung.")
    password = msg.get("password", "")
    if not isinstance(password, str) or len(password) > 128:
        raise ValueError("Ungültiges Passwort.")
    return identity, secret, password


class Service:
    def __init__(self):
        self.registry = Rooms()
        self.lock = asyncio.Lock()
        self.connections = 0
        self.outgoing = {}
        self.attempts = {}

    def limit_handshake(self, ws):
        # Internal only; addresses never enter rosters, errors or logs.
        address = ws.remote_address[0] if ws.remote_address else 'local'
        now = time.monotonic()
        self.attempts = {key:value for key,value in self.attempts.items() if now-value[0] < 60}
        started, count = self.attempts.get(address, (now, 0))
        if count >= 120 or len(self.attempts) >= 4096:
            raise ValueError('Zu viele Verbindungsversuche. Bitte eine Minute warten.')
        self.attempts[address] = (started, count+1)

    async def send(self, ws, msg):
        await asyncio.wait_for(ws.send(json.dumps(msg, ensure_ascii=False, allow_nan=False)), 15)

    async def broadcast(self, room, msg):
        encoded = json.dumps(msg, ensure_ascii=False, allow_nan=False)
        if len(encoded.encode()) > MAX_MESSAGE:
            raise ValueError('Gemeinsame Änderung überschreitet das Nachrichtenlimit.')
        for ws in list(room.peers.values()):
            queue = self.outgoing.get(ws)
            if queue is None:
                continue
            try:
                queue.put_nowait(encoded)
            except asyncio.QueueFull:
                # A slow peer reconnects and receives a fresh snapshot; others continue.
                asyncio.create_task(ws.close(1013, 'Neu synchronisieren'))

    async def writer(self, ws, queue):
        try:
            while True:
                raw = await queue.get()
                try:
                    await asyncio.wait_for(ws.send(raw), 15)
                finally:
                    queue.task_done()
        except asyncio.CancelledError:
            raise
        except Exception:
            await ws.close(1013, 'Neu synchronisieren')

    async def handle(self, ws):
        room = None
        identity = None
        writer_task = None
        self.connections += 1
        try:
            if self.connections > 128:
                await ws.close(1013, "Server ausgelastet")
                return
            self.limit_handshake(ws)
            request = decode(await asyncio.wait_for(ws.recv(), 15))
            action = request.get("type")
            if action == "list":
                await self.send(ws, dict(type="rooms", rooms=self.registry.public()))
                return
            identity, secret, password = credentials(request)
            async with self.lock:
                if action == "create":
                    room = await asyncio.to_thread(self.registry.create, request.get("name"), password,
                                                   request.get("maximum"), identity, request.get("state"))
                elif action == "join":
                    room = self.registry.rooms.get(request.get("room"))
                    if room is None:
                        raise ValueError("Raum nicht gefunden oder bereits geschlossen.")
                else:
                    raise ValueError("Unbekannte Anfrage.")
                async with room.lock:
                    await asyncio.to_thread(room.authenticate, identity, secret, request.get("username"), password)
                    previous = room.peers.get(identity)
                    if previous:
                        await previous.close(4001, "Neue Verbindung")
                    room.peers[identity] = ws
                    await self.send(ws, dict(type="snapshot", state=await asyncio.to_thread(room.state.export),
                                            ack=room.users[identity]["last"], room=room.description()))
                    queue = asyncio.Queue(maxsize=4)
                    self.outgoing[ws] = queue
                    writer_task = asyncio.create_task(self.writer(ws, queue))
                    await self.broadcast(room, dict(type="users", users=room.roster()))
            started, count, byte_count = time.monotonic(), 0, 0
            async for raw in ws:
                now = time.monotonic()
                if now - started >= 1:
                    started, count, byte_count = now, 0, 0
                count += 1
                byte_count += len(raw)
                if count > 120 or byte_count > 64 * 1024 * 1024:
                    raise ValueError("Zu viele Daten. Bitte erneut verbinden.")
                msg = decode(raw)
                async with room.lock:
                    if room.peers.get(identity) is not ws:
                        return
                    kind = msg.get("type")
                    if kind == "ping":
                        await self.send(ws, dict(type="ping"))
                    elif kind == "op":
                        result = await asyncio.to_thread(room.operation, identity, msg.get("seq"), msg.get("op"))
                        if result["type"] == "op":
                            await self.broadcast(room, result)
                        else:
                            await self.send(ws, result)
                    elif kind == "cursor":
                        from draw_state import integer
                        x = integer(msg.get("x"), 0, room.state.size[0]-1)
                        y = integer(msg.get("y"), 0, room.state.size[1]-1)
                        user = room.users[identity]
                        if now-user.get("cursor_time", 0) >= .05:
                            user["cursor_time"] = now
                            await self.broadcast(room, dict(type="cursor", identity=identity,
                                                            name=user["name"], x=x, y=y))
                    elif kind in ("close", "kick"):
                        if identity != room.owner:
                            raise ValueError("Nur der Host darf Teilnehmer verwalten.")
                        if kind == "close":
                            await asyncio.gather(*(asyncio.wait_for(self.outgoing[p].join(), 15) for p in list(room.peers.values()) if p in self.outgoing), return_exceptions=True)
                            await asyncio.gather(*(self.send(p, dict(type='ended')) for p in list(room.peers.values())), return_exceptions=True)
                            self.registry.rooms.pop(room.identifier, None)
                            await asyncio.gather(*(p.close() for p in list(room.peers.values())), return_exceptions=True)
                            return
                        target = msg.get("identity")
                        if target == room.owner or target not in room.users:
                            raise ValueError("Ungültiger Teilnehmer.")
                        room.banned.add(target)
                        peer = room.peers.get(target)
                        if peer:
                            await self.send(peer, dict(type="ended"))
                            await peer.close()
                    else:
                        raise ValueError("Unbekannte Nachricht.")
        except Exception as exc:
            try:
                # Do not expose internal exceptions, paths, credentials or IPs.
                message = str(exc) if isinstance(exc, ValueError) else "Verbindung konnte nicht verarbeitet werden."
                await self.send(ws, dict(type="denied", message=message[:180]))
            except Exception:
                pass
        finally:
            self.connections -= 1
            self.outgoing.pop(ws, None)
            if writer_task:
                writer_task.cancel()
                await asyncio.gather(writer_task, return_exceptions=True)
            if room and room.peers.get(identity) is ws:
                room.peers.pop(identity, None)
                room.touched = time.monotonic()
                await self.broadcast(room, dict(type="users", users=room.roster()))


async def main():
    service = Service()
    async with serve(service.handle, os.environ.get("HOST", "127.0.0.1"),
                     int(os.environ.get("PORT", "8765")), max_size=MAX_MESSAGE,
                     max_queue=4, compression=None, ping_interval=20, ping_timeout=20):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
