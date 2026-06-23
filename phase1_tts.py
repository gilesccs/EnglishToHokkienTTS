"""
Phase 1 — native Hokkien TTS test.

Takes Hokkien Hàn-jī text, prints the IPA diagnostic (so we can SEE the pronunciation
goruut chose), then synthesizes it to a .wav with the SuiSiann VITS model.

Run:  hokkien_speech_env\\Scripts\\python.exe phase1_tts.py
"""
import sys, io, os

# Windows console can't print Chinese/IPA in its legacy encoding — force UTF-8 output.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TEXT = "你好！食飽未？"

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "models", "suisiann", "best_model.pth")
CONFIG = os.path.join(HERE, "models", "suisiann", "config.json")
OUT = os.path.join(HERE, "test_native_hokkien.wav")
GORUUT_BIN = os.path.join(os.path.expanduser("~"), ".goruut_bin")
os.makedirs(GORUUT_BIN, exist_ok=True)

# ---------------------------------------------------------------------------
# 1) IPA diagnostic — print what goruut will pronounce, BEFORE making audio.
#    This is our Phase-1 habit: turn "sounds off" into "it read 食 as sit".
# ---------------------------------------------------------------------------
from pygoruut.pygoruut import Pygoruut

pg = Pygoruut(version="v0.6.3", writeable_bin_dir=GORUUT_BIN)
ipa = pg.phonemize(language="MinnanHokkien2", sentence=TEXT)
print("=== IPA diagnostic ===")
print("Input :", TEXT)
print("IPA   :", str(ipa))
for w in ipa.Words:
    print(f"   {w.CleanWord} -> {w.Phonetic}")

# ---------------------------------------------------------------------------
# 2) Synthesis — load the VITS model and write the .wav.
# ---------------------------------------------------------------------------
import torch
from TTS.api import TTS

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"\n=== Loading model (device={device}) ===")
tts = TTS(model_path=MODEL, config_path=CONFIG).to(device)

print("=== Synthesizing ===")
tts.tts_to_file(text=TEXT, file_path=OUT)
print("Saved:", OUT)
