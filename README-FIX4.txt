FIX PACK 4 — make the install step say WHICH package fails
=========================================================

APPLY (2 clicks):
1. Extract into your project folder (the one with run.py) -> "Replace" -> Yes.
2. GitHub Desktop: Summary = "clearer install step" -> Commit to main -> Push origin.

WHY: run #3 stopped after 2m46s, before the tests even started. That points at the
"install python packages" step, but the old step installed everything in one command
and never said which package broke.

WHAT CHANGED in .github/workflows/build-windows.yml
* installs requirements.txt and requirements-voice.txt separately, and throws with the
  file name when one fails (the pip line above it names the package)
* uses --prefer-binary (avoids trying to compile from source on the runner)
* NEW STEP "prove the right packages are installed":
      import PySide6, psutil, PIL, numpy, pypdf, docx, openpyxl, pptx, mutagen
  If a package is missing, this step fails in 2 seconds with the name,
  instead of 12 tests failing later.
* prints `pip list` so a green run proves exactly what was installed
