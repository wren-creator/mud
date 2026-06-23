import asyncio
import logging
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from server import MUDServer
    from entities.player import Player

log = logging.getLogger(__name__)

# Telnet protocol bytes
IAC  = bytes([255])
WILL = bytes([251])
WONT = bytes([252])
DO   = bytes([253])
DONT = bytes([254])
ECHO = bytes([1])
SGA  = bytes([3])

_P = "\033[1;35m"   # bold magenta — Spider Queen
_C = "\033[1;36m"   # bold cyan — Undermountain
_W = "\033[2;35m"   # dim magenta — web lattice
_D = "\033[2m"      # dim
_R = "\033[0m"      # reset

_TITLE_ART = (
    "   _   _           _                                  _        _\r\n"
    "  | | | |_ __   __| | ___ _ __ _ __ ___   ___  _   _| |_ __ _(_)_ __\r\n"
    "  | | | | '_ \\ / _` |/ _ \\ '__| '_ ` _ \\ / _ \\| | | | __/ _` | | '_ \\\r\n"
    "  | |_| | | | | (_| |  __/ |  | | | | | | (_) | |_| | || (_| | | | | |\r\n"
    "   \\___/|_| |_|\\__,_|\\___|_|  |_| |_| |_|\\___/ \\__,_|\\__\\__,_|_|_| |_|"
)

_WEB = (
    r"  * · * · * · * · * · * · * · * · * · * · * · * · * · * · * · * ·" + "\r\n"
    r"   \ / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ / \ /" + "\r\n"
    r"  · * · * · * · * · * · * · * · * · * · * · * · * · * · * · * · *"
)

BANNER = (
    "\r\n"
    + _P
    + "  ════════════════════════════════════════════════════════════════\r\n"
    + "\r\n"
    + "    ✶  C I T Y   O F   T H E   S P I D E R   Q U E E N  ✶\r\n"
    + "\r\n"
    + "  ════════════════════════════════════════════════════════════════\r\n"
    + _R + _W + "\r\n"
    + _WEB + "\r\n"
    + _R + _C
    + _TITLE_ART
    + _R + "\r\n\r\n"
    + _D
    + "       Ruins of Undermountain  ·  A Forgotten Realms MUD  ·  port 4000\r\n"
    + _R + "\r\n"
)


class State(Enum):
    WELCOME    = auto()
    LOGIN_NAME = auto()
    LOGIN_PASS = auto()
    NEW_PASS   = auto()
    NEW_PASS2  = auto()
    CHAR_CLASS = auto()
    PLAYING    = auto()


class ClientSession:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, server: "MUDServer"):
        self.reader = reader
        self.writer = writer
        self.server = server
        self.player: Optional["Player"] = None
        self.state = State.WELCOME
        self._pending_name: Optional[str] = None
        self._pending_pass: Optional[str] = None

    # ─── I/O helpers ───────────────────────────────────────────────────────────

    async def write(self, text: str):
        try:
            self.writer.write(text.encode("utf-8", errors="replace"))
            await self.writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            raise

    async def writeln(self, text: str = ""):
        await self.write(text + "\r\n")

    async def _readline(self) -> str:
        data = await self.reader.readline()
        return data.decode("utf-8", errors="replace").strip("\r\n").strip()

    async def _read_password(self) -> str:
        # Suppress echo for password entry
        self.writer.write(IAC + WILL + ECHO)
        await self.writer.drain()
        password = await self._readline()
        self.writer.write(IAC + WONT + ECHO)
        await self.writer.drain()
        await self.writeln()
        return password

    # ─── Main loop ─────────────────────────────────────────────────────────────

    async def run(self):
        # Negotiate telnet options
        self.writer.write(IAC + WILL + SGA + IAC + DO + SGA)
        await self.writer.drain()

        await self.write(BANNER)
        await self._login_flow()

        if self.player:
            await self._game_loop()

    async def _login_flow(self):
        from db.database import Database
        from entities.player import Player

        await self.write("Name (or 'new' to create account): ")
        name = await self._readline()

        if name.lower() == "new" or not name:
            await self.write("Choose a name: ")
            name = await self._readline()

        if not name or len(name) < 2 or len(name) > 20:
            await self.writeln("Invalid name.")
            return

        name = name.capitalize()
        self._pending_name = name
        existing = Database.load_player(name)

        if existing:
            await self.write("Password: ")
            password = await self._read_password()
            if not Database.check_password(name, password):
                await self.writeln("Wrong password.")
                return
            self.player = existing
            self.server.register_player(name, self)
            await self.writeln(f"Welcome back, {name}!")
        else:
            await self.writeln(f"No account found for '{name}'. Creating new character.")
            await self.write("Choose a password: ")
            pw1 = await self._read_password()
            await self.write("Confirm password: ")
            pw2 = await self._read_password()
            if pw1 != pw2:
                await self.writeln("Passwords do not match.")
                return
            self._pending_pass = pw1

            char_class = await self._pick_class()
            if not char_class:
                return

            self.player = Player.create_new(name, char_class)
            Database.save_player(self.player, pw1)
            self.server.register_player(name, self)
            await self.writeln(f"\nWelcome to Undermountain, {name} the {char_class}!")
            await self.writeln("May Tymora smile upon you.\n")

    async def _pick_class(self) -> Optional[str]:
        classes = [
            "Barbarian", "Bard", "Cleric", "Druid", "Fighter",
            "Monk", "Paladin", "Ranger", "Rogue", "Sorcerer",
            "Warlock", "Wizard"
        ]
        await self.writeln("\nChoose your class:")
        for i, c in enumerate(classes, 1):
            await self.writeln(f"  {i:2}. {c}")
        await self.write("\nEnter number or name: ")
        choice = await self._readline()

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(classes):
                return classes[idx]
        else:
            match = [c for c in classes if c.lower() == choice.lower()]
            if match:
                return match[0]

        await self.writeln("Invalid choice.")
        return None

    # ─── Game loop ─────────────────────────────────────────────────────────────

    async def _game_loop(self):
        from commands import CommandProcessor

        # Place player in starting room if needed
        if not self.player.current_room_id:
            self.player.current_room_id = "yp_common_room"

        processor = CommandProcessor(self)

        # Show the room on entry
        await processor.cmd_look([])

        while True:
            try:
                await self.write("\n> ")
                line = await self._readline()
                if not line:
                    continue
                parts = line.strip().split()
                cmd = parts[0].lower()
                args = parts[1:]
                await processor.dispatch(cmd, args)
            except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
                break
            except SystemExit:
                await self.writeln("Farewell, adventurer.")
                break
