"""Who ARC is when it speaks — one name, one place.

The user's words: *"athu pesum pothu 'I am ARC' nu soluthu; 'I am JARVIS' nu sonna
semaya irukkum."* So the spoken identity is **JARVIS** by default, while the application
is still Arc Desk on the disk and in the title bar (that is what people installed).

Nothing here invents a name at runtime: the default lives in `config.DEFAULTS` under
`"ai" -> "name"`, so anybody can change it in Settings → Brain and it will be used
everywhere — the persona prompt, the first-run voice test, the Lite self-introduction and
the "who are you" answer. One function, no copies.
"""
from __future__ import annotations

DEFAULT_NAME = "JARVIS"


def name(cfg: dict | None = None) -> str:
    """The name ARC answers to and introduces itself with."""
    try:
        got = str((cfg or {}).get("ai", {}).get("name") or "").strip()
    except Exception:
        got = ""
    return got or DEFAULT_NAME


def prompt_line(cfg: dict | None = None) -> str:
    """The one sentence a model needs to get the name right.

    Small local models copy whatever they are told about themselves, so this is stated
    as identity, not as a preference: "you are JARVIS".
    """
    who = name(cfg)
    return (f"Your name is {who}. When you introduce yourself, say \"I am {who}\". "
            f"The application you live inside is called Arc Desk — that is the window, "
            f"not you.")


def intro(cfg: dict | None = None) -> str:
    """A spoken self-introduction that a person would actually want to hear."""
    return f"I am {name(cfg)}, and this is my voice on your machine."
