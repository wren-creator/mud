import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from session import ClientSession

log = logging.getLogger(__name__)

DIRECTIONS = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "u": "up", "d": "down",
    "north": "north", "south": "south", "east": "east", "west": "west",
    "up": "up", "down": "down",
}

DIR_ARROWS = {
    "north": "N", "south": "S", "east": "E", "west": "W", "up": "U", "down": "D"
}


class CommandProcessor:
    def __init__(self, session: "ClientSession"):
        self.session = session
        self.server = session.server
        self.world = session.server.world

    @property
    def player(self):
        return self.session.player

    async def writeln(self, text: str = ""):
        await self.session.writeln(text)

    # ─── Dispatcher ────────────────────────────────────────────────────────────

    async def dispatch(self, cmd: str, args: List[str]):
        handlers = {
            "look": self.cmd_look, "l": self.cmd_look,
            "go":   self.cmd_go,
            "north": self._dir("north"), "n": self._dir("north"),
            "south": self._dir("south"), "s": self._dir("south"),
            "east":  self._dir("east"),  "e": self._dir("east"),
            "west":  self._dir("west"),  "w": self._dir("west"),
            "up":    self._dir("up"),    "u": self._dir("up"),
            "down":  self._dir("down"),  "d": self._dir("down"),
            "say":   self.cmd_say,
            "talk":  self.cmd_talk,
            "attack": self.cmd_attack,   "kill": self.cmd_attack,
            "flee":  self.cmd_flee,      "run": self.cmd_flee,
            "cast":   self.cmd_cast,
            "get":    self.cmd_get,      "take": self.cmd_get,      "pick": self.cmd_get,
            "drop":   self.cmd_drop,
            "equip":  self.cmd_equip,    "wear": self.cmd_equip,    "wield": self.cmd_equip,
            "remove": self.cmd_unequip,  "unequip": self.cmd_unequip,
            "loot":   self.cmd_loot,
            "use":    self.cmd_use,
            "examine": self.cmd_examine, "x": self.cmd_examine,
            "inv":    self.cmd_inv,      "inventory": self.cmd_inv, "i": self.cmd_inv,
            "score":  self.cmd_score,    "stats": self.cmd_score,
            "shop":   self.cmd_shop,     "browse": self.cmd_shop,  "wares": self.cmd_shop,
            "buy":    self.cmd_buy,
            "sell":   self.cmd_sell,
            "who":    self.cmd_who,
            "help":   self.cmd_help,   "?": self.cmd_help,  "h": self.cmd_help,
            "quit":   self.cmd_quit,     "exit": self.cmd_quit,
            "save":   self.cmd_save,
            "rest":   self.cmd_rest,
        }
        handler = handlers.get(cmd)
        if handler:
            await handler(args)
        else:
            await self.writeln(f"Unknown command '{cmd}'. Type 'help' for a list.")

    def _dir(self, direction: str):
        async def _handler(args):
            await self.cmd_go([direction])
        return _handler

    # ─── Commands ──────────────────────────────────────────────────────────────

    async def cmd_look(self, args: List[str]):
        room = self.world.get_room(self.player.current_room_id)
        if not room:
            await self.writeln("[ERROR] You are nowhere. Tell an admin.")
            return

        await self.writeln(f"\n\033[1;33m{room.name}\033[0m")
        await self.writeln("-" * len(room.name))
        await self.writeln(room.description)

        # Items on the ground
        if room.items:
            for item in room.items:
                await self.writeln(f"  A \033[1;37m{item.name}\033[0m lies here.")

        # Exits
        exits = [DIR_ARROWS[d] for d in room.exits if d in DIR_ARROWS]
        await self.writeln(f"\n\033[1;36mExits:\033[0m {' '.join(exits) if exits else 'none'}")

        # NPCs in room
        npcs = [self.world.get_npc(nid) for nid in room.npc_ids if self.world.get_npc(nid)]
        if npcs:
            for npc in npcs:
                if npc.is_alive():
                    await self.writeln(f"\033[1;32m{npc.name}\033[0m is here.")
                else:
                    await self.writeln(f"\033[2mThe corpse of {npc.name} lies here.\033[0m")

        # Other players in room
        others = [
            s.player.name for name, s in self.server.sessions.items()
            if s.player and s.player.name != self.player.name
            and s.player.current_room_id == self.player.current_room_id
        ]
        for other in others:
            await self.writeln(f"\033[1;35m{other}\033[0m is here.")

    async def cmd_go(self, args: List[str]):
        if not args:
            await self.writeln("Go where?")
            return

        direction = DIRECTIONS.get(args[0].lower())
        if not direction:
            await self.writeln(f"'{args[0]}' is not a valid direction.")
            return

        room = self.world.get_room(self.player.current_room_id)
        if not room:
            return

        dest_id = room.exits.get(direction)
        if not dest_id:
            await self.writeln("You can't go that way.")
            return

        dest = self.world.get_room(dest_id)
        if not dest:
            await self.writeln("That passage leads nowhere (broken room link).")
            return

        # Announce departure to current room
        await self.server.broadcast_to_room(
            self.player.current_room_id,
            f"{self.player.name} leaves {direction}.",
            exclude=self.player.name
        )

        self.player.current_room_id = dest_id

        # Announce arrival to new room
        await self.server.broadcast_to_room(
            dest_id,
            f"{self.player.name} arrives.",
            exclude=self.player.name
        )

        await self.cmd_look([])
        await self._check_aggro()

        from db.database import Database
        Database.save_player(self.player)

    async def cmd_say(self, args: List[str]):
        if not args:
            await self.writeln("Say what?")
            return
        message = " ".join(args)
        await self.writeln(f"You say: \"{message}\"")
        await self.server.broadcast_to_room(
            self.player.current_room_id,
            f'{self.player.name} says: "{message}"',
            exclude=self.player.name
        )

    async def cmd_talk(self, args: List[str]):
        if not args:
            await self.writeln("Talk to whom?")
            return

        target = args[0].lower()
        message = " ".join(args[1:]) if len(args) > 1 else "Hello."

        room = self.world.get_room(self.player.current_room_id)
        npc = next(
            (self.world.get_npc(nid) for nid in room.npc_ids
             if self.world.get_npc(nid)
             and self.world.get_npc(nid).name.lower().startswith(target)
             and self.world.get_npc(nid).is_alive()),
            None
        )
        if not npc:
            await self.writeln(f"There is no '{target}' here.")
            return

        await self.writeln(f"You speak to {npc.name}: \"{message}\"")
        await self.writeln(f"\033[1;32m{npc.name}\033[0m thinks...")

        from systems.npc_ai import get_npc_response
        response = await get_npc_response(npc, self.player, message)

        await self.writeln(f"\033[1;32m{npc.name}\033[0m says: \"{response}\"")

        await self.server.broadcast_to_room(
            self.player.current_room_id,
            f'{self.player.name} speaks with {npc.name}. {npc.name} replies: "{response}"',
            exclude=self.player.name
        )

    async def cmd_attack(self, args: List[str]):
        if not args:
            await self.writeln("Attack whom?")
            return

        target = args[0].lower()
        room = self.world.get_room(self.player.current_room_id)
        npc = next(
            (self.world.get_npc(nid) for nid in room.npc_ids
             if self.world.get_npc(nid) and self.world.get_npc(nid).name.lower().startswith(target)),
            None
        )
        if not npc:
            await self.writeln(f"There is no '{target}' here to attack.")
            return
        if not npc.hostile and npc.hp > 0:
            await self.writeln(f"{npc.name} is not hostile. They eye you warily.")
            return
        if not npc.is_alive():
            await self.writeln(f"{npc.name} is already dead.")
            return

        from systems.combat import resolve_attack
        result = resolve_attack(self.player, npc)
        await self.writeln(result.narrative)

        await self.server.broadcast_to_room(
            self.player.current_room_id,
            f"{self.player.name} attacks {npc.name}!",
            exclude=self.player.name
        )

        # NPC death
        if not npc.is_alive():
            import time as _time
            npc.dead_at = _time.monotonic()
            self.player.experience += npc.xp_reward
            await self.writeln(f"\n  {npc.name} is dead. You gain {npc.xp_reward} XP.")
            await self.writeln(f"  (You can 'loot {npc.name.split()[0].lower()}' to search the corpse.)")
            await self._check_levelup()
            return

        # NPC counter-attack
        from systems.npc_combat import npc_take_turn
        npc_result = npc_take_turn(npc, self.player)
        await self.writeln(npc_result.narrative)

        if npc_result.npc_fled and npc.id in room.npc_ids:
            room.npc_ids.remove(npc.id)
            return

        if not self.player.is_alive:
            await self._handle_player_death()

    async def cmd_flee(self, args: List[str]):
        room = self.world.get_room(self.player.current_room_id)
        hostiles = [
            self.world.get_npc(nid) for nid in room.npc_ids
            if self.world.get_npc(nid) and self.world.get_npc(nid).hostile and self.world.get_npc(nid).is_alive()
        ]
        if not hostiles:
            await self.writeln("There's nothing to flee from.")
            return

        exits = list(room.exits.items())
        if not exits:
            await self.writeln("There's nowhere to run!")
            return

        import random as _random
        npc = _random.choice(hostiles)

        from systems.npc_combat import resolve_flee
        success, narrative = resolve_flee(self.player, npc)
        await self.writeln(narrative)

        if success:
            direction, dest_id = _random.choice(exits)
            dest = self.world.get_room(dest_id)
            if dest:
                await self.server.broadcast_to_room(
                    self.player.current_room_id,
                    f"{self.player.name} flees {direction}!",
                    exclude=self.player.name
                )
                self.player.current_room_id = dest_id
                await self.cmd_look([])
        elif not self.player.is_alive:
            await self._handle_player_death()

    async def _check_aggro(self):
        """Hostile alive NPCs in the current room get a free attack on room entry."""
        from systems.npc_combat import npc_take_turn
        room = self.world.get_room(self.player.current_room_id)
        if not room:
            return
        hostiles = [
            self.world.get_npc(nid) for nid in list(room.npc_ids)
            if self.world.get_npc(nid)
            and self.world.get_npc(nid).hostile
            and self.world.get_npc(nid).is_alive()
        ]
        for npc in hostiles:
            if not self.player.is_alive:
                break
            result = npc_take_turn(npc, self.player, is_aggro=True)
            await self.writeln(result.narrative)
            if result.npc_fled and npc.id in room.npc_ids:
                room.npc_ids.remove(npc.id)
        if not self.player.is_alive:
            await self._handle_player_death()

    async def _handle_player_death(self):
        from db.database import Database
        gold_lost = self.player.gold // 4
        self.player.gold -= gold_lost
        self.player._hp = max(1, self.player.max_hp // 2)
        self.player.restore_spell_slots()
        self.player.current_room_id = "yp_common_room"

        await self.writeln(f"""
\033[1;31m
  ╔══════════════════════════════════════╗
  ║           YOU HAVE FALLEN            ║
  ╚══════════════════════════════════════╝
\033[0m
  You collapse into darkness...

  ...and wake on the floor of the Yawning Portal Inn,
  lighter by {gold_lost} gold pieces. Durnan is watching
  you with the expression of a man who has seen this
  before. Many times.

  He slides you an ale. It costs 4 copper.
  You're alive. Probably lucky.
""")
        Database.save_player(self.player)
        await self.cmd_look([])

    async def _check_levelup(self):
        import random
        from entities.character import HIT_DICE
        _XP = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000]
        current_level = self.player.level
        new_level = current_level
        for lvl, xp_needed in enumerate(_XP, 1):
            if self.player.experience >= xp_needed:
                new_level = lvl

        if new_level <= current_level:
            return

        old_prof = self.player.proficiency_bonus
        hd = HIT_DICE.get(self.player.char_class, 8)
        con_mod = self.player.stats.modifier(self.player.stats.constitution)
        hp_gain = sum(
            max(1, random.randint(1, hd) + con_mod)
            for _ in range(new_level - current_level)
        )
        self.player.level = new_level
        self.player._hp = min(self.player.max_hp, self.player._hp + hp_gain)
        self.player.restore_spell_slots()
        new_prof = self.player.proficiency_bonus

        Y = "\033[1;33m"
        R = "\033[0m"
        W = 40

        def _bl(s: str) -> str:
            return f"  ║ {s.ljust(W - 1)}║"

        lines = [
            f"\n{Y}  ╔{'=' * W}╗",
            _bl("  ★  ★   L E V E L   U P !   ★  ★"),
            f"  ╠{'=' * W}╣",
            _bl(f"  {self.player.char_class.capitalize()} reaches level {new_level}!"),
            _bl(f"  Hit points  +{hp_gain}"),
        ]
        if new_prof > old_prof:
            lines.append(_bl(f"  Proficiency  +{old_prof} → +{new_prof}"))
        lines.append(f"  ╚{'=' * W}╝{R}")
        await self.writeln("\n".join(lines))

    async def cmd_cast(self, args: List[str]):
        if len(args) < 2:
            await self.writeln("Usage: cast <spell> at <target>")
            return
        from systems.combat import resolve_spell, SPELL_LEVELS
        if "at" in args:
            at_idx = args.index("at")
            spell_name = " ".join(args[:at_idx]).lower()
            target_name = " ".join(args[at_idx + 1:]).lower()
        else:
            spell_name = " ".join(args[:-1]).lower()
            target_name = args[-1].lower()

        spell_level = SPELL_LEVELS.get(spell_name, 1)
        if spell_level > 0:
            if not self.player.use_spell_slot(spell_level):
                ordinals = ["1st", "2nd", "3rd", "4th", "5th"]
                needed = ordinals[spell_level - 1]
                await self.writeln(
                    f"You have no {needed}-level spell slots remaining. "
                    f"Type 'rest' to recover them."
                )
                return

        room = self.world.get_room(self.player.current_room_id)
        target = next(
            (self.world.get_npc(nid) for nid in room.npc_ids
             if self.world.get_npc(nid) and self.world.get_npc(nid).name.lower().startswith(target_name)),
            None
        )
        if not target:
            await self.writeln(f"No target '{target_name}' here.")
            return

        result = resolve_spell(self.player, spell_name, target)
        await self.writeln(result.narrative)

        if target.hp <= 0:
            import time as _time
            target.dead_at = _time.monotonic()
            self.player.experience += target.xp_reward
            await self.writeln(f"\n  {target.name} is dead. You gain {target.xp_reward} XP.")
            await self.writeln(f"  (You can 'loot {target.name.split()[0].lower()}' to search the corpse.)")
            await self._check_levelup()

    # ── Item commands ───────────────────────────────────────────────────────

    def _find_item_in_room(self, name: str):
        room = self.world.get_room(self.player.current_room_id)
        name = name.lower()
        return next((i for i in room.items if name in i.name.lower()), None), room

    def _find_item_in_inv(self, name: str):
        name = name.lower()
        return next((i for i in self.player.inventory if name in i.name.lower()), None)

    async def cmd_get(self, args: List[str]):
        if not args:
            await self.writeln("Get what?")
            return
        target = " ".join(args).lower()
        item, room = self._find_item_in_room(target)
        if not item:
            await self.writeln(f"You don't see '{target}' here.")
            return
        room.items.remove(item)
        self.player.inventory.append(item)
        await self.writeln(f"You pick up the {item.name}.")
        await self.server.broadcast_to_room(
            self.player.current_room_id,
            f"{self.player.name} picks up {item.name}.",
            exclude=self.player.name
        )

    async def cmd_drop(self, args: List[str]):
        if not args:
            await self.writeln("Drop what?")
            return
        target = " ".join(args).lower()
        item = self._find_item_in_inv(target)
        if not item:
            # Check equipment slots
            for slot, equipped in self.player.equipment.items():
                if equipped and target in equipped.name.lower():
                    self.player.equipment[slot] = None
                    item = equipped
                    break
        if not item:
            await self.writeln(f"You aren't carrying '{target}'.")
            return
        if item in self.player.inventory:
            self.player.inventory.remove(item)
        room = self.world.get_room(self.player.current_room_id)
        room.items.append(item)
        await self.writeln(f"You drop the {item.name}.")

    async def cmd_equip(self, args: List[str]):
        if not args:
            await self.writeln("Equip what?")
            return
        target = " ".join(args).lower()
        item = self._find_item_in_inv(target)
        if not item:
            await self.writeln(f"You aren't carrying '{target}'.")
            return
        slot = item.slot()
        if not slot:
            await self.writeln(f"You can't equip the {item.name}.")
            return
        # Unequip current item in that slot back to inventory
        current = self.player.equipment.get(slot)
        if current:
            self.player.inventory.append(current)
            await self.writeln(f"You remove the {current.name}.")
        self.player.inventory.remove(item)
        self.player.equipment[slot] = item
        await self.writeln(f"You equip the {item.name}. [AC: {self.player.ac}]")

    async def cmd_unequip(self, args: List[str]):
        if not args:
            await self.writeln("Remove what?")
            return
        target = " ".join(args).lower()
        for slot, equipped in self.player.equipment.items():
            if equipped and target in equipped.name.lower():
                self.player.equipment[slot] = None
                self.player.inventory.append(equipped)
                await self.writeln(f"You remove the {equipped.name}. [AC: {self.player.ac}]")
                return
        await self.writeln(f"You aren't wearing or wielding '{target}'.")

    async def cmd_loot(self, args: List[str]):
        import random as _random
        import copy as _copy
        if not args:
            await self.writeln("Loot whom?")
            return
        target = " ".join(args).lower()
        room = self.world.get_room(self.player.current_room_id)
        npc = next(
            (self.world.get_npc(nid) for nid in room.npc_ids
             if self.world.get_npc(nid) and self.world.get_npc(nid).name.lower().startswith(target)),
            None
        )
        if not npc:
            await self.writeln(f"No '{target}' here to loot.")
            return
        if npc.is_alive():
            await self.writeln(f"{npc.name} is still alive. Kill them first.")
            return
        if npc.looted:
            await self.writeln(f"{npc.name}'s corpse has already been looted.")
            return

        npc.looted = True
        loot = npc.loot_table
        gained = []

        # Gold
        gold_entry = loot.get("gold")
        if gold_entry:
            n, sides = gold_entry
            gold_rolled = sum(_random.randint(1, sides) for _ in range(n))
            self.player.gold += gold_rolled
            gained.append(f"{gold_rolled} gold")

        # Items
        from world.loader import ITEM_REGISTRY
        for entry in loot.get("items", []):
            if _random.random() < entry.get("chance", 1.0):
                template = ITEM_REGISTRY.get(entry["id"])
                if template:
                    item = _copy.deepcopy(template)
                    self.player.inventory.append(item)
                    gained.append(item.name)

        if gained:
            await self.writeln(f"You loot {npc.name}: {', '.join(gained)}.")
        else:
            await self.writeln(f"{npc.name} had nothing of value.")

        # Remove corpse
        if npc.id in room.npc_ids:
            room.npc_ids.remove(npc.id)

    async def cmd_use(self, args: List[str]):
        import random as _random
        if not args:
            await self.writeln("Use what?")
            return
        target = " ".join(args).lower()
        item = self._find_item_in_inv(target)
        if not item:
            await self.writeln(f"You aren't carrying '{target}'.")
            return
        if item.item_type != "consumable":
            await self.writeln(f"You can't use the {item.name} that way. Try 'equip'.")
            return

        self.player.inventory.remove(item)

        if item.effect == "heal":
            n, sides = item.effect_dice[0], item.effect_dice[1]
            healed = sum(_random.randint(1, sides) for _ in range(n)) + item.effect_mod
            healed = min(healed, self.player.max_hp - self.player.hp)
            self.player.hp += healed
            await self.writeln(
                f"You use the {item.name} and recover {healed} HP. "
                f"[{self.player.hp}/{self.player.max_hp}]"
            )
        elif item.effect == "damage":
            await self.writeln(
                f"You read the {item.name}. It needs a target: 'cast magic missile at <target>'."
            )
            self.player.inventory.append(item)  # give it back
        else:
            await self.writeln(f"You use the {item.name}, but nothing obvious happens.")

    async def cmd_examine(self, args: List[str]):
        if not args:
            await self.writeln("Examine what?")
            return
        target = " ".join(args).lower()
        # Check inventory
        item = self._find_item_in_inv(target)
        if not item:
            # Check equipped
            for slot, equipped in self.player.equipment.items():
                if equipped and target in equipped.name.lower():
                    item = equipped
                    break
        if not item:
            # Check room
            item, _ = self._find_item_in_room(target)
        if item:
            lines = [f"\n\033[1;33m{item.name}\033[0m  [{item.item_type}]"]
            lines.append(item.description.strip())
            if item.item_type == "weapon":
                lines.append(f"  Damage: {item.damage_dice[0]}d{item.damage_dice[1]}{'+' if item.damage_mod>=0 else ''}{item.damage_mod or ''}  Attack: {item.attack_mod:+d}")
            if item.item_type in ("armor", "shield"):
                lines.append(f"  AC: {item.ac_base or ''}{'+'+str(item.ac_bonus) if item.ac_bonus else ''}  Type: {item.ac_type}")
            if item.item_type == "consumable" and item.effect == "heal":
                lines.append(f"  Heals: {item.effect_dice[0]}d{item.effect_dice[1]}+{item.effect_mod}")
            lines.append(f"  Value: {item.value} gp  Weight: {item.weight} lbs")
            await self.writeln("\n".join(lines))
            return
        # Check NPCs
        room = self.world.get_room(self.player.current_room_id)
        npc = next(
            (self.world.get_npc(nid) for nid in room.npc_ids
             if self.world.get_npc(nid) and target in self.world.get_npc(nid).name.lower()),
            None
        )
        if npc:
            await self.writeln(f"\n\033[1;32m{npc.name}\033[0m\n{npc.description}")
            return
        await self.writeln(f"You don't see '{target}' here.")

    async def cmd_inv(self, args: List[str]):
        await self.writeln("\n\033[1;33mEquipped:\033[0m")
        slots = {"weapon": "Weapon", "offhand": "Offhand", "armor": "Armor"}
        for slot, label in slots.items():
            item = self.player.equipment.get(slot)
            name = item.name if item else "\033[2m(none)\033[0m"
            await self.writeln(f"  {label:8}: {name}")

        await self.writeln(f"\n\033[1;33mCarrying:\033[0m")
        if not self.player.inventory:
            await self.writeln("  (nothing)")
        else:
            for item in self.player.inventory:
                await self.writeln(f"  {item.name}")
        await self.writeln(f"\nGold: {self.player.gold} gp")

    async def cmd_score(self, args: List[str]):
        p = self.player
        s = p.stats
        _XP = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000]
        if p.level < len(_XP):
            xp_line = f"XP: {p.experience} / {_XP[p.level]}  (next level)"
        else:
            xp_line = f"XP: {p.experience}  (max level)"
        slot_line = ""
        if p.is_spellcaster:
            ordinals = ["1st", "2nd", "3rd", "4th", "5th"]
            parts = [
                f"{ordinals[i]}: {cur}/{mx}"
                for i, (cur, mx) in enumerate(zip(p.spell_slots, p.max_spell_slots))
                if mx > 0
            ]
            slot_line = f"\nSpell slots: {', '.join(parts) if parts else 'none'}"

        await self.writeln(f"""
\033[1;33m{p.name}\033[0m  —  {p.char_class.capitalize()} Level {p.level}
HP: {p.hp}/{p.max_hp}   AC: {p.ac}   Prof: +{p.proficiency_bonus}
{xp_line}{slot_line}

STR {s.strength:2} ({s.modifier(s.strength):+d})   DEX {s.dexterity:2} ({s.modifier(s.dexterity):+d})   CON {s.constitution:2} ({s.modifier(s.constitution):+d})
INT {s.intelligence:2} ({s.modifier(s.intelligence):+d})   WIS {s.wisdom:2} ({s.modifier(s.wisdom):+d})   CHA {s.charisma:2} ({s.modifier(s.charisma):+d})
""")

    async def cmd_who(self, args: List[str]):
        await self.writeln("\n\033[1;33mAdventurers Online:\033[0m")
        for name, session in self.server.sessions.items():
            if session.player:
                p = session.player
                room = self.world.get_room(p.current_room_id)
                loc = room.name if room else "???"
                await self.writeln(f"  {p.name} ({p.char_class} {p.level}) — {loc}")

    async def cmd_help(self, args: List[str]):
        await self.writeln("""
\033[1;33mCommands:\033[0m  (also: ? or h)\033[0m
  look / l            — Describe your current location
  go <dir> / n s e w u d — Move in a direction
  say <message>       — Speak aloud in the room
  talk <npc> <msg>    — Speak with an NPC (AI-powered)
  attack / kill <npc> — Attack an enemy (NPC counter-attacks each round)
  flee / run          — Attempt to escape combat (DEX check; failure = opportunity attack)
  cast <spell> at <target> — Cast a spell
  get / take <item>   — Pick up an item from the room
  drop <item>         — Drop an item from your inventory
  equip / wear <item> — Equip a weapon, armor, or shield
  remove <item>       — Unequip an item
  loot <npc>          — Loot a dead enemy's corpse
  use <item>          — Use a consumable (potion, scroll)
  examine / x <thing> — Examine an item or NPC in detail
  inv / inventory / i — Show your inventory and equipped gear
  shop / browse       — Browse a merchant's wares
  buy <item>          — Purchase an item from a merchant
  sell <item>         — Sell an item from your inventory (50% value)
  score / stats       — Show your character sheet (includes spell slots)
  who                 — List online players
  rest                — Recover HP and restore all spell slots
  save                — Save your character
  quit                — Save and disconnect
""")

    async def cmd_rest(self, args: List[str]):
        self.player.restore_spell_slots()
        heal = self.player.max_hp // 4
        self.player.hp = min(self.player.max_hp, self.player.hp + heal)
        msg = f"You rest. HP +{heal} [{self.player.hp}/{self.player.max_hp}]."
        if self.player.is_spellcaster:
            msg += " Spell slots restored."
        await self.writeln(msg)
        from db.database import Database
        Database.save_player(self.player)

    async def cmd_save(self, args: List[str]):
        from db.database import Database
        Database.save_player(self.player)
        await self.writeln("Character saved.")

    async def cmd_quit(self, args: List[str]):
        from db.database import Database
        Database.save_player(self.player)
        raise SystemExit

    # ── Economy ─────────────────────────────────────────────────────────────────

    def _find_shopkeeper(self):
        room = self.world.get_room(self.player.current_room_id)
        for nid in room.npc_ids:
            npc = self.world.get_npc(nid)
            if npc and npc.shop and not npc.hostile:
                return npc
        return None

    async def cmd_shop(self, args: List[str]):
        from world.loader import ITEM_REGISTRY
        merchant = self._find_shopkeeper()
        if not merchant:
            await self.writeln("There's no merchant here.")
            return

        Y = "\033[1;33m"
        D = "\033[2m"
        R = "\033[0m"
        W = 48

        lines = [f"\n{Y}{merchant.name}'s Wares:{R}"]
        lines.append(f"  {'─' * W}")
        lines.append(f"  {'Item':<34}{'Price':>12}")
        lines.append(f"  {'─' * W}")

        for item_id, price in merchant.shop.items():
            template = ITEM_REGISTRY.get(item_id)
            if template:
                lines.append(f"  {template.name:<34}{price:>9} gp")

        buy_pct = int(merchant.buy_rate * 100)
        lines.append(f"  {'─' * W}")
        lines.append(f"  {D}Merchant buys your items at {buy_pct}% of their value.{R}")
        lines.append(f"  You have {Y}{self.player.gold} gp{R}.")
        await self.writeln("\n".join(lines))

    async def cmd_buy(self, args: List[str]):
        if not args:
            await self.writeln("Buy what? (type 'shop' to browse available items)")
            return
        merchant = self._find_shopkeeper()
        if not merchant:
            await self.writeln("There's no merchant here.")
            return

        import copy
        from world.loader import ITEM_REGISTRY
        query = " ".join(args).lower()

        match = None
        for item_id, price in merchant.shop.items():
            template = ITEM_REGISTRY.get(item_id)
            if template and query in template.name.lower():
                match = (item_id, price, template)
                break

        if not match:
            await self.writeln(f"{merchant.name} doesn't carry '{query}'.")
            return

        item_id, price, template = match
        if self.player.gold < price:
            await self.writeln(
                f"You can't afford that. (Need {price} gp, have {self.player.gold} gp)"
            )
            return

        self.player.gold -= price
        self.player.inventory.append(copy.deepcopy(template))
        await self.writeln(
            f"You buy the {template.name} for {price} gp.  "
            f"({self.player.gold} gp remaining)"
        )

    async def cmd_sell(self, args: List[str]):
        if not args:
            await self.writeln("Sell what?")
            return
        merchant = self._find_shopkeeper()
        if not merchant:
            await self.writeln("There's no merchant here.")
            return

        query = " ".join(args).lower()
        item = self._find_item_in_inv(query)
        if not item:
            await self.writeln(f"You don't have '{query}' in your inventory.")
            return

        sell_price = max(1, int(item.value * merchant.buy_rate))
        self.player.inventory.remove(item)
        self.player.gold += sell_price
        await self.writeln(
            f"You sell the {item.name} for {sell_price} gp.  "
            f"({self.player.gold} gp total)"
        )
