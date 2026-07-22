import asyncio
import logging
import time
from typing import Dict, Optional

from aiohttp import web

log = logging.getLogger(__name__)


class _WsCommandSession:
    """Wraps a real ClientSession so a WS-issued command's own narrative
    (attack rolls, "you say...", NPC replies, aggro hits) reaches the
    WebSocket that issued it, on top of the normal telnet output."""

    def __init__(self, session: "ClientSession", ws: web.WebSocketResponse):
        self._session = session
        self._ws = ws

    @property
    def player(self):
        return self._session.player

    @property
    def server(self):
        return self._session.server

    async def writeln(self, text: str = ""):
        await self._session.writeln(text)
        try:
            await self._ws.send_json({"type": "log", "text": text})
        except ConnectionResetError:
            pass


class MUDServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 4000, ws_port: int = 4001):
        self.host = host
        self.port = port
        self.ws_port = ws_port
        self.sessions: Dict[str, "ClientSession"] = {}  # name -> session
        self.ws_clients: Dict[str, web.WebSocketResponse] = {}  # player name -> ws
        self.state_seq = 0
        self.world = None

    async def start(self):
        from world.loader import WorldLoader
        from session import ClientSession

        log.info("Loading world data...")
        self.world = WorldLoader.load("data/zones")
        log.info(f"World loaded: {len(self.world.rooms)} rooms across {len(self.world.zones)} zones")

        server = await asyncio.start_server(
            self._handle_connection, self.host, self.port
        )
        log.info(f"MUD server listening on {self.host}:{self.port}")

        ws_app = web.Application()
        ws_app.router.add_get("/ws", self._handle_ws)
        ws_runner = web.AppRunner(ws_app)
        await ws_runner.setup()
        ws_site = web.TCPSite(ws_runner, self.host, self.ws_port)
        await ws_site.start()
        log.info(f"WebSocket state feed listening on {self.host}:{self.ws_port}/ws")

        async with server:
            asyncio.create_task(self._respawn_loop())
            asyncio.create_task(self._roaming_loop())
            await server.serve_forever()

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        from session import ClientSession

        addr = writer.get_extra_info("peername")
        log.info(f"New connection from {addr}")
        session = ClientSession(reader, writer, self)
        try:
            await session.run()
        except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            pass
        except Exception as e:
            log.exception(f"Session error from {addr}: {e}")
        finally:
            if session.player and session.player.name in self.sessions:
                del self.sessions[session.player.name]
            log.info(f"Connection closed: {addr}")

    def register_player(self, name: str, session: "ClientSession"):
        self.sessions[name] = session

    def get_session(self, name: str) -> Optional["ClientSession"]:
        return self.sessions.get(name)

    async def _respawn_loop(self):
        TICK = 10  # seconds between checks
        while True:
            await asyncio.sleep(TICK)
            if not self.world:
                continue
            now = time.monotonic()
            for npc_id, npc in self.world.npcs.items():
                if npc.is_alive() or npc.dead_at is None:
                    continue
                if npc.respawn_time == 0:
                    continue
                if now - npc.dead_at < npc.respawn_time:
                    continue
                room = self.world.get_room(npc.spawn_room_id) if npc.spawn_room_id else None
                if not room:
                    continue
                npc.hp = npc.max_hp
                npc.dead_at = None
                npc.looted = False
                npc.conversation_history.clear()
                if npc_id not in room.npc_ids:
                    room.npc_ids.append(npc_id)
                log.info(f"NPC {npc.name} respawned in {room.id}")
                await self.broadcast_to_room(room.id, f"\n{npc.name} stirs back to life.")

    async def _roaming_loop(self):
        import random
        TICK = 120  # seconds between moves
        while True:
            await asyncio.sleep(TICK)
            if not self.world:
                continue
            for npc_id, npc in self.world.npcs.items():
                if not npc.roaming or not npc.is_alive() or not npc.current_room_id:
                    continue
                current_room = self.world.get_room(npc.current_room_id)
                if not current_room or not current_room.exits:
                    continue
                next_room_id = random.choice(list(current_room.exits.values()))
                next_room = self.world.get_room(next_room_id)
                if not next_room:
                    continue
                if npc_id in current_room.npc_ids:
                    current_room.npc_ids.remove(npc_id)
                next_room.npc_ids.append(npc_id)
                npc.current_room_id = next_room_id
                await self.broadcast_to_room(current_room.id, f"{npc.name} packs up and moves on.")
                await self.broadcast_to_room(next_room_id, f"\n{npc.name} rolls in with a creak of cart wheels.")
                log.info(f"Roaming NPC {npc.name} moved to {next_room_id}")

    async def broadcast_to_room(self, room_id: str, message: str, exclude: str = None):
        for name, session in self.sessions.items():
            if name == exclude:
                continue
            if session.player and session.player.current_room_id == room_id:
                await session.writeln(message)
        for name, ws in list(self.ws_clients.items()):
            if name == exclude:
                continue
            session = self.sessions.get(name)
            if session and session.player and session.player.current_room_id == room_id:
                await ws.send_json({"type": "log", "text": message})
        await self.push_room_state(room_id)

    # ─── WebSocket state feed (3D/web client POC) ─────────────────────────────

    async def _handle_ws(self, request: "web.Request") -> web.WebSocketResponse:
        import json

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        identified_name = None
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue
            try:
                data = json.loads(msg.data)
            except ValueError:
                continue

            if data.get("type") == "identify":
                # Piggybacks on an existing telnet-authenticated session rather
                # than implementing a separate login over WebSocket.
                candidate = self.sessions.get(str(data.get("name", "")).capitalize())
                if not candidate or not candidate.player:
                    await ws.send_json({"type": "error", "message": "no such logged-in player"})
                    continue
                identified_name = candidate.player.name
                self.ws_clients[identified_name] = ws
                await self._send_room_state(ws, candidate.player)

            elif data.get("type") == "command":
                if not identified_name:
                    await ws.send_json({"type": "error", "message": "identify first"})
                    continue
                session = self.sessions.get(identified_name)
                if not session or not session.player:
                    await ws.send_json({"type": "error", "message": "player no longer connected"})
                    continue
                line = str(data.get("line", "")).strip()
                if not line:
                    continue
                parts = line.split()
                cmd, args = parts[0].lower(), parts[1:]
                # Runs the exact same dispatch table a telnet player uses, so
                # move/say/talk/attack/flee all stay in sync with no separate
                # rules to maintain for the web client.
                from commands import CommandProcessor
                processor = CommandProcessor(_WsCommandSession(session, ws))
                try:
                    await processor.dispatch(cmd, args)
                except SystemExit:
                    pass  # 'quit' saves and returns; doesn't disconnect the telnet session
                else:
                    # Commands like buy/sell/loot/equip only ever wrote to the
                    # acting player (no broadcast_to_room call), so push a
                    # refresh explicitly, gold/inventory/corpse-removal would
                    # otherwise go stale in the web client until someone else
                    # triggered a broadcast.
                    await self.push_room_state(session.player.current_room_id)

        if identified_name and self.ws_clients.get(identified_name) is ws:
            del self.ws_clients[identified_name]
        return ws

    async def _send_room_state(self, ws: web.WebSocketResponse, player: "Player"):
        room = self.world.get_room(player.current_room_id) if self.world else None
        if not room:
            return
        self.state_seq += 1
        payload = room.to_state_dict(self.world, self.sessions, self.state_seq)
        payload["self"] = player.to_client_state()
        await ws.send_json(payload)

    async def push_room_state(self, room_id: str):
        if not self.ws_clients or not self.world:
            return
        room = self.world.get_room(room_id)
        if not room:
            return
        self.state_seq += 1
        base = room.to_state_dict(self.world, self.sessions, self.state_seq)
        for name, ws in list(self.ws_clients.items()):
            session = self.sessions.get(name)
            if session and session.player and session.player.current_room_id == room_id:
                payload = dict(base)
                payload["self"] = session.player.to_client_state()
                await ws.send_json(payload)
