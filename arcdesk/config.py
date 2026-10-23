"""Settings + file paths. JSON on disk, atomic writes, no database.

Stored in %APPDATA%\\ArcDesk on Windows, ~/.config/ArcDesk elsewhere.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

APP_NAME = "ArcDesk"

DEFAULTS: dict[str, Any] = {
    "mode": "chill",
    "animations": True,
    "fps_cap": None,            # None = follow the mode's own cap
    "effects": None,            # None = follow the mode's own scale
    "window": {"w": 1000, "h": 690, "x": None, "y": None},
    "shortcuts": [
        {"label": "FILES", "target": "explorer"},
        {"label": "NOTES", "target": "notepad"},
        {"label": "CALC", "target": "calc"},
        {"label": "TASKS", "target": "taskmgr"},
    ],
    "weather": {
        "enabled": False,       # OFF by default -> fully offline app
        "lat": 15.8497,         # Belagavi, default to the user's city
        "lon": 74.4977,
        "city": "Belagavi",
        "refresh_min": 20,
    },
    "ai": {
        "enabled": True,
        "provider": "auto",      # auto | groq | gemini | openai | ollama | custom | lite
        "model": "",             # blank = provider default
        "api_key": "",           # prefer env vars: GROQ_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY
        "base_url": "",
        "voice": True,
        "nudges": False,            # speak up unprompted (battery, disk, long session)           # speak replies via the OS voice
        "voice_rate": 1,
        "voice_clone": True,        # use the imported reference voice when possible
        "voice_engine": "auto",         # -5 .. 5
    },
    "wake": {
        "enabled": False,               # off by default: nothing listens to your mic
        "phrase": "hey jarvis",
        "engine": "auto",               # auto | vosk | openwakeword
        "port": 8765,
        "command_seconds": 7,
        "converse": True,               # keep listening after an answer (6 turns)
        "converse_turns": 6,
        "voice_lock": False,        # only the enrolled voice may command it
        "barge_in": True,               # talking over ARC stops it
        "autostart_daemon": True,       # app spawns the daemon when enabled
    },
    "first_run": True,          # show the one-page welcome/setup card once
    "shadow": {
        "enabled": True,          # boot with no window, no tray icon, no taskbar entry
        "hotkey_palette": "ctrl+alt+j",
        "hotkey_quit": "ctrl+alt+q",
        "hotkeys": True,
        "awaken": True,           # cinematic screen takeover when the wake word fires
        "awaken_mode": "chill",   # mode to land in after the awakening
        "tray": True,             # one normal tray icon, like any background app
        "preserve_windows": True, # never alter wallpaper / icons / taskbar / theme
        # What "BYE JARVIS" does to the application itself. The default is "exit" because
        # the promise is "the app opens and closes by voice", not "the app hides".
        #   hide  -> app stays in the background (instantest to reopen, tray icon stays)
        #   exit  -> app really quits; a small launcher daemon stays armed so
        #            "hey jarvis" can start it again. If nothing could hear you after
        #            closing (no mic library / no engine) this FALLS BACK to hide
        #            instead of quitting into silence.
        #   quit  -> app quits and nothing stays behind; reopen from the shortcut
        "bye_action": "exit",
        "relaunch_on_wake": True, # only used when bye_action = exit
    },
    "charms": {
        "enabled": True,
        "items": [
            {"kind": "reactor", "x": 120, "y": 160, "scale": 1.15, "speed": 1.0},
            {"kind": "planet", "x": 1420, "y": 240, "scale": 1.0, "speed": 0.7},
            {"kind": "butterfly", "x": 300, "y": 560, "scale": 0.8, "speed": 1.6},
            {"kind": "bot", "x": 1180, "y": 520, "scale": 0.9, "speed": 1.1},
        ],
    },
    "magic": {
        "enabled": True,              # "Hey JARVIS" -> full screen ARC workspace
        "exit_phrase": "bye jarvis",  # say this to return to normal Windows
        "wallpaper": True,            # swap the desktop wallpaper while active
        "restore_on_start": True,     # heal an interrupted session
    },
    "cost": {
        "enabled": True,
        "max_class": "free",      # local | free | paid   (paid only if you change this)
    },
    "mcp": {
        "enabled": True,
        "servers": [
            # {"name": "files", "command": "npx",
            #  "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:/Users/you/Documents"],
            #  "enabled": false}
        ],
    },
    # ---- the Vault: where your work lives (see vault.py)
    "vault": {
        "root": "",              # "" = %APPDATA%\ArcDesk\vault ; or any folder you like
        "portable": False,       # True = keep the vault next to the program (USB stick)
        "follow_answers": True,  # save each ARC answer into the open project as it happens
    },
    "autostart": False,
    "battery_saver": True,
    "minimise_to_tray_on_close": True,
}


def data_dir() -> Path:
    """Where settings, logs and caches live.

    Overridable with ARCDESK_HOME — that is what makes two things possible:
    a portable copy that keeps everything in its own folder (USB stick), and
    tests that cannot pollute the real settings of the person running them.
    """
    override = os.getenv("ARCDESK_HOME")
    if override:
        d = Path(override).expanduser()
        d.mkdir(parents=True, exist_ok=True)
        return d
    if os.name == "nt":
        base = Path(os.getenv("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def settings_path() -> Path:
    return data_dir() / "settings.json"


def weather_cache_path() -> Path:
    return data_dir() / "weather_cache.json"


# Kept for backwards compatibility (imported by a few modules at import time).
# NOT used by load()/save(): those call settings_path() every time, so a process that
# moves its data folder (or a tool that switches ARCDESK_HOME, like tools/move.py and
# the tests) reads and writes the folder it is actually pointing at.
SETTINGS_PATH = settings_path()
WEATHER_CACHE_PATH = weather_cache_path()


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load() -> dict[str, Any]:
    try:
        raw = json.loads(settings_path().read_text("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("settings root is not an object")
        return _merge(DEFAULTS, raw)
    except FileNotFoundError:
        return json.loads(json.dumps(DEFAULTS))
    except Exception:
        # Corrupt settings must never stop the app from booting.
        return json.loads(json.dumps(DEFAULTS))


def save(cfg: dict[str, Any]) -> None:
    """Atomic write: a crash mid-save can never leave a broken settings file."""
    try:
        target = settings_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
        os.replace(tmp, target)
    except Exception:
        pass
