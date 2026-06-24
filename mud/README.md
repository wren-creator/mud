# City of the Spider Queen — Ruins of Undermountain MUD

A text-based multiplayer dungeon (MUD) set in the Forgotten Realms, built with Python and powered by Claude AI for NPC dialogue. Players explore the Yawning Portal Inn, descend into Undermountain, and press deeper toward the City of the Spider Queen.

## Features

- **12 D&D 5e classes** — Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard
- **D&D 5e combat mechanics** — attack rolls, AC, hit dice, proficiency bonus, spell save DC, weapon damage by class
- **AI-powered NPCs** — Durnan, Meloon Rawlins, Farideh Brasswind, and dungeon denizens respond dynamically via Claude
- **Multi-zone world** — The Yawning Portal Inn → Undermountain Level 1 → City of the Spider Queen
- **Economy** — shops, buy/sell, loot tables with dice rolls
- **Persistent characters** — SQLite-backed save system with password auth
- **Multiplayer** — real-time room broadcasts, player-to-player visibility

## Requirements

- Python 3.10+
- An Anthropic API key (for NPC dialogue)

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
│   ├── npc_ai.py     — Claude-powered NPC dialogue
│   └── dice_art.py   — ASCII dice display
├── world/
│   ├── loader.py     — Loads YAML zones and item registry
│   └── room.py       — Room data class
├── db/
│   └── database.py   — SQLite persistence (players, passwords)
└── data/
    ├── items.yaml
    └── zones/
        ├── yawning_portal.yaml
        ├── undermountain_l1.yaml
        └── city_of_spider_queen.yaml
```

## Character Creation

New players choose a name, password, and one of 12 classes. Stats are rolled using the standard D&D method: 4d6, drop the lowest, for each of the six ability scores. Starting room is the Common Room of the Yawning Portal Inn.

## Death

When a player's HP reaches 0, they wake on the floor of the Yawning Portal — alive, slightly poorer (25% of gold lost), and with Durnan watching them with the expression of a man who has seen this before. Many times.
