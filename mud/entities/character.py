import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from entities.item import Item


@dataclass
class Stats:
    strength:     int = 10
    dexterity:    int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom:       int = 10
    charisma:     int = 10

    def modifier(self, value: int) -> int:
        return (value - 10) // 2

    @classmethod
    def roll(cls) -> "Stats":
        def roll4d6drop1():
            rolls = [random.randint(1, 6) for _ in range(4)]
            return sum(sorted(rolls)[1:])
        return cls(
            strength=roll4d6drop1(),
            dexterity=roll4d6drop1(),
            constitution=roll4d6drop1(),
            intelligence=roll4d6drop1(),
            wisdom=roll4d6drop1(),
            charisma=roll4d6drop1(),
        )


HIT_DICE = {
    "barbarian": 12, "fighter": 10, "paladin": 10, "ranger": 10,
    "bard": 8, "cleric": 8, "druid": 8, "monk": 8, "rogue": 8, "warlock": 8,
    "sorcerer": 6, "wizard": 6,
}

SPELL_CLASSES = {"wizard", "sorcerer", "warlock", "cleric", "druid", "bard", "paladin", "ranger"}
FINESSE_CLASSES = {"rogue", "ranger", "monk"}


class Character:
    def __init__(self, name: str, char_class: str, stats: Stats, level: int = 1):
        self.name = name
        self.char_class = char_class.lower()
        self.level = level
        self.stats = stats
        self._hp: int = self._calc_max_hp()
        self.inventory: List["Item"] = []
        self.equipment: Dict[str, Optional["Item"]] = {
            "weapon": None,
            "offhand": None,
            "armor": None,
        }
        self.gold: int = 0
        self.experience: int = 0
        self.current_room_id: str = ""

    def _calc_max_hp(self) -> int:
        hd = HIT_DICE.get(self.char_class, 8)
        con_mod = self.stats.modifier(self.stats.constitution)
        base = hd + con_mod
        if self.level > 1:
            base += (self.level - 1) * (hd // 2 + 1 + con_mod)
        return max(1, base)

    @property
    def max_hp(self) -> int:
        return self._calc_max_hp()

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, value: int):
        self._hp = max(0, value)

    @property
    def ac(self) -> int:
        dex_mod = self.stats.modifier(self.stats.dexterity)
        armor = self.equipment.get("armor")
        shield = self.equipment.get("offhand")

        if armor:
            if armor.ac_type == "light":
                base = armor.ac_base + dex_mod
            elif armor.ac_type == "medium":
                base = armor.ac_base + min(2, dex_mod)
            else:  # heavy
                base = armor.ac_base
        else:
            # Unarmored defense
            if self.char_class == "barbarian":
                base = 10 + dex_mod + self.stats.modifier(self.stats.constitution)
            elif self.char_class == "monk":
                base = 10 + dex_mod + self.stats.modifier(self.stats.wisdom)
            else:
                base = 10 + dex_mod

        if shield and shield.item_type == "shield":
            base += shield.ac_bonus

        return base

    @property
    def proficiency_bonus(self) -> int:
        return 2 + (self.level - 1) // 4

    @property
    def attack_mod(self) -> int:
        weapon = self.equipment.get("weapon")
        weapon_bonus = weapon.attack_mod if weapon else 0

        if self.char_class == "wizard":
            stat_mod = self.stats.modifier(self.stats.intelligence)
        elif self.char_class in {"cleric", "druid", "ranger", "paladin"}:
            stat_mod = self.stats.modifier(self.stats.wisdom)
        elif self.char_class in {"warlock", "bard", "sorcerer"}:
            stat_mod = self.stats.modifier(self.stats.charisma)
        else:
            str_mod = self.stats.modifier(self.stats.strength)
            dex_mod = self.stats.modifier(self.stats.dexterity)
            stat_mod = max(str_mod, dex_mod) if self.char_class in FINESSE_CLASSES else str_mod

        return self.proficiency_bonus + stat_mod + weapon_bonus

    def weapon_damage(self) -> tuple:
        """Returns (n_dice, sides, modifier)."""
        weapon = self.equipment.get("weapon")
        str_mod = max(0, self.stats.modifier(self.stats.strength))
        if weapon:
            return weapon.damage_dice[0], weapon.damage_dice[1], weapon.damage_mod + str_mod
        return 1, 4, str_mod  # unarmed

    @property
    def spell_dc(self) -> int:
        if self.char_class == "wizard":
            mod = self.stats.modifier(self.stats.intelligence)
        elif self.char_class in {"cleric", "druid", "ranger", "paladin"}:
            mod = self.stats.modifier(self.stats.wisdom)
        else:
            mod = self.stats.modifier(self.stats.charisma)
        return 8 + self.proficiency_bonus + mod

    @property
    def is_alive(self) -> bool:
        return self._hp > 0

    @property
    def is_spellcaster(self) -> bool:
        return self.char_class in SPELL_CLASSES
