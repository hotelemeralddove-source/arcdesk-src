"""One settings window: voice, wake word, boot behaviour, hotkeys, charms, weather.

Everything that used to need a JSON edit lives here. Same rule as the rest of the
app: cheap, plain widgets, one stylesheet, no background work while closed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from .. import autostart, config
from ..hotkeys import parse_combo
from ..theme import Theme
from ..wake.daemon_runner import model_path


def _note(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("note")
    lb.setWordWrap(True)
    return lb


def _heading(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("heading")
    return lb


class SettingsDialog(QDialog):
    applied = Signal()
    wake_test = Signal()
    open_brain = Signal()
    mcp_restart = Signal()

    def __init__(self, cfg: dict, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.theme = theme
        self.setWindowTitle("Arc Desk · settings")
        self.setMinimumSize(640, 560)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(12)

        head = QLabel("ARC DESK · SETTINGS")
        f = head.font()
        f.setPixelSize(10)
        f.setWeight(f.Weight.Bold)
        f.setLetterSpacing(f.SpacingType.AbsoluteSpacing, 2.6)
        head.setFont(f)
        lay.addWidget(head)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._voice_tab(), "Voice")
        self.tabs.addTab(self._system_tab(), "System")
        self.tabs.addTab(self._extras_tab(), "Charms & weather")
        tools_tab = self._tools_tab()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(tools_tab)
        self.tabs.addTab(scroll, "Local AI & tools")
        lay.addWidget(self.tabs, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self._save)
        row.addWidget(cancel)
        row.addWidget(save)
        lay.addLayout(row)

        self._load()
        self._style()

    # ------------------------------------------------------------ voice tab
    def _voice_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(9)

        # ---- how it opens: one question, two answers (same as first-run) -----
        from PySide6.QtWidgets import QRadioButton
        self.mode_icon = QRadioButton("Desktop icon — I double-click when I need you")
        self.mode_voice = QRadioButton('Voice — always waiting for "hey jarvis" '
                                       '(starts with Windows, microphone open)')
        self.mode_icon.setToolTip("Nothing runs in the background and nothing listens. "
                                  "Every feature still works once the window is open.")
        self.mode_voice.setToolTip("A microphone is open and a small daemon runs. "
                                   "Ctrl+Alt+Q quits at any time.")
        self.mode_icon.toggled.connect(self._mode_changed)
        self.mode_voice.toggled.connect(self._mode_changed)
        form.addRow("How ARC opens", self.mode_icon)
        form.addRow("", self.mode_voice)
        self.mode_hint = _note("")
        form.addRow("", self.mode_hint)

        self.wake_on = QCheckBox("Listen for the wake word")
        self.wake_on.setToolTip("Off by default. Nothing touches your microphone until this is on.")
        form.addRow(self.wake_on)

        self.phrase = QLineEdit()
        self.phrase.setPlaceholderText("hey jarvis")
        self.phrase.setToolTip("Any phrase works — no training, no download needed for the phrase")
        form.addRow("Wake phrase", self.phrase)

        self.engine = QComboBox()
        for key, label in (("auto", "Auto (recommended)"),
                           ("vosk", "Vosk — any phrase, offline"),
                           ("openwakeword", "openWakeWord — 'hey jarvis' only")):
            self.engine.addItem(label, key)
        form.addRow("Engine", self.engine)

        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        form.addRow("Local port", self.port)

        self.command_seconds = QDoubleSpinBox()
        self.command_seconds.setRange(2.0, 20.0)
        self.command_seconds.setSingleStep(1.0)
        self.command_seconds.setSuffix(" s")
        form.addRow("Command window", self.command_seconds)

        self.voice_on = QCheckBox("Speak answers aloud (Windows SAPI, free, offline)")
        form.addRow(self.voice_on)

        self.voice_status = _note("")
        form.addRow(self.voice_status)

        self.reply_note = _note("")
        form.addRow(self.reply_note)

        self.open_my_voice = QPushButton("Voices — who commands, which voice replies…")
        self.open_my_voice.setToolTip("Two lists: the voices allowed to command ARC, and "
                                      "the voice it answers in (yours, or any clip you have).")
        self.open_my_voice.clicked.connect(self.open_my_voice_dialog)
        myvoice_row = QHBoxLayout()
        myvoice_row.addWidget(self.open_my_voice)
        myvoice_row.addStretch(1)
        form.addRow(myvoice_row)

        btn_row = QHBoxLayout()
        test = QPushButton("Test wake (no mic)")
        test.clicked.connect(self.wake_test.emit)
        btn_row.addWidget(test)
        ears = QPushButton("Get the ears ready (mic + wake word)…")
        ears.setToolTip("Checks the microphone library, the wake engine, the 40 MB speech "
                        "model and the voice-lock model — and downloads what is missing.")
        ears.clicked.connect(self.open_ears)
        btn_row.addWidget(ears)
        install = QPushButton("Get the reply-voice engine…")
        install.setToolTip("IndicF5 (Tamil/Hindi) and XTTS (English) — the models that make "
                           "a cloned voice sound like the person. Installed from here.")
        install.clicked.connect(self.open_engines)
        btn_row.addWidget(install)
        btn_row.addStretch(1)
        form.addRow(btn_row)

        form.addRow(_heading("CINEMATIC SOUND & A COMPANION VOICE"))
        self.sfx_on = QCheckBox("Cinematic cues — open bloom, task tick, completion chime")
        self.sfx_on.setToolTip("Short cues generated in the app itself: no download, no "
                               "licence, and one switch away from silence.")
        form.addRow(self.sfx_on)
        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("Volume"))
        self.sfx_volume = QSlider(Qt.Orientation.Horizontal)
        self.sfx_volume.setRange(0, 100)
        self.sfx_volume.setFixedWidth(180)
        self.sfx_volume.setToolTip("Applies to the cues only — the reply voice has its own "
                                   "volume in Windows.")
        vol_row.addWidget(self.sfx_volume)
        self.sfx_test = QPushButton("Hear one")
        self.sfx_test.clicked.connect(lambda: __import__("arcdesk.sfx", fromlist=["sfx"]).play(
            "task_done", {"sfx": {"enabled": True,
                                  "volume": self.sfx_volume.value() / 100}}))
        vol_row.addWidget(self.sfx_test)
        vol_row.addStretch(1)
        form.addRow(vol_row)

        self.companion_on = QCheckBox("Talk to me like a person — \"Hi commander\", "
                                      "a task-related acknowledgement, \"Thank you\"")
        form.addRow(self.companion_on)
        hon = QHBoxLayout()
        hon.addWidget(QLabel("Call me"))
        self.honorific = QLineEdit()
        self.honorific.setPlaceholderText("commander")
        self.honorific.setFixedWidth(160)
        hon.addWidget(self.honorific)
        self.companion_preview = QPushButton("Preview the lines")
        self.companion_preview.clicked.connect(self._preview_companion)
        hon.addWidget(self.companion_preview)
        hon.addStretch(1)
        form.addRow(hon)
        self.companion_note = _note("")
        form.addRow(self.companion_note)

        form.addRow(_heading("WHO MAY COMMAND IT"))
        self.lock_on = QCheckBox("Only my voice may command ARC on this computer")
        self.lock_on.setToolTip("Record three short takes once; after that, another "
                                "person's voice is ignored. Not a security control — a "
                                "recording of you still passes.")
        form.addRow(self.lock_on)
        self.lock_status = _note("")
        form.addRow(self.lock_status)
        teach = QPushButton("Teach ARC my voice…")
        teach.clicked.connect(self.open_voice_lock)
        row2 = QHBoxLayout()
        row2.addWidget(teach)
        row2.addStretch(1)
        form.addRow(row2)
        return w

    # ------------------------------------------------------- open mode / lock
    def _mode_changed(self, _checked: bool = False) -> None:
        """The radio choice moves the two flags underneath it, everywhere.

        Picking "icon" clears both, because that is what the person just asked for: no
        microphone and nothing starting by itself. Anyone who wants "start silently at
        login but only open from the icon" ticks the start-with-Windows box afterwards —
        loading the settings never overwrites that choice (see `_refresh_mode_hint`).
        """
        voice = self.mode_voice.isChecked()
        self.wake_on.setChecked(voice)
        self.autostart_on.setChecked(voice)
        self._refresh_mode_hint()

    def _refresh_mode_hint(self) -> None:
        voice = self.mode_voice.isChecked()
        self.mode_hint.setText("Microphone stays open and ARC starts with Windows — that is "
                               "what makes \"hey jarvis\" work."
                               if voice else
                               "Nothing listens, nothing starts by itself. Double-click the "
                               "shortcut when you need me; every feature is there.")

    def open_my_voice_dialog(self) -> None:
        """Both lists: who may command ARC, and which voice it answers in."""
        from .voicelib_dialog import VoiceLibraryDialog
        dlg = VoiceLibraryDialog(self.cfg, self.theme, parent=self)
        dlg.exec()
        self.voice_on.setChecked(bool(self.cfg.get("ai", {}).get("voice", True)))
        self._refresh_voice_status()

    def open_voice_lock(self) -> None:
        """Enrol this person's voice without leaving the app."""
        from .voicelock import VoiceLockDialog
        dlg = VoiceLockDialog(self.cfg, parent=self)
        dlg.exec()
        if getattr(dlg, "result_note", ""):
            self.lock_status.setText(dlg.result_note)
        self.lock_on.setChecked(bool(self.cfg.setdefault("wake", {}).get("voice_lock", False)))
        self._refresh_lock_status()

    def _refresh_lock_status(self) -> None:
        try:
            from .. import voiceid
        except Exception as exc:                                # noqa: BLE001
            self.lock_status.setText(f"voice lock unavailable: {exc}")
            return
        ok, why = voiceid.available()
        people = voiceid.profiles()
        if not ok:
            self.lock_status.setText(f"needs the speaker-id engine — {why}")
            self.lock_on.setEnabled(False)
            return
        self.lock_on.setEnabled(True)
        if not people:
            self.lock_status.setText("ready, nobody enrolled yet — anyone can wake it")
        else:
            who = ", ".join(f"{n} ({p['samples']} takes)" for n, p in people.items())
            self.lock_status.setText(f"enrolled: {who}")

    def _refresh_voice_status(self) -> None:
        have_vosk = shutil.which("python") is not None and self._module_ok("vosk")
        have_mic = self._module_ok("sounddevice") or self._module_ok("pyaudio")
        have_model = model_path().exists()
        parts = [
            f"vosk: {'yes' if have_vosk else 'missing'}",
            f"microphone lib: {'yes' if have_mic else 'missing'}",
            f"speech model: {'present' if have_model else 'missing (~40 MB)'}",
        ]
        self.voice_status.setText("  ·  ".join(parts))
        # ...and the honest answer to "which voice will actually answer me?"
        reply = self.reply_voice_line(self.cfg)
        if hasattr(self, "reply_note"):
            self.reply_note.setText("Reply voice: " + reply)

    @staticmethod
    def reply_voice_line(cfg: dict | None = None) -> str:
        """One sentence naming the voice ARC will answer in, right now.

        Before this existed, the only way to find out was to make it speak and recognise
        the voice — which is how someone ends up asking "why is the reply voice a
        different voice?" The app now says it in words.
        """
        try:
            from .. import clone, voicelib
            ref = clone.reference()
            chosen = voicelib.active_reply()
            if not ref:
                return ("the system voice — no reply voice added yet (Settings → Voice).")
            if not (cfg or {}).get("ai", {}).get("voice_clone", True):
                return ("the system voice — \"use my voice for replies\" is switched off "
                        "(a clip of you is imported and kept).")
            ready = [k for k, v in clone.engines().items() if v.get("available")]
            if not ready:
                return ("the system voice — a clip is imported, but no clone engine is "
                        "installed (Settings → Voice → Get the reply-voice engine…).")
            who = f"“{chosen['name']}”" if chosen else "your recording"
            return (f"{who}, spoken by {' / '.join(ready)} "
                    f"({clone.analyse(ref)['seconds']:.1f} s reference).")
        except Exception as exc:                                     # noqa: BLE001
            return f"could not check ({type(exc).__name__})."

    @staticmethod
    def _module_ok(name: str) -> bool:
        try:
            __import__(name)
            return True
        except Exception:
            return False

    def open_brain_dialog(self) -> None:
        """Needs this name: `open_brain` is already a signal on this dialog."""
        from .brain_dialog import BrainDialog
        BrainDialog(self.cfg, self.theme, parent=self).exec()
        self._scan_backends()

    def open_ears(self) -> None:
        from .ears_dialog import EarsDialog
        EarsDialog(self.theme, parent=self).exec()
        self._refresh_voice_status()

    def open_engines(self) -> None:
        """The neural engine, installed from inside the app — one click, real output."""
        from .engine_dialog import EngineDialog
        EngineDialog(self.theme, parent=self).exec()
        self._refresh_voice_status()

    def _install_voice_help(self) -> None:
        QMessageBox.information(
            self, "Install the voice backend",
            "Run this once from the Arc Desk folder:\n\n"
            "    install_voice.bat\n\n"
            "It installs vosk + sounddevice and downloads the 40 MB speech model.\n"
            "Wake word stays OFF until you tick the box and save.")

    # ----------------------------------------------------------- system tab
    def _system_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(9)

        self.shadow = QCheckBox("Start hidden at boot (no window, no splash)")
        self.shadow.setToolTip("Windows itself is never modified — this only hides Arc Desk's window")
        form.addRow(self.shadow)

        self.tray = QCheckBox("Show a tray icon (recommended: gives you a visible handle)")
        form.addRow(self.tray)

        self.autostart_on = QCheckBox("Start Arc Desk when Windows starts")
        if sys.platform != "win32":
            self.autostart_on.setEnabled(False)
            self.autostart_on.setToolTip("Windows only")
        form.addRow(self.autostart_on)

        self.hotkey_palette = QLineEdit()
        self.hotkey_palette.setPlaceholderText("ctrl+alt+j")
        form.addRow("Palette hotkey", self.hotkey_palette)

        self.hotkey_quit = QLineEdit()
        self.hotkey_quit.setPlaceholderText("ctrl+alt+q")
        form.addRow("Quit hotkey", self.hotkey_quit)

        self.awaken_on = QCheckBox("Play the awakening sequence on the wake word")
        form.addRow(self.awaken_on)

        # This setting existed in settings.json and was read by nothing. A laptop on
        # battery, or an old GPU, is exactly why it should exist — and it is the one
        # visual control that measurably changes the cost of a frame.
        self.effects = QComboBox()
        self.effects.addItem("Follow the mode (default)", None)
        self.effects.addItem("Full glow", 1.0)
        self.effects.addItem("Reduced — lighter on old GPUs", 0.55)
        self.effects.addItem("Off — fastest, flat colours", 0.0)
        self.effects.setToolTip("How much glow and animation the ARC world draws. "
                                "Off is the fastest; charms hide themselves at Off.")
        form.addRow("Visual effects", self.effects)

        diag = QHBoxLayout()
        self.btn_doctor = QPushButton("Run doctor")
        self.btn_doctor.setToolTip("Check the whole install: toolkit, mic, wake word, "
                                   "brain, cost guard, log. Read-only.")
        self.btn_doctor.clicked.connect(self.show_doctor)
        self.btn_log = QPushButton("Open log")
        self.btn_log.setToolTip("Show the crash log. It never contains API keys.")
        self.btn_log.clicked.connect(self.show_log)
        diag.addWidget(self.btn_doctor)
        diag.addWidget(self.btn_log)
        diag.addStretch(1)
        holder = QWidget()
        holder.setLayout(diag)
        diag.setContentsMargins(0, 0, 0, 0)
        form.addRow("Diagnostics", holder)

        self.magic_on = QCheckBox('"Hey JARVIS" enters magic mode (fullscreen ARC + wallpaper)')
        form.addRow(self.magic_on)

        self.magic_exit = QLineEdit()
        self.magic_exit.setPlaceholderText("bye jarvis")
        form.addRow("Exit phrase", self.magic_exit)

        self.bye_action = QComboBox()
        self.bye_action.addItem("Close the app — launcher keeps listening", "exit")
        self.bye_action.addItem("Close the app — nothing stays behind", "quit")
        self.bye_action.addItem("Hide to background — instantest to reopen", "hide")
        self.bye_action.setToolTip("What \"BYE JARVIS\" does to the application itself")
        form.addRow("On \"BYE JARVIS\"", self.bye_action)

        self.magic_wallpaper = QCheckBox("Swap the wallpaper while magic mode is active")
        form.addRow(self.magic_wallpaper)
        form.addRow(_note("Every magic-mode change is reversible and journaled: if Arc Desk "
                          "is killed mid-session, your original wallpaper is restored on the "
                          "next start. We never touch Explorer, the taskbar's own settings or "
                          "the Windows shell."))

        form.addRow(_note("Windows is never altered: no wallpaper, icon, taskbar or theme "
                          "changes. Verify any time with the button below."))
        row = QHBoxLayout()
        b1 = QPushButton("Check Windows untouched")
        b1.clicked.connect(self._audit)
        row.addWidget(b1)
        b2 = QPushButton("Open settings folder")
        b2.clicked.connect(self._open_folder)
        row.addWidget(b2)
        b3 = QPushButton("Assistant brain…")
        b3.clicked.connect(self.open_brain.emit)
        row.addWidget(b3)
        row.addStretch(1)
        form.addRow(row)
        return w

    def _audit(self) -> None:
        from .. import desktop_guard
        problems = desktop_guard.scan_sources()
        base = config.data_dir() / "desktop_baseline.json"
        msg = []
        if problems:
            msg.append(f"{len(problems)} desktop-altering call(s) found in the code:")
            msg.extend(problems[:5])
        else:
            msg.append("Code scan: clean. No wallpaper / icon / taskbar / explorer APIs.")
        if base.exists():
            import json
            before = json.loads(base.read_text("utf-8"))
            diffs = desktop_guard.compare(before, desktop_guard.snapshot())
            msg.append("Shell: " + ("CHANGED\n  " + "\n  ".join(diffs) if diffs
                                    else "UNCHANGED since the baseline."))
        else:
            import json
            base.write_text(json.dumps(desktop_guard.snapshot(), indent=2), "utf-8")
            msg.append("Baseline saved for future comparisons.")
        QMessageBox.information(self, "Windows untouched", "\n".join(msg))

    def _open_folder(self) -> None:
        folder = str(config.data_dir())
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            QMessageBox.warning(self, "Could not open", f"{folder}\n\n{exc}")

    # ----------------------------------------------------------- extras tab
    def _extras_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(9)

        self.charms_on = QCheckBox("Show floating charms on the desktop")
        form.addRow(self.charms_on)
        self.charms_edit = QCheckBox("Start in charm edit mode (drag / resize)")
        form.addRow(self.charms_edit)
        form.addRow(_note("Charms are click-through unless edit mode is on, so they never "
                          "block your icons or taskbar. Hidden automatically in Gaming mode."))

        self.weather_on = QCheckBox("Weather in the HUD (needs internet)")
        form.addRow(self.weather_on)
        self.city = QLineEdit()
        form.addRow("City name", self.city)
        latlon = QHBoxLayout()
        self.lat = QLineEdit()
        self.lat.setPlaceholderText("latitude")
        self.lon = QLineEdit()
        self.lon.setPlaceholderText("longitude")
        latlon.addWidget(self.lat)
        latlon.addWidget(self.lon)
        form.addRow("Coordinates", latlon)
        form.addRow(_note("Weather is the only online feature and it is off by default. "
                          "Latitude/longitude come from your city; Belagavi is pre-filled."))
        return w

    # --------------------------------------------------------- tools tab
    def _tools_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        head = QHBoxLayout()
        self.btn_scan = QPushButton("Scan for local AI backends")
        self.btn_scan.clicked.connect(self._scan_backends)
        head.addWidget(self.btn_scan)
        self.btn_brain = QPushButton("Add a brain (local model)…")
        self.btn_brain.setToolTip("Downloads a small model and runs it on this laptop — "
                                  "no account, no separate Ollama install.")
        self.btn_brain.clicked.connect(self.open_brain_dialog)
        head.addWidget(self.btn_brain)
        head.addStretch(1)
        lay.addLayout(head)

        # what the brain is called out loud: "I am JARVIS"
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("It calls itself:"))
        self.ai_name = QLineEdit(str(self.cfg.get("ai", {}).get("name", "JARVIS")))
        self.ai_name.setPlaceholderText("JARVIS")
        self.ai_name.setToolTip("The name it introduces itself with — spoken, and in the "
                                "persona it is given.")
        name_row.addWidget(self.ai_name, 1)
        lay.addLayout(name_row)

        self.scan_out = QPlainTextEdit()
        self.scan_out.setObjectName("scanOut")
        self.scan_out.setReadOnly(True)
        self.scan_out.setFixedHeight(92)
        self.scan_out.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.scan_out.setPlainText(
            "Local engines detected on this PC:\n"
            + "\n".join(f"  {b.label:24s} :{b.port}"
                         for b in __import__("arcdesk.ai.backends",
                                             fromlist=["BACKENDS"]).BACKENDS[:5])
            + "\n  … 9 in total, see OPEN_SOURCE.md")
        lay.addWidget(self.scan_out)

        lay.addWidget(_note("Pick one and start it yourself — Arc Desk never bundles a model. "
                            "Its RAM stays in that process, not in Arc Desk."))

        row = QHBoxLayout()
        self.backend_combo = QComboBox()
        self.backend_combo.addItem("Auto-detect (recommended)", "auto")
        for b in __import__("arcdesk.ai.backends", fromlist=["BACKENDS"]).BACKENDS:
            self.backend_combo.addItem(f"{b.label}  ({b.repo})", b.key)
        self.backend_combo.addItem("ARC Lite (offline, no model)", "lite")
        self.backend_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.backend_combo.setMinimumContentsLength(10)
        row.addWidget(self.backend_combo, 1)
        use = QPushButton("Use this brain")
        use.clicked.connect(self._use_backend)
        row.addWidget(use)
        lay.addLayout(row)

        lay.addSpacing(6)
        cost_row = QHBoxLayout()
        cost_row.addWidget(QLabel("Allowed brain cost"))
        self.cost_combo = QComboBox()
        self.cost_combo.addItem("Local only — ₹0 forever, offline", "local")
        self.cost_combo.addItem("Free tiers allowed — ₹0, needs a key", "free")
        self.cost_combo.addItem("Anything — ⚠ may charge money", "paid")
        self.cost_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cost_combo.setMinimumContentsLength(10)
        cost_row.addWidget(self.cost_combo, 1)
        lay.addLayout(cost_row)
        self.cost_note = _note("")
        self.cost_note.setMinimumHeight(16)
        lay.addWidget(self.cost_note)
        self.cost_combo.currentIndexChanged.connect(self._cost_changed)

        lay.addSpacing(8)
        lay.addWidget(_note("MCP tool servers — any open-source MCP project on GitHub, "
                            "one per line as  name: command args\n"
                            "  files: npx -y @modelcontextprotocol/server-filesystem C:/Users/you/Docs\n"
                            "  fetch: uvx mcp-server-fetch"))
        self.mcp_text = QPlainTextEdit()
        self.mcp_text.setObjectName("scanOut")
        self.mcp_text.setFixedHeight(78)
        self.mcp_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.mcp_text.setPlaceholderText("name: command args…")
        lay.addWidget(self.mcp_text)

        addrow = QHBoxLayout()
        self.btn_mcp_all = QPushButton("Add all free servers")
        self.btn_mcp_all.setToolTip("Fetch, Time, Memory, Filesystem, Sequential Thinking, "
                                    "Everything, Playwright — all MIT/Apache, no account")
        self.btn_mcp_all.clicked.connect(self._add_mcp_presets)
        addrow.addWidget(self.btn_mcp_all)
        addrow.addStretch(1)
        lay.addLayout(addrow)
        self.mcp_preset_note = _note("")
        lay.addWidget(self.mcp_preset_note)
        self._refresh_mcp_presets()
        lay.addStretch(1)

        row2 = QHBoxLayout()
        self.mcp_on = QCheckBox("Enable MCP tool servers")
        row2.addWidget(self.mcp_on)
        row2.addStretch(1)
        self.btn_restart_mcp = QPushButton("Save & restart MCP")
        self.btn_restart_mcp.clicked.connect(self._save_mcp)
        row2.addWidget(self.btn_restart_mcp)
        lay.addLayout(row2)

        self.mcp_status = _note("")
        lay.addWidget(self.mcp_status)
        w.setMinimumHeight(560)
        w.setMinimumWidth(0)
        return w

    def _cost_changed(self) -> None:
        cls_ = self.cost_combo.currentData()
        if cls_ == "paid":
            box = QMessageBox(self)
            box.setWindowTitle("Allow paid providers?")
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText("This lets Arc Desk use providers that bill per token "
                        "(OpenAI, or any cloud endpoint).\n\n"
                        "Nothing is charged automatically and no card is stored here — "
                        "but requests to those providers cost money on your account.\n\n"
                        "Free options stay available: ARC Lite and the local engines.")
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            if box.exec() != QMessageBox.StandardButton.Yes:
                idx = max(0, self.cost_combo.findData("free"))
                self.cost_combo.setCurrentIndex(idx)
                return
        self._refresh_cost_note()

    def _refresh_cost_note(self) -> None:
        cls_ = self.cost_combo.currentData()
        text = {
            "local": "ARC Lite and all 9 local engines. No key, no account, no rate limit, "
                     "₹0 forever. Cloud providers are refused before a request is sent.",
            "free": "ARC Lite + local engines + cloud free tiers (Groq, Gemini). Still ₹0 — "
                    "they only need a key and have rate limits. Paid providers are blocked.",
            "paid": "⚠ Paid providers are allowed. Nothing is charged by Arc Desk itself; "
                    "your provider account is billed for the tokens you use.",
        }[cls_]
        self.cost_note.setText(text)

    def _preview_companion(self) -> None:
        from .. import companion_voice
        cfg = {"companion": {"enabled": True,
                             "honorific": self.honorific.text().strip() or "commander"}}
        lines = companion_voice.phrases(cfg)
        self.companion_note.setText("  ·  ".join(f"“{v}”" for v in lines.values()))

    def _save_ai_name(self) -> None:
        got = (self.ai_name.text() or "").strip()
        self.cfg.setdefault("ai", {})["name"] = got or "JARVIS"

    def _scan_backends(self) -> None:
        from ..ai import backends as bk
        self.btn_scan.setEnabled(False)
        self.scan_out.setPlainText("scanning localhost…")
        out: dict[str, str] = {}

        def work() -> None:
            found = bk.probe()
            if not found:
                out["text"] = ("nothing running. Install any of these, start it, then rescan:\n\n"
                               + "\n\n".join(f"{b.label} — {b.repo}\n  {hint}"
                                              for b, hint in
                                              ((b, bk.INSTALL_HINTS.get(b.key, ""))
                                               for b in bk.BACKENDS)))
            else:
                lines = ["found:"]
                for d in found:
                    lines.append(f"  {d.backend.label:20s} {d.base_url}")
                    lines.append(f"  {'':20s} models: {', '.join(d.models) or '(none loaded)'}")
                out["text"] = "\n".join(lines)

        t = threading.Thread(target=lambda: (work(), self.scan_out.setPlainText(out["text"]),
                                             self.btn_scan.setEnabled(True)), daemon=True)
        t.start()

    def _use_backend(self) -> None:
        ai = self.cfg.setdefault("ai", {})
        ai["provider"] = self.backend_combo.currentData()
        if ai["provider"] in ("auto", "lite"):
            ai["model"] = ""
            ai["base_url"] = ""
        config.save(self.cfg)
        self.mcp_status.setText(f"brain set to {self.backend_combo.currentText()}")
        self.applied.emit()

    def _refresh_mcp_presets(self) -> None:
        from ..ai import mcp_presets
        ok = mcp_presets.available()
        missing = mcp_presets.missing_runners()
        text = (f"{len(ok)} free servers can start on this PC: "
                + ", ".join(p.name for p in ok))
        if missing:
            text += ("\nMissing runner: " + ", ".join(missing)
                     + " — free to install; those servers stay off until then.")
        self.mcp_preset_note.setText(text)
        self.btn_mcp_all.setEnabled(bool(ok))

    def _add_mcp_presets(self) -> None:
        from ..ai import mcp_presets
        folder = QFileDialog.getExistingDirectory(
            self, "Which folder may the Filesystem server read?",
            str(Path.home() / "Documents"))
        added, skipped = mcp_presets.enable_all(self.cfg, workspace=folder or "")
        lines = self.mcp_text.toPlainText().splitlines()
        lines = [ln for ln in lines if ln.strip()]
        for srv in self.cfg.get("mcp", {}).get("servers", []):
            line = f"{srv['name']}: {srv['command']} " + " ".join(srv.get("args") or [])
            if not any(existing.startswith(srv["name"] + ":") for existing in lines):
                lines.append(line.strip())
        self.mcp_text.setPlainText("\n".join(lines))
        self._refresh_mcp_presets()
        body = f"Added {len(added)}: " + ", ".join(added)
        if skipped:
            body += "\n\nSkipped:\n  " + "\n  ".join(skipped)
        body += ("\n\nThey start when you press Save — Arc Desk spawns each one "
                 "on demand and kills them on exit.")
        QMessageBox.information(self, "MCP servers", body)

    def _save_mcp(self) -> None:
        servers = []
        for raw in self.mcp_text.toPlainText().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            name, rest = line.split(":", 1)
            parts = rest.split()
            if not parts:
                continue
            servers.append({"name": name.strip(), "command": parts[0],
                            "args": parts[1:], "enabled": True})
        cost = self.cfg.setdefault("cost", {})
        cost["enabled"] = True
        cost["max_class"] = self.cost_combo.currentData() or "free"

        mcp = self.cfg.setdefault("mcp", {})
        mcp["enabled"] = self.mcp_on.isChecked()
        mcp["servers"] = servers
        config.save(self.cfg)
        self.mcp_status.setText(f"{len(servers)} server(s) saved — restarting…")
        self.mcp_restart.emit()

    # -------------------------------------------------------------- loading
    # ---------------------------------------------------------- diagnostics
    def show_doctor(self) -> None:
        """Run the same checks as `python run.py --doctor`, in a window."""
        import contextlib
        import io
        import sys as _sys
        from pathlib import Path as _Path
        out = io.StringIO()
        try:
            tools_dir = str(_Path(__file__).resolve().parents[2] / "tools")
            if tools_dir not in _sys.path:
                _sys.path.insert(0, tools_dir)
            import doctor
            with contextlib.redirect_stdout(out):
                code = doctor.run(verbose=True)
            body = out.getvalue()
            if code != 0:
                body += ("\nFix the [FAIL] lines above - the app still opens, "
                         "but that feature will not work.")
        except Exception as exc:
            body = f"doctor could not run: {type(exc).__name__}: {exc}"
        box = QMessageBox(self)
        box.setWindowTitle("Arc Desk · doctor")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText("Install check")
        box.setInformativeText(body.strip().splitlines()[-1] if body.strip() else "")
        box.setDetailedText(body)
        box.exec()

    def show_log(self) -> None:
        """Show the crash log, then offer to clear it."""
        from .. import logs
        lines = logs.tail(200)
        text = "\n".join(lines) or "(the log is empty - nothing has gone wrong yet)"
        box = QMessageBox(self)
        box.setWindowTitle("Arc Desk · log")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(f"Last 200 lines · {logs.log_path()}")
        box.setDetailedText(text)
        box.exec()
        if lines:
            logs.clear()
            self.btn_log.setToolTip("Cleared. A new file starts at the next boot.")

    def _load(self) -> None:
        ai = self.cfg.get("ai", {})
        wk = self.cfg.get("wake", {})
        sh = self.cfg.get("shadow", {})
        ch = self.cfg.get("charms", {})
        we = self.cfg.get("weather", {})

        self.wake_on.setChecked(bool(wk.get("enabled")))
        self.autostart_on.setChecked(autostart.is_enabled())     # reality, before deciding
        mode = "voice" if (wk.get("enabled") and self.autostart_on.isChecked()) else "icon"
        for radio, on in ((self.mode_voice, mode == "voice"),
                          (self.mode_icon, mode != "voice")):
            radio.blockSignals(True)
            radio.setChecked(on)
            radio.blockSignals(False)
        self._refresh_mode_hint()
        self.lock_on.setChecked(bool(wk.get("voice_lock", False)))
        self._refresh_lock_status()
        self.phrase.setText(str(wk.get("phrase") or "hey jarvis"))
        idx = max(0, self.engine.findData(str(wk.get("engine") or "auto")))
        self.engine.setCurrentIndex(idx)
        self.port.setValue(int(wk.get("port", 8765)))
        self.command_seconds.setValue(float(wk.get("command_seconds", 7)))
        self.voice_on.setChecked(bool(ai.get("voice", True)))
        self.ai_name.setText(str(ai.get("name") or "JARVIS"))
        sfc = self.cfg.get("sfx", {})
        self.sfx_on.setChecked(bool(sfc.get("enabled", True)))
        self.sfx_volume.setValue(int(round(float(sfc.get("volume", 0.55)) * 100)))
        comp = self.cfg.get("companion", {})
        self.companion_on.setChecked(bool(comp.get("enabled", True)))
        self.honorific.setText(str(comp.get("honorific") or "commander"))
        self._refresh_voice_status()

        self.shadow.setChecked(bool(sh.get("enabled", True)))
        self.tray.setChecked(bool(sh.get("tray", True)))
        self.autostart_on.setChecked(autostart.is_enabled())
        self.hotkey_palette.setText(str(sh.get("hotkey_palette", "ctrl+alt+j")))
        self.hotkey_quit.setText(str(sh.get("hotkey_quit", "ctrl+alt+q")))
        self.awaken_on.setChecked(bool(sh.get("awaken", True)))
        eff = self.cfg.get("effects")
        eidx = self.effects.findData(eff)
        if eidx < 0:
            eidx = 0
        self.effects.setCurrentIndex(eidx)
        mg = self.cfg.get("magic", {})
        self.magic_on.setChecked(bool(mg.get("enabled", True)))
        self.magic_exit.setText(str(mg.get("exit_phrase") or "bye jarvis"))
        self.magic_wallpaper.setChecked(bool(mg.get("wallpaper", True)))
        bidx = max(0, self.bye_action.findData(str(sh.get("bye_action") or "exit")))
        self.bye_action.setCurrentIndex(bidx)

        self.charms_on.setChecked(bool(ch.get("enabled", True)))
        self.charms_edit.setChecked(bool(ch.get("edit_at_start", False)))
        mcp = self.cfg.get("mcp", {})
        self.mcp_on.setChecked(bool(mcp.get("enabled", True)))
        lines = []
        for srv in mcp.get("servers") or []:
            args = srv.get("args") or []
            lines.append(f"{srv.get('name','server')}: {srv.get('command','')} "
                         + " ".join(str(a) for a in args))
        self.mcp_text.setPlainText("\n".join(lines))
        cost = self.cfg.get("cost", {})
        cidx = max(0, self.cost_combo.findData(str(cost.get("max_class") or "free")))
        self.cost_combo.setCurrentIndex(cidx)
        self._refresh_cost_note()
        ai = self.cfg.get("ai", {})
        idx = max(0, self.backend_combo.findData(str(ai.get("provider") or "auto")))
        self.backend_combo.setCurrentIndex(idx)
        self.mcp_status.setText(self._mcp_hint())

        self.weather_on.setChecked(bool(we.get("enabled")))
        self.city.setText(str(we.get("city") or ""))
        self.lat.setText(str(we.get("lat") or ""))
        self.lon.setText(str(we.get("lon") or ""))

    # --------------------------------------------------------------- saving
    def _save(self) -> None:
        # validate hotkeys before writing anything
        for field, label in ((self.hotkey_palette, "Palette hotkey"),
                             (self.hotkey_quit, "Quit hotkey")):
            text = field.text().strip()
            if not text:
                continue
            try:
                parse_combo(text)
            except ValueError as exc:
                QMessageBox.warning(self, "Check the hotkey",
                                    f"{label}: {exc}\n\nTry ctrl+alt+j")
                self.tabs.setCurrentIndex(1)
                field.setFocus()
                return

        ai = self.cfg.setdefault("ai", {})
        ai["voice"] = self.voice_on.isChecked()

        wk = self.cfg.setdefault("wake", {})
        wk["enabled"] = self.wake_on.isChecked()
        wk["phrase"] = (self.phrase.text().strip() or "hey jarvis").lower()
        wk["engine"] = self.engine.currentData()
        wk["port"] = int(self.port.value())
        wk["command_seconds"] = float(self.command_seconds.value())
        wk["voice_lock"] = self.lock_on.isChecked()
        self.cfg["open_mode"] = "voice" if self.mode_voice.isChecked() else "icon"

        sh = self.cfg.setdefault("shadow", {})
        sh["enabled"] = self.shadow.isChecked()
        sh["tray"] = self.tray.isChecked()
        sh["hotkey_palette"] = self.hotkey_palette.text().strip() or "ctrl+alt+j"
        sh["hotkey_quit"] = self.hotkey_quit.text().strip() or "ctrl+alt+q"
        sh["awaken"] = self.awaken_on.isChecked()
        self.cfg["effects"] = self.effects.currentData()      # None = follow the mode
        sh["bye_action"] = self.bye_action.currentData() or "exit"

        mg = self.cfg.setdefault("magic", {})
        mg["enabled"] = self.magic_on.isChecked()
        mg["exit_phrase"] = (self.magic_exit.text().strip() or "bye jarvis").lower()
        mg["wallpaper"] = self.magic_wallpaper.isChecked()

        ch = self.cfg.setdefault("charms", {})
        ch["enabled"] = self.charms_on.isChecked()
        ch["edit_at_start"] = self.charms_edit.isChecked()

        we = self.cfg.setdefault("weather", {})
        we["enabled"] = self.weather_on.isChecked()
        we["city"] = self.city.text().strip()
        try:
            if self.lat.text().strip():
                we["lat"] = float(self.lat.text())
            if self.lon.text().strip():
                we["lon"] = float(self.lon.text())
        except ValueError:
            QMessageBox.warning(self, "Coordinates", "Latitude and longitude must be numbers.")
            return

        want = self.autostart_on.isChecked()
        if want != autostart.is_enabled():
            took = autostart.set_enabled(want)
            if not took:
                QMessageBox.information(
                    self, "Startup entry not created",
                    "The system refused to add (or remove) the startup entry, so ARC "
                    "will not start by itself. Everything else saved. On Windows this "
                    "is one per-user value; on other systems it may need a desktop entry.")
        self.cfg["autostart"] = autostart.is_enabled()
        self._save_ai_name()
        self.cfg.setdefault("sfx", {}).update(enabled=self.sfx_on.isChecked(),
                                              volume=self.sfx_volume.value() / 100)
        self.cfg.setdefault("companion", {}).update(
            enabled=self.companion_on.isChecked(),
            honorific=(self.honorific.text().strip() or "commander"))

        config.save(self.cfg)
        self.applied.emit()
        self.accept()

    # ---------------------------------------------------------------- style
    @staticmethod
    def _mcp_hint() -> str:
        try:
            from ..ai.mcp import shutil as _sh
            have_npx = bool(_sh.which("npx"))
            have_uvx = bool(_sh.which("uvx"))
            return (f"node/npx: {'yes' if have_npx else 'not found'}  ·  "
                    f"uvx: {'yes' if have_uvx else 'not found'}")
        except Exception:
            return ""

    def _style(self) -> None:
        th = self.theme
        self.setStyleSheet(f"""
            QDialog {{ background: {th.bg}; color: {th.text}; }}
            QLabel {{ color: {th.text}; }}
            QLabel#note {{ color: {th.q('dim').lighter(150).name()}; font-size: 11px; }}
            QScrollArea, QScrollArea > QWidget > QWidget {{
                background: transparent; }}
            QTabWidget::pane {{ border: 1px solid {th.q('dim').name()};
                                border-radius: 10px; top: -1px; }}
            QTabBar::tab {{ background: {th.panel}; color: {th.q('dim').lighter(150).name()};
                            padding: 7px 14px; border-top-left-radius: 8px;
                            border-top-right-radius: 8px; margin-right: 2px;
                            font-size: 11px; }}
            QTabBar::tab:selected {{ background: {th.q('accent').darker(150).name()};
                                     color: {th.accent}; }}
            QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
                background: {th.panel}; color: {th.text};
                border: 1px solid {th.q('dim').name()}; border-radius: 8px; padding: 5px 8px; }}
            QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {th.accent}; }}
            QComboBox QAbstractItemView {{ background: {th.panel}; color: {th.text};
                selection-background-color: {th.accent}; }}
            QCheckBox {{ color: {th.text}; }}
            QPushButton {{ background: {th.q('accent').darker(115).name()}; color: #04090f;
                border: none; border-radius: 8px; padding: 7px 14px; font-weight: 600; }}
            QPushButton:disabled {{ background: {th.panel}; color: {th.dim}; }}
            QPlainTextEdit#scanOut {{ background: {th.panel};
                color: {th.q('dim').lighter(150).name()};
                border: 1px solid {th.q('dim').name()}; border-radius: 8px;
                font-family: Consolas, monospace; font-size: 11px; padding: 6px; }}
        """)
