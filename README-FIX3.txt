FIX PACK 3 — the real cause of the red build
============================================

APPLY (2 clicks):
1. Extract into your project folder (the one with run.py) -> "Replace" -> Yes.
2. GitHub Desktop: Summary = "declare dependencies" -> Commit to main -> Push origin.

THE BIG ONE
-----------
The log said:  test_vision: No module named 'PIL'

requirements.txt only listed PySide6 and psutil. The app actually needs TEN packages:
Pillow, numpy, pypdf, python-docx, openpyxl, python-pptx, mutagen...
Your PC had them from an earlier install, so nothing looked wrong. GitHub's clean
machine did not. That is why 12 tests failed at once.

All ten are now declared in requirements.txt, so the runner installs them,
and the packaged .exe carries them too.

ALSO
----
* tests/run_all.py now prints the last 12 lines of EVERY failing test, and writes
  them to .failures/ — the run page shows them automatically. Next time a test
  fails we will see the reason, not just the name.
* a new check in test_audit.py fails if any import is undeclared, so this cannot
  come back.

WHAT TO EXPECT: run 4 should pass, or tell us exactly which lines failed.
