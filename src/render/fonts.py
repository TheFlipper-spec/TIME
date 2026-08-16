"""Font loading and caching."""
from __future__ import annotations

import pygame

from ..config import FONTS_DIR

_fonts: dict[tuple[str, int], pygame.font.Font] = {}
_cjk_fonts: dict[int, pygame.font.Font] = {}

_FILES = {
    "sans": FONTS_DIR / "DejaVuSans.ttf",
    "sans_bold": FONTS_DIR / "DejaVuSans-Bold.ttf",
    "serif_bold": FONTS_DIR / "DejaVuSerif-Bold.ttf",
}

# System fonts that can render CJK (Chinese/Japanese/Korean) when the game is
# auto-translated into those languages.
_CJK_CANDIDATES = (
    "notosanscjk", "notosanscjksc", "notosanscjkregular", "microsoftyahei",
    "msyh", "pingfang", "hiraginosansgb", "wqymicrohei", "wenquanyimicrohei",
    "droidsansfallback", "sourcehansanscn", "simhei",
)


def has_cjk(text: str) -> bool:
    return any(0x2E80 <= ord(c) <= 0x9FFF or 0xAC00 <= ord(c) <= 0xD7AF
               or 0xF900 <= ord(c) <= 0xFAFF for c in text)


def get_cjk(size: int = 20) -> pygame.font.Font:
    if size not in _cjk_fonts:
        try:
            path = pygame.font.match_font(_CJK_CANDIDATES)
        except Exception:
            path = None
        _cjk_fonts[size] = pygame.font.Font(path, size) if path else get("sans", size)
    return _cjk_fonts[size]


def get(kind: str = "sans", size: int = 20) -> pygame.font.Font:
    key = (kind, size)
    if key not in _fonts:
        path = _FILES.get(kind)
        try:
            _fonts[key] = pygame.font.Font(str(path), size)
        except Exception:
            _fonts[key] = pygame.font.Font(None, size)
    return _fonts[key]


def measure(text: str, kind: str = "sans", size: int = 20) -> tuple[int, int]:
    return get(kind, size).size(text)
