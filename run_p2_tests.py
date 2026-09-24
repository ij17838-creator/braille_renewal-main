import json
import os
import sys

from ko_parser import KoreanBrailleEngine
from en_parser import BrailleEngine
from ko_syntax_analyzer import BrailleRuleValidator as KoValidator
from en_syntax_analyzer import BrailleRuleValidator as EnValidator


def test_korean():
    print("=== Korean Loader & Converter Test ===")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    with open(os.path.join(base_dir, "ko.json"), "r", encoding="utf-8") as f:
        ko_data = json.load(f)
    with open(os.path.join(base_dir, "ko_marks.json"), "r", encoding="utf-8") as f:
        marks_data = json.load(f)
    with open(os.path.join(base_dir, "numbers.json"), "r", encoding="utf-8") as f:
        numbers_data = json.load(f)
    with open(os.path.join(base_dir, "ko_number_rules.json"), "r", encoding="utf-8") as f:
        number_rules = json.load(f)
    with open(os.path.join(base_dir, "lexicon_ko.json"), "r", encoding="utf-8") as f:
        lexicon_data = json.load(f)

    ko_engine = KoreanBrailleEngine(
        ko_data=ko_data,
        marks_data=marks_data,
        numbers_data=numbers_data,
        number_rules=number_rules,
        lexicon_data=lexicon_data
    )

    # 1. Text -> Braille
    text1 = "그리고 123m"
    res1 = ko_engine.text_to_braille(text1)
    print(f"Text to Braille: '{text1}' -> '{res1['braille']}'")

    text2 = "쌍둥이 5개"
    res2 = ko_engine.text_to_braille(text2)
    print(f"Text to Braille: '{text2}' -> '{res2['braille']}'")

    # 2. Braille -> Text
    b_test1 = res1['braille']
    rev1 = ko_engine.braille_to_text(b_test1)
    print(f"Braille to Text: '{b_test1}' -> '{rev1}'")

    b_test2 = res2['braille']
    rev2 = ko_engine.braille_to_text(b_test2)
    print(f"Braille to Text: '{b_test2}' -> '{rev2}'")

    # Syntax Analyzer
    ko_val = KoValidator(data_dir=base_dir)
    val_res = ko_val.validate_text("제2차 세계대전은 1945년에 끝났다. 5월 12일 3미터 앞.")
    print(f"Korean Syntax Validation (valid={val_res['is_valid']}): issues={val_res['total_issues']}")


def test_english():
    print("\n=== English Loader & Converter Test ===")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    en_engine = BrailleEngine(base_data_dir=base_dir)

    # 1. Text -> Braille
    text1 = "but can do 123a react"
    b1 = en_engine.text_to_braille(text1)
    print(f"Text to Braille: '{text1}' -> '{b1}'")

    # 2. Braille -> Text
    rev1 = en_engine.braille_to_text(b1)
    print(f"Braille to Text: '{b1}' -> '{rev1}'")

    # Syntax Analyzer
    en_val = EnValidator(base_data_dir=base_dir)
    val_res = en_val.validate_sentence("He's 123a-4 and reacted abouts.")
    print(f"English Syntax Validation sentence: {val_res['sentence']}")
    for tok in val_res['tokens']:
        print(f"  [{tok['token']}] -> {tok['validations']}")


if __name__ == "__main__":
    test_korean()
    test_english()
