"""The core gameplay scene: exploration, time flow, HUD, interactions."""
from __future__ import annotations

import math
from datetime import datetime

import pygame

from ..audio import play, play_theme
from ..config import (DAY_START_MINUTE, DESIGN_H, DESIGN_W, GAME_DAYS_TOTAL,
                      INTERACTION_DIST, TILE)
from ..core.camera import Camera
from ..core.scene import Scene
from ..game import witnesses
from ..game.clues import get as get_clue
from ..game.gamestate import GameState
from ..game.story import deliver_postcards, update_stage
from ..game.time import fmt_clock, fmt_date_short, game_minutes_from_real, world_datetime
from ..render.fx import Particles, ScreenFade
from ..render.sprites import SpriteBank
from ..render.text import draw_text
from ..render.ui import ProgressBar
from ..world.mapgen import DOORS, WORLD_H, WORLD_W
from ..world.npcs import NPC_DATA, npc_on_map
from ..world.props import props_for
from ..world.world import World

SPRINT_FACTOR = 1.55
WALK_SPEED = 3.4 * TILE


class Player:
    """Mike. `state.pos` is the single source of truth for his position."""

    def __init__(self, state: GameState) -> None:
        self.state = state
        self.facing = state.facing
        self.walk = 0.0

    @property
    def x(self) -> float:
        return self.state.pos[0]

    @property
    def y(self) -> float:
        return self.state.pos[1]

    def set_pos(self, x: float, y: float) -> None:
        self.state.pos = (x, y)

    def sprite_key(self) -> tuple:
        if self.state.dressed:
            return ((186, 160, 120), (74, 62, 50), (222, 190, 156), (52, 42, 30), 1, 0)
        return ((64, 84, 120), (50, 54, 66), (222, 190, 156), (52, 42, 30), 0, 0)


class GameplayScene(Scene):
    def __init__(self, app, state: GameState | None = None, fresh: bool = False) -> None:
        super().__init__(app)
        self.state = state if state is not None else GameState()
        self.world = World()
        self.bank = SpriteBank()
        self.player = Player(self.state)
        self._pause_depth = 0
        self.toasts: list = []
        self.events_queue: list[str] = []
        self._last_step = False
        self.t = 0.0
        self.snow = Particles(150)
        self.fade = ScreenFade(speed=1.4)
        self.big_text: dict | None = None      # {"text": ..., "t": ...}
        if fresh:
            self.state.current_map = "town"
            door = (10, 11)  # Mike's house door
            self.state.pos = (door[0] * TILE + TILE // 2, (door[1] + 1) * TILE - 6)
            self.state.facing = "down"
        elif not self.state.pos:
            self.state.pos = (10 * TILE + TILE // 2, 12 * TILE)

        self.camera = Camera(*self.world.map_size(self.state.current_map))
        self.camera.snap(*self._player_center())
        self._tutorial_queue: list[tuple[float, str]] = []
        if fresh:
            self._tutorial_queue.append((0.5, "tut.move"))
            self._tutorial_queue.append((6.0, "tut.interact"))
        self._enter_map(self.state.current_map)
        self._fresh_briefing = fresh

    # ------------------------------------------------------------ helpers --
    def world_now(self) -> datetime:
        return world_datetime(self.state.day, self.state.minutes, self.state.offset_min)

    def player_tile(self) -> tuple[int, int]:
        return int(self.player.x // TILE), int(self.player.y // TILE)

    def _player_center(self) -> tuple[float, float]:
        return self.player.x + TILE // 2, self.player.y + TILE // 2

    def autosave(self) -> None:
        from ..saves import autosave
        autosave(self.state)

    def toast(self, text: str, duration: float = 6.0) -> None:
        from ..render.ui import Toast
        self.toasts.append(Toast(text, duration=duration))

    def pause(self) -> None:
        """Pause the game clock (called by overlays on enter)."""
        self._pause_depth += 1

    def resume(self) -> None:
        """Unpause (called by overlays on exit)."""
        self._pause_depth = max(0, self._pause_depth - 1)

    @property
    def paused(self) -> bool:
        return self._pause_depth > 0

    def _tut_once(self, tut_id: str) -> None:
        if tut_id in self.state.tutorial_done:
            return
        self.state.tutorial_done.append(tut_id)
        self.toast(self.app.tr.t(f"tut.{tut_id}"))

    def _check_warnings(self) -> None:
        st = self.state
        if st.fatigue > 60:
            self._tut_once("fatigue")
        if st.hunger < 25:
            self._tut_once("hunger")
        if st.sick and not st.flags.get("sick_notified"):
            st.flags["sick_notified"] = True
            play("sick")
            self._tut_once("sick")

    def on_enter(self, **kwargs) -> None:
        self.app.gameplay = self
        self.app.on_quit = self.autosave
        # a re-entered gameplay (e.g. loaded save) restores the camera
        self._enter_map(self.state.current_map)
        if self._fresh_briefing:
            # open with the Day-1 briefing card
            self._fresh_briefing = False
            from .screens import BriefingScene
            self.pause()
            self.app.push(BriefingScene(self.app))

    def on_exit(self) -> None:
        if self.app.gameplay is self:
            self.app.gameplay = None
            self.app.on_quit = None

    def on_plot_progress(self) -> None:
        update_stage(self.state)
        for note in self._pending_notes():
            self.state.notebook_notes.append(note)
        if self.state.plot_stage >= 4 and not self.state.flags.get("emit_known_toast"):
            self.state.flags["emit_known_toast"] = True
            self.toast(self.app.tr.t("gameplay.emit_known"))

    def _pending_notes(self) -> list[dict]:
        from ..game.story import clue_notes
        existing = {n.get("clue") for n in self.state.notebook_notes}
        return [n for n in clue_notes(self.state) if n["clue"] not in existing]

    # ------------------------------------------------------------- events --
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.paused:
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_e:
            self._interact()
        elif event.key == pygame.K_q:
            self._open_time_travel()
        elif event.key in (pygame.K_j, pygame.K_TAB):
            self._open_notebook()
        elif event.key == pygame.K_ESCAPE:
            self._open_pause()

    def _open_time_travel(self) -> None:
        from .overlays import TimeTravelScene
        if not self.state.flags.get("tt_seen"):
            self.state.flags["tt_seen"] = True
            self._tut_once("time")
        play("whoosh")
        self.app.push(TimeTravelScene(self.app))

    def _open_notebook(self) -> None:
        from .overlays import NotebookScene
        play("notebook")
        self.app.push(NotebookScene(self.app))

    def _open_pause(self) -> None:
        from .overlays import PauseScene
        play("click")
        self.app.push(PauseScene(self.app))

    # ------------------------------------------------------------ update ---
    def update(self, dt: float) -> None:
        self.t += dt
        self.fade.update(dt)
        self.snow.update(dt, wind=10)
        for to in self.toasts:
            to.update(dt)
        self.toasts = [t for t in self.toasts if not t.done]
        if self.big_text:
            self.big_text["t"] += dt
            if self.big_text["t"] > 2.6:
                self.big_text = None
        # tutorial queue
        if self._tutorial_queue:
            delay, tid = self._tutorial_queue[0]
            delay -= dt
            if delay <= 0:
                self._tutorial_queue.pop(0)
                self.toast(self.app.tr.t(tid))
            else:
                self._tutorial_queue[0] = (delay, tid)
        self._check_warnings()
        if self.paused:
            return
        # process pending events (news / briefing / game over)
        if self.events_queue:
            self._process_event(self.events_queue.pop(0))
            return
        if self.state.game_over:
            if not self.state.flags.get("go_scene_shown"):
                self.state.flags["go_scene_shown"] = True
                self.pause()
                from .screens import GameOverScene
                self.app.push(GameOverScene(self.app, reason=self.state.game_over))
            return
        # overdue loans end the game even without a clock tick
        if self.state._check_loans():
            self.pause()
            from .screens import GameOverScene
            self.app.push(GameOverScene(self.app, reason="loan"))
            return
        # chase trigger
        if self._check_chase_trigger():
            return
        # movement
        self._move_player(dt)
        # time flow
        gmin = game_minutes_from_real(dt)
        sprinting = self._sprinting()
        if gmin > 0:
            self.state.fatigue = min(100.0, self.state.fatigue + gmin * self.state.fatigue_gain_per_minute(sprinting))
            self.state.hunger = max(0.0, self.state.hunger + gmin * self.state.hunger_gain_per_minute())
            if self.state.fatigue >= 100.0:
                self._pass_out()
            else:
                self.state.play_seconds += dt
                for ev in self.state.advance_minutes(gmin):
                    self.events_queue.append(ev)
        self.camera.follow(*self._player_center(), dt)

    def _sprinting(self) -> bool:
        return bool(self.app.input.is_down(pygame.K_LSHIFT, pygame.K_RSHIFT)) and \
            (self.app.input.is_down(pygame.K_w, pygame.K_UP) or
             self.app.input.is_down(pygame.K_s, pygame.K_DOWN) or
             self.app.input.is_down(pygame.K_a, pygame.K_LEFT) or
             self.app.input.is_down(pygame.K_d, pygame.K_RIGHT))

    def _pass_out(self) -> None:
        state = self.state
        hours = state.do_sleep(passed_out=True)
        play("sleep")
        play("alert")
        self.toast(self.app.tr.t("gameplay.passed_out", h=hours))
        for ev in state.advance_minutes(hours * 60):
            self.events_queue.append(ev)

    def sleep_in_bed(self) -> None:
        state = self.state
        hours = state.do_sleep(passed_out=False)
        play("sleep")
        self.toast(self.app.tr.t("gameplay.slept", h=hours))
        for ev in state.advance_minutes(hours * 60):
            self.events_queue.append(ev)

    def _process_event(self, ev: str) -> None:
        if ev in ("news", "utilities"):
            from .screens import NewsScene
            self.pause()
            self.app.push(NewsScene(self.app))
        elif ev == "briefing":
            from .screens import BriefingScene
            self.pause()
            self.app.push(BriefingScene(self.app))
        elif ev in ("deadline", "loan", "death"):
            from .screens import GameOverScene
            self.pause()
            self.app.push(GameOverScene(self.app, reason=self.state.game_over or ev))
        elif ev == "health":
            if self.state.sick:
                self.toast(self.app.tr.t("tut.sick"))
            elif self.state.hunger <= 0:
                self.toast(self.app.tr.t("gameplay.starving"))

    # ----------------------------------------------------------- movement --
    def _move_player(self, dt: float) -> None:
        inp = self.app.input
        dx = (1 if inp.is_down(pygame.K_d, pygame.K_RIGHT) else 0) - \
             (1 if inp.is_down(pygame.K_a, pygame.K_LEFT) else 0)
        dy = (1 if inp.is_down(pygame.K_s, pygame.K_DOWN) else 0) - \
             (1 if inp.is_down(pygame.K_w, pygame.K_UP) else 0)
        moving = dx != 0 or dy != 0
        if not moving:
            return
        if dx and dy:
            dx, dy = dx / math.sqrt(2), dy / math.sqrt(2)
        speed = WALK_SPEED * self.state.speed_multiplier
        if self._sprinting():
            speed *= SPRINT_FACTOR
        nx = self.player.x + dx * speed * dt
        ny = self.player.y + dy * speed * dt
        map_id = self.state.current_map
        # axis-separated collision
        px, py = self.player.x, self.player.y
        if not self.world.solid_at_px(map_id, nx, py):
            px = nx
        if not self.world.solid_at_px(map_id, px, ny):
            py = ny
        # keep inside map
        w, h = self.world.map_size(map_id)
        px = max(0.0, min(w - TILE, px))
        py = max(0.0, min(h - TILE, py))
        self.player.set_pos(px, py)
        if abs(dx) > abs(dy):
            self.player.facing = "right" if dx > 0 else "left"
        else:
            self.player.facing = "down" if dy > 0 else "up"
        self.player.walk += dt * (10 if self._sprinting() else 7)
        self.state.facing = self.player.facing
        # step sounds (sparse: once per animation cycle)
        step_i = int(self.player.walk * 2) % 4
        if step_i == 1 and not self._last_step:
            play("step", 0.3)
        self._last_step = (step_i == 1)

    # -------------------------------------------------------- interactions --
    def _interactions(self) -> list[dict]:
        items = []
        map_id = self.state.current_map
        px, py = self._player_center()
        now = self.world_now()
        for prop in props_for(map_id):
            if not prop.visible(self.state, now):
                continue
            cx = prop.x * TILE + TILE // 2
            cy = prop.y * TILE + TILE // 2
            d = math.hypot(px - cx, py - cy)
            if d < INTERACTION_DIST * TILE:
                items.append({"type": "prop", "prop": prop, "d": d})
        for nid in npc_on_map(self.state, map_id):
            pos = NPC_DATA[nid].pos_at(self.state.minutes, map_id)
            if pos is None:
                continue
            cx, cy = pos[0] * TILE + TILE // 2, pos[1] * TILE + TILE // 2
            d = math.hypot(px - cx, py - cy)
            if d < INTERACTION_DIST * TILE + 6:
                items.append({"type": "npc", "nid": nid, "d": d})
        if map_id == "town":
            pt = self.player_tile()
            for (dx, dy) in DOORS:
                if abs(pt[0] - dx) <= 1 and abs(pt[1] - dy) <= 1:
                    d = math.hypot(px - (dx * TILE + TILE // 2), py - (dy * TILE + TILE // 2))
                    items.append({"type": "door", "tile": (dx, dy), "d": d})
        items.sort(key=lambda it: it["d"])
        return items

    def _prompt(self) -> str | None:
        items = self._interactions()
        if not items:
            return None
        it = items[0]
        tr = self.app.tr
        if it["type"] == "npc":
            nid = it["nid"]
            if nid == "cat":
                return tr.t("gameplay.pick_cat")
            return tr.t("hud.speak")
        if it["type"] == "door":
            return tr.t("hud.enter")
        prop = it["prop"]
        kind = prop.kind
        if kind == "inspect":
            return tr.t("hud.interact", action=tr.t("gameplay.inspect"))
        if kind == "victim_door":
            if not self.state.has_clue("fingerprints"):
                return tr.t("gameplay.inspect_handle")
            return tr.t("gameplay.open_door")
        if kind == "bed":
            return tr.t("gameplay.sleep")
        if kind == "wardrobe":
            return tr.t("gameplay.dress")
        if kind == "computer":
            return tr.t("gameplay.computer")
        if kind == "fridge":
            return tr.t("gameplay.fridge")
        if kind == "counter_shop":
            return tr.t("gameplay.buy")
        if kind == "counter_bank":
            return tr.t("gameplay.bank")
        if kind == "mailbox":
            return tr.t("gameplay.mailbox")
        if kind == "enter":
            return tr.t("hud.enter")
        if kind == "exit":
            return tr.t("hud.leave")
        if kind == "emit_door":
            return tr.t("hud.enter")
        return tr.t("hud.interact", action=tr.t("gameplay.inspect"))

    def _interact(self) -> None:
        items = self._interactions()
        if not items:
            return
        it = items[0]
        if it["type"] == "npc":
            self._talk(it["nid"])
        elif it["type"] == "door":
            self._enter_interior(it["tile"])
        elif it["type"] == "prop":
            self._prop_action(it["prop"])

    def _talk(self, nid: str) -> None:
        state = self.state
        if nid == "cat":
            if state.flags.get("cat_carried"):
                self.toast(self.app.tr.t("gameplay.cat_already"))
                return
            state.flags["cat_carried"] = True
            play("confirm")
            self.toast(self.app.tr.t("gameplay.cat_picked"))
            return
        if nid == "emit":
            self._start_chase()
            return
        if nid == "banker":
            from .overlays import BankScene
            play("click")
            self.app.push(BankScene(self.app))
            return
        if nid not in state.witnesses_met:
            state.witnesses_met.append(nid)
            state.stats["witnesses_total"] += 1
        talk = {
            "marta": witnesses.talk_marta,
            "nick": witnesses.talk_nick,
            "boris": witnesses.talk_boris,
            "volkov": witnesses.talk_volkov,
            "krylov": witnesses.talk_krylov,
            "krylov2": witnesses.talk_krylov2,
            "w1": lambda s, g: witnesses.talk_wanderer(s, g, "w1"),
            "w2": lambda s, g: witnesses.talk_wanderer(s, g, "w2"),
            "w3": lambda s, g: witnesses.talk_wanderer(s, g, "w3"),
        }
        fn = talk.get(nid)
        if fn is None:
            return
        # In the past, Marta doesn't know the future yet.
        if nid == "marta" and self.world_now() < datetime(2023, 11, 23, 6, 0):
            turn = witnesses.Turn("marta", {
                "ru": "Ох, не к добру вы по улицам в такой час ходите. Виктор сегодня сам не свой: ждёт кого-то в полночь.",
                "en": "Oh, wandering the streets at this hour bodes ill. Viktor is not himself today: he is expecting someone at midnight.",
            })
        else:
            turn = fn(state, self)
        from .overlays import DialogueScene
        self.pause()
        self.app.push(DialogueScene(self.app, nid, turn))

    def _enter_interior(self, tile: tuple[int, int]) -> None:
        interior = self.world.interior_of(tile)
        if interior is None:
            return
        play("door")
        self.state.current_map = interior
        entry = self.world.interiors[interior].enter_tile
        self.state.pos = (entry[0] * TILE + TILE // 2, entry[1] * TILE + TILE // 2)
        self._enter_map(interior)

    def _exit_to_town(self) -> None:
        play("door")
        tile = self.state.flags.get("last_door_tile", (10, 11))
        self.state.current_map = "town"
        self.state.pos = (tile[0] * TILE + TILE // 2, (tile[1] + 1) * TILE - 6)
        self._enter_map("town")
        if not self.state.flags.get("town_seen"):
            self.state.flags["town_seen"] = True
            self._tut_once("time")
            self._tut_once("save")

    def _enter_map(self, map_id: str) -> None:
        self.state.current_map = map_id
        w, h = self.world.map_size(map_id)
        self.camera = Camera(w, h)
        self.camera.snap(*self._player_center())

    def _prop_action(self, prop) -> None:
        state = self.state
        kind = prop.kind
        if kind == "inspect":
            self._inspect_prop(prop)
        elif kind == "enter":
            tile = (prop.x, prop.y)
            state.flags["last_door_tile"] = tile
            self._enter_interior(tile)
        elif kind == "exit":
            self._exit_to_town()
        elif kind == "victim_door":
            self._victim_door(prop)
        elif kind == "emit_door":
            if state.plot_stage >= 4:
                state.flags["last_door_tile"] = (12, 50)
                self._enter_interior((12, 50))
            else:
                play("error")
                self.toast(self.app.tr.t("tut.door_locked"))
        elif kind == "warehouse_door":
            play("error")
            self.toast(self.app.tr.t("gameplay.warehouse_locked"))
        elif kind == "mailbox":
            self._mailbox()
        elif kind == "bed":
            self._bed()
        elif kind == "wardrobe":
            self._wardrobe()
        elif kind == "computer":
            from .overlays import ComputerScene
            play("click")
            self.app.push(ComputerScene(self.app))
        elif kind == "fridge":
            self._fridge()
        elif kind == "counter_shop":
            from .overlays import ShopScene
            play("click")
            self.app.push(ShopScene(self.app))
        elif kind == "counter_bank":
            from .overlays import BankScene
            play("click")
            self.app.push(BankScene(self.app))

    def _inspect_prop(self, prop) -> None:
        state = self.state
        clue_id = prop.clue_id
        if clue_id and state.add_clue(clue_id):
            clue = get_clue(clue_id)
            play("clue")
            self.toast(self.app.tr.t("gameplay.clue_found"))
            self.on_plot_progress()
        else:
            play("notebook")
        custom = None
        if prop.id == "exit_sign" and state.plot_stage >= 4:
            custom = ({"ru": "Выезд из города", "en": "Town exit"},
                      {"ru": "Полиция ищет EMIT. Кто-то видел у выезда человека в кепке — он свернул к старому складу.",
                       "en": "The police are looking for EMIT. Someone saw a man in a cap near the exit — he turned toward the old warehouse."})
        from .overlays import InfoScene
        self.pause()
        if custom:
            self.app.push(InfoScene(self.app, prop, custom_title=custom[0],
                                    custom_text=custom[1]))
        else:
            self.app.push(InfoScene(self.app, prop))

    def _victim_door(self, prop) -> None:
        state = self.state
        now = self.world_now()
        if not state.has_clue("fingerprints"):
            if now >= datetime(2023, 11, 25, 0, 0):
                state.add_clue("fingerprints")
                state.clue_found_day["fingerprints"] = state.day
                play("clue")
                self.toast(self.app.tr.t("gameplay.fingerprints_found"))
                self.on_plot_progress()
                from .overlays import InfoScene
                self.pause()
                self.app.push(InfoScene(self.app, prop, custom_title=(
                    {"ru": "Отпечатки пальцев", "en": "Fingerprints"}),
                    custom_text=({"ru": "На дверной ручке — чужие отпечатки. Нужно проверить, чьи они. Записано в блокнот.",
                                  "en": "On the door handle — someone else's fingerprints. They need to be checked. Noted in the notebook."})))
                return
            else:
                play("notebook")
                from .overlays import InfoScene
                self.pause()
                self.app.push(InfoScene(self.app, prop, custom_title=(
                    {"ru": "Дверная ручка", "en": "Door handle"}),
                    custom_text=({"ru": "Ручка чистая. В это время отпечатков здесь ещё нет.",
                                  "en": "The handle is clean. At this time, there are no prints here yet."})))
                return
        # open the door
        if not state.dressed:
            play("error")
            self._tut_once("gloves")
            return
        if now < datetime(2023, 11, 23, 0, 25):
            play("error")
            self.toast(self.app.tr.t("tut.door_locked"))
            return
        state.flags["last_door_tile"] = (47, 51)
        self._enter_interior((47, 51))

    def _mailbox(self) -> None:
        state = self.state
        delivered = deliver_postcards(state, mailbox=True)
        if delivered:
            play("postcard")
            from .overlays import PostcardScene
            self.pause()
            self.app.push(PostcardScene(self.app, delivered))
        else:
            play("notebook")
            self.toast(self.app.tr.t("gameplay.mailbox_empty"))

    def _bed(self) -> None:
        state = self.state
        if state.fatigue < 15:
            self.toast(self.app.tr.t("gameplay.not_tired"))
            return
        self._tut_once("bed")
        from .overlays import ConfirmScene
        self.pause()
        hours = state.sleep_hours()
        self.app.push(ConfirmScene(self.app,
            self.app.tr.t("tut.sleep_prompt", f=int(state.fatigue), h=hours),
            on_yes=self.sleep_in_bed))

    def _wardrobe(self) -> None:
        state = self.state
        if state.dressed:
            self.toast(self.app.tr.t("gameplay.already_dressed"))
            return
        state.dressed = True
        play("confirm")
        self.toast(self.app.tr.t("tut.dress_done"))

    def _fridge(self) -> None:
        state = self.state
        if state.flags.get("fridge_day") == state.day:
            self.toast(self.app.tr.t("gameplay.fridge_empty"))
            return
        state.flags["fridge_day"] = state.day
        state.hunger = min(100.0, state.hunger + 25)
        play("eat")
        self.toast(self.app.tr.t("gameplay.fridge_eat"))

    # --------------------------------------------------------------- chase --
    def _check_chase_trigger(self) -> bool:
        state = self.state
        if state.plot_stage < 4 or state.offset_min != 0:
            return False
        if state.flags.get("chase_started"):
            return False
        if state.current_map != "town":
            return False
        pos = NPC_DATA["emit"].pos_at(self.state.minutes, "town")
        if pos is None:
            return False
        px, py = self._player_center()
        d = math.hypot(px - pos[0] * TILE, py - pos[1] * TILE)
        if d < 10 * TILE:
            self._start_chase()
            return True
        return False

    def _start_chase(self) -> None:
        state = self.state
        state.flags["chase_started"] = True
        state.stats["chase"] += 1
        play("chase")
        play_theme("chase")
        self.pause()
        from .screens import ChaseScene
        self.app.push(ChaseScene(self.app))

    # ---------------------------------------------------------------- draw --
    def draw(self, surface: pygame.Surface) -> None:
        state = self.state
        self.world.draw(surface, self.camera, state.current_map, state,
                        self.app.settings.language, self.bank,
                        entity_drawer=self._draw_player, tr=self.app.tr)
        self._draw_hud(surface)
        for to in self.toasts:
            to.draw(surface)
        if self.big_text:
            draw_text(surface, self.big_text["text"], (DESIGN_W // 2, 300),
                      size=64, kind="serif_bold", color=(245, 226, 170),
                      align="center", glow=(212, 175, 55), glow_radius=3)
        self.fade.draw(surface)

    def _draw_player(self, surface, cam_x, cam_y) -> None:
        bank = self.bank
        key = self.player.sprite_key()
        phase = math.sin(self.player.walk * 1.4) if self.player.walk else 0
        del phase
        sprite = bank.character(key, dir_name=self.player.facing)
        sx = int(self.player.x - cam_x)
        sy = int(self.player.y - cam_y)
        surface.blit(sprite, (sx - TILE // 2, sy - TILE // 2 - 6))
        # carried cat
        if self.state.flags.get("cat_carried"):
            cat = bank.cat()
            bob = int(3 * math.sin(self.t * 5))
            surface.blit(cat, (sx + 8, sy - TILE - 10 + bob))

    def _draw_hud(self, surface: pygame.Surface) -> None:
        state = self.state
        tr = self.app.tr
        lang = self.app.settings.language
        # ---- clock (top center)
        now = self.world_now()
        clock_txt = fmt_clock(state.minutes)
        draw_text(surface, clock_txt, (DESIGN_W // 2, 14), size=44, kind="serif_bold",
                  color=(240, 240, 245), align="center", glow=(212, 175, 55),
                  glow_radius=2, shadow=False)
        date_txt = fmt_date_short(now, lang).replace(" 2023", "")
        day_txt = tr.t("hud.day", day=state.day, total=GAME_DAYS_TOTAL)
        draw_text(surface, f"{date_txt}  ·  {day_txt}", (DESIGN_W // 2, 66),
                  size=17, color=(190, 200, 220), align="center", outline=True, shadow=False)
        # ---- money (top left)
        money_txt = tr.t("hud.money", money=int(state.money))
        draw_text(surface, money_txt, (16, 14), size=30, kind="sans_bold",
                  color=(245, 226, 170), shadow=True)
        days_left = state.days_left
        if days_left >= 0:
            draw_text(surface, tr.t("hud.days_left", n=days_left), (18, 52),
                      size=15, color=(200, 130, 130) if days_left <= 2 else (170, 180, 205),
                      shadow=False)
        # ---- timeline badge (top right)
        if state.offset_min < 0:
            badge = tr.t("hud.past_badge", date=fmt_date_short(now, lang), time=fmt_clock(state.minutes))
            draw_text(surface, badge, (DESIGN_W - 18, 16), size=18, kind="sans_bold",
                      color=(255, 170, 150), align="right", outline=True, shadow=False)
            draw_text(surface, tr.t("tt.return_present") + " [Q]", (DESIGN_W - 18, 42),
                      size=14, color=(255, 210, 190), align="right", shadow=False)
        else:
            draw_text(surface, tr.t("hud.present_badge"), (DESIGN_W - 18, 16),
                      size=14, color=(140, 170, 150), align="right", shadow=False)
        # ---- status bars (bottom left)
        bx, by = 18, DESIGN_H - 120
        labels = [
            (tr.t("hud.fatigue"), state.fatigue / 100.0,
             (240, 180, 70) if state.fatigue < 80 else (240, 90, 60)),
            (tr.t("hud.hunger"), state.hunger / 100.0,
             (110, 200, 110) if state.hunger > 25 else (240, 110, 70)),
            (tr.t("hud.health"), state.health / 100.0,
             (110, 160, 230) if state.health > 50 else (230, 90, 80)),
        ]
        for i, (name, val, color) in enumerate(labels):
            y = by + i * 34
            draw_text(surface, name, (bx, y), size=14, color=(200, 205, 220), shadow=True)
            bar = ProgressBar(pygame.Rect(bx + 92, y + 1, 150, 12), val, color=color)
            bar.draw(surface)
        if state.sick:
            draw_text(surface, tr.t("hud.sick_badge"), (bx, by + 110), size=16,
                      kind="sans_bold", color=(255, 130, 110), shadow=False)
        elif state.fatigue > 60:
            draw_text(surface, tr.t("hud.tired_badge"), (bx, by + 110), size=16,
                      kind="sans_bold", color=(240, 190, 90), shadow=False)
        elif state.hunger < 25:
            draw_text(surface, tr.t("hud.hungry_badge"), (bx, by + 110), size=16,
                      kind="sans_bold", color=(240, 170, 90), shadow=False)
        # ---- interaction prompt (bottom center)
        prompt = self._prompt()
        if prompt:
            draw_text(surface, prompt, (DESIGN_W // 2, DESIGN_H - 46), size=22,
                      color=(255, 255, 255), align="center", outline=True, shadow=False)
        # ---- control hints (bottom right)
        draw_text(surface, "Q — " + tr.t("tt.title"), (DESIGN_W - 16, DESIGN_H - 60),
                  size=14, color=(150, 160, 185), align="right", shadow=False)
        draw_text(surface, "J — " + tr.t("notebook.title"), (DESIGN_W - 16, DESIGN_H - 38),
                  size=14, color=(150, 160, 185), align="right", shadow=False)
        draw_text(surface, "Esc — " + tr.t("pause.title"), (DESIGN_W - 16, DESIGN_H - 16),
                  size=14, color=(150, 160, 185), align="right", shadow=False)
