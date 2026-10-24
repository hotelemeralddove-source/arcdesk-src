ARC DESK - FIX PACK 26
"The icon was there all along. Windows was refusing to draw it."
==============================================================================

YOUR REPORT
-----------
    "install pannadhu ku appuram icon sparkle ah illa python ah irukku"

So the exe had our icon (step 4b proves that byte-for-byte) and Explorer still showed
PyInstaller's python. That is not a cache problem. That is the .ico itself.

THE CAUSE, FOUND BY LOOKING AT THE FILES
----------------------------------------
I pulled the frames out of shots/arc_icon.ico and printed each one:

    BEFORE                             AFTER
    16x16   32bpp  PNG                 16x16   32bpp  BMP/DIB
    24x24   32bpp  PNG                 24x24   32bpp  BMP/DIB
    32x32   32bpp  PNG                 32x32   32bpp  BMP/DIB
    48x48   32bpp  PNG                 48x48   32bpp  BMP/DIB
    64x64   32bpp  PNG                 64x64   32bpp  BMP/DIB
    128x128 32bpp  PNG                 128x128 32bpp  BMP/DIB
    256x256 32bpp  PNG                 256x256 32bpp  PNG   (correct, keep)

Pillow writes every frame as a PNG blob. Windows renders the 256x256 PNG frame fine, so
the icon "works" in Preview and in large views — but the sizes a desktop shortcut actually
asks for are 16, 32 and 48, and there Explorer gives up and falls back to the *file type's*
icon: the python. That is exactly the picture you sent, twice.

THE FIX
-------
tools/make_icon.py now writes the icon itself (write_ico()):

  * 16/24/32/48/64/128  -> BMP/DIB frames: 40-byte BITMAPINFOHEADER, 32-bit BGRA rows
                          bottom-up, plus the 1-bit AND mask Windows still expects;
  * 256                 -> PNG (the one size where PNG is the normal choice);
  * and it is regenerated from shots/arc_icon.png, so the artwork is unchanged.

Regenerating changed the file from 63 KB (7 PNG frames) to 134 KB (6 DIB + 1 PNG) — that
size jump is the fix, not waste: uncompressed DIB frames are what Explorer can read.

PROOF
-----
  * decoded the new 48x48 frame back to a picture and looked at it: the reactor sparkle,
    drawn correctly (arcdesk-icon-48.png, if you want to compare with your screen).
  * tests/test_windows_build.py now asserts the frame layout:
        the icon has all seven sizes Windows asks for ....... [16, 24, 32, 48, 64, 128, 256]
        every size below 256 is a BMP frame ................. [BMP x6]
        256 is a PNG frame, like every icon tool produces ... [PNG]
    So a future `make_icon.py` run cannot quietly go back to PNG-only frames.
  * tools/preflight_win.py --icon-check still reads all 7 images out of the new file, so
    step 4b keeps working byte-for-byte.

WHAT TO DO (after this is pushed and run #18 is green)
------------------------------------------------------
1. Download the new artifact, unzip, and look at ArcDesk.exe's own icon in the folder.
   It should be the sparkle BEFORE you install anything. If the folder icon is sparkle,
   the rest will follow.
2. ReinstallClean.bat, then install. The new shortcut is drawn from the new frames.
3. If a python icon survives even then, it is the old shortcut or the old cache: delete
   the desktop shortcut, right-click the new ArcDesk.exe > Send to > Desktop (create
   shortcut). That copy is drawn from the exe you are looking at, so it cannot be cached
   from an older build.

GATES
-----
  python tests/run_all.py          72/72 passed in 108.3 s
  python tests/test_windows_build.py   frame layout asserted, ALL PASS
  python tools/gen_tools_doc.py --check   88 tools, 0 mismatch
  python tools/make_icon.py        regenerated PNG + ICO
