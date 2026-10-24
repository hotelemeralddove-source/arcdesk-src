"""The neural engines that make a cloned voice sound like a person.

A clone is not a setting — it is a model. Without one of these, ARC can only speak in the
system voice, and it must say so. This module owns the whole "get the model" job so the
app can do it in one click instead of sending anyone to a command prompt:

    status()   -> what is installed, what is missing, how big, and why
    install()  -> pip install + a warm-up download, streaming every line it prints
    method()   -> how this build can install anything (pip / bundled script / no)

Rules this file keeps, because a wrong "ready" is worse than a slow one:

* nothing is called ready until the *model weights* are on disk, not just the package;
* every failure carries the last real error line, not "something went wrong";
* a cancelled install is reported as cancelled — never as installed;
* every size is stated before the download starts (~1.5 GB, ~1.9 GB).
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]

# engine id -> what it is for, how big, and the two steps that make it real
SPECS: dict[str, dict] = {
    "indicf5": {
        "label": "IndicF5",
        "langs": "Tamil, Hindi",
        "size_mb": 1500,
        "packages": ["torch", "transformers", "soundfile"],
        "warm": ("from transformers import AutoModel\n"
                 "AutoModel.from_pretrained('ai4bharat/IndicF5', trust_remote_code=True)\n"),
        "why": "the only one of the two that can speak Tamil or Hindi in a cloned voice",
        "needs": "a GPU to feel instant; on a CPU it works but slowly",
    },
    "xtts": {
        "label": "XTTS-v2",
        "langs": "English",
        "size_mb": 1900,
        "packages": ["coqui-tts"],
        "warm": ("from TTS.api import TTS\n"
                 "TTS('tts_models/multilingual/multi-dataset/xtts_v2')\n"),
        "why": "cloned English; it cannot speak Tamil",
        "needs": "works on a CPU, slower than real time on a weak laptop",
    },
}

Line = Callable[[str], None]


# --------------------------------------------------------------------------- method
def method() -> dict:
    """How can THIS build install anything?

    A frozen one-file build has no `pip` of its own — `sys.executable` is `ArcDesk.exe`.
    Rather than pretend, the app says which of the two honest routes exists here.
    """
    frozen = bool(getattr(sys, "frozen", False))
    bat = ROOT / "install_clone.bat"
    pip_ok = False
    try:
        import importlib.util
        pip_ok = importlib.util.find_spec("pip") is not None
    except Exception:
        pip_ok = False
    can = (not frozen) and pip_ok
    if can:
        why = ""
    elif frozen and external_python():
        # one click still: the app borrows that Python and builds its own environment
        why = ""            # nothing to explain, it can install
        can = True
    elif frozen:
        why = ("this is the installed app and no Python is installed on this computer. "
               "The clone engine needs one: install Python 3 from python.org (one "
               "installer, default options), then press Install again — or use the free "
               "piper voice, which needs nothing")
    elif not pip_ok:
        why = "pip is not available to this Python"
    else:
        why = "unknown"
    return {"frozen": frozen, "pip": pip_ok, "can_install": can, "bat": str(bat),
            "bat_exists": bat.exists(), "why": why,
            "sidecar": sidecar_any(), "env": str(sidecar_dir())}


# --------------------------------------------------------------------------- status
def status() -> dict[str, dict]:
    """Per engine: ready or not, and the size it would cost to fix that."""
    from . import clone
    have = clone.engines()
    out: dict[str, dict] = {}
    for key, spec in SPECS.items():
        got = have.get(key, {})
        out[key] = {
            "id": key,
            "label": spec["label"],
            "langs": spec["langs"],
            "size_mb": spec["size_mb"],
            "why": spec["why"],
            "needs": spec["needs"],
            "ready": bool(got.get("available")),
            "problem": got.get("why", ""),
            "model": got.get("model", ""),
        }
    return out


def any_ready() -> bool:
    return any(v["ready"] for v in status().values())


def line_for_voice() -> str:
    """One honest sentence for anywhere in the app that shows the reply voice."""
    st = status()
    ready = [v["label"] for v in st.values() if v["ready"]]
    if ready:
        return f"clone engine ready: {' / '.join(ready)}"
    return ("no clone engine installed yet — until one is, replies use the system voice "
            "(Settings → Voice → Get the reply-voice engine…)")


# --------------------------------------------------------------------------- install
# --------------------------------------------------------------- the .exe's sidecar
# A frozen build CANNOT import a package that is installed later: torch is not inside
# ArcDesk.exe and never will be (it would add ~2 GB to the installer). So the installed
# app gets the engine a different way: a private, disposable Python environment in the
# user's data folder, created and filled by the app itself with one click. The app then
# hands the sentence to that interpreter and plays the wav it returns. From the person's
# side it is still one button; nothing is installed globally and nothing is on PATH.
def _app_dir() -> Path:
    """Where the app's own files are — the frozen folder, or the repo."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return ROOT


def external_python() -> str:
    """A Python already on this computer that we may borrow ('' if none).

    Preferred: the `py` launcher, because on Windows it always finds a real interpreter
    even when `python` is a Microsoft Store stub that opens the Store.
    """
    import shutil
    for name, probe in (("py", ["py", "-3", "-c", "print(1)"]),
                        ("python", ["python", "-c", "print(1)"]),
                        ("python3", ["python3", "-c", "print(1)"])):
        found = shutil.which(name)
        if not found:
            continue
        try:
            got = subprocess.run(probe, capture_output=True, text=True, timeout=25)
        except Exception:
            continue
        if got.returncode == 0 and "1" in (got.stdout or ""):
            return found if name != "py" else found      # 'py' is run with -3 below
    return ""


def sidecar_dir() -> Path:
    from .config import data_dir
    return data_dir() / "engine_env"


def sidecar_python() -> Path:
    d = sidecar_dir()
    win = d / "Scripts" / "python.exe"
    if win.exists():
        return win
    return d / "bin" / "python"


def sidecar_flag(engine: str) -> Path:
    return sidecar_dir() / f"ready-{engine}.txt"


def sidecar_ready(engine: str) -> bool:
    """True only when the venv exists AND the warm-up for THAT engine finished."""
    return sidecar_python().exists() and sidecar_flag(engine).exists()


def sidecar_any() -> bool:
    return any(sidecar_ready(k) for k in SPECS)


def script_path(name: str) -> Path:
    """tools/<name> both in the repo and inside the frozen app (bundled as data)."""
    for base in (_app_dir(), Path(getattr(sys, "_MEIPASS", "")), ROOT):
        if not str(base):
            continue
        p = base / "tools" / name
        if p.is_file():
            return p
    return _app_dir() / "tools" / name


def _make_venv(target: Path, on_line: Line, cancel) -> dict:
    py = external_python()
    if not py:
        return {"ok": False, "code": -1, "why": "no Python on this computer", "last": ""}
    base = [py] if not py.endswith("py.exe") and Path(py).name != "py" else [py, "-3"]
    return _run([*base, "-m", "venv", str(target)], on_line, cancel)


def ensure_sidecar(engine: str, on_line: Line | None = None,
                   cancel: threading.Event | None = None) -> dict:
    """Build the borrowed environment and fill it with one engine. One button, no console."""
    say: Line = on_line or (lambda _l: None)
    lines: list[str] = []

    def note(text: str) -> None:
        lines.append(text)
        say(text)

    spec = SPECS[engine]
    target = sidecar_dir()
    note(f"a private engine folder for this app: {target}")
    if not sidecar_python().exists():
        note(f"step 1 of 3 · creating it with the Python already on this computer "
             f"({external_python() or 'not found'})")
        got = _make_venv(target, note, cancel)
        if not got["ok"]:
            note(f"could not create it ({got['why']}). Last line: {got['last'][:160]}")
            return {"ok": False, "engine": engine, "why": got["why"], "lines": lines}
    else:
        note("step 1 of 3 · the folder already exists")

    note(f"step 2 of 3 · {spec['label']} packages, about {spec['size_mb'] / 1000:.1f} GB "
         f"including the model")
    got = _run([str(sidecar_python()), "-m", "pip", "install", *spec["packages"]],
               note, cancel)
    if not got["ok"]:
        note(f"packages did not install ({got['why']}; last line: {got['last'][:160]})")
        return {"ok": False, "engine": engine, "why": got["why"], "lines": lines}

    note("step 3 of 3 · the weights")
    warm = _run([str(sidecar_python()), "-c", spec["warm"]], note, cancel)
    if not warm["ok"]:
        note(f"weights did not arrive ({warm['why']}; last line: {warm['last'][:160]})")
        return {"ok": False, "engine": engine, "why": warm["why"], "lines": lines}

    try:
        sidecar_flag(engine).parent.mkdir(parents=True, exist_ok=True)
        sidecar_flag(engine).write_text(spec["label"], encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        note(f"the engine works but the note that records it did not save ({exc})")
    note(f"{spec['label']} is ready — replies in {spec['langs']} will use the voice you "
         f"chose. Speaking takes a few seconds on a CPU; that is the model, not a bug.")
    return {"ok": True, "engine": engine, "why": "", "lines": lines}


def sidecar_speak(text: str, lang: str, ref: str, transcript: str = "",
                  out_wav: str = "", engine: str = "") -> dict:
    """Hand one sentence to the borrowed interpreter; get a wav back. Nothing else."""
    engine = engine or ("indicf5" if (lang or "en").split("-")[0] == "ta" else "xtts")
    if not sidecar_ready(engine):
        return {"ok": False, "why": f"the {engine} engine is not installed",
                "wav": ""}
    script = script_path("clone_speak.py")
    if not script.is_file():
        return {"ok": False, "why": f"{script.name} is missing from the app", "wav": ""}
    argv = [str(sidecar_python()), str(script), "--engine", engine, "--text", text,
            "--reference", str(ref), "--out", str(out_wav),
            "--lang", (lang or "en").split("-")[0]]
    if transcript:
        argv += ["--transcript", transcript]
    got = _run(argv, lambda _l: None, None)
    if not got["ok"]:
        return {"ok": False, "why": got["last"] or got["why"], "wav": ""}
    import os as _os
    if out_wav and _os.path.exists(out_wav) and _os.path.getsize(out_wav) > 1024:
        return {"ok": True, "why": "", "wav": out_wav}
    return {"ok": False, "why": "the engine ran but wrote no audio", "wav": ""}


def _run(argv: list[str], on_line: Line, cancel: threading.Event | None) -> dict:
    """Run a child process and stream both streams into `on_line`.

    Kept as one small seam so tests can replace it and prove the logic without
    downloading 3.4 GB.
    """
    env = dict(os.environ, PYTHONUNBUFFERED="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1, env=env)
    except Exception as exc:  # noqa: BLE001 — must be reported, not raised
        return {"ok": False, "code": -1, "why": f"could not start: {exc}", "last": ""}
    last = ""
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.rstrip("\r\n")
        if line:
            last = line
            on_line(line)
        if cancel is not None and cancel.is_set():
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except Exception:
                proc.kill()
            return {"ok": False, "code": -2, "why": "cancelled", "last": last}
    code = proc.wait()
    return {"ok": code == 0, "code": code,
            "why": "" if code == 0 else f"exit code {code}", "last": last}


def install(engine: str, on_line: Line | None = None,
            cancel: threading.Event | None = None) -> dict:
    """Make one engine real: packages first, then the weights.

    Returns {"ok", "engine", "lines", "why"} — and `ok` means the warm-up step ran,
    which is the only thing that proves the weights are there.
    """
    say: Line = on_line or (lambda _l: None)
    if engine not in SPECS:
        return {"ok": False, "engine": engine, "why": f"unknown engine {engine!r}",
                "lines": []}
    spec = SPECS[engine]
    m = method()
    lines: list[str] = []

    def note(text: str) -> None:
        lines.append(text)
        say(text)

    note(f"{spec['label']} for {spec['langs']} — about {spec['size_mb'] / 1000:.1f} GB, "
         f"once. Internet needed. {spec['needs']}.")

    if m["frozen"]:
        note("this is the installed app, so the engine goes into a private folder of its "
             "own instead of inside the .exe (the .exe must stay small).")
        return ensure_sidecar(engine, on_line=say, cancel=cancel)

    if not m["can_install"]:
        note(f"cannot install from here: {m['why']}")
        return {"ok": False, "engine": engine, "why": m["why"] or "no pip", "lines": lines}

    note("step 1 of 2 · packages")
    got = _run([sys.executable, "-m", "pip", "install", *spec["packages"]], note, cancel)
    if not got["ok"]:
        note(f"packages did not install ({got['why']}; last line: {got['last'][:160]})")
        return {"ok": False, "engine": engine, "why": got["why"], "lines": lines}
    if cancel is not None and cancel.is_set():
        return {"ok": False, "engine": engine, "why": "cancelled", "lines": lines}

    note("step 2 of 2 · the weights (the big download, and the part that must not lie)")
    warm = _run([sys.executable, "-c", spec["warm"]], note, cancel)
    if not warm["ok"]:
        note(f"weights did not arrive ({warm['why']}; last line: {warm['last'][:160]})")
        note("the packages are installed but nothing is ready — retry, or use the free "
             "piper voice. ARC will keep saying 'system voice'.")
        return {"ok": False, "engine": engine, "why": warm["why"], "lines": lines}

    try:
        from . import clone
        clone.refresh()
    except Exception:
        pass
    from . import clone as _c
    if not _c.engines().get(engine, {}).get("available"):
        note("the download finished but the probe still cannot see the model — "
             "restart ARC, and if it still says 'system voice' the model folder is wrong.")
        return {"ok": False, "engine": engine, "why": "model not found after install",
                "lines": lines}

    note(f"{spec['label']} is ready. Replies in {spec['langs']} now use the voice you chose.")
    return {"ok": True, "engine": engine, "why": "", "lines": lines}


def summary() -> str:
    """Plain multi-line text for a console or a tool dialog."""
    m = method()
    rows = []
    for v in status().values():
        state = "ready" if v["ready"] else f"missing ({v['problem'] or 'not installed'})"
        rows.append(f"  {v['label']:<10} {v['langs']:<14} {v['size_mb']:>5} MB  {state}")
    head = ("  install route: " + ("pip (this build can do it in one click)"
                                   if m["can_install"] else m["why"]))
    return "\n".join([head, *rows])
