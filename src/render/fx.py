"""Particles & visual effects: snow, sparkles, glows, screen fades."""
from __future__ import annotations

import math
import random

import pygame

from ..config import DESIGN_H, DESIGN_W


class Particles:
    """A lightweight particle system (snow, sparkles, dust...)."""

    def __init__(self, count: int = 120) -> None:
        self.count = count
        self.parts: list[dict] = []
        self._rng = random.Random(42)

    def reset(self, area: pygame.Rect) -> None:
        self.parts = []
        for _ in range(self.count):
            self.parts.append({
                "x": self._rng.uniform(area.left, area.right),
                "y": self._rng.uniform(area.top, area.bottom),
                "vx": self._rng.uniform(-6, 6),
                "vy": self._rng.uniform(12, 34),
                "size": self._rng.uniform(1.0, 2.6),
                "phase": self._rng.uniform(0, math.tau),
                "sway": self._rng.uniform(0.4, 1.2),
            })

    def update(self, dt: float, wind: float = 0.0) -> None:
        for p in self.parts:
            p["phase"] += dt * 2.2
            p["x"] += (p["vx"] + wind + math.sin(p["phase"]) * p["sway"] * 22) * dt
            p["y"] += p["vy"] * dt
            if p["y"] > DESIGN_H + 4:
                p["y"] = -4
                p["x"] = self._rng.uniform(0, DESIGN_W)
            if p["x"] > DESIGN_W + 4:
                p["x"] = -4
            if p["x"] < -4:
                p["x"] = DESIGN_W + 4

    def draw(self, surface: pygame.Surface, color=(225, 228, 240), alpha: int = 170) -> None:
        for p in self.parts:
            s = max(1, int(p["size"]))
            r = pygame.Rect(int(p["x"]), int(p["y"]), s, s)
            shade = max(0, min(255, alpha + int(30 * math.sin(p["phase"]))))
            pygame.draw.rect(surface, color, r)
            if s > 1:
                pygame.draw.rect(surface, (255, 255, 255), r, 1)
            del shade


class Sparks:
    """Small rising/rotating sparkles for menus and titles."""

    def __init__(self, count: int = 40) -> None:
        self.parts = []
        self._rng = random.Random(7)
        for _ in range(count):
            self.parts.append(self._new())

    def _new(self) -> dict:
        return {
            "x": self._rng.uniform(0, DESIGN_W),
            "y": self._rng.uniform(0, DESIGN_H),
            "r": self._rng.uniform(0.5, 2.0),
            "vx": self._rng.uniform(-8, 8),
            "vy": self._rng.uniform(-26, -8),
            "phase": self._rng.uniform(0, math.tau),
            "life": self._rng.uniform(2, 5),
        }

    def update(self, dt: float) -> None:
        for p in self.parts:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["phase"] += dt * 3
            p["life"] -= dt
            if p["life"] <= 0:
                p.update(self._new())

    def draw(self, surface: pygame.Surface, color=(220, 225, 255), alpha: int = 140) -> None:
        for p in self.parts:
            tw = 0.5 + 0.5 * math.sin(p["phase"])
            a = int(alpha * tw)
            if a <= 0:
                continue
            c = (color[0], color[1], color[2])
            pygame.draw.circle(surface, c, (int(p["x"]), int(p["y"])), max(1, int(p["r"])))
            if p["r"] > 1.4:
                pygame.draw.circle(surface, (255, 255, 255),
                                   (int(p["x"]), int(p["y"])), 1)
            del a


class Glow:
    """Radial glow blitted onto a surface (for lamps, windows, titles)."""

    @staticmethod
    def make(color: tuple[int, int, int], radius: int, intensity: float = 0.5) -> pygame.Surface:
        size = radius * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        for r in range(radius, 0, -1):
            t = r / radius
            a = int(255 * intensity * (1 - t) * (1 - t))
            pygame.draw.circle(surf, (*color, a), (radius, radius), r)
        return surf


class ScreenFade:
    """Full-screen fade (black/color) used for scene transitions."""

    def __init__(self, color=(0, 0, 0), speed: float = 1.6) -> None:
        self.color = color
        self.speed = speed
        self.value = 1.0          # 1 = fully opaque
        self.target = 0.0
        self.hold = 0.0

    def fade_out(self, hold: float = 0.0) -> None:
        self.target = 1.0
        self.hold = hold

    def fade_in(self) -> None:
        self.target = 0.0

    def update(self, dt: float) -> float:
        if self.hold > 0:
            self.hold -= dt
            return self.value
        diff = self.target - self.value
        if abs(diff) < 0.004:
            self.value = self.target
        else:
            self.value += diff * min(1.0, self.speed * dt * 3.0)
        return self.value

    @property
    def opaque(self) -> bool:
        return self.value >= 0.99 and self.target >= 0.99

    @property
    def clear(self) -> bool:
        return self.value <= 0.01 and self.target <= 0.01

    def draw(self, surface: pygame.Surface) -> None:
        if self.value > 0.01:
            overlay = pygame.Surface((DESIGN_W, DESIGN_H))
            overlay.fill(self.color)
            overlay.set_alpha(int(255 * min(1.0, self.value)))
            surface.blit(overlay, (0, 0))
