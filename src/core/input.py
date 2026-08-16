"""Keyboard state helper (pressed / just pressed / held repeat)."""
from __future__ import annotations

import pygame


class Input:
    def __init__(self) -> None:
        self._down: set[int] = set()
        self._pressed: set[int] = set()
        self._repeat: dict[int, float] = {}
        self._repeat_initial = 0.35
        self._repeat_interval = 0.12

    def handle(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key not in self._down:
                self._pressed.add(event.key)
                self._repeat[event.key] = self._repeat_initial
            self._down.add(event.key)
        elif event.type == pygame.KEYUP:
            self._down.discard(event.key)
            self._repeat.pop(event.key, None)

    def update(self, dt: float) -> None:
        self._pressed.clear()
        for k, t in list(self._repeat.items()):
            self._repeat[k] = t - dt
            if self._repeat[k] <= 0:
                self._repeat[k] = self._repeat_interval
                self._pressed.add(k)

    def is_down(self, *keys) -> bool:
        return any(k in self._down for k in keys)

    def just_pressed(self, *keys) -> bool:
        return any(k in self._pressed for k in keys)
