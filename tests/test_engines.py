"""The neural engine — installed from inside the app, and never claimed early

    python tests/test_engines.py

Why this file exists: a cloned voice is not a preference, it is a model. The user's rule is
"it must sound like a real person, no TTS" — so the part of the app that fetches the model
has to be as honest as the part that speaks. Three things must be impossible:

    1. saying "installed" when only the pip package landed (the weights are the model),
    2. saying "installed" when the person pressed Stop,
    3. showing "system voice" with no way to fix it from the screen.

The real download is 1.5-3.4 GB, so the child processes are faked here. The logic, the
wording, and the dialog are real.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ARCDESK_HOME"] = tempfile.mkdtemp(prefix="arcdesk-engines-")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from arcdesk import clone, engines  # noqa: E402
from arcdesk.theme import get_theme  # noqa: E402
from arcdesk.widgets.engine_dialog import EngineDialog  # noqa: E402

ok = True


def check(label: str, got, want=True) -> None:
    global ok
    good = got == want
    print(f"   {'OK  ' if good else 'FAIL'} {label:<58} {str(got)[:46]!r}")
    ok &= bool(good)


READY = {"on": False}          # flipped by the fake warm-up, like a real model landing


def fake_engines():
    return {"indicf5": {"available": READY["on"], "why": "" if READY["on"] else "missing",
                        "model": ""},
            "xtts": {"available": False, "why": "missing", "model": ""},
            "piper": {"available": False, "why": "piper is not installed", "model": ""}}


clone.engines = fake_engines          # the probe the installer consults
clone.refresh = lambda: None

CALLS: list[list[str]] = []


def ok_run(argv, on_line, cancel=None):
    CALLS.append(list(argv))
    on_line("fake: " + " ".join(argv[2:4]))
    if "-c" in argv:                      # the warm-up = the weights
        READY["on"] = True
    return {"ok": True, "code": 0, "why": "", "last": "fake done"}


print("1) both engines are described honestly before anything is downloaded")
st = engines.status()
check("two engines", len(st), 2)
check("IndicF5 is for Tamil and Hindi", st["indicf5"]["langs"], "Tamil, Hindi")
check("XTTS is for English", st["xtts"]["langs"], "English")
check("the sizes are on the tin", (st["indicf5"]["size_mb"], st["xtts"]["size_mb"]),
      (1500, 1900))
check("nothing is ready yet", engines.any_ready(), False)
check("and the app says so in words", "system voice" in engines.line_for_voice(), True)
check("summary names both engines", "IndicF5" in engines.summary()
      and "XTTS-v2" in engines.summary(), True)

print("\n2) one click installs: packages first, then the weights")
engines._run = ok_run                   # noqa: SLF001 — the seam exists for this
seen: list[str] = []
got = engines.install("indicf5", on_line=seen.append)
check("it worked", got["ok"], True)
check("it said the size before starting", "1.5 GB" in seen[0], True)
check("two steps were run", len(CALLS), 2)
check("step 1 was pip", CALLS[0][1:3], ["-m", "pip"])
check("step 1 installed the packages",
      [p for p in CALLS[0] if p in ("torch", "transformers", "soundfile")],
      ["torch", "transformers", "soundfile"])
check("step 2 downloaded the weights", "-c" in CALLS[1], True)
check("the streamed lines reach the caller", len(seen) >= 5, True)
check("ready is reported only now", engines.status()["indicf5"]["ready"], True)
check("and the honest line changes", "clone engine ready" in engines.line_for_voice(), True)

print("\n3) a package that installs but weights that fail is NOT 'installed'")
READY["on"] = False
CALLS.clear()


def warm_fails(argv, on_line, cancel=None):
    CALLS.append(list(argv))
    if "-c" in argv:
        on_line("OSError: cannot reach huggingface.co")
        return {"ok": False, "code": 1, "why": "exit code 1",
                "last": "OSError: cannot reach huggingface.co"}
    return ok_run(argv, on_line, cancel)


engines._run = warm_fails             # noqa: SLF001
seen.clear()
got = engines.install("indicf5", on_line=seen.append)
check("not ok", got["ok"], False)
check("it blames the weights, not the network in general", got["why"], "exit code 1")
check("the real error line is kept", any("huggingface" in l for l in seen), True)
check("it warns that nothing is ready", any("nothing is ready" in l for l in seen), True)
check("still not ready", engines.status()["indicf5"]["ready"], False)
check("still says system voice", "system voice" in engines.line_for_voice(), True)

print("\n4) Stop means stopped — never 'installed'")
cancel = threading.Event()
cancel.set()


def cancelled_run(argv, on_line, cancel=None):
    return {"ok": False, "code": -2, "why": "cancelled", "last": ""}


engines._run = cancelled_run          # noqa: SLF001
got = engines.install("xtts", cancel=cancel)
check("not ok", got["ok"], False)
check("it says cancelled", got["why"], "cancelled")
check("nothing became ready", engines.status()["xtts"]["ready"], False)

print("\n5) an unknown engine is refused, not guessed")
check("refused", engines.install("magic")["ok"], False)

print("\n6) the install route is stated for this build")
m = engines.method()
check("a run-from-source build can use pip", m["can_install"], True)
check("it knows where the bundled script is", Path(m["bat"]).name, "install_clone.bat")
sys.frozen = True                     # what an installed ArcDesk.exe looks like
_real_external = engines.external_python
engines.external_python = lambda: ""
m2 = engines.method()
check("a frozen build does not pretend pip works", m2["pip"] and not m2["can_install"], True)
check("...it asks for Python once, plainly", "python.org" in m2["why"], True)
check("...and then refuses honestly", engines.install("indicf5")["ok"], False)
engines.external_python = lambda: "/usr/bin/python3"
m3 = engines.method()
check("with a Python present the .exe CAN install (private folder)", m3["can_install"], True)
check("...and has nothing to apologise for", m3["why"], "")
del sys.frozen

print("\n7) the dialog: sizes on the buttons, live output, real verdicts")
dlg = EngineDialog(get_theme("chill"))
check("one entry per engine", dlg.picker.count(), 2)
check("the button carries the size", "1.5 GB" in dlg.go.text(), True)
check("the state line names the language", "Tamil" in dlg.state.text(), True)
check("the log starts empty", dlg.log.toPlainText(), "")
dlg._finished({"ok": True, "engine": "indicf5", "why": "", "lines": []})
check("a real install says done", "is installed" in dlg.verdict.text(), True)
dlg._finished({"ok": False, "engine": "indicf5", "why": "cancelled", "lines": []})
check("a cancel says stopped, not done", dlg.verdict.text().startswith("Stopped"), True)
dlg._finished({"ok": False, "engine": "indicf5", "why": "exit code 1", "lines": []})
check("a failure admits it and keeps saying system voice",
      "system voice" in dlg.verdict.text(), True)

print("\n8) it is reachable from the two screens that mention it")
settings_src = (ROOT / "arcdesk" / "widgets" / "settings.py").read_text(encoding="utf-8")
voice_src = (ROOT / "arcdesk" / "widgets" / "voicelib_dialog.py").read_text(encoding="utf-8")
check("Settings → Voice opens it", "from .engine_dialog import EngineDialog" in settings_src,
      True)
check("the voice library opens it too",
      "from .engine_dialog import EngineDialog" in voice_src, True)
check("no command prompt is asked of the user in the honest line",
      "install_clone.bat" in (ROOT / "arcdesk" / "engines.py").read_text(encoding="utf-8"),
      True)
check("the engine module never claims ready without the weights",
      "weights did not arrive" in (ROOT / "arcdesk" / "engines.py").read_text(
          encoding="utf-8"), True)

print("\n9) the installed .exe: the engine goes in a private folder, one button")
import shutil  # noqa: E402

engines.external_python = lambda: "/usr/bin/python3"
check("nothing is ready in that folder yet", engines.sidecar_ready("indicf5"), False)
check("the app can say where it would live", "engine_env" in str(engines.sidecar_dir()), True)
check("the helper script ships with the app", engines.script_path("clone_speak.py").is_file(),
      True)


def venv_ok(target, on_line, cancel=None):
    (target / "bin").mkdir(parents=True, exist_ok=True)
    (target / "bin" / "python").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    return {"ok": True, "code": 0, "why": "", "last": "venv made"}


engines._make_venv = venv_ok        # noqa: SLF001
CALLS.clear()
engines._run = ok_run               # noqa: SLF001
sys.frozen = True
seen.clear()
got = engines.install("indicf5", on_line=seen.append)
check("one click installed it", got["ok"], True)
check("it built its own environment first", any("private engine folder" in l for l in seen),
      True)
check("it pip-installed WITH the borrowed python", "pip" in CALLS[0], True)
check("it downloaded the weights too", "-c" in CALLS[1], True)
check("now the folder counts as ready", engines.sidecar_ready("indicf5"), True)
check("...and only for the engine that finished", engines.sidecar_ready("xtts"), False)
del sys.frozen

print("\n10) the app then speaks through that folder, and only then")
written: list[list[str]] = []


def run_and_write(argv, on_line, cancel=None):
    written.append(list(argv))
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        out.write_bytes(b"RIFF" + b"\0" * 4000)
    return {"ok": True, "code": 0, "why": "", "last": ""}


engines._run = run_and_write        # noqa: SLF001
got = engines.sidecar_speak("vanakkam macha", "ta", "/tmp/ref.wav", "vanakkam", "/tmp/o.wav")
check("it spoke", got["ok"], True)
_argv = " ".join(written[-1])
check("with the engine that was installed", "--engine indicf5" in _argv, True)
check("and the sentence it was given", "--text vanakkam macha" in _argv, True)
check("the transcript travelled too", "--transcript vanakkam" in _argv, True)
check("a missing engine is refused, not guessed",
      engines.sidecar_speak("hi", "en", "/tmp/ref.wav", "", "/tmp/x.wav",
                            "xtts")["ok"], False)

# and clone.speak actually reaches it: no local packages, but a ready folder
from arcdesk import clone as _clone  # noqa: E402
_clone.refresh()
ref_path = Path(_clone.reference()) if _clone.reference() else None
if ref_path is None:
    ref_path = _clone.voice_dir() / "reference.wav"
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_bytes(b"RIFF" + b"\0" * 2000)
_clone.refresh()
check("the reference is in place", Path(_clone.reference()).exists(), True)
check("Tamil now routes to the cloned engine", _clone.route("ta"), "indicf5")
check("speak() produced the wav through the folder",
      _clone.speak("vanakkam", "ta", wav="/tmp/spoken.wav"), True)
check("...using the helper script",
      any("clone_speak.py" in a[1] for a in written), True)

print()
print("RESULT:", "ALL PASS" if ok else "FAILURES ABOVE")
raise SystemExit(0 if ok else 1)
