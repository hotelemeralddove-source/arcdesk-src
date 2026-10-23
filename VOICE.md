# Your voice, and only your voice

Two different things were asked for in the same breath, so they get two different
answers — and neither of them is pretending to be more than it is.

| Question | Answer | Where |
|---|---|---|
| "ARC should **speak in my voice**" | voice **cloning**: a local model copies your tone from a 10 s clip | `arcdesk/clone.py` |
| "ARC should reply in **whatever language I spoke**" | already done — the reply language follows your words | `arcdesk/lang.py` |
| "Only **my** voice should wake it on this laptop" | speaker verification: a fingerprint of your voice, enrolled here | `arcdesk/voiceid.py` |
| "On another laptop, a **different person**" | profiles live per machine, so laptop B starts empty | `arcdesk/voiceid.py` |

---

## 1. Speak in the uploaded voice

```bat
python tools\voice_setup.py import  "C:\Users\you\Downloads\clip.mp4"
python tools\voice_setup.py try     "vanakkam macha, ellam ready"
```

`import` does the unglamorous work that decides whether a clone sounds like you:

* converts any audio or video (ffmpeg, already bundled) to **24 kHz mono 16-bit**;
* finds the **actual speech** with an energy VAD — an edited clip with music gaps is
  **stitched** into one usable reference instead of being refused;
* normalises loudness and keeps every peak below 0 dBFS;
* refuses a clip that has less than 4 s of speech, and says how much it found;
* stores the reference **and its transcript** (`%APPDATA%\ArcDesk\voice\reference.txt`), because IndicF5 needs
  to know which words it is hearing.

Nothing is uploaded anywhere. The reference stays in `%APPDATA%\ArcDesk\voice\`.

### The scope: **Tamil, Hindi, English** — those three are the promise

```python
PROMISED = {"ta": ("indicf5", "Tamil"), "hi": ("indicf5", "Hindi"), "en": ("xtts", "English")}
```

Three languages, three tested routes, nothing vague. The other nine Indic languages
and the other sixteen XTTS languages usually work and are still in the table below as a
**bonus** — they are never claimed, because a language that half-works in a voice you
cannot understand is worse than a clear "not supported".

### Which engine speaks which language — and why

| Language you speak | Engine | Clones? | Reality |
|---|---|---|---|
| **Tamil, Hindi, Kannada, Telugu, Malayalam, Bengali, Gujarati, Marathi, Punjabi, Odia, Assamese** | **IndicF5** (AI4Bharat, 330 M) | yes | needs a GPU to be quick; on CPU it is slow but honest |
| English, Spanish, French, German, Italian, Portuguese, Polish, Turkish, Russian, Dutch, Czech, Arabic, Chinese, Japanese, Hungarian, Korean | **XTTS-v2** (Coqui) | yes | CPU is possible |
| anything, when no clone engine is installed | **Piper** | no | *real* language, *different* voice — and it says so |
| last resort | Windows SAPI | no | instant, robotic |

**The awkward truth:** **XTTS cannot speak Tamil.** Neither can Chatterbox, the other
MIT-licensed clone model. If IndicF5 is not installed, ARC will speak Tamil in a Piper
voice rather than have your cloned English voice mispronounce Tamil. That is a
deliberate choice: a wrong voice is better than a wrong language.

### Before you clone: is the clip good enough?

```bat
python tools\clean_voice.py "clip.mp3"
python tools\clean_voice.py "clip.mp3" --import --transcript "the words it says"
```

`clone.analyse()` grades a clip with numbers instead of opinions:

| grade | means | what to do |
|---|---|---|
| `good` | SNR ≥ 25 dB, 8–20 s, no clipping | clone it |
| `short` | clean voice, under 8 s | add a few seconds — this is the one your 4.5 s clips got |
| `workable` | SNR 15–25 dB or clipped a little | run `clean_voice.py` first |
| `poor` | noisy, clipped or unusable | record again, in a quieter room |

`clean_voice.py` runs highpass (kills 50 Hz mains hum and desk thumps), spectral denoise
(fan, hiss, air-con), edge trimming and loudness normalisation, then **measures the SNR
again** and prints before/after. Measured on a synthetic 50 Hz-hum clip: **SNR 12.2 →
20.6 dB, grade poor → workable**. On a music bed it cannot help — music and voice share
the spectrum — and it says so, pointing at `demucs` if it is installed.

### Licence, stated plainly

* **IndicF5** — code MIT; the model's own terms say: *clone only voices you have
  permission to use.* Your own voice, or a person who said yes. Not a film star.
* **XTTS-v2** — CPML: **personal / non-commercial only**. Fine for your own machine;
  it is not something you can ship inside a paid product.
* **Piper** — GPL-3.0 fork, commercially usable with the usual copyleft conditions.

Only clone a voice you have the right to clone. A cloned voice saying something the
person never said is the one genuinely harmful thing this feature can do.

---

## 2. Only your voice wakes it, on this computer

### When, and where — the short answer

**Do it once, right after installing, in the app: Settings → Voice → "Teach ARC my
voice…"**. Three takes of four seconds each, in a quiet room, alone. No terminal, no
files to find. The card shows a live level bar so a dead microphone is obvious in the
first second rather than after a silent failure, and it counts the takes for you.

Then tick **"Only my voice may command ARC on this computer"** and press Done. That is
the whole submission. To undo it, untick the same box — the lock is per machine, so a
second laptop enrols the person who uses *that* laptop, never a copy of your biometrics.

If the microphone is unavailable, the same card has **"Use a WAV file…"**. If the
speaker model is missing it says so and offers to download it (30 MB) instead of
pretending to be ready.

**Prove it actually works** rather than trusting the screen:

```bat
python tools\voice_setup.py selftest --against other.wav
```

That imports a reference, enrols three takes, then scores a take it has never seen (your
voice — must pass) and another person's recording (must fail). Measured here with the real
`campplus` model on real audio: same voice **0.70**, another voice **0.16**, threshold
**0.62**.

### The command-line version (same machinery, for scripting)

```bat
python tools\voice_setup.py lock-model
python tools\voice_setup.py lock-enroll me rec1.wav rec2.wav rec3.wav
python tools\voice_setup.py lock-test  rec4.wav
python tools\voice_setup.py selftest --against rec4.wav   :: import + enrol + prove
python tools\voice_setup.py lock-on
```

* **3 recordings, 3–8 seconds each**, same person, quiet room, normal speaking voice.
* The clips are reduced to a **fingerprint** (a unit vector). The audio is not kept.
* Enrolment measures how much your own clips agree and **raises its own threshold**
  from that: inconsistent clips make the lock stricter, never looser.
* Two people can be enrolled on one machine (you and your wife, say); the closest
  match wins and is named in the log.
* With **nobody** enrolled the lock stays **open** — a lock that shuts the owner out
  is a bug, not a feature.
* The daemon checks the **command audio** (not just the wake word), because that is
  when real work is about to happen:

```
VOICE · wake word detected
voice lock: me (0.81)
heard: open notepad
```

Rejected:

```
voice lock: rejected (score 0.41 < 0.62) — not acting on it
```

### What this is not

This is a **convenience filter, not a security control.** It keeps your family, the
television and a YouTube video from waking ARC. It does **not** stop a recording of
your voice on a phone — no system that runs on one microphone can. If it is off, is
broken, or has no model, the app says so and falls back to the plain wake word.

Turning it on without an engine is refused with the reason, and the app never claims
to be locked when it is not.

---

## 3. A second laptop

| What | How |
|---|---|
| **This laptop** stays yours | `%APPDATA%\ArcDesk\voiceid\profiles.json` holds your fingerprint |
| **Laptop B** is someone else's | it has its own (empty) folder → run `lock-enroll` there with *their* recordings |
| you *want* the same voice on both | there is no command for that on purpose; copy the profiles.json yourself if you really mean it |
| the cloned voice on both | copy `%APPDATA%\ArcDesk\voice\` — or just run `import` again on B |

---

## 4. What was actually run here

```
python tests\test_clone.py        ALL PASS   (routing, trimming, stitching, refusal, fallback)
python tests\test_voiceid.py      ALL PASS   (enrol, verify, thresholds, per-machine profiles)
python tools\voice_setup.py status           no clone engine installed — and it says so
python tools\voice_setup.py import <clip>     stitched 5.9 s · 24 kHz mono
```

The 1.5 GB models were **not** downloaded and could not be run in the sandbox that
built this. `status` reports `no — missing the IndicF5 weights and the 'transformers'
package` instead of claiming a cloned voice you would not hear.
