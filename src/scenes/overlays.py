"""Overlay scenes: dialogue, time travel, notebook, pause, shop, bank,
computer, inspection cards, postcards, confirmations."""
from __future__ import annotations

import math

import pygame

from ..audio import play
from ..config import (DESIGN_H, DESIGN_W, LOAN_MAX, LOAN_MIN, MEDICINE_PRICE,
                      TRAVEL_MAX_OFFSET, TRAVEL_MIN_OFFSET)
from ..core.scene import Scene
from ..game.clues import get as get_clue
from ..game.economy import loan_due_total, repay_loan, take_loan
from ..game.story import POSTCARDS, update_stage
from ..game.time import fmt_clock, fmt_date_short, world_datetime
from ..render.text import draw_text, draw_wrapped
from ..render.ui import Button, InputBox, Panel, ProgressBar
from ..world.npcs import display_name


def _gp(app):
    """Current gameplay scene (may be None in menus)."""
    return app.gameplay


class OverlayScene(Scene):
    """Base for overlays: pauses the gameplay while open."""

    def on_enter(self, **kwargs) -> None:
        gp = _gp(self.app)
        if gp is not None:
            gp.pause()

    def on_exit(self) -> None:
        gp = _gp(self.app)
        if gp is not None:
            gp.resume()


# ------------------------------------------------------------- dialogue ----
class DialogueScene(OverlayScene):
    def __init__(self, app, nid: str, turn) -> None:
        super().__init__(app)
        self.nid = nid
        self.turn = turn
        self.chars = 0.0
        self.choice_rects = []
        portraits = getattr(app, "witness_portraits", {})
        self.portrait = app.sprites.portrait(portraits.get(nid, 1))

    def _text(self, d: dict) -> str:
        lang = self.app.settings.language
        t = d.get(lang)
        if t is None:
            t = d.get("en") or d.get("ru") or ""
            if lang not in ("ru", "en"):
                t = self.app.tr.tr_text(d.get("ru", t))
        return t

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
                if self._text_typing():
                    self.chars = 10 ** 6
                else:
                    self._choose(0)
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                idx = event.key - pygame.K_1
                self._choose(idx)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._text_typing():
                self.chars = 10 ** 6
                return
            for i, ch in enumerate(self.choice_rects):
                if ch.collidepoint(event.pos):
                    self._choose(i)
                    return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()

    def _text_typing(self) -> bool:
        return self.chars < len(self._text(self.turn.text))

    def _choose(self, idx: int) -> None:
        if self._text_typing() or idx >= len(self.turn.choices):
            return
        choice = self.turn.choices[idx]
        if choice.cond is not None and not choice.cond(self.state(), self.app.gameplay):
            play("error")
            return
        play("click")
        gp = self.app.gameplay
        result = None
        if choice.effect is not None:
            result = choice.effect(self.state(), gp)
        if isinstance(result, type(self.turn)):
            self.turn = result
            self.chars = 0.0
        elif choice.next is not None:
            self.turn = choice.next
            self.chars = 0.0
        else:
            self.close()

    def state(self):
        return self.app.gameplay.state

    def close(self) -> None:
        self.app.pop()

    def update(self, dt: float) -> None:
        if self._text_typing():
            self.chars += dt * 46

    def draw(self, surface: pygame.Surface) -> None:
        gp = self.app.gameplay
        dim = pygame.Surface((DESIGN_W, DESIGN_H))
        dim.fill((4, 6, 12))
        dim.set_alpha(150)
        surface.blit(dim, (0, 0))
        lang = self.app.settings.language
        # portrait
        surface.blit(self.portrait, (120, 420))
        name = display_name(self.nid, lang) if self.nid in ("marta", "nick", "boris",
                                                            "volkov", "krylov", "emit") \
            else (self.app.tr.t("hud.speak"))
        draw_text(surface, name, (235, 430), size=26, kind="sans_bold",
                  color=(245, 226, 170), shadow=False)
        panel = Panel(pygame.Rect(220, 470, 900, 210))
        panel.draw(surface)
        text = self._text(self.turn.text)
        shown = text[: int(self.chars)]
        draw_wrapped(surface, shown, (250, 495), 840, size=22, color=(228, 233, 244),
                     line_spacing=8)
        if self._text_typing():
            pygame.draw.circle(surface, (245, 226, 170), (1230, 470), 5)
        # choices
        self.choice_rects = []
        if not self._text_typing() and self.turn.choices:
            y = 700 - 30 * min(3, len(self.turn.choices))
            for i, ch in enumerate(self.turn.choices):
                rect = pygame.Rect(250, y, 780, 34)
                if ch.cond is not None and not ch.cond(self.state(), gp):
                    color = (90, 95, 110)
                else:
                    color = (222, 228, 240)
                draw_text(surface, f"{i + 1}. {self._text(ch.label)}", (rect.x, rect.y),
                          size=20, color=color, shadow=False)
                self.choice_rects.append(rect)
                y += 38
        else:
            draw_text(surface, "E", (250, 662), size=18, color=(150, 160, 185), shadow=False)


# ---------------------------------------------------------- time travel ----
class TimeTravelScene(OverlayScene):
    def on_enter(self, **kwargs) -> None:
        self.offset = self.app.gameplay.state.offset_min
        self.slider_pos = -self.offset / abs(TRAVEL_MIN_OFFSET)
        self.buttons: list[Button] = []
        cx = DESIGN_W // 2
        self.buttons.append(Button(pygame.Rect(cx - 260, 470, 120, 44), "−1 д",
                                   self.shift_day(-1), style="default", size=18))
        self.buttons.append(Button(pygame.Rect(cx - 130, 470, 120, 44), "+1 д",
                                   self.shift_day(1), style="default", size=18))
        self.buttons.append(Button(pygame.Rect(cx + 10, 470, 120, 44), "−1 ч",
                                   self.shift_hour(-1), style="default", size=18))
        self.buttons.append(Button(pygame.Rect(cx + 140, 470, 120, 44), "+1 ч",
                                   self.shift_hour(1), style="default", size=18))
        self.buttons.append(Button(pygame.Rect(cx - 140, 560, 280, 48),
                                   self.app.tr.t("tt.return_present"),
                                   self.to_present, style="gold", size=20))
        self.dragging = False

    def state(self):
        return self.app.gameplay.state

    def shift_hour(self, h: int):
        def cb():
            new = max(TRAVEL_MIN_OFFSET, min(TRAVEL_MAX_OFFSET, self.offset + h * 60))
            self._set(new)
        return cb

    def shift_day(self, d: int):
        def cb():
            new = max(TRAVEL_MIN_OFFSET, min(TRAVEL_MAX_OFFSET, self.offset + d * 1440))
            self._set(new)
        return cb

    def to_present(self) -> None:
        self._set(0)

    def _set(self, offset: int) -> None:
        if offset == self.offset:
            return
        self.offset = offset
        self.slider_pos = -offset / abs(TRAVEL_MIN_OFFSET)
        self.state().offset_min = offset
        self.state().stats["times_traveled"] += 1
        play("whoosh" if offset < 0 else "whoosh_rev", 0.6)

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
            elif event.key == pygame.K_LEFT:
                self._set(max(TRAVEL_MIN_OFFSET, self.offset - 60))
            elif event.key == pygame.K_RIGHT:
                self._set(min(TRAVEL_MAX_OFFSET, self.offset + 60))
            elif event.key == pygame.K_DOWN:
                self._set(max(TRAVEL_MIN_OFFSET, self.offset - 1440))
            elif event.key == pygame.K_UP:
                self._set(min(TRAVEL_MAX_OFFSET, self.offset + 1440))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.slider_rect.collidepoint(event.pos):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            x = max(self.slider_rect.x, min(self.slider_rect.right, event.pos[0]))
            v = (x - self.slider_rect.x) / self.slider_rect.w
            self._set(-int(v * abs(TRAVEL_MIN_OFFSET) / 60) * 60)

    def close(self) -> None:
        play("whoosh_rev", 0.5)
        self.app.pop()

    def update(self, dt: float) -> None:
        mouse = self.app.mouse()
        for b in self.buttons:
            b.update(dt, mouse)

    def draw(self, surface: pygame.Surface) -> None:
        gp = self.app.gameplay
        dim = pygame.Surface((DESIGN_W, DESIGN_H))
        dim.fill((2, 4, 10))
        dim.set_alpha(215)
        surface.blit(dim, (0, 0))
        tr = self.app.tr
        lang = self.app.settings.language
        state = gp.state
        # swirling clock backdrop
        cx, cy = DESIGN_W // 2, 320
        t = pygame.time.get_ticks() / 1000
        for i in range(3):
            r = 180 + i * 40
            pts = []
            for k in range(64):
                a = t * (0.5 + i * 0.2) + k / 64 * math.tau
                rr = r + 8 * math.sin(a * 5 + t)
                pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
            pygame.draw.lines(surface, (40 + i * 20, 60 + i * 20, 110), True, pts, 1)
        # observed datetime
        dt = world_datetime(state.day, state.minutes, self.offset)
        draw_text(surface, tr.t("tt.title"), (cx, 90), size=40, kind="serif_bold",
                  color=(245, 226, 170), align="center", glow=(212, 175, 55), glow_radius=2)
        draw_text(surface, tr.t("tt.observing"), (cx, 160), size=18,
                  color=(150, 160, 185), align="center", shadow=False)
        date_txt = fmt_date_short(dt, lang)
        clock_txt = fmt_clock(dt.hour * 60 + dt.minute)
        draw_text(surface, f"{date_txt}", (cx, 195), size=44, kind="serif_bold",
                  color=(240, 240, 245), align="center", shadow=False)
        draw_text(surface, clock_txt, (cx, 250), size=58, kind="serif_bold",
                  color=(245, 226, 170), align="center", shadow=False)
        # range labels
        min_dt = world_datetime(state.day, state.minutes, TRAVEL_MIN_OFFSET)
        max_dt = world_datetime(state.day, state.minutes, 0)
        draw_text(surface, fmt_date_short(min_dt, lang), (cx - 300, 395), size=16,
                  color=(110, 120, 150), align="center", shadow=False)
        draw_text(surface, tr.t("tt.present"), (cx + 300, 395), size=16,
                  color=(110, 120, 150), align="center", shadow=False)
        # slider
        self.slider_rect = pygame.Rect(cx - 280, 420, 560, 16)
        pygame.draw.rect(surface, (30, 36, 56), self.slider_rect, border_radius=8)
        filled = pygame.Rect(self.slider_rect.x, self.slider_rect.y,
                             int(self.slider_rect.w * self.slider_pos), 16)
        pygame.draw.rect(surface, (212, 175, 55), filled, border_radius=8)
        knob_x = self.slider_rect.x + int(self.slider_rect.w * self.slider_pos)
        pygame.draw.circle(surface, (240, 240, 240), (knob_x, self.slider_rect.centery), 12)
        pygame.draw.circle(surface, (70, 80, 110), (knob_x, self.slider_rect.centery), 12, 2)
        for b in self.buttons:
            b.draw(surface)
        draw_text(surface, tr.t("tt.hint"), (cx, 630), size=15, color=(110, 120, 150),
                  align="center", shadow=False)
        draw_text(surface, tr.t("tt.close"), (cx, 656), size=15, color=(140, 150, 175),
                  align="center", shadow=False)


# ------------------------------------------------------------- notebook ----
class NotebookScene(OverlayScene):
    TABS = ["clues", "witnesses", "postcards", "case"]

    def on_enter(self, **kwargs) -> None:
        self.tab = 0
        self.scroll = 0
        self.selected_postcard = None

    def state(self):
        return self.app.gameplay.state

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
            elif event.key == pygame.K_LEFT:
                self.tab = (self.tab - 1) % 4
                self.scroll = 0
            elif event.key == pygame.K_RIGHT:
                self.tab = (self.tab + 1) % 4
                self.scroll = 0
            elif event.key == pygame.K_DOWN:
                self.scroll += 1
            elif event.key == pygame.K_UP:
                self.scroll = max(0, self.scroll - 1)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.tab_rects):
                if rect.collidepoint(event.pos):
                    self.tab = i
                    self.scroll = 0
                    play("click")
                    return
            # postcard click
            if self.tab == 2:
                for pc_id, rect in self.pc_rects:
                    if rect.collidepoint(event.pos):
                        self.selected_postcard = pc_id
                        return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if event.button == 4:
                self.scroll = max(0, self.scroll - 1)
            else:
                self.scroll += 1

    def close(self) -> None:
        play("notebook")
        self.app.pop()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        dim = pygame.Surface((DESIGN_W, DESIGN_H))
        dim.fill((8, 10, 18))
        dim.set_alpha(215)
        surface.blit(dim, (0, 0))
        tr = self.app.tr
        lang = self.app.settings.language
        state = self.state()
        panel = Panel(pygame.Rect(180, 70, 920, 590), tr.t("notebook.title"), 34)
        panel.draw(surface)
        # tabs
        self.tab_rects = []
        labels = [tr.t("notebook.tab_clues"), tr.t("notebook.tab_witnesses"),
                  tr.t("notebook.tab_postcards"), tr.t("notebook.tab_case")]
        for i, lab in enumerate(labels):
            rect = pygame.Rect(210 + i * 222, 130, 210, 38)
            self.tab_rects.append(rect)
            active = i == self.tab
            bg = (60, 50, 22) if active else (28, 34, 52)
            pygame.draw.rect(surface, bg, rect, border_radius=8)
            pygame.draw.rect(surface, (212, 175, 55) if active else (60, 72, 108),
                             rect, width=2, border_radius=8)
            draw_text(surface, lab, (rect.centerx, rect.centery - 11), size=19,
                      color=(245, 226, 170) if active else (180, 188, 205),
                      align="center", shadow=False)
        # content
        y = 185 - self.scroll * 64
        if self.tab == 0:
            if not state.clues:
                draw_text(surface, tr.t("notebook.empty_clues"), (640, 300), size=20,
                          color=(150, 160, 185), align="center", shadow=False)
            for cid in state.clues:
                clue = get_clue(cid)
                name = clue.name.get(lang, clue.name_ru)
                if lang not in ("ru", "en"):
                    name = self.app.tr.tr_text(clue.name_ru)
                desc = clue.desc.get(lang, clue.desc_ru)
                if lang not in ("ru", "en"):
                    desc = self.app.tr.tr_text(clue.desc_ru)
                found_day = state.clue_found_day.get(cid, state.day)
                from ..game.time import fmt_date_short, game_date
                fdate = fmt_date_short(game_date(found_day), lang)
                draw_text(surface, "◆ " + name, (230, y), size=21, kind="sans_bold",
                          color=(245, 226, 170), shadow=False)
                draw_text(surface, tr.t("notebook.found", date=fdate), (1040, y),
                          size=14, color=(130, 140, 165), align="right", shadow=False)
                draw_wrapped(surface, desc, (248, y + 28), 830, size=16,
                             color=(200, 208, 224), line_spacing=4)
                draw_text(surface, f"{tr.t('notebook.reward_label')}: ${clue.reward:.0f}",
                          (1040, y + 52), size=14, color=(150, 180, 130), align="right",
                          shadow=False)
                y += 86
        elif self.tab == 1:
            if not state.witnesses_met:
                draw_text(surface, tr.t("notebook.empty_witnesses"), (640, 300), size=20,
                          color=(150, 160, 185), align="center", shadow=False)
            for wid in state.witnesses_met:
                from ..game.witnesses import WITNESSES
                w = WITNESSES.get(wid)
                if not w:
                    continue
                name = w["name"].get(lang, w["name"]["ru"])
                desc = w["desc"].get(lang, w["desc"]["ru"])
                draw_text(surface, "● " + name, (230, y), size=21, kind="sans_bold",
                          color=(200, 215, 235), shadow=False)
                draw_wrapped(surface, desc, (248, y + 28), 830, size=16,
                             color=(190, 198, 216), line_spacing=4)
                y += 76
        elif self.tab == 2:
            if not state.postcards:
                draw_text(surface, tr.t("notebook.empty_postcards"), (640, 300), size=20,
                          color=(150, 160, 185), align="center", shadow=False)
            self.pc_rects = []
            for pc_id in state.postcards:
                pc = next((p for p in POSTCARDS if p["id"] == pc_id), None)
                if pc is None:
                    continue
                rect = pygame.Rect(230, y, 820, 44)
                self.pc_rects.append((pc_id, rect))
                pygame.draw.rect(surface, (30, 36, 54), rect, border_radius=8)
                pygame.draw.rect(surface, (90, 100, 130), rect, width=1, border_radius=8)
                title = pc["title"].get(lang, pc["title"]["ru"])
                draw_text(surface, "✉ " + title, (248, y + 10), size=19,
                          color=(230, 235, 245), shadow=False)
                if self.selected_postcard == pc_id:
                    txt = pc["text"].get(lang, pc["text"]["ru"])
                    draw_wrapped(surface, txt, (248, y + 52), 800, size=16,
                                 color=(205, 212, 230), line_spacing=4)
                    y += 60
                y += 52
        elif self.tab == 3:
            days = state.days_left
            if days > 0:
                draw_text(surface, tr.t("notebook.case_days_left", n=days), (230, y),
                          size=22, kind="sans_bold", color=(230, 190, 130), shadow=False)
            else:
                draw_text(surface, tr.t("notebook.case_over"), (230, y), size=22,
                          kind="sans_bold", color=(240, 120, 110), shadow=False)
            y += 46
            draw_text(surface, tr.t("notebook.support"), (230, y), size=18,
                      color=(190, 198, 216), shadow=False)
            bar = ProgressBar(pygame.Rect(420, y + 3, 220, 14), state.support / 100.0,
                              color=(90, 170, 120))
            bar.draw(surface)
            draw_text(surface, f"{int(state.support)}%", (660, y), size=18,
                      color=(150, 180, 130), shadow=False)
            y += 56
            draw_text(surface, tr.t("notebook.tasks"), (230, y), size=20,
                      kind="sans_bold", color=(245, 226, 170), shadow=False)
            y += 34
            tasks = list(state.tasks.items())
            if not tasks:
                draw_text(surface, tr.t("notebook.no_tasks"), (248, y), size=17,
                          color=(140, 150, 175), shadow=False)
            for tid, status in tasks:
                label_key = f"notebook.task_{tid}"
                label = tr.t(label_key)
                if label == label_key:      # no translation for this task id
                    label = tid
                status_txt = tr.t("notebook.task_done") if status == "done" \
                    else tr.t("notebook.task_active")
                color = (140, 200, 140) if status == "done" else (230, 200, 120)
                draw_text(surface, ("✔ " if status == "done" else "• ") + label,
                          (248, y), size=17, color=color, shadow=False)
                draw_text(surface, status_txt, (1040, y), size=15, color=color,
                          align="right", shadow=False)
                y += 30
            y += 10
            draw_text(surface, tr.t("notebook.note_title"), (230, y), size=20,
                      kind="sans_bold", color=(245, 226, 170), shadow=False)
            y += 34
            for note in state.notebook_notes:
                title = note["title"].get(lang, note["title"]["ru"])
                text = note["text"].get(lang, note["text"]["ru"])
                draw_text(surface, "— " + title, (248, y), size=17, kind="sans_bold",
                          color=(210, 218, 235), shadow=False)
                draw_wrapped(surface, text, (270, y + 24), 810, size=15,
                             color=(175, 184, 205), line_spacing=4)
                y += 58
        draw_text(surface, "← → — " + tr.t("misc.back"), (200, 630), size=14,
                  color=(110, 120, 150), shadow=False)
        draw_text(surface, "Esc", (1080, 630), size=14, color=(110, 120, 150),
                  align="right", shadow=False)


# ---------------------------------------------------------------- pause ----
class PauseScene(OverlayScene):
    def on_enter(self, **kwargs) -> None:
        cx = DESIGN_W // 2
        self.buttons = [
            Button(pygame.Rect(cx - 160, 180, 320, 52), self.app.tr.t("pause.continue"),
                   self.close, style="gold", size=24),
            Button(pygame.Rect(cx - 160, 248, 320, 52), self.app.tr.t("pause.save_game"),
                   self.save, size=24),
            Button(pygame.Rect(cx - 160, 316, 320, 52), self.app.tr.t("pause.settings"),
                   self.settings, size=24),
            Button(pygame.Rect(cx - 160, 384, 320, 52), self.app.tr.t("pause.main_menu"),
                   self.main_menu, size=24),
            Button(pygame.Rect(cx - 160, 452, 320, 52), self.app.tr.t("pause.exit_game"),
                   self.quit_game, style="danger", size=24),
        ]
        self.notice = ""

    def close(self) -> None:
        play("back")
        self.app.pop()

    def save(self) -> None:
        from .saves_menu import SavesScene
        self.app.push(SavesScene(self.app, mode="save"))

    def settings(self) -> None:
        from .settings_menu import SettingsScene
        self.app.push(SettingsScene(self.app, from_menu=False))

    def main_menu(self) -> None:
        from .splash import MainMenuScene
        gp = self.app.gameplay
        if gp:
            gp.autosave()
        play("back")
        self.app.reset(MainMenuScene(self.app))

    def quit_game(self) -> None:
        gp = self.app.gameplay
        if gp:
            gp.autosave()
        self.app.quit()

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()

    def update(self, dt: float) -> None:
        mouse = self.app.mouse()
        for b in self.buttons:
            b.update(dt, mouse)

    def draw(self, surface: pygame.Surface) -> None:
        dim = pygame.Surface((DESIGN_W, DESIGN_H))
        dim.fill((4, 6, 12))
        dim.set_alpha(190)
        surface.blit(dim, (0, 0))
        tr = self.app.tr
        draw_text(surface, tr.t("pause.title"), (640, 110), size=46, kind="serif_bold",
                  color=(240, 240, 245), align="center", glow=(212, 175, 55), glow_radius=2)
        for b in self.buttons:
            b.draw(surface)
        if self.notice:
            draw_text(surface, self.notice, (640, 540), size=18, color=(150, 210, 150),
                      align="center", shadow=False)
        gp = self.app.gameplay
        if gp:
            from ..game.time import fmt_clock
            st = gp.state
            draw_text(surface, f"{st.day}/7 · {fmt_clock(st.minutes)} · ${int(st.money)}",
                      (640, 560), size=16, color=(140, 150, 175), align="center", shadow=False)


# ------------------------------------------------------------------ shop ---
class ShopScene(OverlayScene):
    ITEMS = [
        ("sandwich", 6, "shop.sandwich"),
        ("lunch", 12, "shop.lunch"),
        ("coffee", 5, "shop.coffee"),
        ("medicine", MEDICINE_PRICE, "shop.medicine"),
    ]

    def on_enter(self, **kwargs) -> None:
        cx = DESIGN_W // 2
        self.buttons: list[Button] = []
        self.exit_btn = Button(pygame.Rect(cx - 100, 600, 200, 46),
                               self.app.tr.t("shop.exit"), self.close, style="gold", size=20)
        self.notice = ""
        self.notice_color = (200, 205, 220)
        for i, (item_id, price, label_key) in enumerate(self.ITEMS):
            b = Button(pygame.Rect(cx - 220, 190 + i * 74, 440, 58), "", self.buy(item_id),
                       style="default", size=20)
            self.buttons.append((b, item_id, price, label_key))

    def state(self):
        return self.app.gameplay.state

    def buy(self, item_id: str):
        def cb():
            state = self.state()
            price = next(p for i, p, _ in self.ITEMS if i == item_id)
            if state.money < price:
                play("error")
                self.notice = self.app.tr.t("shop.not_enough")
                self.notice_color = (230, 130, 120)
                return
            state.money -= price
            tr = self.app.tr
            if item_id == "sandwich":
                state.hunger = min(100.0, state.hunger + 55)
                state.stats["meals"] += 1
                play("eat")
            elif item_id == "lunch":
                state.hunger = min(100.0, state.hunger + 85)
                state.stats["meals"] += 1
                play("eat")
            elif item_id == "coffee":
                state.fatigue = max(0.0, state.fatigue - 15)
                state.stats["coffees"] += 1
                play("confirm")
            elif item_id == "medicine":
                state.sick = False
                state.health = min(100.0, state.health + 60)
                play("confirm")
            self.notice = tr.t("shop.bought", item=tr.t(self._label_key(item_id)))
            self.notice_color = (150, 210, 150)
        return cb

    def _label_key(self, item_id: str) -> str:
        for i, p, k in self.ITEMS:
            if i == item_id:
                return k
        return ""

    def close(self) -> None:
        play("back")
        self.app.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        for b, _i, _p, _k in self.buttons:
            if b.handle(event):
                return
        self.exit_btn.handle(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()

    def update(self, dt: float) -> None:
        mouse = self.app.mouse()
        for b, _i, _p, _k in self.buttons:
            b.update(dt, mouse)
        self.exit_btn.update(dt, mouse)

    def draw(self, surface: pygame.Surface) -> None:
        dim = pygame.Surface((DESIGN_W, DESIGN_H))
        dim.fill((6, 8, 16))
        dim.set_alpha(220)
        surface.blit(dim, (0, 0))
        tr = self.app.tr
        draw_text(surface, tr.t("shop.title"), (640, 90), size=40, kind="serif_bold",
                  color=(245, 226, 170), align="center", glow=(212, 175, 55), glow_radius=2)
        draw_text(surface, tr.t("shop.welcome"), (640, 150), size=18, color=(170, 180, 205),
                  align="center", shadow=False)
        for b, item_id, price, label_key in self.buttons:
            b.draw(surface)
            label = tr.t(label_key)
            draw_text(surface, label, (b.rect.x + 20, b.rect.centery - 11), size=20,
                      shadow=False)
        draw_text(surface, tr.t("shop.money", money=int(self.state().money)),
                  (640, 180), size=20, color=(245, 226, 170), align="center", shadow=False)
        if self.notice:
            draw_text(surface, self.notice, (640, 560), size=19, color=self.notice_color,
                      align="center", shadow=False)
        self.exit_btn.draw(surface)


# ------------------------------------------------------------------ bank ---
class BankScene(OverlayScene):
    AMOUNTS = [50, 100, 200, 500]

    def on_enter(self, **kwargs) -> None:
        self.mode = "main"
        self.buttons: list[Button] = []
        self.notice = ""
        self.notice_color = (200, 205, 220)
        self.rebuild()

    def state(self):
        return self.app.gameplay.state

    def rebuild(self) -> None:
        self.buttons = []
        cx = DESIGN_W // 2
        tr = self.app.tr
        if self.mode == "main":
            self.buttons.append(Button(pygame.Rect(cx - 180, 220, 360, 50),
                                       tr.t("bank.take_loan"), self.take_mode, size=22))
            self.buttons.append(Button(pygame.Rect(cx - 180, 288, 360, 50),
                                       tr.t("bank.repay_loan"), self.repay_mode, size=22))
        elif self.mode == "take":
            for i, amt in enumerate(self.AMOUNTS):
                b = Button(pygame.Rect(cx - 220 + (i % 2) * 230, 230 + (i // 2) * 60, 210, 50),
                           f"${amt}", self.take(amt), size=24)
                self.buttons.append(b)
            self.buttons.append(Button(pygame.Rect(cx - 100, 370, 200, 44),
                                       tr.t("misc.back"), self.back, style="ghost", size=20))
        elif self.mode == "repay":
            loans = self.state().loans
            if not loans:
                self.buttons.append(Button(pygame.Rect(cx - 100, 300, 200, 44),
                                           tr.t("misc.back"), self.back, style="ghost", size=20))
            for i, loan in enumerate(loans):
                total = loan_due_total(loan)
                b = Button(pygame.Rect(cx - 220, 230 + i * 64, 440, 52),
                           f"${total:.0f}", self.repay(loan), size=22)
                self.buttons.append(b)
        self.exit_btn = Button(pygame.Rect(cx - 100, 600, 200, 46),
                               tr.t("bank.thanks"), self.close, style="gold", size=20)

    def take_mode(self) -> None:
        play("click")
        self.mode = "take"
        self.rebuild()

    def repay_mode(self) -> None:
        play("click")
        self.mode = "repay"
        self.rebuild()

    def back(self) -> None:
        play("back")
        self.mode = "main"
        self.rebuild()

    def take(self, amount: int):
        def cb():
            state = self.state()
            loan = take_loan(state, float(amount), state.total_min)
            state.stats["loans_taken"] += 1
            play("coin")
            self.notice = self.app.tr.t("bank.loan_taken", amount=amount)
            self.notice_color = (150, 210, 150)
            self.mode = "main"
            self.rebuild()
        return cb

    def repay(self, loan: dict):
        def cb():
            state = self.state()
            total = loan_due_total(loan)
            if state.money < total:
                play("error")
                self.notice = self.app.tr.t("bank.not_enough")
                self.notice_color = (230, 130, 120)
                return
            repay_loan(state, loan)
            play("coin")
            self.notice = self.app.tr.t("bank.loan_repaid")
            self.notice_color = (150, 210, 150)
            self.mode = "main"
            self.rebuild()
        return cb

    def close(self) -> None:
        play("back")
        self.app.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            if b.handle(event):
                return
        self.exit_btn.handle(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()

    def update(self, dt: float) -> None:
        mouse = self.app.mouse()
        for b in self.buttons:
            b.update(dt, mouse)
        self.exit_btn.update(dt, mouse)

    def draw(self, surface: pygame.Surface) -> None:
        dim = pygame.Surface((DESIGN_W, DESIGN_H))
        dim.fill((6, 8, 16))
        dim.set_alpha(220)
        surface.blit(dim, (0, 0))
        tr = self.app.tr
        draw_text(surface, tr.t("bank.title"), (640, 80), size=40, kind="serif_bold",
                  color=(245, 226, 170), align="center", glow=(212, 175, 55), glow_radius=2)
        draw_text(surface, tr.t("bank.welcome"), (640, 140), size=18, color=(170, 180, 205),
                  align="center", shadow=False)
        draw_text(surface, tr.t("shop.money", money=int(self.state().money)),
                  (640, 172), size=20, color=(245, 226, 170), align="center", shadow=False)
        if self.mode == "take":
            draw_text(surface, tr.t("bank.choose"), (640, 210), size=17,
                      color=(150, 160, 185), align="center", shadow=False)
            draw_text(surface, tr.t("bank.interest_note"), (640, 440), size=16,
                      color=(150, 160, 185), align="center", shadow=False)
        elif self.mode == "repay":
            if not self.state().loans:
                draw_text(surface, tr.t("bank.no_loans"), (640, 260), size=20,
                          color=(150, 160, 185), align="center", shadow=False)
            else:
                for i, loan in enumerate(self.state().loans):
                    left_min = loan["due_min"] - self.state().total_min
                    days = left_min // 1440
                    hours = (left_min % 1440) // 60
                    due_txt = tr.t("bank.due_in", days=days, hours=hours) if left_min > 0 \
                        else tr.t("bank.overdue")
                    draw_text(surface, due_txt, (640, 296 + i * 64), size=16,
                              color=(230, 150, 120) if left_min <= 0 else (150, 160, 185),
                              align="center", shadow=False)
        for b in self.buttons:
            b.draw(surface)
        if self.notice:
            draw_text(surface, self.notice, (640, 560), size=19, color=self.notice_color,
                      align="center", shadow=False)
        self.exit_btn.draw(surface)


# -------------------------------------------------------------- computer ---
class ComputerScene(OverlayScene):
    def on_enter(self, **kwargs) -> None:
        self.input_box = InputBox(pygame.Rect(440, 220, 400, 42),
                                  placeholder=self.app.tr.t("computer.placeholder"),
                                  max_len=40, on_submit=self.search)
        self.result = ""
        self.found = False
        self.search_btn = Button(pygame.Rect(850, 220, 120, 42),
                                 self.app.tr.t("computer.search_btn"), self.do_search,
                                 style="gold", size=20)
        self.close_btn = Button(pygame.Rect(540, 600, 200, 46),
                                self.app.tr.t("computer.close"), self.close,
                                style="default", size=20)

    def state(self):
        return self.app.gameplay.state

    def do_search(self) -> None:
        self.search(self.input_box.text)

    def search(self, query: str) -> None:
        state = self.state()
        q = query.strip().upper().replace(" ", "")
        play("click")
        if q in ("EMIT", "ЕМИТ", "ЕГОР", "ЕГОРМИТИН", "МИТИН", "TIMUROV"):
            if not state.has_clue("database_emit"):
                state.add_clue("database_emit")
                state.clue_found_day["database_emit"] = state.day
                update_stage(state)
                gp = self.app.gameplay
                if gp:
                    gp.on_plot_progress()
                play("clue")
            self.found = True
            self.result = self._dossier()
        else:
            self.found = False
            self.result = self.app.tr.t("computer.no_results", q=query)

    def _dossier(self) -> str:
        lang = self.app.settings.language
        data = {
            "ru": ("ДОСЬЕ: ЕГОР МИТИН (псевдоним — EMIT)\n"
                   "Возраст: 34. Место жительства: Тихореченск, дом на южной окраине.\n"
                   "Судимости: кражи, мелкое хулиганство.\n"
                   "Особые приметы: постоянно носит часы циферблатом внутрь.\n"
                   "Из задержаний: «время идёт ко мне, а не от меня».\n"
                   "23.11.2023, 00:14 — телефон зарегистрирован у базовой станции "
                   "в 200 метрах от дома Соколова. Совпадение? Вряд ли."),
            "en": ("FILE: YEGOR MITIN (alias — EMIT)\n"
                   "Age: 34. Residence: Tikhorchensk, house on the southern edge.\n"
                   "Criminal record: theft, petty hooliganism.\n"
                   "Distinctive habit: always wears his watch with the face inward.\n"
                   "From arrests: “time comes to me, not away from me”.\n"
                   "23.11.2023, 00:14 — phone registered at a cell tower "
                   "200 metres from Sokolov's house. A coincidence? Unlikely."),
        }
        t = data.get(lang, data["ru"])
        if lang not in ("ru", "en"):
            t = self.app.tr.tr_text(data["ru"])
        return t

    def close(self) -> None:
        play("back")
        self.app.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.input_box.handle(event):
            return
        if self.search_btn.handle(event):
            return
        if self.close_btn.handle(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()

    def update(self, dt: float) -> None:
        mouse = self.app.mouse()
        self.input_box.update(dt, mouse)
        self.search_btn.update(dt, mouse)
        self.close_btn.update(dt, mouse)

    def draw(self, surface: pygame.Surface) -> None:
        dim = pygame.Surface((DESIGN_W, DESIGN_H))
        dim.fill((4, 8, 14))
        dim.set_alpha(230)
        surface.blit(dim, (0, 0))
        tr = self.app.tr
        draw_text(surface, tr.t("computer.title"), (640, 80), size=40, kind="serif_bold",
                  color=(140, 210, 160), align="center", glow=(60, 160, 100), glow_radius=2)
        draw_text(surface, tr.t("computer.welcome"), (640, 140), size=17,
                  color=(150, 170, 165), align="center", shadow=False)
        draw_text(surface, tr.t("computer.search"), (440, 190), size=18,
                  color=(190, 210, 200), shadow=False)
        self.input_box.draw(surface)
        self.search_btn.draw(surface)
        if self.result:
            rect = pygame.Rect(340, 300, 600, 250)
            pygame.draw.rect(surface, (10, 24, 18), rect, border_radius=10)
            pygame.draw.rect(surface, (50, 110, 80), rect, width=2, border_radius=10)
            if self.found:
                draw_text(surface, tr.t("computer.results_title"), (370, 318), size=20,
                          kind="sans_bold", color=(140, 210, 160), shadow=False)
            draw_wrapped(surface, self.result, (370, 352), 540, size=17,
                         color=(190, 220, 200), line_spacing=8)
        self.close_btn.draw(surface)


# ------------------------------------------------------------------ info ---
class InfoScene(OverlayScene):
    def __init__(self, app, prop=None, custom_title=None, custom_text=None) -> None:
        super().__init__(app)
        self.prop = prop
        self.custom_title = custom_title
        self.custom_text = custom_text
        self.close_btn = None

    def on_enter(self, **kwargs) -> None:
        self.close_btn = Button(pygame.Rect(540, 600, 200, 46),
                                self.app.tr.t("misc.close"), self.close,
                                style="gold", size=20)

    def state(self):
        return self.app.gameplay.state

    def _resolve(self, d: dict) -> str:
        lang = self.app.settings.language
        t = d.get(lang)
        if t is None:
            t = d.get("en") or d.get("ru") or ""
            if lang not in ("ru", "en"):
                t = self.app.tr.tr_text(d.get("ru", t))
        return t

    def close(self) -> None:
        play("back")
        self.app.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.close_btn and self.close_btn.handle(event):
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_e,
                                                          pygame.K_RETURN):
            self.close()

    def update(self, dt: float) -> None:
        if self.close_btn:
            self.close_btn.update(dt, self.app.mouse())

    def draw(self, surface: pygame.Surface) -> None:
        dim = pygame.Surface((DESIGN_W, DESIGN_H))
        dim.fill((4, 6, 12))
        dim.set_alpha(190)
        surface.blit(dim, (0, 0))
        tr = self.app.tr
        state = self.state()
        if self.custom_title is not None:
            title = self._resolve(self.custom_title)
            text = self._resolve(self.custom_text)
        elif self.prop is not None:
            title = self._resolve(self.prop.title)
            text = self._resolve(self.prop.text)
        else:
            title, text = "", ""
        panel = Panel(pygame.Rect(290, 160, 700, 400), title, 30)
        panel.draw(surface)
        draw_wrapped(surface, text, (330, 260), 620, size=21, color=(225, 231, 244),
                     line_spacing=10)
        clue_id = self.prop.clue_id if self.prop is not None else None
        if clue_id and state.has_clue(clue_id):
            clue = get_clue(clue_id)
            name = clue.name.get(self.app.settings.language, clue.name_ru)
            draw_text(surface, f"✦ {name} — {tr.t('notebook.reward_label')} ${clue.reward:.0f}",
                      (640, 480), size=18, color=(245, 226, 170), align="center", shadow=False)
        self.close_btn.draw(surface)


# -------------------------------------------------------------- postcard ---
class PostcardScene(OverlayScene):
    def __init__(self, app, postcards: list) -> None:
        super().__init__(app)
        self.queue = list(postcards)
        self.current = self.queue.pop(0)

    def on_enter(self, **kwargs) -> None:
        self.age = 0.0
        self.next_btn = Button(pygame.Rect(540, 600, 200, 46), "", self.advance,
                               style="gold", size=20)

    def advance(self) -> None:
        play("notebook")
        if self.queue:
            self.current = self.queue.pop(0)
            self.age = 0.0
        else:
            self.app.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.next_btn.handle(event):
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_e,
                                                          pygame.K_RETURN):
            self.advance()

    def update(self, dt: float) -> None:
        self.age += dt
        self.next_btn.update(dt, self.app.mouse())

    def draw(self, surface: pygame.Surface) -> None:
        dim = pygame.Surface((DESIGN_W, DESIGN_H))
        dim.fill((6, 6, 10))
        dim.set_alpha(210)
        surface.blit(dim, (0, 0))
        tr = self.app.tr
        lang = self.app.settings.language
        draw_text(surface, tr.t("postcard.new"), (640, 90), size=24,
                  color=(245, 226, 170), align="center", shadow=False)
        # postcard
        card = pygame.Rect(340, 140, 600, 420)
        pygame.draw.rect(surface, (238, 232, 214), card, border_radius=8)
        pygame.draw.rect(surface, (170, 150, 110), card, width=2, border_radius=8)
        pygame.draw.line(surface, (200, 185, 150), (340, 350), (940, 350), 1)
        title = self.current["title"].get(lang, self.current["title"]["ru"])
        text = self.current["text"].get(lang, self.current["text"]["ru"])
        if lang not in ("ru", "en"):
            title = self.app.tr.tr_text(self.current["title"]["ru"])
            text = self.app.tr.tr_text(self.current["text"]["ru"])
        draw_text(surface, title, (640, 170), size=24, kind="sans_bold", color=(80, 60, 40),
                  align="center", shadow=False)
        draw_wrapped(surface, text, (380, 230), 520, size=22, color=(70, 55, 40),
                     line_spacing=10)
        # stamp
        stamp = pygame.Rect(840, 160, 56, 66)
        pygame.draw.rect(surface, (150, 60, 50), stamp, border_radius=4)
        pygame.draw.rect(surface, (200, 90, 70), stamp, width=2, border_radius=4)
        draw_text(surface, "TIME", (868, 180), size=13, kind="sans_bold",
                  color=(245, 226, 170), align="center", shadow=False)
        # handwriting flourish
        for i in range(3):
            x = 380 + i * 60
            pygame.draw.arc(surface, (120, 100, 70), (x, 420 + (i % 2) * 30, 40, 24),
                            0, 3.4, 2)
        self.next_btn.label = tr.t("misc.ok") if not self.queue else tr.t("misc.continue")
        self.next_btn.draw(surface)


# ------------------------------------------------------------- confirm -----
class ConfirmScene(OverlayScene):
    def __init__(self, app, text: str, on_yes=None) -> None:
        super().__init__(app)
        self.text = text
        self.on_yes = on_yes

    def on_enter(self, **kwargs) -> None:
        cx = DESIGN_W // 2
        self.yes_btn = Button(pygame.Rect(cx - 170, 400, 160, 48),
                              self.app.tr.t("dialogue.yes"), self.yes, style="gold", size=22)
        self.no_btn = Button(pygame.Rect(cx + 10, 400, 160, 48),
                             self.app.tr.t("dialogue.no"), self.no, style="ghost", size=22)

    def yes(self) -> None:
        play("confirm")
        cb = self.on_yes
        self.app.pop()
        if cb:
            cb()

    def no(self) -> None:
        play("back")
        self.app.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.yes_btn.handle(event):
            return
        if self.no_btn.handle(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.no()
            elif event.key in (pygame.K_RETURN, pygame.K_e):
                self.yes()

    def update(self, dt: float) -> None:
        mouse = self.app.mouse()
        self.yes_btn.update(dt, mouse)
        self.no_btn.update(dt, mouse)

    def draw(self, surface: pygame.Surface) -> None:
        dim = pygame.Surface((DESIGN_W, DESIGN_H))
        dim.fill((4, 6, 12))
        dim.set_alpha(200)
        surface.blit(dim, (0, 0))
        panel = Panel(pygame.Rect(340, 200, 600, 280))
        panel.draw(surface)
        draw_wrapped(surface, self.text, (380, 250), 520, size=21, color=(230, 235, 245),
                     line_spacing=8, align="center")
        self.yes_btn.draw(surface)
        self.no_btn.draw(surface)
