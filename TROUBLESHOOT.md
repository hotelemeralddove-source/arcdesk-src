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
