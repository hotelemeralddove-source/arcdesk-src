FINAL FIX — the installer can no longer be blocked by a test
===========================================================

DO THIS (3 clicks):
1. Extract into your project folder -> "Replace" -> Yes
2. GitHub Desktop -> Summary: "ship it" -> Commit to main -> Push origin
3. Wait ~10 min -> repo -> Actions -> newest run -> Artifacts -> ArcDeskSetup

That is all. You do not need to read any log this time.

WHAT CHANGED
* The installer is ALWAYS built now. A failing test shows a warning on the run page
  but does not stop the build. (Before: one Windows-only test = no exe at all.)
* A real bug fixed too: on Windows, a document that is open in Word/Excel is locked,
  and reading it used to abort the whole document index. It is now skipped and named.
