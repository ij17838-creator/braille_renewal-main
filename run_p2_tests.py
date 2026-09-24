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


def test_canonical_roundtrip():
    print("\n=== Canonical cell and round-trip check ===")
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

    assert "connectors" not in numbers_data, "numbers.json must not carry language-specific connectors"
    assert set(numbers_data["digits"]) == set("0123456789")

    ko_engine = KoreanBrailleEngine(ko_data, marks_data, numbers_data, number_rules, lexicon_data)
    sa = ko_data["abbreviation_syllable"]["items"]["사"]["expanded_unicode"]
    assert sa == ko_engine.sa_expanded == "⠠⠣"

    bang = marks_data["terminal_punctuation"]["items"]["!"]["unicode"]
    period = marks_data["terminal_punctuation"]["items"]["."]["unicode"]
    assert bang == "⠖" and period == "⠲"

    for path in ("morpheme_words.json", "morpheme_quizzes.json"):
        with open(os.path.join(base_dir, path), "r", encoding="utf-8") as f:
            quiz = json.load(f)
        for item in quiz.get("KO", []):
            text = item.get("target_text", "")
            braille = item.get("target_braille", "")
            if text.startswith("느낌표"):
                assert braille == bang, path
            if text.startswith("마침표"):
                assert braille == period, path
            if text == "4사분기":
                assert "⠠⠣" in braille and "⠇" not in braille, path
                assert braille == ko_engine.text_to_braille(text)["braille"], path
            if text == "사람":
                assert braille == "⠇⠐⠣⠢", path
                assert braille == ko_engine.text_to_braille(text)["braille"], path
            assert text != "하지만", path

    units = set(number_rules["collision_resolutions"]["trailing_letters"]["exempt_units"])
    assert ko_engine.exempt_units == units
    assert KoValidator(data_dir=base_dir).exempt_units == units

    for cell, senses in ko_engine.rev_uses.items():
        if len({sense["text"] for sense in senses}) > 1:
            assert all(sense.get("context") for sense in senses), cell
    assert {"ㅎ", "”", "》"} <= {sense["text"] for sense in ko_engine.rev_uses["⠴"]}
    assert {"“", "《", "?"} <= {sense["text"] for sense in ko_engine.rev_uses["⠦"]}
    assert "”" in ko_engine.braille_to_text("⠴") and "》" in ko_engine.braille_to_text("⠴")
    assert "“" in ko_engine.braille_to_text("⠦⠫") and "《" in ko_engine.braille_to_text("⠦⠫")
    assert ko_engine.braille_to_text("⠦") == "?"
    assert ko_engine.braille_to_text("⠠⠄⠠⠄") == "<tn></tn>"
    placeholders = ko_engine.braille_to_text("⠴⠴")
    assert all(ch in placeholders for ch in ("×", "○", "△"))
    dashes = ko_engine.braille_to_text("⠤⠤")
    assert all(ch in dashes for ch in ("~", "—", "□"))

    for word in ["라", "간", "차", "좋", "사람", "1,000", "4사분기"]:
        braille = ko_engine.text_to_braille(word)["braille"]
        back = ko_engine.braille_to_text(braille)
        print(f"KO {word} -> {braille} -> {back}")
        assert back == word, (word, braille, back)

    en_engine = BrailleEngine(base_data_dir=base_dir)
    overlapped = [cell for cell, senses in en_engine.rev_groupsign_senses.items() if len(senses) > 1]
    assert overlapped, "expected shared cells such as be/bb to keep more than one sense"
    for cell in overlapped:
        assert all("rule" in sense for sense in en_engine.rev_groupsign_senses[cell])
    assert {sense["text"] for sense in en_engine.rev_groupsign_senses["⠆"]} >= {"bb", "be"}
    assert {sense["text"] for sense in en_engine.rev_groupsign_senses["⠒"]} >= {"cc", "con"}
    assert {sense["text"] for sense in en_engine.rev_groupsign_senses["⠲"]} >= {"dd", "dis"}
    assert all(sense.get("context") for sense in en_engine.rev_symbol_senses["⠂"])
    a = en_engine.spelling["a"]
    b = en_engine.spelling["b"]
    assert en_engine.braille_to_text(a + en_engine.contraction_items["bb"]["unicode"] + a) == "abba"
    assert en_engine.braille_to_text(en_engine.contraction_items["be"]["unicode"] + a) == "bea"
    assert en_engine.braille_to_text(a + en_engine.contraction_items["cc"]["unicode"] + a) == "acca"
    assert en_engine.braille_to_text(en_engine.contraction_items["con"]["unicode"] + a) == "cona"
    assert en_engine.braille_to_text(a + en_engine.contraction_items["dd"]["unicode"] + a) == "adda"
    assert en_engine.braille_to_text(en_engine.contraction_items["dis"]["unicode"] + a) == "disa"
    assert en_engine.braille_to_text(a + "⠂" + a) == "aea"
    assert en_engine.braille_to_text(a + "⠲") == "a."
    assert en_engine.braille_to_text(a + "⠖") == "a!"
    assert en_engine.braille_to_text(en_engine.num_prefix + a + "⠂" + b) == "1,2"

    for word in ["the", "be", "con", "dis"]:
        braille = en_engine.text_to_braille(word)
        back = en_engine.braille_to_text(braille)
        print(f"EN {word} -> {braille} -> {back}")
        assert back == word, (word, braille, back)

    print("Canonical checks passed.")


if __name__ == "__main__":
    test_korean()
    test_english()
    test_canonical_roundtrip()
