"""Can this machine actually hear? — asked before anything promises to listen.

A "yes" here has to mean all four of these, and it is cheap to check:

    sounddevice (or pyaudio)   something to read the microphone
    vosk or openwakeword       something to recognise the wake phrase
    a model (for vosk)         the 40 MB speech model, if Vosk is the engine

The wizard, Settings and the doctor all use this one function, so the app can never say
"listening" in one place and "not installed" in another.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _have(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def mic_backend() -> str:
    for name in ("sounddevice", "pyaudio"):
        if _have(name):
            return name
    return ""


def engine() -> str:
    for name in ("openwakeword", "vosk"):
        if _have(name):
            return name
    return ""


def model_dir() -> Path | None:
    from .. import config
    for candidate in (config.data_dir() / "models" / "vosk",
                      config.data_dir() / "vosk-model",
                      Path.home() / ".cache" / "arcdesk" / "vosk"):
        if candidate.is_dir() and any(candidate.iterdir()):
            return candidate
    return None


def can_listen() -> tuple[bool, str]:
    """(True, what is available) or (False, the one sentence that says what to install)."""
    mic = mic_backend()
    eng = engine()
    if not mic and not eng:
        return False, ("no microphone library yet — run install_voice.bat "
                       "(installs sounddevice + vosk + the 40 MB model)")
    if not mic:
        return False, f"{eng} is installed but no mic library is (sounddevice/pyaudio)"
    if not eng:
        return False, (f"{mic} is installed but no wake-word engine is "
                       f"(openwakeword or vosk)")
    if eng == "vosk" and model_dir() is None:
        return False, ("vosk is installed but the speech model is not — run "
                       "python arc_daemon.py --download-model")
    return True, f"{mic} + {eng}"
