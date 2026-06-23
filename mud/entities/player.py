from entities.character import Character, Stats
from entities.item import Item


class Player(Character):
    def __init__(self, name: str, char_class: str, stats: Stats, level: int = 1):
        super().__init__(name, char_class, stats, level)

    @classmethod
    def create_new(cls, name: str, char_class: str) -> "Player":
        stats = Stats.roll()
        p = cls(name, char_class, stats)
        p.current_room_id = "yp_common_room"
        p.gold = 50
        p._hp = p.max_hp
        _apply_starting_gear(p)
        return p

    def to_dict(self) -> dict:
        s = self.stats
        return {
            "name": self.name,
            "char_class": self.char_class,
            "level": self.level,
            "hp": self._hp,
            "experience": self.experience,
            "gold": self.gold,
            "current_room_id": self.current_room_id,
            "inventory": [item.to_dict() for item in self.inventory],
            "equipment": {
                slot: item.to_dict() if item else None
                for slot, item in self.equipment.items()
            },
            "stats": {
                "strength": s.strength,
                "dexterity": s.dexterity,
                "constitution": s.constitution,
                "intelligence": s.intelligence,
                "wisdom": s.wisdom,
                "charisma": s.charisma,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        s = data["stats"]
        stats = Stats(
            strength=s["strength"], dexterity=s["dexterity"],
            constitution=s["constitution"], intelligence=s["intelligence"],
            wisdom=s["wisdom"], charisma=s["charisma"],
        )
        p = cls(data["name"], data["char_class"], stats, data.get("level", 1))
        p._hp = data.get("hp", p.max_hp)
        p.experience = data.get("experience", 0)
        p.gold = data.get("gold", 0)
        p.current_room_id = data.get("current_room_id", "yp_common_room")

        # Inventory — support both old string format and new dict format
        raw_inv = data.get("inventory", [])
        p.inventory = [
            Item.from_dict(i) if isinstance(i, dict) else None
            for i in raw_inv
        ]
        p.inventory = [i for i in p.inventory if i is not None]

        # Equipment
        raw_eq = data.get("equipment", {})
        for slot in ("weapon", "offhand", "armor"):
            item_data = raw_eq.get(slot)
            p.equipment[slot] = Item.from_dict(item_data) if item_data else None

        return p


def _apply_starting_gear(p: Player):
    """Give the player their class starting equipment, auto-equipped."""
    from world.loader import ITEM_REGISTRY

    def give(item_id: str, equip_slot: str = None):
        item = ITEM_REGISTRY.get(item_id)
        if item:
            import copy
            it = copy.deepcopy(item)
            if equip_slot and p.equipment.get(equip_slot) is None:
                p.equipment[equip_slot] = it
            else:
                p.inventory.append(it)

    c = p.char_class
    if c == "barbarian":
        give("handaxe", "weapon"); give("handaxe"); give("wooden_shield", "offhand")
    elif c == "bard":
        give("shortsword", "weapon"); give("leather_armor", "armor"); give("health_potion")
    elif c == "cleric":
        give("shortsword", "weapon"); give("chain_shirt", "armor"); give("wooden_shield", "offhand")
    elif c == "druid":
        give("shortsword", "weapon"); give("leather_armor", "armor")
    elif c == "fighter":
        give("longsword", "weapon"); give("chain_mail", "armor"); give("wooden_shield", "offhand")
    elif c == "monk":
        give("shortsword", "weapon"); give("leather_armor", "armor")
    elif c == "paladin":
        give("longsword", "weapon"); give("chain_mail", "armor"); give("wooden_shield", "offhand")
    elif c == "ranger":
        give("shortsword", "weapon"); give("shortsword"); give("scale_mail", "armor")
    elif c == "rogue":
        give("shortsword", "weapon"); give("dagger"); give("leather_armor", "armor")
    elif c == "sorcerer":
        give("dagger", "weapon"); give("health_potion")
    elif c == "warlock":
        give("dagger", "weapon"); give("leather_armor", "armor")
    elif c == "wizard":
        give("dagger", "weapon"); give("scroll_magic_missile"); give("health_potion")
