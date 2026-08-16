"""Game clock: days, minutes, real-time flow, date formatting."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from ..config import DAY_START_DATE, GAME_MINUTES_PER_REAL_SECOND

MONTHS_RU = ["", "янв", "фев", "мар", "апр", "мая", "июн",
             "июл", "авг", "сен", "окт", "ноя", "дек"]
MONTHS_EN = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS_RU = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
WEEKDAYS_EN = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


def game_minutes_from_real(dt: float) -> float:
    return dt * GAME_MINUTES_PER_REAL_SECOND


def base_date() -> date:
    return date(*DAY_START_DATE)


def game_date(day: int) -> date:
    return base_date() + timedelta(days=day - 1)


def world_datetime(day: int, minutes: int, offset_min: int) -> datetime:
    """Absolute date-time of the observed world (present + time-travel offset)."""
    return datetime.combine(game_date(day), datetime.min.time()) + timedelta(
        minutes=minutes + offset_min
    )


def fmt_clock(minutes: int) -> str:
    minutes = int(minutes) % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def fmt_date(dt: datetime, lang: str = "ru") -> str:
    months = MONTHS_RU if lang == "ru" else MONTHS_EN
    wd = WEEKDAYS_RU if lang == "ru" else WEEKDAYS_EN
    return f"{wd[dt.weekday()]} {dt.day} {months[dt.month]} {dt.year}"


def fmt_date_short(dt: datetime, lang: str = "ru") -> str:
    months = MONTHS_RU if lang == "ru" else MONTHS_EN
    return f"{dt.day} {months[dt.month]} {dt.year}"


def fmt_datetime(day: int, minutes: int, offset_min: int, lang: str = "ru") -> str:
    dt = world_datetime(day, minutes, offset_min)
    return f"{fmt_date(dt, lang)} · {fmt_clock(minutes)}"


def parse_world_datetime(day: int, minutes: int, offset_min: int) -> datetime:
    return world_datetime(day, minutes, offset_min)
