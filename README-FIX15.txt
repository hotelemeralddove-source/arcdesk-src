ARC DESK — FIX PACK 15
"Cinematic cues, and a companion that talks like one"
================================================================

WHAT THIS ADDS
--------------
1. Seven short sound cues, GENERATED inside the app on first launch.
   No download, no licence, no audio library. 0.15 s to render all seven,
   ~90 KB total, in %APPDATA%\ArcDesk\sfx\.

     wake         1.45 s   "hey jarvis" was heard
     magic_begin  1.50 s   the window opens / magic mode begins
     magic_end    1.20 s   magic mode closes, the app hides or quits
     task_start   0.28 s   a task starts being processed
     task_done    0.90 s   the task finished
     task_failed  0.55 s   the task failed
     click        0.12 s   a charm button was pressed

   Playback is on a daemon thread with a per-cue min_gap, so four tools
   finishing in the same second chime once. A missing sound card is
   swallowed silently — it never raises into the app.

2. A companion voice — spoken in YOUR cloned reply voice, through the
   same engine as every other answer:

     "hey jarvis"            -> Hi commander.
     bye / app closing       -> Thank you, commander.
     "open notepad"          -> Opening Notepad, commander.
     "close chrome"          -> Closing Chrome, commander.
     "what is my cpu usage"  -> Checking the machine, commander.
     "set a timer for 10 m"  -> Setting that up, commander.
     "take a screenshot"     -> Capturing the screen, commander.
     "search for flights"    -> Searching, commander.
     anything else, work     -> On it, commander.
     a question to think on  -> Let me think about that, commander.
     still running after 1.2 s -> Still on it, commander. (then rotates)

   Completion is a chime, not narration (announce_done defaults off).

3. The goodbye is spoken BEFORE the close:
   QTimer.singleShot(900 + 55 x characters) ms. Roughly 1.9 s for
   "Thank you, commander." — the sentence finishes, then it hides/quits.

4. Settings -> Sound: cue on/off, volume slider + "Hear one", companion
   voice on/off, "It calls you:" honourific field, "Preview the lines".
   Nothing about the sound is a config-file secret.

FILES IN THIS PACK
------------------
  arcdesk/sfx.py                    NEW  cues, render, cache, play
  arcdesk/companion_voice.py        NEW  every line, honourific, acks
  arcdesk/config.py                      sfx + companion defaults
  arcdesk/widgets/window.py              say/greet/_say_ack/farewell_and_close
  arcdesk/widgets/settings.py            the Sound block
  arcdesk/ai/agent.py                    remembers the last request, for the ack
  tests/test_cinematic.py           NEW  8 sections
  tests/test_app_lifecycle.py            waits for the goodbye instead of racing it
  COMMANDS.md                            new section 0c: cues + lines
  CAPABILITIES.md   MACHI.md   README.md   REEVAL.md   CROSSCHECK.md
  SETUP_GITHUB.md   WHATS_INCLUDED.md     test counts 68 -> 69
  README-FIX15.txt                       this file

HOW TO APPLY
------------
Copy these files over your existing folder, keeping the paths. Nothing else
to install — the cues are generated on first launch.

VERIFIED
--------
  python tests/run_all.py    ->  69/69 passed in 79.2s · "everything passes."
  tests/test_cinematic.py    ->  ALL PASS, three runs in a row (no flakes)
  Cue render                 ->  7 cues in 0.15 s, total ~90 KB, mono 16-bit 22 kHz
  Offscreen smoke            ->  greeting, ack and farewell all spoken, and the
                                 farewell completes before the window closes

Three real defects were found and fixed while verifying this pack:
  * a progress line picked at random made the suite flaky -> it now rotates
    (same variety, first one always "Still on it")
  * opening the app WITHOUT the wake word (the magic button, or any road that is not
    "hey jarvis") had no opening beat and no greeting at all — it opened in silence.
    Both doors now run one guarded opener (_cinematic_open), so there is a beat and a
    "Hi commander" either way, and never twice if the two land together.
  * a test raced the goodbye with a fixed 0.3 s wait -> it now waits for the
    effect, which is what "closes after it speaks" actually means
