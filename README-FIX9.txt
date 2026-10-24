FIX PACK 9 — the neural engine, installed from inside the app
=============================================================
(Use this one. If you also have fix8, that is fine — this contains it too.)

APPLY (2 clicks):
1. Extract over your project folder -> Replace -> Yes
2. GitHub Desktop -> Summary = "engine in the app" -> Commit to main -> Push origin
   -> ~10 min -> Actions -> Artifacts -> ArcDesk -> ArcDeskSetup.exe

WHAT IS NEW
  Settings -> Voice -> "Get the reply-voice engine…"

   IndicF5   Tamil, Hindi   1.5 GB
   XTTS-v2   English        1.9 GB

  Press Install -> the lines scroll as it downloads -> it says ready, or it says
  exactly why not. Stop works, and a stopped install never says "installed".

WHY A MODEL IS NEEDED
  A clone is a model, not a setting. Without it you get the system voice, and the app
  says so instead of pretending.

THE INSTALLED .EXE CAN DO IT TOO
  The .exe cannot swallow a 2 GB model, so the app makes a private folder of its own
  (ArcDesk\engine_env), puts the engine there, and speaks through it. One button from
  your side. It borrows the Python already on the computer; if there is none, the
  dialog says so in one sentence and points at python.org.

SPEED, SAID PLAINLY
  Cloning on a CPU takes a few seconds per sentence. On a GPU it is instant. Until the
  engine is ready, ARC answers in the free voice and tells you that is what it is doing.

PERMISSION, once: only use a voice you have the right to use.
