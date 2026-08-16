"""The full investigation state: time, money, health, clues, plot."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from ..config import (
    DAY_START_MINUTE,
    GAME_DAYS_TOTAL,
    MINUTES_PER_DAY,
    START_MONEY,
    TRAVEL_MAX_OFFSET,
    TRAVEL_MIN_OFFSET,
)


@dataclass
class GameState:
    # ---- time -------------------------------------------------------------
    day: int = 1
    minutes: int = DAY_START_MINUTE          # 06:00
    offset_min: int = 0                      # time-travel offset (<= 0)
    play_seconds: float = 0.0

    # ---- body -------------------------------------------------------------
    money: float = START_MONEY
    fatigue: float = 10.0                    # 0..100
    hunger: float = 65.0                     # 0..100
    health: float = 100.0                    # 0..100
    sick: bool = False
    dressed: bool = False

    # ---- investigation -----------------------------------------------------
    clues: list[str] = field(default_factory=list)          # clue ids found
    clue_found_day: dict = field(default_factory=dict)      # id -> day
    witnesses_met: list[str] = field(default_factory=list)
    tasks: dict = field(default_factory=dict)               # id -> active/done
    support: float = 40.0
    plot_stage: int = 0
    postcards: list[int] = field(default_factory=list)      # received ids
    seen_postcards: list[int] = field(default_factory=list)
    notebook_notes: list[dict] = field(default_factory=list)  # auto notes
    pending_briefing: bool = False
    pending_news: dict = field(default_factory=dict)
    utilities_debt: float = 0.0
    loans: list = field(default_factory=list)

    # ---- stats -------------------------------------------------------------
    stats: dict = field(default_factory=lambda: {
        "money_earned": 0.0,
        "clues_total": 0,
        "witnesses_total": 0,
        "meals": 0,
        "coffees": 0,
        "sleeps": 0,
        "passed_out": 0,
        "utilities_paid": 0,
        "utilities_missed": 0,
        "loans_taken": 0,
        "loans_repaid": 0,
        "times_traveled": 0,
        "postcards_received": 0,
        "intimidations": 0,
        "chase": 0,
    })

    # ---- world position -----------------------------------------------------
    current_map: str = "town"
    pos: tuple = (0.0, 0.0)
    facing: str = "down"

    # ---- meta ----------------------------------------------------------------
    game_over: str | None = None             # reason id, if the game ended
    ending: bool = False                     # true ending reached
    tutorial_done: list = field(default_factory=list)
    flags: dict = field(default_factory=dict)
    new_game: bool = True

    # ------------------------------------------------------------------ time --
    @property
    def total_min(self) -> int:
        return (self.day - 1) * MINUTES_PER_DAY + self.minutes

    @property
    def days_left(self) -> int:
        return GAME_DAYS_TOTAL - self.day

    def advance_minutes(self, amount: float) -> list[str]:
        """Advance the clock; returns the list of events that happened.

        Events: 'news' (day rollover with news+utilities+health),
                'briefing' (06:00 day start with clue rewards),
                'deadline' (day 7 ended without a solution),
                'loan' (overdue loan -> apartment taken),
                'death' (health reached zero).
        """
        events: list[str] = []
        total = self.minutes + amount
        crossed = 0
        while total >= MINUTES_PER_DAY:
            total -= MINUTES_PER_DAY
            crossed += 1
        if crossed:
            for _ in range(crossed):
                self._rollover(events)
            self.minutes = int(total) % MINUTES_PER_DAY
            if self.game_over:
                return events
        else:
            self.minutes = int(total) % MINUTES_PER_DAY
        # day-start briefing: once per day, when the clock passes 06:00
        if (self.day > 1 and self.minutes >= DAY_START_MINUTE
                and self.day != self.flags.get("briefed_day", 0)
                and not self.pending_briefing):
            self.pending_briefing = True
            events.append("briefing")
        # loan deadlines are checked continuously
        if self._check_loans():
            events.append("loan")
        # final deadline: end of day 7 (awake path)
        if (self.day >= GAME_DAYS_TOTAL and self.minutes >= MINUTES_PER_DAY - 1
                and not self.ending and not self.game_over):
            self.game_over = "case_closed"
            events.append("deadline")
        if self.health <= 0 and not self.game_over:
            self.game_over = "death"
            events.append("death")
        return events

    def _rollover(self, events: list[str]) -> None:
        """Midnight rollover: new day begins."""
        self.day += 1
        # health drains
        drained = False
        if self.sick:
            self.health -= 25
            drained = True
        if self.hunger <= 0:
            self.health -= 15
            drained = True
        if drained:
            events.append("health")
        if self.health <= 0:
            self.game_over = "death"
            events.append("death")
            return
        # sickness chance if the day ended exhausted
        if self.fatigue >= 90 and not self.sick:
            if random.random() < 0.15:
                self.sick = True
        # the case closes if the 7th day ends without a solution
        if self.day > GAME_DAYS_TOTAL and not self.ending:
            self.game_over = "case_closed"
            events.append("deadline")
            return
        # news + utilities for the ended day (payment happens here, the
        # news screen only reports it)
        self.pending_news = {"for_day": self.day - 1}
        # utilities are charged for every ended day except the first one
        if self.day >= 3:
            from .economy import pay_utilities
            paid, amount = pay_utilities(self)
            self.pending_news["utilities"] = {"paid": paid, "amount": amount}
        events.append("news")

    def _check_loans(self) -> bool:
        overdue = [l for l in self.loans if self.total_min > l["due_min"]]
        if overdue:
            self.game_over = "loan"
            return True
        return False

    # ------------------------------------------------------------- travel ---
    def can_travel(self, new_offset: int) -> bool:
        return TRAVEL_MIN_OFFSET <= new_offset <= TRAVEL_MAX_OFFSET

    def travel_to(self, new_offset: int) -> bool:
        if not self.can_travel(new_offset):
            return False
        if new_offset != self.offset_min:
            self.offset_min = new_offset
            self.stats["times_traveled"] += 1
        return True

    def return_to_present(self) -> None:
        if self.offset_min != 0:
            self.offset_min = 0
            self.stats["times_traveled"] += 1

    # ----------------------------------------------------------- economy ----
    def earn(self, amount: float, source: str = "clue") -> None:
        self.money += amount
        self.stats["money_earned"] += amount

    def add_clue(self, clue_id: str) -> bool:
        """Register a discovered clue; returns True if it is new."""
        if clue_id in self.clues:
            return False
        self.clues.append(clue_id)
        self.clue_found_day[clue_id] = self.day
        self.stats["clues_total"] += 1
        return True

    def add_note(self, title_ru: str, text_ru: str, title_en: str, text_en: str,
                 clue_id: str | None = None) -> None:
        self.notebook_notes.append({
            "title": {"ru": title_ru, "en": title_en},
            "text": {"ru": text_ru, "en": text_en},
            "clue": clue_id,
        })

    # -------------------------------------------------------------- sleep ----
    def sleep_hours(self) -> int:
        """How long Mike sleeps now (fatigue-dependent)."""
        hours = max(1, min(16, int(round(16.0 * self.fatigue / 100.0))))
        return hours

    def do_sleep(self, passed_out: bool = False) -> int:
        hours = 16 if passed_out else self.sleep_hours()
        self.fatigue = 3.0
        # Sleep restores some health (documented in the player guide).
        self.health = min(100.0, self.health + hours)
        self.stats["sleeps"] += 1
        if passed_out:
            self.stats["passed_out"] += 1
            if not self.sick and random.random() < 0.25:
                self.sick = True
        return hours

    def fatigue_gain_per_minute(self, sprinting: bool) -> float:
        base = 5.0 / 60.0
        return base * (1.5 if sprinting else 1.0)

    def hunger_gain_per_minute(self) -> float:
        return -3.0 / 60.0

    @property
    def speed_multiplier(self) -> float:
        m = 1.0
        if self.fatigue > 60:
            m *= 0.7
        if self.sick:
            m *= 0.75
        return m

    @property
    def intimidation_chance(self) -> float:
        base = 0.40 + self.support / 100.0 * 0.20
        if self.sick:
            base -= 0.20
        return max(0.05, min(0.85, base))

    # -------------------------------------------------------------- helpers --
    def has_clue(self, clue_id: str) -> bool:
        return clue_id in self.clues

    def total_minutes_int(self) -> int:
        return int(self.total_min)

    def lang_dict(self, d: dict, lang: str) -> str:
        return d.get(lang) or d.get("en") or d.get("ru") or ""
