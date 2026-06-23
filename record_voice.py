"""
Record a short reference clip of YOUR voice for OmniVoice voice cloning.

Records ~8 seconds from your default microphone to my_voice.wav.
Read the sentence printed below, clearly and at a normal pace.

Run:
    omnivoice_env\\Scripts\\python.exe record_voice.py
"""
import sys, io, os, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

import sounddevice as sd
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "my_voice.wav")
DURATION = 15         # seconds
SR = 44100            # recording sample rate (model resamples as needed)

# This exact text is saved so the clone step knows what you said.
# Read it naturally, like you're chatting with a friend — not flat/robotic.
REF_TEXT = ("Hey, I just got back from the hawker centre near my place, and the food "
            "there was really good. I had some chicken rice and a cold drink, sat down, "
            "and relaxed for a bit. It's one of my favourite things to do on the weekend.")

print("=" * 60)
print("READ THIS ALOUD when recording starts (normal pace, clear voice):")
print()
print("   " + REF_TEXT)
print("=" * 60)
print()
for n in (3, 2, 1):
    print(f"  recording in {n}...")
    time.sleep(1)

print(f"\n>>> RECORDING NOW for {DURATION} seconds — speak! <<<")
rec = sd.rec(int(DURATION * SR), samplerate=SR, channels=1)
sd.wait()
sf.write(OUT, rec, SR)

print(f"\nDone. Saved: {OUT}")
print("If you fumbled, just run this script again to re-record.")
