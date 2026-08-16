#!/usr/bin/env python3
"""TIME — детективная игра о перемещениях во времени.

Запуск:  python main.py
Требования:  pygame (pip install pygame)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    import pygame

    pygame.init()

    from src import audio
    from src.core.app import App, ensure_userdata
    from src.i18n import Translator
    from src.render.sprites import SpriteBank
    from src.settings import Settings

    ensure_userdata()
    settings = Settings().load()

    audio.init()
    audio.set_sfx_volume(settings.sfx_volume)
    audio.set_music_volume(settings.music_volume)

    tr = Translator()
    tr.set_language(settings.language)
    tr.bind_settings(lambda: settings)

    app = App(settings)
    app.tr = tr
    app.sprites = SpriteBank()
    app.witness_portraits = {
        "marta": 11, "nick": 22, "boris": 33, "volkov": 44, "krylov": 55,
        "banker": 66, "w1": 77, "w2": 88, "w3": 99, "emit": 13, "krylov2": 56,
    }
    app.setup_window()

    from src.scenes.splash import SplashScene

    app.push(SplashScene(app))
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        if app.on_quit is not None:
            try:
                app.on_quit()
            except Exception:
                pass
        pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
