"""Conversation mode, barge-in and memory — the three "it feels alive" rules.

None of these needs a microphone to test, because the decisions were written as
pure functions on purpose. The failures being locked out:

  * "thanks" being fed to the model as a new command;
  * "no" ending the conversation when the user just answered a question;
  * a single loud frame (chair, door, click) cutting ARC off mid-sentence;
  * ARC being unable to hear anything because the room is loud;
  * ARC learning that your name is "not" or that you use vim because you asked
    "do I use vim?".

Run:  python tests/test_talk.py
"""
from __future__ import annotations

import os
import sys
import tempfile

os.environ["ARCDESK_HOME"] = tempfile.mkdtemp(prefix="arcdesk-talk-")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arcdesk import profile  # noqa: E402
from arcdesk.wake import talk  # noqa: E402


def check(label: str, got, want) -> bool:
    good = got == want
    print(f"   {'OK  ' if good else 'FAIL'} {label:<48} {got!r}"
          + ("" if good else f"  (want {want!r})"))
    return good


def main() -> int:
    ok = True

    print("1) the chat ends when the user says it ends")
    for phrase in ("thanks", "Thanks da!", "that's all", "nothing else", "seri podhum",
                   "ok bye", "chalo", "theek hai", "nandri"):
        ok &= check(f"ends: {phrase}", talk.ends_conversation(phrase), True)
    for phrase in ("no", "no louder", "open chrome", "what time is it",
                   "thanks, open chrome", "ok"):
        ok &= check(f"continues: {phrase}", talk.ends_conversation(phrase), False)

    print("2) a cough is not a command")
    ok &= check("empty", talk.wants_followup(""), False)
    ok &= check("single letter", talk.wants_followup("a"), False)
    ok &= check("real words", talk.wants_followup("volume 20"), True)

    print("3) barge-in needs sustained speech, not one spike")
    ok &= check("one loud frame is ignored", talk.is_barge([100, 900, 100, 100]), False)
    ok &= check("four loud frames interrupt", talk.is_barge([900, 900, 900, 900]), True)
    ok &= check("quiet room never interrupts", talk.is_barge([80] * 12), False)
    ok &= check("speech after a pause still counts",
                talk.is_barge([80, 80, 900, 950, 1000, 1100]), True)
    ok &= check("threshold adapts up in a noisy room",
                talk.barge_threshold(300) > talk.barge_threshold(50), True)
    ok &= check("never below the speech floor", talk.barge_threshold(0) >= 500, True)

    print("4) memory learns facts, not grammar")
    ok &= check("name", profile.learn("my name is Arun").startswith("Remembered"), True)
    ok &= check("stored", profile.get("name"), "Arun")
    ok &= check("editor normalised", profile.learn("i use vscode"), "Remembered: your editor is VS Code.")
    ok &= check("asked, not stated", profile.learn("do I use vim?"), "")
    ok &= check("not a name", profile.learn("i am going home"), "")
    ok &= check("language", profile.learn("reply in tanglish"), "Remembered: your language is tanglish.")

    print("5) the profile reaches the prompt, briefly")
    summary = profile.summary()
    ok &= check("mentions the name", "Arun" in summary, True)
    ok &= check("stays small", len(summary) <= profile.LIMIT, True)
    ok &= check("one line", "\n" not in summary, True)

    print("6) the profile cannot smuggle anything executable")
    profile.set("name", "$(rm -rf ~)")
    ok &= check("stored as text", profile.get("name").startswith("$(rm"), True)
    ok &= check("and it is only text", profile.summary().count(";") >= 1, True)
    ok &= check("unknown key refused", profile.set("sudo", "yes").startswith("ERROR"), True)

    print("7) clearing works and is honest")
    ok &= check("clear", profile.reset().startswith("Profile cleared"), True)
    ok &= check("empty afterwards", profile.summary(), "")
    ok &= check("forget unknown is honest", profile.forget("city").startswith("I had nothing"), True)

    print()
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
