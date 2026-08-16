"""Scene base class."""
from __future__ import annotations

import pygame


class Scene:
    """A screen state: splash, menu, gameplay, overlays, etc."""

    def __init__(self, app) -> None:
        self.app = app

    # lifecycle
    def on_enter(self, **kwargs) -> None:
        pass

    def on_exit(self) -> None:
        pass

    # events / update / draw
    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pass
