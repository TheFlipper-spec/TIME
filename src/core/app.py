"""Application core: window, event loop, scene stack, rendering pipeline."""
from __future__ import annotations

import sys

import pygame

from .. import __version__
from ..config import DESIGN_H, DESIGN_W, FPS, USERDATA
from ..settings import Settings
from .input import Input
from .scene import Scene


class App:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.input = Input()
        self.running = True
        self.scenes: list[Scene] = []
        self.canvas = pygame.Surface((DESIGN_W, DESIGN_H))
        self.window: pygame.Surface | None = None
        self.screen_size = (DESIGN_W, DESIGN_H)
        self.letterbox = (0, 0)
        self.max_frames: int | None = None   # test hook: stop after N frames
        self._frames = 0
        self.quit_requested = False
        self._last_frame_time = 0.0
        # services injected by main.py
        self.tr = None                       # Translator
        self.sprites = None                  # SpriteBank
        self.witness_portraits: dict = {}
        self.gameplay = None                 # current GameplayScene (or None)
        self.on_quit = None                  # autosave hook

    # ------------------------------------------------------------ window ---
    def setup_window(self) -> None:
        pygame.display.set_caption(f"TIME {__version__} — детектив FL1PPER")
        try:
            icon = pygame.Surface((32, 32))
            icon.fill((16, 20, 32))
            pygame.draw.rect(icon, (212, 175, 55), (6, 6, 20, 20), width=3, border_radius=4)
            font = pygame.font.SysFont("serif", 20, bold=True)
            img = font.render("T", True, (245, 226, 170))
            icon.blit(img, (11, 3))
            pygame.display.set_icon(icon)
        except Exception:
            pass
        flags = pygame.FULLSCREEN | pygame.SCALED if self.settings.fullscreen else pygame.RESIZABLE
        try:
            self.window = pygame.display.set_mode(self.settings.resolution, flags)
        except Exception:
            self.window = pygame.display.set_mode((DESIGN_W, DESIGN_H))
        self.screen_size = self.window.get_size()
        self._update_letterbox()

    def _update_letterbox(self) -> None:
        scale = min(self.screen_size[0] / DESIGN_W, self.screen_size[1] / DESIGN_H)
        w, h = int(DESIGN_W * scale), int(DESIGN_H * scale)
        self.letterbox = ((self.screen_size[0] - w) // 2, (self.screen_size[1] - h) // 2, w, h)

    def apply_settings(self) -> None:
        self.setup_window()
        self.settings.save()

    # ------------------------------------------------------------ scenes ---
    def push(self, scene: Scene, **kwargs) -> None:
        # the scene must be on the stack before its on_enter runs, so it can
        # safely push overlays on top of itself
        self.scenes.append(scene)
        scene.on_enter(**kwargs)

    def pop(self) -> None:
        if self.scenes:
            s = self.scenes.pop()
            s.on_exit()

    def switch(self, scene: Scene, **kwargs) -> None:
        self.pop()
        self.push(scene, **kwargs)

    def replace_top(self, scene: Scene, **kwargs) -> None:
        """Replace the top scene without on_exit of the old one (for overlays)."""
        if self.scenes:
            self.scenes.pop()
        self.push(scene, **kwargs)

    def reset(self, scene: Scene, **kwargs) -> None:
        """Clear the whole scene stack (running on_exit) and push one scene.

        Used to return to the main menu: this guarantees no stale gameplay
        scene lingers below the menu and keeps app.gameplay / autosave hooks
        in a clean state.
        """
        while self.scenes:
            s = self.scenes.pop()
            try:
                s.on_exit()
            except Exception:
                pass
        self.push(scene, **kwargs)

    def top(self) -> Scene:
        return self.scenes[-1] if self.scenes else None  # type: ignore[return-value]

    def quit(self) -> None:
        self.running = False

    def mouse(self) -> tuple[int, int]:
        """Current mouse position in design-resolution coordinates."""
        x, y = pygame.mouse.get_pos()
        scale = min(self.screen_size[0] / DESIGN_W, self.screen_size[1] / DESIGN_H)
        return int((x - self.letterbox[0]) / scale), int((y - self.letterbox[1]) / scale)

    def _remap_event(self, event: pygame.event.Event) -> pygame.event.Event:
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN,
                          pygame.MOUSEBUTTONUP):
            x, y = event.pos
            scale = min(self.screen_size[0] / DESIGN_W, self.screen_size[1] / DESIGN_H)
            event.pos = (int((x - self.letterbox[0]) / scale),
                         int((y - self.letterbox[1]) / scale))
        return event

    # ------------------------------------------------------------- loop ---
    def run(self) -> None:
        clock = pygame.time.Clock()
        while self.running:
            dt = clock.tick(FPS) / 1000.0
            dt = min(dt, 0.1)
            self._frames += 1
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                if event.type == pygame.VIDEORESIZE and not self.settings.fullscreen:
                    self.screen_size = event.size
                    self._update_letterbox()
                self.input.handle(event)
                if self.scenes:
                    self.scenes[-1].handle_event(self._remap_event(event))
            if not self.running:
                break
            self.input.update(dt)
            if self.scenes:
                scene = self.scenes[-1]
                scene.update(dt)
                self.canvas.fill((0, 0, 0))
                scene.draw(self.canvas)
            self._present()
            if self.max_frames is not None and self._frames >= self.max_frames:
                self.running = False

    def _present(self) -> None:
        if self.window is None:
            return
        scale = min(self.screen_size[0] / DESIGN_W, self.screen_size[1] / DESIGN_H)
        if scale == 1.0:
            self.window.blit(self.canvas, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(self.canvas,
                                                  (int(DESIGN_W * scale), int(DESIGN_H * scale)))
            self.window.fill((0, 0, 0))
            self.window.blit(scaled, (self.letterbox[0], self.letterbox[1]))
        pygame.display.flip()


def ensure_userdata() -> None:
    USERDATA.mkdir(parents=True, exist_ok=True)
    (USERDATA / "saves").mkdir(parents=True, exist_ok=True)
    (USERDATA / "cache").mkdir(parents=True, exist_ok=True)
