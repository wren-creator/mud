import copy
from dataclasses import dataclass, field
from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from entities.item import Item
    from world.loader import World
    from session import ClientSession


@dataclass
class Room:
    id: str
    name: str
    description: str
    zone_id: str
    exits: Dict[str, str] = field(default_factory=dict)
    npc_ids: List[str] = field(default_factory=list)
    items: List["Item"] = field(default_factory=list)    # live item instances

    @classmethod
    def from_dict(cls, data: dict, zone_id: str, item_registry: dict) -> "Room":
        room = cls(
            id=data["id"],
            name=data["name"],
            description=data["description"].strip(),
            zone_id=zone_id,
            exits=data.get("exits", {}),
            npc_ids=list(data.get("npcs", [])),
        )
        for item_id in data.get("items", []):
            template = item_registry.get(item_id)
            if template:
                room.items.append(copy.deepcopy(template))
        return room

    def to_state_dict(self, world: "World", sessions: Dict[str, "ClientSession"], seq: int) -> dict:
        """Structured room snapshot for the WebSocket state feed (3D/web client POC).

        Assigns each entity a stable-for-this-snapshot `slot` index so a client
        can place them in the scene without any real position data existing yet.
        """
        npcs = []
        for i, npc_id in enumerate(self.npc_ids):
            npc = world.get_npc(npc_id)
            if not npc:
                continue
            npcs.append({
                "id": npc.id,
                "name": npc.name,
                "race": npc.race,
                "role": npc.role,
                "hostile": npc.hostile,
                "hp": npc.hp,
                "max_hp": npc.max_hp,
                "alive": npc.is_alive(),
                "slot": i,
            })

        players = []
        for i, session in enumerate(sessions.values()):
            p = session.player
            if not p or p.current_room_id != self.id:
                continue
            players.append({
                "name": p.name,
                "char_class": p.char_class,
                "level": p.level,
                "hp": p.hp,
                "max_hp": p.max_hp,
                "equipment": {
                    slot: item.name if item else None
                    for slot, item in p.equipment.items()
                },
                "slot": i,
            })

        items = [
            {"id": item.id, "name": item.name, "item_type": item.item_type, "slot": i}
            for i, item in enumerate(self.items)
        ]

        return {
            "type": "room_state",
            "seq": seq,
            "room": {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "zone_id": self.zone_id,
                "exits": self.exits,
            },
            "players": players,
            "npcs": npcs,
            "items": items,
        }
