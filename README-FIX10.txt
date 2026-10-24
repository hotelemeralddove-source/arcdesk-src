FIX PACK 10 — the setup card that would not let go, and a silent "hey jarvis"
=============================================================================
APPLY (2 clicks):
1. Extract over your project folder -> Replace -> Yes
2. GitHub Desktop -> Summary = "first run fix" -> Commit to main -> Push origin
   -> ~10 min -> Actions -> Artifacts -> ArcDesk -> double-click ArcDeskSetup.exe

WHAT WAS WRONG (your three complaints, one by one)

1. "the setup card comes and nothing else opens"
   The card was taller than your screen, so its buttons (Done / Just use Lite) were
   drawn BELOW the bottom edge. It looked like the app stopped there. Now the lists
   scroll inside the card and the buttons are always on screen. Enter also works.
   And closing it with the X finally SAVES your answer - before, it saved nothing, which
   is why the same card came back every time you double-clicked.

2. "close it, double-click again, same thing; voice gets no response"
   ArcDesk starts in stealth (no window until "hey jarvis"), and after the card was
   answered it stayed invisible - so it looked like nothing opened. Now the window
   appears once, right after you answer the card. Later launches are silent again.

3. "floating icons appear on the desktop by default"
   They did, because that was the default. Now they are OFF. Settings -> Look turns
   them back on any time, and once you choose, the app never changes it again.

WHY "HEY JARVIS" SAID NOTHING
   Four things are needed: microphone library, wake engine, the 40 MB speech model,
   the 30 MB speaker model. The card had only mentioned one of them in small grey text.
   Now: Settings -> Voice -> "Get the ears ready (mic + wake word)..." shows all four
   with a tick or a cross, and one button downloads what is missing (70 MB), with a
   Stop button and an honest re-check afterwards. The next installer also really
   bundles the wake engine (the build now installs it one package at a time and prints
   which ones made it in).

ONE THING YOU STILL DO AFTER INSTALLING
   Settings -> Voice -> "Get the ears ready..." -> press the button, wait for 70 MB.
   Then say "hey jarvis".
