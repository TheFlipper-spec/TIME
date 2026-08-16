"""Settings screen: resolution, fullscreen, language, volumes, Yandex key."""
from __future__ import annotations

import threading

import pygame

from ..audio import play, play_theme, set_music_volume, set_sfx_volume
from ..core.scene import Scene
from ..render.background import draw_menu_bg
from ..render.text import draw_text, draw_wrapped
from ..render.ui import Button, Dropdown, InputBox, Panel, Slider
from ..settings import LANGUAGES, desktop_resolutions


class SettingsScene(Scene):
    def __init__(self, app, from_menu: bool = False) -> None:
        super().__init__(app)
        self.from_menu = from_menu

    def on_enter(self, **kwargs) -> None:
        self.s = self.app.settings
        self.orig = (self.s.resolution, self.s.fullscreen, self.s.language,
                     self.s.sfx_volume, self.s.music_volume)
        self.build_ui()
        self.notice = ""
        self.notice_color = (150, 200, 150)
        self.testing = False

    def build_ui(self) -> None:
        self.widgets = []
        cx = 640
        y = 130
        panel = Panel(pygame.Rect(200, 90, 880, 540), self.app.tr.t("settings.title"))
        self.panel = panel

        def row(label_key, ypos):
            draw_label = True
            return draw_label, ypos

        # resolution dropdown
        res = desktop_resolutions()
        res_options = []
        for r in res:
            tag = "«системное»" if r == res[0] else f"{r[0]}×{r[1]}"
            res_options.append((f"{r[0]}x{r[1]}", tag))
        self.res_dd = Dropdown(pygame.Rect(cx - 200, y, 400, 36), res_options,
                               f"{self.s.resolution[0]}x{self.s.resolution[1]}",
                               self.on_resolution, size=20)
        self.res_label = (cx - 200, y - 26)
        self.widgets.append(self.res_dd)
        y += 58

        # fullscreen
        self.fs_btn = Button(pygame.Rect(cx - 200, y, 400, 36), "", self.on_fullscreen,
                             style="default", size=20)
        self.widgets.append(self.fs_btn)
        y += 58

        # language
        lang_options = [(k, f"{v[0]} ({k})") for k, v in LANGUAGES.items()]
        self.lang_dd = Dropdown(pygame.Rect(cx - 200, y, 400, 36), lang_options,
                                self.s.language, self.on_language, size=20)
        self.lang_label = (cx - 200, y - 26)
        self.widgets.append(self.lang_dd)
        y += 58

        # volumes
        self.sfx_slider = Slider(pygame.Rect(cx - 200, y, 300, 18), self.s.sfx_volume,
                                 self.on_sfx)
        self.music_slider = Slider(pygame.Rect(cx - 200, y + 40, 300, 18),
                                   self.s.music_volume, self.on_music)
        self.sfx_label = (cx - 200, y - 26)
        self.music_label = (cx - 200, y + 14)
        self.widgets += [self.sfx_slider, self.music_slider]
        y += 96

        # yandex
        self.yk_input = InputBox(pygame.Rect(cx - 200, y, 400, 36),
                                 self.s.yandex_api_key, placeholder="API-ключ…",
                                 secret=True, max_len=200)
        self.yk_label = (cx - 200, y - 26)
        self.widgets.append(self.yk_input)
        y += 52
        self.test_btn = Button(pygame.Rect(cx - 200, y, 180, 32),
                               self.app.tr.t("settings.yandex_test"), self.test_key,
                               style="ghost", size=18)
        self.reset_btn = Button(pygame.Rect(cx + 20, y, 180, 32),
                                self.app.tr.t("settings.reset"), self.reset_settings,
                                style="danger", size=18)
        self.widgets += [self.test_btn, self.reset_btn]
        y += 52
        self.back_btn = Button(pygame.Rect(cx - 100, 640, 200, 46),
                               self.app.tr.t("settings.back"), self.go_back,
                               style="gold", size=22)
        self.widgets.append(self.back_btn)
        self._update_labels()

    def _update_labels(self) -> None:
        self.fs_btn.label = self.app.tr.t("settings.fullscreen") + ": " + (
            self.app.tr.t("settings.on") if self.s.fullscreen else self.app.tr.t("settings.off"))

    # ------------------------------------------------------------- events --
    def on_resolution(self, val: str) -> None:
        w, h = val.split("x")
        self.s.resolution = (int(w), int(h))
        self.app.apply_settings()

    def on_fullscreen(self) -> None:
        self.s.fullscreen = not self.s.fullscreen
        self.app.apply_settings()
        self._update_labels()

    def on_language(self, val: str) -> None:
        self.s.language = val
        self.app.tr.set_language(val)
        self.s.save()
        self.build_ui()

    def on_sfx(self, v: float) -> None:
        self.s.sfx_volume = v
        set_sfx_volume(v)
        self.s.save()

    def on_music(self, v: float) -> None:
        self.s.music_volume = v
        set_music_volume(v)
        self.s.save()

    def test_key(self) -> None:
        if self.testing:
            return
        self.testing = True
        self.notice = "…"

        def worker():
            from ..i18n import Translator
            t = Translator()
            t.bind_settings(lambda: self.s)
            try:
                out = t.tr_text("Привет из Тихореченска", "en")
                ok = bool(out)
            except Exception:
                ok = False
            self.testing = False
            self.notice = self.app.tr.t("settings.yandex_test_ok") if ok \
                else self.app.tr.t("settings.yandex_test_fail")
            self.notice_color = (150, 210, 150) if ok else (220, 120, 120)

        threading.Thread(target=worker, daemon=True).start()

    def reset_settings(self) -> None:
        self.s.resolution, self.s.fullscreen, self.s.language, \
            self.s.sfx_volume, self.s.music_volume = \
            desktop_resolutions()[0], False, "ru", 0.8, 0.5
        self.s.yandex_api_key = ""
        self.s.yandex_folder_id = ""
        self.s.yandex_iam_token = ""
        self.app.tr.set_language("ru")
        self.app.apply_settings()
        set_sfx_volume(0.8)
        set_music_volume(0.5)
        self.build_ui()
        self.notice = self.app.tr.t("settings.applied")
        self.notice_color = (150, 210, 150)

    def go_back(self) -> None:
        play("back")
        self.app.pop()

    # ------------------------------------------------------------- update --
    def handle_event(self, event: pygame.event.Event) -> None:
        for w in self.widgets:
            if w.handle(event):
                return

    def update(self, dt: float) -> None:
        mouse = self.app.mouse()
        for w in self.widgets:
            w.update(dt, mouse)
        self.s.yandex_api_key = self.yk_input.text if hasattr(self, "yk_input") else self.s.yandex_api_key
        self.s.save()

    def draw(self, surface: pygame.Surface) -> None:
        draw_menu_bg(surface, 0.0, dark=True)
        self.panel.draw(surface)
        tr = self.app.tr
        cx = 640
        draw_text(surface, tr.t("settings.resolution"), (cx - 200, self.res_label[1]),
                  size=16, color=(160, 170, 195), shadow=False)
        draw_text(surface, tr.t("settings.language"), (cx - 200, self.lang_label[1]),
                  size=16, color=(160, 170, 195), shadow=False)
        draw_text(surface, tr.t("settings.sfx"), (cx - 200, self.sfx_label[1]),
                  size=16, color=(160, 170, 195), shadow=False)
        draw_text(surface, tr.t("settings.music"), (cx - 200, self.music_label[1]),
                  size=16, color=(160, 170, 195), shadow=False)
        draw_text(surface, tr.t("settings.yandex_key"), (cx - 200, self.yk_label[1]),
                  size=16, color=(160, 170, 195), shadow=False)
        draw_text(surface, tr.t("settings.yandex_title"), (cx, 100), size=24,
                  color=(212, 175, 55), align="center", kind="sans_bold", shadow=False)
        note = tr.t("settings.yandex_note_ok") if self.s.yandex_configured \
            else tr.t("settings.yandex_note_offline")
        draw_wrapped(surface, note, (cx - 200, 552), 400, size=14,
                     color=(130, 140, 165), line_spacing=4)
        if self.notice:
            draw_text(surface, self.notice, (cx, 610), size=17, color=self.notice_color,
                      align="center", shadow=False)
        for w in self.widgets:
            w.draw(surface)
