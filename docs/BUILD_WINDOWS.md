# Сборка Windows .exe

Готовый дистрибутив: **`dist/TIME_v1.0.0_windows_x64.zip`** (портативная
сборка, ~26 МБ). Распаковать и запустить `TIME.exe`.

Ниже — два способа собрать exe самостоятельно.

---

## Способ 1. Портативная сборка (любая ОС, официальный скрипт)

`tools/build_windows.py` собирает Windows-дистрибутив прямо из Linux/macOS
(и из Windows тоже). Внутри:

- официальный **CPython 3.13 embeddable** (пакет `python-embed` на PyPI),
- **pygame 2.6.1** (колесо `cp313-win_amd64`),
- игра (`src/`, `assets/`).

Принцип: `pythonw.exe` (без консоли) переименовывается в `TIME.exe`.
Встроенный Python при старте ищет файл `TIME._pth` рядом с исполняемым
файлом (это подтверждено исходниками CPython 3.13, `Modules/getpath.py`),
который добавляет в `sys.path` `python313.zip` (стандартная библиотека),
папку игры и `Lib/site-packages`, включает `site`, а исполняемая строка
`.pth` автоматически импортирует `time_launcher`, который запускает игру.
Окно консоли не появляется.

```bash
pip install pefile lief pillow   # для иконки и статических проверок
python tools/build_windows.py
```

Результат:

- `dist/TIME_Windows_x64/` — развёрнутый дистрибутив;
- `dist/TIME_v1.0.0_windows_x64.zip` — архив для распространения.

Скрипт **валидирует сборку** до упаковки:

- `TIME.exe` — корректный PE32+ x86-64, подсистема GUI;
- замыкание DLL-импортов всех 96 PE-файлов (каждая импортируемая DLL
  либо в комплекте, либо системная);
- замыкание модулей: все импорты игры разрешаются в `python313.zip`,
  встроенных модулях 3.13, pygame или `src/`;
- целостность `python313.zip`.

> Примечание: полный запуск Windows-бинарника возможен только на Windows
> (или под Wine). Рекомендуется дополнительно прогнать `tests/smoke.py`
> на целевой машине после распаковки.

## Способ 2. PyInstaller (нужен Windows)

Самый «классический» вариант — один файл `TIME.exe`, собирается на Windows
за пару минут:

```bat
build_windows.bat
```

Скрипт ставит `pygame` и `PyInstaller` и выполняет:

```bat
pyinstaller --noconfirm --clean --onefile --windowed --name TIME ^
    --add-data "assets;assets" --icon assets\icon.ico main.py
```

Результат: `dist\TIME.exe`. Или напрямую:

```bat
pyinstaller TIME.spec
```

## Что входит в дистрибутив

```
TIME.exe                  — игра (без консоли, своя иконка)
TIME._pth                 — конфигурация путей встроенного Python
python313.dll/.zip, python3.dll, vcruntime140*.dll, *.pyd — рантайм
src/  assets/  main.py    — игра
pygame/                   — pygame 2.6.1 (cp313-win_amd64)
SDL2*.dll, freetype.dll   — зависимости pygame
Lib/site-packages/        — авто-запуск (time_launcher.pth/.py)
README.txt                — краткая инструкция
THIRD_PARTY_NOTICES.txt   — лицензии
```

## Проверка сборки на Windows

1. Распаковать архив в папку с правами на запись.
2. Запустить `TIME.exe` — должна появиться заставка FL1PPER.
3. Пройти день 1 до вечерних новостей (это проверяет часы, сон, улики).
4. При проблемах — открыть `crash.log` рядом с `TIME.exe`.

## Известные ограничения

- Файл не подписан — Windows SmartScreen может показать предупреждение
  («Подробнее» → «Выполнить в любом случае»).
- Портативная сборка не пишет в реестр и не требует прав администратора.
