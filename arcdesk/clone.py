"""Your voice, saying ARC's words — the honest version.

The ask: *"naan enna language-la pesunalum, reply antha language-la varanum, aana
voice naan upload panna clip-oda voice-la irukanum."* That is **zero-shot voice
cloning**: give a model 5-20 seconds of a voice plus its transcript, and it speaks
new text in that voice.

What it takes, and what this file refuses to pretend:

| | engine | clones? | languages | licence | runs on |
|---|---|---|---|---|---|
| Indic language reply | **IndicF5** (AI4Bharat, 330M) | yes | 11 Indic: ta, hi, kn, te, ml, bn, gu, mr, pa, or, as | code MIT; weights: clone only voices you have permission for | GPU strongly recommended |
| English / other | **XTTS-v2** (Coqui) | yes | 17, incl. hi — **no Tamil** | CPML: personal / non-commercial only | CPU possible, slow |
| no clone engine | **Piper** | no | many, incl. ta | GPL-3.0 fork | CPU, fast |
| nothing installed | **Windows SAPI** | no | whatever Windows has | OS | instant |

Three consequences, stated plainly instead of discovered later:

1. **Tamil + your cloned voice needs IndicF5.** XTTS cannot pronounce Tamil at all,
   and Chatterbox (MIT) does not tokenise Tamil either. If IndicF5 is not installed,
   ARC says so and speaks Tamil in a Piper voice — a different voice, but real Tamil.
   It does **not** silently play your English voice mispronouncing Tamil.
2. **Cloning is a model, not a setting.** Nothing here downloads 1-2 GB behind your
   back. `install_clone.bat` does it once, visibly, and `plan()` always reports what
   is actually on the machine.
3. **A 12-second clip with music in it clones the music too.** `import_reference()`
   trims to the best continuous speech, normalises loudness, resamples to 24 kHz
   mono, and keeps the transcript on disk, because IndicF5 needs it.

Nothing in this module is allowed to raise into the speech thread: `speak()` returns
False when it cannot do the job, and the caller falls back down the chain.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import wave
from pathlib import Path

# Languages each engine can actually pronounce. Kept as data, not prose, so the
# routing can be tested. Codes are the ones `lang.py` already produces.
INDIC_LANGS = ("ta", "hi", "kn", "te", "ml", "bn", "gu", "mr", "pa", "or", "as")
XTTS_LANGS = ("en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs",
              "ar", "zh", "ja", "hu", "ko", "hi")
PIPER_LANGS = INDIC_LANGS + XTTS_LANGS          # voices exist for most of these

# THE CONTRACT: three languages are promised and tested. Everything else in
# INDIC_LANGS / XTTS_LANGS is a bonus that may work, and is never claimed.
PROMISED = {
    "ta": ("indicf5", "Tamil"),
    "hi": ("indicf5", "Hindi"),
    "en": ("xtts", "English"),
}
PROMISED_CODES = tuple(PROMISED)

SAMPLE_RATE = 24000          # what both cloning engines want to hear
MIN_SECONDS = 4.0            # shorter than this and the clone sounds like a stranger
IDEAL_SECONDS = 12.0


# --------------------------------------------------------------------- paths
def voice_dir() -> Path:
    from . import config
    d = config.data_dir() / "voice"
    d.mkdir(parents=True, exist_ok=True)
    return d


def reference() -> Path | None:
    """The clip ARC clones, if one has been imported."""
    p = voice_dir() / "reference.wav"
    return p if p.exists() else None


def transcript() -> str:
    t = voice_dir() / "reference.txt"
    return t.read_text(encoding="utf-8").strip() if t.exists() else ""


def _set_transcript(text: str) -> None:
    (voice_dir() / "reference.txt").write_text((text or "").strip() + "\n", encoding="utf-8")


# ------------------------------------------------------------------- engines
def _model_dir(name: str) -> Path | None:
    """Where a Hugging Face model would already be cached, without downloading."""
    env = os.getenv("ARCDESK_MODELS", "").strip()
    roots = [Path(env)] if env else []
    home = Path.home()
    roots += [home / ".cache" / "huggingface" / "hub", home / ".cache" / "arcdesk" / "models"]
    for root in roots:
        if not root.exists():
            continue
        for cand in root.glob(f"*{name}*"):
            if cand.is_dir():
                return cand
    return None


_CACHE: dict = {"at": 0.0, "data": None}
CACHE_SECONDS = 30.0


def refresh() -> None:
    """Forget the cached probe — call after installing or removing an engine."""
    _CACHE["at"] = 0.0
    _CACHE["data"] = None


def engines() -> dict[str, dict]:
    """What is installed right now. Never imports a heavy module just to check.

    Cached for `CACHE_SECONDS` on purpose: `route()` runs on every spoken sentence,
    and importing `transformers` to answer "is it there?" takes seconds. Probing a
    model cache is cheap; importing the model is not.
    """
    import time as _time
    now = _time.monotonic()
    if _CACHE["data"] is not None and (now - _CACHE["at"]) < CACHE_SECONDS:
        return _CACHE["data"]
    out: dict[str, dict] = {}
    for key, module, model in (("indicf5", "transformers", "IndicF5"),
                               ("xtts", "TTS", "xtts_v2")):
        model_path = _model_dir(model)
        out[key] = {
            "available": bool(model_path) and _importable(module),
            "module": module,
            "model": str(model_path) if model_path else "",
            "why": "",
        }
        if not out[key]["available"]:
            missing = []
            if not model_path:
                missing.append(f"the {model} weights")
            if not _importable(module):
                missing.append(f"the '{module}' package")
            out[key]["why"] = "missing " + " and ".join(missing)
    piper_ok = _piper_ready()
    out["piper"] = {"available": piper_ok, "module": "piper", "model": "",
                    "why": "" if piper_ok else "piper is not installed"}
    _CACHE["data"] = out
    _CACHE["at"] = now
    return out


def _importable(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def _piper_ready() -> bool:
    try:
        from .ai.voice import piper_available
        return bool(piper_available())
    except Exception:
        return False


def route(lang: str) -> str:
    """Which engine should speak `lang`. Pure function — this is the testable bit."""
    code = (lang or "en").split("-")[0].lower()
    have = engines()
    if code == "ta" or code in INDIC_LANGS:
        if have["indicf5"]["available"] and reference():
            return "indicf5"
        return "piper" if have["piper"]["available"] else "sapi"
    if have["xtts"]["available"] and reference() and code in XTTS_LANGS:
        return "xtts"
    if have["piper"]["available"] and code in PIPER_LANGS:
        return "piper"
    return "sapi"


def plan() -> dict:
    """Everything a person needs to know, without guessing."""
    have = engines()
    ref = reference()
    t = transcript()
    return {
        "engines": have,
        "reference": str(ref) if ref else "",
        "reference_seconds": round(_seconds(ref), 2) if ref else 0.0,
        "transcript": bool(t),
        "promised": {code: name for code, (_e, name) in PROMISED.items()},
        "order": ["indicf5 for Tamil and Hindi (the promise)", "xtts for English",
                  "the other 9 Indic + 16 XTTS languages are a bonus, not a claim",
                  "piper (same language, no cloning)", "Windows SAPI"],
        "limits": [
            "XTTS-v2 cannot speak Tamil; IndicF5 can.",
            "IndicF5 wants a GPU. On CPU it is slow enough to be noticeable.",
            "A clone copies the recording: music or hiss in the clip becomes music or hiss.",
            "XTTS-v2 weights are CPML — personal / non-commercial use.",
        ],
    }


# ---------------------------------------------------------------- reference
def _ffmpeg() -> str:
    from . import paths
    return paths.which("ffmpeg")


def _seconds(path: Path) -> float:
    try:
        with wave.open(str(path)) as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except Exception:
        return 0.0


def _read_mono(path: Path) -> tuple[list[float], int]:
    import array
    with wave.open(str(path)) as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError("expected 16-bit mono PCM")
        sr = w.getframerate()
        data = array.array("h")
        data.frombytes(w.readframes(w.getnframes()))
    scale = 1.0 / 32768.0
    return [s * scale for s in data], sr


def _resample(samples: list[float], sr: int, target: int = SAMPLE_RATE) -> list[float]:
    """Linear resample. Good enough for a voice reference; the engines do their own
    conversion anyway — this just keeps the file's promise (24 kHz)."""
    if sr == target or not samples:
        return samples
    ratio = target / float(sr)
    out_len = int(len(samples) * ratio)
    out = [0.0] * out_len
    for i in range(out_len):
        pos = i / ratio
        j = int(pos)
        frac = pos - j
        a = samples[j] if j < len(samples) else samples[-1]
        b = samples[j + 1] if j + 1 < len(samples) else a
        out[i] = a + (b - a) * frac
    return out


def _canonical(path: Path) -> bool:
    """Already 16-bit mono? Then a WAV can be read directly instead of via ffmpeg."""
    try:
        with wave.open(str(path)) as w:
            return w.getnchannels() == 1 and w.getsampwidth() == 2
    except Exception:
        return False


def _write_mono(samples: list[float], sr: int, path: Path) -> None:
    import array
    clipped = [max(-1.0, min(1.0, s)) for s in samples]
    data = array.array("h", (int(s * 32767) for s in clipped))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def speech_segments(samples: list[float], sr: int,
                    min_length: float = 0.25) -> list[tuple[int, int]]:
    """Where the talking is: energy VAD, 30 ms frames, 350 ms of silence ends a run.

    Returns [(start_sample, end_sample), ...] in order, each at least `min_length`
    long. Silence between them is real silence, not a pause inside a sentence.
    """
    win = max(1, int(0.03 * sr))
    frames = [samples[i:i + win] for i in range(0, max(0, len(samples) - win), win)]
    if not frames:
        return []
    energy = [sum(s * s for s in f) / len(f) for f in frames]
    peak = max(energy) or 1e-9
    floor = peak * 0.002                     # ~ -27 dB under the loudest frame
    voiced = [e > floor for e in energy]

    runs: list[tuple[int, int]] = []
    i = 0
    while i < len(voiced):
        if not voiced[i]:
            i += 1
            continue
        start = i
        gap = 0
        while i < len(voiced):
            if voiced[i]:
                gap = 0
            else:
                gap += 1
                if gap * 0.03 > 0.35:
                    break
            i += 1
        end = i - gap
        if (end - start) * 0.03 >= min_length:
            runs.append((start * win, end * win))
    return runs


def best_window(samples: list[float], sr: int,
                target: float = IDEAL_SECONDS) -> tuple[int, int]:
    """The longest continuous stretch of speech, capped at `target` seconds."""
    segs = speech_segments(samples, sr)
    if not segs:
        return 0, min(len(samples), int(target * sr))
    start, end = max(segs, key=lambda ab: ab[1] - ab[0])
    limit = int(target * sr)
    if end - start > limit:
        # keep the middle of the run: the edges are usually a half-spoken word
        pad = (end - start - limit) // 2
        start += pad
        end = start + limit
    return max(0, start), min(len(samples), end)


def stitch(samples: list[float], sr: int, segs: list[tuple[int, int]],
           target: float = 12.0, gap: float = 0.12) -> tuple[list[float], int]:
    """Join pieces of speech, in order, until `target` seconds — for an edited clip.

    An 12-second reel with cuts and music gaps has no single usable 10-second run;
    refusing it would be useless. Splicing with short fades is honest and works, as
    long as the caller says so — a clone from spliced audio keeps the edits' tone.
    """
    out: list[float] = []
    used = 0
    need = int(target * sr)
    pad = [0.0] * int(gap * sr)
    fade = max(1, int(0.008 * sr))
    for start, end in segs:
        if len(out) >= need:
            break
        piece = list(samples[start:min(end, start + (need - len(out)))])
        for i in range(min(fade, len(piece))):
            k = i / fade
            piece[i] *= k
            piece[-1 - i] *= k
        out.extend(piece)
        out.extend(pad)
        used += 1
    return out[:need], used


def _normalise(samples: list[float], target_rms: float = 0.10,
               peak_ceiling: float = 0.79) -> list[float]:
    if not samples:
        return samples
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5 or 1e-9
    gain = target_rms / rms
    peak = max(abs(s) for s in samples) or 1e-9
    gain = min(gain, peak_ceiling / peak)
    return [s * gain for s in samples]


def analyse(path: str | Path) -> dict:
    """How good is this clip as a clone reference? Numbers, not opinions.

    `background_db` is the quietest tenth of the frames, `speech_db` the loudest
    tenth; `snr_db` is the difference. A music bed raises the background, so a low
    SNR means the clone will carry that bed with it.
    """
    import numpy as np
    p = Path(str(path)).expanduser()
    read_from = p
    if p.suffix.lower() != ".wav":
        # analyse() reads PCM, not codecs: convert first through the bundled ffmpeg
        exe = _ffmpeg()
        if not exe:
            return {"path": str(p), "seconds": 0.0, "speech_db": -120.0,
                    "background_db": -120.0, "snr_db": 0.0, "clip_pct": 0.0,
                    "grade": "unknown", "advice": "ffmpeg is needed to read that format"}
        tmp = Path(str(p) + ".analyse.wav")
        done = subprocess.run([exe, "-y", "-hide_banner", "-loglevel", "error",
                               "-i", str(p), "-vn", "-ac", "1",
                               "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(tmp)],
                              capture_output=True, text=True, timeout=600)
        if done.returncode != 0 or not tmp.exists():
            return {"path": str(p), "seconds": 0.0, "speech_db": -120.0,
                    "background_db": -120.0, "snr_db": 0.0, "clip_pct": 0.0,
                    "grade": "unknown",
                    "advice": f"could not decode it: {(done.stderr or '')[-120:]}"}
        read_from = tmp
    out = {"path": str(p), "seconds": 0.0, "speech_db": -120.0, "background_db": -120.0,
           "snr_db": 0.0, "clip_pct": 0.0, "grade": "poor", "advice": ""}
    try:
        with wave.open(str(read_from)) as w:
            sr = w.getframerate()
            raw = w.readframes(w.getnframes())
        if not raw:
            out["advice"] = "the file has no audio in it"
            out["grade"] = "unknown"
            return out
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception as exc:                                    # noqa: BLE001
        out["advice"] = f"could not read it: {type(exc).__name__}: {exc}"
        return out
    finally:
        if read_from != p:
            try:
                read_from.unlink()
            except OSError:
                pass
    if not len(x):
        out["advice"] = "the file is empty"
        return out
    out["seconds"] = round(len(x) / sr, 2)
    out["clip_pct"] = round(float(np.mean(np.abs(x) > 0.98)) * 100, 3)
    win = max(1, int(0.03 * sr))
    frames = [x[i:i + win] for i in range(0, max(1, len(x) - win), win)]
    rms = np.array([float(np.sqrt(np.mean(f * f))) + 1e-9 for f in frames])
    db = 20 * np.log10(rms)
    out["background_db"] = round(float(np.percentile(db, 10)), 1)
    out["speech_db"] = round(float(np.percentile(db, 90)), 1)
    out["snr_db"] = round(out["speech_db"] - out["background_db"], 1)
    # Reported, not used to excuse a bad score: a heavily noisy clip also has no
    # quiet frames, and calling that "good" because there was nowhere quiet to look
    # would be exactly the kind of flattery this project refuses.
    out["quiet_ratio"] = round(float(np.mean(db < (out["speech_db"] - 15))), 3)

    secs, snr, clip = out["seconds"], out["snr_db"], out["clip_pct"]
    advice = []
    if secs < 6:
        advice.append(f"only {secs:g} s — add ~{max(0, 10 - secs):.0f} s more for a clone "
                      f"that keeps your rhythm, not just your tone")
    elif secs < 8:
        advice.append(f"{secs:g} s is workable; 10-12 s is noticeably better")
    if snr < 18:
        advice.append(f"background is only {snr:g} dB below your voice — run "
                      f"tools/clean_voice.py, or record in a quieter room")
    if clip > 0.5:
        advice.append(f"{clip:g}% of samples are at full scale (clipped) — turn the "
                      f"mic gain down and record again")
    if out["quiet_ratio"] < 0.03 and snr >= 25:
        advice.append("there is no pause in this clip, so the noise floor reading is a "
                      "best guess — a clip with natural pauses grades more reliably")
    clean = snr >= 25 and clip <= 0.5
    if clean and 8 <= secs <= 20:
        out["grade"] = "good"
    elif clean and secs < 8:
        out["grade"] = "short"          # clean voice, just not enough of it
    elif snr >= 15 and secs >= 4 and clip <= 2:
        out["grade"] = "workable"
    else:
        out["grade"] = "poor"
    out["advice"] = "; ".join(advice) or "good reference"
    return out


def quality(path: str | Path | None = None) -> dict:
    """Grade the current reference (or the file given)."""
    target = path or reference()
    if not target:
        return {"grade": "none", "advice": "no reference imported yet"}
    return analyse(target)


def import_reference(src: str, transcript_text: str = "") -> dict:
    """Turn any audio/video file into the 24 kHz mono clip the clone engines want.

    Returns {"ok", "path", "seconds", "source", "message"}. Never raises.
    """
    source = Path(str(src)).expanduser()
    if not source.exists():
        return {"ok": False, "message": f"no such file: {source}"}

    work = voice_dir()
    raw = work / "reference_raw.wav"
    try:
        if source.suffix.lower() == ".wav" and _canonical(source):
            shutil.copyfile(source, raw)
        else:
            exe = _ffmpeg()
            if not exe:
                return {"ok": False,
                        "message": "ffmpeg is needed to read that file — run install.bat "
                                   "or export the clip as WAV and try again"}
            done = subprocess.run(
                [exe, "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
                 "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(raw)],
                capture_output=True, text=True, timeout=300)
            if done.returncode != 0 or not raw.exists():
                return {"ok": False,
                        "message": f"ffmpeg could not read it: {(done.stderr or '')[-200:]}"}

        samples, sr = _read_mono(raw)
        if sr != SAMPLE_RATE:                 # the engines want 24 kHz; keep the promise
            samples = _resample(samples, sr, SAMPLE_RATE)
            sr = SAMPLE_RATE
        segs = speech_segments(samples, sr)
        longest = max((b - a for a, b in segs), default=0) / sr
        note = ""
        if longest >= MIN_SECONDS:
            start, end = best_window(samples, sr)
            picked = _normalise(samples[start:end])
        else:
            picked, used = stitch(samples, sr, segs, target=IDEAL_SECONDS)
            picked = _normalise(picked)
            if used > 1:
                note = (f" — stitched from {used} separate pieces of speech, because this "
                        f"clip has cuts in it. One continuous 10-12 s recording will clone "
                        f"noticeably better.")
        if len(picked) / sr < MIN_SECONDS:
            return {"ok": False,
                    "message": f"only {len(picked) / sr:.1f} s of speech found — I need at "
                               f"least {MIN_SECONDS:g} s, ideally {IDEAL_SECONDS:g} s of "
                               f"one person talking with no music"}
        out = work / "reference.wav"
        _write_mono(picked, sr, out)
        if transcript_text.strip():
            _set_transcript(transcript_text)
        speak_text = transcript()
        graded = analyse(out)
        return {"ok": True, "path": str(out), "seconds": round(len(picked) / sr, 2),
                "grade": graded["grade"], "snr_db": graded["snr_db"],
                "background_db": graded["background_db"],
                "advice": graded["advice"],
                "source": str(source),
                "transcript": speak_text,
                "message": (f"reference ready: {len(picked) / sr:.1f} s, {sr // 1000} kHz "
                            f"mono{note}"
                            + ("" if speak_text else " — add the words it says with "
                               "`--transcript`, IndicF5 needs them")
                            + f" [{graded['grade']}: {graded['advice']}]")}
    except Exception as exc:                                    # noqa: BLE001
        return {"ok": False, "message": f"{type(exc).__name__}: {exc}"}


# -------------------------------------------------------------------- speak
def speak(text: str, lang: str = "en", wav: str = "") -> bool:
    """Speak in the cloned voice. False = nothing happened, fall back."""
    if not (text or "").strip():
        return False
    ref = reference()
    engine = route(lang)
    try:
        if engine == "indicf5" and ref:
            return _indicf5(text, lang, ref, wav)
        if engine == "xtts" and ref:
            return _xtts(text, lang, ref, wav)
        return False            # piper / sapi are handled by voice.py itself
    except Exception:
        return False


def _indicf5(text: str, lang: str, ref: Path, wav: str) -> bool:
    try:
        import numpy as np
        from transformers import AutoModel
    except Exception:
        return False
    model_path = engines()["indicf5"]["model"]
    if not model_path:
        return False
    try:
        model = AutoModel.from_pretrained(model_path, trust_remote_code=True)
        audio = model(text, ref_audio_path=str(ref), ref_text=transcript() or None)
        if isinstance(audio, tuple):
            audio = audio[0]
        if wav:
            _save_int16(np.asarray(audio), wav)
            return True
        return _play_array(np.asarray(audio))
    except Exception:
        return False


def _xtts(text: str, lang: str, ref: Path, wav: str) -> bool:
    try:
        from TTS.api import TTS
    except Exception:
        return False
    model_path = engines()["xtts"]["model"]
    if not model_path:
        return False
    try:
        tts = TTS(model_path=model_path).to("cpu")
        tts.tts_to_file(text=text, speaker_wav=str(ref),
                        language=(lang or "en").split("-")[0],
                        file_path=wav or str(voice_dir() / "last_tts.wav"))
        return bool(wav) or _play_file(voice_dir() / "last_tts.wav")
    except Exception:
        return False


def _save_int16(arr, path: str) -> None:
    import numpy as np
    a = np.asarray(arr, dtype=np.float32)
    a = np.clip(a / (np.max(np.abs(a)) + 1e-9) * 0.9, -1, 1)
    import wave as _w
    with _w.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes((a * 32767).astype("<i2").tobytes())


def _play_array(arr) -> bool:
    tmp = voice_dir() / "last_tts.wav"
    _save_int16(arr, str(tmp))
    return _play_file(tmp)


def _play_file(path: Path) -> bool:
    """Play a WAV with no extra dependency where we can help it."""
    try:
        import sys
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(str(path), winsound.SND_FILENAME)
            return True
        if shutil.which("aplay"):
            subprocess.run(["aplay", "-q", str(path)], timeout=120)
            return True
        if shutil.which("afplay"):
            subprocess.run(["afplay", str(path)], timeout=120)
            return True
    except Exception:
        return False
    return False


def describe() -> str:
    """One line for the doctor / settings screen."""
    p = plan()
    ready = [k for k, v in p["engines"].items() if v["available"]]
    ref = f"{p['reference_seconds']:g} s reference" if p["reference"] else "no reference clip"
    return (f"voice clone: {', '.join(ready) or 'none installed'} · {ref} · "
            f"Tamil → {route('ta')}, English → {route('en')}")
