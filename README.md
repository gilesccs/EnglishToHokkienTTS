# HokkienTTS

A **100% local, offline** pipeline that turns **typed English** into spoken **Singapore
Hokkien** — eventually in your own cloned voice, behind a chat interface.

Everything runs on your own GPU. No APIs, no cloud, no telemetry.

Setup gotchas: [`SETUP_NOTES.md`](SETUP_NOTES.md)

---

## 🚀 Quick start (demo runbook)

**1. Confirm the models exist** (Ollama auto-starts on boot):
```
ollama list          # should show:  qwen2.5:3b   and   taigi
```

**2. Start the chat app** — pick whichever is easier:

| Windows (PowerShell / double-click) | Git Bash |
|-------------------------------------|----------|
| Double-click **`run.bat`**, or run `.\run.bat` | `./run.sh` |

It loads + warms up the models (~20–30s), then shows `Running on local URL`.

**3. Open it:** http://127.0.0.1:7860

**4. Demo it** — type a phrase, press Enter (leave **"My voice"** ticked). Phrasebook lines
(e.g. "have you eaten") are instant + always correct.

**5. Stop it:** double-click **`stop.bat`** (or `.\stop.bat`, or `./stop.sh`).

**Good to know for a live demo:**
- The **first message is slow** (one-time warm-up). Send one throwaway message *before* the
  audience is watching so the rest feel snappy.
- **Phrasebook phrases are instant and guaranteed correct** — use those for the key moments.
  Free-typed sentences take ~16–20s and quality can vary (see [Quality](#quality--evaluation)).
- It's **100% local** — you can pull the network cable and it still works.
- If audio doesn't auto-play, click the ▶ on the player (browser autoplay policies).

---

## Architecture

```
 English text                "Have you eaten yet?"
        │
        ▼
 ┌──────────────────┐
 │ Qwen 2.5 (Ollama)│   English → Mandarin            你吃過飯沒有？
 └──────────────────┘
        │
        ▼
 ┌──────────────────┐
 │ Taigi-Llama-2    │   Mandarin → Hokkien Hàn-jī     你食飽未？
 │ (Ollama)         │
 └──────────────────┘
        │
        ▼
 ┌──────────────────────────────┐
 │ MERaLiON-OmniVoice-Hokkien   │   Hàn-jī → Singapore Hokkien audio,
 │  (+ optional voice clip)     │   optionally in YOUR cloned voice
 └──────────────────────────────┘
        │
        ▼
 🔊 .wav   (Singapore Hokkien, 24 kHz)
```

Two halves: **translate** (text → Hokkien characters) then **speak** (characters → audio).
The translation half never touches audio; the speech model never translates — it only
pronounces the characters it's handed.

### Roadmap

```
✅ Translate:  English → Hokkien Hàn-jī            (Qwen → Taigi, working)
✅ Speak:      Hokkien Hàn-jī → Sg Hokkien audio   (MERaLiON OmniVoice, working)
✅ Connect:    type English → hear Singapore Hokkien (english_to_hokkien.py)
✅ Your voice: record ~15s clip → output in your own voice (OmniVoice voice cloning)
✅ Chat UI:    local web app — type English, hear Hokkien in your voice (chat_app.py)
```

---

## Why English → Mandarin → Hokkien (not English → Hokkien directly)

Hokkien is a **low-resource** language: there's little English↔Hokkien training data, so a
direct jump is weak. But there's a lot of Mandarin↔Hokkien data, and Qwen is excellent at
English→Mandarin. So we route **through Mandarin** — each model does its strongest direction.

Translation quality from the Taigi-Llama paper ([arXiv 2403.12024](https://arxiv.org/abs/2403.12024)),
measured in **BLEU** (0 = broken, 10–19 = rough gist, 30–40 = good/fluent):

| Direction | BLEU | Feel |
|-----------|------|------|
| English → Hokkien (direct) | **12.8** | gist only, awkward (~40% right) |
| Mandarin → Hokkien | **32.6** | good, fine for everyday speech (~63% right) |

Routing through Mandarin roughly **2.5×** the quality. The cost is one extra model in the
chain — cheap, since both translation models are small and run locally in Ollama.

---

## The speech model: MERaLiON-OmniVoice

[`MERaLiON/MERaLiON-OmniVoice-Hokkien-TTS`](https://huggingface.co/MERaLiON/MERaLiON-OmniVoice-Hokkien-TTS)
— a Singapore-built TTS that speaks **Singapore Hokkien** (incl. local slang and Malay/English
loanwords) from Chinese characters.

**It replaces two earlier planned components at once:**

| Old plan | Now |
|----------|-----|
| Coqui-VITS-SuiSiann (Taiwanese TTS) + a separate goruut→IPA stage | **OmniVoice** maps Hàn-jī → audio internally |
| OpenVoice v2 (separate voice-morph model) | **OmniVoice** has built-in voice cloning (3–8 s reference clip) |

Because OmniVoice handles characters→sound internally, the old IPA-dump / polyphony-fix
machinery (needed for Coqui) is **gone**. The trade-off: we lose that per-character IPA
visibility, so the native-speaker spot-check (below) matters more.

> The original Coqui pipeline (`phase1_tts.py`, `models/suisiann/`, `hokkien_speech_env/`) is
> kept in the repo but **superseded**. It produced Taiwanese Hokkien; we switched after
> confirming OmniVoice sounds clearly better for Singapore speech.

---

## Hardware & CUDA considerations

Target machine: **AMD Ryzen 7 7700 · 32 GB RAM · NVIDIA RTX 4070 Ti (12 GB VRAM)**.

- **GPU is required for usable speed.** PyTorch must be the **CUDA build**, not the default
  CPU build — installed from the CUDA wheel index (`--index-url .../whl/cu124`, for CUDA 12.4).
  Verify with `torch.cuda.is_available() == True`.
- **fp16 (half precision):** the model loads with `dtype=torch.float16` and
  `device_map="cuda:0"`, which halves VRAM use and speeds inference, at no audible quality cost
  here.
- **Stages run sequentially** (translate → speak), but keeping them all resident at once does
  **not** fit in 12 GB — this turned out to be the central engineering problem (see
  [Engineering notes](#engineering-notes-making-it-usable-on-a-12-gb-gpu) below). The chat app
  keeps OmniVoice warm and frees the translation models before each speech step.
- **Two Python environments on purpose:** OmniVoice needs `transformers` 5.x; the old Coqui
  stack pins `transformers <5`. They can't share one venv, so OmniVoice lives in its own
  `omnivoice_env\`. The translation models are reached over HTTP (Ollama), so they're
  environment-independent.

## Engineering notes: making it usable on a 12 GB GPU

This was the hard part, and the measurements tell a clear story. The challenge: **three AI
models, one 12 GB graphics card, and they don't all fit at once.**

### The constraint

Rough VRAM footprint of each model when loaded:

| Model | Job | VRAM |
|-------|-----|------|
| OmniVoice (+ audio tokenizer) | speech | ~4–5 GB resident, **and it needs free headroom to generate** |
| Taigi-Llama-2 7B (Q4) | Mandarin→Hokkien | ~4.7 GB |
| Qwen 2.5 7B (Q4) | English→Mandarin | ~5 GB |
| Qwen 2.5 3B (Q4) | English→Mandarin | ~2 GB |

All three together ≈ **13–14 GB > 12 GB**. So something always has to give.

### The core discovery: VRAM "thrashing"

We added per-stage timing (the single most useful debugging move) and found the speech step
was wildly inconsistent:

| OmniVoice voice-clone generation | Time |
|----------------------------------|------|
| GPU has free room | **~1 s** |
| GPU overcommitted (models crammed past 12 GB) | **17–66 s** |

Same operation, up to **60× slower.** When a GPU is pushed past 100%, the framework spends its
time shuffling memory in and out instead of computing — like a desk so cluttered you spend all
day moving papers to find space to write. **The bottleneck was never the "thinking" — it was
running out of memory.**

A second finding pinned it down: **default voice = 1 s, voice-cloned = 53 s** under the same
pressure. Voice cloning adds the reference clip's audio tokens to every generation, making a
much longer (memory-hungry) sequence — so cloning is what tips an already-full GPU over the
edge. (A shorter reference clip would lighten this; ours is 15 s for quality.)

### Experiment log (what we tried, what happened)

| Attempt | Result |
|---------|--------|
| **Keep all models "warm" in VRAM** (`keep_alive`) — the obvious speed trick | ❌ Backfired. Pinning the translation models filled the card → OmniVoice starved → speech **thrashed** to 17–66 s. |
| **Qwen 7B for best translation** | ❌ Too big. Overcommitted VRAM *harder* → **76 s** per reply. Correct text, unusable speed. |
| **Qwen 3B to free ~3 GB** | ⚠️ Fast, fits — but 3B inconsistently emits **Simplified** characters and drops words, which **breaks Taigi** (trained on Traditional) → garbage Hokkien. |
| **`num_ctx=1024`** (shrink each model's reserved context from 4096) | ✅ Frees ~1–2 GB. Inputs are one short sentence, so the big reservation was pure waste. |
| **OpenCC `s2tw`** (Simplified→Traditional converter) | ✅ Deterministic lookup table (no AI, no quality loss) that fixes 3B's Simplified output before Taigi sees it. Recovers the quality 3B lost. |
| **Free VRAM *before* speaking** (`keep_alive=0` + wait for unload) | ✅ The fix that works: unload the translation models, then OmniVoice has room → speech back to **~1.5 s**. |
| **`temperature=0`** on translation | ✅ Makes output **deterministic** — same input → same output. (At default temperature the same sentence produced 4 different Hokkien answers; sometimes great, sometimes junk — a demo can't gamble.) |
| **Phrasebook** for core phrases | ✅ Hard-codes known-good Hokkien for key demo lines → always correct *and* instant (skips translation entirely). |

### Where the time goes now

With the working setup (Qwen 3B + OpenCC, free-VRAM-before-speech, temp 0):

```
translate (Qwen + Taigi):  ~13 s   ← now the bottleneck (models RELOAD each message)
speak (OmniVoice):         ~1.5 s
phrasebook phrase:         instant  (skips translation)
------------------------------------
total:                     ~16–20 s per sentence, STABLE
```

### The fundamental trade-off (the one-line takeaway for the demo)

> On a 12 GB GPU you can have **fast translation** (keep the translators in memory) **or**
> **fast speech** (keep that memory free for voice-cloning) — **but not both at once.** We
> chose to free memory for speech and accept that translation reloads each message. The honest
> fix for "both" is more VRAM (a 16–24 GB card), or a lighter/shorter voice-clip.

### Other settings worth knowing

- **CUDA build of PyTorch** (cu124) is required — the default install is CPU-only and far too
  slow. Verify with `torch.cuda.is_available()`.
- **fp16 (half precision)** halves VRAM and speeds inference at no audible cost here.
- **`num_step`** (OmniVoice's diffusion steps) is *not* worth tuning — speech is ~1.5 s when it
  has memory; the headroom is what matters, not the step count.

---

## How to run

Ollama must be running (it auto-starts after install) with both translation models available
(`qwen2.5:3b` and the custom `taigi` model — see [`SETUP_NOTES.md`](SETUP_NOTES.md)).

### The chat app (main way to use it)

```bash
# from the project root (Git Bash):
./run.sh        # starts the local web app, prints the URL when ready
./stop.sh       # shuts it down
```

Then open **http://127.0.0.1:7860**, type English, hear Singapore Hokkien in your voice.
Local only — no public link. First message warms up the models; later ones are faster.

### Record your voice (for the cloned-voice option)

```bash
omnivoice_env/Scripts/python.exe record_voice.py   # records ~15 s to my_voice.wav
```

### One-off scripts (no UI)

| Script | Does |
|--------|------|
| `english_to_hokkien_myvoice.py "…"` | Full chain → Hokkien audio in your cloned voice |
| `english_to_hokkien.py "…"` | Full chain → Hokkien audio (default voice) |
| `omnivoice_tts.py "你好！食飽未？"` | Speech stage only (Hàn-jī → audio), for isolating TTS issues |
| `batch_translate.py` | Translate a list of sentences (text only) to pick demo-safe ones |

### Curating demo phrases

Edit [`phrasebook.py`](phrasebook.py): any English line you put there is spoken with your exact,
known-good Hokkien — always correct and instant (skips the translation gamble). Ideal for a demo.

---

## Quality & evaluation

Hokkien output is **not guaranteed correct** — both the translation and the pronunciation can
slip. We check quality deliberately rather than assuming.

**Now (v1): native-speaker spot-check.** Have a Hokkien speaker listen to a batch of outputs
and flag wrong/unnatural ones. This is the gold standard for accuracy and naturalness, and it
matters more now that OmniVoice hides the internal pronunciation (no IPA dump to inspect).

**Known limitations to listen for:**
- **~1 in 3 sentences** may carry a translation slip; **casual chat & slang are rougher** than
  formal speech. (Real example: *"Wah this chicken rice damn nice sia"* came back as 雞肉 —
  "chicken meat", losing "rice" and the slang. The gist survives; the flavour doesn't always.)
- Each extra hop (English→Mandarin→Hokkien) can compound small errors.

**Parked future eval upgrades** (add when native checks become a bottleneck):
- **Back-translation:** Hokkien → English/Mandarin and compare to the original; mismatches flag
  likely errors. Cheap, offline, no Hokkien speaker needed.
- **Tâi-lô (romanized) output:** also emit a readable/soundable romanization to cross-check.
- **Dictionary lookup:** verify key word choices in the MOE Taiwanese dictionary / iTaigi
  (catches Mandarin-in-disguise, e.g. 吃 vs 食).
- **Golden test set:** ~20–30 fixed sentences with known-good Hokkien; re-run after each change
  to catch regressions.

---

## Confidentiality

- **Zero cloud trailing:** no APIs, external requests, or telemetry. Models run locally.
- **To verify:** run the full pipeline with network adapters disconnected (after models are
  downloaded once).
