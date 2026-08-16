"""User settings: resolution, language, volumes, Yandex key.

Persisted as JSON in userdata/config.json.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Optional

import pygame

from .config import CONFIG_PATH, DESIGN_W, DESIGN_H

# Languages offered in the switcher: id -> (display name, yandex code).
# `ru` and `en` are fully offline; the rest use Yandex Translate when a key
# is configured (otherwise the UI falls back to English).
LANGUAGES: dict[str, tuple[str, str]] = {
    "ru": ("Русский", "ru"),
    "en": ("English", "en"),
    "de": ("Deutsch", "de"),
    "fr": ("Français", "fr"),
    "es": ("Español", "es"),
    "it": ("Italiano", "it"),
    "pl": ("Polski", "pl"),
    "uk": ("Українська", "uk"),
    "tr": ("Türkçe", "tr"),
    "zh": ("中文", "zh"),
}
DEFAULT_LANG = "ru"
OFFLINE_LANGS = ("ru", "en")


def desktop_resolutions() -> list[tuple[int, int]]:
    """Resolutions offered in Settings: the user's desktop one first."""
    seen: list[tuple[int, int]] = []
    try:
        modes = pygame.display.get_desktop_sizes()
    except Exception:
        modes = []
    for m in modes:
        if m not in seen:
            seen.append(m)
    fallback = [(1920, 1080), (1600, 900), (1536, 864), (1366, 768),
                (1280, 720), (1024, 576), (800, 600)]
    for m in fallback:
        if m not in seen and m[0] >= 800:
            seen.append(m)
    if (DESIGN_W, DESIGN_H) not in seen:
        seen.append((DESIGN_W, DESIGN_H))
    return seen


@dataclass
class Settings:
    resolution: tuple[int, int] = field(default_factory=lambda: desktop_resolutions()[0])
    fullscreen: bool = False
    language: str = DEFAULT_LANG
    sfx_volume: float = 0.8
    music_volume: float = 0.5
    yandex_api_key: str = ""
    yandex_folder_id: str = ""          # for Yandex Cloud (optional)
    yandex_iam_token: str = ""          # for Yandex Cloud (optional)

    def __post_init__(self) -> None:
        if not isinstance(self.resolution, (tuple, list)) or len(self.resolution) != 2:
            self.resolution = (DESIGN_W, DESIGN_H)
        self.resolution = (int(self.resolution[0]), int(self.resolution[1]))
        if self.language not in LANGUAGES:
            self.language = DEFAULT_LANG

    @property
    def yandex_configured(self) -> bool:
        return bool(self.yandex_api_key or self.yandex_iam_token)

    def load(self) -> "Settings":
        try:
            if CONFIG_PATH.exists():
                raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                for k, v in raw.items():
                    if hasattr(self, k):
                        setattr(self, k, v)
        except Exception:
            pass
        self.__post_init__()
        return self

    def save(self) -> None:
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(
                json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def effective_key(self) -> Optional[str]:
        """Yandex legacy API key: from settings or environment."""
        return self.yandex_api_key or os.environ.get("YANDEX_API_KEY") or None
