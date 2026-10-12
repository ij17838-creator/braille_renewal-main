# -*- coding: utf-8 -*-
import json
import os
import sys

# 저장소 루트를 import 경로에 넣어 어디서 실행해도 engine 패키지를 찾게 한다.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data_paths import find_data_file
from engine.ko.ko_syntax_analyzer import BrailleRuleValidator
from engine.ko.ko_parser import KoreanBrailleEngine

v = BrailleRuleValidator()
samples = ["5동안", "5동", "5동에", "5년", "5년동안", "5미터", "5미터가", "8호", "”》", "“가”》"]
for t in samples:
    r = v.validate_text(t)
    print("VAL", t, r["is_valid"])
    for c in r["collisions"]:
        print("  COL", c["message"])
    for d in r["delimiters"]:
        print("  DEL", d["message"])

ko = json.load(open(find_data_file("ko.json"), encoding="utf-8"))
marks = json.load(open(find_data_file("ko_marks.json"), encoding="utf-8"))
nums = json.load(open(find_data_file("numbers.json"), encoding="utf-8"))
nr = json.load(open(find_data_file("ko_number_rules.json"), encoding="utf-8"))
lex = json.load(open(find_data_file("lexicon_ko.json"), encoding="utf-8"))
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
