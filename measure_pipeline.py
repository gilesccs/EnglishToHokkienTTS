"""
Measure the full pipeline with keep_alive=0 (translation models unload after each
call, freeing VRAM so OmniVoice's voice-cloning has room). Runs twice for steady state.
"""
import sys, io, os, json, time, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
REF_AUDIO = os.path.join(HERE, "my_voice.wav")
OLLAMA = "http://localhost:11434/api/generate"
REF_TEXT = ("Hey, I just got back from the hawker centre near my place, and the food "
            "there was really good. I had some chicken rice and a cold drink, sat down, "
            "and relaxed for a bit. It's one of my favourite things to do on the weekend.")

from opencc import OpenCC
_s2tw = OpenCC("s2tw")


def ollama(model_name, prompt, keep_alive):
    payload = {"model": model_name, "prompt": prompt, "stream": False,
               "keep_alive": keep_alive, "options": {"num_ctx": 1024}}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["response"].strip()


def wait_unloaded(timeout=6.0):
    """Block until Ollama reports no models in VRAM (so OmniVoice gets full room)."""
    t = time.time()
    while time.time() - t < timeout:
        try:
            with urllib.request.urlopen("http://localhost:11434/api/ps") as r:
                if not json.loads(r.read().decode("utf-8")).get("models"):
                    return time.time() - t
        except Exception:
            pass
        time.sleep(0.2)
    return time.time() - t


def qprompt(eng):
    return ("Translate the following English sentence into natural, complete Traditional "
            "Chinese (Mandarin). Keep the full meaning; do not drop words. "
            "Output ONLY the translation - no pinyin, no explanation, no quotes.\n\n"
            f"English: {eng}\nTraditional Chinese:")


import numpy as np, torch, soundfile as sf
from omnivoice.models.omnivoice import OmniVoice

print("Loading OmniVoice...")
model = OmniVoice.from_pretrained(
    "MERaLiON/MERaLiON-OmniVoice-Hokkien-TTS", device_map="cuda:0", dtype=torch.float16)
clone = model.create_voice_clone_prompt(ref_audio=REF_AUDIO, ref_text=REF_TEXT)


def run(eng, keep_alive):
    t0 = time.time()
    man = _s2tw.convert(ollama("qwen2.5:3b", qprompt(eng), keep_alive))
    t1 = time.time()
    hok = ollama("taigi", man, keep_alive)
    t2 = time.time()
    waited = wait_unloaded()
    t2b = time.time()
    model.generate(text=hok, language="nan", voice_clone_prompt=clone, guidance_scale=3.0)
    t3 = time.time()
    print(f"  '{eng}' -> {hok}")
    print(f"  qwen {t1-t0:.1f}s | taigi {t2-t1:.1f}s | wait-unload {t2b-t2:.1f}s | speak {t3-t2b:.1f}s | TOTAL {t3-t0:.1f}s")


print("\n=== keep_alive=0 (unload translation models before speak) ===")
run("Have you eaten yet?", 0)
print("--- second run (steady state) ---")
run("The weather is very hot today", 0)
print("\nDone.")
