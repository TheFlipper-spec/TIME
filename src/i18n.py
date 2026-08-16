"""Translation system.

Offline dictionaries ship for Russian (ru) and English (en).
For any other language the game translates itself on the fly through the
Yandex Translate API when a key is configured (Settings → «Яндекс Перевод»,
or env vars YANDEX_API_KEY / YANDEX_IAM_TOKEN + YANDEX_FOLDER_ID).
All translations are cached on disk, so a language is translated only once.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from .config import CACHE_DIR, LANG_DIR
from .settings import LANGUAGES, OFFLINE_LANGS

_API_LEGACY = "https://translate.yandex.net/api/v1.5/tr.json/translate"
_API_CLOUD = "https://translate.api.cloud.yandex.net/translate/v2/translate"


class TranslationError(Exception):
    pass


class Translator:
    def __init__(self) -> None:
        self._lang = "ru"
        self._dicts: dict[str, dict[str, str]] = {}
        self._cache: dict[str, dict[str, str]] = {}   # lang -> text -> translation
        self._lock = threading.Lock()
        self._settings_provider = None
        self._load_offline("ru")
        self._load_offline("en")

    def bind_settings(self, provider) -> None:
        """Give the translator access to the live Settings (for the Yandex key)."""
        self._settings_provider = provider

    # ------------------------------------------------------------- setup --
    def _load_offline(self, lang: str) -> None:
        path = LANG_DIR / f"{lang}.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        # flatten nested sections into dot-keys: {"menu": {"new_game": ...}}
        flat: dict[str, str] = {}
        for key, val in raw.items():
            if isinstance(val, dict):
                for k2, v2 in val.items():
                    flat[f"{key}.{k2}"] = v2
            else:
                flat[key] = val
        self._dicts[lang] = flat

    def set_language(self, lang: str) -> None:
        if lang in LANGUAGES:
            self._lang = lang

    @property
    def language(self) -> str:
        return self._lang

    # --------------------------------------------------------- offline UI --
    def t(self, key: str, **fmt) -> str:
        """Translate a UI string by key (fast, offline for ru/en)."""
        lang = self._lang
        text = self._dicts.get(lang, {}).get(key)
        if text is None:
            text = self._dicts.get("ru", {}).get(key, key)
        if fmt:
            try:
                text = text.format(**fmt)
            except Exception:
                pass
        return text

    def tr_text(self, text: str, lang: Optional[str] = None) -> str:
        """Translate an arbitrary string into the current language.

        ru/en are returned as-is (they are authored offline). For other
        languages, tries the cached copy, then the Yandex API (if configured),
        and finally falls back to English or the original text.
        """
        lang = lang or self._lang
        if lang in OFFLINE_LANGS:
            return text
        if not text or text.strip() == "":
            return text
        with self._lock:
            cache = self._cache.setdefault(lang, {})
            if text in cache:
                return cache[text]
        # Check disk cache
        disk = self._load_disk_cache(lang)
        with self._lock:
            if text in disk:
                self._cache.setdefault(lang, {})[text] = disk[text]
                return disk[text]
        # Try API; on any failure fall back to English.
        try:
            translated = self._yandex_translate(text, lang)
        except Exception:
            translated = self._fallback(text)
        with self._lock:
            self._cache.setdefault(lang, {})[text] = translated
        self._save_disk_cache(lang)
        return translated

    def tr_batch(self, texts: list[str], lang: Optional[str] = None) -> list[str]:
        lang = lang or self._lang
        if lang in OFFLINE_LANGS:
            return list(texts)
        out: list[str] = []
        missing: list[tuple[int, str]] = []
        with self._lock:
            cache = self._cache.setdefault(lang, {})
            disk = self._load_disk_cache(lang)
            for i, t in enumerate(texts):
                if t in cache:
                    out.append(cache[t])
                elif t in disk:
                    cache[t] = disk[t]
                    out.append(cache[t])
                else:
                    out.append("")
                    missing.append((i, t))
        if missing:
            try:
                translated = self._yandex_translate_batch([t for _, t in missing], lang)
            except Exception:
                translated = [self._fallback(t) for t, _ in missing]
            with self._lock:
                cache = self._cache.setdefault(lang, {})
                for (i, _), tr in zip(missing, translated):
                    cache[texts[i]] = tr
                    out[i] = tr
            self._save_disk_cache(lang)
        return out

    def _fallback(self, text: str) -> str:
        # Fallback order: English -> original (Russian).
        return self._dicts.get("en", {}).get(text, text)

    # ------------------------------------------------------------ cache ----
    def _cache_file(self, lang: str) -> Path:
        return CACHE_DIR / f"translations_{lang}.json"

    def _load_disk_cache(self, lang: str) -> dict[str, str]:
        try:
            p = self._cache_file(lang)
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_disk_cache(self, lang: str) -> None:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            data = {}
            for l, m in self._cache.items():
                if l == lang:
                    data.update(m)
            p = self._cache_file(lang)
            old = {}
            if p.exists():
                try:
                    old = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    old = {}
            old.update(data)
            p.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ------------------------------------------------------ yandex api ----
    def _yandex_translate(self, text: str, lang: str) -> str:
        return self._yandex_translate_batch([text], lang)[0]

    def _yandex_translate_batch(self, texts: list[str], lang: str) -> list[str]:
        if not texts:
            return []
        yandex_lang = LANGUAGES[lang][1]
        # 1) Yandex Cloud v2 (IAM token + folder id) — modern API.
        token = self._iam_token()
        if token:
            payload = {
                "folderId": self._folder_id(),
                "texts": texts,
                "targetLanguageCode": yandex_lang,
                "sourceLanguageCode": "ru",
                "format": "PLAIN_TEXT",
            }
            req = urllib.request.Request(
                _API_CLOUD,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            out = [t.get("text", "") for t in data.get("translations", [])]
            if len(out) != len(texts):
                raise TranslationError("unexpected cloud response")
            return out
        # 2) Legacy free API key.
        key = self._api_key()
        if key:
            form = urllib.parse.urlencode(
                [("key", key), ("lang", f"ru-{yandex_lang}"), ("format", "plain")]
                + [("text", t) for t in texts]
            ).encode("utf-8")
            req = urllib.request.Request(_API_LEGACY, data=form)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") != 200:
                raise TranslationError(data.get("message", "yandex error"))
            out = data.get("text", [])
            if len(out) != len(texts):
                raise TranslationError("unexpected legacy response")
            return out
        raise TranslationError("no yandex credentials")

    def _api_key(self) -> Optional[str]:
        if self._settings_provider is None:
            return None
        return self._settings_provider().effective_key()

    def _iam_token(self) -> Optional[str]:
        if self._settings_provider is None:
            return ""
        return self._settings_provider().yandex_iam_token or ""

    def _folder_id(self) -> str:
        if self._settings_provider is None:
            return ""
        return self._settings_provider().yandex_folder_id or ""
