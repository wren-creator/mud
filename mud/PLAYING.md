# Play Reference — City of the Spider Queen MUD

Connect via telnet on port 4000. Create a character, pick a class, and find the well.

---

## Movement

| Command | Aliases | Action |
|---------|---------|--------|
| `north` | `n` | Move north |
| `south` | `s` | Move south |
| `east` | `e` | Move east |
| `west` | `w` | Move west |
| `up` | `u` | Move up |
| `down` | `d` | Move down |
| `go <dir>` | — | Explicit move |

---

## Looking Around

| Command | Aliases | Action |
|---------|---------|--------|
| `look` | `l` | Describe your current room |
| `examine <thing>` | `x <thing>` | Inspect an item or NPC in detail |

---

## Combat

| Command | Aliases | Action |
|---------|---------|--------|
| `attack <npc>` | `kill <npc>` | Attack a target (NPC counter-attacks each round) |
| `flee` | `run` | Attempt to escape combat (DEX check; failure = opportunity attack) |
| `cast <spell> at <target>` | — | Cast a spell (spellcasters only) |

**Cantrips (unlimited):** `firebolt`, `ray of frost`, `shocking grasp`, `sacred flame`, `eldritch blast`

**Leveled spells (consume a slot):**

| Spell | Level | Notes |
|-------|-------|-------|
| `magic missile` | 1st | Auto-hits, 3d4+1 force |
| `burning hands` | 1st | DEX save, 3d6 fire |
| `cure wounds` | 1st | Self-heal 1d8+mod |
| `chromatic orb` | 1st | Spell attack, 3d8 |
| `hex` | 1st | Warlock curse, 1d6 |
| `inflict wounds` | 1st | Necrotic, 3d10 |
| `thunderwave` | 2nd | CON save, 2d8 |
| `fireball` | 3rd | DEX save, 8d6 fire |
| `lightning bolt` | 3rd | DEX save, 8d6 lightning |

Spell slots refresh on `rest` or when you die and wake at the Yawning Portal.

---

## Inventory & Equipment

| Command | Aliases | Action |
|---------|---------|--------|
| `inv` | `inventory`, `i` | Show inventory and equipped gear |
| `get <item>` | `take`, `pick` | Pick up an item from the room |
| `drop <item>` | — | Drop an item from your inventory |
| `equip <item>` | `wear`, `wield` | Equip a weapon, armor, or shield |
| `remove <item>` | `unequip` | Unequip an item (returns to inventory) |
| `use <item>` | — | Use a consumable (potions, scrolls) |
| `loot <npc>` | — | Loot a dead enemy's corpse |

---

## Social & NPC Dialogue

| Command | Action |
|---------|--------|
| `say <message>` | Speak aloud (all players in room hear it) |
| `talk <npc> <message>` | Speak with an NPC — they respond via AI |
| `who` | List all online players and their locations |

---

## Shopping

| Command | Aliases | Action |
|---------|---------|--------|
| `shop` | `browse`, `wares` | Browse a merchant's inventory and prices |
| `buy <item>` | — | Purchase an item |
| `sell <item>` | — | Sell an inventory item (50% of item value) |

---

## Character Info

| Command | Aliases | Action |
|---------|---------|--------|
| `score` | `stats` | Full character sheet (HP, AC, ability scores, XP, spell slots) |
| `rest` | — | Short rest: recover 25% HP and restore all spell slots |

---

## System

| Command | Aliases | Action |
|---------|---------|--------|
| `save` | — | Save your character |
| `quit` | `exit` | Save and disconnect |
| `help` | — | In-game command reference |

---

## Classes at a Glance

| Class | Hit Die | Key Stat | Notes |
|-------|---------|----------|-------|
| Barbarian | d12 | STR | Highest HP, melee powerhouse |
| Fighter | d10 | STR/DEX | Versatile, strong early combat |
| Paladin | d10 | STR/WIS | Heavy armor, divine spells |
| Ranger | d10 | WIS | DEX melee or ranged, spells |
| Bard | d8 | CHA | Spells + social situations |
| Cleric | d8 | WIS | Healing spells, divine damage |
| Druid | d8 | WIS | Nature spells |
| Monk | d8 | DEX/WIS | Fast, unarmored |
| Rogue | d8 | DEX | Finesse weapons, high damage |
| Warlock | d8 | CHA | Eldritch blast, dark pacts |
| Sorcerer | d6 | CHA | Arcane spells |
| Wizard | d6 | INT | Widest spell selection |

---

## Death

If your HP hits 0, you wake on the floor of the Yawning Portal Inn. You lose 25% of your gold. Your HP is restored to half maximum. Durnan does not charge you for the ale.
