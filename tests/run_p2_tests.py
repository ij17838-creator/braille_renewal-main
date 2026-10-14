import json
import os
import sys

# 저장소 루트를 import 경로에 넣어 어디서 실행해도 engine 패키지를 찾게 한다.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data_paths import find_data_file
from engine.ko.ko_parser import KoreanBrailleEngine
from engine.en.en_parser import BrailleEngine
from engine.ko.ko_syntax_analyzer import BrailleRuleValidator as KoValidator
from engine.en.en_syntax_analyzer import BrailleRuleValidator as EnValidator


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
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    with open(find_data_file("ko.json"), "r", encoding="utf-8") as f:
        ko_data = json.load(f)
    with open(find_data_file("ko_marks.json"), "r", encoding="utf-8") as f:
        marks_data = json.load(f)
    with open(find_data_file("numbers.json"), "r", encoding="utf-8") as f:
        numbers_data = json.load(f)
    with open(find_data_file("ko_number_rules.json"), "r", encoding="utf-8") as f:
        number_rules = json.load(f)
    with open(find_data_file("lexicon_ko.json"), "r", encoding="utf-8") as f:
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
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(find_data_file("ko.json"), "r", encoding="utf-8") as f:
        ko_data = json.load(f)
    with open(find_data_file("ko_marks.json"), "r", encoding="utf-8") as f:
        marks_data = json.load(f)
    with open(find_data_file("numbers.json"), "r", encoding="utf-8") as f:
        numbers_data = json.load(f)
    with open(find_data_file("ko_number_rules.json"), "r", encoding="utf-8") as f:
        number_rules = json.load(f)
    with open(find_data_file("lexicon_ko.json"), "r", encoding="utf-8") as f:
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
        with open(find_data_file(path), "r", encoding="utf-8") as f:
            quiz = json.load(f)
        for item in quiz.get("KO", []):
            text = item.get("target_text", "")
            braille = item.get("target_braille", "")
            if text.startswith("느낌표"):
                assert braille == bang, path
            if text.startswith("마침표"):
                assert braille == period, path
            if text == "4사분기":
                # 제13·14·44항: '사'는 숫자 뒤에서도 약자로 붙여 적는다.
                assert braille == "⠼⠙⠇⠘⠛⠈⠕", path
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

    # 제44항 [다만]: ㄴ·ㄷ·ㅁ·ㅋ·ㅌ·ㅍ·ㅎ으로 시작하는 단위어도 숫자와 띄어 쓴다 (규정 보기: 1년 ⠼⠁ ⠉⠡, 3명 ⠼⠉ ⠑⠻).
    for text in ["5동안", "5동", "5동에", "5미터가", "1945년에"]:
        assert " " in ko_engine.text_to_braille(text)["braille"], text
        assert ko_val_units.check_number_letter_collision(text), text
    assert ko_engine.text_to_braille("1년")["braille"] == "⠼⠁ ⠉⠡"
    assert ko_engine.text_to_braille("3명")["braille"] == "⠼⠉ ⠑⠻"
    assert ko_engine.braille_to_text(ko_engine.text_to_braille("5동")["braille"]) == "5 동"
    # 숫자와 겹치지 않는 첫소리는 붙여 적는다 (규정 보기: 5월 ⠼⠑⠏⠂, 6일 ⠼⠋⠕⠂).
    for text in ["5월", "12일", "5개", "5월에"]:
        assert " " not in ko_engine.text_to_braille(text)["braille"], text
        assert ko_engine.braille_to_text(ko_engine.text_to_braille(text)["braille"]) == text
    assert not ko_val_units.check_number_letter_collision("5월 12일 5개")

    for cell, senses in ko_engine.rev_uses.items():
        if len({sense["text"] for sense in senses}) > 1:
            assert all(sense.get("context") for sense in senses), cell
    assert {"ㅎ", "”"} <= {sense["text"] for sense in ko_engine.rev_uses["⠴"]}
    assert {"“", "?"} <= {sense["text"] for sense in ko_engine.rev_uses["⠦"]}
    assert ko_engine.braille_to_text("⠴") == "”"
    assert ko_engine.braille_to_text("⠦⠫") == "“가"
    # 제49항: 겹·홑화살괄호와 겹·홑낫표는 따옴표와 점형이 다르다.
    assert ko_engine.text_to_braille("《가》")["braille"] == "⠰⠶⠫⠶⠆"
    assert ko_engine.text_to_braille("「가」")["braille"] == "⠐⠦⠫⠴⠂"
    assert ko_engine.braille_to_text("⠦") == "?"
    assert ko_engine.braille_to_text("⠠⠄⠠⠄") == "<tn></tn>"
    # 제57·58항: 숨김표·빠짐표. 여러 개면 ⠸과 ⠇ 사이에 개수만큼 적는다.
    assert ko_engine.text_to_braille("○")["braille"] == "⠸⠴⠇"
    assert ko_engine.text_to_braille("김○○ 씨")["braille"] == "⠈⠕⠢⠸⠴⠴⠇ ⠠⠠⠕"
    assert ko_engine.text_to_braille("□□□")["braille"] == "⠸⠶⠶⠶⠇"
    assert ko_engine.braille_to_text("⠸⠭⠭⠭⠇") == "×××"
    assert ko_engine.braille_to_text("⠤⠤") == "—"
    assert ko_engine.braille_to_text("⠴⠴") == "〃"

    apostrophe = marks_data["connectors_and_symbols"]["items"]["'"]["unicode"]
    assert ko_engine.text_to_braille("'")["braille"] == apostrophe
    assert ko_engine.geot_spell_out == {"껐"}
    assert ko_engine.text_to_braille("껏")["braille"] == ko_engine.TENSER_SIGN + ko_engine.geot_unicode
    assert ko_engine.TENSER_SIGN + ko_engine.geot_unicode not in ko_engine.text_to_braille("껐")["braille"]
    so_abbr = ko_data["abbreviation_word"]["items"]["그래서"]["unicode"]
    assert ko_engine.text_to_braille("그래서")["braille"] == so_abbr
    # 제18항 [붙임]: 약어 뒤에 글자가 붙어도 약어를 쓴다. [다만]: 앞에 붙으면 풀어 적는다.
    assert ko_engine.text_to_braille("그래서는")["braille"].startswith(so_abbr)
    assert so_abbr not in ko_engine.text_to_braille("아그래서")["braille"]
    assert " " in ko_engine.text_to_braille("7운")["braille"]
    assert {"7", "운"} <= {sense["text"] for sense in ko_engine.rev_uses["⠛"]}
    assert "g" in {sense["text"] for sense in ko_engine.rev_uses["⠴⠛⠲"]}
    assert "cm" in {sense["text"] for sense in ko_engine.rev_uses["⠴⠉⠍⠲"]}
    # 제69항: 로마자 단위 기호는 로마자표와 로마자 종료표 사이에 적는다.
    assert ko_engine.text_to_braille("1m는")["braille"] == "⠼⠁⠴⠍⠲⠉⠵"
    # 제43항 [다만]·제47항 [붙임]: 붙임표·빗금 뒤의 숫자에는 수표를 다시 적는다.
    assert ko_engine.text_to_braille("12,1-9")["braille"] == "⠼⠁⠃⠂⠁⠤⠼⠊"
    assert ko_engine.text_to_braille("2/3")["braille"] == "⠼⠃⠸⠌⠼⠉"
    # 제13·14항: '사'는 모음 앞에서도 약자를 쓴다.
    assert ko_engine.text_to_braille("사이")["braille"] == "⠇⠕"

    roundtrip_words = [
        "라", "간", "차", "좋", "사람", "1,000", "4사분기", "사이",
        "그래서", "그래서.", "(그래서)", "그러나", "그래서는", "아그래서",
        "값", "앉", "않", "닭", "흙", "밖", "여덟",
        "왜", "외", "웨", "위", "얘", "귀", "돼",
        "껏", "껐", "성", "썽", "정", "청", "셩", "쳥",
        "떠", "뻐", "쩌", "써", "꺼", "빠", "싸",
        "2월", "1,000원", "3시", "5층",
        "얽", "꺾", "넋", "읊다", "끓다", "젊", "외국", "부엌에서", "앞집", "겉보리",
        "5개", "7 운", "12km", "1/2", "3.14",
        "것.", "<tn>주</tn>",
        # 받침 ㅋ·ㅌ·ㅍ·ㅎ과 ! ? . ”는 점형이 같다(제3항, 제49항). 낱말 목록과 따옴표 짝으로 가른다.
        "부엌", "부엌.", "무릎", "바깥", "나뭇잎", "햇볕", "대나무밭", "키읔", "히읗", "앞", "밭",
        "왜?", "네.", "아!", "어디 가?", "내 거.", "“왜?”", "“부엌”", "그는 “앞!” 했다.", "왔다.”",
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
    assert en_engine.braille_to_text(a + "⠂" + a) == "aeaa"
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

    # 같은 점형 여러 뜻 (reports/영어_같은점형_조사.md). 점자는 UEB 규정 예시 그대로.
    shared_cell_cases = [
        ("A.B.", "⠠⠁⠲⠠⠃⠲"),            # 7.1.1 U.S.A.: 마침표로 이어진 글자는 단독이 아님
        ("e.g.", "⠑⠲⠛⠲"),
        ("U.S.A.", "⠠⠥⠲⠠⠎⠲⠠⠁⠲"),
        ("J. S. Bach", "⠰⠠⠚⠲ ⠰⠠⠎⠲ ⠠⠃⠁⠡"),  # 5.2: 1급 점자표가 대문자 표시 앞
        ("Mrs X and Mr O", "⠠⠍⠗⠎ ⠰⠠⠭ ⠯ ⠠⠍⠗ ⠠⠕"),
        ("22b 22B", "⠼⠃⠃⠰⠃ ⠼⠃⠃⠠⠃"),
        ("4.b", "⠼⠙⠲⠰⠃"),               # 6.5.2
        ("4.2", "⠼⠙⠲⠃"),
        ("He said “yes.”", "⠠⠓⠑ ⠎⠙ ⠦⠽⠑⠎⠲⠴"),  # 7.6.7: 낱말 앞 ⠦는 여는 큰따옴표
        ("His dog", "⠠⠦ ⠙⠕⠛"),         # 7.6.10: 단독 ⠠⠦ = His
        ("Was it", "⠠⠴ ⠭"),
        ("(“ ... that is the question.”)", "⠐⠣⠘⠦ ⠲⠲⠲ ⠞ ⠊⠎ ⠮ ⠐⠟⠲⠘⠴⠐⠜"),  # 7.6.8
        ("the ” at the end", "⠮ ⠘⠴ ⠁⠞ ⠮ ⠢⠙"),
        ("(‘ ... that is the question.’)", "⠐⠣⠰⠠⠦ ⠲⠲⠲ ⠞ ⠊⠎ ⠮ ⠐⠟⠲⠠⠴⠐⠜"),  # 7.6.10
        ("the ’ at the end", "⠮ ⠰⠠⠴ ⠁⠞ ⠮ ⠢⠙"),
        # 10.5.1: be·were·his·was는 아래 점 부호(따옴표 포함)에 붙으면 풀어 쓴다
        ("‘His mother owns “his” car.’", "⠠⠦⠠⠓⠊⠎ ⠐⠍ ⠪⠝⠎ ⠦⠓⠊⠎⠴ ⠉⠜⠲⠠⠴"),
        ("“Was that his?”", "⠦⠠⠺⠁⠎ ⠞ ⠓⠊⠎⠦⠴"),
        ("“Be safe.”", "⠦⠠⠃⠑ ⠎⠁⠋⠑⠲⠴"),
        ("That was right!", "⠠⠞ ⠴ ⠐⠗⠖"),
        ("at my (not his) house", "⠁⠞ ⠍⠽ ⠐⠣⠝ ⠦⠐⠜ ⠓⠳⠎⠑"),
        ("He is [was]; they are [were].", "⠠⠓⠑ ⠊⠎ ⠨⠣⠺⠁⠎⠨⠜⠆ ⠮⠽ ⠜⠑ ⠨⠣⠺⠻⠑⠨⠜⠲"),
        ("Be good.", "⠠⠆ ⠛⠙⠲"),
    ]
    for text, expected in shared_cell_cases:
        braille = en_engine.text_to_braille(text)
        back = en_engine.braille_to_text(braille)
        print(f"EN {text} -> {braille} -> {back}")
        assert braille == expected, (text, braille, expected)
        assert back == text, (text, braille, back)

    # UEB에서 가져온 영어 묶음은 영어 단원에서만 쓴다 (중연 결정, 2026-10-14).
    with open(find_data_file("curriculum.json"), "r", encoding="utf-8") as f:
        curriculum = json.load(f)
    ueb_bundles = {"en_spell.json", "en_shortform.json", "en_contractions.json", "ueb_number_rules.json", "en_contraction_rules.json"}
    for unit in curriculum["units"]:
        if unit.get("lang") == "en":
            continue
        for item in (unit.get("source") or {}).get("slices", []):
            assert item.get("bundle") not in ueb_bundles, (unit["id"], item.get("bundle"))
            assert (item.get("prefix") or {}).get("bundle") not in ueb_bundles, unit["id"]

    print("Canonical checks passed.")


def test_en_contraction_rules():
    """en_contraction_rules.json: UEB 약어·약자·축어 사용 규칙과 예외 목록 (영어 단원 전용)."""
    print("\n=== UEB contraction rule catalog ===")
    with open(find_data_file("en_contraction_rules.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    rules = data["rules"]
    ids = [rule["id"] for rule in rules]
    assert len(ids) == len(set(ids)), "규칙 번호가 겹침"
    assert data["summary"]["total"] == len(rules)
    for rule in rules:
        assert rule["status"] in data["statuses"], rule["id"]
        assert rule["kind"] in data["kinds"], rule["id"]
        assert rule["group"] in data["groups"], rule["id"]
        assert 41 <= rule["pdf_page"] <= 285, rule["id"]
        assert rule["text"].strip(), rule["id"]
    # 한글 규정집 제37항·[붙임]은 ko_rules.json에 있으므로 이 목록에 다시 넣지 않는다.
    with open(find_data_file("ko_rules.json"), "r", encoding="utf-8") as f:
        ko_ids = {rule["id"] for rule in json.load(f)["rules"]}
    for item in data["excluded_korean_overlap"]:
        assert item["see"].split("#")[1] in ko_ids, item
    # 목록일 뿐이므로 점역기는 이 파일을 읽지 않는다 (점역 결과가 바뀌지 않음).
    engine_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine")
    for root, _, files in os.walk(engine_dir):
        for name in files:
            if name.endswith(".py"):
                with open(os.path.join(root, name), encoding="utf-8") as handle:
                    assert "en_contraction_rules" not in handle.read(), name
    print(f"{len(rules)} rules checked.")


# UEB 약자 규칙 고치기 (중연 허락 2026-10-14). 기대값은 모두 UEB 본문 예시.
UEB_CONTRACTION_CASES = [
    # 1묶음: 축어로 잘못 읽히지 않게 (UEB 10.9.6~10.9.9, 5.7.2, 10.8.1)
    ("al dente", "⠰⠁⠇ ⠙⠢⠞⠑"),
    ("“Hm, is this Al's CD?”", "⠦⠰⠠⠓⠍⠂ ⠊⠎ ⠹ ⠰⠠⠁⠇⠄⠎ ⠰⠠⠠⠉⠙⠦⠴"),
    ("Use the ALT key.", "⠠⠥⠎⠑ ⠮ ⠰⠠⠠⠁⠇⠞ ⠅⠑⠽⠲"),
    ("My friends are Fr Ted and Sr Ann.", "⠠⠍⠽ ⠋⠗⠎ ⠜⠑ ⠰⠠⠋⠗ ⠠⠞⠫ ⠯ ⠠⠎⠗ ⠠⠁⠝⠝⠲"),
    ("the Imm family", "⠮ ⠰⠠⠊⠍⠍ ⠋⠁⠍⠊⠇⠽"),
    ("Herf gun", "⠠⠓⠑⠗⠋ ⠛⠥⠝"),
    ("Blvd", "⠰⠠⠃⠇⠧⠙"),
    ("LLC", "⠰⠠⠠⠇⠇⠉"),
    ("llama", "⠇⠇⠁⠍⠁"),
    ("Grtsamada", "⠰⠠⠛⠗⠞⠎⠁⠍⠁⠙⠁"),
    ("ozbrl", "⠰⠰⠕⠵⠃⠗⠇"),
    ("Dobrljin", "⠰⠰⠠⠙⠕⠃⠗⠇⠚⠊⠝"),
    ("CD-ROM", "⠰⠠⠠⠉⠙⠤⠠⠠⠗⠕⠍"),
    ("3 yrs 6 mths", "⠼⠉ ⠰⠽⠗⠎ ⠼⠋ ⠍⠹⠎"),
    ("enceinte", "⠢⠉⠑⠔⠞⠑"),
    ("lessee", "⠇⠑⠎⠎⠑⠑"),
    # 2묶음: 모음·y 앞의 bl은 blind가 아니다 (UEB 10.9.3)
    ("blunder", "⠃⠇⠥⠝⠙⠻"),
    ("blowhard", "⠃⠇⠪⠓⠜⠙"),
    ("Blakeney", "⠠⠃⠇⠁⠅⠢⠑⠽"),
    ("Blindoc", "⠠⠃⠇⠔⠙⠕⠉"),
    # 3묶음: ing·be·con·dis 위치 (UEB 10.4.3, 10.6.1, 10.6.2, 10.6.4)
    ("ingot", "⠔⠛⠕⠞"),
    ("Smith–Inge", "⠠⠎⠍⠊⠹⠠⠤⠠⠔⠛⠑"),
    ("concave/convex", "⠒⠉⠁⠧⠑⠸⠌⠉⠕⠝⠧⠑⠭"),
    ("www.living.beyond.myself.org", "⠺⠺⠺⠲⠇⠊⠧⠬⠲⠃⠑⠽⠕⠝⠙⠲⠍⠽⠎⠑⠇⠋⠲⠕⠗⠛"),
    ("be'ave", "⠃⠑⠄⠁⠧⠑"),
    ("dis'armony", "⠙⠊⠎⠄⠜⠍⠕⠝⠽"),
    ("m'lord", "⠍⠄⠐⠇"),
    ("'e 'as", "⠄⠰⠑ ⠄⠵"),
    ("best", "⠃⠑⠌"),
    ("been", "⠃⠑⠢"),
    ("better", "⠃⠑⠞⠞⠻"),
    ("begging", "⠃⠑⠶⠬"),
    ("conch", "⠉⠕⠝⠡"),
    ("disc", "⠙⠊⠎⠉"),
    ("dishevel", "⠙⠊⠩⠑⠧⠑⠇"),
    ("Conestoga", "⠠⠒⠑⠌⠕⠛⠁"),
    ("Belg", "⠠⠃⠑⠇⠛"),
    ("Bev", "⠠⠃⠑⠧"),
    ("cont", "⠒⠞"),
    ("Beethoven", "⠠⠃⠑⠑⠹⠕⠧⠢"),
    ("become", "⠆⠉⠕⠍⠑"),
    # 4묶음: 낱말 안 대문자·곧은 큰따옴표 (UEB 10.6.3, 10.6.6, 10.8.2, 10.9.4, 10.12.12)
    ("McConnell", "⠠⠍⠉⠠⠉⠕⠝⠝⠑⠇⠇"),
    ("O'Connor", "⠠⠕⠄⠠⠉⠕⠝⠝⠕⠗"),
    ("MetroDisco", "⠠⠍⠑⠞⠗⠕⠠⠙⠊⠎⠉⠕"),
    ("BeLinda", "⠠⠃⠑⠠⠇⠔⠙⠁"),
    ("conCUR", "⠉⠕⠝⠠⠠⠉⠥⠗"),
    ("DISlike", "⠠⠠⠙⠊⠎⠠⠄⠇⠊⠅⠑"),
    ("BEd", "⠠⠃⠠⠫"),
    ("SeaWorld", "⠠⠎⠑⠁⠠⠸⠺"),
    ("TEAspoon", "⠠⠠⠞⠑⠁⠠⠄⠎⠏⠕⠕⠝"),
    ("AttenTION!", "⠠⠁⠞⠞⠢⠠⠠⠞⠊⠕⠝⠖"),
    ("ELesson", "⠠⠑⠠⠇⠑⠎⠎⠕⠝"),
    ("QuickTime", "⠠⠟⠅⠠⠐⠞"),
    ("GREATgreatGrandChildren", "⠠⠠⠛⠗⠞⠠⠄⠛⠗⠞⠠⠛⠗⠯⠠⠡⠝"),
    ("GodChildren's", "⠠⠛⠕⠙⠠⠡⠝⠄⠎"),
    ("StepChildren.org", "⠠⠌⠑⠏⠠⠡⠊⠇⠙⠗⠢⠲⠕⠗⠛"),
    ("PenFriend", "⠠⠏⠢⠠⠋⠗⠊⠢⠙"),
    ("FirstAmerica", "⠠⠋⠊⠗⠌⠠⠁⠍⠻⠊⠉⠁"),
    ("HANDsome", "⠠⠠⠓⠯⠠⠄⠐⠎"),
    ("founDAtion", "⠋⠳⠝⠠⠙⠠⠁⠰⠝"),
    ("verY", "⠧⠻⠠⠽"),
    ("“Belinda!”", "⠦⠠⠆⠇⠔⠙⠁⠖⠴"),
]


def test_en_ueb_contraction_fixes():
    print("\n=== UEB contraction fixes ===")
    engine = BrailleEngine()
    for text, expected in UEB_CONTRACTION_CASES:
        braille = engine.text_to_braille(text)
        back = engine.braille_to_text(braille)
        print(f"EN {text} -> {braille} -> {back}")
        assert braille == expected, (text, braille, expected)
        assert back == text, (text, braille, back)


if __name__ == "__main__":
    test_korean()
    test_english()
    test_canonical_roundtrip()
    test_homograph_conjugation()
    test_en_contraction_rules()
    test_en_ueb_contraction_fixes()
