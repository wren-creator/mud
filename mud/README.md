# City of the Spider Queen — Ruins of Undermountain MUD

A text-based multiplayer dungeon (MUD) set in the Forgotten Realms, built with Python. NPC dialogue is powered locally by Ollama (llama3). Players explore the Yawning Portal Inn, descend into Undermountain, and press deeper toward the City of the Spider Queen.

## Features

- **12 D&D 5e classes** — Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard
- **10 levels** — XP-gated progression with HP gains, proficiency scaling, and spell slot upgrades on level-up
- **D&D 5e combat mechanics** — attack rolls, AC, hit dice, proficiency bonus, spell save DC, weapon damage by class
- **Spell slot system** — cantrips are unlimited; leveled spells (1st–3rd) consume slots per class table; `rest` restores all slots
- **AI-powered NPCs** — Durnan, Meloon Rawlins, Farideh Brasswind, and dungeon denizens respond dynamically via Ollama (llama3, running locally)
- **NPC respawning** — enemies return to their spawn room after 5 minutes (configurable per NPC with `respawn_time`)
- **Multi-zone world** — The Yawning Portal Inn → Undermountain Level 1 → City of the Spider Queen
- **Economy** — shops, buy/sell, loot tables with dice rolls
- **Persistent characters** — SQLite-backed save system with password auth
- **Multiplayer** — real-time room broadcasts, player-to-player visibility

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) running locally with the `llama3` model pulled (`ollama pull llama3`)

```
pip install -r requirements.txt
```

## Running the Server

```bash
python main.py
```

The server listens on port 4000.

## Connecting

Any telnet client works:

```bash
telnet localhost 4000
```

On macOS, `telnet` is no longer bundled by default. Alternatives:

```bash
brew install telnet
# or
nc localhost 4000
```

## Project Structure

```
mud/
├── main.py           — Entry point (starts the async TCP server)
├── server.py         — MUDServer: accepts connections, manages sessions
├── session.py        — Per-client state machine: login, char creation, game loop
├── commands.py       — All player commands (look, go, attack, cast, shop, ...)
├── entities/
│   ├── character.py  — Base Character class, Stats, D&D 5e calculations
│   ├── player.py     — Player subclass, persistence helpers
│   ├── npc.py        — NPC data class
│   └── item.py       — Item data class (weapon/armor/shield/consumable)
├── systems/
│   ├── combat.py     — Player attack and spell resolution
│   ├── npc_combat.py — NPC counter-attack and flee resolution
│   ├── npc_ai.py     — Ollama-powered NPC dialogue
│   └── dice_art.py   — ASCII dice display
├── world/
│   ├── loader.py     — Loads YAML zones and item registry
│   └── room.py       — Room data class
├── db/
│   └── database.py   — SQLite persistence (players, passwords)
├── web/
│   └── index.html    — Proof-of-concept web client for the room-state feed (see below)
└── data/
    ├── items.yaml
    └── zones/
        ├── yawning_portal.yaml
        ├── undermountain_l1.yaml
        └── city_of_spider_queen.yaml
```

## Room-State WebSocket Feed (3D client proof of concept)

The telnet game loop and rules are untouched. Alongside it, the server exposes
structured (JSON) room state over a WebSocket, the first step toward a
graphical (eventually 3D) client without rewriting any game logic. The web
client is now a standalone way to play, telnet isn't required.

- `Room.to_state_dict()` (`world/room.py`) builds a snapshot of a room, its
  players, NPCs, and items. The server pushes it over `ws://<host>:4001/ws`,
  once on login and again automatically any time something in that room
  changes, movement, combat, chat, item pickup, NPC respawn/roam.
- `mud/web/index.html` is a plain, dependency-free web page that connects to
  the feed and renders it live.
- **Login / character creation happens over the socket itself**, no telnet
  session required: `{"type": "check_name", "name": "..."}` tells the client
  whether that name is a new character (show a class picker), an existing
  one (show a password box), or already connected elsewhere (offer to
  attach instead). `{"type": "login", ...}` / `{"type": "create_account",
  ...}` follow. `{"type": "identify", "name": "..."}` still exists
  separately for attaching the web view to a session that's already logged
  in over telnet, useful for watching the two clients side by side, but it's
  no longer the only way in. A web-native login is backed by
  `WsOnlySession` (`server.py`), a stand-in that implements just enough of
  the `ClientSession` interface (`.player`, `.server`, async `.writeln()`)
  for the existing broadcast and command machinery to treat it like any
  other player, no parallel game loop needed.
- The client can also act: `{"type": "command", "line": "..."}` runs the exact
  same `CommandProcessor.dispatch()` a telnet player uses, so `go north`,
  `say ...`, `talk <npc> ...`, `attack <npc>`, `flee`, `buy`, `sell`, `loot`,
  and `cast <spell> at <target>` all behave identically whether they came
  from telnet or the browser, no separate rules to maintain per client. The
  web page wraps this behind exit buttons, a Say box, per-NPC Attack/Loot
  buttons, a Flee button, a Merchants panel (Buy per item), a "You" panel
  (gold, HP, inventory with Sell buttons), a Spells panel (slot counts, spell
  + target pickers, only shown for spellcasting classes), and a raw command
  box for anything else already implemented on the telnet side. Narrative
  output (attack rolls, "you say...", NPC replies) is relayed back over the
  socket as `{"type": "log", "text": "..."}` and rendered with the same ANSI
  colors telnet shows.
- Gold, inventory, HP, and spell slots are player-private, so they travel
  separately from the shared room broadcast: every pushed state includes a
  `self` key built from `Player.to_client_state()`, computed per recipient
  rather than shared verbatim like the rest of the payload. Merchant wares
  are public (anyone can `shop`) and live directly on the NPC's entry in the
  shared state. The spell catalog (names/levels/descriptions) is static, not
  per-player, so it's sent once as `{"type": "spell_catalog", ...}` right
  after login rather than riding on every state push.

To try it: `./start.sh`, then open `mud/web/index.html` in a browser and enter
a character name, no telnet needed. (Telnet still works exactly as before,
and `{"type": "identify", ...}` lets a browser tab attach to a telnet session
that's already logged in, if you want both views on the same character.)

## Character Creation

New players choose a name, password, and one of 12 classes. Stats are rolled using the standard D&D method: 4d6, drop the lowest, for each of the six ability scores. Starting room is the Common Room of the Yawning Portal Inn.

## Death

When a player's HP reaches 0, they wake on the floor of the Yawning Portal — alive, slightly poorer (25% of gold lost), with HP at half maximum, and all spell slots restored. Durnan is watching them with the expression of a man who has seen this before. Many times.
