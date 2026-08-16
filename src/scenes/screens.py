"""Full-screen sequences: evening news, day briefing, game over, chase,
true ending."""
from __future__ import annotations

import math

import pygame

from ..audio import play, play_theme, stop_theme
from ..config import DESIGN_H, DESIGN_W, UTILITIES_PER_DAY
from ..core.scene import Scene
from ..game.clues import get as get_clue
from ..game.economy import pay_utilities, reward_for_yesterday
from ..game.newsgen import ANCHOR, apply_news, generate_news
from ..game.story import update_stage
from ..game.time import fmt_clock
from ..render.background import draw_menu_bg
from ..render.fx import ScreenFade
from ..render.text import draw_text, draw_wrapped
from ..render.ui import Button, Panel, ProgressBar


def _gp(app):
    return app.gameplay


# ------------------------------------------------------------------ news ---
class NewsScene(Scene):
    def on_enter(self, **kwargs) -> None:
        gp = _gp(self.app)
        if gp is None:
            self.app.pop()
            return
        self.gp = gp
        state = gp.state
        for_day = state.pending_news.get("for_day", state.day - 1)
        self.news = generate_news(state, for_day)
        self.support_delta = apply_news(state, self.news)
        self.age = 0.0
        self.chars = 0.0
        # utilities were already charged at the midnight rollover
        u = state.pending_news.get("utilities") if isinstance(state.pending_news, dict) else None
        self.utility_ok = u["paid"] if u else None
        state.pending_news = {}
        play("news")
        self.continue_btn = Button(pygame.Rect(540, 620, 200, 46),
                                   self.app.tr.t("news.continue"), self.close,
                                   style="gold", size=20)

    def close(self) -> None:
        play("click")
        gp = _gp(self.app)
        if gp is not None:
            gp.resume()
        self.app.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.continue_btn.handle(event):
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_e,
                                                          pygame.K_RETURN):
            self.close()
        elif event.type == pygame.KEYDOWN and self.chars < 10 ** 6:
            self.chars = 10 ** 6

    def update(self, dt: float) -> None:
        self.age += dt
        self.chars += dt * 40
        self.continue_btn.update(dt, self.app.mouse())
        if self.age > 4.5 and self.chars >= 10 ** 6:
            pass

    def draw(self, surface: pygame.Surface) -> None:
        # TV room
        surface.fill((10, 10, 14))
        # TV frame
        tv = pygame.Rect(240, 90, 800, 470)
        pygame.draw.rect(surface, (30, 30, 38), tv.inflate(40, 40), border_radius=16)
        pygame.draw.rect(surface, (10, 10, 14), tv, border_radius=12)
        pygame.draw.rect(surface, (60, 62, 74), tv, width=2, border_radius=12)
        tr = self.app.tr
        lang = self.app.settings.language
        # anchor
        anchor_img = self.app.sprites.portrait(77)
        surface.blit(anchor_img, (280, 120))
        draw_text(surface, tr.t("news.anchor"), (400, 140), size=24, kind="sans_bold",
                  color=(240, 240, 245), shadow=False)
        pygame.draw.line(surface, (90, 100, 130), (280, 330), (1000, 330), 1)
        headline = self.news["headline"].get(lang, self.news["headline"]["ru"])
        if lang not in ("ru", "en"):
            headline = self.app.tr.tr_text(self.news["headline"]["ru"])
        draw_wrapped(surface, headline, (400, 350), 560, size=26, kind="sans_bold",
                     color=(245, 226, 170), line_spacing=6)
        body = self.news["body"].get(lang, self.news["body"]["ru"])
        if lang not in ("ru", "en"):
            body = self.app.tr.tr_text(self.news["body"]["ru"])
        shown = body[: int(self.chars)]
        draw_wrapped(surface, shown, (280, 420), 720, size=19, color=(210, 218, 232),
                     line_spacing=7)
        # ticker
        tick = pygame.Rect(240, 560, 800, 36)
        pygame.draw.rect(surface, (18, 20, 28), tick, border_radius=8)
        clue_txt = tr.t("news.clues_found", n=self.news["clues_today"])
        delta = self.support_delta
        if delta > 0:
            sup_txt = tr.t("news.support_up", n=delta)
        elif delta < 0:
            sup_txt = tr.t("news.support_down", n=-delta)
        else:
            sup_txt = tr.t("news.support_neutral")
        if self.utility_ok is True:
            util_txt = tr.t("news.utilities_paid")
        elif self.utility_ok is False:
            util_txt = tr.t("news.utilities_debt")
        else:
            util_txt = ""
        draw_text(surface, f"{clue_txt}   {sup_txt}   {util_txt}", (640, tick.centery - 12),
                  size=17, color=(200, 208, 225), align="center", shadow=False)
        self.continue_btn.draw(surface)
        # subtle CRT scanlines
        for y in range(90, 560, 4):
            pygame.draw.line(surface, (255, 255, 255), (240, y), (1040, y), 1)
            surface.set_at((240, y), (30, 30, 40))


# -------------------------------------------------------------- briefing ----
class BriefingScene(Scene):
    def on_enter(self, **kwargs) -> None:
        gp = _gp(self.app)
        if gp is None:
            self.app.pop()
            return
        self.gp = gp
        state = gp.state
        self.day = state.day
        self.age = 0.0
        # rewards for clues found yesterday
        self.rewards: list[tuple[str, float]] = []
        total = 0.0
        if self.day > 1:
            for cid, found_day in state.clue_found_day.items():
                if found_day == self.day - 1:
                    clue = get_clue(cid)
                    self.rewards.append((cid, clue.reward))
                    total += clue.reward
            if total > 0:
                state.earn(total, "clues")
        self.total = total
        self.continue_btn = Button(pygame.Rect(540, 600, 200, 46),
                                   self.app.tr.t("misc.continue"), self.close,
                                   style="gold", size=20)
        # autosave at each new day
        gp.autosave()
        play("wake")
        update_stage(state)
        # clear pending flag
        state.pending_briefing = False
        state.flags["briefed_day"] = state.day

    def close(self) -> None:
        play("click")
        gp = _gp(self.app)
        if gp is not None:
            gp.resume()
        self.app.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.continue_btn.handle(event):
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_e,
                                                          pygame.K_RETURN):
            self.close()

    def update(self, dt: float) -> None:
        self.age += dt
        self.continue_btn.update(dt, self.app.mouse())

    def draw(self, surface: pygame.Surface) -> None:
        draw_menu_bg(surface, 0.0, dark=True)
        tr = self.app.tr
        draw_text(surface, tr.t("hud.day", day=self.day, total=7), (640, 130), size=70,
                  kind="serif_bold", color=(245, 226, 170), align="center",
                  glow=(212, 175, 55), glow_radius=3)
        days_left = 7 - self.day
        if days_left > 0:
            draw_text(surface, tr.t("hud.days_left", n=days_left), (640, 220), size=22,
                      color=(190, 160, 130), align="center", shadow=False)
        if self.rewards:
            panel = Panel(pygame.Rect(340, 280, 600, 260), tr.t("gameplay.rewards_title"), 24)
            panel.draw(surface)
            y = 330
            for cid, reward in self.rewards:
                clue = get_clue(cid)
                name = clue.name.get(self.app.settings.language, clue.name_ru)
                draw_text(surface, f"+${reward:.0f}", (900, y), size=20,
                          color=(150, 210, 130), align="right", shadow=False)
                draw_text(surface, "• " + name, (380, y), size=19, color=(225, 231, 244),
                          shadow=False)
                y += 36
            draw_text(surface, tr.t("news.clue_rewards", sum=self.total), (640, 500),
                      size=20, color=(245, 226, 170), align="center", shadow=False)
        else:
            draw_text(surface, tr.t("gameplay.day1_hint"), (640, 300), size=20,
                      color=(170, 180, 205), align="center", shadow=False)
        self.continue_btn.draw(surface)


# ------------------------------------------------------------- game over ---
class GameOverScene(Scene):
    def __init__(self, app, reason: str) -> None:
        super().__init__(app)
        self.reason = reason

    def on_enter(self, **kwargs) -> None:
        play_theme("menu")
        self.age = 0.0
        self.fade = ScreenFade(speed=1.0)
        self.fade.fade_in()
        cx = DESIGN_W // 2
        self.buttons = [
            Button(pygame.Rect(cx - 170, 540, 160, 48), self.app.tr.t("gameover.to_menu"),
                   self.to_menu, style="default", size=20),
            Button(pygame.Rect(cx + 10, 540, 160, 48), self.app.tr.t("gameover.to_load"),
                   self.to_load, style="ghost", size=20),
        ]

    def to_menu(self) -> None:
        from .splash import MainMenuScene
        play("click")
        self.app.reset(MainMenuScene(self.app))

    def to_load(self) -> None:
        from .saves_menu import SavesScene
        play("click")
        self.app.push(SavesScene(self.app, mode="load"))

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.to_menu()

    def update(self, dt: float) -> None:
        self.age += dt
        self.fade.update(dt)
        for b in self.buttons:
            b.update(dt, self.app.mouse())

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((6, 6, 10))
        tr = self.app.tr
        st = _gp(self.app).state if _gp(self.app) else None
        reason = self.reason
        if reason in ("case_closed", "deadline"):
            title = tr.t("gameover.case_closed_title")
            text = tr.t("gameover.case_closed")
        elif reason == "loan":
            title = tr.t("gameover.loan_title")
            text = tr.t("gameover.loan")
        elif reason == "death":
            if st and st.sick:
                text = tr.t("gameover.death_sick")
            else:
                text = tr.t("gameover.death_starved")
            title = tr.t("hud.health").upper()
        else:
            title = tr.t("gameover.case_closed_title")
            text = tr.t("gameover.case_closed")
        # big hourglass-ish title
        draw_text(surface, title, (640, 140), size=64, kind="serif_bold",
                  color=(200, 70, 60), align="center", glow=(200, 40, 30), glow_radius=3)
        draw_wrapped(surface, text, (640, 250), 760, size=23, color=(215, 220, 235),
                     line_spacing=9, align="center")
        if st:
            panel = Panel(pygame.Rect(340, 380, 600, 130), tr.t("gameover.stats_title"), 22)
            panel.draw(surface)
            stats = st.stats
            draw_text(surface, tr.t("gameover.days_used") + f": {st.day}", (380, 430),
                      size=19, color=(220, 226, 240), shadow=False)
            draw_text(surface, tr.t("gameover.clues_found") + f": {stats['clues_total']}",
                      (380, 458), size=19, color=(220, 226, 240), shadow=False)
            draw_text(surface, tr.t("gameover.witnesses") + f": {stats['witnesses_total']}",
                      (780, 430), size=19, color=(220, 226, 240), shadow=False)
            draw_text(surface, tr.t("gameover.money_earned") + f": ${int(stats['money_earned'])}",
                      (780, 458), size=19, color=(220, 226, 240), shadow=False)
        for b in self.buttons:
            b.draw(surface)
        self.fade.draw(surface)


# ---------------------------------------------------------------- chase ----
class ChaseScene(Scene):
    """Cinematic chase: EMIT runs to the warehouse, Mike follows."""

    def on_enter(self, **kwargs) -> None:
        self.t = 0.0
        self.fade = ScreenFade(speed=1.6)
        self.fade.fade_in()
        self.bank = self.app.sprites

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self.t += 0.4

    def update(self, dt: float) -> None:
        self.t += dt
        self.fade.update(dt)
        if self.t > 6.2:
            self.finish()

    def finish(self) -> None:
        play("gunshot")
        self.app.replace_top(EndingScene(self.app))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((14, 14, 20))
        tr = self.app.tr
        cx, cy = DESIGN_W // 2, 360
        # motion blur streaks
        for i in range(14):
            y = cy - 200 + i * 30
            off = math.sin(self.t * 9 + i) * 40
            pygame.draw.line(surface, (40, 44, 60), (cx - 500 + off, y),
                             (cx + 500 + off, y), 2)
        # running figures
        emit = self.bank.character(((36, 36, 44), (28, 28, 36), (214, 172, 134),
                                    (24, 24, 30), 0, 3), dir_name="right")
        mike = self.bank.character(((186, 160, 120), (74, 62, 50), (222, 190, 156),
                                    (52, 42, 30), 1, 0), dir_name="right")
        speed = self.t * 260
        ex = (cx + 120 + speed) % (DESIGN_W + 300) - 150
        mx = (cx - 140 + speed) % (DESIGN_W + 300) - 150
        bob = math.sin(self.t * 14) * 6
        surface.blit(emit, (ex - 16, cy - 30 + bob))
        surface.blit(mike, (mx - 16, cy - 30 - bob))
        draw_text(surface, tr.t("gameplay.chase_line"), (cx, 180), size=30,
                  kind="serif_bold", color=(245, 226, 170), align="center",
                  glow=(212, 175, 55), glow_radius=2)
        draw_text(surface, "…", (cx, 480), size=40, align="center", shadow=False)
        self.fade.draw(surface)


# --------------------------------------------------------------- ending ----
class EndingScene(Scene):
    def on_enter(self, **kwargs) -> None:
        gp = _gp(self.app)
        st = gp.state if gp else None
        if st:
            st.ending = True
            st.flags["chase_done"] = True
        stop_theme(400)
        self.t = 0.0
        self.chars = 0.0
        self.fade = ScreenFade(speed=1.2)
        self.fade.fade_in()
        self.menu_btn = Button(pygame.Rect(540, 620, 200, 46),
                               self.app.tr.t("ending.to_menu"), self.to_menu,
                               style="gold", size=20)

    def to_menu(self) -> None:
        from .splash import MainMenuScene
        play("click")
        self.app.reset(MainMenuScene(self.app))

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.menu_btn.handle(event):
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_e,
                                                          pygame.K_RETURN):
            if self.chars < 10 ** 6:
                self.chars = 10 ** 6
            else:
                self.to_menu()

    def update(self, dt: float) -> None:
        self.t += dt
        self.chars += dt * 34
        self.fade.update(dt)
        self.menu_btn.update(dt, self.app.mouse())

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((4, 4, 8))
        tr = self.app.tr
        lang = self.app.settings.language
        gp = _gp(self.app)
        st = gp.state if gp else None
        # dark silhouette stage
        if self.t < 3.0:
            pygame.draw.rect(surface, (8, 8, 14), (0, 0, DESIGN_W, DESIGN_H))
            draw_text(surface, "…", (640, 340), size=90, align="center",
                      color=(140, 140, 160), shadow=False)
        else:
            # faint blood writing on the wall
            from ..render.text import draw_text as dt2
            dt2(surface, "TIME", (640, 120), size=110, kind="serif_bold",
                color=(140, 30, 26), align="center", glow=(120, 20, 18), glow_radius=4)
            for i in range(6):
                x = 500 + i * 56
                pygame.draw.line(surface, (110, 22, 20), (x, 190), (x + 14, 250), 2)
            draw_text(surface, tr.t("ending.title"), (640, 250), size=44,
                      kind="serif_bold", color=(235, 235, 245), align="center",
                      glow=(212, 175, 55), glow_radius=2)
            ep = tr.t("ending.epilogue")
            if lang not in ("ru", "en"):
                ep = self.app.tr.tr_text(tr.t("ending.epilogue") if lang == "ru" else ep)
            shown = ep[: int(self.chars)]
            draw_wrapped(surface, shown, (200, 330), 880, size=21, color=(205, 210, 230),
                         line_spacing=8)
            if st:
                stats = st.stats
                line = (tr.t("gameover.days_used") + f": {st.day}    "
                        + tr.t("gameover.clues_found") + f": {stats['clues_total']}    "
                        + tr.t("gameover.money_earned") + f": ${int(stats['money_earned'])}")
                draw_text(surface, line, (640, 540), size=18, color=(150, 160, 185),
                          align="center", shadow=False)
            draw_text(surface, tr.t("ending.thanks"), (640, 580), size=20,
                      color=(245, 226, 170), align="center", shadow=False)
            draw_text(surface, tr.t("ending.author") + " · 2023", (640, 606), size=15,
                      color=(120, 130, 155), align="center", shadow=False)
            draw_text(surface, tr.t("ending.sub"), (640, 640), size=16,
                      color=(150, 110, 90), align="center", shadow=False)
        self.fade.draw(surface)
