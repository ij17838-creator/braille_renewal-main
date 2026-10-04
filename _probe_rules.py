# -*- coding: utf-8 -*-
import json
from ko_syntax_analyzer import BrailleRuleValidator
from ko_parser import KoreanBrailleEngine

v = BrailleRuleValidator()
samples = ["5동안", "5동", "5동에", "5년", "5년동안", "5미터", "5미터가", "8호", "”》", "“가”》"]
for t in samples:
    r = v.validate_text(t)
    print("VAL", t, r["is_valid"])
    for c in r["collisions"]:
        print("  COL", c["message"])
    for d in r["delimiters"]:
        print("  DEL", d["message"])

ko = json.load(open("ko.json", encoding="utf-8"))
marks = json.load(open("ko_marks.json", encoding="utf-8"))
nums = json.load(open("numbers.json", encoding="utf-8"))
nr = json.load(open("ko_number_rules.json", encoding="utf-8"))
lex = json.load(open("lexicon_ko.json", encoding="utf-8"))
e = KoreanBrailleEngine(ko, marks, nums, nr, lex)
for t in ["5동안", "5동", "5동에", "5년", "1년", "8호", "3미터", "5개", "5년동안"]:
    b = e.text_to_braille(t)["braille"]
    back = e.braille_to_text(b)
    print("RT", t, "->", b, "->", back)

print("--- conj ---")
pairs = [
    ("깨닫", "아"), ("깨닫", "으면"), ("얻", "어"), ("듣", "어"),
    ("집", "어"), ("돕", "아"), ("곱", "아"), ("잇", "어"), ("솟", "아"),
    ("이르", "어"), ("걷", "어"), ("묻", "어"), ("닫", "아"),
]
for stem, eomi in pairs:
    print(stem, eomi, v.analyze_conjugation_form(stem, eomi))
