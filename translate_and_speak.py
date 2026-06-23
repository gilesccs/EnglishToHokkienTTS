"""
Phases 1+2 combined — English in, spoken Hokkien out.

  English --(Qwen)--> Mandarin --(Taigi)--> Hokkien Han-ji --(IPA dump)--> SuiSiann TTS --> .wav

Ollama must be running (it starts automatically after install). Run:
    set PYTHONUTF8=1
    hokkien_speech_env\\Scripts\\python.exe translate_and_speak.py "Have you eaten yet?"
"""
import sys, io, os, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ENGLISH = sys.argv[1] if len(sys.argv) > 1 else "Have you eaten yet?"

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "models", "suisiann", "best_model.pth")
CONFIG = os.path.join(HERE, "models", "suisiann", "config.json")
OUT = os.path.join(HERE, "output.wav")
GORUUT_BIN = os.path.join(os.path.expanduser("~"), ".goruut_bin")
os.makedirs(GORUUT_BIN, exist_ok=True)

OLLAMA = "http://localhost:11434/api/generate"


def ollama(model: str, prompt: str) -> str:
    """Send a prompt to a local Ollama model, return the response text."""
    data = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["response"].strip()


# --- Step 1: English -> Mandarin (Qwen is great at this high-resource direction) ---
qwen_prompt = (
    "Translate the following English sentence into Traditional Chinese (Mandarin). "
    "Output ONLY the translation - no pinyin, no explanation, no quotes.\n\n"
    f"English: {ENGLISH}\nTraditional Chinese:"
)
mandarin = ollama("qwen2.5:7b", qwen_prompt)

# --- Step 2: Mandarin -> Hokkien Han-ji (Taigi specialist; template adds [TRANS]..[HAN]) ---
hokkien = ollama("taigi", mandarin)

print("=== Translation ===")
print("English :", ENGLISH)
print("Mandarin:", mandarin)
print("Hokkien :", hokkien)

# --- Step 3: IPA diagnostic (see the pronunciation before audio) ---
from pygoruut.pygoruut import Pygoruut

pg = Pygoruut(version="v0.6.3", writeable_bin_dir=GORUUT_BIN)
ipa = pg.phonemize(language="MinnanHokkien2", sentence=hokkien)
print("\n=== IPA diagnostic ===")
print("IPA :", str(ipa))
for w in ipa.Words:
    print(f"   {w.CleanWord} -> {w.Phonetic}")

# --- Step 4: synthesize audio ---
import torch
from TTS.api import TTS

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"\n=== Synthesizing (device={device}) ===")
tts = TTS(model_path=MODEL, config_path=CONFIG).to(device)
tts.tts_to_file(text=hokkien, file_path=OUT)
print("Saved:", OUT)
