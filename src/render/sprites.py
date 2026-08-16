"""Procedural pixel-art sprites: tiles, characters, portraits, facades.

Everything is generated with rectangles/circles at startup and cached, so the
game ships with zero binary assets.
"""
from __future__ import annotations

import math
import random

import pygame

from ..config import TILE

# ------------------------------------------------------------- helpers -----
def _shade(c: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _px(surface: pygame.Surface, x: int, y: int, color) -> None:
    if 0 <= x < surface.get_width() and 0 <= y < surface.get_height():
        surface.set_at((x, y), color)


class SpriteBank:
    """Caches generated tile & object sprites."""

    def __init__(self) -> None:
        self._cache: dict = {}

    def get(self, name: str, make) -> pygame.Surface:
        if name not in self._cache:
            self._cache[name] = make()
        return self._cache[name]

    # ------------------------------------------------------------- tiles ---
    def tile(self, name: str) -> pygame.Surface:
        return self.get(f"tile:{name}", lambda: self._make_tile(name))

    def _make_tile(self, name: str) -> pygame.Surface:
        s = pygame.Surface((TILE, TILE))
        if name == "grass":
            s.fill((58, 84, 58))
            rng = random.Random(5)
            for _ in range(26):
                x, y = rng.randrange(TILE), rng.randrange(TILE)
                _px(s, x, y, (66, 94, 66) if rng.random() < 0.5 else (48, 72, 50))
        elif name == "grass_snow":
            s.fill((66, 92, 66))
            rng = random.Random(6)
            for _ in range(20):
                x, y = rng.randrange(TILE), rng.randrange(TILE)
                _px(s, x, y, (200, 208, 214))
        elif name == "road":
            s.fill((52, 54, 60))
            rng = random.Random(7)
            for _ in range(10):
                _px(s, rng.randrange(TILE), rng.randrange(TILE), (58, 60, 66))
        elif name == "road_lane":
            s.fill((52, 54, 60))
            pygame.draw.rect(s, (200, 200, 90), (0, TILE // 2 - 2, TILE, 4))
        elif name == "crosswalk":
            s.fill((52, 54, 60))
            for i in range(4):
                pygame.draw.rect(s, (228, 228, 228), (i * 8, 12, 6, 9))
        elif name == "sidewalk":
            s.fill((110, 112, 118))
            pygame.draw.line(s, (96, 98, 104), (0, 0), (0, TILE), 1)
            pygame.draw.line(s, (96, 98, 104), (TILE - 1, 0), (TILE - 1, TILE), 1)
            _px(s, 5, 5, (120, 122, 128))
            _px(s, 20, 22, (118, 120, 126))
        elif name == "fence":
            s.fill((0, 0, 0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.rect(s, (90, 74, 52), (6, 4, 20, 24), border_radius=3)
            pygame.draw.rect(s, (120, 100, 70), (6, 4, 20, 24), width=2, border_radius=3)
            for i in range(4):
                pygame.draw.rect(s, (150, 130, 96), (8 + i * 5, 0, 3, 8), border_radius=1)
        elif name == "tree":
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.rect(s, (92, 66, 44), (13, 20, 6, 12))
            pygame.draw.circle(s, (34, 62, 40), (16, 12), 9)
            pygame.draw.circle(s, (42, 72, 48), (11, 16), 6)
            pygame.draw.circle(s, (42, 72, 48), (21, 16), 6)
            pygame.draw.arc(s, (235, 240, 245), (8, 2, 17, 14), 0, math.pi, 2)
        elif name == "lamp":
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.rect(s, (60, 62, 70), (14, 10, 4, 22))
            pygame.draw.rect(s, (40, 42, 48), (10, 6, 12, 6), border_radius=2)
            pygame.draw.circle(s, (255, 240, 190), (16, 7), 3)
        elif name == "bench":
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.rect(s, (110, 82, 52), (2, 14, 28, 6), border_radius=2)
            pygame.draw.rect(s, (110, 82, 52), (2, 20, 28, 4), border_radius=2)
            pygame.draw.rect(s, (80, 58, 38), (4, 24, 4, 8))
            pygame.draw.rect(s, (80, 58, 38), (24, 24, 4, 8))
        elif name == "bush":
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.circle(s, (44, 76, 48), (10, 22), 8)
            pygame.draw.circle(s, (48, 82, 52), (22, 24), 7)
            pygame.draw.circle(s, (40, 68, 44), (16, 16), 7)
        elif name == "flowers":
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            s.fill((0, 0, 0, 0))
            for i, (x, c) in enumerate([(8, (220, 90, 110)), (16, (240, 220, 120)), (24, (160, 120, 220))]):
                pygame.draw.circle(s, c, (x, 22), 3)
                pygame.draw.circle(s, (255, 240, 160), (x, 22), 1)
        elif name == "trash":
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.rect(s, (70, 78, 92), (6, 12, 20, 18), border_radius=3)
            pygame.draw.rect(s, (52, 58, 70), (6, 12, 20, 5), border_radius=3)
            pygame.draw.rect(s, (60, 66, 80), (10, 6, 12, 6), border_radius=2)
            _px(s, 12, 18, (40, 44, 54))
            _px(s, 20, 24, (40, 44, 54))
        elif name == "busstop":
            s = pygame.Surface((TILE * 2, TILE), pygame.SRCALPHA)
            pygame.draw.rect(s, (70, 74, 84), (4, 4, 52, 24), border_radius=4)
            pygame.draw.rect(s, (100, 105, 118), (4, 4, 52, 24), width=2, border_radius=4)
            pygame.draw.rect(s, (46, 50, 60), (14, 8, 34, 16), border_radius=2)
            pygame.draw.rect(s, (60, 62, 70), (28, 26, 4, 6))
            pygame.draw.circle(s, (255, 214, 90), (12, 12), 4)
            s2 = pygame.Surface((TILE * 2, TILE))
            s2.fill((0, 0, 0))
            s2.blit(s, (0, 0))
            s2.set_colorkey((0, 0, 0))
            return s2
        elif name == "mailbox":
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.rect(s, (52, 58, 70), (12, 18, 8, 14))
            pygame.draw.rect(s, (120, 84, 56), (4, 6, 24, 14), border_radius=3)
            pygame.draw.rect(s, (160, 120, 84), (4, 6, 24, 14), width=2, border_radius=3)
            pygame.draw.circle(s, (200, 170, 120), (25, 10), 2)
        elif name == "hydrant":
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.rect(s, (170, 60, 54), (12, 16, 8, 12), border_radius=2)
            pygame.draw.rect(s, (190, 70, 62), (10, 12, 12, 6), border_radius=2)
            pygame.draw.circle(s, (190, 70, 62), (16, 10), 4)
        elif name == "crate":
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.rect(s, (126, 96, 58), (4, 10, 24, 22), border_radius=2)
            pygame.draw.rect(s, (150, 118, 74), (4, 10, 24, 22), width=2, border_radius=2)
            pygame.draw.line(s, (110, 82, 48), (4, 10), (28, 32), 2)
            pygame.draw.line(s, (110, 82, 48), (28, 10), (4, 32), 2)
        elif name == "floor":
            s.fill((150, 118, 84))
            pygame.draw.line(s, (132, 102, 70), (0, 16), (TILE, 16), 1)
            pygame.draw.line(s, (132, 102, 70), (16, 0), (16, TILE), 1)
            rng = random.Random(3)
            for _ in range(8):
                _px(s, rng.randrange(TILE), rng.randrange(TILE), (160, 128, 92))
        elif name == "wall":
            s.fill((74, 80, 104))
            pygame.draw.rect(s, (66, 72, 94), (0, 0, TILE, TILE))
            for i in range(4):
                pygame.draw.line(s, (84, 92, 118), (i * 8, 0), (i * 8, TILE), 1)
            pygame.draw.rect(s, (58, 63, 84), (0, TILE - 6, TILE, 6))
        elif name == "carpet":
            s.fill((96, 62, 70))
            pygame.draw.rect(s, (108, 72, 80), (2, 2, TILE - 4, TILE - 4), border_radius=4)
            pygame.draw.rect(s, (84, 52, 60), (2, 2, TILE - 4, TILE - 4), width=1, border_radius=4)
        elif name == "wood":
            s.fill((104, 82, 58))
            for i in range(2):
                pygame.draw.line(s, (88, 68, 46), (i * 16, 0), (i * 16, TILE), 1)
            rng = random.Random(9)
            for _ in range(6):
                _px(s, rng.randrange(TILE), rng.randrange(TILE), (116, 92, 66))
        elif name == "door":
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.rect(s, (70, 52, 36), (3, 2, TILE - 6, TILE - 2), border_radius=3)
            pygame.draw.rect(s, (96, 74, 52), (3, 2, TILE - 6, TILE - 2), width=2, border_radius=3)
            pygame.draw.circle(s, (235, 205, 140), (TILE - 10, TILE // 2), 3)
        else:
            s.fill((200, 60, 220))
        return s

    # ------------------------------------------------------- characters ----
    def character(self, key: tuple, walk_phase: float = 0.0,
                  dir_name: str = "down") -> pygame.Surface:
        """key: (coat, pants, skin, hair, hat, hair_style)."""
        return self.get(("char", key, dir_name), lambda: self._make_character(key, dir_name))

    def _make_character(self, key, dir_name: str) -> pygame.Surface:
        coat, pants, skin, hair, hat, style = key
        s = pygame.Surface((TILE, TILE + 8), pygame.SRCALPHA)
        cx = TILE // 2
        # shadow
        pygame.draw.ellipse(s, (0, 0, 0, 90), (6, TILE + 2, 20, 6))
        side = dir_name in ("left", "right")
        # legs
        leg = pygame.Rect(cx - 8, 26, 7, 10) if not side else pygame.Rect(cx - 7, 26, 6, 10)
        leg2 = leg.move(9, 0) if not side else leg.move(8, 0)
        pygame.draw.rect(s, pants, leg, border_radius=3)
        pygame.draw.rect(s, pants, leg2, border_radius=3)
        # body / coat
        body = pygame.Rect(cx - 9, 12, 18, 16)
        pygame.draw.rect(s, coat, body, border_radius=5)
        pygame.draw.rect(s, _shade(coat, 0.7), body, width=1, border_radius=5)
        if dir_name == "left":
            pygame.draw.rect(s, _shade(coat, 0.8), (cx - 11, 14, 4, 10), border_radius=2)
        elif dir_name == "right":
            pygame.draw.rect(s, _shade(coat, 0.8), (cx + 7, 14, 4, 10), border_radius=2)
        else:
            pygame.draw.rect(s, _shade(coat, 0.8), (cx - 11, 14, 4, 10), border_radius=2)
            pygame.draw.rect(s, _shade(coat, 0.8), (cx + 7, 14, 4, 10), border_radius=2)
        # head
        head = pygame.Rect(cx - 6, 2, 12, 12)
        pygame.draw.rect(s, skin, head, border_radius=4)
        if style == 0:      # short hair
            pygame.draw.rect(s, hair, (cx - 6, 2, 12, 5), border_radius=3)
        elif style == 1:    # bald
            pass
        elif style == 2:    # long hair
            pygame.draw.rect(s, hair, (cx - 6, 2, 12, 5), border_radius=3)
            pygame.draw.rect(s, hair, (cx - 7, 6, 3, 7), border_radius=2)
            pygame.draw.rect(s, hair, (cx + 4, 6, 3, 7), border_radius=2)
        elif style == 3:    # cap
            pygame.draw.rect(s, hair, (cx - 7, 2, 14, 5), border_radius=3)
            pygame.draw.rect(s, _shade(hair, 0.75), (cx - 7, 6, 14, 2))
        # eyes
        if dir_name == "left":
            _px(s, cx - 3, 8, (20, 20, 24))
        elif dir_name == "right":
            _px(s, cx + 3, 8, (20, 20, 24))
        else:
            _px(s, cx - 3, 8, (20, 20, 24))
            _px(s, cx + 3, 8, (20, 20, 24))
        # hat (fedora) for detective Mike
        if hat:
            pygame.draw.ellipse(s, (70, 52, 34), (cx - 9, 0, 18, 5))
            pygame.draw.rect(s, (70, 52, 34), (cx - 5, -2, 10, 5), border_radius=2)
        return s

    def cat(self) -> pygame.Surface:
        return self.get("cat", lambda: self._make_cat())

    def _make_cat(self) -> pygame.Surface:
        s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (222, 140, 66), (6, 14, 20, 14))
        pygame.draw.circle(s, (222, 140, 66), (9, 13), 5)
        pygame.draw.circle(s, (222, 140, 66), (23, 13), 5)
        pygame.draw.polygon(s, (222, 140, 66), [(8, 9), (10, 3), (13, 9)])
        pygame.draw.polygon(s, (222, 140, 66), [(19, 9), (22, 3), (24, 9)])
        pygame.draw.circle(s, (40, 60, 40), (7, 13), 1)
        pygame.draw.circle(s, (40, 60, 40), (21, 13), 1)
        pygame.draw.rect(s, (90, 60, 40), (18, 20, 8, 3), border_radius=1)
        return s

    # --------------------------------------------------------- portraits ---
    def portrait(self, seed: int) -> pygame.Surface:
        return self.get(("portrait", seed), lambda: self._make_portrait(seed))

    def _make_portrait(self, seed: int) -> pygame.Surface:
        rng = random.Random(seed)
        s = pygame.Surface((96, 96), pygame.SRCALPHA)
        skin = rng.choice([(232, 196, 160), (214, 172, 134), (244, 214, 178), (188, 140, 104)])
        hair = rng.choice([(58, 44, 34), (34, 30, 28), (92, 68, 46), (168, 148, 118), (28, 28, 32)])
        coat = rng.choice([(70, 84, 110), (96, 74, 54), (60, 92, 84), (88, 60, 66), (52, 54, 62)])
        style = rng.randrange(4)
        glasses = rng.random() < 0.3
        beard = rng.random() < 0.3
        age_lines = rng.random() < 0.4
        # background
        pygame.draw.rect(s, (22, 28, 44), (0, 0, 96, 96), border_radius=14)
        pygame.draw.rect(s, (60, 74, 108), (0, 0, 96, 96), width=2, border_radius=14)
        # shoulders
        pygame.draw.ellipse(s, coat, (10, 62, 76, 40))
        pygame.draw.ellipse(s, _shade(coat, 0.75), (10, 62, 76, 40), width=2)
        # neck
        pygame.draw.rect(s, skin, (42, 48, 12, 16), border_radius=3)
        # face
        pygame.draw.ellipse(s, skin, (24, 10, 48, 56))
        # ears
        pygame.draw.circle(s, skin, (26, 18), 6)
        pygame.draw.circle(s, skin, (70, 18), 6)
        # hair
        if style == 0:
            pygame.draw.ellipse(s, hair, (22, 6, 52, 26))
        elif style == 1:
            pygame.draw.ellipse(s, hair, (22, 8, 52, 22))
            pygame.draw.rect(s, hair, (22, 20, 10, 40), border_radius=4)
            pygame.draw.rect(s, hair, (64, 20, 10, 40), border_radius=4)
        elif style == 2:
            pygame.draw.ellipse(s, hair, (24, 4, 48, 18))
        elif style == 3:
            pygame.draw.ellipse(s, (150, 130, 110), (20, 6, 56, 16))
            pygame.draw.rect(s, (150, 130, 110), (20, 14, 56, 4))
        # brows
        pygame.draw.rect(s, _shade(hair, 0.8), (34, 28, 10, 3), border_radius=1)
        pygame.draw.rect(s, _shade(hair, 0.8), (52, 28, 10, 3), border_radius=1)
        # eyes
        pygame.draw.circle(s, (250, 250, 250), (39, 36), 5)
        pygame.draw.circle(s, (250, 250, 250), (57, 36), 5)
        pygame.draw.circle(s, (44, 60, 86), (40, 36), 3)
        pygame.draw.circle(s, (44, 60, 86), (58, 36), 3)
        pygame.draw.circle(s, (10, 12, 16), (41, 36), 1)
        pygame.draw.circle(s, (10, 12, 16), (59, 36), 1)
        if glasses:
            pygame.draw.rect(s, (40, 44, 54), (31, 30, 16, 13), width=2, border_radius=4)
            pygame.draw.rect(s, (40, 44, 54), (49, 30, 16, 13), width=2, border_radius=4)
            pygame.draw.line(s, (40, 44, 54), (47, 34), (49, 34), 2)
        # nose
        pygame.draw.circle(s, _shade(skin, 0.9), (48, 44), 2)
        # mouth
        pygame.draw.rect(s, (150, 90, 90), (42, 52, 12, 3), border_radius=2)
        if beard:
            pygame.draw.ellipse(s, _shade(hair, 0.9), (32, 44, 32, 22))
            pygame.draw.ellipse(s, skin, (34, 42, 28, 12))
        if age_lines:
            pygame.draw.line(s, _shade(skin, 0.85), (34, 48), (42, 50), 1)
            pygame.draw.line(s, _shade(skin, 0.85), (54, 50), (62, 48), 1)
        return s

    # ---------------------------------------------------------- facades ----
    def facade(self, key: tuple, sign: str = "", sign_color=(212, 175, 55)) -> pygame.Surface:
        """key: (w_tiles, h_tiles, wall, roof, door_color, kind)."""
        return self.get(("facade", key, sign, sign_color),
                        lambda: self._make_facade(key, sign, sign_color))

    def _make_facade(self, key, sign: str, sign_color) -> pygame.Surface:
        wt, ht, wall, roof, door_c, kind = key
        w, h = wt * TILE, ht * TILE
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        # roof
        pygame.draw.rect(s, roof, (0, 0, w, 14))
        pygame.draw.rect(s, _shade(roof, 0.7), (0, 0, w, 14), width=2)
        # wall
        pygame.draw.rect(s, wall, (0, 10, w, h - 10), border_radius=4)
        pygame.draw.rect(s, _shade(wall, 0.7), (0, 10, w, h - 10), width=2, border_radius=4)
        rng = random.Random(abs(hash(key)) % 999)
        # windows
        for wy in range(2, ht - 1):
            for wx in range(1, wt - 1):
                if (wx, wy) == (wt // 2, ht - 1):
                    continue
                if rng.random() < 0.45:
                    x, y = wx * TILE + 5, wy * TILE + 12
                    lit = rng.random() < 0.3
                    c = (255, 222, 140) if lit else (140, 156, 190)
                    pygame.draw.rect(s, c, (x, y, TILE - 10, 14), border_radius=2)
                    pygame.draw.rect(s, _shade(c, 0.7), (x, y, TILE - 10, 14), width=1, border_radius=2)
        # door
        dx = wt // 2 * TILE + 4
        dy = h - TILE + 2
        pygame.draw.rect(s, door_c, (dx, dy, TILE - 8, TILE - 4), border_radius=3)
        pygame.draw.rect(s, _shade(door_c, 0.7), (dx, dy, TILE - 8, TILE - 4), width=2, border_radius=3)
        pygame.draw.circle(s, (240, 220, 150), (dx + TILE - 14, dy + 16), 2)
        # sign board
        if sign:
            from .fonts import get as _get
            f = _get("sans_bold", 14)
            tw = f.size(sign)[0] + 16
            bx = (w - tw) // 2
            pygame.draw.rect(s, (24, 28, 44), (bx, 24, tw, 22), border_radius=4)
            pygame.draw.rect(s, sign_color, (bx, 24, tw, 22), width=2, border_radius=4)
            img = f.render(sign, True, (240, 240, 245))
            s.blit(img, (bx + 8, 28))
        # snow cap
        pygame.draw.rect(s, (238, 242, 248), (0, 0, w, 6), border_radius=2)
        return s
