import json
import os
import sys

from ko_parser import KoreanBrailleEngine
from en_parser import BrailleEngine
from ko_syntax_analyzer import BrailleRuleValidator as KoValidator
from en_syntax_analyzer import BrailleRuleValidator as EnValidator


def test_homograph_conjugation():
    print("\n=== Homograph conjugation ===")
    validator = KoValidator()
    schema = validator.lexicon["entry_schema"]
    for section in ("example_stems", "contrasting_examples"):
        optional = schema[section]["optional"]
        assert "meaning" in optional and "sense_id" in optional, section

    arrive = validator.analyze_conjugation_form("이르", "어", meaning="arrive")
    assert arrive["surface_form"] == "이르러" and arrive["rule_applied"] == "러 불규칙"
    assert arrive["meaning"] == "arrive" and arrive["sense_id"] == "ireu-arrive"
    tell = validator.analyze_conjugation_form("이르", "어", meaning="tell")
    assert tell["surface_form"] == "일러" and tell["rule_applied"] == "르 불규칙"
    assert validator.analyze_conjugation_form("이르", "어", context="도착하다")["surface_form"] == "이르러"
    assert validator.analyze_conjugation_form("이르", "어서", tag="말하다")["surface_form"] == "일러서"
    assert validator.analyze_conjugation_form("이르", "었다", meaning="tell")["surface_form"] == "일렀다"
    assert validator.analyze_conjugation_form("이르", "었다", meaning="arrive")["surface_form"] == "이르렀다"
    assert validator.analyze_conjugation_form("이르", "아", sense_id="ireu-tell")["surface_form"] == "일러"

    both = validator.analyze_conjugation_form("이르", "어")
    assert both["ambiguous"] is True and both["surface_form"] is None
    assert {item["surface_form"] for item in both["candidates"]} == {"이르러", "일러"}
    unmatched = validator.analyze_conjugation_form("이르", "어", meaning="dance")
    assert unmatched["ambiguous"] is True and unmatched["sense_unmatched"] is True

    pureu = validator.analyze_conjugation_form("푸르", "어")
    assert pureu["surface_form"] == "푸르러" and not pureu.get("ambiguous")
    assert validator.analyze_conjugation_form("부르", "어")["surface_form"] == "불러"
    assert validator.analyze_conjugation_form("빠르", "아")["surface_form"] == "빨라"
    assert validator.analyze_conjugation_form("이르", "면")["surface_form"] == "이르면"

    assert validator.analyze_conjugation_form("걷", "어", meaning="walk")["surface_form"] == "걸어"
    assert validator.analyze_conjugation_form("걷", "어", sense_id="geot-roll")["surface_form"] == "걷어"
    assert validator.analyze_conjugation_form("걷", "으면", context="길을 가다")["surface_form"] == "걸으면"
    assert validator.analyze_conjugation_form("묻", "어", tag="질문하다")["surface_form"] == "물어"
    assert validator.analyze_conjugation_form("묻", "어요", meaning="bury")["surface_form"] == "묻어요"
    geot = validator.analyze_conjugation_form("걷", "어")
    assert geot["ambiguous"] is True
    assert {item["surface_form"] for item in geot["candidates"]} == {"걸어", "걷어"}
    mut = validator.analyze_conjugation_form("묻", "어")
    assert {item["meaning"] for item in mut["candidates"]} == {"ask", "bury"}

    heard = validator.analyze_conjugation_form("듣", "어")
    assert heard == {
        "rule_applied": "ㄷ 불규칙",
        "surface_form": "들어",
        "braille_instruction": "받침 ㄷ을 ㄹ로 바꾸어 적음",
    }
    assert validator.analyze_conjugation_form("깨닫", "아")["surface_form"] == "깨달아"
    assert validator.analyze_conjugation_form("닫", "아")["surface_form"] == "닫아"
    assert validator.analyze_conjugation_form("걷", "고")["surface_form"] == "걷고"
    print("Homograph conjugation checks passed.")


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

    for path in ("quiz_bank.json",):
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
    ko_val_units = KoValidator(data_dir=base_dir)
    assert ko_val_units.exempt_units == units
    assert ko_engine.unit_boundary_enabled and ko_val_units.unit_boundary_enabled
    assert "에" in ko_engine.josa_sorted and "에" in ko_val_units.josa_sorted

    assert " " in ko_engine.text_to_braille("5동안")["braille"]
    assert " " not in ko_engine.text_to_braille("5동")["braille"]
    assert " " not in ko_engine.text_to_braille("5동에")["braille"]
    assert " " not in ko_engine.text_to_braille("5동에서")["braille"]
    assert " " not in ko_engine.text_to_braille("5미터가")["braille"]
    assert " " not in ko_engine.text_to_braille("1945년에")["braille"]
    assert ko_engine.braille_to_text(ko_engine.text_to_braille("5동안")["braille"]) == "5 동안"
    assert ko_engine.braille_to_text(ko_engine.text_to_braille("5동")["braille"]) == "5동"
    assert ko_engine.braille_to_text(ko_engine.text_to_braille("5동에")["braille"]) == "5동에"
    assert ko_engine.braille_to_text(ko_engine.text_to_braille("5동에서")["braille"]) == "5동에서"
    assert ko_engine.braille_to_text(ko_engine.text_to_braille("5미터가")["braille"]) == "5미터가"
    assert ko_engine.braille_to_text(ko_engine.text_to_braille("1945년에")["braille"]) == "1945년에"
    assert ko_val_units.check_number_letter_collision("5동안")
    assert not ko_val_units.check_number_letter_collision("5동")
    assert not ko_val_units.check_number_letter_collision("5동에")
    assert not ko_val_units.check_number_letter_collision("1945년에")
    assert not ko_val_units.check_number_letter_collision("제2차 세계대전은 1945년에 끝났다. 5월 12일 3미터 앞.")

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

    apostrophe = marks_data["connectors_and_symbols"]["items"]["'"]["unicode"]
    assert ko_engine.text_to_braille("'")["braille"] == apostrophe
    assert ko_engine.geot_spell_out == {"껐"}
    assert ko_engine.text_to_braille("껏")["braille"] == ko_engine.TENSER_SIGN + ko_engine.geot_unicode
    assert ko_engine.TENSER_SIGN + ko_engine.geot_unicode not in ko_engine.text_to_braille("껐")["braille"]
    so_abbr = ko_data["abbreviation_word"]["items"]["그래서"]["unicode"]
    assert ko_engine.text_to_braille("그래서")["braille"] == so_abbr
    assert so_abbr not in ko_engine.text_to_braille("그래서는")["braille"]
    assert so_abbr not in ko_engine.text_to_braille("아그래서")["braille"]
    assert " " in ko_engine.text_to_braille("7운")["braille"]
    assert {"7", "운", "g"} <= {sense["text"] for sense in ko_engine.rev_uses["⠛"]}
    assert "cm" in {sense["text"] for sense in ko_engine.rev_uses["⠉⠍"]}

    roundtrip_words = [
        "라", "간", "차", "좋", "사람", "1,000", "4사분기", "사이",
        "그래서", "그래서.", "(그래서)", "그러나", "그래서는", "아그래서",
        "값", "앉", "않", "닭", "흙", "밖", "여덟",
        "왜", "외", "웨", "위", "얘", "귀", "돼",
        "껏", "껐", "성", "썽", "정", "청", "셩", "쳥",
        "떠", "뻐", "쩌", "써", "꺼", "빠", "싸",
        "1년", "2월", "3미터", "5명", "8호", "1945년", "1,000명", "2킬로미터",
        "5개", "7 운", "12km", "1/2", "3.14",
        "것.", "<tn>주</tn>",
    ]
    for word in roundtrip_words:
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
    assert {sense["text"] for sense in en_engine.rev_groupsign_senses["⠲"]} == {"dis"}
    assert "dd" not in en_engine.contraction_items
    assert "ation" not in en_engine.contraction_items
    assert "ally" not in en_engine.contraction_items
    assert "o'clock" not in en_engine.shortforms_standalone
    assert all(sense.get("context") for sense in en_engine.rev_symbol_senses["⠂"])
    a = en_engine.spelling["a"]
    b = en_engine.spelling["b"]
    d = en_engine.spelling["d"]
    assert en_engine.braille_to_text(a + en_engine.contraction_items["bb"]["unicode"] + a) == "abba"
    assert en_engine.braille_to_text(en_engine.contraction_items["be"]["unicode"] + a) == "bea"
    assert en_engine.braille_to_text(a + en_engine.contraction_items["cc"]["unicode"] + a) == "acca"
    assert en_engine.braille_to_text(en_engine.contraction_items["con"]["unicode"] + a) == "cona"
    assert en_engine.text_to_braille("adda") == a + d + d + a
    assert en_engine.braille_to_text(en_engine.contraction_items["dis"]["unicode"] + a) == "disa"
    assert en_engine.braille_to_text(a + "⠂" + a) == "aea"
    assert en_engine.braille_to_text(a + "⠲") == "a."
    assert en_engine.braille_to_text(a + "⠖") == "a!"
    assert en_engine.braille_to_text(en_engine.num_prefix + a + "⠂" + b) == "1,2"

    assert en_engine.text_to_braille("en") == en_engine.spelling["e"] + en_engine.spelling["n"]
    assert en_engine.shortforms_standalone["oneself"] == "\u2810\u2815\u280b"
    assert en_engine.shortforms_compound["conceive"] == "\u2812\u2809\u2827"
    assert en_engine.shortforms_compound["conceiving"] == "\u2812\u2809\u2827\u281b"
    assert en_engine.terminating_connectors["–"] == "\u2820\u2824"
    for word in ["the", "be", "con", "dis", "enough", "were", "his", "was", "in", "en", "oneself", "conceive", "conceiving", "end"]:
        braille = en_engine.text_to_braille(word)
        back = en_engine.braille_to_text(braille)
        print(f"EN {word} -> {braille} -> {back}")
        assert back == word, (word, braille, back)

    print("Canonical checks passed.")


if __name__ == "__main__":
    test_korean()
    test_english()
    test_canonical_roundtrip()
    test_homograph_conjugation()
