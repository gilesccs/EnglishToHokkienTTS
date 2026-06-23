"""
MERaLiON-OmniVoice Hokkien TTS — plain text-to-speech test (no voice cloning yet).

Speaks Hokkien Han-ji using the Singapore-Hokkien OmniVoice model.
Run (from project root, using the omnivoice_env):
    set PYTHONUTF8=1
    omnivoice_env\\Scripts\\python.exe omnivoice_tts.py "你好！食飽未？"

First run downloads the model (~2.7 GB) + audio tokenizer into the HuggingFace cache.
"""
import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TEXT = sys.argv[1] if len(sys.argv) > 1 else "你好！食飽未？"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "omnivoice_output.wav")

import torch
import soundfile as sf
from omnivoice.models.omnivoice import OmniVoice

device = "cuda:0" if torch.cuda.is_available() else "cpu"
print(f"=== Loading MERaLiON-OmniVoice (device={device}) ===")
print("(first run downloads ~2.7 GB — be patient)")

model = OmniVoice.from_pretrained(
    "MERaLiON/MERaLiON-OmniVoice-Hokkien-TTS",
    device_map=device,
    dtype=torch.float16,
)

print(f"=== Synthesizing Hokkien ===")
print("Text:", TEXT)
audios = model.generate(text=TEXT, language="nan")   # nan = Min Nan / Hokkien

sf.write(OUT, audios[0], model.sampling_rate)
print(f"Saved: {OUT}  ({model.sampling_rate} Hz)")
