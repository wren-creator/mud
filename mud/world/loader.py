import copy
import os
import yaml
import logging
from typing import Dict, List, Optional

from world.room import Room
from entities.npc import NPC
from entities.item import Item

log = logging.getLogger(__name__)

# Global item template registry — populated on load
ITEM_REGISTRY: Dict[str, Item] = {}


class World:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.npcs:  Dict[str, NPC]  = {}
        self.zones: Dict[str, str]  = {}

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)

    def get_npc(self, npc_id: str) -> Optional[NPC]:
        return self.npcs.get(npc_id)


class WorldLoader:
    @staticmethod
    def load(zone_dir: str) -> World:
        global ITEM_REGISTRY
        world = World()

        # Load global items first
        items_path = os.path.join("data", "items.yaml")
        if os.path.exists(items_path):
            with open(items_path) as f:
                items_data = yaml.safe_load(f)
            for idata in items_data.get("items", []):
                item = Item.from_dict(idata)
                ITEM_REGISTRY[item.id] = item
            log.info(f"  Loaded {len(ITEM_REGISTRY)} item templates")

        for fname in sorted(os.listdir(zone_dir)):
            if not fname.endswith(".yaml"):
                continue
            fpath = os.path.join(zone_dir, fname)
            with open(fpath) as f:
                data = yaml.safe_load(f)

            zone_meta = data.get("zone", {})
            zone_id   = zone_meta.get("id", fname.replace(".yaml", ""))
            zone_name = zone_meta.get("name", zone_id)
            world.zones[zone_id] = zone_name
            log.info(f"  Loading zone: {zone_name}")

            # Additional item definitions inside zone file
            for idata in data.get("items", []):
                item = Item.from_dict(idata)
                ITEM_REGISTRY[item.id] = item

            for room_data in data.get("rooms", []):
                room = Room.from_dict(room_data, zone_id, ITEM_REGISTRY)
                world.rooms[room.id] = room

            for npc_data in data.get("npcs", []):
                npc = NPC.from_dict(npc_data)
                world.npcs[npc.id] = npc

            # Record which room each NPC spawns in (used for respawning and roaming)
            for room in world.rooms.values():
                for npc_id in room.npc_ids:
                    if npc_id in world.npcs and world.npcs[npc_id].spawn_room_id is None:
                        world.npcs[npc_id].spawn_room_id = room.id
                        world.npcs[npc_id].current_room_id = room.id

        return world
