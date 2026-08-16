"""Save / load screens (list of slots with metadata)."""
from __future__ import annotations

import pygame

from ..audio import play
from ..core.scene import Scene
from ..render.background import draw_menu_bg
from ..render.text import draw_text, draw_wrapped
from ..render.ui import Button, Panel
from ..saves import (AUTOSAVE_FILE, delete_save, list_saves, load_game,
                     save_slot)


class SavesScene(Scene):
    """mode: 'load' (from main menu / game over) or 'save' (from pause)."""

    def __init__(self, app, mode: str = "load") -> None:
        super().__init__(app)
        self.mode = mode

    def on_enter(self, **kwargs) -> None:
        self.entries = list_saves()
        self.confirm_delete: dict | None = None
        self.notice = ""
        self.buttons: list[Button] = []
        self.rebuild()

    def rebuild(self) -> None:
        self.buttons = []
        self.entries = list_saves()
        self.entry_widgets = []          # (button, entry, title, sub, money, meta)
        self.del_buttons = []            # (button, entry)
        tr = self.app.tr
        y = 170
        from ..config import MAX_SAVE_SLOTS
        if self.mode == "save":
            # save mode: show all slots, empty ones as placeholders
            existing = {e["slot"]: e for e in self.entries if not e["autosave"]}
            shown: list = [e for e in self.entries if e["autosave"]]
            for i in range(1, MAX_SAVE_SLOTS + 1):
                shown.append(existing.get(i, {"slot": i, "empty": True, "meta": None}))
        else:
            shown = self.entries
        for e in shown:
            if e.get("empty"):
                meta = None
                title = tr.t("saves.slot", n=e["slot"]) + " — " + tr.t("saves.empty").lower()
                sub, money = "", ""
                btn = Button(pygame.Rect(300, y, 680, 64), "", self.on_save_empty(e),
                             style="ghost", size=18)
                self.entry_widgets.append((btn, e, title, sub, money, meta))
                del_btn = None
                y += 76
                continue
            meta = e["meta"]
            title = tr.t("saves.autosave") if e["autosave"] else tr.t("saves.slot", n=e["slot"])
            sub = tr.t("saves.day_info", day=meta["day"], date=meta["date"], time=meta["time"])
            money = tr.t("saves.money", money=meta["money"])
            btn = Button(pygame.Rect(300, y, 680, 64), "", self.on_click(e),
                         style="default", size=18)
            self.entry_widgets.append((btn, e, title, sub, money, meta))
            if not e.get("autosave") or self.mode == "load":
                del_btn = Button(pygame.Rect(990, y, 60, 64), "✕", self.on_delete(e),
                                 style="danger", size=22)
                self.del_buttons.append((del_btn, e))
            y += 76
        self.back_btn = Button(pygame.Rect(540, 620, 200, 46),
                               tr.t("saves.back"), self.go_back, style="gold", size=22)
        self.buttons = [self.back_btn]

    def on_save_empty(self, entry):
        def cb():
            if self.mode == "save" and self.app.gameplay is not None:
                if save_slot(self.app.gameplay.state, entry["slot"]):
                    play("confirm")
                    self.notice = self.app.tr.t("pause.saved")
                    self.rebuild()
        return cb

    def on_click(self, entry):
        def cb():
            if self.mode == "save":
                gp = self.app.gameplay
                if gp is not None:
                    save_slot(gp.state, entry["slot"] or 1)
                    play("confirm")
                    self.notice = self.app.tr.t("pause.saved")
                self.rebuild()
            else:
                st = load_game(entry["path"])
                if st is None:
                    self.notice = self.app.tr.t("pause.save_failed")
                    return
                from .gameplay import GameplayScene
                play("confirm")
                # drop this menu, any overlays and the old gameplay scene
                while self.app.scenes and not isinstance(self.app.scenes[-1],
                                                         GameplayScene):
                    self.app.scenes.pop()
                if self.app.scenes and isinstance(self.app.scenes[-1], GameplayScene):
                    self.app.scenes.pop()
                self.app.push(GameplayScene(self.app, state=st))
        return cb

    def on_delete(self, entry):
        def cb():
            if entry.get("autosave"):
                delete_save(entry["path"])
            else:
                delete_save(entry["path"])
            play("back")
            self.notice = self.app.tr.t("saves.deleted")
            self.rebuild()
        return cb

    def go_back(self) -> None:
        play("back")
        self.app.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.back_btn.handle(event):
            return
        for btn, _e in self.del_buttons:
            if btn.handle(event):
                return
        for btn, _e, _t, _s, _m, _meta in self.entry_widgets:
            if btn.handle(event):
                return

    def update(self, dt: float) -> None:
        mouse = self.app.mouse()
        self.back_btn.update(dt, mouse)
        for btn, _e in self.del_buttons:
            btn.update(dt, mouse)
        for btn, *_rest in self.entry_widgets:
            btn.update(dt, mouse)

    def draw(self, surface: pygame.Surface) -> None:
        draw_menu_bg(surface, 0.0, dark=True)
        tr = self.app.tr
        title = tr.t("saves.title") if self.mode == "load" else tr.t("pause.save_game")
        draw_text(surface, title, (640, 90), size=44, kind="serif_bold",
                  color=(240, 240, 245), align="center", glow=(212, 175, 55), glow_radius=2)
        if not self.entries:
            draw_text(surface, tr.t("saves.empty"), (640, 300), size=30,
                      align="center", color=(200, 205, 220))
            draw_wrapped(surface, tr.t("saves.empty_hint"), (640, 350), 600,
                         size=18, color=(140, 150, 175), align="center")
        self.back_btn.draw(surface)
        for btn, _e in self.del_buttons:
            btn.draw(surface)
        for btn, e, title, sub, money, meta in self.entry_widgets:
            btn.draw(surface)
            draw_text(surface, title, (330, btn.rect.y + 10), size=22, kind="sans_bold",
                      shadow=False)
            draw_text(surface, sub, (330, btn.rect.y + 36), size=16,
                      color=(160, 170, 195), shadow=False)
            draw_text(surface, money, (940, btn.rect.y + 20), size=20,
                      color=(245, 226, 170), align="right", shadow=False)
        if self.notice:
            draw_text(surface, self.notice, (640, 590), size=18, color=(150, 210, 150),
                      align="center", shadow=False)
