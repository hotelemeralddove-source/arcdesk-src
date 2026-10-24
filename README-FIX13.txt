FIX PACK 13 — a brain in the box, the name JARVIS, and the step you can watch
================================================================================
APPLY (2 clicks):
1. Extract over your project folder -> Replace -> Yes
2. GitHub Desktop -> Summary = "brain + jarvis + steps" -> Commit -> Push
   -> ~10 min -> Actions -> Artifacts -> ArcDesk -> ArcDeskSetup.exe

1. "NO LOCAL MODEL DETECTED"  ->  fixed with a BUTTON
   Setup card, step 3, and Settings -> Local AI now have "Add a brain...".
   It downloads a small model and runs it on your laptop:
       Qwen2.5 1.5B    1066 MB   can use the tools (opens apps, reads the system)
       Qwen2.5 0.5B     469 MB   chat only (it says so, so you are not misled)
   No account, no key, no separate Ollama install. It listens on 127.0.0.1:8010
   (your own machine only) and the app points itself at it when it is ready.
   Stop works. Lite keeps answering the whole time, so nothing ever dead-ends.

2. IT SAYS "I AM JARVIS" NOW
   The spoken name is JARVIS everywhere: the persona, the "who are you" answer, the
   first-run voice test. You can change it in Settings -> Local AI -> "It calls itself:".
   (The window is still called Arc Desk - that is the app, not the assistant.)

3. THE TASK PROCESS, STEP BY STEP
   Under the live line there is now a strip that fills in as it works:
       v thinking - the model is reading it 1.9 s   .   v tool: open_app 0.3 s   .   > tool: system_report
   Each step appears when it STARTS and turns into a tick with its own time when it
   finishes. So you can see which part is slow, not just that something is slow.

4. ESC
   Esc is now a real application-wide shortcut, so it fires even while your cursor is
   in the chat box (that was the case where it did nothing):
       dialog -> speech -> the running task -> console -> hide the window
   Press it once more on a hidden window and the app QUITS.
   Ctrl+Alt+H hides the window without touching the task, if you want to keep it going.

5. DESIGN CROSS-CHECK (rendered here, not guessed)
   Dashboard: clock, CPU/RAM gauges, shortcuts, and a new status card that says
       BRAIN . JARVIS . Lite (offline, instant)
       EARS  . not ready (...)
       VOICE . the system voice - no reply voice added yet
   Console: live line + seconds + STOP + the step strip + transcript.
   Footer: real frame cost (30 FPS . 4.1 ms/frame), so "slow" has a number.

INSTALL ORDER AFTER THIS UPDATE
   1. Settings -> Local AI -> Add a brain... -> Install and start (1066 MB, once)
   2. Settings -> Voice -> Get the ears ready... (70 MB, the wake word)
   3. Say "hey jarvis"
