"""Camera that follows a target with smoothing."""
from __future__ import annotations

import pygame

from ..config import DESIGN_H, DESIGN_W


class Camera:
    def __init__(self, world_w: int, world_h: int) -> None:
        self.world_w = world_w
        self.world_h = world_h
        self.x = 0.0
        self.y = 0.0
        self._smooth = 6.0

    def snap(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self._clamp()

    def follow(self, target_x: float, target_y: float, dt: float) -> None:
        self.x += (target_x - self.x) * min(1.0, self._smooth * dt)
        self.y += (target_y - self.y) * min(1.0, self._smooth * dt)
        self._clamp()

    def _clamp(self) -> None:
        self.x = max(0.0, min(self.world_w - DESIGN_W, self.x))
        self.y = max(0.0, min(self.world_h - DESIGN_H, self.y))

    def offset(self) -> tuple[int, int]:
        return int(self.x), int(self.y)

    def to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        return int(wx - self.x), int(wy - self.y)
