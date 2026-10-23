"""The rules of a conversation — kept as pure functions so they can be tested.

Three decisions the voice daemon has to make between turns, and all three are
easier to get wrong than they look:

  * **when the conversation is over** — you said "thanks", not another command;
  * **when you are interrupting** — sustained speech, not one loud frame from a
    chair creak or the tail of ARC's own sentence in the speakers;
  * **when a follow-up is real work** — so a cough does not become an empty turn.

Everything here is a pure function of (text, levels). No microphone, no Qt, no
sockets, so `tests/test_talk.py` can hammer the edges without any hardware.
"""
from __future__ import annotations

import re

# Deliberately complete phrases, not keywords: "no" alone is a valid answer to a
# question ("do you want it louder?" → "no"), so only the full shrug counts.
ENDINGS = {
    "thanks", "thank you", "thanks da", "thank you da", "thats all", "that is all",
    "that's all", "nothing else", "no thanks", "ok thanks", "okay thanks",
    "good bye", "goodbye", "bye", "ok bye", "cool thanks", "nice thanks",
    "nandri", "romba nandri", "seri", "seri podhum", "podhum", "chalo",
    "theek hai", "bas", "bas karo",
}

# "no" and "stop" are handled elsewhere: stop silences speech, no is an answer.


def _norm(text: str) -> str:
    return re.sub(r"[^\w\s']", " ", (text or "").lower()).strip()


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", _norm(text))


def ends_conversation(text: str) -> bool:
    """True when the user is closing the chat rather than asking something."""
    said = _squash(text)
    if not said:
        return False
    if said in ENDINGS:
        return True
    # "thanks, that's all" / "ok thanks da, nothing else"
    words = said.split()
    if len(words) <= 5 and any(said == e for e in ENDINGS):
        return True
    if len(words) <= 5 and said.rstrip("s") in {e.rstrip("s") for e in ENDINGS}:
        return True
    return False


def wants_followup(text: str, min_chars: int = 2) -> bool:
    """Is this worth treating as a command? A cough transcribes as nothing."""
    said = _norm(text)
    return len(said.replace(" ", "")) >= min_chars


def is_barge(levels: list[int], threshold: int = 700, frames: int = 4) -> bool:
    """Sustained loud speech = you started talking over ARC.

    `frames` consecutive frames above `threshold`. A single spike (a click, a
    door) fails; the tail of ARC's own voice through speakers does not usually
    hold four frames at speaking volume, and when it does, we err on the side of
    listening — being interrupted is better than being ignored.

    Levels are int16 RMS values, so ~700 is quiet speech and ~3000 is close-mic talk.
    """
    run = 0
    for level in levels:
        if level >= threshold:
            run += 1
            if run >= frames:
                return True
        else:
            run = 0
    return False


def barge_threshold(noise_floor: int) -> int:
    """Adapt to the room: loud fans need a higher bar than a silent bedroom."""
    floor = max(0, int(noise_floor))
    return max(500, int(floor * 3 + 400))
