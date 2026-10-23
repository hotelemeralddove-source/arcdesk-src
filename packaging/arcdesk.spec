# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — TWO binaries, one folder.

    ArcDesk.exe       the window, the HUD, magic mode, charms            (run.py)
    ArcDeskVoice.exe  the ears: microphone, wake word, speech           (arc_daemon.py)

Build with:  packaging\\build.bat      (never call PyInstaller directly; build.bat
                                      runs the static pre-flight first)

Design notes that matter:

  * Modules are collected with collect_submodules("arcdesk"). A hand-written list is
    how a packaged app imports fine and then dies on the one screen you only open
    once. tools/packaging.py FAILS the build if a hand-written list ever comes back.
  * Two EXEs on purpose: a microphone and a speech model never share a process with
    the Qt window. That separation is where the memory budget comes from.
  * onedir, not onefile: onefile unpacks itself to %TEMP% on every launch.
  * upx=False: UPX compression is the single most common cause of antivirus
    false-positives on PyInstaller output. A slightly bigger folder is worth it.
  * This directory is named `packaging/`, NOT `build/`: some tooling (and this
    project's own workspace snapshots) treats a folder called `build` as disposable.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# SPECPATH is the folder that holds THIS file, i.e. packaging/. The repo root is its
# parent. (This used to apply .parent twice, which pointed ROOT at the folder *above*
# the repo: PyInstaller then died with "script '.../run.py' not found". It was found by
# actually running the build, which is the only way that class of bug shows up.)
PACKAGING = Path(SPECPATH).resolve()
ROOT = PACKAGING.parent
PKG = ROOT / "arcdesk"
if not (ROOT / "run.py").is_file():
    raise SystemExit(
        f"[spec] cannot find run.py next to {PACKAGING}\n"
        f"[spec] expected the repo root at {ROOT}\n"
        "[spec] build with: packaging\\build.bat (or python -m PyInstaller "
        "packaging\\arcdesk.spec from the repo root)")

hiddenimports = collect_submodules("arcdesk")
# Imported lazily inside functions, so the static analyser cannot see them.
hiddenimports += [
    "PySide6.QtNetwork", "PySide6.QtSvg",
    "arcdesk.widgets", "arcdesk.widgets.window", "arcdesk.widgets.assistant",
    "arcdesk.widgets.palette", "arcdesk.widgets.settings", "arcdesk.widgets.welcome",
    "arcdesk.widgets.artview", "arcdesk.widgets.aisetup", "arcdesk.ai.tools",
    "arcdesk.ai.lite", "arcdesk.ai.agent", "arcdesk.ai.voice",
]

datas = []
for pattern in ("*.json", "*.png", "*.svg", "*.ico", "*.wav", "*.qm", "*.html"):
    datas += [(str(p), "arcdesk") for p in PKG.rglob(pattern)]

# The generated in-app pages live *inside* arcdesk/ and are picked up by the rglob
# above. This loop only warns, so a page that was never generated cannot slip by
# unnoticed. Repo-root showcase pages (DEMO_PAGE.html, PREVIEW.html) are deliberately
# not shipped inside the app.
# --doctor is a promised feature (README, INSTALL, Settings -> System), and it is a
# plain script that imports only the stdlib and arcdesk. Ship it as data; without this
# the frozen app answers "--doctor" with ModuleNotFoundError.
DOCTOR = ROOT / "tools" / "doctor.py"
if DOCTOR.is_file():
    datas += [(str(DOCTOR), "tools")]
else:
    print("[spec] WARNING: tools/doctor.py is missing — --doctor will not work")

for page in ("KNOWS_PAGE.html", "STUDIO_PAGE.html", "TOOLS_PAGE.html"):
    if (PKG / page).is_file():
        print(f"[spec] bundling arcdesk/{page}")
    else:
        print(f"[spec] WARNING: arcdesk/{page} is missing — run the generator")

icon = str(ROOT / "shots" / "arc_icon.ico")
icon_arg = icon if Path(icon).is_file() else None

common = dict(
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "matplotlib", "scipy", "pandas", "IPython",
              "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore",
              "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtMultimedia"],
    noarchive=False,
    optimize=0,
)

a = Analysis([str(ROOT / "run.py")], **common)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="ArcDesk",
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=False, disable_windowed_traceback=False,
          icon=icon_arg)

v = Analysis([str(ROOT / "arc_daemon.py")], **common)
voice_pyz = PYZ(v.pure)
voice_exe = EXE(voice_pyz, v.scripts, [], exclude_binaries=True, name="ArcDeskVoice",
                debug=False, bootloader_ignore_signals=False, strip=False,
                upx=False, console=False, disable_windowed_traceback=False,
                icon=icon_arg)

COLLECT(exe, a.binaries, a.datas, voice_exe, v.binaries, v.datas,
        strip=False, upx=False, name="ArcDesk")

# A tiny provenance file next to the exe, so "which build is this?" has an answer.
import datetime as _dt
import sys as _sys
_out = ROOT / "packaging" / "build_info.txt"
_out.write_text(
    "ArcDesk build\n"
    f"built      : {_dt.datetime.now().isoformat(timespec='seconds')}\n"
    f"python     : {_sys.version.split()[0]}\n"
    f"platform   : {_sys.platform}\n"
    f"modules    : {len(hiddenimports)} hidden imports collected\n"
    f"data files : {len(datas)}\n", encoding="utf-8")
