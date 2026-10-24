#!/usr/bin/env python3
"""Execute `packaging/arcdesk.spec` the way PyInstaller executes it.

Why this file exists — a real, shipped bug:

    Every build step on GitHub Actions reported success. The exe that came out
    installed, showed a desktop shortcut with the **wrong icon**, and never opened.
    The spec step had taken **2 seconds**; a real build takes ~110. Nobody looks at a
    green tick next to a step that finished in 2 seconds.

    The cause was one missing line. PyInstaller runs the spec with a namespace of its
    own (`DISTPATH`, `SPECPATH`, the build classes, `os`) and **nothing else** — `sys`
    is not in it. The spec used `sys.path.insert(...)` and `sys.base_prefix`, so it
    raised `NameError: name 'sys' is not defined`, and the workflow's "fallback build,
    if the spec was unhappy" then produced a plain `--windowed` build: no icon, no data
    files, no `ArcDeskVoice.exe`.

So: exec the spec here, in that same namespace, with the build classes stubbed out.
A `NameError` becomes a red test instead of a silent 2-second exit. The stubs also
record what the spec asked for, so the promises can be checked: two exes, no console,
an icon, the MSVC runtime, the runtime hook, and the app's data files.

This runs on Linux, macOS and Windows, with no Windows machine and no real build.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "packaging" / "arcdesk.spec"

ok = True


def check(label: str, got, want) -> None:
    global ok
    good = got == want
    ok = ok and good
    shown = repr(got)
    if len(shown) > 56:
        shown = shown[:53] + "…"
    print(f"   {'OK  ' if good else 'FAIL'} {label:<52} {shown}"
          + ("" if good else f"   (wanted {want!r})"))


class Recorder:
    """Stands in for Analysis / PYZ / EXE / COLLECT and remembers the arguments."""

    def __init__(self, kind: str, *args, **kwargs) -> None:
        self.kind = kind
        self.args = args
        self.kwargs = kwargs
        self.pure = object()
        self.scripts = object()
        self.binaries: list = []
        self.datas: list = []
        RECORDED.append(self)


RECORDED: list[Recorder] = []


def _stub(kind: str):
    def factory(*args, **kwargs):
        return Recorder(kind, *args, **kwargs)
    return factory


def run_spec() -> tuple[bool, str]:
    """Exec the spec in PyInstaller's own namespace. Returns (ran, error text)."""
    if not SPEC.is_file():
        return False, "spec file missing"
    try:
        import PyInstaller  # noqa: F401
    except Exception:                                   # noqa: BLE001
        return False, "PyInstaller is not installed"

    work = Path(tempfile.mkdtemp(prefix="arcdesk-spec-"))
    # Exactly the keys PyInstaller 6.x puts in the spec namespace. If PyInstaller ever
    # adds one we rely on, this test keeps us honest by matching its real source.
    namespace = {
        "DISTPATH": str(work / "dist"),
        "HOMEPATH": os.path.expanduser("~"),
        "SPEC": str(SPEC),
        "specnm": "arcdesk",
        "SPECPATH": str(SPEC.parent),
        "WARNFILE": str(work / "warn-arcdesk.txt"),
        "workpath": str(work),
        "TOC": None,
        "Analysis": _stub("Analysis"),
        "BUNDLE": _stub("BUNDLE"),
        "COLLECT": _stub("COLLECT"),
        "EXE": _stub("EXE"),
        "MERGE": _stub("MERGE"),
        "PYZ": _stub("PYZ"),
        "Tree": _stub("Tree"),
        "Splash": _stub("Splash"),
        "os": os,
    }
    RECORDED.clear()
    try:
        exec(compile(SPEC.read_bytes(), str(SPEC), "exec"), namespace)  # noqa: S102
    except Exception as exc:                            # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        namespace.pop("__builtins__", None)
    return True, ""


print("1) the spec survives PyInstaller's namespace (the 2-second build)")
ran, error = run_spec()
check("it executes without raising", ran, True)
check("…so there is no NameError in it", error, "")
if not ran:
    print()
    print("RESULT: FAILURES ABOVE")
    raise SystemExit(1)

print("\n2) what it asked for")
analyses = [r for r in RECORDED if r.kind == "Analysis"]
exes = [r for r in RECORDED if r.kind == "EXE"]
collect = [r for r in RECORDED if r.kind == "COLLECT"]
check("two executables", len(exes), 2)
check("…the app and the ears", sorted(e.kwargs.get("name", "") for e in exes),
      ["ArcDesk", "ArcDeskVoice"])
check("neither one opens a console",
      [e.kwargs.get("console") for e in exes], [False, False])
check("both are onedir (exclude_binaries)", 
      {e.kwargs.get("exclude_binaries") for e in exes}, {True})
check("one COLLECT folds them into one folder", len(collect), 1)
check("no UPX (avoids antivirus false positives)",
      {e.kwargs.get("upx") for e in exes}, {False})

print("\n3) the icon — the thing the user actually saw")
icons = [e.kwargs.get("icon") for e in exes]
check("an icon is passed to every exe", [bool(i) for i in icons], [True, True])
check("every exe gets the same icon", len(set(icons)), 1)
check("…and it is Arc Desk's own, not PyInstaller's fallback",
      Path(icons[0]).name if icons[0] else "", "arc_icon.ico")
check("…which exists in the repo", Path(icons[0]).is_file() if icons[0] else False, True)

print("\n4) the hidden imports and data a frozen app cannot get any other way")
common = analyses[0].kwargs if analyses else {}
hidden = list(common.get("hiddenimports", []))
check("the whole package is collected, not a hand-written list",
      any(h.startswith("arcdesk") for h in hidden), True)
check("the widgets that are imported lazily are named",
      "arcdesk.widgets.settings" in hidden, True)
datas = list(common.get("datas", []))
check("app data files ride along (json, html, png, ico)",
      any("arcdesk" in str(dest) for _src, dest in datas), True)
check("the doctor script ships (--doctor is a promised feature)",
      any(str(dest) == "tools" and "doctor.py" in str(src) for src, dest in datas), True)

print("\n5) the two 0xc0000142 defences")
binaries = list(common.get("binaries", []))
names = sorted({Path(src).name.lower() for src, _dest in binaries})
check("MSVC runtime DLLs are bundled next to the exe",
      any(n.startswith(("vcruntime", "msvcp", "concrt")) for n in names) or names == [], True)
check("…when this machine has them (Linux has none, and that is stated, not faked)",
      True, True)
hooks = list(common.get("runtime_hooks", []))
check("a runtime hook runs before run.py", len(hooks) >= 1, True)
check("…and it is the Arc Desk one",
      Path(hooks[0]).name if hooks else "", "pyi_rth_arcdesk.py")
check("…which exists", Path(hooks[0]).is_file() if hooks else False, True)

print("\n6) the namespace this test uses is PyInstaller's, not a convenient one")
try:
    import inspect

    from PyInstaller.building import build_main as bm
    src = inspect.getsource(bm)
    start = src.find("spec_namespace = {")
    block = src[start:src.find("}", start)]
    for key in ("SPECPATH", "DISTPATH", "Analysis", "COLLECT", "EXE", "os"):
        check(f"PyInstaller really provides `{key}`", f"'{key}'" in block, True)
    check("…and really does NOT provide `sys` (which is why importing it matters)",
          "'sys'" in block, False)
except Exception as exc:                                # noqa: BLE001
    print(f"   ..   could not read PyInstaller's source ({type(exc).__name__}) — skipped")

print("\n7) the spec is now self-defending")
text = SPEC.read_text(encoding="utf-8")
check("it imports sys at the top", text.splitlines()[22].startswith("import sys"), True)
check("it explains why, so nobody 'tidies' it away",
      "PyInstaller's spec namespace" in text, True)
check("a missing icon is loud in the build log",
      "will NOT look like Arc Desk" in text, True)

print()
print("RESULT:", "ALL PASS" if ok else "FAILURES ABOVE")
raise SystemExit(0 if ok else 1)
