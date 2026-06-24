import asyncio
import logging
import time
from typing import Dict, Optional

log = logging.getLogger(__name__)


class MUDServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 4000):
        self.host = host
        self.port = port
        self.sessions: Dict[str, "ClientSession"] = {}  # name -> session
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

        async with server:
            asyncio.create_task(self._respawn_loop())
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

    async def broadcast_to_room(self, room_id: str, message: str, exclude: str = None):
        for name, session in self.sessions.items():
            if name == exclude:
                continue
            if session.player and session.player.current_room_id == room_id:
                await session.writeln(message)
