"""
Diagnostic: how long does OmniVoice speech generation actually take, with VRAM free?

Times several configs on the SAME fixed sentence. First call is a throwaway warm-up
(the first generate always pays one-time CUDA kernel setup). Run with the chat app
stopped and Ollama models unloaded so the GPU is free.
"""
import sys, io, os, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
REF_AUDIO = os.path.join(HERE, "my_voice.wav")
HOKKIEN = "你食飽未？"
REF_TEXT = ("Hey, I just got back from the hawker centre near my place, and the food "
            "there was really good. I had some chicken rice and a cold drink, sat down, "
            "and relaxed for a bit. It's one of my favourite things to do on the weekend.")

import torch
from omnivoice.models.omnivoice import OmniVoice

device = "cuda:0" if torch.cuda.is_available() else "cpu"
print(f"Loading OmniVoice on {device}...")
model = OmniVoice.from_pretrained(
    "MERaLiON/MERaLiON-OmniVoice-Hokkien-TTS", device_map=device, dtype=torch.float16,
)
clone = model.create_voice_clone_prompt(ref_audio=REF_AUDIO, ref_text=REF_TEXT)


def timed(label, **kw):
    torch.cuda.synchronize()
    t = time.time()
    model.generate(text=HOKKIEN, language="nan", **kw)
    torch.cuda.synchronize()
    print(f"  {label}: {time.time() - t:.1f}s")


print("\n--- warm-up (one-time kernel setup, ignore this number) ---")
timed("warmup", voice_clone_prompt=clone, guidance_scale=3.0)

print("\n--- measured, GPU free ---")
timed("default voice,  32 step", )
timed("cloned voice,   32 step", voice_clone_prompt=clone, guidance_scale=3.0)
timed("cloned voice,   16 step", voice_clone_prompt=clone, guidance_scale=3.0, num_step=16)
timed("cloned voice,    8 step", voice_clone_prompt=clone, guidance_scale=3.0, num_step=8)
print("\nDone.")
