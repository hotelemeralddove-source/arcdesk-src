#!/usr/bin/env python3
"""The build machine, judged: Store Python, the MSVC runtime, and the diagnostic.

The dialog this file exists for:

    AppInstallerPythonRedirector.exe - Application Error
    The application was unable to start correctly (0xc0000142).

That is not a bug inside the app's logic — it is a **build-machine** bug that produces an
installer which never opens. Two causes, both preventable, both checked here:

  1. building with the Microsoft Store's Python alias (its DLLs come from a restricted
     package folder, so the frozen exe cannot initialise them),
  2. a missing MSVC runtime on the target PC (Qt needs vcruntime140/msvcp140).

`tools/preflight_win.py` decides, before PyInstaller runs. Its rules are pure functions,
so they are proven here without a Windows machine.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("ARCDESK_HOME", tempfile.mkdtemp(prefix="arcdesk-win-"))

import preflight_win as pre  # noqa: E402

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


print("1) the Store Python alias is refused, by path, before anything is built")
store = r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe"
verdict, detail, fix = pre.classify_python(store, (3, 12), bits=64, in_venv=False)
check("verdict", verdict, pre.FAIL)
check("it is named as the store alias", "Microsoft Store Python alias" in detail, True)
check("the title of the dialog is quoted back", "0xc0000142" in detail, True)
check("the fix is the alias switch, not 'reinstall Windows'",
      "App execution aliases" in fix, True)
check("a store base_prefix is caught too, even from a real exe path",
      pre.classify_python(r"C:\Python312\python.exe", (3, 12),
                          base_prefix=store)[0], pre.FAIL)
check("the redirector name is caught",
      pre.classify_python(r"C:\x\AppInstallerPythonRedirector.exe", (3, 12))[0], pre.FAIL)

print("\n2) a real python.org interpreter passes")
verdict, detail, fix = pre.classify_python(r"C:\Python312\python.exe", (3, 12),
                                           bits=64, in_venv=True)
check("verdict", verdict, pre.PASS)
check("it says 64-bit", "64-bit" in detail, True)
check("nothing to fix", fix, "")
check("a venv is recognised",
      pre.classify_python(r"C:\repo\.venv\Scripts\python.exe", (3, 12), in_venv=True)[0],
      pre.PASS)
check("…and not being in one is only a warning",
      pre.classify_python(r"C:\Python312\python.exe", (3, 12), in_venv=False)[0], pre.WARN)

print("\n3) the other ways a build produces an exe that cannot open")
check("32-bit python is refused",
      pre.classify_python(r"C:\Python312-32\python.exe", (3, 12), bits=32)[0], pre.FAIL)
check("python 3.8 is refused",
      pre.classify_python(r"C:\Python38\python.exe", (3, 8), bits=64)[0], pre.FAIL)
check("python 3.9 builds but is flagged",
      pre.classify_python(r"C:\Python39\python.exe", (3, 9), bits=64)[0], pre.WARN)
check("python 3.11 in a venv is exactly right",
      pre.classify_python(r"C:\repo\.venv\Scripts\python.exe", (3, 11), bits=64,
                          in_venv=True)[0], pre.PASS)

print("\n4) the MSVC runtime is found and shipped, not assumed")
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    (base / "DLLs").mkdir()
    (base / "vcruntime140.dll").write_bytes(b"x")
    (base / "vcruntime140_1.dll").write_bytes(b"x")
    (base / "DLLs" / "msvcp140.dll").write_bytes(b"x")
    found = pre.msvc_runtime_files(base)
    names = sorted(Path(src).name for src, _ in found)
    check("all three are collected", names,
          ["msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"])
    check("they are shipped next to the exe, not in a subfolder",
          {dest for _, dest in found}, {"."})
    check("a name that is not there is not invented",
      "concrt140.dll" in names, False)
check("an empty folder yields nothing rather than a crash",
      pre.msvc_runtime_files(Path(tempfile.gettempdir()) / "does-not-exist-arcdesk"), [])
check("the list matches what Qt actually needs",
      set(pre.MSVC_DLLS) >= {"vcruntime140.dll", "msvcp140.dll"}, True)

print("\n5) the spec ships them (a static fact, checkable anywhere)")
spec = (ROOT / "packaging" / "arcdesk.spec").read_text(encoding="utf-8")
check("the spec asks preflight_win for the runtime",
      "from preflight_win import msvc_runtime_files" in spec, True)
check("…and puts them in binaries", "binaries=list(_msvc)" in spec, True)
check("…and says so when it finds none",
      "no MSVC DLLs found next to this Python" in spec, True)
check("0xc0000142 is explained where a builder will read it",
      "0xc0000142" in spec, True)
check("no console window still holds", "console=False" in spec, True)
check("still no UPX", "upx=False" in spec, True)
check("still onedir (onefile unpacks to %TEMP% every launch)",
      "exclude_binaries=True" in spec, True)

print("\n5b) the frozen app keeps a log even if it dies before run.py")
hook = ROOT / "packaging" / "pyi_rth_arcdesk.py"
check("the runtime hook exists", hook.is_file(), True)
check("the spec wires it in", "runtime_hooks=RUNTIME_HOOKS" in spec, True)
check("…and names the file", "pyi_rth_arcdesk.py" in spec, True)
import importlib.util                                          # noqa: E402
saved = sys.stdout, sys.stderr
try:
    sys.stdout = None                                          # what a windowed build has
    sys.stderr = None
    module_spec = importlib.util.spec_from_file_location("arc_rth", hook)
    hook_mod = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(hook_mod)                   # type: ignore[union-attr]
    rescued = sys.stdout, sys.stderr
finally:
    sys.stdout, sys.stderr = saved
check("with no console it still ends up with real streams",
      all(stream is not None for stream in rescued), True)
check("…both pointing at the same log file",
      getattr(rescued[0], "name", "") == getattr(rescued[1], "name", ""), True)
check("…and that file exists on disk", Path(getattr(rescued[0], "name", "/nope")).is_file(),
      True)

print("\n6) the build scripts cannot skip the check")
for name in ("build.bat", "build_all.bat"):
    bat = (ROOT / "packaging" / name).read_text(encoding="utf-8")
    order_pre = bat.find("tools\\preflight_win.py")
    # the *invocation*, not the word in a comment
    order_pyi = bat.find("-m PyInstaller")
    check(f"{name} runs the preflight", order_pre > 0, True)
    check(f"{name} runs it BEFORE PyInstaller starts", 0 < order_pre < order_pyi, True)
    check(f"{name} stops on a failure", "if errorlevel 1 (" in bat, True)
    check(f"{name} closes that block", "exit /b 1\n)" in bat, True)

print("\n7) the diagnostic needs nothing but Windows itself")
diag = ROOT / "ArcDeskDiag.bat"
check("ArcDeskDiag.bat exists (double-click, no install)", diag.is_file(), True)
text = diag.read_text(encoding="utf-8", errors="replace")
check("it runs without Python (only lookups, never an interpreter call)",
      "python -c" not in text and "%PY%" not in text, True)
check("it looks for the Store alias", "WindowsApps" in text, True)
check("it quotes the error the user saw", "0xc0000142" in text, True)
check("it checks the MSVC runtime", "vcruntime140.dll" in text, True)
check("it checks whether the download is blocked", "Unblock-File" in text, True)
check("…by reading the real zone stream, not a filename that never exists",
      "Zone.Identifier" in text, True)
check("…unblocks only, never deletes the download",
      "del " not in text.lower() and "rmdir" not in text.lower(), True)
check("…and asks before changing anything", "choice /c YN" in text, True)
check("it writes a report file", "ArcDeskDiag.txt" in text, True)
check("it points at the portable route that needs no installer",
      "ArcDesk-portable.zip" in text, True)
check("it ends with a pause so the window does not vanish", "pause" in text, True)
check("no PowerShell policy change, no PATH edit, no registry write",
      all(bad not in text.lower() for bad in ("setx ", "set-executionpolicy",
                                              "reg add", "net user")), True)

print("\n8) the guide matches the dialogs people actually get")
guide = (ROOT / "TROUBLESHOOT.md").read_text(encoding="utf-8")
for phrase in ("AppInstallerPythonRedirector", "0xc0000142", "Visual C++ Redistributable",
               "MSVCP140.dll", "Windows protected your PC", "WindowsApps"):
    check(f"covers {phrase}", phrase.lower() in guide.lower(), True)
check("the first thing it offers is the route that needs no Python at all",
      guide.index("Use it today, no installer") < guide.index("Rebuild only if you want"),
      True)
check("…and that route is the portable zip", "Extract All" in guide, True)
check("it says where the crash log is", "arcdesk.log" in guide, True)

print("\n9) the tool itself answers honestly on this machine")
rc_all = pre.run(verbose=False)
check("run(verbose=False) returns on warnings but fails on a real problem",
      rc_all in (0, 1), True)
import io                                                       # noqa: E402
import contextlib                                               # noqa: E402
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    pre.run(as_json=True)
import json                                                     # noqa: E402
data = json.loads(buf.getvalue())
check("the JSON has one row per check", len(data["rows"]), len(pre.CHECKS))
check("every row names a fix when it is not a pass",
      all(r["fix"] for r in data["rows"] if r["verdict"] in (pre.FAIL, pre.WARN)), True)

print()
print("RESULT:", "ALL PASS" if ok else "FAILURES ABOVE")
raise SystemExit(0 if ok else 1)
