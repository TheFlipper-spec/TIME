"""Procedural town map + interior layouts.

The town is a tile grid with roads, buildings (entered through doors) and
decorations. Coordinates are in tiles; the map is 100 x 62 tiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import tiles as T

WORLD_W, WORLD_H = 100, 62

# Buildings: id -> (x, y, w, h) facade rect, door tile (relative to rect)
BUILDINGS: dict[str, dict] = {
    "home":       {"rect": (7, 7, 7, 5),  "door": (3, 4)},
    "shop":       {"rect": (70, 7, 7, 5), "door": (3, 4)},
    "police":     {"rect": (8, 26, 8, 6), "door": (4, 5)},
    "bank":       {"rect": (68, 26, 7, 6), "door": (3, 5)},
    "emit_house": {"rect": (10, 46, 6, 5), "door": (2, 4)},
    "victim_house": {"rect": (44, 46, 8, 6), "door": (3, 5)},
    "warehouse":  {"rect": (78, 46, 8, 6), "door": (3, 5)},
}

BUILDING_COLORS: dict[str, tuple] = {
    "home":       ((150, 120, 90), (110, 60, 40), (96, 70, 46)),
    "shop":       ((160, 140, 110), (90, 70, 40), (120, 90, 50)),
    "police":     ((110, 120, 140), (60, 70, 90), (70, 80, 100)),
    "bank":       ((170, 165, 150), (120, 105, 80), (110, 90, 60)),
    "emit_house": ((130, 110, 90), (100, 70, 50), (90, 70, 48)),
    "victim_house": ((145, 120, 100), (110, 70, 45), (100, 78, 50)),
    "warehouse":  ((120, 110, 100), (80, 80, 90), (95, 85, 75)),
}

BUILDING_SIGNS: dict[str, str] = {
    "home": "home_sign", "shop": "shop_sign", "police": "police_sign",
    "bank": "bank_sign", "emit_house": "emit_sign",
    "victim_house": "victim_sign", "warehouse": "warehouse_sign",
}

# door tile -> interior map id (world door interaction)
DOORS: dict[tuple[int, int], str] = {}

# building id -> interior map id (names differ on purpose)
BUILDING_INTERIOR = {
    "home": "home", "shop": "shop", "police": "police", "bank": "bank",
    "emit_house": "emit", "victim_house": "victim", "warehouse": "warehouse",
}


@dataclass
class InteriorMap:
    id: str
    w: int
    h: int
    tiles: list = field(default_factory=list)       # 2D list of tile ids
    exit_tile: tuple[int, int] = (0, 0)             # door back to town
    enter_tile: tuple[int, int] = (0, 0)            # where player appears


def _ascii_interior(rows: list[str], floor: str = T.FLOOR) -> tuple[list, int, int]:
    h = len(rows)
    w = max(len(r) for r in rows)
    grid = []
    for r in rows:
        row = []
        for ch in r:
            if ch == "#":
                row.append(T.WALL)
            elif ch == ".":
                row.append(floor)
            elif ch == ",":
                row.append(T.CARPET)
            elif ch == "D":
                row.append(T.DOOR)
            elif ch == "=":
                row.append(T.WOOD)
            else:
                row.append(T.FLOOR)
        while len(row) < w:
            row.append(T.FLOOR)
        grid.append(row)
    return grid, w, h


INTERIORS: dict[str, InteriorMap] = {}


def _register(id_: str, rows: list[str], exit_tile, enter_tile, floor=T.FLOOR) -> None:
    grid, w, h = _ascii_interior(rows, floor)
    INTERIORS[id_] = InteriorMap(id_, w, h, grid, exit_tile, enter_tile)


def _blank_interior(w: int = 30, h: int = 18, door_col: int = 12,
                    carpets: list = None) -> list:
    """A walled rectangle with an exit door and optional carpet patches."""
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                row.append("#")
            else:
                row.append(".")
        rows.append("".join(row))
    r = list(rows[2])
    r[door_col] = "D"
    rows[2] = "".join(r)
    for (x0, y0, x1, y1) in (carpets or []):
        for y in range(y0, y1 + 1):
            rr = list(rows[y])
            for x in range(x0, x1 + 1):
                if rr[x] == ".":
                    rr[x] = ","
            rows[y] = "".join(rr)
    return rows


def build_interiors() -> None:
    _register("home", _blank_interior(carpets=[(2, 12, 10, 16), (20, 4, 28, 10)]),
              exit_tile=(12, 2), enter_tile=(6, 3))
    _register("shop", _blank_interior(door_col=4, carpets=[(20, 4, 28, 12)]),
              exit_tile=(4, 2), enter_tile=(6, 3))
    _register("bank", _blank_interior(door_col=4, carpets=[(20, 4, 28, 12)]),
              exit_tile=(4, 2), enter_tile=(6, 3))
    _register("police", _blank_interior(door_col=4, carpets=[(20, 4, 28, 12)]),
              exit_tile=(4, 2), enter_tile=(6, 3))
    _register("victim", _blank_interior(carpets=[(2, 10, 14, 16), (18, 4, 28, 16)]),
              exit_tile=(4, 2), enter_tile=(6, 3))
    _register("emit", _blank_interior(carpets=[(2, 10, 14, 16)]),
              exit_tile=(4, 2), enter_tile=(6, 3))
    _register("warehouse", _blank_interior(door_col=4),
              exit_tile=(4, 2), enter_tile=(6, 3), floor=T.WOOD)


# ------------------------------------------------------------------ town ---
def _rect(grid, x0, y0, x1, y1, tile: str) -> None:
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
                grid[y][x] = tile


def _h_road(grid, y: int, x0: int = 0, x1: int = None) -> None:
    x1 = len(grid[0]) - 1 if x1 is None else x1
    for x in range(x0, x1 + 1):
        grid[y][x] = T.ROAD_LANE if x % 8 == 4 else T.ROAD


def _v_road(grid, x: int, y0: int = 0, y1: int = None) -> None:
    y1 = len(grid) - 1 if y1 is None else y1
    for y in range(y0, y1 + 1):
        if grid[y][x] in (T.ROAD, T.ROAD_LANE):
            grid[y][x] = T.ROAD


def build_town() -> tuple[list, set]:
    """Returns (tile grid, solid set)."""
    grid = [[T.GRASS for _ in range(WORLD_W)] for _ in range(WORLD_H)]

    # ---- roads ------------------------------------------------------------
    for y in (20, 21, 41, 42, 58, 59):
        _h_road(grid, y)
    for x in (32, 33, 64, 65):
        _v_road(grid, x)
    # crosswalks at intersections
    for cx in (32, 33, 64, 65):
        for cy in (20, 21, 41, 42, 58, 59):
            if 0 <= cy < WORLD_H and 0 <= cx < WORLD_W:
                grid[cy][cx] = T.CROSSWALK
    # sidewalks around the main roads
    for y in (19, 22, 40, 43, 57, 60):
        for x in range(WORLD_W):
            if grid[y][x] == T.GRASS:
                grid[y][x] = T.SIDEWALK
    for x in (31, 34, 63, 66):
        for y in range(WORLD_H):
            if grid[y][x] == T.GRASS:
                grid[y][x] = T.SIDEWALK

    # ---- tree border --------------------------------------------------------
    for x in range(WORLD_W):
        for y in (0, 1, 2, WORLD_H - 3, WORLD_H - 2, WORLD_H - 1):
            if grid[y][x] == T.GRASS:
                grid[y][x] = T.TREE
    for y in range(WORLD_H):
        for x in (0, 1, WORLD_W - 2, WORLD_W - 1):
            if grid[y][x] == T.GRASS:
                grid[y][x] = T.TREE

    # ---- buildings -----------------------------------------------------------
    for bid, info in BUILDINGS.items():
        x, y, w, h = info["rect"]
        _rect(grid, x, y, x + w - 1, y + h - 1, T.FLOOR)   # interior placeholder
        dx, dy = info["door"]
        door_tile = (x + dx, y + dy)
        grid[y + dy][x + dx] = T.DOOR
        DOORS[door_tile] = BUILDING_INTERIOR[bid]

    # ---- decorations ----------------------------------------------------------
    # lamps along the roads
    for lx in (6, 14, 26, 38, 50, 60, 72, 84, 94):
        if 0 <= lx < WORLD_W:
            grid[18][lx] = T.LAMP if grid[18][lx] == T.SIDEWALK else grid[18][lx]
            grid[23][lx] = T.LAMP if grid[23][lx] == T.SIDEWALK else grid[23][lx]
    for lx in (4, 16, 28, 44, 56, 70, 82, 92):
        if 0 <= lx < WORLD_W:
            grid[39][lx] = T.LAMP if grid[39][lx] == T.SIDEWALK else grid[39][lx]
            grid[44][lx] = T.LAMP if grid[44][lx] == T.SIDEWALK else grid[44][lx]
    # park trees
    for (px, py) in [(36, 27), (38, 39), (56, 27), (58, 39), (40, 28), (54, 38),
                     (44, 27), (52, 39), (47, 27), (49, 39), (35, 33), (59, 33)]:
        grid[py][px] = T.TREE
    # park benches
    for (bx, by) in [(43, 32), (51, 32), (47, 36)]:
        grid[by][bx] = T.BENCH
    for (bx, by) in [(47, 31), (43, 35), (51, 35)]:
        grid[by][bx] = T.BUSH
    # flowers near houses
    for (fx, fy) in [(6, 12), (14, 12), (66, 8), (78, 8), (6, 31), (16, 31),
                     (76, 31), (66, 31), (8, 51), (16, 51), (38, 47), (53, 47)]:
        grid[fy][fx] = T.FLOWERS
    # bushes
    for (bx, by) in [(5, 11), (15, 11), (69, 12), (77, 12), (7, 32), (17, 32),
                     (67, 32), (76, 32), (9, 51), (17, 51), (39, 51), (52, 51),
                     (77, 51), (86, 51)]:
        grid[by][bx] = T.BUSH
    # trash cans
    grid[12][13] = T.TRASH
    grid[52][55] = T.TRASH
    grid[44][86] = T.TRASH
    # hydrant
    grid[44][70] = T.HYDRANT
    # mailbox at Mike's yard
    grid[12][12] = T.MAILBOX
    # bus stop near the victim's house
    grid[43][56] = T.BUSSTOP
    grid[43][57] = T.BUSSTOP
    # exit gate markers (east end of the mid road)
    grid[40][96] = T.FENCE
    grid[44][96] = T.FENCE
    grid[41][97] = T.TREE
    grid[42][97] = T.TREE

    # ---- solid set ------------------------------------------------------------
    solid = set()
    for y, row in enumerate(grid):
        for x, t in enumerate(row):
            if T.is_solid(t) or t == T.DOOR or t == T.BUSSTOP or t == T.MAILBOX:
                solid.add((x, y))
    return grid, solid


build_interiors()
