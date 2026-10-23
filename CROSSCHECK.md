# ARC DESK — cross-check (generated)

Last run: 23 October 2026, 09:45 · `python tools/crosscheck.py --write`

Every `ok` below is a command that ran. `need` means this machine physically cannot prove it (no Windows build machine, no microphone, no desktop).

| | what | how it was checked |
|---|---|---|
| ok | 88 tools in the registry | 7 ask before acting |
| ok | 27 documents | BOOT.md, BUILD_REPORT.md, CAPABILITIES.md, COMMANDS.md … |
| ok | 60 test files | present |
| ok | arcdesk/TOOLS_PAGE.html | present |
| ok | arcdesk/KNOWS_PAGE.html | present |
| ok | packaging/arcdesk.spec | present |
| ok | packaging/build.bat | present |
| ok | packaging/arcdesk.iss | present |
| ok | packaging/make_installer.bat | present |
| ok | packaging/build_all.bat | present |
| ok | arcdesk/photo.py | present |
| ok | arcdesk/clone.py | present |
| ok | arcdesk/voiceid.py | present |
| ok | arcdesk/widgets/voicelock.py | present |
| ok | tools/voice_setup.py | present |
| ok | tools/clean_voice.py | present |
| ok | tools/move.py | present |
| ok | install_clone.bat | present |
| ok | MOVE.md | present |
| ok | VOICE.md | present |
| ok | packaging/fetch_runtime.py | present |
| ok | shots/arc_icon.ico | present |
| ok | TOOLS.md | present |
| ok | uninstall.bat | present |
| ok | check.bat | present |
| ok | install.bat | present |
| ok | install_voice.bat | present |
| **ok** | TOOLS.md + TOOLS_PAGE.html current | tools reference is current — 88 tools, 10 sections, 0 mismatch |
| **ok** | packaging consistent | 76 checks, 0 failed |
| **ok** | docs agree with the code | counts, files, tests |
| **ok** | Answer speed measured | Lite p50 0.36 ms · routing 1.06 ms |
| **ok** | every tool answers when called | live 65 · failed 0 · guarded 6 · platform 0 · skipped 17 |
| **ok** | Holographic deck | CPU rasteriser, 30 fps budget |
| **ok** | 86 tools, every one answers | tools/capability.py executes them |
| **ok** | ARC Lite offline brain | ~1 ms, no model |
| **ok** | Voice: OS TTS, manly neural voice, language mirroring | test_voice.py |
| **ok** | Machine-acting layer (windows, keys, clicking, OCR) | UIA + OCR |
| **ok** | Media studio: video, audio, image | ffmpeg/Pillow, free |
| **ok** | search_inside: the words inside your documents | test_inside.py |
| **ok** | pc_health: 'why is this PC slow' | two measured samples |
| **ok** | explain: read an error and quote it first | 24 error families |
| **ok** | Backup with SHA-256 proof | test_backup.py |
| **ok** | Autostart: one HKCU entry, read back | test_backup.py |
| **ok** | Coach / mentor / analyst modes | test_coach.py |
| **ok** | Medicine rails + crisis numbers | information, never a prescription |
| **ok** | Markets: quotes, arithmetic, position size | test_market.py |
| **ok** | Business, travel, craft, data mining | test_business.py |
| **ok** | Reminders, focus sessions, briefing | test_reminders.py |
| **ok** | Learned voice macros | test_macros.py |
| **ok** | MCP tool servers | 7 reference servers |
| **ok** | 86-package free/open-source catalogue | test_packages.py |
| **ok** | Docs match the code (counts, files, tests) | test_docs.py rule 1 + 2 |
| **ok** | Packaging: spec, installer, uninstaller | tools/packaging.py |
| **ok** | Moves to another laptop without carrying its voice lock | pack/unpack, keys stripped, voiceid excluded, merge keeps both |
| **ok** | Speaks in the imported voice, per language | IndicF5 for Tamil/Indic, XTTS for English, piper/SAPI fallback |
| **ok** | Only the enrolled voice may command it | per-machine profiles, threshold from self-similarity |
| **ok** | Real photographs, with credit (not a drawing) | Wikimedia Commons, free licences, no key, no GPU |
| **ok** | The Vault: projects, notes, progress, export | copy-not-move, verified export, 0.45 ms saves |
| **ok** | One-click installer (payload + script) | packaging/build_all.bat + fetch_runtime.py + arcdesk.iss |
| **FAIL** | 41/60 tests pass | test_agent_guards, test_agent_loop, test_app_lifecycle, test_art |
| **FAIL** | BYE JARVIS closes the application | es a recognised phrase produces (tools/voice_roundtrip.py header).
RESULT: FAILURES ABOVE
 |
| **FAIL** | the app boots (run.py --shadow) | on a real screen — this sandbox has no display, Qt runs offscreen.
RESULT: FAILURES ABOVE
 |
| **FAIL** | Application opens by voice | test_wake_pipeline.py did not pass |
| **FAIL** | 'Bye JARVIS' CLOSES the app | test_voice_close.py did not pass |
| **FAIL** | 'Bye JARVIS' three choices (exit/quit/hide) | test_voice_close.py did not pass |
| **FAIL** | Magic mode (fullscreen ARC + wallpaper, restored on exit) | test_magic.py did not pass |
| **FAIL** | Windows untouched (no shell/taskbar/explorer changes) | test_magic.py did not pass |
| **FAIL** | Gravity charms (floating sprites, click-through) | test_magic.py did not pass |
| **FAIL** | Real local LLM over HTTP | test_agent_loop.py did not pass |
| **FAIL** | Streaming + barge-in | test_stream.py did not pass |
| **FAIL** | Reading any file (pdf/docx/xlsx/pptx/csv/image/audio) | test_reading.py did not pass |
| **FAIL** | Editing files without overwriting the original | test_reading.py did not pass |
| **FAIL** | Playback of your own music/video, external disks | test_playback.py did not pass |
| **FAIL** | First-run wizard (five decisions) | test_firstrun.py did not pass |
| **FAIL** | Money: free enforced in code | test_free_guard.py did not pass |
| **FAIL** | The real entry point boots | test_firstrun.py did not pass |
| **FAIL** | Asks icon-vs-voice at setup, and again in Settings | test_openmode.py did not pass |
| **FAIL** | Voice enrolment inside the app | test_voicelock_gui.py did not pass |
| **FAIL** | Every Settings control actually changes something | test_audit.py did not pass |
| **FAIL** | All 88 tools are callable, described, schema-valid | test_audit.py did not pass |
| **FAIL** | Three languages, and clips graded before cloning | test_clean.py did not pass |
| need | ArcDesk.exe launches after PyInstaller | needs a Windows build machine |
| need | Vosk hears your actual voice | needs a microphone + the speech model |
| need | Windows 11 UI behaves as documented | needs a Windows desktop |
| need | Inno Setup produces Setup.exe | needs Inno Setup 6 on Windows |

**27 present · 32 proven · 22 failed · 4 cannot prove here.**
