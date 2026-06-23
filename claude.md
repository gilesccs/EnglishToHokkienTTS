# Local Confidential English-to-Hokkien Translator (with Voice Morphing)

## 🎯 Project Goal

Build a **100% local, offline, and confidential** language pipeline that takes spoken or
written English input and outputs accurate spoken Hokkien using **your own cloned voice
profile**.

> **Scope — v1 is text input only.** Spoken-English input (a speech-to-text front end such as
> Whisper) is **deferred**. Start with typed English → Hokkien audio; add microphone/STT later
> as a front stage that produces the same English text the pipeline already expects.

---

## 🏗️ System Architecture Pipeline

```text
[English Input]
       │
       ▼
[Ollama: Qwen 2.5]         ─────────▶  Step 1 of 2 — translates English → Mandarin (Hàn-zì)
       │                                (Qwen's strong, high-resource direction)
       ▼
[Taigi-Llama-2-Translator] ─────────▶  Step 2 of 2 — translates Mandarin → Hokkien Hàn-jī
       │                                (the specialist's strongest direction)
       ▼
[Coqui-VITS-SuiSiann]      ─────────▶  PRONOUNCES Hàn-jī → native Hokkien audio (.wav)
       │                                (does NOT translate — reads aloud only)
       ▼
[OpenVoice v2]             ─────────▶  Morphs the native speaker's voice to match
                                        your own voice profile
```

> **Why two translation steps (the "2-prong" approach):** direct English→Hokkien is weak
> (BLEU ≈ 13), but Mandarin→Hokkien is solid (BLEU ≈ 33). Routing through Mandarin lets each
> model do what it's best at and roughly **doubles** translation quality. See Phase 2.

> **Key fact:** Coqui-VITS only *pronounces* the characters it's given — it cannot fix word
> choice. All translation must be finished **before** audio. Feeding it Mandarin characters
> yields "Mandarin words in a Hokkien accent," not real Hokkien.

---

## 🛠️ System Specs & Hardware Considerations

| Component | Spec | Role |
|-----------|------|------|
| **CPU** | AMD Ryzen 7 7700 (8-core / 16-thread) | Orchestration, file I/O, fallback processing |
| **RAM** | 32 GB | Keeps text and speech frameworks resident simultaneously |
| **GPU** | NVIDIA RTX 4070 Ti (12 GB VRAM) | Primary inference engine |

**VRAM allocation strategy**

The pipeline stages run **sequentially** (translate → speak → voice-morph), so they do **not**
all need to be in VRAM at once. 12 GB is comfortable. Approx. footprints (quantized GGUF):

- Qwen 2.5 7B (Ollama, quantized): **~5 GB**
- Taigi-Llama-2-Translator 7B (GGUF Q4): **~5 GB** (13B Q4 ≈ 9 GB also fits)
- Coqui-VITS-SuiSiann + OpenVoice v2: a few GB

Prefer **load → infer → unload per stage** over keeping everything resident; only force
co-residency if you later need live, low-latency turnaround.

---

## 📅 Execution Strategy (Phased Approach)

### 📊 Phase 1 — Validate Native Hokkien TTS Output

**Objective:** Verify that the open-source dialect model accurately handles Hokkien
vocabulary, pronunciation, and tone sandhi *before* injecting a personal voice fingerprint.

**1. Isolated environment setup**

```bash
python3 -m venv hokkien_speech_env
source hokkien_speech_env/bin/activate

# Install the localized fork for the Hokkien speech architecture
pip install coqui-tts-pygoruut
```

**2. Pull model weights locally**

```bash
wget https://huggingface.co/neurlang/coqui-vits-suisiann-minnan-hokkien/resolve/main/best_model.pth -O ./best_model.pth
wget https://huggingface.co/neurlang/coqui-vits-suisiann-minnan-hokkien/resolve/main/config.json -O ./config.json
```

**3. Execution & verification test**

```bash
tts --text "你好！食飽未？" \
    --model_path ./best_model.pth \
    --config_path ./config.json \
    --out_path ./test_native_hokkien.wav
```

**Success criteria:** Listen to `test_native_hokkien.wav`. Confirm the pronunciation
matches accurate Taiwanese / Southeast Asian Minnan vernacular and does **not** fall back
to a Mandarin accent.

#### ℹ️ Verified input format (from the model's `config.json` + goruut dicts)

- The model is **phoneme-based** (`use_phonemes: true`); its alphabet is **IPA** with tone
  marks (`˥ ˦ ˧ ˨ ˩`). Phonemizer: `pygoruut:v0.6.3`, language `MinnanHokkien2`.
- goruut's dictionary maps **Hàn-jī → IPA directly**, so the pipeline takes **Chinese
  characters end-to-end — no Tâi-lô / POJ romanization stage is required.**

#### ⚠️ Polyphony is the real accuracy risk

Common *words* are **not** stored as units (`你好`, `食飽未` are absent), so goruut resolves
them per-character via a learned weights model. Many characters are polyphonic:

| Char | Candidate IPA readings |
|------|------------------------|
| `食` | `tsiaʔ˦` (eat) **/** `sit˦` |
| `未` | `bue˧˧` **/** `bi˧˧` |
| `好` | `ho˥˧` **/** `hõ˨˩` |

A wrong pick produces wrong-sounding Hokkien that is invisible from audio alone.

#### ✅ Add an IPA-dump diagnostic

Log the IPA string goruut produces for each sentence (call the phonemizer directly before
synthesis). This turns "sounds off" into "it read `食` as *sit*", making errors debuggable
instead of mysterious. Make this a standard part of Phase 1 verification.

#### 🔧 How to fix a mispronunciation (and where each fix lives)

> **Mental model:** the voice model is a singer who can only read sheet music. goruut writes
> the sheet music (the IPA) from the characters. If a word sounds wrong, the *sheet music* was
> wrong, not the singer — which is why the IPA-dump above is how you find the real problem.

> **Install note:** `pip install pygoruut` downloads a **single pre-built program** (e.g.
> `goruut.exe`) and the dictionary is **embedded inside it** — it is *not* a loose file you
> can open and edit. That rules out hand-editing the official dictionary unless you rebuild
> goruut from source (not worth it).

**Fix #1 — change the input text** *(easy; use this first)*
- Lives at the **start of the pipeline, in plain text you already control.**
- Phase 1: the `--text "..."` argument of the `tts` command.
- Phase 2: how you prompt Qwen, or a post-edit of Qwen's output before it reaches the TTS.
- If a character is misread, give goruut a different but still-correct way to write the word.

**Fix #2 — override a word's pronunciation** *(later; a few lines of Python, not a file edit)*
- pygoruut returns each word with its IPA separately, so you keep a small correction list,
  e.g. `食飽未 → tsiaʔ˦ pa˥˧ bue˧˧`, and substitute your IPA for known-bad words before
  synthesis. Build the correct IPA by reusing the per-character readings already in the dict.
- This is an **intermediate step** — adopt it once you're running the pipeline from a Python
  script rather than the one-line CLI.

**Editing the official dictionary** — skip; requires rebuilding goruut from source.

---

### 🎙️ Phase 2 — Translation (2-Prong: Qwen → Taigi-Llama)

**Objective:** Turn English into **authentic Hokkien Hàn-jī** before it reaches the speech
engine — using two models in series, each on its strongest task.

#### Why two steps (the evidence)

Translation quality from the Taigi-Llama paper ([arxiv 2403.12024](https://arxiv.org/abs/2403.12024)):

| Direction | BLEU | ≈ feel |
|-----------|------|--------|
| English → Hokkien (direct) | **12.8** | gist only, rough/awkward (~40% correct) |
| Mandarin → Hokkien | **32.6** | good, mostly fine for everyday speech (~63% correct) |

Direct English→Hokkien is weak; Mandarin→Hokkien is ~2.5× better. So we route **through
Mandarin** — Qwen does the easy English→Mandarin step, the specialist does its best
Mandarin→Hokkien step. (BLEU: 0 = broken, 10–19 = gist/rough, 30–40 = good/fluent.)

#### The pipeline

1. **Step 1 — Qwen (English → Mandarin):** run `ollama run qwen2.5:7b` and translate the
   English input into Traditional Mandarin Chinese. Qwen is excellent at this high-resource
   direction. Instruct it to return **only the translation**, no commentary.
2. **Step 2 — Taigi-Llama-2-Translator (Mandarin → Hokkien Hàn-jī):** feed the Mandarin into
   the specialist using its required prompt template:
   ```text
   [TRANS]
   {mandarin_sentence}
   [/TRANS]
   [HAN]
   ```
   `[HAN]` = output Hokkien in Chinese characters. (Other target codes: `EN`, `ZH`, `POJ`, `HL`.)
3. Pass the resulting Hàn-jī straight into the Phase 1 TTS script.

#### Model & setup notes

- **Model:** `Bohanlu/Taigi-Llama-2-Translator-7B` (13B also available for higher quality).
  LLaMA-2 based; translates ZH/EN ↔ Hokkien (HAN/POJ/HL).
- **Off-the-shelf — no training required.** You only run *inference* (use the finished
  model); download the **GGUF (quantized) build** and run via Ollama / LM Studio / llama.cpp.
- **Fits your GPU easily:** 7B Q4 ≈ 5 GB VRAM (13B Q4 ≈ 9 GB) on the 12 GB 4070 Ti.
- **License:** CC-BY-NC-SA 4.0 (non-commercial — fine for personal use).

#### Honest quality expectation

Benchmark sentences (news/formal) land in the "mostly OK" zone via Mandarin; **casual chat
and slang will be rougher**, and ~1 in 3 sentences may still have an error — keep the
pronunciation-inspection habit from Phase 1. Optional later upgrade: try Taigi-Llama's
**direct English→Hokkien** mode and compare; if it ever beats the 2-step on your inputs,
drop Qwen.

---

### 🎭 Phase 3 — Zero-Shot Voice Morphing (OpenVoice v2)

**Objective:** Layer your specific vocal timbre over the native pronunciation, while
keeping the native Hokkien accent and prosody intact.

> **Why OpenVoice v2, not RVC:** RVC is *not* zero-shot — it requires ~10+ min of target
> audio plus a training run and a retrieval index. OpenVoice v2 is true zero-shot tone-color
> cloning: it extracts your timbre from a few seconds of reference audio and transplants it
> onto the source while preserving the source's accent/prosody — exactly this use case.

1. Record a clean **15–20 second** clip of your own voice (`my_voice.wav`).
2. Set up a local OpenVoice v2 instance (tone-color extractor + converter).
3. Pass `test_native_hokkien.wav` as the **source audio** and your recording as the
   **target timbre**. OpenVoice transfers your tone color onto the native Hokkien audio —
   keeping the accent, changing who it sounds like.

*Upgrade path:* if timbre similarity isn't tight enough, train a dedicated RVC model on
~10+ min of your voice for higher fidelity.

---

## ✅ Quality Verification

**Now (v1):** native-speaker spot-check. Have a Hokkien speaker listen to a batch of outputs
and flag wrong/unnatural ones. This is the gold standard for accuracy and naturalness.

**Future TODO (parked — add when native checks become a bottleneck):**

- **Back-translation:** run Hokkien → English/Mandarin via Taigi (reverse) and compare to the
  original; mismatches flag likely errors. Cheap, offline, no Hokkien needed.
- **Tâi-lô output:** also emit romanized Hokkien (readable/soundable) to cross-check the audio
  and look up words.
- **Dictionary lookup:** verify key word choices in the MOE Taiwanese dictionary / iTaigi
  (catches Mandarin-in-disguise, e.g. 吃 vs 食).
- **Golden test set:** ~20–30 fixed sentences with known-good Hokkien; re-run after each
  change to catch regressions.
- *(IPA-dump for pronunciation is already covered in Phase 1.)*

---

## 🔒 Confidentiality Check

- **Zero cloud trailing:** no APIs, external network requests, or telemetry.
- **To verify:** run the full pipeline with network adapters disconnected.
