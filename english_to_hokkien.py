"""
FULL PIPELINE — type English, hear Singapore Hokkien (MERaLiON OmniVoice).

  English --(Qwen via Ollama)--> Mandarin --(Taigi via Ollama)--> Hokkien Han-ji
          --(MERaLiON-OmniVoice)--> Singapore Hokkien audio (.wav)

Translation runs in Ollama (a local server), so this single script — running in
omnivoice_env — just calls it over HTTP, then synthesizes speech locally.

Run (from project root):
    set PYTHONUTF8=1
    omnivoice_env\\Scripts\\python.exe english_to_hokkien.py "Have you eaten yet?"
"""
import sys, io, os, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ENGLISH = sys.argv[1] if len(sys.argv) > 1 else "Have you eaten yet?"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "english_to_hokkien_output.wav")
OLLAMA = "http://localhost:11434/api/generate"


def ollama(model: str, prompt: str) -> str:
    """Send a prompt to a local Ollama model, return the response text."""
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

# --- Step 2: Mandarin -> Hokkien Han-ji (Taigi specialist) ---
hokkien = ollama("taigi", mandarin)

print("=== Translation ===")
print("English :", ENGLISH)
print("Mandarin:", mandarin)
print("Hokkien :", hokkien)

# --- Step 3: speak it with MERaLiON OmniVoice (Singapore Hokkien) ---
import torch
import soundfile as sf
from omnivoice.models.omnivoice import OmniVoice

device = "cuda:0" if torch.cuda.is_available() else "cpu"
print(f"\n=== Synthesizing Singapore Hokkien (device={device}) ===")
model = OmniVoice.from_pretrained(
    "MERaLiON/MERaLiON-OmniVoice-Hokkien-TTS",
    device_map=device,
    dtype=torch.float16,
)
audios = model.generate(text=hokkien, language="nan")   # nan = Min Nan / Hokkien
sf.write(OUT, audios[0], model.sampling_rate)
print("Saved:", OUT)
