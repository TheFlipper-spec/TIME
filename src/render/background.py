"""Menu backgrounds: animated gradient + gears + vignette."""
from __future__ import annotations

import math

import pygame

from ..config import DESIGN_H, DESIGN_W


def draw_menu_bg(surface: pygame.Surface, t: float, dark: bool = False,
                 accent=(90, 120, 200)) -> None:
    """Vertical gradient sky with a huge faint clock face."""
    top = (12, 16, 30) if dark else (16, 22, 42)
    bottom = (30, 42, 78) if dark else (44, 62, 108)
    h = DESIGN_H
    for y in range(0, h, 4):
        f = y / h
        c = tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3))
        pygame.draw.rect(surface, c, (0, y, DESIGN_W, 4))
    # faint clock face
    cx, cy, r = DESIGN_W // 2, DESIGN_H // 2 - 40, 260
    for i in range(60):
        ang = i / 60 * math.tau
        r1 = r - (10 if i % 5 == 0 else 4)
        x1, y1 = cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)
        x2, y2 = cx + r * math.cos(ang), cy + r * math.sin(ang)
        alpha = 26 if i % 5 else 44
        pygame.draw.line(surface, (140, 160, 210), (x1, y1), (x2, y2), 2 if i % 5 == 0 else 1)
        pygame.draw.circle(surface, (150, 170, 220), (x1, y1), 2 if i % 5 == 0 else 1)
        pygame.draw.circle(surface, (150, 170, 220), (x1, y1), 1)
        del alpha
    # sweeping hands
    ha = t * 0.5
    hx, hy = cx + 150 * math.cos(ha), cy + 150 * math.sin(ha)
    pygame.draw.line(surface, (200, 215, 245), (cx, cy), (hx, hy), 3)
    pygame.draw.line(surface, (200, 215, 245), (cx, cy),
                     (cx + 210 * math.cos(ha * 2.4), cy + 210 * math.sin(ha * 2.4)), 2)
    pygame.draw.circle(surface, (220, 230, 250), (cx, cy), 7)
    # vignette
    vig = pygame.Surface((DESIGN_W, DESIGN_H), pygame.SRCALPHA)
    for i in range(90):
        a = int(4 * (i / 90))
        pygame.draw.rect(vig, (0, 0, 6, a), (i, i, DESIGN_W - 2 * i, DESIGN_H - 2 * i), width=2)
    surface.blit(vig, (0, 0))
