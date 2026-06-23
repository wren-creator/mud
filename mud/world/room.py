import copy
from dataclasses import dataclass, field
from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from entities.item import Item


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
