"""Story intro: cinematic cards before Day 1 (no spoilers)."""
from __future__ import annotations

import pygame

from ..audio import play
from ..core.scene import Scene
from ..render.background import draw_menu_bg
from ..render.fx import ScreenFade
from ..render.text import draw_text, draw_wrapped
from ..render.ui import Button, Panel


class IntroScene(Scene):
    CARDS = [
        ("intro.t1_title", "intro.t1_text"),
        ("intro.t2_title", "intro.t2_text"),
        ("intro.t3_title", "intro.t3_text"),
        ("intro.t4_title", "intro.t4_text"),
    ]

    def on_enter(self, **kwargs) -> None:
        self.index = 0
        self.char_t = 0.0
        self.fade = ScreenFade(speed=1.2)
        self.fade.fade_in()
        self.transition = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_e, pygame.K_SPACE,
                                                          pygame.K_RETURN):
            self.advance()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.advance()

    def advance(self) -> None:
        if self.transition > 0:
            return
        if self.index < len(self.CARDS) - 1:
            self.index += 1
            self.char_t = 0.0
            play("notebook")
        else:
            self.start_game()

    def start_game(self) -> None:
        from .gameplay import GameplayScene
        from ..game.gamestate import GameState
        play("confirm")
        self.app.switch(GameplayScene(self.app, state=GameState(), fresh=True))

    def update(self, dt: float) -> None:
        self.fade.update(dt)
        self.char_t += dt * 42
        if self.transition > 0:
            self.transition -= dt

    def draw(self, surface: pygame.Surface) -> None:
        draw_menu_bg(surface, self.index * 0.7, dark=True)
        tr = self.app.tr
        key_title, key_text = self.CARDS[self.index]
        title = tr.t(key_title)
        text = tr.t(key_text)
        # title
        draw_text(surface, title, (640, 170), size=56, kind="serif_bold",
                  color=(245, 226, 170), align="center", glow=(212, 175, 55), glow_radius=3)
        pygame.draw.line(surface, (100, 110, 140), (430, 230), (850, 230), 1)
        # typewriter text
        shown = text[: int(self.char_t)]
        draw_wrapped(surface, shown, (190, 300), 900, size=26, color=(222, 228, 240),
                     line_spacing=12)
        if int(self.char_t) < len(text):
            pygame.draw.circle(surface, (245, 226, 170), (1240, 660), 5)
        # progress dots
        for i in range(len(self.CARDS)):
            c = (245, 226, 170) if i == self.index else (70, 80, 110)
            pygame.draw.circle(surface, c, (640 - 30 + i * 20, 620), 5)
        draw_text(surface, tr.t("intro.skip"), (640, 660), size=16,
                  color=(120, 130, 160), align="center", shadow=False)
        self.fade.draw(surface)
