"""Start with Windows — on purpose, reversibly, and only if you asked.

A startup entry is one of the few things a desktop app can do that outlives it, so
this module is deliberately boring:

* **Only your own account, only HKCU.** No admin, no HKLM, no service, no scheduled
  task with SYSTEM rights. A per-user Run key is reversible by deleting one value,
  which is the whole reason it was chosen.
* **Verify by reading it back.** "Enabled" is what the registry says, not what the
  code intended. Every write is followed by a read, and the read is what is returned.
* **Never hides itself.** The command it registers is the normal launcher — visible in
  Task Manager → Startup apps, removable from there, and disabling it inside ARC
  deletes the value immediately. Nothing self-heals, nothing re-registers.
* **Honest about the rebuild.** If ARC is later moved or reinstalled, the old path
  lingers; `status()` reports a path that no longer exists as `stale` rather than
  quietly claiming it works.

Linux and macOS are implemented too, because the tests run here: a freedesktop
`.desktop` file in `~/.config/autostart`, and a per-user LaunchAgent on macOS. Same
rules — per-user, reversible, readable back.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "ArcDesk"
LINUX_ENTRY = "arcdesk.desktop"
MAC_LABEL = "ai.arena.arcdesk"


# ------------------------------------------------------------------- launcher
def launcher() -> list[str]:
    """The command that starts ARC. Frozen builds re-open the exe; source runs pythonw."""
    # `--shadow` is the real flag in run.py: start hidden, no window, no tray icon,
    # hotkeys live. Silent start, never stealth — Ctrl+Alt+Q still quits.
    if getattr(sys, "frozen", False):
        return [sys.executable, "--shadow"]
    script = Path(__file__).resolve().parents[1] / "run.py"
    if not script.is_file():
        script = Path(__file__).resolve().parents[1] / "arc_daemon.py"
    python = sys.executable
    if IS_WIN:
        windowless = Path(python).with_name("pythonw.exe")
        if windowless.is_file():
            python = str(windowless)
    return [python, str(script), "--shadow"]


def command_line() -> str:
    """Quoted, so a path with spaces still works (it is the #1 startup-entry bug)."""
    return " ".join(f'"{part}"' if " " in part else part for part in launcher())


def _linux_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "autostart" / LINUX_ENTRY


def _mac_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{MAC_LABEL}.plist"


# --------------------------------------------------------------------- status
def status() -> dict:
    """What is actually registered right now. Never inferred from config."""
    if IS_WIN:
        try:
            import winreg
        except Exception:
            return {"supported": False, "enabled": False,
                    "detail": "the registry is not available in this build"}
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                value, _kind = winreg.QueryValueEx(key, VALUE_NAME)
        except FileNotFoundError:
            return {"supported": True, "enabled": False, "detail": "not registered",
                    "command": command_line()}
        except OSError as exc:
            return {"supported": True, "enabled": False,
                    "detail": f"could not read the key: {exc}", "command": command_line()}
        return _describe(str(value))

    if IS_MAC:
        path = _mac_path()
        if not path.is_file():
            return {"supported": True, "enabled": False, "detail": "not registered",
                    "command": command_line()}
        return {"supported": True, "enabled": True, "detail": f"LaunchAgent at {path}",
                "command": command_line(), "path": str(path)}

    path = _linux_path()
    if not path.is_file():
        return {"supported": True, "enabled": False, "detail": "not registered",
                "command": command_line()}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"supported": True, "enabled": False, "detail": f"unreadable: {exc}",
                "command": command_line()}
    hidden = "Hidden=true" in text.replace(" ", "")
    exec_line = next((line.split("=", 1)[1].strip() for line in text.splitlines()
                      if line.startswith("Exec=")), "")
    result = _describe(exec_line)
    result["path"] = str(path)
    if hidden:
        result["enabled"] = False
        result["detail"] = "an entry exists but is marked Hidden"
    return result


def _describe(registered: str) -> dict:
    """Shared check: is the registered command still a real, runnable file?"""
    text = (registered or "").strip().strip('"')
    exe = ""
    if os.name == "nt":
        if text.upper().startswith('"'):
            exe = text.split('"')[1]
        elif " " in text and text.lower().endswith(".exe"):
            exe = text.strip()
        else:
            exe = text.split(" ")[0]
    else:
        exe = text.split(" ")[0].strip('"')
    exists = bool(exe) and Path(exe).exists()
    return {
        "supported": True, "enabled": True, "registered": registered, "exe": exe,
        "stale": not exists,
        "detail": ("registered and the program is there" if exists
                   else f"registered, but {exe or 'the program'} is missing — "
                        f"re-enable to fix the path"),
        "command": command_line(),
    }


# ---------------------------------------------------------------------- toggle
def enable(silent_start: bool = True) -> dict:
    """Register ARC to start with the user's session. Idempotent; returns the read-back."""
    cmd = command_line()
    if IS_WIN:
        try:
            import winreg
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                    winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, cmd)
        except Exception as exc:
            return {"ok": False, "error": f"Windows refused the write: {exc}"}
        return {"ok": True, "state": status(), "mode": "HKCU Run key"}

    if IS_MAC:
        path = _mac_path()
        parts = launcher()
        args = "\n".join(f"    <string>{p}</string>" for p in parts[1:])
        plist = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
                 f'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                 f'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                 f'<plist version="1.0"><dict>\n'
                 f'  <key>Label</key><string>{MAC_LABEL}</string>\n'
                 f'  <key>ProgramArguments</key><array>\n'
                 f'    <string>{parts[0]}</string>\n{args}\n  </array>\n'
                 f'  <key>RunAtLoad</key><true/>\n'
                 f'</dict></plist>\n')
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(plist, encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "error": f"could not write the LaunchAgent: {exc}"}
        return {"ok": True, "state": status(), "mode": "per-user LaunchAgent"}

    path = _linux_path()
    entry = ("[Desktop Entry]\n"
             "Type=Application\n"
             "Name=Arc Desk\n"
             "Comment=Your desktop. Your universe.\n"
             f"Exec={cmd}\n"
             "X-GNOME-Autostart-enabled=true\n"
             "Terminal=false\n")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry, encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": f"could not write the autostart entry: {exc}"}
    return {"ok": True, "state": status(), "mode": "freedesktop autostart"}


def disable() -> dict:
    """Remove the entry. Deletes one registry value or one small file — nothing else."""
    if IS_WIN:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, VALUE_NAME)
        except FileNotFoundError:
            return {"ok": True, "state": status(), "note": "it was not enabled"}
        except OSError as exc:
            return {"ok": False, "error": f"Windows refused the delete: {exc}"}
        return {"ok": True, "state": status(), "mode": "HKCU Run key"}

    path = _mac_path() if IS_MAC else _linux_path()
    try:
        path.unlink()
    except FileNotFoundError:
        return {"ok": True, "state": status(), "note": "it was not enabled"}
    except OSError as exc:
        return {"ok": False, "error": f"could not remove the entry: {exc}"}
    return {"ok": True, "state": status(), "mode": path.name}


def toggle(on: bool | None = None) -> dict:
    """Enable or disable; `None` flips the current state."""
    current = status()
    if not current.get("supported"):
        return {"ok": False, "error": current.get("detail", "not supported here")}
    want = (not current.get("enabled")) if on is None else bool(on)
    return enable() if want else disable()


# ---------------------------------------------------------------------- report
def report(state: dict | None = None) -> str:
    """One honest paragraph. Says which key/value, and what was not touched."""
    state = state or status()
    if not state.get("supported"):
        return f"I cannot set autostart on this platform: {state.get('detail')}"
    where = {"win32": r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run → ArcDesk",
             "darwin": "~/Library/LaunchAgents/ai.arena.arcdesk.plist"}.get(
        state.get("platform") or sys.platform)
    if not where:
        where = str(_linux_path())
    if state.get("enabled") and not state.get("stale"):
        return (f"ARC starts with your account. It is registered in:\n  {where}\n"
                f"  command: {state.get('command')}\n"
                f"No admin was used, no service was created, and nothing is hidden — it "
                f"appears in Task Manager → Startup apps like any other program.\n"
                f"Say 'stop starting with windows' to remove it.")
    if state.get("stale"):
        return (f"There is an entry, but it points at something that no longer exists:\n"
                f"  {state.get('registered')}\n"
                f"Re-enable it and I will write the current path.")
    return ("ARC does not start with your account. Say 'start with windows' and I will add "
            "one per-user entry — no admin, removable from Task Manager or from here.")


# --------------------------------------------------- compatibility shims
# settings.py and the quick menu were written against a two-function API. Keeping
# those names working is cheaper and safer than editing a UI file that cannot be run
# headlessly here — and it means an older build still imports cleanly.
def is_enabled() -> bool:
    """True only when the entry exists AND points at a program that is really there."""
    state = status()
    return bool(state.get("enabled")) and not bool(state.get("stale"))


def set_enabled(on: bool) -> bool:
    """Enable/disable and report the state read back from the system, not the intent."""
    result = toggle(bool(on))
    return bool(result.get("ok")) and is_enabled() == bool(on)


def describe_state(state: dict) -> str:
    if state.get("enabled") and not state.get("stale"):
        return "on"
    return "off"
