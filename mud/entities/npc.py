from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class NPC:
    id: str
    name: str
    race: str
    role: str
    faction: str
    level: int
    hp: int
    max_hp: int
    ac: int
    hostile: bool
    xp_reward: int
    system_prompt: str
    description: str = ""
    # Combat stats
    attack_mod: int = 3
    damage_dice: List[int] = field(default_factory=lambda: [1, 6])  # [n, sides]
    damage_mod: int = 0
    behavior: str = "undead"       # undead | cowardly | berserker | guardian | tactical
    flee_threshold: float = 0.25
    loot_table: Dict[str, Any] = field(default_factory=dict)  # {gold:[n,sides], items:[{id,chance}]}
    looted: bool = False
    shop: Dict[str, int] = field(default_factory=dict)  # {item_id: buy_price}
    # rolling conversation context (resets on server restart)
    conversation_history: List[Dict] = field(default_factory=list)

    def is_alive(self) -> bool:
        return self.hp > 0

    @classmethod
    def from_dict(cls, data: dict) -> "NPC":
        level = data.get("level", 1)
        hp = data.get("hp", 8 * level)
        return cls(
            id=data["id"],
            name=data["name"],
            race=data.get("race", "unknown"),
            role=data.get("role", ""),
            faction=data.get("faction", "neutral"),
            level=level,
            hp=hp,
            max_hp=hp,
            ac=data.get("ac", 10),
            hostile=data.get("hostile", False),
            xp_reward=data.get("xp_reward", level * 50),
            system_prompt=data.get("system_prompt", f"You are {data['name']}, a {data.get('race','creature')} in a D&D world."),
            description=data.get("description", ""),
            attack_mod=data.get("attack_mod", level // 2 + 2),
            damage_dice=data.get("damage_dice", [1, 6]),
            damage_mod=data.get("damage_mod", 0),
            behavior=data.get("behavior", "undead"),
            flee_threshold=data.get("flee_threshold", 0.25),
            loot_table=data.get("loot_table", {}),
            shop=data.get("shop", {}),
        )
