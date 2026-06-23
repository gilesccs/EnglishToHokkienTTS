"""
FULL PIPELINE + VOICE CLONING — type English, hear Singapore Hokkien IN YOUR OWN VOICE.

  English --(Qwen)--> Mandarin --(Taigi)--> Hokkien Han-ji
          --(MERaLiON-OmniVoice + my_voice.wav)--> Hokkien audio in your voice (.wav)

Requires my_voice.wav (record it first with record_voice.py).
Run:
    set PYTHONUTF8=1
    omnivoice_env\\Scripts\\python.exe english_to_hokkien_myvoice.py "Have you eaten yet?"
"""
import sys, io, os, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

ENGLISH = sys.argv[1] if len(sys.argv) > 1 else "Have you eaten yet?"
HERE = os.path.dirname(os.path.abspath(__file__))
REF_AUDIO = os.path.join(HERE, "my_voice.wav")
OUT = os.path.join(HERE, "myvoice_output.wav")
OLLAMA = "http://localhost:11434/api/generate"

# MUST match exactly what you read while recording (see record_voice.py).
REF_TEXT = ("Hey, I just got back from the hawker centre near my place, and the food "
            "there was really good. I had some chicken rice and a cold drink, sat down, "
            "and relaxed for a bit. It's one of my favourite things to do on the weekend.")

GUIDANCE = 3.0   # how hard to clone your voice (tuned: 3.0 sounds most like you)

if not os.path.exists(REF_AUDIO):
    sys.exit(f"Missing {REF_AUDIO} — record it first with record_voice.py")


def ollama(model: str, prompt: str) -> str:
    data = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["response"].strip()


# --- Step 1: English -> Mandarin (Qwen) ---
qwen_prompt = (
    "Translate the following English sentence into Traditional Chinese (Mandarin). "
    "Output ONLY the translation - no pinyin, no explanation, no quotes.\n\n"
    f"English: {ENGLISH}\nTraditional Chinese:"
)
mandarin = ollama("qwen2.5:7b", qwen_prompt)

# --- Step 2: Mandarin -> Hokkien Han-ji (Taigi) ---
hokkien = ollama("taigi", mandarin)

print("=== Translation ===")
print("English :", ENGLISH)
print("Mandarin:", mandarin)
print("Hokkien :", hokkien)

# --- Step 3: speak it in YOUR voice (OmniVoice voice cloning) ---
import numpy as np
import torch
import soundfile as sf
from omnivoice.models.omnivoice import OmniVoice


def normalize(audio, target_peak=0.95):
    """Boost to full volume so a quiet reference clip doesn't make output soft."""
    peak = float(np.abs(audio).max())
    return audio * (target_peak / peak) if peak > 1e-6 else audio


device = "cuda:0" if torch.cuda.is_available() else "cpu"
print(f"\n=== Synthesizing in your cloned voice (device={device}) ===")
model = OmniVoice.from_pretrained(
    "MERaLiON/MERaLiON-OmniVoice-Hokkien-TTS",
    device_map=device,
    dtype=torch.float16,
)
audios = model.generate(
    text=hokkien,
    language="nan",              # Min Nan / Hokkien
    ref_audio=REF_AUDIO,         # your voice clip -> clone its timbre
    ref_text=REF_TEXT,           # what you said in the clip (for accuracy)
    guidance_scale=GUIDANCE,     # tuned for best likeness to you
)
sf.write(OUT, normalize(audios[0]), model.sampling_rate)   # full volume
print("Saved:", OUT)
