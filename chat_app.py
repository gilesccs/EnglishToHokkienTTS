"""
HokkienTTS chat interface — type English, hear Singapore Hokkien (in your voice).

A local Gradio web app. The model loads ONCE at startup and stays warm, so after the
first message every reply is fast (no per-message reload).

  English --(Qwen)--> Mandarin --(Taigi)--> Hokkien Han-ji --(OmniVoice + your voice)--> audio

Run:
    set PYTHONUTF8=1
    omnivoice_env\\Scripts\\python.exe chat_app.py
Then open the http://127.0.0.1:7860 link it prints. Local only — no public sharing.
"""
import sys, io, os, re, json, time, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

from phrasebook import PHRASEBOOK


def phrasebook_lookup(english: str):
    """Return hard-coded Hokkien if this English is a known demo phrase, else None."""
    key = re.sub(r"[^a-z ]", "", english.lower()).strip()
    return PHRASEBOOK.get(key)

HERE = os.path.dirname(os.path.abspath(__file__))
REF_AUDIO = os.path.join(HERE, "my_voice.wav")
OLLAMA = "http://localhost:11434/api/generate"
GUIDANCE = 3.0
QWEN = "qwen2.5:3b"      # 3B's flaw (Simplified chars) is fixed with OpenCC below.
KEEP_ALIVE = 0           # unload translation models after each call. Voice cloning needs
                         # lots of free VRAM; if the translation models stay resident the
                         # cloned speech THRASHES (53s vs 1.5s). So we free them before speaking.
NUM_CTX = 1024           # small context = less VRAM reserved (sentences are tiny)

# MUST match what you read while recording (record_voice.py).
REF_TEXT = ("Hey, I just got back from the hawker centre near my place, and the food "
            "there was really good. I had some chicken rice and a cold drink, sat down, "
            "and relaxed for a bit. It's one of my favourite things to do on the weekend.")


def ollama(model_name: str, prompt: str) -> str:
    payload = {"model": model_name, "prompt": prompt, "stream": False,
               "keep_alive": KEEP_ALIVE,
               "options": {"num_ctx": NUM_CTX, "temperature": 0}}  # 0 = deterministic, same output every time
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["response"].strip()


def wait_unloaded(timeout=6.0):
    """Block until Ollama has unloaded its models, so OmniVoice's voice-cloning gets
    full VRAM (otherwise the cloned speech thrashes: 53s instead of ~1.5s)."""
    t = time.time()
    while time.time() - t < timeout:
        try:
            with urllib.request.urlopen("http://localhost:11434/api/ps") as r:
                if not json.loads(r.read().decode("utf-8")).get("models"):
                    return
        except Exception:
            pass
        time.sleep(0.2)


def qwen_prompt(english: str) -> str:
    return ("Translate the following English sentence into natural, complete Traditional "
            "Chinese (Mandarin). Keep the full meaning; do not drop words. "
            "Output ONLY the translation - no pinyin, no explanation, no quotes.\n\n"
            f"English: {english}\nTraditional Chinese:")


# Qwen sometimes emits Simplified characters; OpenCC converts them to Taiwan Traditional
# (s2tw) so Taigi — trained on Traditional Hokkien Han-ji — receives clean input.
from opencc import OpenCC
_s2tw = OpenCC("s2tw")


def to_traditional(text: str) -> str:
    return _s2tw.convert(text)


# ---- load the speech model once, keep it warm ----
import numpy as np
import torch
import gradio as gr
from omnivoice.models.omnivoice import OmniVoice


def normalize(audio, target_peak=0.95):
    peak = float(np.abs(audio).max())
    return audio * (target_peak / peak) if peak > 1e-6 else audio


device = "cuda:0" if torch.cuda.is_available() else "cpu"
print(f"Loading OmniVoice on {device} (one-time)...")
model = OmniVoice.from_pretrained(
    "MERaLiON/MERaLiON-OmniVoice-Hokkien-TTS", device_map=device, dtype=torch.float16,
)

# Build the voice-clone prompt once (reused for every message).
clone = None
if os.path.exists(REF_AUDIO):
    clone = model.create_voice_clone_prompt(ref_audio=REF_AUDIO, ref_text=REF_TEXT)
    print("Voice clone ready (my_voice.wav).")
else:
    print("No my_voice.wav found — 'My voice' option will fall back to default voice.")

# Pre-warm the translation models so they're already in VRAM before your first message.
print("Warming up translation models...")
ollama(QWEN, "Hello")
ollama("taigi", "你好")
print("Ready.")


def respond(english, use_my_voice):
    """Generator: yields live status after each stage so the UI shows progress."""
    english = (english or "").strip()
    if not english:
        yield "Type an English sentence first.", None
        return

    t0 = time.time()

    # If it's a known demo phrase, use the curated Hokkien (always correct + instant).
    pinned = phrasebook_lookup(english)
    if pinned is not None:
        mandarin = "—  *(phrasebook: skipped translation)*"
        hokkien = pinned
        t1 = t2 = time.time()
    else:
        yield "⏳ **Step 1/3** — Translating English → Mandarin… *(first message also loads the model, so this can take ~10s)*", None
        mandarin = to_traditional(ollama(QWEN, qwen_prompt(english)))   # force Traditional
        t1 = time.time()

        yield (f"**English:**  {english}\n\n"
               f"**Mandarin:**  {mandarin}\n\n"
               f"⏳ **Step 2/3** — Translating Mandarin → Hokkien…"), None
        hokkien = ollama("taigi", mandarin)
        t2 = time.time()

    yield (f"**English:**  {english}\n\n"
           f"**Mandarin:**  {mandarin}\n\n"
           f"**Hokkien:**  {hokkien}\n\n"
           f"⏳ **Step 3/3** — Generating speech…"), None

    kw = dict(text=hokkien, language="nan")
    if use_my_voice and clone is not None:
        wait_unloaded()          # free VRAM so the cloned speech doesn't thrash
        kw.update(voice_clone_prompt=clone, guidance_scale=GUIDANCE)
    audio = normalize(model.generate(**kw)[0])
    t3 = time.time()

    print(f"[timing] qwen {t1-t0:.1f}s | taigi {t2-t1:.1f}s | speak {t3-t2:.1f}s | total {t3-t0:.1f}s")
    steps = (f"**English:**  {english}\n\n"
             f"**Mandarin:**  {mandarin}\n\n"
             f"**Hokkien:**  {hokkien}\n\n"
             f"<sub>✅ {t3-t0:.1f}s "
             f"(translate {t2-t0:.1f}s + speak {t3-t2:.1f}s)</sub>")
    yield steps, (model.sampling_rate, audio)


with gr.Blocks(title="HokkienTTS") as demo:
    gr.Markdown("# 🗣️ HokkienTTS\nType English → hear Singapore Hokkien. 100% local.")
    with gr.Row():
        inp = gr.Textbox(label="English", placeholder="e.g. Have you eaten yet?", scale=4)
        myvoice = gr.Checkbox(label="My voice", value=True, scale=1)
    btn = gr.Button("Speak", variant="primary")
    steps_out = gr.Markdown(label="Translation")
    audio_out = gr.Audio(label="Hokkien", autoplay=True)

    gr.Markdown(
        "<sub>🔒 Runs 100% on your machine — nothing is sent to the internet. · "
        "⚡ The first message warms up the models; after that, replies take a few seconds. · "
        "Pipeline: English → Mandarin (Qwen) → Hokkien (Taigi) → speech (MERaLiON OmniVoice).</sub>"
    )

    btn.click(respond, [inp, myvoice], [steps_out, audio_out])
    inp.submit(respond, [inp, myvoice], [steps_out, audio_out])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", share=False, inbrowser=True)
