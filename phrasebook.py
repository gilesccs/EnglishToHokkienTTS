"""
Phrasebook of KNOWN-GOOD Hokkien for demo phrases.

When the typed English matches an entry here, the app uses this exact Hokkien instead
of running the translation pipeline — so core demo lines are always correct AND instant.

HOW TO EDIT:
  - Left side  = English, lowercase, no punctuation (that's how it's matched).
  - Right side = the exact Hokkien Han-ji you want spoken.
  - Add as many as you like. Giles: please CHECK/FIX every line — these are my best guess.

Matching is case/punctuation-insensitive, so "Have you eaten?" matches "have you eaten".
"""

PHRASEBOOK = {
    # The iconic greeting (you confirmed this one): "jia ba buey"
    "have you eaten":            "你食飽未？",
    "have you eaten yet":        "你食飽未？",
    "have u eaten":              "你食飽未？",

    # From the batch — please verify/correct:
    "what is your name":         "你號做啥物名？",
    "where are you going":       "你欲去佗位？",
    "i am going home":           "我這馬欲轉去矣。",
    "i am going home now":       "我這馬欲轉去矣。",
    "the weather is very hot today": "今仔日天氣誠燒熱。",
    "this food is delicious":    "這物真好食。",
    "i love you":                "我愛你。",

    # Corrected (pipeline got these wrong) — please verify:
    "thank you":                 "多謝！",
    "thank you very much":       "真多謝！",
}
