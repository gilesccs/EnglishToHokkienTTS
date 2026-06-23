"""
Voice-clone TUNING — speak ONE fixed Hokkien sentence in your voice at several settings.

Isolates the voice variable: same words every time, only the cloning settings change.
Produces several .wav files so you can A/B which sounds most like you:

    tune_default.wav    - OmniVoice's own voice (baseline, no cloning)
    tune_g2.0.wav       - your voice, guidance_scale 2.0 (model default)
    tune_g2.5.wav       - your voice, guidance_scale 2.5
    tune_g3.0.wav       - your voice, guidance_scale 3.0
    tune_g3.0_steps64.wav - guidance 3.0 + more refinement steps (slower, cleaner)

Requires my_voice.wav. Run:
    set PYTHONUTF8=1
    omnivoice_env\\Scripts\\python.exe tune_voice.py
"""
import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
REF_AUDIO = os.path.join(HERE, "my_voice.wav")

# Fixed test sentence: "li jia ba buey" = "Have you eaten yet?"
HOKKIEN = "你食飽未？"

# MUST match what you read while recording (record_voice.py).
REF_TEXT = ("Hey, I just got back from the hawker centre near my place, and the food "
            "there was really good. I had some chicken rice and a cold drink, sat down, "
            "and relaxed for a bit. It's one of my favourite things to do on the weekend.")

if not os.path.exists(REF_AUDIO):
    sys.exit(f"Missing {REF_AUDIO} — record it first with record_voice.py")

import numpy as np
import torch
import soundfile as sf
from omnivoice.models.omnivoice import OmniVoice


def normalize(audio, target_peak=0.95):
    """Boost audio to full volume so a quiet reference clip doesn't make it soft."""
    peak = float(np.abs(audio).max())
    return audio * (target_peak / peak) if peak > 1e-6 else audio

device = "cuda:0" if torch.cuda.is_available() else "cpu"
print(f"Loading OmniVoice (device={device})...")
model = OmniVoice.from_pretrained(
    "MERaLiON/MERaLiON-OmniVoice-Hokkien-TTS", device_map=device, dtype=torch.float16,
)
print(f"Sentence: {HOKKIEN}  (li jia ba buey)\n")

# Build the clone prompt ONCE (reuse for every cloned variant).
clone = model.create_voice_clone_prompt(ref_audio=REF_AUDIO, ref_text=REF_TEXT)

variants = [
    ("tune_default.wav",        dict()),                                  # no clone (benchmark)
    ("tune_g3.0.wav",           dict(voice_clone_prompt=clone, guidance_scale=3.0)),
    ("tune_g3.0_steps64.wav",   dict(voice_clone_prompt=clone, guidance_scale=3.0, num_step=64)),
]

for name, kw in variants:
    out = os.path.join(HERE, name)
    audios = model.generate(text=HOKKIEN, language="nan", **kw)
    sf.write(out, normalize(audios[0]), model.sampling_rate)   # full volume
    print("Saved:", name)

print("\nDone. Listen and tell me which sounds most like you.")
