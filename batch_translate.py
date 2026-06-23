"""Translate a batch of demo sentences (text only, no audio) so we can pick good ones."""
import sys, io, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from opencc import OpenCC
_s2tw = OpenCC("s2tw")
OLLAMA = "http://localhost:11434/api/generate"

def ollama(model_name, prompt):
    payload = {"model": model_name, "prompt": prompt, "stream": False,
               "keep_alive": "5m", "options": {"num_ctx": 1024}}
    req = urllib.request.Request(OLLAMA, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))["response"].strip()

def qprompt(eng):
    return ("Translate the following English sentence into natural, complete Traditional "
            "Chinese (Mandarin). Keep the full meaning; do not drop words. "
            "Output ONLY the translation - no pinyin, no explanation, no quotes.\n\n"
            f"English: {eng}\nTraditional Chinese:")

SENTENCES = [
    "Hello, how are you?",
    "Have you eaten?",
    "Thank you very much.",
    "What is your name?",
    "I am going home now.",
    "The weather is very hot today.",
    "How much is this?",
    "I love you.",
    "Where are you going?",
    "See you tomorrow.",
    "This food is delicious.",
    "Be careful on your way home.",
]

for eng in SENTENCES:
    man = _s2tw.convert(ollama("qwen2.5:3b", qprompt(eng)))
    hok = ollama("taigi", man)
    print(f"EN: {eng}\n   Mandarin: {man}\n   Hokkien:  {hok}\n")
