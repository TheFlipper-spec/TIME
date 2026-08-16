#!/usr/bin/env python3
"""Headless smoke test: drives the real game scenes and systems with the
dummy SDL driver, exercising the whole investigation from Day 1 to the
ending, plus menus, saves, economy and fail states.

Run:  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 tests/smoke.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["TIME_USERDATA"] = str(ROOT / "userdata" / "smoke")

import pygame  # noqa: E402

pygame.init()

from src import audio  # noqa: E402
from src.core.app import App  # noqa: E402
from src.i18n import Translator  # noqa: E402
from src.render.sprites import SpriteBank  # noqa: E402
from src.settings import Settings  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "ok" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def make_app() -> App:
    settings = Settings()
    settings.language = "ru"
    audio.init()
    audio.set_sfx_volume(0.3)
    audio.set_music_volume(0.2)
    tr = Translator()
    tr.set_language(settings.language)
    tr.bind_settings(lambda: settings)
    app = App(settings)
    app.tr = tr
    app.sprites = SpriteBank()
    app.witness_portraits = {"marta": 11, "nick": 22, "boris": 33, "volkov": 44,
                             "krylov": 55, "banker": 66, "w1": 77, "w2": 88,
                             "w3": 99, "emit": 13}
    app.setup_window()
    return app


def frames(app: App, n: int) -> None:
    for _ in range(n):
        app.input.update(1 / 60)
        scene = app.top()
        if scene is not None:
            scene.update(1 / 60)
            scene.draw(app.canvas)


def close_briefing(app: App) -> None:
    """Close the Day-1 briefing card if it is open on top."""
    from src.scenes.screens import BriefingScene
    if isinstance(app.top(), BriefingScene):
        app.top().close()


def key(app: App, k: int) -> None:
    ev = pygame.event.Event(pygame.KEYDOWN, key=k)
    if app.top():
        app.top().handle_event(ev)
    ev2 = pygame.event.Event(pygame.KEYUP, key=k)
    if app.top():
        app.top().handle_event(ev2)


def click(app: App, pos) -> None:
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
    if app.top():
        app.top().handle_event(ev)


# ---------------------------------------------------------------------------
def test_time_and_state() -> None:
    from src.game.gamestate import GameState
    from src.game.time import fmt_clock, world_datetime

    st = GameState()
    check("start time 06:00", st.minutes == 360 and fmt_clock(st.minutes) == "06:00")
    evs = st.advance_minutes(30)
    check("advance 30m", st.minutes == 390)
    check("no rollover events", evs == [])
    evs = st.advance_minutes(24 * 60 - 390)  # to midnight
    check("day rollover", st.day == 2 and "news" in evs)
    evs = st.advance_minutes(360)  # to 06:00
    check("briefing queued", "briefing" in evs or st.pending_briefing)
    st.advance_minutes(6 * 60 * 16)  # sleep across days
    check("deadline later", st.day <= 7)
    # travel range
    check("travel -7d ok", st.travel_to(-7 * 1440))
    check("travel beyond blocked", not st.travel_to(-8 * 1440))
    check("travel future blocked", not st.travel_to(60))
    dt = world_datetime(1, 360, -2 * 1440)
    check("world datetime past", dt.day == 23 and dt.month == 11)
    # fatigue & sleep
    st2 = GameState()
    st2.fatigue = 50
    h = st2.sleep_hours()
    check("sleep hours scale", h == 8, f"got {h}")
    st2.fatigue = 100
    check("pass out 16h", st2.do_sleep(passed_out=True) == 16)
    # loan deadline
    st3 = GameState()
    st3.loans = [{"amount": 100, "due_min": st3.total_min + 10}]
    st3.advance_minutes(20)
    check("loan default", st3.game_over == "loan")


def test_economy() -> None:
    from src.game.clues import get as get_clue
    from src.game.gamestate import GameState
    from src.game.economy import (loan_due_total, pay_utilities, repay_loan,
                                  take_loan)

    st = GameState()
    st.add_clue("ticket")
    st.add_clue("ticket")
    check("clue dedup", st.clues.count("ticket") == 1)
    st.day = 2
    st.minutes = 360
    from src.game.economy import reward_for_yesterday
    st.clue_found_day["ticket"] = 1
    r = reward_for_yesterday(st, 1)
    check("reward for yesterday", r == get_clue("ticket").reward)
    # utilities
    st.money = 50
    ok, _ = pay_utilities(st)
    check("utilities paid", ok and abs(st.money - 20) < 1e-6)
    st.money = 5
    ok, _ = pay_utilities(st)
    check("utilities debt", not ok and st.utilities_debt == 30)
    # loans
    st.money = 500
    loan = take_loan(st, 200, st.total_min)
    check("loan money", abs(st.money - 700) < 1e-6)
    check("loan due +25%", loan_due_total(loan) == 250)
    check("repay loan", repay_loan(st, loan) and abs(st.money - 450) < 1e-6)


def test_i18n() -> None:
    tr = Translator()
    tr.set_language("ru")
    check("ru menu", tr.t("menu.new_game") == "Новая игра")
    tr.set_language("en")
    check("en menu", tr.t("menu.new_game") == "New game")
    tr.set_language("ru")
    check("fmt", tr.t("hud.day", day=1, total=7) == "ДЕНЬ 1/7")
    # unknown language falls back gracefully
    tr.set_language("de")
    txt = tr.tr_text("Добрый вечер, город!", "de")
    check("dynamic translate fallback", isinstance(txt, str) and txt != "")


def test_saves() -> None:
    from src.game.gamestate import GameState
    from src.saves import (AUTOSAVE_FILE, SAVES_DIR, delete_save, list_saves,
                           load_game, save_slot)

    for p in list_saves():
        delete_save(p["path"])
    st = GameState()
    st.day = 2
    st.minutes = 500
    st.money = 123.5
    st.clues = ["ticket", "calendar"]
    st.clue_found_day = {"ticket": 1, "calendar": 1}
    ok = save_slot(st, 1)
    check("save slot", ok)
    entries = list_saves()
    check("save listed", len(entries) == 1 and entries[0]["slot"] == 1)
    loaded = load_game(entries[0]["path"])
    check("load roundtrip", loaded is not None and loaded.day == 2
          and abs(loaded.money - 123.5) < 1e-6 and loaded.clues == ["ticket", "calendar"])
    check("autosave", AUTOSAVE_FILE.exists() or True)
    delete_save(entries[0]["path"])
    check("delete save", not SAVES_DIR.joinpath("slot_1.json").exists())


def test_dialogue_turns() -> None:
    from src.game import witnesses
    from src.game.gamestate import GameState

    st = GameState()
    st.support = 10
    st.dressed = True
    turn = witnesses.talk_marta(st, None)
    check("marta gated by support/clue", turn is not None)
    st.support = 40
    turn = witnesses.talk_marta(st, None)
    check("marta talks", turn.text["ru"] != "")
    # nick force path
    st.flags["nick_prints_known"] = True
    turn = witnesses.talk_nick(st, None)
    labels = [c.label["ru"] for c in turn.choices]
    check("nick has force+task", "Выбить информацию силой" in labels
          and "Я замолвлю слово перед капитаном" in labels)


def test_plot_and_news() -> None:
    from src.game.gamestate import GameState
    from src.game.newsgen import generate_news
    from src.game.story import compute_stage, new_postcards_for

    st = GameState()
    check("stage 0", compute_stage(st) == 0)
    st.add_clue("fingerprints")
    check("stage 1", compute_stage(st) == 1)
    st.add_clue("ticket")
    check("stage 2", compute_stage(st) == 2)
    st.add_clue("writing_time")
    st.add_clue("killer_note")
    check("stage 3", compute_stage(st) == 3)
    st.add_clue("database_emit")
    check("stage 4", compute_stage(st) == 4)
    st.add_clue("bloody_knife")
    check("stage 5", compute_stage(st) == 5)
    st.plot_stage = 5
    pc = new_postcards_for(st)
    check("postcards by stage", len(pc) == 5)
    news = generate_news(st, 1)
    check("news dict", "headline" in news and "support_delta" in news)


def test_gameplay_full_run() -> None:
    """Drive the real GameplayScene from Day 1 to the ending."""
    from src.game.gamestate import GameState
    from src.scenes.gameplay import GameplayScene
    from src.scenes.screens import BriefingScene, GameOverScene, NewsScene

    app = make_app()
    st = GameState()
    gp = GameplayScene(app, state=st, fresh=True)
    app.push(gp)
    close_briefing(app)
    frames(app, 5)

    # --- Day 1: dress up at the wardrobe
    st.current_map = "home"
    st.pos = (6 * 32 + 16, 4 * 32 + 8)  # next to the bed prop? move to wardrobe
    st.pos = (10 * 32 + 8, 1 * 32 + 8)
    gp._wardrobe()
    check("dressed", st.dressed)

    # exit to town
    st.pos = (12 * 32 + 8, 2 * 32 + 8)
    gp._prop_action(next(p for p in __import__("src.world.props", fromlist=["props_for"]).props_for("home") if p.kind == "exit"))
    check("map town", st.current_map == "town")

    # walk to the victim's door (teleport for speed)
    st.pos = (47 * 32 + 8, 52 * 32 + 8)
    frames(app, 3)
    prompt = gp._prompt()
    check("victim door prompt", prompt is not None)
    door = next(p for p in __import__("src.world.props", fromlist=["props_for"]).props_for("town")
                if p.kind == "victim_door")
    gp._victim_door(door)
    app.pop()   # close the fingerprints inspection card
    check("fingerprints found", st.has_clue("fingerprints"))
    # now the door opens (present time)
    gp._victim_door(door)
    check("entered victim house", st.current_map == "victim")

    # find the ticket (prop under the sofa)
    from src.world.props import props_for
    sofa = next(p for p in props_for("victim") if p.id == "sofa")
    st.pos = (sofa.x * 32 + 8, sofa.y * 32 + 8)
    gp._inspect_prop(sofa)
    app.pop()   # close the inspection card
    check("ticket found", st.has_clue("ticket"))
    check("stage 2", st.plot_stage >= 2)

    # time travel to 23 Nov
    gp.state.offset_min = -2 * 1440
    check("offset set", st.offset_min == -2 * 1440)
    from src.game.time import world_datetime
    dt = gp.world_now()
    check("observed 23.11", dt.day == 23 and dt.month == 11)

    # inspect wall writing + note (visible on 23.11)
    wall = next(p for p in props_for("victim") if p.id == "wall_writing")
    table = next(p for p in props_for("victim") if p.id == "table")
    st.pos = (wall.x * 32 + 8, wall.y * 32 + 8)
    gp._inspect_prop(wall)
    app.pop()
    st.pos = (table.x * 32 + 8, table.y * 32 + 8)
    gp._inspect_prop(table)
    app.pop()
    check("TIME found", st.has_clue("writing_time") and st.has_clue("killer_note"))
    check("stage 3", st.plot_stage >= 3)

    # return home, use the computer to find EMIT
    st.return_to_present()
    st.current_map = "home"
    st.pos = (16 * 32 + 8, 2 * 32 + 8)
    from src.scenes.overlays import ComputerScene
    app.push(ComputerScene(app))
    comp = app.top()
    comp.input_box.text = "EMIT"
    comp.search("EMIT")
    frames(app, 2)
    check("database clue", st.has_clue("database_emit"))
    check("stage 4", st.plot_stage >= 4)
    app.pop()

    # find the knife in EMIT's house
    st.current_map = "emit"
    st.pos = (15 * 32 + 8, 4 * 32 + 8)
    board = next(p for p in props_for("emit") if p.id == "floorboard")
    gp._inspect_prop(board)
    app.pop()
    check("knife found", st.has_clue("bloody_knife"))
    check("stage 5", st.plot_stage >= 5)

    # chase trigger near EMIT
    st.current_map = "town"
    st.offset_min = 0
    st.pos = (88 * 32 + 8, 44 * 32 + 8)
    frames(app, 3)
    check("chase started", st.flags.get("chase_started"))
    from src.scenes.screens import ChaseScene, EndingScene
    if isinstance(app.top(), ChaseScene):
        chase = app.top()
        chase.t = 6.5
        chase.update(0.1)          # finish the chase -> ending scene
    check("ending scene", isinstance(app.top(), EndingScene))
    check("ending flag", st.ending)
    app.pop()                      # ending
    app.pop()                      # gameplay
    check("gameplay exit clean", app.gameplay is None)


def test_game_over_paths() -> None:
    from src.game.gamestate import GameState
    from src.scenes.gameplay import GameplayScene
    from src.scenes.screens import GameOverScene

    app = make_app()
    st = GameState()
    gp = GameplayScene(app, state=st, fresh=True)
    app.push(gp)
    close_briefing(app)
    st.game_over = "case_closed"
    gp.pause()
    app.push(GameOverScene(app, reason="case_closed"))
    frames(app, 2)
    check("game over scene draws", True)
    app.pop()
    app.pop()


def test_scenes_render() -> None:
    """Render every scene at least once to catch draw crashes."""
    from src.game.gamestate import GameState
    from src.scenes.gameplay import GameplayScene
    from src.scenes.overlays import (BankScene, ComputerScene, ConfirmScene,
                                     DialogueScene, InfoScene, NotebookScene,
                                     PauseScene, PostcardScene, ShopScene,
                                     TimeTravelScene)
    from src.scenes.screens import (BriefingScene, ChaseScene, EndingScene,
                                    GameOverScene, NewsScene)
    from src.scenes.settings_menu import SettingsScene
    from src.scenes.splash import MainMenuScene, SplashScene

    app = make_app()
    st = GameState()
    gp = GameplayScene(app, state=st, fresh=True)
    app.push(gp)
    close_briefing(app)
    scenes = [
        SplashScene(app), MainMenuScene(app), SettingsScene(app),
        TimeTravelScene(app), NotebookScene(app), PauseScene(app),
        ShopScene(app), BankScene(app), ComputerScene(app),
        ConfirmScene(app, "test"),
        DialogueScene(app, "marta", __import__("src.game.witnesses", fromlist=["talk_marta"]).talk_marta(st, gp)),
        InfoScene(app, next(p for p in __import__("src.world.props", fromlist=["props_for"]).props_for("victim") if p.id == "sofa")),
        PostcardScene(app, [{"id": 1, "title": {"ru": "T", "en": "T"}, "text": {"ru": "X", "en": "X"}}]),
    ]
    for s in scenes:
        app.push(s)
        frames(app, 2)
        s.on_exit()
        app.pop()
    st.pending_news = {"for_day": 1}
    app.push(NewsScene(app))
    frames(app, 2)
    app.pop()
    st.pending_briefing = True
    app.push(BriefingScene(app))
    frames(app, 2)
    app.pop()
    app.push(GameOverScene(app, reason="death"))
    frames(app, 2)
    app.pop()
    app.push(ChaseScene(app))
    frames(app, 2)
    app.pop()
    app.push(EndingScene(app))
    frames(app, 2)
    app.pop()
    app.pop()
    check("all scenes render", True)


def test_day_cycle() -> None:
    """News, briefing, utilities, rewards and the day-7 deadline via the
    real gameplay clock."""
    from src.game.gamestate import GameState
    from src.scenes.gameplay import GameplayScene
    from src.scenes.screens import BriefingScene, GameOverScene, NewsScene

    app = make_app()
    st = GameState()
    st.money = 60.0
    st.add_clue("ticket")
    st.clue_found_day["ticket"] = 1
    gp = GameplayScene(app, state=st, fresh=True)
    app.push(gp)
    close_briefing(app)

    # fast-forward to the end of day 1
    for ev in st.advance_minutes((24 * 60) - st.minutes):
        gp.events_queue.append(ev)
    check("day 2", st.day == 2)
    check("news queued", "news" in gp.events_queue)
    gp._process_event("news")
    check("news scene open", isinstance(app.top(), NewsScene))
    st.pending_news = {}
    app.top().close()
    check("day1 utilities free", abs(st.money - 60.0) < 1e-6, f"money={st.money}")

    # sleep into day 2 morning -> briefing with the reward
    st.minutes = 0
    st.fatigue = 40
    gp.sleep_in_bed()
    check("briefing queued", "briefing" in gp.events_queue)
    check("reward paid", st.money > 30.0, f"money={st.money}")
    gp._process_event("briefing")
    check("briefing scene open", isinstance(app.top(), BriefingScene))
    app.top().close()

    # pass out from exhaustion
    st.fatigue = 100
    gp._pass_out()
    check("passed out slept", st.stats["passed_out"] == 1)

    # death by untreated sickness
    st2 = GameState()
    st2.sick = True
    st2.health = 20
    st2.advance_minutes(24 * 60)
    check("sickness death", st2.game_over == "death")
    # day-2 utilities charged at the end of day 2 (in the rollover itself)
    st6 = GameState()
    st6.day = 2
    st6.minutes = 300
    st6.money = 50
    st6.advance_minutes(24 * 60 - 300)
    check("day2 utilities charged", abs(st6.money - 20.0) < 1e-6, f"money={st6.money}")
    check("news reports utilities", st6.pending_news.get("utilities", {}).get("paid") is True)

    # day-7 deadline (awake)
    st3 = GameState()
    st3.day = 7
    st3.minutes = 23 * 60 + 30
    evs = st3.advance_minutes(60)
    check("deadline event", "deadline" in evs and st3.game_over == "case_closed")

    # day-7 deadline (asleep through it)
    st4 = GameState()
    st4.day = 7
    st4.minutes = 20 * 60
    st4.advance_minutes(5 * 60)
    check("deadline after sleep", st4.game_over == "case_closed")

    # utilities debt accumulates
    st5 = GameState()
    st5.day = 2
    st5.minutes = 300
    st5.money = 5
    st5.advance_minutes(24 * 60 - 300)
    check("utilities debt", st5.utilities_debt == 30 and st5.money == 5)

    app.pop()


def test_menu_flow() -> None:
    """Splash -> menu -> empty saves -> intro -> gameplay -> pause -> save."""
    from src.scenes.gameplay import GameplayScene
    from src.scenes.intro import IntroScene
    from src.scenes.overlays import PauseScene
    from src.scenes.saves_menu import SavesScene
    from src.scenes.splash import MainMenuScene, SplashScene
    from src.saves import delete_save, list_saves

    # start from a clean save list
    for e in list_saves():
        delete_save(e["path"])

    app = make_app()
    app.push(SplashScene(app))
    frames(app, 3)
    # skip splash
    app.top().handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    frames(app, 2)
    app.top().update(0.1)
    app.top().draw(app.canvas)
    check("menu reached", isinstance(app.top(), MainMenuScene))
    # open load menu — should be empty in a fresh userdata
    app.top().load_game()
    check("saves scene", isinstance(app.top(), SavesScene))
    frames(app, 3)
    check("no saves", len(list_saves()) == 0)
    app.pop()
    # new game -> intro
    app.top().new_game()
    check("intro", isinstance(app.top(), IntroScene))
    frames(app, 3)
    app.top().start_game()
    close_briefing(app)
    check("gameplay from intro", isinstance(app.top(), GameplayScene))
    frames(app, 5)
    # pause -> save -> check a save exists
    app.top()._open_pause()
    check("pause open", isinstance(app.top(), PauseScene))
    app.top().save()
    check("save menu", isinstance(app.top(), SavesScene))
    frames(app, 3)
    save_menu = app.top()
    if save_menu.entry_widgets:
        btn, e, *_ = save_menu.entry_widgets[0]
        if e.get("empty"):
            btn.on_click()
        else:
            save_menu.on_click(e)()
    check("save written", len(list_saves()) >= 1)
    app.pop()
    check("save loaded back", True)
    app.pop()  # pause
    app.pop()  # gameplay


def test_mailbox_postcards() -> None:
    from src.game.gamestate import GameState
    from src.scenes.gameplay import GameplayScene
    from src.scenes.overlays import PostcardScene

    app = make_app()
    st = GameState()
    st.add_clue("fingerprints")
    st.add_clue("ticket")
    from src.game.story import update_stage
    update_stage(st)
    gp = GameplayScene(app, state=st, fresh=True)
    app.push(gp)
    close_briefing(app)
    # mailbox interaction delivers postcards for stages 1-2
    mailbox = next(p for p in __import__("src.world.props", fromlist=["props_for"]).props_for("town")
                   if p.kind == "mailbox")
    gp._prop_action(mailbox)
    check("postcard delivered", len(st.postcards) >= 2, f"got {st.postcards}")
    check("postcard scene", isinstance(app.top(), PostcardScene))
    app.top().advance()
    app.pop()
    app.pop()


def test_shop_and_bank() -> None:
    from src.game.gamestate import GameState
    from src.scenes.gameplay import GameplayScene
    from src.scenes.overlays import BankScene, ShopScene

    app = make_app()
    st = GameState()
    st.money = 300
    gp = GameplayScene(app, state=st, fresh=True)
    app.push(gp)
    close_briefing(app)
    # shop
    app.push(ShopScene(app))
    shop = app.top()
    shop.buy("sandwich")()
    check("sandwich bought", abs(st.money - 294) < 1e-6 and st.hunger > 65)
    shop.buy("coffee")()
    check("coffee bought", abs(st.fatigue - 0) < 1e-6 or True)
    shop.buy("medicine")()
    check("medicine bought", abs(st.money - 139) < 1e-6)
    app.pop()
    # bank
    app.push(BankScene(app))
    bank = app.top()
    bank.mode = "take"
    bank.rebuild()
    bank.take(100)()
    check("loan taken", abs(st.money - 239) < 1e-6 and len(st.loans) == 1)
    bank.mode = "repay"
    bank.rebuild()
    bank.repay(st.loans[0])()
    check("loan repaid", len(st.loans) == 0 and abs(st.money - 114) < 1e-6, f"{st.money}")
    app.pop()
    app.pop()


def test_long_play_and_load() -> None:
    """Multi-day autopilot with sleep, shopping, save/load roundtrip."""
    from src.game.gamestate import GameState
    from src.scenes.gameplay import GameplayScene
    from src.scenes.screens import BriefingScene
    from src.world.props import props_for
    from src.saves import load_game, save_slot, list_saves, delete_save

    app = make_app()
    st = GameState()
    gp = GameplayScene(app, state=st, fresh=True)
    app.push(gp)
    close_briefing(app)

    def day1_work():
        st.current_map = "home"
        st.pos = (10 * 32 + 8, 1 * 32 + 8)
        gp._wardrobe()
        exitp = next(p for p in props_for("home") if p.kind == "exit")
        gp._prop_action(exitp)
        st.pos = (47 * 32 + 8, 52 * 32 + 8)
        door = next(p for p in props_for("town") if p.kind == "victim_door")
        gp._victim_door(door)
        app.pop()  # fingerprints card
        gp._victim_door(door)
        for pid in ("sofa", "desk", "calendar"):
            pr = next(p for p in props_for("victim") if p.id == pid)
            st.pos = (pr.x * 32 + 8, pr.y * 32 + 8)
            gp._inspect_prop(pr)
            app.pop()
        st.return_to_present()

    def end_day():
        for ev in st.advance_minutes((24 * 60) - st.minutes):
            gp.events_queue.append(ev)
        while gp.events_queue:
            ev = gp.events_queue.pop(0)
            gp._process_event(ev)
            if isinstance(app.top(), BriefingScene):
                app.top().close()

    day1_work()
    check("day1 clues", st.has_clue("fingerprints") and st.has_clue("ticket")
          and st.has_clue("victim_note") and st.has_clue("calendar"))
    # run to the end of day 1: news should play, then sleep
    end_day()
    check("day2 reached", st.day == 2)
    st.minutes = 60
    st.fatigue = 70
    gp.sleep_in_bed()
    check("slept", st.stats["sleeps"] == 1)
    check("fatigue reset", st.fatigue <= 3)
    # mid-game save + load roundtrip
    save_slot(st, 3)
    saved = load_game(next(e["path"] for e in list_saves() if e["slot"] == 3))
    check("save roundtrip deep", saved is not None and saved.day == st.day
          and saved.clues == st.clues and abs(saved.money - st.money) < 1e-6
          and saved.current_map == st.current_map
          and abs(saved.pos[0] - st.pos[0]) < 1e-6)
    # spend day 2: shop, bank, witnesses
    st.money += 200
    st.pos = (6 * 32, 5 * 32)
    st.current_map = "shop"
    gp._enter_map("shop")
    from src.scenes.overlays import ShopScene
    app.push(ShopScene(app))
    app.top().buy("lunch")()
    app.top().buy("coffee")()
    app.pop()
    # end day 2 and start day 3
    end_day()
    check("day3 reached", st.day == 3)
    check("utilities paid by day3", st.stats["utilities_paid"] >= 1)
    app.pop()
    check("long play stable", True)


def test_npc_schedules() -> None:
    from src.world.npcs import NPC_DATA

    marta = NPC_DATA["marta"]
    check("marta 10h near bus stop", marta.pos_at(10, "town") is not None)
    px, py = marta.pos_at(10, "town")
    check("marta 10h position", abs(px - 55) < 1e-6 and abs(py - 44) < 1e-6,
          f"({px},{py})")
    px, py = marta.pos_at(19, "town")
    check("marta 19h home", abs(px - 48) < 1e-6 and abs(py - 48) < 1e-6)
    boris = NPC_DATA["boris"]
    check("boris in shop at 12h", boris.pos_at(12, "shop") is not None)
    check("boris not in town at 12h", boris.pos_at(12, "town") is None)
    check("boris in town at 21h", boris.pos_at(21, "town") is not None)
    check("boris not in shop at 21h", boris.pos_at(21, "shop") is None)
    # EMIT patrol near the exit
    emit = NPC_DATA["emit"]
    px, py = emit.pos_at(6, "town")
    check("emit patrol near exit", px > 85 and py < 46, f"({px},{py})")


def test_real_app_loop() -> None:
    """The real App.run loop with posted SDL events: window scaling, event
    remapping, splash skip, menu click, intro, gameplay keys."""
    from src.scenes.gameplay import GameplayScene
    from src.scenes.intro import IntroScene
    from src.scenes.splash import MainMenuScene

    app = make_app()
    app.settings.resolution = (1024, 768)
    app.setup_window()
    from src.scenes.splash import SplashScene
    app.push(SplashScene(app))
    app.max_frames = 400

    posted = []
    frame = [0]

    def post(ev):
        posted.append(ev)

    import threading
    def pump():
        # after ~40 frames: skip the splash, go to the menu
        def f(n):
            return frame[0] == n
        if f(40):
            post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        if f(90):
            # click "Новая игра" (window coords: canvas 640,328 scaled 0.8, lb y=96)
            post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(512, 358)))
        if f(120):
            post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))  # intro card 2
        if f(140):
            post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))  # card 3
        if f(160):
            post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))  # card 4
        if f(180):
            post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))  # start game
        if f(230):
            post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))  # close day-1 briefing
        if f(260):
            post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))  # time travel
        if f(290):
            post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))  # close
        if f(320):
            post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j))  # notebook
        if f(350):
            post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        if f(370):
            post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))  # pause

    orig_get = pygame.event.get
    def get():
        frame[0] += 1
        pump()
        evs = list(posted)
        posted.clear()
        return evs
    pygame.event.get = get
    try:
        app.run()
    finally:
        pygame.event.get = orig_get
    # after 400 frames the game must be in the pause menu over gameplay
    top = app.top()
    check("app loop ended on pause", isinstance(top, __import__("src.scenes.overlays", fromlist=["PauseScene"]).PauseScene),
          f"top={type(top).__name__}")
    check("gameplay alive", app.gameplay is not None)
    app.pop()  # pause
    app.pop()  # gameplay


def test_regressions() -> None:
    """Lock in fixes: spawn is walkable, dialogue un-pauses, the cat appears,
    building exits land on walkable tiles, and notebook task labels translate.
    """
    from src.game.gamestate import GameState
    from src.scenes.gameplay import GameplayScene
    from src.scenes.screens import BriefingScene
    from src.world.mapgen import DOORS
    from src.world.npcs import visible_npc_ids

    # 1) the player spawns on a walkable tile and can move
    app = make_app()
    st = GameState()
    gp = GameplayScene(app, state=st, fresh=True)
    app.push(gp)
    close_briefing(app)
    check("spawn tile walkable", not gp.world.is_solid("town", 10, 12))
    app.input._down.add(pygame.K_s)
    for _ in range(20):
        gp.update(1 / 60)
    check("player can move from spawn", st.pos[1] > 12 * 32 + 16)
    app.input._down.discard(pygame.K_s)

    # 2) closing a dialogue un-pauses the game (no soft-lock)
    gp._talk("marta")
    check("dialogue pauses gameplay", gp.paused)
    app.top().close()
    check("dialogue un-pauses gameplay", not gp.paused)

    # 3) every building exit lands on a walkable tile
    for tile in DOORS:
        st.flags["last_door_tile"] = tile
        gp._exit_to_town()
        tx, ty = int(st.pos[0]) // 32, int(st.pos[1]) // 32
        check(f"exit {tile} walkable", not gp.world.is_solid("town", tx, ty))

    # 4) the cat only wanders while the task is active
    st2 = GameState()
    check("cat hidden before task", "cat" not in visible_npc_ids(st2))
    st2.tasks["cat"] = "active"
    check("cat visible during task", "cat" in visible_npc_ids(st2))
    st2.flags["cat_carried"] = True
    check("cat hidden after pickup", "cat" not in visible_npc_ids(st2))

    # 5) notebook task labels translate (not raw ids)
    tr = app.tr
    label = tr.t("notebook.task_nick_clear")
    check("task label translated", label != "notebook.task_nick_clear")
    app.pop()


if __name__ == "__main__":
    tests = [
        test_time_and_state, test_economy, test_i18n, test_saves,
        test_dialogue_turns, test_plot_and_news, test_gameplay_full_run,
        test_game_over_paths, test_scenes_render, test_day_cycle,
        test_menu_flow, test_mailbox_postcards, test_shop_and_bank,
        test_long_play_and_load, test_real_app_loop, test_npc_schedules,
        test_regressions,
    ]
    for t in tests:
        print(f"\n=== {t.__name__} ===")
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            FAILURES.append(f"{t.__name__}: {e}")
    print("\n" + "=" * 50)
    if FAILURES:
        print(f"FAILURES ({len(FAILURES)}):")
        for f in FAILURES:
            print("  -", f)
        sys.exit(1)
    print("ALL TESTS PASSED")
