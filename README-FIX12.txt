FIX PACK 12 — the white letters, and the model that was already there
=====================================================================
APPLY (2 clicks):
1. Extract over your project folder -> Replace -> Yes
2. GitHub Desktop -> Summary = "dialog colours + model folder" -> Commit -> Push
   -> ~10 min -> Actions -> Artifacts -> ArcDesk -> ArcDeskSetup.exe

1. WHITE LETTERS ON WHITE — fixed
   The "Can ARC hear you?" and "voice engine" windows were built with Qt's default
   white theme, and the log box was drawing every line as if it were selected.
   Now both use the same dark colours as the rest of the app, and the log can no
   longer take the keyboard, so it cannot paint itself white.

2. THE BIG ONE — your own log said it
       [arc-voice] already present: ...\ArcDesk\vosk-model-small-en-us-0.15
       ...speech model not downloaded.
   Both lines were true. The download saves the model in one folder; the check was
   looking in two other folders. So "hey jarvis" could never work on your PC, no matter
   how many times you downloaded it. There is now ONE list of folders - the one the
   downloader writes to is on it - and a folder only counts when the model files are
   really inside it.

   After this fix you should see three ticks out of four:
       [v] microphone library
       [v] wake-word engine
       [v] speech model (40 MB)      <-- this one should now be ticked for you
       [ ] speaker model (voice lock) - optional, only needed for "only my voice"

3. If the speech model is STILL crossed after this update: press "Download what is
   missing" once. It will say "already present" and the tick will appear, because the
   check now looks where the file goes.
