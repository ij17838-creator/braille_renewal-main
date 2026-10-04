# -*- coding: utf-8 -*-
"""불규칙 활용, 다의어, 단위 경계, 닫는 따옴표·낫표 변경에 대한 단위 테스트."""

import json
import os
import unittest

from ko_parser import KoreanBrailleEngine
from ko_syntax_analyzer import BrailleRuleValidator


ROOT = os.path.dirname(os.path.abspath(__file__))


def load_engine():
    with open(os.path.join(ROOT, "ko.json"), encoding="utf-8") as handle:
        ko_data = json.load(handle)
    with open(os.path.join(ROOT, "ko_marks.json"), encoding="utf-8") as handle:
        marks_data = json.load(handle)
    with open(os.path.join(ROOT, "numbers.json"), encoding="utf-8") as handle:
        numbers_data = json.load(handle)
    with open(os.path.join(ROOT, "ko_number_rules.json"), encoding="utf-8") as handle:
        number_rules = json.load(handle)
    with open(os.path.join(ROOT, "lexicon_ko.json"), encoding="utf-8") as handle:
        lexicon_data = json.load(handle)
    return KoreanBrailleEngine(ko_data, marks_data, numbers_data, number_rules, lexicon_data)


class ConjugationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = BrailleRuleValidator(data_dir=ROOT)

    def conjugate(self, stem, eomi, **options):
        return self.validator.analyze_conjugation_form(stem, eomi, **options)


class TestIrregularAndRegularConjugation(ConjugationTestCase):
    def test_kkeedatda_is_digeut_irregular(self):
        result = self.conjugate("깨닫", "아")
        self.assertEqual(result["surface_form"], "깨달아")
        self.assertEqual(result["rule_applied"], "ㄷ 불규칙")
        self.assertNotEqual(result["surface_form"], "깨닫아")

    def test_eodda_stays_regular(self):
        result = self.conjugate("얻", "어")
        self.assertEqual(result["surface_form"], "얻어")
        self.assertNotEqual(result["surface_form"], "얼어")
        self.assertEqual(result["rule_applied"], "규칙 결합")
        self.assertNotEqual(result["rule_applied"], "ㄷ 불규칙")

    def test_jip_ssip_jeop_stay_regular(self):
        expected = {
            ("집", "어"): "집어",
            ("집", "으면"): "집으면",
            ("씹", "어"): "씹어",
            ("씹", "으면"): "씹으면",
            ("접", "어"): "접어",
            ("접", "으면"): "접으면",
        }
        irregular = {
            ("집", "어"): "지워",
            ("씹", "어"): "씨워",
            ("접", "어"): "저워",
        }
        for (stem, eomi), surface in expected.items():
            with self.subTest(stem=stem, eomi=eomi):
                result = self.conjugate(stem, eomi)
                self.assertEqual(result["surface_form"], surface)
                self.assertEqual(result["rule_applied"], "규칙 결합")
                self.assertNotEqual(result["rule_applied"], "ㅂ 불규칙")
                if (stem, eomi) in irregular:
                    self.assertNotEqual(result["surface_form"], irregular[(stem, eomi)])

    def test_dopda_gopda_use_positive_o(self):
        cases = {
            ("돕", "아"): "도와",
            ("곱", "아"): "고와",
        }
        for (stem, eomi), surface in cases.items():
            with self.subTest(stem=stem, eomi=eomi):
                result = self.conjugate(stem, eomi)
                self.assertEqual(result["surface_form"], surface)
                self.assertEqual(result["rule_applied"], "ㅂ 불규칙")
                self.assertIn("와", result["surface_form"])

        self.assertNotEqual(self.conjugate("돕", "아")["surface_form"], "도워")
        self.assertNotEqual(self.conjugate("곱", "아")["surface_form"], "구워")
        self.assertEqual(self.conjugate("돕", "으면")["surface_form"], "도우면")
        self.assertEqual(self.conjugate("곱", "으면")["surface_form"], "고우면")


class TestPolysemousIreuda(ConjugationTestCase):
    def test_arrive_sense_uses_reo(self):
        by_meaning = self.conjugate("이르", "어", meaning="arrive")
        by_sense = self.conjugate("이르", "어", sense_id="ireu-arrive")
        by_context = self.conjugate("이르", "어", context="도착하다")
        for result in (by_meaning, by_sense, by_context):
            self.assertEqual(result["surface_form"], "이르러")
            self.assertEqual(result["rule_applied"], "러 불규칙")
            self.assertFalse(result.get("ambiguous"))

    def test_tell_sense_uses_reu(self):
        by_meaning = self.conjugate("이르", "어", meaning="tell")
        by_sense = self.conjugate("이르", "아", sense_id="ireu-tell")
        by_tag = self.conjugate("이르", "어서", tag="말하다")
        self.assertEqual(by_meaning["surface_form"], "일러")
        self.assertEqual(by_meaning["rule_applied"], "르 불규칙")
        self.assertEqual(by_sense["surface_form"], "일러")
        self.assertEqual(by_tag["surface_form"], "일러서")
        self.assertFalse(by_meaning.get("ambiguous"))

    def test_missing_sense_keeps_both_candidates(self):
        result = self.conjugate("이르", "어")
        self.assertTrue(result["ambiguous"])
        self.assertIsNone(result["surface_form"])
        self.assertEqual(
            {item["surface_form"] for item in result["candidates"]},
            {"이르러", "일러"},
        )
        self.assertEqual(
            {item["rule_applied"] for item in result["candidates"]},
            {"러 불규칙", "르 불규칙"},
        )


class TestUnitBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = BrailleRuleValidator(data_dir=ROOT)
        cls.engine = load_engine()

    def test_dong_euro_keeps_unit(self):
        self.assertEqual(self.validator._match_exempt_unit("동으로"), "동")
        self.assertEqual(self.engine._match_exempt_unit("동으로"), "동")
        self.assertFalse(self.validator.check_number_letter_collision("5동으로"))

        converted = self.engine.text_to_braille("5동으로")
        self.assertNotIn(" ", converted["braille"])
        self.assertEqual(self.engine.braille_to_text(converted["braille"]), "5동으로")

    def test_dongan_is_not_split_as_unit(self):
        self.assertIsNone(self.validator._match_exempt_unit("동안"))
        self.assertEqual(self.engine._match_exempt_unit("동안"), "")
        self.assertTrue(self.validator.check_number_letter_collision("5동안"))

        converted = self.engine.text_to_braille("5동안")
        self.assertIn(" ", converted["braille"])
        self.assertEqual(self.engine.braille_to_text(converted["braille"]), "5 동안")


class TestClosingQuoteBeforeNatpyo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = BrailleRuleValidator(data_dir=ROOT)
        cls.engine = load_engine()

    def test_quote_then_natpyo_parses_without_error(self):
        text = "《“가”》"
        self.assertIn("”》", text)

        result = self.validator.validate_text(text)
        self.assertTrue(result["is_valid"], result["delimiters"])
        self.assertEqual(result["delimiters"], [])
        self.assertFalse(
            any(issue.get("type") == "PUNCTUATION_CONTEXT" for issue in result["delimiters"])
        )

        converted = self.engine.text_to_braille(text)
        self.assertIsInstance(converted["braille"], str)
        self.assertTrue(converted["braille"])
        restored = self.engine.braille_to_text(converted["braille"])
        self.assertIsInstance(restored, str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
