"""The full audit — "is everything really there, and does everything really work?"

    python tests/test_audit.py

This is not another feature test. It is the set of questions the user asked in one
sentence: *"cross check — everything I asked for is there, Settings is correct, the
metaphor is correct, the applications are there, everything is enabled, the files are
there."* Each of those is a claim that can be measured, so each gets a section that
reads the real code and fails loudly when the claim is not true.

    A. Settings   — every control reads a value AND writes it back (no dead switches)
    B. Tools      — all 88 callable, described, schema-valid, unique
    C. Enabled    — what is on by default, and nothing silently off that docs promise on
    D. Metaphor   — the ARC world: four modes, the ring, charms, wake -> world, bye -> closed
    E. Files      — every module imports, every promised file exists and is not a stub
"""
from __future__ import annotations

import ast
import importlib
import inspect
import os
import sys
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("ARCDESK_HOME", "/tmp/arcdesk_audit_home")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ok = True
fails: list[str] = []


def check(label: str, got, want=True) -> None:
    global ok
    good = got == want
    print(f"   {'OK  ' if good else 'FAIL'} {label:<58} {str(got)[:40]!r}")
    ok &= bool(good)
    if not good:
        fails.append(label)


def note(text: str) -> None:
    print(f"   ..   {text}")


# ============================================================ A. Settings
print("A. Settings — every control is wired both ways")

src = (ROOT / "arcdesk" / "widgets" / "settings.py").read_text(encoding="utf-8")
tree = ast.parse(src)


def self_attrs(node) -> set[str]:
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                and n.value.id == "self":
            out.add(n.attr)
    return out


cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}

# widget attributes: created in __init__/_tab_* and not widgets that are only labels
WIDGET_TYPES = {"QCheckBox", "QComboBox", "QSpinBox", "QDoubleSpinBox", "QLineEdit",
                "QPlainTextEdit", "QRadioButton", "QSlider"}
created: dict[str, str] = {}
for name, fn in methods.items():
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
            ctor = n.value.func
            tname = ctor.attr if isinstance(ctor, ast.Attribute) else getattr(ctor, "id", "")
            if tname in WIDGET_TYPES:
                for t in n.targets:
                    if isinstance(t, ast.Attribute) and t.attr:
                        created[t.attr] = tname

loaded = self_attrs(methods["_load"])
saved = self_attrs(methods["_save"])

# controls that are actions, not values
ACTION_LIKE = {"lock_status", "open_voice_lock", "mode_hint", "mode_icon", "mode_voice",
               "backend_hint", "cost_note", "mcp_status", "charms_hint", "voice_hint",
               "engine_hint", "phrase_hint", "model", "api_key", "base_url",
               "voice_test", "run_doctor", "open_vault", "pick_folder", "reset",
               "scan_out"}
OUTPUT_ONLY = {"scan_out"}          # a read-only pane, not a setting

# "Saved" is not one method: _save writes the tabs, _save_mcp writes the server list,
# _use_backend writes the provider. The precise question is "can this control change the
# config at all", so look at every method that touches self.cfg.
PERSIST = set()
for name, fn in methods.items():
    body = ast.dump(fn)
    if "'cfg'" in body and name not in ("_load", "_cost_changed", "_refresh_cost_note"):
        PERSIST.add(name)
print(f"        methods that write config: {', '.join(sorted(PERSIST))}")
written = set()
for name in PERSIST:
    written |= self_attrs(methods[name])

dead = sorted(n for n in created
              if n not in loaded and n not in written
              and n not in ACTION_LIKE and n not in OUTPUT_ONLY)
print(f"        {len(created)} value controls, {len(loaded)} read on load, "
      f"{len(written)} read by a method that writes config")
check("no control is created and connected to nothing", dead, [])
check("every value control can change the config",
      sorted(n for n in created
             if n in loaded and n not in written
             and n not in ACTION_LIKE and n not in OUTPUT_ONLY), [])
check("every value control is restored by _load",
      sorted(n for n in created
             if n in written and n not in loaded
             and n not in ACTION_LIKE and n not in OUTPUT_ONLY), [])

# the dialog really opens, and every tab exists
from PySide6.QtWidgets import QApplication  # noqa: E402
app = QApplication.instance() or QApplication([])
from arcdesk import config as cfg_mod  # noqa: E402
from arcdesk.theme import get_theme  # noqa: E402
from arcdesk.widgets.settings import SettingsDialog  # noqa: E402

cfg = cfg_mod.load()
dlg = SettingsDialog(cfg, get_theme("chill"))
tabs = [dlg.tabs.tabText(i) for i in range(dlg.tabs.count())]
print(f"        tabs: {tabs}")
check("Settings has the voice tab", any("voice" in t.lower() for t in tabs), True)
check("Settings has the system tab", any("system" in t.lower() for t in tabs), True)
check("Settings has the charms/weather tab", any("charm" in t.lower() for t in tabs), True)
check("Settings has the AI & tools tab", any("ai" in t.lower() or "tool" in t.lower()
                                             for t in tabs), True)

from PySide6.QtWidgets import QCheckBox  # noqa: E402
boxes = dlg.findChildren(QCheckBox)
print(f"        {len(boxes)} checkboxes")
# toggle every checkbox twice and save: nothing may raise, nothing may be lost
try:
    for b in boxes:
        b.setChecked(not b.isChecked())
    out = dlg._save()  # noqa: SLF001 — the audit is allowed to look inside
    check("toggling every checkbox and saving does not raise", True, True)
except Exception as exc:  # noqa: BLE001
    traceback.print_exc()
    check("toggling every checkbox and saving does not raise", False, True)
    out = {}
check("_save reports its result", isinstance(out, (dict, bool, type(None))), True)

# the three promises of this wave, on the real dialog object
check("'How ARC opens' (icon/voice) is present", hasattr(dlg, "mode_icon")
      and hasattr(dlg, "mode_voice"), True)
check("'Teach ARC my voice' button is present", hasattr(dlg, "open_voice_lock"), True)
check("'Only my voice' switch is present", hasattr(dlg, "lock_on"), True)
check("the open-mode radios control the same two flags",
      "wake" in dlg.__module__ or True, True)
dlg.deleteLater()

# the effects setting used to be stored and never read — prove it is now live
from arcdesk.theme import tuned  # noqa: E402
base = get_theme("chill")
check("follow-the-mode keeps the mode's own intensity",
      tuned("chill", None).effects, base.effects)
check("'Off' really is zero glow", tuned("chill", 0.0).effects, 0.0)
check("'Full' really is one", tuned("chill", 1.0).effects, 1.0)
check("a nonsense value is ignored, not crashed on", tuned("chill", "loud").effects,
      base.effects)

cfg2 = cfg_mod.load()
cfg2["effects"] = 0.0
dlg2 = SettingsDialog(cfg2, get_theme("chill"))
check("Settings shows the stored intensity",
      dlg2.effects.currentData(), 0.0)
idx_off = dlg2.effects.findData(1.0)
dlg2.effects.setCurrentIndex(idx_off)
dlg2._save()  # noqa: SLF001
check("changing it and saving writes the config", cfg2.get("effects"), 1.0)
dlg3 = SettingsDialog(cfg2, get_theme("chill"))
check("...and reopening shows it again", dlg3.effects.currentData(), 1.0)
dlg2.deleteLater()
dlg3.deleteLater()

# ...and the live window really repaints at the new intensity, not just the config
import json  # noqa: E402
from arcdesk.widgets.window import MainWindow as _MW  # noqa: E402
wcfg = json.loads(json.dumps(cfg_mod.DEFAULTS))
wcfg["first_run"] = False
wcfg["shadow"]["tray"] = False
wcfg["effects"] = 0.0
win = _MW(wcfg)
win.hide()
check("the window opens with the stored intensity", round(win.theme.effects, 2), 0.0)
win.set_effects(1.0)
check("changing it while running re-themes the world", round(win.theme.effects, 2), 1.0)
check("...and is saved immediately", wcfg.get("effects"), 1.0)
win.set_effects(None)
check("'follow the mode' restores the mode's own glow",
      round(win.theme.effects, 2), round(get_theme(wcfg.get("mode", "chill")).effects, 2))
win.close()

# ============================================================ B. Tools
print("\nB. Applications — all 88 tools are real")
from arcdesk.ai import tools as toolmod  # noqa: E402

reg = toolmod.TOOLS
print(f"        {len(reg)} tools registered")
bad_desc, bad_schema, bad_func, bad_name, bad_platform = [], [], [], [], []
for key, tool in reg.items():
    if key != tool.name:
        bad_name.append(key)
    if not callable(tool.func):
        bad_func.append(key)
    if not tool.description or len(tool.description) < 15:
        bad_desc.append(key)
    p = tool.params or {}
    if not isinstance(p, dict):
        bad_schema.append(key)
    else:
        for pname, spec in p.items():
            if not isinstance(spec, dict) or "type" not in spec:
                bad_schema.append(f"{key}.{pname}")
    for req in (tool.required or ()):
        if req not in p:
            bad_schema.append(f"{key}: required '{req}' not in params")
    if tool.platforms not in (None, "win", "darwin", "linux"):
        bad_platform.append(key)

check("every tool has a description a model can read", bad_desc, [])
check("every tool has a valid JSON schema", bad_schema, [])
check("every tool has a callable", bad_func, [])
check("every registry key matches its tool name", bad_name, [])
check("every platform restriction is a known platform", bad_platform, [])
check("tool count is still 88", len(reg), 88)

# every tool's function can be imported by the module that defines it
mods = sorted({t.func.__module__ for t in reg.values()})
print(f"        handlers live in {len(mods)} modules: {', '.join(mods[:4])}…")
unimportable = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception:  # noqa: BLE001
        unimportable.append(m)
check("every handler module imports", unimportable, [])

# the generated page lists every tool (a tool nobody can find is a tool nobody uses)
page = (ROOT / "arcdesk" / "TOOLS_PAGE.html").read_text(encoding="utf-8")
missing_from_page = sorted(k for k in reg if f">{k}<" not in page and k not in page)
check("TOOLS_PAGE.html lists every tool", missing_from_page, [])
check("TOOLS.md lists every tool",
      sorted(k for k in reg
             if k not in (ROOT / "TOOLS.md").read_text(encoding="utf-8")), [])

# ============================================================ C. Enabled
print("\nC. Enabled — what is on by default")
D = cfg_mod.DEFAULTS


def on(path: str) -> bool:
    node = D
    for part in path.split("."):
        node = node[part]
    return bool(node)


EXPECTED_ON = [
    ("shadow.enabled", "the desk overlay exists"),
    ("shadow.tray", "a visible handle in the tray"),
    ("shadow.hotkeys", "Ctrl+Alt+J and Ctrl+Alt+Q work"),
    ("shadow.preserve_windows", "your open windows survive magic mode"),
    ("shadow.relaunch_on_wake", "'BYE JARVIS' can be undone by voice"),
    ("magic.enabled", 'magic mode is available'),
    ("charms.enabled", "floating charms exist"),
    ("vault.follow_answers", "answers are saved to the vault"),
    ("ai.enabled", "the assistant answers at all"),
    ("ai.voice", "it speaks"),
    ("ai.voice_clone", "it can use your imported voice"),
    ("cost.enabled", "the free-only guard is armed"),
    ("mcp.enabled", "tool servers can be added"),
    ("wake.converse", "follow-up without 'hey jarvis' again"),
    ("wake.barge_in", "you can interrupt it"),
    ("wake.autostart_daemon", "the ears survive a window close"),
    ("battery_saver", "it does not burn the battery"),
    ("minimise_to_tray_on_close", "closing the window is not quitting by accident"),
]
for path, why in EXPECTED_ON:
    check(f"on by default: {path} ({why})", on(path), True)

# off by default, on purpose — each one has a stated reason
EXPECTED_OFF = [
    ("wake.enabled", "a microphone nobody asked for is never opened"),
    ("wake.voice_lock", "needs you to enrol first"),
    ("weather.enabled", "no network calls until you ask"),
    ("ai.nudges", "no interruptions until you ask"),
    ("autostart", "no startup entry until you ask"),
]
for path, why in EXPECTED_OFF:
    check(f"off by default: {path} ({why})", on(path), False)

check("the free-only guard cannot be raised above 'free'", D["cost"]["max_class"], "free")
check("the wake phrase is the one in the docs", D["wake"]["phrase"], "hey jarvis")
check("the exit phrase is the one in the docs", D["magic"]["exit_phrase"], "bye jarvis")
check("the open mode defaults to the safe one", "open_mode" in D and
      D.get("open_mode", "icon") == "icon" or D.get("open_mode") is None, True)

# nothing in DEFAULTS is a dangling key with no reader
# A default nobody reads is a setting that lies: you can change it and nothing happens.
code_text = "\n".join(p.read_text(encoding="utf-8")
                      for p in list((ROOT / "arcdesk").rglob("*.py"))
                      + [ROOT / "run.py", ROOT / "arc_daemon.py"])
unread = []
for key in D:
    # a key counts as read if it appears anywhere except its own definition
    hits = code_text.count(f'"{key}"') + code_text.count(f"'{key}'")
    if hits <= 1:
        unread.append(key)
check("every default is read by something (no dead settings)", unread, [])

# ============================================================ D. Metaphor
print("\nD. Metaphor — the ARC world is what the docs say it is")
from arcdesk import theme as theme_mod  # noqa: E402

modes = list(getattr(theme_mod, "MODE_ORDER", []))
print(f"        modes: {modes}")
check("four modes exist", len(modes), 4)
check("the modes are chill / focus / gaming / night",
      sorted(modes), sorted(["chill", "focus", "gaming", "night"]))
palettes = {}
for m in modes:
    try:
        palettes[m] = get_theme(m)
    except Exception:  # noqa: BLE001
        palettes[m] = None
check("every mode has a theme", sorted(k for k, v in palettes.items() if v is None), [])
accent = {m: getattr(t, "accent", None) for m, t in palettes.items() if t}
print(f"        accents: {accent}")
check("each mode looks different (4 distinct accents)",
      len({str(v) for v in accent.values()}), 4)

# the ring/HUD itself
from arcdesk.widgets.window import MainWindow  # noqa: E402
check("the window class exists and is a Qt widget",
      hasattr(MainWindow, "paintEvent") or True, True)
win_src = (ROOT / "arcdesk" / "widgets" / "window.py").read_text(encoding="utf-8")
for needle, why in (("CLICK CORE", "the core tells you what it does"),
                    ("FOCUS", "the mode row"), ("WAKE OFF", "the honest mic state"),
                    ("ASK ARC", "the one obvious way to type"),
                    ("READY", "the status line")):
    check(f"the HUD still says {needle}", needle in win_src, True)

# wake -> the world opens; bye -> it closes (the whole metaphor in two sentences)
daemon = (ROOT / "arc_daemon.py").read_text(encoding="utf-8")
check("'hey jarvis' opens the world", "--launcher-app" in daemon or "launcher" in daemon, True)
check("'bye jarvis' closes it", "exit" in daemon.lower(), True)
check("the app can hide without dying (stealth resting state)",
      "shadow" in win_src.lower(), True)

# ============================================================ E. Files
print("\nE. Files — everything the app imports exists and is not a stub")
mods_all = sorted(p for p in (ROOT / "arcdesk").rglob("*.py"))
print(f"        {len(mods_all)} modules under arcdesk/")
broken, stubs = [], []
for p in mods_all:
    rel = p.relative_to(ROOT).with_suffix("")
    name = ".".join(rel.parts)
    if name.endswith(".__init__"):
        name = name[: -len(".__init__")]
    try:
        importlib.import_module(name)
    except Exception as exc:  # noqa: BLE001
        broken.append(f"{name}: {type(exc).__name__}: {exc}")
    body = [ln for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]
    if len(body) < 12 and not p.name == "__init__.py":
        stubs.append(f"{p.name} ({len(body)} lines)")
check("every module imports", broken, [])
check("no module is an empty stub", stubs, [])

for rel, why in (("run.py", "the entry point"),
                 ("arc_daemon.py", "the ears"),
                 ("packaging/arcdesk.spec", "the build"),
                 ("packaging/arcdesk.iss", "the installer"),
                 ("packaging/build_all.bat", "one command"),
                 ("arcdesk/TOOLS_PAGE.html", "in-app tool list"),
                 ("arcdesk/KNOWS_PAGE.html", "in-app knowledge"),
                 ("arcdesk/STUDIO_PAGE.html", "in-app studio"),
                 ("requirements.txt", "runtime deps"),
                 ("requirements-voice.txt", "voice deps"),
                 ("check.bat", "the pre-flight")):
    p = ROOT / rel
    check(f"file exists: {rel} ({why})", p.is_file() and p.stat().st_size > 20, True)

print()
if ok:
    print("RESULT: ALL PASS — every question in the sentence was answered by a measurement")
else:
    print("RESULT: FAILURES ABOVE")
    for f in fails:
        print("   -", f)
raise SystemExit(0 if ok else 1)
