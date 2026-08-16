"""World model & rendering: town grid, interiors, facades, props, NPCs."""
from __future__ import annotations

import math
from datetime import datetime

import pygame

from ..config import DESIGN_H, DESIGN_W, TILE
from ..render.fx import Glow
from ..render.sprites import SpriteBank
from . import tiles as T
from .mapgen import BUILDINGS, BUILDING_COLORS, DOORS, INTERIORS, WORLD_H, WORLD_W, build_town
from .npcs import NPC_DATA, npc_on_map
from .props import props_for

SIGN_KEYS = {
    "home": "sign.home", "shop": "sign.shop", "police": "sign.police",
    "bank": "sign.bank", "emit_house": "sign.emit", "victim_house": "sign.victim",
    "warehouse": "sign.warehouse",
}


class World:
    def __init__(self) -> None:
        self.town_tiles, self.town_solid = build_town()
        self.interiors = INTERIORS
        self.doors = DOORS

    # ------------------------------------------------------------- queries --
    def tile(self, map_id: str, tx: int, ty: int) -> str:
        if map_id == "town":
            if 0 <= tx < WORLD_W and 0 <= ty < WORLD_H:
                return self.town_tiles[ty][tx]
            return T.TREE
        interior = self.interiors.get(map_id)
        if interior and 0 <= tx < interior.w and 0 <= ty < interior.h:
            return interior.tiles[ty][tx]
        return T.WALL

    def is_solid(self, map_id: str, tx: int, ty: int) -> bool:
        t = self.tile(map_id, tx, ty)
        if t in (T.DOOR, T.WALL, T.TREE, T.FENCE, T.LAMP, T.BENCH, T.BUSH,
                 T.FLOWERS, T.TRASH, T.BUSSTOP, T.MAILBOX, T.HYDRANT, T.CRATE):
            return True
        return False

    def solid_at_px(self, map_id: str, x: float, y: float, radius: float = 8.0) -> bool:
        """AABB collision against solid tiles (point with a small radius)."""
        x0, y0 = x - radius, y - radius
        x1, y1 = x + radius, y + radius
        for ty in range(int(y0) // TILE, int(y1) // TILE + 1):
            for tx in range(int(x0) // TILE, int(x1) // TILE + 1):
                if self.is_solid(map_id, tx, ty):
                    tile_rect = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
                    if tile_rect.colliderect(pygame.Rect(x0, y0, x1 - x0, y1 - y0)):
                        return True
        return False

    def map_size(self, map_id: str) -> tuple[int, int]:
        if map_id == "town":
            return WORLD_W * TILE, WORLD_H * TILE
        interior = self.interiors.get(map_id)
        if interior:
            return interior.w * TILE, interior.h * TILE
        return WORLD_W * TILE, WORLD_H * TILE

    def interior_of(self, door_tile: tuple[int, int]) -> str | None:
        return self.doors.get(door_tile)

    # ------------------------------------------------------------ drawing --
    def draw(self, surface: pygame.Surface, camera, map_id: str, state,
             lang: str, bank: SpriteBank, entity_drawer=None, tr=None) -> None:
        from ..game.time import world_datetime
        cam_x, cam_y = camera.offset()
        world_now = world_datetime(state.day, state.minutes, state.offset_min)
        if map_id == "town":
            self._draw_town(surface, cam_x, cam_y, state, lang, bank, world_now,
                            entity_drawer, tr)
        else:
            self._draw_interior(surface, cam_x, cam_y, map_id, state, bank,
                                world_now, entity_drawer, lang)

    def _draw_town(self, surface, cam_x, cam_y, state, lang, bank,
                   world_now: datetime, entity_drawer=None, tr=None) -> None:
        x0 = max(0, cam_x // TILE - 1)
        y0 = max(0, cam_y // TILE - 1)
        x1 = min(WORLD_W - 1, (cam_x + DESIGN_W) // TILE + 1)
        y1 = min(WORLD_H - 1, (cam_y + DESIGN_H) // TILE + 1)

        now = world_now
        hour = now.hour + now.minute / 60.0

        # ground
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                t = self.town_tiles[ty][tx]
                if t in (T.DOOR, T.FLOOR):
                    continue
                sprite = bank.tile(t)
                surface.blit(sprite, (tx * TILE - cam_x, ty * TILE - cam_y))

        # building facades
        drawn_rects = []
        for bid, info in BUILDINGS.items():
            bx, by, bw, bh = info["rect"]
            px, py = bx * TILE - cam_x, by * TILE - cam_y
            if px + bw * TILE < 0 or px > DESIGN_W or py + bh * TILE < 0 or py > DESIGN_H:
                continue
            wall, roof, door_c = BUILDING_COLORS[bid]
            sign_text = tr.t(SIGN_KEYS[bid]) if (bid in SIGN_KEYS and tr) else ""
            facade = bank.facade((bw, bh, wall, roof, door_c, bid), sign_text)
            surface.blit(facade, (px, py))
            drawn_rects.append((bx, by, bw, bh, px, py))

        # exit roadblock sign (drawn near the blocked road)
        self._draw_exit_block(surface, cam_x, cam_y, bank, state)

        # props
        for prop in props_for("town"):
            if not prop.visible(state, world_now):
                continue
            px, py = prop.x * TILE - cam_x, prop.y * TILE - cam_y
            self._draw_prop(surface, prop, px, py, bank)

        # npcs
        for nid in npc_on_map(state, "town"):
            pos = NPC_DATA[nid].pos_at(hour, "town")
            if pos is None:
                continue
            nx, ny = pos[0] * TILE, pos[1] * TILE
            sx, sy = int(nx - cam_x), int(ny - cam_y)
            if -TILE < sx < DESIGN_W + TILE and -TILE * 2 < sy < DESIGN_H + TILE:
                self._draw_npc(surface, nid, sx, sy, bank, state, lang, pos)

        # player & carried entities (drawn above NPCs, below lighting)
        if entity_drawer is not None:
            entity_drawer(surface, cam_x, cam_y)

        # night tint & lamps
        self._apply_lighting(surface, state, now, drawn_rects, cam_x, cam_y)

    def _draw_exit_block(self, surface, cam_x, cam_y, bank, state) -> None:
        """A police sign at the roadblock (drawn as a small prop)."""
        tx, ty = 93, 40
        px, py = tx * TILE - cam_x, ty * TILE - cam_y
        if -TILE < px < DESIGN_W + TILE and -TILE < py < DESIGN_H + TILE:
            s = pygame.Surface((TILE * 2, TILE), pygame.SRCALPHA)
            pygame.draw.rect(s, (150, 60, 50), (4, 4, TILE * 2 - 8, TILE - 8), border_radius=4)
            pygame.draw.rect(s, (200, 90, 70), (4, 4, TILE * 2 - 8, TILE - 8), width=2, border_radius=4)
            from ..render.text import draw_text
            draw_text(s, "STOP", (TILE, 10), size=16, kind="sans_bold",
                      color=(255, 255, 255), align="center", shadow=False)
            surface.blit(s, (px, py))

    def _draw_interior(self, surface, cam_x, cam_y, map_id, state, bank,
                       world_now: datetime, entity_drawer=None, lang: str = "ru") -> None:
        interior = self.interiors[map_id]
        # dark backdrop so the margins around the room look deliberate
        surface.fill((13, 11, 14))
        pygame.draw.rect(surface, (8, 7, 9), (0, 0, DESIGN_W, DESIGN_H), width=60)
        x0 = max(0, cam_x // TILE - 1)
        y0 = max(0, cam_y // TILE - 1)
        x1 = min(interior.w - 1, (cam_x + DESIGN_W) // TILE + 1)
        y1 = min(interior.h - 1, (cam_y + DESIGN_H) // TILE + 1)
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                t = interior.tiles[ty][tx]
                sprite = bank.tile(t)
                surface.blit(sprite, (tx * TILE - cam_x, ty * TILE - cam_y))
        # props
        for prop in props_for(map_id):
            if not prop.visible(state, world_now):
                continue
            px, py = prop.x * TILE - cam_x, prop.y * TILE - cam_y
            self._draw_prop(surface, prop, px, py, bank)
        # npcs
        for nid in npc_on_map(state, map_id):
            pos = NPC_DATA[nid].pos_at(state.minutes, map_id)
            if pos is None:
                continue
            sx, sy = int(pos[0] * TILE - cam_x), int(pos[1] * TILE - cam_y)
            if -TILE < sx < DESIGN_W + TILE and -TILE * 2 < sy < DESIGN_H + TILE:
                self._draw_npc(surface, nid, sx, sy, bank, state, lang, pos)

        if entity_drawer is not None:
            entity_drawer(surface, cam_x, cam_y)

    def _draw_npc(self, surface, nid, sx, sy, bank, state, lang, pos) -> None:
        key = APPEARANCE.get(nid)
        if key is None:
            key = ((120, 120, 130), (60, 60, 70), (214, 172, 134), (60, 44, 34), 0, 0)
        sprite = bank.character(key, dir_name="down")
        surface.blit(sprite, (sx - TILE // 2, sy - TILE // 2 - 6))
        # name label for witnesses (when close enough to the player)
        if nid != "cat":
            px, py = state.pos
            dx = abs(px // TILE - pos[0]) + abs(py // TILE - pos[1])
            if dx < 6:
                from ..render.text import draw_text
                name = display_name(nid, lang)
                draw_text(surface, name, (sx, sy - TILE - 14), size=15,
                          color=(240, 240, 245), align="center", outline=True, shadow=False)

    def _draw_prop(self, surface, prop, px, py, bank) -> None:
        # small glowing marker for inspectable clues
        if prop.marker:
            phase = pygame.time.get_ticks() / 400
            bob = int(3 * math.sin(phase)) if prop.kind == "inspect" else 0
            cx, cy = px + TILE // 2, py - 8 + bob
            glow = Glow.make((255, 214, 90), 14, 0.55)
            surface.blit(glow, (cx - 14, cy - 14))
            pygame.draw.circle(surface, (255, 226, 130), (cx, cy), 4)
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 2)
        # door markers
        if prop.kind in ("enter", "exit", "victim_door", "emit_door", "warehouse_door",
                         "bed", "wardrobe", "computer", "fridge", "counter_shop",
                         "counter_bank", "mailbox"):
            cx, cy = px + TILE // 2, py + TILE // 2
            pygame.draw.circle(surface, (90, 140, 220), (cx, cy), 3)
            pygame.draw.circle(surface, (200, 220, 255), (cx, cy), 1)

    def _apply_lighting(self, surface, state, now, building_rects,
                        cam_x, cam_y) -> None:
        hour = now.hour + now.minute / 60.0
        if 6 <= hour < 8:
            # gentle warm morning
            overlay = pygame.Surface((DESIGN_W, DESIGN_H))
            overlay.fill((255, 226, 190))
            overlay.set_alpha(16)
            surface.blit(overlay, (0, 0))
            return
        if 8 <= hour < 17:
            return
        if 17 <= hour < 19:
            overlay = pygame.Surface((DESIGN_W, DESIGN_H))
            overlay.fill((255, 190, 120))
            overlay.set_alpha(34)
            surface.blit(overlay, (0, 0))
            return
        # ---- night: multiply the scene dark, then add warm light ----
        night = min(1.0, max(0.0, (hour - 19) / 2.0)) if hour >= 19 else \
            min(1.0, max(0.0, (7.0 - hour) / 2.0))
        if hour < 19:  # before 19:00 but after 17 handled above -> pre-dawn
            night = min(1.0, max(0.0, (7.0 - hour) / 2.0))
        dark = 0.42 + 0.20 * night
        overlay = pygame.Surface((DESIGN_W, DESIGN_H))
        overlay.fill((int(52 * dark / 0.62), int(58 * dark / 0.62), int(110 * dark / 0.62)))
        surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        # lamp glows (additive)
        if night > 0.25:
            glow = Glow.make((255, 200, 120), 80, 0.65)
            for lx in (6, 14, 26, 38, 50, 60, 72, 84, 94):
                for ly in (18, 23):
                    px, py = lx * TILE - cam_x, ly * TILE - cam_y
                    if -80 < px < DESIGN_W + 80 and -80 < py < DESIGN_H + 80:
                        glow.set_alpha(int(200 * night))
                        surface.blit(glow, (px + TILE // 2 - 80, py + TILE // 2 - 80),
                                     special_flags=pygame.BLEND_RGBA_ADD)
        # window lights
        if night > 0.25:
            win = Glow.make((255, 226, 150), 46, 0.5)
            win.set_alpha(int(190 * night))
            for (bx, by, bw, bh, px, py) in building_rects:
                for wy in (1, 3):
                    for wx in (1, bw - 2):
                        surface.blit(win, (px + wx * TILE + 8 - 46, py + wy * TILE + 14 - 46),
                                     special_flags=pygame.BLEND_RGBA_ADD)


# re-export for convenience
from .npcs import APPEARANCE, display_name  # noqa: E402  (isort:skip)
