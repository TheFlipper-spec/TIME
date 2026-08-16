"""Procedural audio: all SFX and ambient music are synthesized in memory.

No external files are needed; everything is generated with plain math so the
game is fully self-contained. If no audio device is available the mixer is
disabled gracefully and the game keeps running silently.
"""
from __future__ import annotations

import array
import math
import random

import pygame

_ENABLED = False
_sounds: dict[str, pygame.mixer.Sound] = {}
_music_channel = None
_current_theme = None
_sfx_volume = 0.8
_music_volume = 0.5

SR = 22050


def init() -> bool:
    global _ENABLED, _music_channel
    try:
        pygame.mixer.pre_init(SR, -16, 1, 512)
        pygame.mixer.init(SR, -16, 1, 512)
        pygame.mixer.set_num_channels(12)
        _music_channel = pygame.mixer.Channel(11)
        _ENABLED = True
        _build_all()
        return True
    except Exception:
        _ENABLED = False
        return False


def enabled() -> bool:
    return _ENABLED


def set_sfx_volume(v: float) -> None:
    global _sfx_volume
    _sfx_volume = max(0.0, min(1.0, v))


def set_music_volume(v: float) -> None:
    global _music_volume
    _music_volume = max(0.0, min(1.0, v))
    if _music_channel is not None:
        _music_channel.set_volume(_music_volume * 0.5)


# ------------------------------------------------------------- synthesis ---
def _make_sound(samples: list[float]) -> pygame.mixer.Sound:
    arr = array.array("h", (int(max(-1.0, min(1.0, s)) * 32767) for s in samples))
    snd = pygame.mixer.Sound(buffer=arr.tobytes())
    snd.set_volume(_sfx_volume)
    return snd


def _env(i: int, n: int, attack: float = 0.01, release: float = 0.3) -> float:
    """Simple AD envelope: linear attack then exponential-ish release."""
    t = i / n
    a = min(1.0, i / max(1, n * attack))
    r = math.exp(-t / max(0.05, release * 2.0))
    return a * r


def _tone(freq: float, dur: float, vol: float = 0.5, attack: float = 0.01,
          release: float = 0.25, harmonics: tuple[float, ...] = (1.0,)) -> list[float]:
    n = int(SR * dur)
    out: list[float] = []
    for i in range(n):
        t = i / SR
        s = 0.0
        for h, w in enumerate(harmonics, start=1):
            s += w * math.sin(2 * math.pi * freq * h * t)
        s /= sum(harmonics) if harmonics else 1
        out.append(s * vol * _env(i, n, attack, release))
    return out


def _noise(dur: float, vol: float = 0.4, lp: float = 0.0, attack: float = 0.01,
           release: float = 0.2, seed: int = 1) -> list[float]:
    """White noise with optional one-pole low-pass."""
    rng = random.Random(seed)
    n = int(SR * dur)
    out: list[float] = []
    prev = 0.0
    for i in range(n):
        x = rng.uniform(-1, 1)
        if lp > 0:
            prev += lp * (x - prev)
            x = prev
        out.append(x * vol * _env(i, n, attack, release))
    return out


def _mix(*tracks: list[float]) -> list[float]:
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    peak = max(1.0, max(abs(v) for v in out))
    return [v / peak * 0.9 for v in out]


# ---------------------------------------------------------------- build ----
def _build_all() -> None:
    def add(name: str, samples: list[float]) -> None:
        _sounds[name] = _make_sound(samples)

    add("click", _tone(700, 0.05, 0.35, attack=0.005, release=0.15))
    add("hover", _tone(1100, 0.03, 0.15, attack=0.005, release=0.2))
    add("back", _tone(500, 0.08, 0.3, attack=0.005, release=0.25) +
                _tone(350, 0.1, 0.25, attack=0.02, release=0.3))
    add("confirm", _tone(520, 0.07, 0.3, release=0.2) + _tone(780, 0.09, 0.3, release=0.25))
    # two-note chime for a found clue
    add("clue", _mix(_tone(659, 0.12, 0.4, release=0.3), _tone(880, 0.22, 0.35, attack=0.08, release=0.4)))
    add("coin", _mix(_tone(987, 0.08, 0.3, release=0.2), _tone(1318, 0.25, 0.3, attack=0.06, release=0.4)))
    add("notebook", _mix(_noise(0.12, 0.25, lp=0.5, seed=7), _noise(0.1, 0.18, lp=0.3, seed=8, attack=0.05)))
    add("postcard", _mix(_tone(440, 0.1, 0.3, release=0.2), _tone(554, 0.1, 0.3, attack=0.07, release=0.2),
                         _tone(659, 0.3, 0.3, attack=0.14, release=0.45)))
    add("whoosh", _mix(_noise(0.7, 0.5, lp=0.0, release=0.6, seed=3),
                       _tone(220, 0.7, 0.2, attack=0.3, release=0.5)))
    add("whoosh_rev", _mix(_noise(0.7, 0.5, lp=0.0, release=0.6, seed=4),
                           _tone(180, 0.7, 0.2, attack=0.3, release=0.5)))
    add("sleep", _mix(_tone(196, 1.2, 0.25, attack=0.3, release=0.8),
                      _tone(147, 1.2, 0.2, attack=0.4, release=0.8)))
    add("wake", _mix(_tone(392, 0.15, 0.25, release=0.3), _tone(523, 0.25, 0.25, attack=0.08, release=0.4)))
    add("alert", _mix(_tone(320, 0.12, 0.35, release=0.2), _tone(240, 0.18, 0.35, attack=0.1, release=0.3)))
    add("error", _tone(180, 0.25, 0.35, attack=0.01, release=0.4) + _tone(140, 0.3, 0.3, attack=0.05, release=0.5))
    add("sick", _noise(0.35, 0.4, lp=0.25, release=0.4, seed=11) + _tone(120, 0.3, 0.2, release=0.4))
    add("eat", _mix(_noise(0.25, 0.3, lp=0.4, seed=5), _noise(0.2, 0.2, lp=0.6, seed=6, attack=0.1)))
    add("door", _tone(90, 0.18, 0.5, attack=0.01, release=0.3) + _noise(0.1, 0.15, lp=0.3, seed=9))
    add("step", _tone(70, 0.06, 0.08, attack=0.005, release=0.2) + _noise(0.05, 0.05, lp=0.5, seed=10))
    add("chase", _mix(*[_tone(60 + i * 8, 0.09, 0.35, release=0.15) for i in range(6)]))
    add("gunshot", _mix(_noise(0.35, 0.8, lp=0.0, attack=0.001, release=0.25, seed=13),
                        _tone(55, 0.4, 0.6, attack=0.001, release=0.4)))
    add("news", _mix(_tone(523, 0.14, 0.35, release=0.2), _tone(659, 0.14, 0.35, attack=0.1, release=0.2),
                     _tone(784, 0.3, 0.35, attack=0.2, release=0.5)))
    add("type", _noise(0.02, 0.05, lp=0.7, seed=21))


# ---------------------------------------------------------------- public ---
def play(name: str, volume: float = 1.0) -> None:
    if not _ENABLED:
        return
    snd = _sounds.get(name)
    if snd is None:
        return
    try:
        snd.set_volume(_sfx_volume * volume)
        snd.play()
    except Exception:
        pass


# ---------------------------------------------------------------- themes ---
def _pad_theme(chords: list[tuple[float, ...]], dur_per_chord: float, vol: float,
               bass: bool = True, seed: int = 1) -> pygame.mixer.Sound:
    rng = random.Random(seed)
    out: list[float] = []
    for chord in chords:
        n = int(SR * dur_per_chord)
        for i in range(n):
            t = i / SR
            s = 0.0
            for c, f in enumerate(chord):
                detune = 1.0 + rng.uniform(-0.002, 0.002)
                vib = 1.0 + 0.002 * math.sin(2 * math.pi * 0.2 * t + c)
                s += math.sin(2 * math.pi * f * detune * vib * t) * (0.5 / len(chord))
            if bass:
                s += 0.22 * math.sin(2 * math.pi * chord[0] * 0.5 * t)
            # slow breathing LFO
            lfo = 0.7 + 0.3 * math.sin(2 * math.pi * 0.1 * t + seed)
            # gentle crossfade between chords
            fade = min(1.0, i / (0.25 * n), (n - i) / (0.25 * n))
            out.append(s * vol * lfo * max(0.0, fade))
    peak = max(1.0, max(abs(v) for v in out))
    return _make_sound([v / peak * 0.85 for v in out])


_THEMES: dict[str, pygame.mixer.Sound] = {}


def play_theme(name: str) -> None:
    global _current_theme
    if not _ENABLED or _music_channel is None:
        return
    if _current_theme == name:
        return
    _current_theme = name
    if not _THEMES:
        # A minor — F — C — G: calm, slightly mysterious investigation pad.
        _THEMES["day"] = _pad_theme(
            [(110.0, 130.81, 164.81), (87.31, 110.0, 130.81),
             (65.41, 98.0, 130.81), (98.0, 123.47, 146.83)], 4.0, 0.16, seed=1)
        # Night: darker Dm — Bb — F — C.
        _THEMES["night"] = _pad_theme(
            [(73.42, 87.31, 110.0), (58.27, 73.42, 87.31),
             (43.65, 65.41, 87.31), (65.41, 98.0, 130.81)], 4.0, 0.13, seed=2)
        # Menu: airy, ticking feel (A minor with high octave).
        _THEMES["menu"] = _pad_theme(
            [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63),
             (130.81, 196.0, 261.63), (196.0, 246.94, 293.66)], 3.5, 0.15, seed=3)
        # Tense chase pulse.
        _THEMES["chase"] = _pad_theme(
            [(55.0, 110.0, 164.81), (55.0, 110.0, 164.81),
             (61.74, 123.47, 185.0), (55.0, 110.0, 164.81)], 1.5, 0.22, seed=4)
    snd = _THEMES.get(name)
    if snd is not None:
        _music_channel.set_volume(_music_volume * 0.5)
        _music_channel.play(snd, loops=-1, fade_ms=800)


def stop_theme(fade_ms: int = 600) -> None:
    global _current_theme
    if _music_channel is not None:
        _music_channel.fadeout(fade_ms)
    _current_theme = None
