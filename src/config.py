"""Global paths and constants."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------- paths ----
# Project root: the folder containing the `src` package.
ROOT = Path(__file__).resolve().parent.parent

ASSETS = ROOT / "assets"
FONTS_DIR = ASSETS / "fonts"
LANG_DIR = ASSETS / "lang"

# Runtime data lives next to the game (portable), overridable via env var.
USERDATA = Path(os.environ.get("TIME_USERDATA", str(ROOT / "userdata")))
SAVES_DIR = USERDATA / "saves"
CACHE_DIR = USERDATA / "cache"
CONFIG_PATH = USERDATA / "config.json"

DEBUG = os.environ.get("TIME_DEBUG", "0") == "1"

# ----------------------------------------------------------- design res ----
# The whole game is rendered at a fixed internal resolution and then scaled
# to the window, so any screen resolution / aspect ratio works.
DESIGN_W, DESIGN_H = 1280, 720
FPS = 60

# ------------------------------------------------------------ time model ----
# One full game day (24h) lasts 30 real minutes => 48 game minutes per real
# minute => 0.8 game minutes per real second.
REAL_SECONDS_PER_GAME_DAY = 30 * 60
GAME_MINUTES_PER_REAL_SECOND = 24 * 60 / REAL_SECONDS_PER_GAME_DAY

MINUTES_PER_DAY = 24 * 60
GAME_DAYS_TOTAL = 7                 # the case closes after 7 days
DAY_START_MINUTE = 6 * 60           # Mike wakes at 06:00
DAY_START_DATE = (2023, 11, 25)     # Day 1 starts 25 Nov 2023

# Time travel range: up to 7 days into the past.
TRAVEL_MAX_BACK_MIN = 7 * MINUTES_PER_DAY
TRAVEL_MIN_OFFSET = -TRAVEL_MAX_BACK_MIN
TRAVEL_MAX_OFFSET = 0

# ------------------------------------------------------------ economy -----
START_MONEY = 50.0
UTILITIES_PER_DAY = 30.0           # paid at the end of every day except day 1
LOAN_INTEREST = 0.25               # +25% must be repaid within 3 days
LOAN_DAYS = 3
LOAN_MIN, LOAN_MAX = 20, 500
MEDICINE_PRICE = 150.0
BED_MIN_SLEEP_HOURS = 1            # least sleep possible at the bed
BED_MAX_SLEEP_HOURS = 16           # pass-out / max fatigue sleep

# ------------------------------------------------------------------ misc ---
TILE = 32                          # pixel-art tile size
INTERACTION_DIST = 1.6             # tiles
MAX_SAVE_SLOTS = 6
