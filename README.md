# City of the Spider Queen — Ruins of Undermountain MUD

A text-based multiplayer dungeon (MUD) set in the Forgotten Realms, built with Python. NPC dialogue is powered locally by Ollama (llama3). Players explore the Yawning Portal Inn, descend into Undermountain, and press deeper toward the City of the Spider Queen.

Playable two ways: any telnet client, or a themed web client with no telnet required. See [`mud/README.md`](mud/README.md) for full documentation, this file is a quick overview.

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
- **Web client** — a themed browser client (`mud/web/index.html`) backed by a structured WebSocket state feed, standalone login/character creation, no telnet needed. First step toward a full graphical/3D client; see `mud/README.md` for the architecture.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) running locally with the `llama3` model pulled (`ollama pull llama3`)

```
cd mud
pip install -r requirements.txt
```

## Running the Server

```bash
cd mud
./start.sh   # starts in the background, logs to mud.log
./stop.sh    # stops it cleanly
```

Or run it directly in the foreground with `python main.py` from `mud/`.

The telnet server listens on port 4000; the WebSocket state feed for the web client listens on port 4001.

## Connecting

**Telnet** (any client works):

```bash
telnet localhost 4000
# or, since macOS no longer bundles telnet:
brew install telnet
# or
nc localhost 4000
```

**Web client**: open `mud/web/index.html` in a browser with the server running, enter a character name, and follow the prompts (new name → pick a class; existing name → enter password).

## Project Structure

See [`mud/README.md`](mud/README.md) for the full directory layout, the WebSocket state feed's message protocol, and character creation/death mechanics.
