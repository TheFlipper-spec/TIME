"""Splash screen (FL1PPER) and the main menu."""
from __future__ import annotations

import math
import pygame

from .. import AUTHOR, __version__
from ..audio import play, play_theme
from ..core.scene import Scene
from ..render.background import draw_menu_bg
from ..render.fx import Sparks
from ..render.text import draw_text
from ..render.ui import Button
from ..settings import LANGUAGES

SPLASH_SECONDS = 4.2


class SplashScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self.t = 0.0
        self.skipped = False
        self.sparks = Sparks(60)
        self.done = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.t = SPLASH_SECONDS + 0.5

    def update(self, dt: float) -> None:
        self.t += dt
        self.sparks.update(dt)
        if self.t >= SPLASH_SECONDS and not self.done:
            self.done = True
            self.app.switch(MainMenuScene(self.app))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((6, 8, 16))
        # slow rotating rings
        cx, cy = 640, 330
        t = self.t
        for i, rr in enumerate((150, 190, 230)):
            ang = t * (0.4 + i * 0.13)
            pts = []
            for k in range(48):
                a = ang + k / 48 * math.tau
                r = rr + 6 * math.sin(a * 3 + t * 2)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            color = (60 + i * 30, 80 + i * 30, 140 + i * 20)
            pygame.draw.lines(surface, color, True, pts, 1 if i < 2 else 2)
        # letters of FL1PPER appear one by one
        word = "FL1PPER"
        letters = []
        for i, ch in enumerate(word):
            appear = max(0.0, min(1.0, (t - 0.4 - i * 0.28) / 0.5))
            if appear <= 0:
                continue
            scale = 0.6 + 0.4 * appear
            x = 640 - 5 * 34 + i * 68 + (1 - appear) * 30
            size = int(120 * scale * (0.6 + 0.4 * appear))
            glow = int(180 * appear)
            img = pygame.font.Font(None, size).render(ch, True, (235, 235, 245))
            if glow < 255:
                img.set_alpha(glow)
            surface.blit(img, (x - img.get_width() // 2, cy - img.get_height() // 2))
            letters.append((x, size))
        if t > 1.2:
            a = max(0.0, min(1.0, (t - 1.2) * 2))
            draw_text(surface, self.app.tr.t("splash.presents"), (640, cy + 110),
                      size=26, color=(170, 180, 210), align="center", alpha=int(255 * a))
        if t > 2.0:
            a = max(0.0, min(1.0, (t - 2.0) * 2))
            draw_text(surface, "2023 · v" + __version__, (640, cy + 160),
                      size=16, color=(110, 120, 150), align="center", alpha=int(255 * a))
        if t > 2.6:
            a = 0.5 + 0.5 * math.sin(t * 4)
            draw_text(surface, self.app.tr.t("splash.skip"), (640, 690),
                      size=15, color=(120, 130, 160), align="center", alpha=int(200 * a))
        self.sparks.draw(surface, alpha=120)


class MainMenuScene(Scene):
    def on_enter(self, **kwargs) -> None:
        play_theme("menu")
        self.t = 0.0
        self.sparks = Sparks(50)
        self.buttons: list[Button] = []
        cx = 640
        y = 300
        items = [
            ("menu.new_game", self.new_game, "gold"),
            ("menu.load_game", self.load_game, "default"),
            ("menu.settings", self.settings, "default"),
            ("menu.exit", self.exit_game, "ghost"),
        ]
        for key, cb, style in items:
            b = Button(pygame.Rect(cx - 180, y, 360, 56), self.app.tr.t(key), cb,
                       style=style, size=26)
            self.buttons.append(b)
            y += 72
        self.lang_button = Button(pygame.Rect(24, 18, 150, 42), "", self.cycle_lang,
                                  style="ghost", size=20)
        self.update_lang_label()

    def update_lang_label(self) -> None:
        lang = self.app.settings.language
        name = LANGUAGES[lang][0]
        self.lang_button.label = f"{name} ▾"

    def cycle_lang(self) -> None:
        langs = list(LANGUAGES.keys())
        cur = self.app.settings.language
        nxt = langs[(langs.index(cur) + 1) % len(langs)]
        self.app.settings.language = nxt
        self.app.tr.set_language(nxt)
        self.app.settings.save()
        self.update_lang_label()
        # refresh button labels
        labels = [("menu.new_game", "Новая игра"), ("menu.load_game", "Загрузить игру"),
                  ("menu.settings", "Настройки"), ("menu.exit", "Выход")]
        for b, (key, _old) in zip(self.buttons, labels):
            b.label = self.app.tr.t(key)

    def new_game(self) -> None:
        from .intro import IntroScene
        self.app.switch(IntroScene(self.app))

    def load_game(self) -> None:
        from .saves_menu import SavesScene
        self.app.push(SavesScene(self.app, mode="load"))

    def settings(self) -> None:
        from .settings_menu import SettingsScene
        self.app.push(SettingsScene(self.app, from_menu=True))

    def exit_game(self) -> None:
        self.app.quit()

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            if b.handle(event):
                return
        self.lang_button.handle(event)

    def update(self, dt: float) -> None:
        self.t += dt
        self.sparks.update(dt)
        mouse = self.app.mouse()
        for b in self.buttons + [self.lang_button]:
            b.update(dt, mouse)

    def draw(self, surface: pygame.Surface) -> None:
        draw_menu_bg(surface, self.t)
        self.sparks.draw(surface, alpha=110)
        # Title: TIME with glow
        t = self.t
        for dy in range(8, 0, -1):
            a = max(0, 120 - dy * 12)
            draw_text(surface, "TIME", (640, 90 + dy), size=120, kind="serif_bold",
                      color=(212, 175, 55), align="center", glow=(212, 175, 55),
                      alpha=a, glow_radius=2, shadow=False)
        draw_text(surface, "TIME", (640, 90), size=120, kind="serif_bold",
                  color=(245, 226, 170), align="center", outline=True, shadow=False)
        # subtle breathing glow on the title
        ph = math.sin(t * 1.4)
        draw_text(surface, "TIME", (640, 90), size=120, kind="serif_bold",
                  color=(255, 244, 205), align="center", shadow=False,
                  alpha=int(120 + 90 * ph))
        draw_text(surface, self.app.tr.t("menu.subtitle"), (640, 228), size=22,
                  color=(170, 180, 205), align="center", shadow=False)
        # divider
        pygame.draw.line(surface, (90, 100, 130), (430, 262), (850, 262), 1)
        for b in self.buttons:
            b.draw(surface)
        self.lang_button.draw(surface)
        draw_text(surface, self.app.tr.t("menu.author"), (20, 690), size=14,
                  color=(110, 120, 150), shadow=False)
        draw_text(surface, f"v{__version__}", (1240, 690), size=14,
                  color=(110, 120, 150), align="right", shadow=False)
