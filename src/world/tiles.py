"""Tile ids and solidity rules."""
from __future__ import annotations

# Ground / decorative tiles
GRASS = "grass"
GRASS_SNOW = "grass_snow"
ROAD = "road"
ROAD_LANE = "road_lane"
CROSSWALK = "crosswalk"
SIDEWALK = "sidewalk"
TREE = "tree"
FENCE = "fence"
LAMP = "lamp"
BENCH = "bench"
BUSH = "bush"
FLOWERS = "flowers"
TRASH = "trash"
BUSSTOP = "busstop"
MAILBOX = "mailbox"
HYDRANT = "hydrant"
CRATE = "crate"
DOOR = "door"
FLOOR = "floor"
WALL = "wall"
CARPET = "carpet"
WOOD = "wood"
TILESET = "tileset"

# Interior walls keep their own look
SOLID = {
    TREE, FENCE, LAMP, BENCH, BUSH, FLOWERS, TRASH, BUSSTOP, MAILBOX,
    HYDRANT, CRATE, WALL,
}


def is_solid(tile: str) -> bool:
    return tile in SOLID
