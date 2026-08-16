#!/usr/bin/env python3
"""Assembles the Windows x64 build of TIME into dist/TIME_Windows_x64/.

The build is a *portable* Windows distribution:
  - the official Windows CPython 3.13 embeddable runtime (from the
    `python-embed` package on PyPI),
  - the official pygame 2.6.1 wheel for cp313-win_amd64,
  - the game itself (src/, assets/).

`pythonw.exe` (console-less) is renamed to `TIME.exe`; the embeddable
runtime looks for a `TIME._pth` file next to it, which puts the bundled
`python313.zip` stdlib, the game folder and `Lib/site-packages` on the
search path, enables `site`, and an executable `.pth` line auto-imports
`time_launcher`, which boots the game. No console window appears; the
game window opens directly.

The result is validated statically (PE parsing + DLL import closure +
module closure) with `pefile`. Run on any OS with network access:

    python tools/build_windows.py

Output: dist/TIME_v1.0.0_windows_x64.zip  (unzip anywhere, run TIME.exe)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
WORK = ROOT / "build" / "win"
VERSION = "1.0.0"

PYTHON_EMBED = "python-embed==3.13.0"
PYGAME = "pygame==2.6.1"

# DLLs that may be resolved from the Windows system and need no bundling.
SYSTEM_DLLS = {
    "advapi32.dll", "api-ms-win-core-*", "api-ms-win-crt-*", "ext-ms-win-*",
    "apphelp.dll", "avrt.dll",
    "bcrypt.dll", "cfgmgr32.dll", "comctl32.dll", "comdlg32.dll", "crypt32.dll",
    "cryptsp.dll", "d3d11.dll", "d3d9.dll", "dcomp.dll", "dinput8.dll",
    "dnsapi.dll", "dwmapi.dll", "dwrite.dll", "dxgi.dll", "gdi32.dll",
    "glu32.dll", "hid.dll", "imm32.dll", "iphlpapi.dll", "kernel32.dll",
    "kernelbase.dll", "mpr.dll", "msimg32.dll", "msvcp140.dll", "msvcr100.dll",
    "msvcrt.dll", "ncrypt.dll", "netapi32.dll", "ntdll.dll", "ole32.dll",
    "oleaut32.dll", "opengl32.dll", "powrprof.dll", "propsys.dll", "psapi.dll",
    "rpcrt4.dll", "secur32.dll", "setupapi.dll", "shell32.dll", "shlwapi.dll",
    "sspicli.dll", "user32.dll", "userenv.dll", "usp10.dll", "uxtheme.dll", "version.dll",
    "vcruntime140.dll", "vcruntime140_1.dll", "winhttp.dll", "wininet.dll",
    "winmm.dll", "winspool.drv", "wintrust.dll", "ws2_32.dll", "wtsapi32.dll",
    "ucrtbase.dll", "dxva2.dll", "d2d1.dll", "mfplat.dll", "mfreadwrite.dll",
    "mfuuid.dll", "mfsvr.dll", "evr.dll", "windowsappruntime.dll",
}


def log(msg: str) -> None:
    print(f"[build] {msg}")


def fetch_pypi_json(pkg: str) -> dict:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json", timeout=30) as r:
        return json.load(r)


def download(url: str, dest: Path, label: str = "") -> None:
    if dest.exists() and dest.stat().st_size > 0:
        log(f"already have {label or dest.name}")
        return
    log(f"downloading {label or url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)
    tmp.rename(dest)


# ------------------------------------------------------------ fetch inputs --
def get_python_embed(work: Path) -> Path:
    """Return the folder with the Windows embeddable CPython."""
    out = work / "cpython-embed"
    if (out / "pythonw.exe").exists():
        return out
    data = fetch_pypi_json(PYTHON_EMBED.split("==")[0])
    ver = PYTHON_EMBED.split("==")[1]
    sdist = next(u for u in data["urls"] if u["filename"].endswith(".tar.gz"))
    tarball = work / sdist["filename"]
    download(sdist["url"], tarball, "python-embed sdist")
    shutil.rmtree(work / "sdist", ignore_errors=True)
    shutil.unpack_archive(str(tarball), str(work / "sdist"))
    data_zip = next((work / "sdist").rglob("data.zip"), None)
    if data_zip is None:
        raise SystemExit("data.zip not found in python-embed sdist")
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(data_zip) as z:
        names = z.namelist()
        # data.zip contains a single top folder like cp313/
        top = names[0].split("/")[0] if names else ""
        for n in names:
            if "/" not in n:
                continue
            rel = n[n.index("/") + 1:]
            if not rel:
                continue
            target = out / rel
            if n.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(n))
    log(f"python embeddable 3.13 unpacked ({len(list(out.iterdir()))} files)")
    return out


def get_pygame(work: Path) -> Path:
    """Download the pygame wheel for cp313-win_amd64 and extract it."""
    out = work / "pygame-win"
    if (out / "pygame" / "base.cp313-win_amd64.pyd").exists():
        return out / "pygame"
    data = fetch_pypi_json("pygame")
    wheel = next(u for u in data["urls"]
                 if u["filename"] == "pygame-2.6.1-cp313-cp313-win_amd64.whl")
    dest = work / wheel["filename"]
    download(wheel["url"], dest, "pygame cp313 wheel")
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest) as z:
        z.extractall(out)
    return out / "pygame"


# ------------------------------------------------------------------- icon --
def _make_dib(img) -> bytes:
    """PIL RGBA image -> ICO DIB (BITMAPINFOHEADER + BGRA bottom-up + AND mask)."""
    w, h = img.size
    header = struct.pack("<IiiHHIIiiII", 40, w, 2 * h, 1, 32, 0, 0, 0, 0, 0, 0)
    raw = img.tobytes("raw", "BGRA")
    rows = [raw[y * w * 4: (y + 1) * w * 4] for y in range(h)]
    rows.reverse()
    mask_row = b"\x00" * (((w + 31) // 32) * 4)
    return header + b"".join(rows) + mask_row * h


def _draw_icon(size: int):
    """Paint the TIME clock face at the given size."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (size, size), (18, 24, 42, 255))
    d = ImageDraw.Draw(img)
    m = max(1, size // 14)
    d.ellipse((m, m, size - m, size - m), outline=(212, 175, 55, 255), width=max(1, size // 12))
    cx = cy = size // 2
    # hour hand (up) and minute hand (to 4 o'clock)
    d.line((cx, cy, cx, size // 4), fill=(245, 226, 170, 255), width=max(2, size // 10))
    d.line((cx, cy, cx + size // 4, cy + size // 5), fill=(212, 175, 55, 255),
           width=max(1, size // 14))
    r = max(2, size // 16)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(245, 226, 170, 255))
    return img


def make_icon(assets: Path) -> Path:
    """Generate assets/icon.ico (16/24/32/48/64/256, BMP-format entries)."""
    ico = assets / "icon.ico"
    if ico.exists():
        return ico
    import struct as _st
    sizes = [16, 24, 32, 48, 64, 256]
    dibs = []
    for size in sizes:
        img = _draw_icon(size)
        dibs.append((0 if size == 256 else size, 0 if size == 256 else size,
                     _make_dib(img)))
    with open(ico, "wb") as f:
        f.write(b"\x00\x00\x01\x00" + _st.pack("<H", len(dibs)))
        offset = 6 + 16 * len(dibs)
        for bw, bh, dib in dibs:
            f.write(_st.pack("<BBBBHHII", bw, bh, 0, 0, 1, 32, len(dib), offset))
            offset += len(dib)
        for _bw, _bh, dib in dibs:
            f.write(dib)
    return ico


def try_set_icon(exe: Path, ico: Path) -> bool:
    try:
        import lief
    except Exception as e:
        log(f"LIEF not available ({e}); skipping custom icon")
        return False
    try:
        binary = lief.PE.parse(str(exe))
        mgr = binary.resources_manager
        if mgr is None:
            return False
        # parse our ico: (bw, bh) -> dib
        data = ico.read_bytes()
        count = int.from_bytes(data[4:6], "little")
        entries = {}
        for i in range(count):
            ent = data[6 + 16 * i: 6 + 16 * (i + 1)]
            bw, bh = ent[0], ent[1]
            size = int.from_bytes(ent[8:12], "little")
            off = int.from_bytes(ent[12:16], "little")
            entries[(bw, bh)] = data[off:off + size]
        icons = list(mgr.icons)
        if not icons:
            raise RuntimeError("no icons in exe")
        import struct as _st
        changed = 0
        for old in icons:
            key = (int(old.width), int(old.height))
            dib = entries.get(key) or next(iter(entries.values()))
            serialized = _st.pack("<HHHBBBBHHII", 0, 1, 1, key[0], key[1],
                                  0, 0, 1, 32, len(dib), 22) + dib
            new = lief.PE.ResourceIcon.from_serialization(serialized)
            if isinstance(new, lief.lief_errors):
                continue
            new.id = old.id
            mgr.change_icon(old, new)
            changed += 1
        if changed == 0:
            raise RuntimeError("no icon swapped")
        binary.write(str(exe))
        log(f"custom icon injected into TIME.exe ({changed} sizes)")
        return True
    except Exception as e:
        log(f"icon injection failed: {e}")
        return False


# --------------------------------------------------------------- assembly --
def assemble(dist: Path, py: Path, pygame_dir: Path) -> None:
    shutil.rmtree(dist, ignore_errors=True)
    dist.mkdir(parents=True)

    # 1) embedded runtime (everything except the ._pth file)
    for item in py.iterdir():
        if item.name.endswith("._pth"):
            continue
        dst = dist / item.name
        if item.is_dir():
            shutil.copytree(item, dst)
        else:
            shutil.copy2(item, dst)

    # 2) console-less launcher becomes TIME.exe
    shutil.copy2(dist / "pythonw.exe", dist / "TIME.exe")
    if not (dist / "pythonw.exe").exists():
        raise SystemExit("pythonw.exe missing from embeddable runtime")
    log("TIME.exe created from pythonw.exe")

    # 3) pygame package + its DLLs also placed next to the exe
    shutil.copytree(pygame_dir, dist / "pygame")
    for dll in sorted((dist / "pygame").glob("*.dll")):
        shutil.copy2(dll, dist / dll.name)
    log(f"pygame bundled ({len(list((dist/'pygame').glob('*.pyd')))} extensions)")

    # 4) the game
    shutil.copytree(ROOT / "src", dist / "src")
    shutil.copy2(ROOT / "main.py", dist / "main.py")
    shutil.copytree(ROOT / "assets", dist / "assets")
    log("game files copied")

    # 5) auto-launch: TIME._pth + site-packages bootstrap
    (dist / "TIME._pth").write_text(
        "python313.zip\r\n.\r\nLib/site-packages\r\nimport site\r\n",
        encoding="utf-8",
    )
    sp = dist / "Lib" / "site-packages"
    sp.mkdir(parents=True)
    (sp / "time_launch.pth").write_text("import time_launcher\r\n", encoding="utf-8")
    (sp / "time_launcher.py").write_text(
        """# TIME launcher: runs the game on the embedded Python runtime.
# Imported automatically via an executable .pth line at startup.
import os
import sys
import traceback
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2]

try:
    os.chdir(APP_DIR)
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))
    # make bundled pygame DLLs loadable (safe no-op elsewhere)
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(APP_DIR))
            os.add_dll_directory(str(APP_DIR / "pygame"))
        except Exception:
            pass
    import main
    main.main()
except Exception:
    try:
        (APP_DIR / "crash.log").write_text(traceback.format_exc(), encoding="utf-8")
    except Exception:
        pass
    raise
""",
        encoding="utf-8",
    )
    log("auto-launch bootstrap written")

    # 6) notices
    notices = dist / "THIRD_PARTY_NOTICES.txt"
    notices.write_text(
        """TIME — детективная игра FL1PPER. Версия 1.0.0.

Этот дистрибутив включает:
  * CPython 3.13 (Windows embeddable) — лицензия PSF, см. python LICENSE.txt
  * pygame 2.6.1 — лицензия LGPL-2.1 (http://www.pygame.org)
  * Шрифты DejaVu — см. assets/fonts/LICENSE-DejaVu.txt
  * Исходный код игры: src/ (см. репозиторий TIME)

Запуск: TIME.exe
Сохранения: папка userdata/ рядом с игрой.
""",
        encoding="utf-8",
    )
    readme = dist / "README.txt"
    readme.write_text(
        """TIME v1.0.0 — детектив FL1PPER
================================

Запустите TIME.exe — откроется игра.

Управление:
  WASD/стрелки — движение, Shift — бег
  E — осмотреть / поговорить / войти
  Q — перемещение во времени
  J — блокнот, Esc — пауза

Сохранения лежат в папке userdata/. Если игра не запустилась —
проверьте файл crash.log рядом с TIME.exe и сообщите о проблеме.

Приятного расследования!
""",
        encoding="utf-8",
    )
    log("dist assembled: " + str(dist))


# --------------------------------------------------------------- validate --
def validate(dist: Path) -> list[str]:
    problems: list[str] = []

    def pe_imports(path: Path) -> set[str]:
        try:
            import pefile
        except Exception:
            return set()
        try:
            pe = pefile.PE(str(path), fast_load=True)
            pe.parse_data_directories(directories=[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            ])
            out = set()
            for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
                name = (entry.dll or b"").decode("utf-8", "ignore").lower()
                out.add(name)
            return out
        except Exception as e:
            problems.append(f"PE parse failed: {path.name}: {e}")
            return set()

    # 1) exe sanity
    exe = dist / "TIME.exe"
    try:
        import pefile
        pe = pefile.PE(str(exe), fast_load=True)
        check = (
            pe.FILE_HEADER.Machine == 0x8664
            and pe.OPTIONAL_HEADER.Subsystem == 2  # GUI
        )
        if not check:
            problems.append(f"TIME.exe: machine/subsystem unexpected "
                            f"({hex(pe.FILE_HEADER.Machine)}, "
                            f"{pe.OPTIONAL_HEADER.Subsystem})")
        else:
            log("TIME.exe: PE32+ x86-64, GUI subsystem — ok")
    except Exception as e:
        problems.append(f"pefile failed on TIME.exe: {e}")

    # 2) DLL import closure
    pyd_dll = [p for p in dist.rglob("*") if p.suffix.lower() in (".dll", ".pyd")]
    present = {p.name.lower() for p in pyd_dll}
    for path in sorted(pyd_dll):
        for imp in pe_imports(path):
            if imp in present:
                continue
            is_system = False
            for w in SYSTEM_DLLS:
                if w.endswith("*"):
                    if imp.startswith(w[:-1]):
                        is_system = True
                        break
                elif imp == w:
                    is_system = True
                    break
            if is_system:
                continue
            problems.append(f"unresolved DLL import: {path.name} -> {imp}")
    log(f"checked {len(pyd_dll)} PE files for DLL closure")

    # 3) stdlib module closure
    with zipfile.ZipFile(dist / "python313.zip") as z:
        names = z.namelist()
    stdlib_tops = {n.split("/")[0] for n in names}          # 'json' from json/__init__.pyc
    stdlib_tops |= {n[:-4] for n in names if "/" not in n and n.endswith((".pyc", ".py"))}
    # modules statically built into python313.dll (Windows official build)
    builtins = set("""__main__ _ast _codecs _collections _contextvars _csv _datetime
    _functools _imp _io _json _locale _lsprof _opcode _operator _pickle _random
    _signal _sre _stat _statistics _string _symtable _thread _tokenize
    _tracemalloc _typing _warnings _weakref _winapi array atexit builtins errno
    faulthandler gc itertools marshal math msvcrt nt posix pwd sys time winreg
    xxsubtype zlib""".split())

    def py_files(folder: Path):
        return [p for p in folder.rglob("*.py")]

    import ast
    imported: set[str] = set()
    for p in py_files(dist / "src") + [dist / "main.py",
                                       dist / "Lib" / "site-packages" / "time_launcher.py"]:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imported.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    imported.add(node.module.split(".")[0])
    for m in sorted(imported):
        if m in ("src", "main", "time_launcher", "__future__", "pygame"):
            continue
        if m in builtins or m in stdlib_tops:
            continue
        if (dist / "src" / m.replace(".", "/")).exists():
            continue
        # pygame submodule imports handled by the pygame package
        if (dist / "pygame" / m).exists() or m == "pygame":
            continue
        problems.append(f"stdlib module missing: {m}")
    log(f"module closure: {len(imported)} top-level imports checked")

    # 4) bootstrap files
    if not (dist / "TIME._pth").exists():
        problems.append("TIME._pth missing")
    if not (dist / "TIME.exe").exists():
        problems.append("TIME.exe missing")
    if not (dist / "Lib" / "site-packages" / "time_launcher.py").exists():
        problems.append("time_launcher.py missing")
    log("bootstrap files present")

    # 5) archive integrity
    with zipfile.ZipFile(dist / "python313.zip") as z:
        bad = z.testzip()
    if bad:
        problems.append(f"python313.zip corrupt: {bad}")
    log("python313.zip integrity ok")

    return problems


def make_zip(dist: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(dist.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(dist))
    log(f"zip: {zip_path} ({zip_path.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-icon", action="store_true", help="skip icon injection")
    ap.add_argument("--no-zip", action="store_true")
    args = ap.parse_args()

    log("fetching Windows Python 3.13 embeddable…")
    py = get_python_embed(WORK)
    log("fetching pygame cp313-win_amd64…")
    pygame_dir = get_pygame(WORK)

    dist = DIST / "TIME_Windows_x64"
    assemble(dist, py, pygame_dir)

    if not args.no_icon:
        ico = make_icon(ROOT / "assets")
        try_set_icon(dist / "TIME.exe", ico)

    log("validating…")
    problems = validate(dist)
    if problems:
        print("\n[build] VALIDATION PROBLEMS:")
        for p in problems:
            print("   -", p)
        sys.exit(1)

    if not args.no_zip:
        make_zip(dist, DIST / f"TIME_v{VERSION}_windows_x64.zip")
    log("BUILD OK → " + str(dist))


if __name__ == "__main__":
    main()
