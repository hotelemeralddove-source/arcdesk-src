FIX PACK 8 — command voices AND reply voices (any voice, any clip)
=================================================================

APPLY (2 clicks):
1. Extract into your project folder (one with run.py) -> Replace -> Yes
2. GitHub Desktop -> Summary = "voice library" -> Commit to main -> Push origin
   -> ~10 min -> Actions -> Artifacts -> ArcDesk -> ArcDeskSetup.exe

THEN IN THE APP:  Settings -> Voice -> "Voices — who commands, which voice replies…"

  LIST 1  WHO MAY COMMAND IT
     Add a voice…  -> pick a recording of any person (you, amma, a friend)
     -> that voice is obeyed. Any number of people. Remove any of them.

  LIST 2  THE VOICE ARC ANSWERS IN
     Add a voice…  -> pick ANY recording (yours, or a different voice entirely)
     -> "Answer in this voice" -> every reply uses it
     -> "Hear it" speaks one line in that voice

  Two different voices can sit side by side. Switch with one click.

WHAT IS NEEDED FOR IT TO SOUND REAL
  A cloned voice needs a neural engine: run install_clone.bat once
     Tamil / Hindi -> IndicF5 (~1.5 GB)
     English       -> XTTS    (~1.9 GB)
  Until then ARC says "reply voice: the system voice" instead of pretending.

PERMISSION, said once: only use a voice you have the right to use — your own, or
someone who said yes.
