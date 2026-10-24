# When it will not start

Every row below is a real dialog, with the exact cause and the exact clicks. If your
dialog is not here, run **`ArcDeskDiag.bat`** (double-click, nothing to install) and send
me `ArcDeskDiag.txt` — it answers the questions a screenshot cannot.

---

## The one you sent

> **AppInstallerPythonRedirector.exe — Application Error**
> The application was unable to start correctly (0xc0000142). Click OK to close.

**What the title means.** `AppInstallerPythonRedirector.exe` is not part of Arc Desk.
It is the **Microsoft Store's Python alias** — the stub Windows runs when something asks
for `python.exe` and the only Python is the Store package (or a leftover of it). Its
presence in the title is proof: *something on this PC launched Python, and that Python is
the Store alias.*

**What `0xc0000142` means.** `STATUS_DLL_INIT_FAILED` — a DLL refused to initialise. For
us there are exactly three ways to get it:

| # | Cause | How to tell | Fix |
|---|---|---|---|
| 1 | **The setup/app was built with the Store Python.** PyInstaller copies DLLs from a Store package folder with restricted ACLs; the frozen app cannot load them. The build "succeeds", the exe never opens. | `where python` prints a path containing **WindowsApps** | Turn the alias off, install Python from **python.org**, rebuild. `packaging\build_all.bat` now refuses to build with the Store alias |
| 2 | **The VC++ runtime is missing** on this PC (Qt needs `vcruntime140.dll`, `msvcp140.dll`). | `C:\Windows\System32\vcruntime140.dll` does not exist | Install **Microsoft Visual C++ Redistributable (x64)**, or use a build that ships the DLLs beside the exe (the spec now bundles them) |
| 3 | **The download is truncated or blocked.** | The `.exe` is much smaller than 53 MB, or `ArcDeskSetup.exe.zone.identifier` exists | Delete it, download again; or right-click the file → **Properties → Unblock → OK**. `ArcDeskDiag.bat` does this for you |

**The order I would try them, for you right now:**

1. **Use it today, no installer.** Right-click `ArcDesk-portable.zip` → **Extract All** →
   open the folder → double-click **`ArcDesk.exe`**. Nothing is installed, nothing is
   registered, and this needs no Python on your PC at all.
2. **Run **ArcDeskDiag.bat**.** It says in one page whether the file is blocked, whether
   your Python is the Store alias, and whether the runtime is there. Send me the report.
3. **Rebuild only if you want the installer.** With a python.org interpreter:
   `packaging\build_all.bat` — the new step 0 stops with a one-line fix if anything is
   wrong, instead of producing a 53 MB file that cannot open.

---

## "The shortcut is on the desktop but nothing happens"

That is the windowless bug from the other side: the app died in its first second, and a
program with no console has nothing to say about it.

Two ways to see it, in this order:

| Do this | Why |
|---|---|
| Double-click **`ArcDeskStart.bat`** | it keeps a black window open while the app starts, so the error stays on screen instead of vanishing |
| Double-click **`ArcDeskRepair.bat`** | it finds every copy on the PC, starts each one, waits 8 seconds, and tells you which one works. If one works it rebuilds your desktop shortcut to point at it. If none work it names the reason |

The three reasons, and how the repair file tells them apart:

| Cause | The check | Fix |
|---|---|---|
| Built with the **Microsoft Store Python** | `where python` shows a path containing `WindowsApps` | turn the alias off (Settings → Apps → App execution aliases), install Python from python.org, rebuild |
| The **VC++ runtime is missing** | `C:\Windows\System32\vcruntime140.dll` not found | install **Microsoft Visual C++ Redistributable (x64)** |
| The **folder is incomplete** — only `ArcDesk.exe` was copied, not `_internal` | no `_internal` folder beside the exe | copy the whole folder, or reinstall. A packaged app is the exe **plus** that folder |

### And the icon

The shortcut in your picture shows a **yellow-and-blue box** — that is PyInstaller's own
icon, not Arc Desk's. It means the build could not find `shots/arc_icon.ico`, so the exe
carried the fallback. It is cosmetic, but it is also a signal: the build machine was
missing something, and the same run is where the missing DLLs come from.

`tools/preflight_win.py` now **fails the build** when the icon is missing, and
`install_shortcut.bat` writes a shortcut with an explicit `IconLocation`,
`WorkingDirectory` and a target that actually runs — never a shortcut to a `.py` or `.pyw`,
because those get the Python icon and fail silently by design.

---

## Other dialogs, same treatment

| What you see | Cause | Fix |
|---|---|---|
| **"This app can't run on your PC"** | 32-bit build on 64-bit Windows, or the file is a half-download | Download again. `python tools\preflight_win.py` refuses a 32-bit interpreter |
| **"Windows protected your PC"** (blue box) | SmartScreen, because the exe is not code-signed | **More info → Run anyway**. Signing needs a paid certificate — this app ships unsigned on purpose rather than hiding that |
| **"MSVCP140.dll was not found"** | The VC++ runtime, exactly as row 2 above | Install the x64 redistributable, or use a build that bundles it |
| It opens and **closes instantly, no window** | A windowless crash. Before this fix there was no trace anywhere at all | `%APPDATA%\ArcDesk\logs\arcdesk.log` — the app now points its own stdout/stderr there and keeps the traceback |
| It runs but **"hey jarvis" does nothing** | The ears (microphone, wake word) or the 70 MB speech models are missing | **Settings → Voice → "Get the ears ready…"** — it ticks or crosses the four things and downloads what it can |
| It answers **in the system voice, not yours** | No clone engine installed | **Settings → Voice → "Get the reply-voice engine…"** (Tamil/Hindi: IndicF5, English: XTTS) |
| **Several black command prompts** appear while it works | Fixed: every child process is now spawned with `CREATE_NO_WINDOW` (`arcdesk/quiet.py`) | Make sure you are running a build from fix pack 16 or later |
| The **uninstaller asks about your vault** | On purpose. Your notes and files are yours | Answer **No** to keep them; they live in `%APPDATA%\ArcDesk\vault` |

---

## Two files worth knowing

```
%APPDATA%\ArcDesk\logs\arcdesk.log      everything the app would have printed
%APPDATA%\ArcDesk\settings.json         all settings; safe to copy to another PC
```

`python tools\move.py pack D:\carry.zip` puts your settings, vault and clone clip into
one file (keys stripped) if you are changing machines.

---

## For the person building it

```bat
python tools\preflight_win.py     :: judge the machine before PyInstaller does anything
packaging\build_all.bat           :: runs the same check as step 0, then builds
```

`preflight_win.py` fails the build — with the fix printed — when:

* `python` is the Store alias (exit 1, before PyInstaller is even called),
* the interpreter is 32-bit or older than 3.9,
* PySide6 or PyInstaller is missing,
* there is not enough disk for a ~1.2 GB build folder,
* the repo sits inside a OneDrive folder (OneDrive locks files mid-build),
* the path is longer than 110 characters (Windows gives up at 260).

It warns, but does not fail, when there is no venv, no Inno Setup (the app still builds;
only `ArcDeskSetup.exe` needs it) and no icon.

## The desktop icon is a yellow Python, not Arc Desk

That picture — a yellow snake over a white page on a blue floppy — is PyInstaller's
**default** icon. It means the `.exe` you are running was produced without
`icon=shots/arc_icon.ico`, i.e. not by `packaging/arcdesk.spec` (the old fallback build
did exactly this), or by a build where the icon file was not found.

How to tell in ten seconds: open the program folder and look for `ArcDeskVoice.exe` and
a folder called `_internal`. The fallback build has neither. Arc Desk's real build has
both, plus the sparkle icon.

Two things can look identical on screen, so check both:

1. **The exe is old** — reinstall from the newest green run's `ArcDesk-portable.zip`.
   Delete the old program folder *and* the old desktop shortcut first, so a stale
   picture cannot survive (see below).
2. **Windows is showing a cached icon** — Explorer remembers icons *per file path*.
   Copy the whole folder somewhere else and rename it (`ArcDesk2`); if the copy shows
   the sparkle icon, the exe was always fine and only the cache was wrong. To clear it
   without a copy: rename the shortcut, or run `ie4uinit.exe -show`.

The build now refuses to publish an exe whose icon is not Arc Desk's — the workflow
asks `python tools\preflight_win.py --icon-check dist\ArcDesk\ArcDesk.exe
shots\arc_icon.ico`, which compares the icon's bytes with the bytes inside the exe.

## It installs, but nothing happens (no window, no card, nothing)

This was a real bug, fixed in this build, and it is worth knowing what it was.

The app could be told to "start hidden" — stealth mode, no window, no card, only a tray
icon. Two things were wrong together:

1. that hidden start was the **default**, so a fresh install was already in stealth; and
2. `--shadow` (the flag the boot entry passes) was **written into settings.json**, so one
   boot with Windows left every later double-click starting a process that showed nothing.

Now: a double-click always shows the window (the Windows shortcuts pass `--show`), the
boot entry still passes `--shadow` and still starts silent, `--shadow` never becomes a
saved preference, and the app writes its decision to the log so a silence can be read:

    BOOT · the window is shown
    BOOT · handles: tray=yes, hotkeys=yes, stealth=off

Settings files from an older build that say `"enabled": true` without `user_choice` are
corrected once (the same migration pattern the charms use). If you *did* tick "start
hidden" in Settings, that is a real choice and it is kept.

If it is still silent after this version: run `ArcDeskDiag.bat` and send the report —
it now carries the last 60 log lines, `settings.json`'s key values, and the size of the
installed exe. A report with no log at all means the exe never reached its own start-up
code, which is a different fault (and a much more specific one to send back).
