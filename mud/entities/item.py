from dataclasses import dataclass, field
from typing import List


@dataclass
class Item:
    id: str
    name: str
    item_type: str       # weapon | armor | shield | consumable | misc
    description: str
    value: int = 0
    weight: float = 0.0
    # Weapon
    damage_dice: List[int] = field(default_factory=lambda: [1, 4])
    damage_mod: int = 0
    attack_mod: int = 0
    two_handed: bool = False
    # Armor / shield
    ac_base: int = 10
    ac_type: str = ""    # light | medium | heavy | shield
    ac_bonus: int = 0
    # Consumable
    effect: str = ""     # heal | damage
    effect_dice: List[int] = field(default_factory=list)
    effect_mod: int = 0

    def slot(self) -> str:
        if self.item_type == "weapon":
            return "weapon"
        if self.item_type in ("armor",):
            return "armor"
        if self.item_type == "shield":
            return "offhand"
        return ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        return cls(
            id=data["id"],
            name=data["name"],
            item_type=data.get("item_type", "misc"),
            description=data.get("description", ""),
            value=data.get("value", 0),
            weight=float(data.get("weight", 0)),
            damage_dice=data.get("damage_dice", [1, 4]),
            damage_mod=data.get("damage_mod", 0),
            attack_mod=data.get("attack_mod", 0),
            two_handed=data.get("two_handed", False),
            ac_base=data.get("ac_base", 10),
            ac_type=data.get("ac_type", ""),
            ac_bonus=data.get("ac_bonus", 0),
            effect=data.get("effect", ""),
            effect_dice=data.get("effect_dice", []),
            effect_mod=data.get("effect_mod", 0),
        )
