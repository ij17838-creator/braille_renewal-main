"""
ko_syntax_analyzer.py
한글 점자 문장요소 유효성 검증 및 음운/문맥 결합 규칙 판별기.

판정 기준은 ko.json, ko_marks.json, ko_number_rules.json, lexicon_ko.json 이다.
같은 어간 철자에 활용이 둘이면 lexicon의 meaning, sense_id로 가른다.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple, TypedDict, Union

from data_paths import find_data_file, resolve_data_root


class LexicalStemEntry(TypedDict):
    """example_stems 항목. meaning과 sense_id는 같은 base를 뜻별로 가를 때만 쓴다."""

    base: str


class LexicalStemSense(LexicalStemEntry, total=False):
    vowel_trigger: str
    transformed: str
    example: str
    meaning: str
    sense_id: str
    aliases: List[str]


class ContrastingExample(TypedDict):
    """contrasting_rules.examples 항목. 의미 필드는 선택이다."""

    base: str


class ContrastingExampleSense(ContrastingExample, total=False):
    example: str
    meaning: str
    sense_id: str
    aliases: List[str]


StemSenseEntry = Union[LexicalStemSense, ContrastingExampleSense]


class BrailleRuleValidator:
    # 한글 유니코드 기본 자모 테이블
    CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    JUNGSUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
    JONGSUNG_LIST = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = resolve_data_root(data_dir)

        self.ko_data = self._load_json("ko.json")
        self.marks_data = self._load_json("ko_marks.json")
        self.number_rules = self._load_json("ko_number_rules.json")
        self.numbers_data = self._load_json("numbers.json")
        self.lexicon = self._load_json("lexicon_ko.json")

        self._init_rules()

    def _load_json(self, filename: str) -> Dict[str, Any]:
        path = find_data_file(filename, self.data_dir)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _init_rules(self):
        self._init_number_rules()
        self._init_mark_rules()
        self._init_abbreviation_rules()
        self._init_conjugation_rules()

    def _init_number_rules(self):
        number_prefix_rule = self.ko_data.get("special_rules", {}).get("number_prefix_rule", {})
        self.affected_initials = set(number_prefix_rule.get("affected_initials", []))
        self.affected_abbreviations = set(number_prefix_rule.get("affected_abbreviations", []))

        trailing = (
            self.number_rules.get("collision_resolutions", {})
            .get("trailing_letters", {})
        )
        self.exempt_units = set(trailing.get("exempt_units", []))
        self.exempt_units_sorted = tuple(sorted(self.exempt_units, key=len, reverse=True))
        boundary = trailing.get("unit_boundary", {})
        self.unit_boundary_enabled = bool(boundary.get("enabled", False))
        self.josa_sorted = tuple(
            sorted({item for item in boundary.get("josa", []) if item}, key=len, reverse=True)
        )

        self.roman_unit_symbols = trailing.get("roman_unit_symbols", {})
        self.roman_units_sorted = tuple(sorted(self.roman_unit_symbols.keys(), key=len, reverse=True))

        self.numeric_connectors = set()
        for item in self.number_rules.get("symbols", {}).values():
            char = item.get("char")
            if char and item.get("persists_numeric_mode"):
                self.numeric_connectors.add(char)

    def _init_mark_rules(self):
        """ko_marks.json의 짝과 앞뒤 자리 규칙을 읽는다."""
        opens = self.marks_data.get("opening_delimiters", {}).get("items", {})
        closes = self.marks_data.get("closing_delimiters", {}).get("items", {})
        close_by_label = {}
        for ch, item in closes.items():
            label = str(item.get("word", "")).replace("닫는", "").strip()
            close_by_label[label] = ch

        self.bracket_pairs = {}
        for ch, item in opens.items():
            label = str(item.get("word", "")).replace("여는", "").strip()
            if label in close_by_label:
                self.bracket_pairs[ch] = close_by_label[label]
        if len(self.bracket_pairs) != len(opens) and len(opens) == len(closes):
            self.bracket_pairs = {op: cl for op, cl in zip(opens, closes)}

        self.tag_pairs = {}
        tag_items = self.marks_data.get("transcriber_and_formatting_tags", {}).get("items", {})
        for tag, item in tag_items.items():
            if item.get("pairRole") == "open" and item.get("matchingTag"):
                self.tag_pairs[tag] = item["matchingTag"]

        self.char_kinds = {}
        for ch, item in opens.items():
            self.char_kinds[ch] = _delimiter_kind(item.get("word", ""), opening=True)
        for ch, item in closes.items():
            self.char_kinds[ch] = _delimiter_kind(item.get("word", ""), opening=False)

        self.mark_context = {}
        for category in ("terminal_punctuation", "pausal_punctuation", "opening_delimiters", "closing_delimiters"):
            block = self.marks_data.get(category, {})
            rule = block.get("rule", {})
            for ch in block.get("items", {}):
                self.mark_context[ch] = {
                    "category": category,
                    "preceded_by": set(rule.get("precededBy", [])),
                    "followed_by": set(rule.get("followedBy", [])),
                    "allow_space_after": rule.get("allowSpaceAfter", True),
                    "allow_space_before": rule.get("allowSpaceBefore", True),
                    "requires_whitespace_after": bool(rule.get("requiresWhitespaceAfter", False)),
                }
            if category == "terminal_punctuation":
                self.char_kinds.update({ch: "terminal_punctuation" for ch in block.get("items", {})})
            elif category == "pausal_punctuation":
                self.char_kinds.update({ch: "pausal_punctuation" for ch in block.get("items", {})})

    def _init_abbreviation_rules(self):
        syllable_items = self.ko_data.get("abbreviation_syllable", {}).get("items", {})
        word_block = self.ko_data.get("abbreviation_word", {})
        self.word_abbrs = list(word_block.get("items", {}).keys())
        self.word_abbrs.sort(key=len, reverse=True)
        self.word_abbr_standalone = word_block.get("rule", {}).get("position") == "standalone"

        sa = syllable_items.get("사", {})
        sa_rules = sa.get("exception_rules", {})
        self.sa_after_number = "after_number" in sa_rules
        self.sa_before_vowel = "vowel_connection" in sa_rules
        self.sa_spell_out = sa.get("expanded_unicode", "")

        yeong = syllable_items.get("영", {})
        override = yeong.get("initial_vowel_override") or {}
        self.yeong_initials = set(override.get("initials", []))
        self.yeong_surface_vowel = override.get("surface_vowel", "")
        self.yeong_surface_jong = override.get("surface_jong", "")
        yeong_parts = self.decompose("영")
        self.yeong_spell_jung = yeong_parts[1] if yeong_parts else "ㅕ"

        geot = syllable_items.get("것", {})
        self.geot_spell_out = self._geot_spell_out_syllables(geot)

        keep_a = self.ko_data.get("abbreviation_syllable", {}).get("rule", {}).get("keep_a", {})
        keep_vowel = keep_a.get("vowel_connection", {})
        self.keep_a_onsets = {p[0] for p in map(self.decompose, keep_vowel.get("syllables", [])) if p}
        if keep_vowel.get("include_tensed"):
            tensers = self._load_tenser_map()
            self.keep_a_onsets |= {t for t, base in tensers.items() if base in self.keep_a_onsets}
        self.keep_a_spell_out = set(keep_a.get("spell_out", {}))

    def _load_tenser_map(self) -> Dict[str, str]:
        """초성 점형이 ⠠ + 기본 자음이면 된소리로 읽는다."""
        items = self.ko_data.get("chosung", {}).get("items", {})
        sign = "⠠"
        plain = {}
        tensed = {}
        for char, item in items.items():
            uni = item.get("unicode") or ""
            if item.get("isOmitted") or not uni:
                continue
            if uni.startswith(sign) and uni != sign:
                tensed[char] = uni[len(sign):]
            else:
                plain[uni] = char
        mapping = {}
        for char, base_uni in tensed.items():
            base = plain.get(base_uni)
            if base:
                mapping[char] = base
        return mapping

    def _geot_spell_out_syllables(self, geot: dict) -> set:
        """'껐'은 것 약자에 된소리표를 붙이지 않고 꺼 뒤에 받침 ㅆ을 적는다."""
        if not geot.get("ssang_jong_exception"):
            return set()
        parts = self.decompose("것")
        if not parts:
            return set()
        rev = {base: char for char, base in self._load_tenser_map().items()}
        tense_cho = rev.get(parts[0])
        if not tense_cho:
            return set()
        return {self.compose(tense_cho, parts[1], "ㅆ")}

    def _init_conjugation_rules(self):
        self.irregular_rules = self.lexicon.get("irregular_rules", {})
        eu = (self.irregular_rules.get("eu_drop", {}).get("transformation", {}) or {})
        harmony = eu.get("vowel_harmony_determined_by", "")
        self.yang_vowels, self.yang_jung, self.eum_jung = _parse_vowel_harmony(harmony)

        hieut = self.irregular_rules.get("hieut", {})
        h_text = (hieut.get("transformation", {}) or {}).get("with_ah_uh_vowel", "")
        self.hieut_vowel_map = _parse_hieut_vowel_map(h_text)

        rieul = self.irregular_rules.get("rieul_drop", {}).get("trigger_condition", {}) or {}
        self.rieul_drop_before = set(rieul.get("rieul_drops_before", []))

    @classmethod
    def decompose(cls, char: str) -> Optional[Tuple[str, str, str]]:
        """한글 음절(가~힣)을 초성, 중성, 종성으로 분해"""
        if not char:
            return None
        code = ord(char) - 0xAC00
        if 0 <= code <= 11171:
            cho = code // (21 * 28)
            jung = (code % (21 * 28)) // 28
            jong = code % 28
            return cls.CHOSUNG_LIST[cho], cls.JUNGSUNG_LIST[jung], cls.JONGSUNG_LIST[jong]
        return None

    @classmethod
    def compose(cls, cho: str, jung: str, jong: str = "") -> str:
        """초성, 중성, 종성을 조합하여 완성형 한글 음절 반환"""
        cho_idx = cls.CHOSUNG_LIST.index(cho)
        jung_idx = cls.JUNGSUNG_LIST.index(jung)
        jong_idx = cls.JONGSUNG_LIST.index(jong) if jong else 0
        return chr(0xAC00 + (cho_idx * 21 + jung_idx) * 28 + jong_idx)

    def _match_prefix(self, text: str, candidates: Tuple[str, ...]) -> Optional[str]:
        for item in candidates:
            if item and text.startswith(item):
                return item
        return None

    def _unit_boundary_ok(self, after: str) -> bool:
        """단위 직후가 경계이거나 조사일 때만 참이다. 그 외 한글이 이어지면 단위가 아니다."""
        if not self.unit_boundary_enabled:
            return True
        if not after:
            return True
        head = after[0]
        if not ("가" <= head <= "힣"):
            return True
        return any(after.startswith(josa) for josa in self.josa_sorted)

    def _match_exempt_unit(self, tail_text: str) -> Optional[str]:
        """가장 긴 단위 후보 중 경계가 맞는 것만 고른다."""
        for unit in self.exempt_units_sorted:
            if unit and tail_text.startswith(unit) and self._unit_boundary_ok(tail_text[len(unit):]):
                return unit
        return None

    # -------------------------------------------------------------
    # 1. 숫자-한글 음절 충돌 감지
    # -------------------------------------------------------------
    def check_number_letter_collision(self, text: str) -> List[Dict[str, Any]]:
        """
        숫자 바로 뒤에 띄어쓰기 없이 충돌 주의 한글 초성이나 약자가 오면 수표가 끝나지 않은 것으로 본다.
        경계가 맞는 단위어와 로마자 단위 기호는 붙여 적으므로 예외로 둔다.
        단위 후보 직후에 조사가 아닌 한글이 오면 그 후보는 단위가 아니다.
        """
        issues = []
        for i in range(len(text) - 1):
            curr_ch = text[i]
            if not curr_ch.isdigit():
                continue

            tail_text = text[i + 1:]
            if self._match_prefix(tail_text, self.roman_units_sorted):
                continue
            if self._match_exempt_unit(tail_text):
                continue

            next_ch = tail_text[0]
            if not ("가" <= next_ch <= "힣"):
                continue

            decomp = self.decompose(next_ch)
            initial = decomp[0] if decomp else ""
            if next_ch in self.affected_abbreviations or initial in self.affected_initials:
                if next_ch in self.affected_abbreviations:
                    message = f"숫자 '{curr_ch}' 뒤에 약자 '{next_ch}'이 붙어 있어 띄어쓰기가 필요합니다."
                else:
                    message = f"숫자 '{curr_ch}' 뒤에 초성 '{initial}'이(가) 오는 음절 '{next_ch}'이 붙어 있어 띄어쓰기가 필요합니다."
                issues.append({
                    "type": "NUMBER_HANGUL_COLLISION",
                    "index": i + 1,
                    "trigger": f"{curr_ch}{next_ch}",
                    "initial": initial or next_ch,
                    "rule": "띄어쓰기로 숫자 입력 종료",
                    "message": message
                })
        return issues

    # -------------------------------------------------------------
    # 2. 문장부호 및 점역 태그 정합성 검사
    # -------------------------------------------------------------
    def validate_delimiters_and_tags(self, text: str) -> List[Dict[str, Any]]:
        """태그와 괄호의 매칭, 그리고 ko_marks.json의 앞뒤 자리 규칙을 검사한다."""
        errors = []
        stack = []
        tag_spans = _tag_spans(text, self.tag_pairs)

        all_tags = list(self.tag_pairs.keys()) + list(self.tag_pairs.values())
        all_tags.sort(key=len, reverse=True)

        i = 0
        n = len(text)
        while i < n:
            matched_tag = None
            for tag in all_tags:
                if text.startswith(tag, i):
                    matched_tag = tag
                    break

            if matched_tag:
                if matched_tag in self.tag_pairs:
                    stack.append((matched_tag, i))
                elif matched_tag in self.tag_pairs.values():
                    expected_open = None
                    for op, cl in self.tag_pairs.items():
                        if cl == matched_tag:
                            expected_open = op
                            break

                    if not stack or stack[-1][0] != expected_open:
                        errors.append({
                            "type": "UNMATCHED_TAG",
                            "index": i,
                            "tag": matched_tag,
                            "message": f"열린 '{expected_open}' 태그 없이 닫는 태그 '{matched_tag}'가 사용되었습니다."
                        })
                    else:
                        stack.pop()

                i += len(matched_tag)
                continue

            ch = text[i]
            if ch in self.mark_context and not self._is_numeric_connector(text, i):
                errors.extend(self._punctuation_context_errors(text, i, tag_spans))

            if ch in self.bracket_pairs:
                stack.append((ch, i))
            elif ch in self.bracket_pairs.values():
                expected_open = None
                for op, cl in self.bracket_pairs.items():
                    if cl == ch:
                        expected_open = op
                        break

                if not stack or stack[-1][0] != expected_open:
                    errors.append({
                        "type": "UNMATCHED_DELIMITER",
                        "index": i,
                        "delimiter": ch,
                        "message": f"여는 부호({expected_open}) 없이 닫는 부호 '{ch}'가 사용되었습니다."
                    })
                else:
                    stack.pop()
            i += 1

        while stack:
            unclosed, pos = stack.pop()
            errors.append({
                "type": "UNCLOSED_ELEMENT",
                "index": pos,
                "element": unclosed,
                "message": f"부호/태그 '{unclosed}'이(가) 닫히지 않은 채 문장이 종료되었습니다."
            })

        return errors

    def _is_numeric_connector(self, text: str, index: int) -> bool:
        ch = text[index]
        if ch not in self.numeric_connectors:
            return False
        prev_ch = text[index - 1] if index else ""
        next_ch = text[index + 1] if index + 1 < len(text) else ""
        return prev_ch.isdigit() and next_ch.isdigit()

    def _punctuation_context_errors(self, text: str, index: int, tag_spans: List[Tuple[int, int]]) -> List[Dict[str, Any]]:
        rule = self.mark_context[text[index]]
        errors = []
        prev_i = _neighbor_index(text, index, -1, tag_spans)
        next_i = _neighbor_index(text, index, 1, tag_spans)
        prev_kind = self._kind_at(text, prev_i, direction=-1)
        next_kind = self._kind_at(text, next_i, direction=1)
        prev_bad = bool(rule["preceded_by"]) and not _kind_allowed(prev_kind, rule["preceded_by"], direction=-1)
        next_bad = bool(rule["followed_by"]) and not _kind_allowed(next_kind, rule["followed_by"], direction=1)

        if prev_bad:
            errors.append({
                "type": "PUNCTUATION_CONTEXT",
                "index": index,
                "delimiter": text[index],
                "message": f"부호 '{text[index]}' 앞의 자리({prev_kind})가 허용된 환경이 아닙니다."
            })
        if next_bad:
            errors.append({
                "type": "PUNCTUATION_CONTEXT",
                "index": index,
                "delimiter": text[index],
                "message": f"부호 '{text[index]}' 뒤의 자리({next_kind})가 허용된 환경이 아닙니다."
            })
        if rule["allow_space_after"] is False and next_kind == "space" and not next_bad:
            errors.append({
                "type": "PUNCTUATION_CONTEXT",
                "index": index,
                "delimiter": text[index],
                "message": f"여는 부호 '{text[index]}' 뒤에는 띄어쓰기를 두지 않습니다."
            })
        if rule["allow_space_before"] is False and prev_kind == "space" and not prev_bad:
            errors.append({
                "type": "PUNCTUATION_CONTEXT",
                "index": index,
                "delimiter": text[index],
                "message": f"닫는 부호 '{text[index]}' 앞에는 띄어쓰기를 두지 않습니다."
            })
        return errors

    def _kind_at(self, text: str, index: int, direction: int) -> str:
        if index < 0:
            return "start_of_line"
        if index >= len(text):
            return "end_of_line"
        ch = text[index]
        if ch in " \t":
            return "space"
        if ch in "\n\r":
            return "end_of_line" if direction > 0 else "start_of_line"
        if ch.isdigit():
            return "number"
        if ("가" <= ch <= "힣") or ch in self.CHOSUNG_LIST or ch in self.JUNGSUNG_LIST:
            return "hangul"
        if ch.isascii() and ch.isalpha():
            return "alphabetic"
        return self.char_kinds.get(ch, "other")

    # -------------------------------------------------------------
    # 3. 약자 예외 (풀어 적어야 하는 충돌)
    # -------------------------------------------------------------
    def check_abbreviation_constraints(self, text: str) -> List[Dict[str, Any]]:
        """약자를 쓰면 안 되는 자리를 찾는다. 본문 자체가 틀린 것은 아니므로 유효성 실패로는 세지 않는다."""
        notes = []
        if self.word_abbr_standalone:
            notes.extend(self._standalone_word_notes(text))

        for i, ch in enumerate(text):
            if ch == "사":
                notes.extend(self._sa_notes(text, i))
            keep_a = self._keep_a_note(text, i)
            if keep_a:
                notes.append(keep_a)
            spelled = self._yeong_spell_out_note(ch, i)
            if spelled:
                notes.append(spelled)
            if ch in self.geot_spell_out:
                notes.append({
                    "type": "ABBREVIATION_SPELL_OUT",
                    "index": i,
                    "token": ch,
                    "rule": "ssang_jong_exception",
                    "message": f"'{ch}'은 것 약자를 쓰지 않고 풀어 적습니다."
                })
        return notes

    def _standalone_word_notes(self, text: str) -> List[Dict[str, Any]]:
        notes = []
        i = 0
        n = len(text)
        while i < n:
            matched = self._match_prefix(text[i:], self.word_abbrs)
            if not matched:
                i += 1
                continue
            prev_c = text[i - 1] if i else ""
            next_i = i + len(matched)
            next_c = text[next_i] if next_i < n else ""
            attached = ("가" <= prev_c <= "힣") or ("가" <= next_c <= "힣")
            if attached:
                notes.append({
                    "type": "ABBREVIATION_STANDALONE",
                    "index": i,
                    "token": matched,
                    "rule": "standalone",
                    "message": f"단어 약어 '{matched}'은 앞뒤에 한글이 있으면 풀어 적습니다."
                })
            i += len(matched)
        return notes

    def _sa_notes(self, text: str, index: int) -> List[Dict[str, Any]]:
        notes = []
        prev_c = text[index - 1] if index else ""
        if self.sa_after_number and prev_c.isdigit():
            notes.append({
                "type": "ABBREVIATION_SPELL_OUT",
                "index": index,
                "token": "사",
                "rule": "after_number",
                "message": f"숫자 뒤의 '사'는 약자를 쓰지 않고 '{self.sa_spell_out}'으로 풀어 적습니다."
            })
            return notes
        if self.sa_before_vowel and index + 1 < len(text):
            nxt = self.decompose(text[index + 1])
            if nxt and nxt[0] == "ㅇ":
                notes.append({
                    "type": "ABBREVIATION_SPELL_OUT",
                    "index": index,
                    "token": "사",
                    "rule": "vowel_connection",
                    "message": f"'사' 뒤에 모음이 이어지면 약자를 쓰지 않고 '{self.sa_spell_out}'으로 풀어 적습니다."
                })
        return notes

    def _keep_a_note(self, text: str, index: int) -> Optional[Dict[str, Any]]:
        ch = text[index]
        if ch in self.keep_a_spell_out:
            return {
                "type": "ABBREVIATION_SPELL_OUT",
                "index": index,
                "token": ch,
                "rule": "keep_a_spell_out",
                "message": f"'{ch}'은 ㅏ를 생략하지 않고 적습니다."
            }
        parts = self.decompose(ch)
        if not parts or parts[1] != "ㅏ" or parts[2] or parts[0] not in self.keep_a_onsets:
            return None
        nxt = self.decompose(text[index + 1]) if index + 1 < len(text) else None
        if not nxt or nxt[0] != "ㅇ":
            return None
        return {
            "type": "ABBREVIATION_SPELL_OUT",
            "index": index,
            "token": ch,
            "rule": "keep_a_vowel_connection",
            "message": f"'{ch}' 뒤에 모음이 이어지면 약자를 쓰지 않고 ㅏ를 적습니다."
        }

    def _yeong_spell_out_note(self, ch: str, index: int) -> Optional[Dict[str, Any]]:
        if not self.yeong_initials:
            return None
        parts = self.decompose(ch)
        if not parts:
            return None
        cho, jung, jong = parts
        if cho not in self.yeong_initials or jong != self.yeong_surface_jong:
            return None
        if jung != self.yeong_spell_jung or jung == self.yeong_surface_vowel:
            return None
        return {
            "type": "ABBREVIATION_SPELL_OUT",
            "index": index,
            "token": ch,
            "rule": "initial_vowel_override",
            "message": f"'{ch}'은 '영' 약자를 쓰지 않고 풀어 적습니다."
        }

    # -------------------------------------------------------------
    # 4. 불규칙 활용 어간 결합 판별
    # -------------------------------------------------------------
    def analyze_conjugation_form(
        self,
        stem: str,
        eomi: str,
        *,
        meaning: Optional[str] = None,
        sense_id: Optional[str] = None,
        context: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """어간(stem)과 어미(eomi) 결합 시 불규칙/규칙 변동 판정.

        같은 base에 활용이 둘이면 meaning, sense_id, context, tag로 하나를 고른다.
        단서가 없으면 candidates에 후보를 함께 돌려준다.
        """
        if not stem:
            return {"rule_applied": "입력 오류", "surface_form": eomi, "braille_instruction": ""}

        selectors = self._sense_selectors(meaning, sense_id, context, tag)
        decomp_last = self.decompose(stem[-1]) if "가" <= stem[-1] <= "힣" else None
        if decomp_last:
            for checker in (
                self._apply_hieut,
                self._apply_digeut,
                self._apply_bieup,
                self._apply_siot,
                self._apply_yeo,
                self._apply_reu,
                self._apply_eu_drop,
                self._apply_rieul_drop,
            ):
                result = checker(stem, eomi, decomp_last, selectors)
                if result:
                    return result

        return {
            "rule_applied": "규칙 결합",
            "surface_form": f"{stem}{eomi}",
            "braille_instruction": "기본 음소 및 약자 규칙 적용"
        }

    def _exception_bases(self, rule_name: str) -> List[str]:
        rule = self.irregular_rules.get(rule_name, {})
        found = []
        found.extend(rule.get("regular_exceptions") or [])
        found.extend((rule.get("transformation") or {}).get("regular_exceptions") or [])
        return [item.get("base", "") for item in found if item.get("base")]

    def _is_regular_exception(self, stem: str, rule_name: str) -> bool:
        return any(stem == base or stem.endswith(base) for base in self._exception_bases(rule_name))

    def _vowel_onset(self, eomi: str) -> Optional[Tuple[str, str, str]]:
        """어미가 모음으로 시작하면 (중성, 그 음절의 종성, 나머지)를 돌려준다."""
        if not eomi:
            return None
        ch = eomi[0]
        if ch in self.JUNGSUNG_LIST:
            return ch, "", eomi[1:]
        parts = self.decompose(ch) if "가" <= ch <= "힣" else None
        if parts and parts[0] == "ㅇ":
            return parts[1], parts[2], eomi[1:]
        return None

    def _sense_selectors(self, *values: Optional[str]) -> set:
        selected = set()
        for value in values:
            if isinstance(value, str) and value.strip():
                selected.add(self._norm_sense(value))
        return selected

    def _norm_sense(self, value: str) -> str:
        text = str(value).strip().casefold()
        return re.sub(r"[\s()（）\[\]{}<>\"'·]", "", text)

    def _sense_keys(self, item: StemSenseEntry) -> set:
        values = []
        for field in ("meaning", "sense_id"):
            value = item.get(field)
            if isinstance(value, str) and value:
                values.append(value)
        aliases = item.get("aliases") or []
        if isinstance(aliases, list):
            values.extend(alias for alias in aliases if isinstance(alias, str) and alias)
        return {self._norm_sense(value) for value in values}

    def _selector_hits(self, keys: set, selectors: set) -> bool:
        if not keys or not selectors:
            return False
        if keys & selectors:
            return True
        for key in keys:
            if len(key) < 2 or not any("가" <= ch <= "힣" for ch in key):
                continue
            if any(key in selector for selector in selectors):
                return True
        return False

    def _matching_stem_entries(self, stem: str, entries: List[dict]) -> List[dict]:
        hits = [item for item in entries if item.get("base") and stem.endswith(item["base"])]
        if not hits:
            return []
        longest = max(len(item["base"]) for item in hits)
        return [item for item in hits if len(item["base"]) == longest]

    def _contrasting_examples(self, rule: dict) -> List[dict]:
        found = []
        groups = ((rule.get("transformation") or {}).get("contrasting_rules") or {})
        for group in groups.values():
            if not isinstance(group, dict):
                continue
            for item in group.get("examples") or []:
                if not item.get("base"):
                    continue
                tagged = dict(item)
                tagged["_rule_name"] = group.get("name") or "대조 규칙"
                tagged["_instruction"] = group.get("mechanism") or "대조 규칙에 따라 다른 활용을 적용함"
                found.append(tagged)
        return found

    def _resolve_sense_candidates(
        self,
        candidates: List[Tuple[Dict[str, Any], set]],
        selectors: Optional[set],
    ) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None
        selectors = selectors or set()
        keyed = [(result, keys) for result, keys in candidates if keys]
        pool = candidates
        unmatched = False
        if selectors and keyed:
            matched = [(result, keys) for result, keys in keyed if self._selector_hits(keys, selectors)]
            if matched:
                pool = matched
            else:
                pool = keyed
                unmatched = True
        if len(pool) == 1:
            if not unmatched:
                return pool[0][0]
            only = dict(pool[0][0])
            only["sense_unmatched"] = True
            return only
        return {
            "rule_applied": "중의적 활용",
            "surface_form": None,
            "braille_instruction": "같은 철자에 둘 이상의 활용이 있다. meaning, sense_id, context, tag 중 하나로 고른다.",
            "ambiguous": True,
            "sense_unmatched": unmatched,
            "candidates": [result for result, _keys in pool],
        }

    def _expand_reu_trigger(self, prefix: str, trigger: str, eomi: str) -> Optional[str]:
        """'일ㄹ'처럼 끝 자음이 초성이면 모음조화한 라/러로 어미와 합친다."""
        onset = self._vowel_onset(eomi)
        if not onset or not trigger:
            return None
        _eomi_jung, eomi_jong, rest = onset
        if trigger[-1] not in self.CHOSUNG_LIST:
            return f"{prefix}{trigger}{eomi}"
        body = trigger[:-1]
        harmony_char = body[-1] if body else ""
        parts = self.decompose(harmony_char) if "가" <= harmony_char <= "힣" else None
        jung = self.yang_jung if parts and parts[1] in self.yang_vowels else self.eum_jung
        tail = self.compose(trigger[-1], jung, eomi_jong)
        return f"{prefix}{body}{tail}{rest}"

    def _general_reu_surface(self, stem: str, eomi: str) -> Optional[str]:
        onset = self._vowel_onset(eomi)
        if not onset or len(stem) < 2:
            return None
        _eomi_jung, eomi_jong, rest = onset
        prev = self.decompose(stem[-2])
        if not prev or prev[2]:
            return None
        new_prev = self.compose(prev[0], prev[1], "ㄹ")
        tail_jung = self.yang_jung if prev[1] in self.yang_vowels else self.eum_jung
        tail = self.compose("ㄹ", tail_jung, eomi_jong)
        return f"{stem[:-2]}{new_prev}{tail}{rest}"

    def _apply_hieut(self, stem: str, eomi: str, decomp_last: Tuple[str, str, str], _selectors: Optional[set] = None) -> Optional[Dict[str, Any]]:
        rule = self.irregular_rules.get("hieut")
        if not rule or decomp_last[2] != rule.get("target_final_consonant"):
            return None
        if self._is_regular_exception(stem, "hieut"):
            return None
        onset = self._vowel_onset(eomi)
        if not onset:
            return None
        jung, jong, rest = onset
        cho, stem_jung, _ = decomp_last
        prefix = stem[:-1]
        name = rule.get("name", "ㅎ 불규칙")
        if jung == "ㅡ":
            bare = self.compose(cho, stem_jung, jong)
            return _conj(name, f"{prefix}{bare}{rest}", "받침 ㅎ과 매개모음 으를 빼고 적음")
        if jung in ("ㅏ", "ㅓ"):
            new_jung = self.hieut_vowel_map.get(stem_jung)
            if not new_jung:
                return None
            merged = self.compose(cho, new_jung, jong)
            return _conj(name, f"{prefix}{merged}{rest}", "받침 ㅎ이 빠지며 어간 모음이 바뀜")
        return None

    def _apply_digeut(self, stem: str, eomi: str, decomp_last: Tuple[str, str, str], selectors: Optional[set] = None) -> Optional[Dict[str, Any]]:
        rule = self.irregular_rules.get("digeut", {})
        if not self._vowel_onset(eomi):
            return None
        irregular_entries = [
            item for item in ((rule.get("transformation") or {}).get("example_stems") or [])
            if item.get("base") and item.get("vowel_trigger")
        ]
        matched_irregular = self._matching_stem_entries(stem, irregular_entries)
        irregular_bases = {item["base"] for item in matched_irregular}
        exception_bases = set(self._exception_bases("digeut"))
        if not irregular_bases or irregular_bases & exception_bases:
            return None

        matched_regular = [
            item for item in self._matching_stem_entries(stem, self._contrasting_examples(rule))
            if item["base"] in irregular_bases
        ]
        instruction = "받침 ㄷ을 ㄹ로 바꾸어 적음"
        candidates = []
        for item in matched_irregular:
            surface = stem[:-len(item["base"])] + item["vowel_trigger"] + eomi
            candidates.append((
                _conj(rule.get("name", "ㄷ 불규칙"), surface, instruction, item.get("meaning"), item.get("sense_id")),
                self._sense_keys(item),
            ))
        for item in matched_regular:
            candidates.append((
                _conj(
                    item.get("_rule_name") or "규칙 활용",
                    f"{stem}{eomi}",
                    item.get("_instruction") or "이 의미에서는 받침 ㄷ을 유지함",
                    item.get("meaning"),
                    item.get("sense_id"),
                ),
                self._sense_keys(item),
            ))
        return self._resolve_sense_candidates(candidates, selectors)

    def _apply_bieup(self, stem: str, eomi: str, decomp_last: Tuple[str, str, str], _selectors: Optional[set] = None) -> Optional[Dict[str, Any]]:
        rule = self.irregular_rules.get("bieup", {})
        if decomp_last[2] != rule.get("target_final_consonant"):
            return None
        if self._is_regular_exception(stem, "bieup"):
            return None
        onset = self._vowel_onset(eomi)
        if not onset:
            return None
        transform = rule.get("transformation", {}) or {}
        inserted = transform.get("inserted_vowel", {}) or {}
        default_vowel = inserted.get("default", "우")
        special = inserted.get("yang_vowel_monosyllabic_exception", {}) or {}
        o_vowel = special.get("inserted_vowel", "오")
        o_bases = [item.get("base", "") for item in special.get("examples", []) if item.get("base")]

        cho, jung, _ = decomp_last
        base_syl = self.compose(cho, jung, "")
        prefix = stem[:-1]
        eomi_jung, eomi_jong, rest = onset
        uses_o = any(stem.endswith(base) for base in o_bases)

        if eomi_jung in ("ㅏ", "ㅓ"):
            if uses_o and eomi_jung == "ㅏ":
                tail_jung = _contracted_jung(o_vowel, "ㅏ")
            elif uses_o:
                tail_jung = _contracted_jung(o_vowel, "ㅓ")
            else:
                tail_jung = _contracted_jung(default_vowel, "ㅓ")
            tail = self.compose("ㅇ", tail_jung, eomi_jong)
            return _conj("ㅂ 불규칙", f"{prefix}{base_syl}{tail}{rest}", "받침 ㅂ이 빠지고 ㅗ/ㅜ가 어미 모음과 축약됨")
        if eomi_jung == "ㅡ":
            inserted_parts = self.decompose(default_vowel) if "가" <= default_vowel <= "힣" else None
            inserted_jung = inserted_parts[1] if inserted_parts else "ㅜ"
            wu = self.compose("ㅇ", inserted_jung, eomi_jong)
            return _conj("ㅂ 불규칙 (으 모음 흡수)", f"{prefix}{base_syl}{wu}{rest}", "받침 ㅂ이 빠지고 매개모음 으가 우로 바뀜")
        bridge = default_vowel if "가" <= default_vowel <= "힣" else self.compose("ㅇ", default_vowel, "")
        return _conj("ㅂ 불규칙", f"{prefix}{base_syl}{bridge}{eomi}", "받침 ㅂ이 빠지고 우가 들어감")

    def _apply_siot(self, stem: str, eomi: str, decomp_last: Tuple[str, str, str], _selectors: Optional[set] = None) -> Optional[Dict[str, Any]]:
        rule = self.irregular_rules.get("siot", {})
        if decomp_last[2] != rule.get("target_final_consonant"):
            return None
        if self._is_regular_exception(stem, "siot") or not self._vowel_onset(eomi):
            return None
        cho, jung, _ = decomp_last
        base_syl = self.compose(cho, jung, "")
        return _conj(
            rule.get("name", "ㅅ 불규칙"),
            f"{stem[:-1]}{base_syl}{eomi}",
            "받침 ㅅ은 빠지지만 모음은 축약하지 않고 음절을 유지함",
        )

    def _apply_yeo(self, stem: str, eomi: str, decomp_last: Tuple[str, str, str], _selectors: Optional[set] = None) -> Optional[Dict[str, Any]]:
        rule = self.irregular_rules.get("yeo", {})
        target = rule.get("target_stem", "하")
        if not stem.endswith(target):
            return None
        parts = self.decompose(target[-1]) if target else None
        if not parts or decomp_last != parts:
            return None
        onset = self._vowel_onset(eomi)
        if not onset or onset[0] not in ("ㅏ", "ㅓ"):
            return None
        _, jong, rest = onset
        contracted = self.compose("ㅎ", "ㅐ", jong)
        return _conj(
            rule.get("name", "여 불규칙"),
            f"{stem[:-1]}{contracted}{rest}",
            "하 뒤에 아/어가 오면 '하여'가 되고, 줄여 적으면 '해'가 됨",
        )

    def _apply_reu(self, stem: str, eomi: str, decomp_last: Tuple[str, str, str], selectors: Optional[set] = None) -> Optional[Dict[str, Any]]:
        rule = self.irregular_rules.get("reu", {})
        target = rule.get("target_syllable", "르")
        if not stem.endswith(target):
            return None
        onset = self._vowel_onset(eomi)
        if not onset or onset[0] not in ("ㅏ", "ㅓ"):
            return None

        contrast = self._matching_stem_entries(stem, self._contrasting_examples(rule))
        example_entries = [
            item for item in ((rule.get("transformation") or {}).get("example_stems") or [])
            if item.get("base") and (item.get("vowel_trigger") or item.get("meaning") or item.get("sense_id"))
        ]
        contrast_bases = {item["base"] for item in contrast}
        dual_examples = [
            item for item in self._matching_stem_entries(stem, example_entries)
            if item["base"] in contrast_bases
        ]
        if contrast or dual_examples:
            shared = {item["base"] for item in dual_examples} & contrast_bases
            if shared:
                longest = max(len(base) for base in shared)
                shared = {base for base in shared if len(base) == longest}
            candidates = []
            reu_name = rule.get("name", "르 불규칙")
            reu_instruction = "ㅡ가 빠지고 앞 음절에 받침 ㄹ이 붙으며 라/러가 이어짐"
            for item in dual_examples:
                if shared and item["base"] not in shared:
                    continue
                prefix = stem[:-len(item["base"])]
                surface = None
                if item.get("vowel_trigger"):
                    surface = self._expand_reu_trigger(prefix, item["vowel_trigger"], eomi)
                if not surface:
                    surface = self._general_reu_surface(stem, eomi)
                if not surface:
                    continue
                candidates.append((
                    _conj(reu_name, surface, reu_instruction, item.get("meaning"), item.get("sense_id")),
                    self._sense_keys(item),
                ))
            _, eomi_jong, rest = onset
            for item in contrast:
                if shared and item["base"] not in shared:
                    continue
                tail = self.compose("ㄹ", "ㅓ", eomi_jong)
                candidates.append((
                    _conj(
                        item.get("_rule_name") or "러 불규칙",
                        f"{stem}{tail}{rest}",
                        "어간의 르는 유지하고 어미 어를 러로 바꿈",
                        item.get("meaning"),
                        item.get("sense_id"),
                    ),
                    self._sense_keys(item),
                ))
            resolved = self._resolve_sense_candidates(candidates, selectors)
            if resolved:
                return resolved

        surface = self._general_reu_surface(stem, eomi)
        if not surface:
            return _conj("규칙 결합", f"{stem}{eomi}", "기본 음소 및 약자 규칙 적용")
        return _conj(
            rule.get("name", "르 불규칙"),
            surface,
            "ㅡ가 빠지고 앞 음절에 받침 ㄹ이 붙으며 라/러가 이어짐",
        )

    def _apply_eu_drop(self, stem: str, eomi: str, decomp_last: Tuple[str, str, str], _selectors: Optional[set] = None) -> Optional[Dict[str, Any]]:
        rule = self.irregular_rules.get("eu_drop", {})
        if decomp_last[1] != rule.get("target_vowel") or decomp_last[2]:
            return None
        if stem.endswith((self.irregular_rules.get("reu", {}) or {}).get("target_syllable", "르")):
            return None
        onset = self._vowel_onset(eomi)
        if not onset or onset[0] not in ("ㅏ", "ㅓ"):
            return None
        _, eomi_jong, rest = onset
        prev_char = stem[-2] if len(stem) >= 2 else ""
        prev = self.decompose(prev_char) if prev_char else None
        new_jung = self.yang_jung if prev and prev[1] in self.yang_vowels else self.eum_jung
        transformed = self.compose(decomp_last[0], new_jung, eomi_jong)
        return _conj(
            rule.get("name", "ㅡ 탈락"),
            f"{stem[:-1]}{transformed}{rest}",
            "어간 모음 ㅡ가 빠지고 앞 음절 모음에 따라 아/어로 합쳐짐",
        )

    def _apply_rieul_drop(self, stem: str, eomi: str, decomp_last: Tuple[str, str, str], _selectors: Optional[set] = None) -> Optional[Dict[str, Any]]:
        rule = self.irregular_rules.get("rieul_drop", {})
        if decomp_last[2] != rule.get("target_final_consonant"):
            return None
        if not eomi:
            return None
        cho, jung, _ = decomp_last
        bare = stem[:-1] + self.compose(cho, jung, "")
        onset = self._vowel_onset(eomi)
        if onset and onset[0] == "ㅡ":
            _, jong, rest = onset
            if jong == "ㄹ" or rest.startswith("ㄹ"):
                extra = rest[1:] if rest.startswith("ㄹ") else rest
                return _conj("ㄹ 탈락", f"{stem}{extra}", "어미 ㄹ 앞에서는 ㄹ을 겹쳐 적지 않음")
            if self._rieul_trigger_kind(rest) or (jong and jong in self.rieul_drop_before):
                if jong and not rest:
                    attached = self.compose(cho, jung, jong)
                    return _conj("ㄹ 탈락", f"{stem[:-1]}{attached}", "ㄹ이 ㄴ·ㅂ·ㅅ·오 앞에서 빠짐")
                return _conj("ㄹ 탈락", f"{bare}{rest}", "ㄹ이 ㄴ·ㅂ·ㅅ·오 앞에서 빠짐")
            return _conj("ㄹ 유지", f"{stem}{rest}", "매개모음 으만 빠지고 받침 ㄹ은 남음")

        if eomi.startswith("ㄹ"):
            return _conj("ㄹ 탈락", f"{stem}{eomi[1:]}", "어미 ㄹ 앞에서는 ㄹ을 겹쳐 적지 않음")

        kind = self._rieul_trigger_kind(eomi)
        if not kind:
            return None
        if kind == "습니다":
            return _conj("ㄹ 탈락", f"{bare}ㅂ{eomi[1:]}", "ㄹ이 ㅂ 앞에서 빠지고 습니다는 ㅂ니다로 적힘")
        return _conj("ㄹ 탈락", f"{bare}{eomi}", "ㄹ이 ㄴ·ㅂ·ㅅ·오 앞에서 빠짐")

    def _rieul_trigger_kind(self, eomi: str) -> Optional[str]:
        if not eomi:
            return None
        ch = eomi[0]
        if ch in self.rieul_drop_before and ch in self.CHOSUNG_LIST:
            return ch
        if ch == "오" and "오" in self.rieul_drop_before:
            return "오"
        parts = self.decompose(ch) if "가" <= ch <= "힣" else None
        if not parts:
            return None
        cho, _, jong = parts
        if ch == "오" and "오" in self.rieul_drop_before:
            return "오"
        if cho in self.rieul_drop_before and cho in ("ㄴ", "ㅂ"):
            return cho
        if cho == "ㅅ" and "ㅅ" in self.rieul_drop_before:
            if jong == "ㅂ" and "ㅂ" in self.rieul_drop_before:
                return "습니다"
            return "ㅅ"
        return None

    # -------------------------------------------------------------
    # 5. 종합 텍스트 검증 실행
    # -------------------------------------------------------------
    def validate_text(self, text: str) -> Dict[str, Any]:
        """점역 전 텍스트의 구문 규칙 및 충돌 요소를 전수 검사합니다."""
        collision_issues = self.check_number_letter_collision(text)
        delimiter_issues = self.validate_delimiters_and_tags(text)
        abbreviation_notes = self.check_abbreviation_constraints(text)

        is_valid = len(collision_issues) == 0 and len(delimiter_issues) == 0

        return {
            "is_valid": is_valid,
            "total_issues": len(collision_issues) + len(delimiter_issues),
            "collisions": collision_issues,
            "delimiters": delimiter_issues,
            "abbreviations": abbreviation_notes,
        }


def _conj(
    rule: str,
    surface: str,
    instruction: str,
    meaning: Optional[str] = None,
    sense_id: Optional[str] = None,
) -> Dict[str, Any]:
    result = {
        "rule_applied": rule,
        "surface_form": surface,
        "braille_instruction": instruction,
    }
    if isinstance(meaning, str) and meaning:
        result["meaning"] = meaning
    if isinstance(sense_id, str) and sense_id:
        result["sense_id"] = sense_id
    return result


def _delimiter_kind(word: str, opening: bool) -> str:
    if "따옴표" in word:
        return "opening_quote" if opening else "closing_quote"
    return "opening_bracket" if opening else "closing_bracket"


def _parse_vowel_harmony(text: str) -> Tuple[set, str, str]:
    """'ㅏ·ㅑ·ㅗ·ㅛ이면 아, 없으면 어' 형식에서 양성 모음과 결과를 읽는다."""
    vowels = set("ㅏㅑㅗㅛ")
    yang = "ㅏ"
    eum = "ㅓ"
    matched = re.search(r"([ㅏ-ㅣ·]+)이면\s*['\"]([가-힣])['\"]", text)
    if matched:
        vowels = {ch for ch in matched.group(1) if "ㅏ" <= ch <= "ㅣ"}
        head = BrailleRuleValidator.decompose(matched.group(2))
        if head:
            yang = head[1]
    fallback = re.search(r"없으면\s*['\"]([가-힣])['\"]", text)
    if fallback:
        head = BrailleRuleValidator.decompose(fallback.group(1))
        if head:
            eum = head[1]
    return vowels, yang, eum


def _parse_hieut_vowel_map(text: str) -> Dict[str, str]:
    """ㅎ 불규칙의 'ㅏ·ㅓ…계열은 ㅐ, ㅑ는 ㅒ, ㅕ는 ㅖ'를 모음 대응으로 읽는다."""
    mapping = {
        "ㅏ": "ㅐ", "ㅓ": "ㅐ", "ㅗ": "ㅐ", "ㅜ": "ㅐ", "ㅡ": "ㅐ", "ㅣ": "ㅐ",
        "ㅑ": "ㅒ", "ㅕ": "ㅖ",
    }
    if not text:
        return mapping
    parsed = {}
    group = re.search(r"([ㅏ-ㅣ·\s]+)계열은\s*([ㅏ-ㅣ])", text)
    if group:
        for ch in group.group(1):
            if "ㅏ" <= ch <= "ㅣ":
                parsed[ch] = group.group(2)
    for src, dst in re.findall(r"([ㅏ-ㅣ])는\s*([ㅏ-ㅣ])", text):
        parsed[src] = dst
    if "ㅏ" not in parsed:
        mapping.update(parsed)
        return mapping
    return parsed


def _contracted_jung(inserted: str, eomi_jung: str) -> str:
    """삽입 모음과 어미 모음이 만나 줄어든 중성을 돌려준다. 오+아=ㅘ, 우+어=ㅝ."""
    inserted_jung = inserted
    if "가" <= inserted <= "힣":
        parts = BrailleRuleValidator.decompose(inserted)
        inserted_jung = parts[1] if parts else "ㅜ"
    table = {
        ("ㅗ", "ㅏ"): "ㅘ",
        ("ㅗ", "ㅓ"): "ㅝ",
        ("ㅜ", "ㅏ"): "ㅝ",
        ("ㅜ", "ㅓ"): "ㅝ",
    }
    return table.get((inserted_jung, eomi_jung), "ㅝ")


def _tag_spans(text: str, tag_pairs: Dict[str, str]) -> List[Tuple[int, int]]:
    tags = sorted(set(tag_pairs) | set(tag_pairs.values()), key=len, reverse=True)
    spans = []
    i = 0
    while i < len(text):
        matched = next((tag for tag in tags if text.startswith(tag, i)), None)
        if not matched:
            i += 1
            continue
        spans.append((i, i + len(matched)))
        i += len(matched)
    return spans


def _neighbor_index(text: str, index: int, direction: int, spans: List[Tuple[int, int]]) -> int:
    i = index + direction
    while 0 <= i < len(text):
        span = next((item for item in spans if item[0] <= i < item[1]), None)
        if span is None:
            return i
        i = span[1] if direction > 0 else span[0] - 1
    return i


def _kind_allowed(kind: str, allowed: set, direction: int) -> bool:
    if kind in allowed:
        return True
    if kind == "newline":
        if direction < 0:
            return "start_of_line" in allowed or "space" in allowed
        return "end_of_line" in allowed or "space" in allowed
    return False


if __name__ == "__main__":
    validator = BrailleRuleValidator()

    test_text = "제2차 세계대전은 <tn>1945년에 끝났다. 결과는 <i>승리<b>였다. 5월 12일 3미터 앞."
    result = validator.validate_text(test_text)

    print("=== 구문 정합성 검사 결과 ===")
    print(f"검증 통과 여부: {result['is_valid']}")
    print(f"발견된 이슈 수: {result['total_issues']}")
    for col in result["collisions"]:
        print(f" - [충돌 경고]: {col['message']}")
    for delim in result["delimiters"]:
        print(f" - [구문 오류]: {delim['message']}")
    for note in result["abbreviations"]:
        print(f" - [약자 주의]: {note['message']}")

    print("\n=== 용언 활용 결합 판정 ===")
    samples = [
        ("돕", "아"),
        ("눕", "어"),
        ("짓", "어"),
        ("쓰", "어"),
        ("부르", "어"),
        ("푸르", "어"),
        ("파랗", "아"),
        ("살", "니"),
        ("하", "아"),
        ("이르", "어"),
        ("걷", "어"),
        ("묻", "어"),
    ]
    for stem, eomi in samples:
        print(f"{stem}+{eomi}:", validator.analyze_conjugation_form(stem, eomi))
    print("이르+어 arrive:", validator.analyze_conjugation_form("이르", "어", meaning="arrive"))
    print("이르+어 tell:", validator.analyze_conjugation_form("이르", "어", meaning="tell"))
    print("걷+어 walk:", validator.analyze_conjugation_form("걷", "어", meaning="walk"))
    print("묻+어 bury:", validator.analyze_conjugation_form("묻", "어", tag="흙 속에 넣다"))
