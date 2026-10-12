"""
ko_parser.py
한글 점자 양방향 변환 엔진 (Text <-> Braille)

주요 기능:
1. Text -> Braille (정방향 점역): 약어, 초성 ㅇ 생략, 수표 뒤 띄어쓰기로 숫자 종료, 된소리표(⠠) 처리, 영문 단위 기호 결합
2. Braille -> Text (역방향 복원): 점자 토큰 분해 및 음절/숫자 모드 복원, 된소리 역변환, 영문 단위 기호 역변환
3. 규정 준수: 혼동 초성 앞 띄어쓰기, 단위어는 붙여 적기, 숫자 뒤 단위 기호 로마자표 생략
"""

import re
from typing import List, Dict, Any, Optional, Tuple


class KoreanBrailleEngine:
    CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    JUNGSUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
    JONGSUNG_LIST = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

    # 초성 된소리 매핑 (쌍자음 -> 된소리표 ⠠ + 기본 자음)
    TENSER_SIGN = "⠠"  # 6점 (된소리표)
    TENSER_MAP = {
        'ㄲ': 'ㄱ',
        'ㄸ': 'ㄷ',
        'ㅃ': 'ㅂ',
        'ㅆ': 'ㅅ',
        'ㅉ': 'ㅈ'
    }
    REV_TENSER_MAP = {v: k for k, v in TENSER_MAP.items()}

    def __init__(self, ko_data: dict, marks_data: dict, numbers_data: dict, number_rules: Optional[dict] = None, lexicon_data: Optional[dict] = None):
        self.ko = ko_data
        self.marks = marks_data
        self.numbers = numbers_data
        self.num_rules = number_rules or {}
        self.lexicon = lexicon_data or {}
        # 된소리표는 ko.json 초성 ㄲ·ㄸ·ㅃ·ㅆ·ㅉ의 점형에서 읽는다.
        self._load_tensers()

        # 1. 단어 약어 (그리고, 그러나 등). 위치는 standalone.
        self.word_abbr = {k: v["unicode"] for k, v in self.ko.get("abbreviation_word", {}).get("items", {}).items()}
        self.rev_word_abbr = {v: k for k, v in self.word_abbr.items()}
        self.word_abbr_sorted = sorted(self.word_abbr.items(), key=lambda item: len(item[0]), reverse=True)
        self.rev_word_abbr_sorted = sorted(self.rev_word_abbr.items(), key=lambda item: len(item[0]), reverse=True)
        # 같은 점형에 뜻이 둘 이상이면 문맥 태그와 함께 쌓는다. 나중 항목이 앞 항목을 덮지 않는다.
        self.rev_uses = {}

        # 2. 음절/모음+받침 약자
        syllable_items = self.ko.get("abbreviation_syllable", {}).get("items", {})
        self.ga_series = {}          # 가, 나, 다 ...
        self.rev_ga_series = {}
        self.vowel_coda_series = {}  # ('ㅓ', 'ㄱ') -> 억
        self.rev_vowel_coda = {}
        self.complete_syllables = {} # 것
        self.rev_complete = {}

        for k, v in syllable_items.items():
            stype = v.get("type")
            u = v["unicode"]
            if stype == "ga_series":
                self.ga_series[k] = u
                self.rev_ga_series[u] = k
            elif stype == "vowel_coda_series":
                code = ord(k) - 0xAC00
                jung_idx = (code % (21 * 28)) // 28
                jong_idx = code % 28
                pair = (self.JUNGSUNG_LIST[jung_idx], self.JONGSUNG_LIST[jong_idx])
                self.vowel_coda_series[pair] = u
                self.rev_vowel_coda[u] = pair
            elif stype == "complete_syllable":
                self.complete_syllables[k] = u
                self.rev_complete[u] = k

        yeong = syllable_items.get("영", {})
        yeong_override = yeong.get("initial_vowel_override") or {}
        self.yeong_unicode = yeong.get("unicode", "")
        self.yeong_override_initials = set(yeong_override.get("initials", []))
        self.yeong_surface_vowel = yeong_override.get("surface_vowel", "ㅓ")
        self.yeong_surface_jong = yeong_override.get("surface_jong", "ㅇ")
        yeong_parts = self.decompose("영")
        # 약자 '영'을 풀어 쓸 때의 모음. 셩·졍·쳥은 이 모음으로 적고 약자를 쓰지 않는다.
        self.yeong_spell_jung = yeong_parts[1] if yeong_parts else "ㅕ"
        geot = syllable_items.get("것", {})
        self.geot_unicode = geot.get("unicode", "")
        self.geot_tensed = set(geot.get("tensed_same_abbreviation", []))
        self.geot_spell_out = self._geot_spell_out_syllables(geot)

        # 3. 기본 자모음 매핑
        self.chosung_map = {k: v["unicode"] for k, v in self.ko.get("chosung", {}).get("items", {}).items()}
        self.rev_chosung = {v: k for k, v in self.chosung_map.items() if v}  # ㅇ(빈 문자열) 제외
        self.jungsung_map = {k: v["unicode"] for k, v in self.ko.get("jungsung", {}).get("items", {}).items()}
        self.rev_jungsung = {v: k for k, v in self.jungsung_map.items()}
        self.jongsung_map = {k: v["unicode"] for k, v in self.ko.get("jongsung", {}).get("items", {}).items() if k}
        self.rev_jongsung = {v: k for k, v in self.jongsung_map.items()}

        # 4. 숫자 및 지시표
        self.num_prefix = self.numbers.get("numeric_indicators", {}).get("num_prefix", {}).get("unicode", "⠼")
        self.digits = {k: v["unicode"] for k, v in self.numbers.get("digits", {}).items()}
        self.rev_digits = {v: k for k, v in self.digits.items()}

        self.num_connectors = {}
        self.connector_persists = {}
        for item in self.num_rules.get("symbols", {}).values():
            char = item.get("char")
            uni = item.get("unicode")
            if not char or not uni or char == " ":
                continue
            self.num_connectors[char] = uni
            self.connector_persists[char] = bool(item.get("persists_numeric_mode", True))
        self.rev_num_connectors = {}
        for char, uni in self.num_connectors.items():
            self.rev_num_connectors.setdefault(uni, []).append(char)
            self._add_use(uni, char, "between_numbers")

        sa_item = syllable_items.get("사", {})
        self.sa_expanded = self.chosung_map.get("ㅅ", "") + self.jungsung_map.get("ㅏ", "")
        stored_sa = sa_item.get("expanded_unicode")
        if stored_sa and stored_sa != self.sa_expanded:
            raise ValueError(
                f"ko.json 사 풀어쓰기 {stored_sa!r}가 초성 ㅅ+중성 ㅏ({self.sa_expanded!r})와 다릅니다."
            )
        # '사' 예외는 exception_rules에 있는 항목만 적용한다.
        sa_rules = sa_item.get("exception_rules") or {}
        self.sa_after_number = "after_number" in sa_rules
        self.sa_before_vowel = "vowel_connection" in sa_rules

        # 제17항 [붙임]·[다만]: 첫소리와 점형이 같은 약자는 모음 앞에서 ㅏ를 적는다. '팠'도 ㅏ를 적는다.
        keep_a = self.ko.get("abbreviation_syllable", {}).get("rule", {}).get("keep_a", {})
        keep_vowel = keep_a.get("vowel_connection", {})
        self.keep_a_onsets = set()
        for syl in keep_vowel.get("syllables", []):
            parts = self.decompose(syl)
            if parts:
                self.keep_a_onsets.add(parts[0])
        if keep_vowel.get("include_tensed"):
            self.keep_a_onsets |= {t for t, base in self.TENSER_MAP.items() if base in self.keep_a_onsets}
        self.keep_a_spell_out = set(keep_a.get("spell_out", {}))

        word_pos = self.ko.get("abbreviation_word", {}).get("rule", {}).get("position", "standalone")
        self.word_abbr_standalone = word_pos == "standalone"
        self.omit_zero_consonant = bool(
            self.ko.get("chosung", {}).get("rule", {}).get("omitZeroConsonant", True)
        )
        # 같은 칸을 약자+받침과 초성+모음이 나눠 쓰면 우선순위가 높은 쪽을 읽는다.
        abbr_priority = self.ko.get("abbreviation_syllable", {}).get("rule", {}).get("priority", 80)
        jung_priority = self.ko.get("jungsung", {}).get("rule", {}).get("priority", 40)
        self.prefer_abbr_over_jungsung = abbr_priority >= jung_priority

        number_prefix_rule = self.ko.get("special_rules", {}).get("number_prefix_rule", {})
        self.affected_initials = set(
            number_prefix_rule.get("affected_initials", ["ㄴ", "ㄷ", "ㅁ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"])
        )
        self.affected_abbreviations = set(number_prefix_rule.get("affected_abbreviations", []))
        action = number_prefix_rule.get("action", "terminate_number_with_space")
        self.number_gap = " " if action == "terminate_number_with_space" else ""
        self.number_terminators = set(
            self.num_rules.get("termination_triggers", {}).get(
                "terminators",
                ["space", "korean_letter", "punctuation_standalone", "line_break"],
            )
        )

        # 한글 단위어 예외 목록 (한글 음절 충돌 방지용)
        self.exempt_units = set(
            self.num_rules.get("collision_resolutions", {})
            .get("trailing_letters", {})
            .get("exempt_units", [])
        )
        self.exempt_units_sorted = tuple(sorted(self.exempt_units, key=len, reverse=True))
        self._load_unit_boundary()

        # 영문 단위 기호 매핑 로드
        self.roman_unit_symbols = (
            self.num_rules.get("collision_resolutions", {})
            .get("trailing_letters", {})
            .get("roman_unit_symbols", {})
        )
        # 긴 단위 기호(km, ml 등)를 먼저 매칭하기 위해 길이순 정렬
        self.sorted_roman_units = sorted(self.roman_unit_symbols.keys(), key=len, reverse=True)
        # 역변환용 점형 -> 영문 단위 기호 매핑
        self.rev_roman_units = {v: k for k, v in self.roman_unit_symbols.items()}
        self.sorted_rev_roman_units = sorted(self.rev_roman_units.keys(), key=len, reverse=True)

        self._index_letter_uses()
        self._index_abbreviation_uses()

        # 5. 문장부호
        self._init_punctuation()
        # 단위어 점형은 음절 규칙이 준비된 뒤에 만든다.
        self._build_exempt_unit_braille()

    def _load_tensers(self):
        """초성 항목의 점형이 ⠠ + 기본 자음이면 된소리로 읽는다."""
        items = self.ko.get("chosung", {}).get("items", {})
        plain = {}
        tensed = {}
        for char, item in items.items():
            uni = item.get("unicode") or ""
            if item.get("isOmitted") or not uni:
                continue
            if uni.startswith(self.TENSER_SIGN) and uni != self.TENSER_SIGN:
                tensed[char] = uni
            else:
                plain[uni] = char
        mapping = {}
        for char, uni in tensed.items():
            base = plain.get(uni[len(self.TENSER_SIGN):])
            if base:
                mapping[char] = base
        if mapping:
            self.TENSER_MAP = mapping
            self.REV_TENSER_MAP = {base: char for char, base in mapping.items()}

    def _geot_spell_out_syllables(self, geot: dict) -> set:
        """'껐'은 것 약자에 된소리표를 붙이지 않고 꺼+받침 ㅆ으로 적는다."""
        if not geot.get("ssang_jong_exception"):
            return set()
        parts = self.decompose("것")
        if not parts:
            return set()
        tense_cho = self.REV_TENSER_MAP.get(parts[0])
        if not tense_cho:
            return set()
        return {self.compose(tense_cho, parts[1], "ㅆ")}

    def _onset_braille(self, base_cho: str) -> str:
        """초성 ㅇ은 omitZeroConsonant일 때 점형을 내지 않는다."""
        if base_cho == "ㅇ" and self.omit_zero_consonant:
            return ""
        return self.chosung_map.get(base_cho, "")

    def _terminate_number(self, kind: str) -> bool:
        return kind in self.number_terminators

    def _ga_choseong(self, cell: str) -> Optional[str]:
        syllable = self.rev_ga_series.get(cell)
        parts = self.decompose(syllable) if syllable else None
        return parts[0] if parts else None

    def _compose_ga(self, cho: str, jong: str = "", tense: bool = False) -> str:
        if tense:
            cho = self.REV_TENSER_MAP.get(cho, cho)
        return self.compose(cho, "ㅏ", jong)

    def _try_ga_syllable(self, token: str, idx: int) -> Tuple[str, int]:
        """가 계열 약자. 초성과 칸을 나누는 약자는 뒤가 모음이면 초성으로 읽는다.

        뒤 칸이 받침이면서 모음이기도 하면(ㅆ/ㅖ) abbreviation_syllable 우선순위를 따른다.
        """
        if idx >= len(token):
            return "", 0
        cell = token[idx]
        cho = self._ga_choseong(cell)
        if not cho:
            return "", 0
        jong, jong_len = self._read_symbol(self.rev_jongsung, token, idx + 1)
        if jong:
            jong_cells = token[idx + 1:idx + 1 + jong_len]
            if jong_cells in self.rev_jungsung and not self.prefer_abbr_over_jungsung:
                return "", 0
            # ㅆ과 ㅖ가 같은 칸이다. 그 뒤에 받침이 더 있으면 ㅖ+받침으로 읽는다.
            if jong_cells in self.rev_jungsung:
                more, _ = self._read_symbol(self.rev_jongsung, token, idx + 1 + jong_len)
                if more:
                    return "", 0
            return self._compose_ga(cho, jong), 1 + jong_len
        nxt = token[idx + 1] if idx + 1 < len(token) else ""
        nxt_continues = bool(nxt) and (nxt in self.rev_jungsung or nxt in self.rev_vowel_coda)
        if nxt_continues and cell in self.rev_chosung:
            return "", 0
        return self.rev_ga_series[cell], 1

    def _add_use(self, braille: str, text: str, context: str):
        if not braille or text is None:
            return
        bucket = self.rev_uses.setdefault(braille, [])
        if any(item["text"] == text and item["context"] == context for item in bucket):
            return
        bucket.append({"text": text, "context": context})

    def _index_letter_uses(self):
        for uni, char in self.rev_chosung.items():
            if char == "ㄹ":
                context = "word_initial"
            elif char == "ㅊ":
                context = "syllable_initial"
            else:
                context = "syllable_initial"
            self._add_use(uni, char, context)
        for uni, char in self.rev_jungsung.items():
            context = "vowel" if char == "ㅖ" else "vowel"
            self._add_use(uni, char, context)
        for uni, char in self.rev_jongsung.items():
            if char == "ㄴ":
                context = "syllable_final"
            elif char == "ㅎ":
                context = "syllable_final"
            elif char == "ㅆ":
                context = "coda"
            else:
                context = "syllable_final"
            self._add_use(uni, char, context)

    def _index_abbreviation_uses(self):
        for word, uni in self.word_abbr.items():
            self._add_use(uni, word, "standalone")
        for syllable, uni in self.ga_series.items():
            self._add_use(uni, syllable, "abbreviation")
        for (jung, jong), uni in self.vowel_coda_series.items():
            self._add_use(uni, self.compose("ㅇ", jung, jong), "abbreviation")
        for syllable, uni in self.complete_syllables.items():
            self._add_use(uni, syllable, "abbreviation")
        for digit, uni in self.digits.items():
            self._add_use(uni, digit, "numeric")
        for unit, uni in self.roman_unit_symbols.items():
            self._add_use(uni, unit, "after_number")

    def _hangul_word_braille(self, text: str) -> str:
        parts = []
        for char in text:
            parts_of = self.decompose(char)
            if not parts_of:
                return ""
            cho, jung, jong = parts_of
            braille, _ = self._translate_hangul_syllable_with_trace(cho, jung, jong, char)
            parts.append(braille)
        return "".join(parts)

    def _build_exempt_unit_braille(self):
        pairs = []
        for unit in self.exempt_units_sorted:
            braille = self._hangul_word_braille(unit)
            if braille:
                pairs.append((unit, braille))
        pairs.sort(key=lambda item: (len(item[1]), len(item[0])), reverse=True)
        self.exempt_unit_braille = pairs

    def _add_punct_sense(self, char: str, item: dict, category: str):
        uni = item["unicode"]
        self.punct_map[char] = uni
        if category == "terminal_punctuation":
            context = "sentence_end"
        elif category == "opening_delimiters":
            context = "word_initial"
        elif category == "closing_delimiters":
            context = "punctuation"
        elif category == "transcriber_and_formatting_tags":
            context = "tag_" + (item.get("pairRole") or "boundary")
        elif category == "placeholder_marks":
            context = "punctuation"
        else:
            context = "punctuation"
        sense = {
            "char": char,
            "category": category,
            "context": context,
            "position": item.get("pairRole") or self.marks.get(category, {}).get("rule", {}).get("position"),
        }
        self.punct_senses.setdefault(uni, []).append(sense)
        self._add_use(uni, char, context)

    def _init_punctuation(self):
        self.punct_map = {}
        self.punct_senses = {}
        for cat in ["terminal_punctuation", "pausal_punctuation", "connectors_and_symbols", "placeholder_marks", "transcriber_and_formatting_tags"]:
            for k, v in self.marks.get(cat, {}).get("items", {}).items():
                self._add_punct_sense(k, v, cat)

        self.open_delims = {k: v["unicode"] for k, v in self.marks.get("opening_delimiters", {}).get("items", {}).items()}
        self.close_delims = {k: v["unicode"] for k, v in self.marks.get("closing_delimiters", {}).get("items", {}).items()}
        for k, v in self.marks.get("opening_delimiters", {}).get("items", {}).items():
            self._add_punct_sense(k, v, "opening_delimiters")
        for k, v in self.marks.get("closing_delimiters", {}).get("items", {}).items():
            self._add_punct_sense(k, v, "closing_delimiters")

        # 같은 점형을 여는 태그와 닫는 태그가 나눠 쓰는 경우. <tn>과 </tn>은 둘 다 ⠠⠄다.
        grouped = {}
        for tag, item in self.marks.get("transcriber_and_formatting_tags", {}).get("items", {}).items():
            grouped.setdefault(item["unicode"], []).append((tag, item.get("pairRole")))
        self.toggle_tags = {}
        for uni, entries in grouped.items():
            opens = [tag for tag, role in entries if role == "open"]
            closes = [tag for tag, role in entries if role == "close"]
            if uni and len(opens) == 1 and len(closes) == 1:
                self.toggle_tags[uni] = (opens[0], closes[0])
        self.toggle_tag_sorted = sorted(self.toggle_tags.items(), key=lambda item: len(item[0]), reverse=True)

    @classmethod
    def decompose(cls, char: str) -> Optional[Tuple[str, str, str]]:
        code = ord(char) - 0xAC00
        if 0 <= code <= 11171:
            cho = code // (21 * 28)
            jung = (code % (21 * 28)) // 28
            jong = code % 28
            return cls.CHOSUNG_LIST[cho], cls.JUNGSUNG_LIST[jung], cls.JONGSUNG_LIST[jong]
        return None

    @classmethod
    def compose(cls, cho: str, jung: str, jong: str = "") -> str:
        cho_idx = cls.CHOSUNG_LIST.index(cho)
        jung_idx = cls.JUNGSUNG_LIST.index(jung)
        jong_idx = cls.JONGSUNG_LIST.index(jong) if jong else 0
        return chr(0xAC00 + (cho_idx * 21 + jung_idx) * 28 + jong_idx)

    # -------------------------------------------------------------
    # 1. TEXT -> BRAILLE
    # -------------------------------------------------------------
    def text_to_braille(self, text: str) -> Dict[str, Any]:
        out = []
        traces = []
        i = 0
        n = len(text)

        in_number_mode = False
        quote_open = False

        while i < n:
            ch = text[i]

            # 1. 공백 및 개행
            if ch in (' ', '\n', '\r'):
                out.append(ch)
                kind = "space" if ch == " " else "line_break"
                if self._terminate_number(kind):
                    in_number_mode = False
                traces.append({"token": ch, "braille": ch, "rule": "Whitespace/Newline", "scope": "Reset numeric mode"})
                i += 1
                continue

            # 2. 문장부호 및 마크업 태그 다중문자 매칭 (최장 일치)
            matched_punct = False
            for length in [5, 4, 3, 2]:
                sub = text[i:i+length]
                if sub in self.punct_map:
                    b = self.punct_map[sub]
                    out.append(b)
                    if self._terminate_number("punctuation_standalone"):
                        in_number_mode = False
                    traces.append({"token": sub, "braille": b, "rule": "Multi-char Mark/Tag", "scope": "Reset numeric mode"})
                    i += length
                    matched_punct = True
                    break
            if matched_punct:
                continue

            # 3. 단어 약어. ko.json position은 standalone이라 앞뒤가 한글 음절이면 풀어 적는다.
            matched_word = False
            for w, b_code in self.word_abbr_sorted:
                w_len = len(w)
                if text[i:i+w_len] != w:
                    continue
                prev_c = text[i - 1] if i else ""
                next_c = text[i + w_len:i + w_len + 1]
                if self.word_abbr_standalone and (
                    (prev_c and "가" <= prev_c <= "힣") or (next_c and "가" <= next_c <= "힣")
                ):
                    break
                out.append(b_code)
                in_number_mode = False
                traces.append({
                    "token": w,
                    "braille": b_code,
                    "rule": "Word Abbreviation",
                    "explanation": f"단어 약어 '{w}' 적용"
                })
                i += w_len
                matched_word = True
                break
            if matched_word:
                continue

            # 4. 숫자 모드 유지 중 영문 단위 기호 분기 (숫자 처리 앞단에서 매칭)
            if in_number_mode:
                matched_unit = None
                for unit in self.sorted_roman_units:
                    if text[i:].startswith(unit):
                        matched_unit = unit
                        break

                if matched_unit:
                    out.append(self.roman_unit_symbols[matched_unit])
                    traces.append({
                        "token": matched_unit,
                        "braille": self.roman_unit_symbols[matched_unit],
                        "rule": "Roman Unit Symbol",
                        "explanation": f"숫자 뒤 단위 기호 '{matched_unit}' 로마자표 생략 결합"
                    })
                    i += len(matched_unit)
                    in_number_mode = False
                    continue

            # 5. 숫자 처리
            if ch.isdigit():
                prefix = ""
                explanation = "연속 숫자"
                if not in_number_mode:
                    prefix = self.num_prefix
                    in_number_mode = True
                    explanation = "수표(⠼) 시작"
                b_digit = prefix + self.digits[ch]
                out.append(b_digit)
                traces.append({"token": ch, "braille": b_digit, "rule": "Numeric Mode", "explanation": explanation})
                i += 1
                continue

            # 숫자 사이 쉼표·온점·하이픈·슬래시. 유지 여부는 ko_number_rules.json만 본다.
            if in_number_mode and ch in self.num_connectors:
                if i + 1 < n and text[i+1].isdigit():
                    b_conn = self.num_connectors[ch]
                    out.append(b_conn)
                    if not self.connector_persists.get(ch, True):
                        in_number_mode = False
                    traces.append({"token": ch, "braille": b_conn, "rule": "Numeric Connector", "explanation": "ko_number_rules 연결자"})
                    i += 1
                    continue
                else:
                    in_number_mode = False

            # 6. 따옴표 열림/닫힘 판별
            if ch == '"':
                b_q = self.open_delims.get("“", "⠦") if not quote_open else self.close_delims.get("”", "⠴")
                quote_open = not quote_open
                out.append(b_q)
                if self._terminate_number("punctuation_standalone"):
                    in_number_mode = False
                traces.append({"token": ch, "braille": b_q, "rule": "Quote Delimiter", "explanation": "여는/닫는 큰따옴표"})
                i += 1
                continue

            # 7. 일반 단일 문장부호. 아포스트로피(')는 ko_marks.json대로 ⠐이다.
            if ch in self.punct_map:
                b = self.punct_map[ch]
                out.append(b)
                if self._terminate_number("punctuation_standalone"):
                    in_number_mode = False
                traces.append({"token": ch, "braille": b, "rule": "Punctuation", "explanation": "문장부호"})
                i += 1
                continue

            # 8. 한글 음절 변환
            if '가' <= ch <= '힣':
                decomp = self.decompose(ch)
                cho, jung, jong = decomp
                number_break = ""
                rules_applied = []

                # 제17항: '사' 약자 예외. 제18항은 그래서·그러나 등 단어 약어이다.
                # 제2호: 숫자 바로 뒤에 '사'가 오면 풀어 적음 (예: "4사분기")
                # 제1호: '사' 뒤에 모음으로 시작하는 음절이 이어지면 풀어 적음 (예: "사이")
                is_sa_exception = False
                if ch == '사':
                    if self.sa_after_number and (in_number_mode or (i > 0 and text[i-1].isdigit())):
                        is_sa_exception = True
                        rules_applied.append(f"제17항 제2호 적용: 숫자 뒤 '사' 예외 풀어쓰기('{self.sa_expanded}') 적용")
                    elif self.sa_before_vowel and i + 1 < n and '가' <= text[i+1] <= '힣':
                        next_decomp = self.decompose(text[i+1])
                        if next_decomp and next_decomp[0] == 'ㅇ':
                            is_sa_exception = True
                            rules_applied.append(f"제17항 제1호 적용: 모음 연접 '사' 예외 풀어쓰기('{self.sa_expanded}') 적용")

                # 혼동 초성·약자 운은 띄어쓰기로 수표를 끝낸다. 경계가 맞는 단위어만 붙여 적는다.
                if in_number_mode:
                    is_exempt = bool(self._match_exempt_unit(text[i:]))
                    if not is_exempt and (cho in self.affected_initials or ch in self.affected_abbreviations):
                        number_break = self.number_gap
                        if ch in self.affected_abbreviations:
                            rules_applied.append(f"약자 '{ch}'이 숫자와 겹치므로 띄어쓰기로 숫자 입력 종료")
                        else:
                            rules_applied.append(f"초성 '{cho}'이 숫자와 겹치므로 띄어쓰기로 숫자 입력 종료")
                    if self._terminate_number("korean_letter"):
                        in_number_mode = False

                keep_a = ""
                if not is_sa_exception and jung == 'ㅏ':
                    if ch in self.keep_a_spell_out:
                        keep_a = f"제17항 [다만]: '{ch}'은 ㅏ를 생략하지 않고 적음"
                    elif not jong and cho in self.keep_a_onsets and i + 1 < n and '가' <= text[i+1] <= '힣':
                        next_decomp = self.decompose(text[i+1])
                        if next_decomp and next_decomp[0] == 'ㅇ':
                            keep_a = f"제17항 [붙임]: 모음 앞 '{ch}'은 약자를 쓰지 않고 ㅏ를 적음"

                if is_sa_exception:
                    braille_syllable = self.sa_expanded
                    if jong:
                        braille_syllable += self.jongsung_map.get(jong, '')
                elif keep_a:
                    rules_applied.append(keep_a)
                    braille_syllable = (self.chosung_map.get(cho, '') + self.jungsung_map.get(jung, '')
                                        + (self.jongsung_map.get(jong, '') if jong else ''))
                else:
                    braille_syllable, syl_rules = self._translate_hangul_syllable_with_trace(cho, jung, jong, ch)
                    rules_applied.extend(syl_rules)

                final_b = number_break + braille_syllable
                out.append(final_b)
                traces.append({
                    "token": ch,
                    "braille": final_b,
                    "decomposition": f"초성:{cho}, 중성:{jung}, 종성:{jong or '-'}",
                    "rule": "Hangul Syllable",
                    "explanation": "; ".join(rules_applied)
                })
                i += 1
                continue

            # 9. 미정의 문자 / 알파벳 패스스루
            in_number_mode = False
            out.append(ch)
            traces.append({"token": ch, "braille": ch, "rule": "Raw Passthrough", "explanation": "기타/알파벳"})
            i += 1

        return {
            "braille": "".join(out),
            "traces": traces
        }

    def _translate_hangul_syllable_with_trace(self, cho: str, jung: str, jong: str, raw_char: str) -> Tuple[str, List[str]]:
        rules = []
        spell_out_geot = raw_char in self.geot_spell_out

        # A. 완전 일치 음절 ('것' 등). '껐'은 이 약자를 쓰지 않는다.
        if raw_char in self.complete_syllables and not spell_out_geot:
            rules.append(f"완전 일치 음절 약자 '{raw_char}' 적용")
            return self.complete_syllables[raw_char], rules

        # B. 초성 된소리 접두표(⠠) 분리 처리
        tenser_prefix = ""
        base_cho = cho
        if cho in self.TENSER_MAP:
            tenser_prefix = self.TENSER_SIGN
            base_cho = self.TENSER_MAP[cho]
            rules.append(f"된소리 초성 '{cho}' 된소리표(⠠) 적용")

        if raw_char in self.geot_tensed and self.geot_unicode and not spell_out_geot:
            rules.append(f"된소리표와 '것' 약자 결합 ('{raw_char}')")
            return tenser_prefix + self.geot_unicode, rules

        # ㅅ·ㅆ·ㅈ·ㅉ·ㅊ 뒤의 '영' 약자는 성·썽·정·쩡·청. 셩·졍·쳥 등은 풀어 적는다.
        skip_yeong_abbr = False
        if self.yeong_unicode and cho in self.yeong_override_initials and jong == self.yeong_surface_jong:
            if jung == self.yeong_surface_vowel:
                cho_b = self._onset_braille(base_cho)
                rules.append(f"'{cho}' 뒤 '영' 약자는 '{raw_char}'")
                return tenser_prefix + cho_b + self.yeong_unicode, rules
            if jung == self.yeong_spell_jung and jung != self.yeong_surface_vowel:
                skip_yeong_abbr = True
                rules.append(f"'{raw_char}'은 '영' 약자를 쓰지 않고 풀어 적음")

        # C. '가' 계열 약자 (초성 + 'ㅏ'). 키는 완성형 음절이다.
        base_ga = self.compose(base_cho, "ㅏ") if jung == "ㅏ" else ""
        if jung == 'ㅏ' and base_ga in self.ga_series:
            ga_b = self.ga_series[base_ga]
            jong_b = self.jongsung_map[jong] if jong else ""
            rules.append(f"가 계열 약자 '{base_ga}' 적용" + (f" + 종성 '{jong}' 결합" if jong else ""))
            return tenser_prefix + ga_b + jong_b, rules

        # D. '모음+받침' 약자
        if not skip_yeong_abbr and (jung, jong) in self.vowel_coda_series:
            vc_b = self.vowel_coda_series[(jung, jong)]
            if base_cho == 'ㅇ' and self.omit_zero_consonant:
                rules.append(f"초성 'ㅇ' 생략 및 모음+받침 약자 적용 (중성:{jung}, 종성:{jong})")
                return tenser_prefix + vc_b, rules
            else:
                cho_b = self._onset_braille(base_cho)
                rules.append(f"초성 '{cho}' + 모음+받침 약자 적용 (중성:{jung}, 종성:{jong})")
                return tenser_prefix + cho_b + vc_b, rules

        # E. 일반 자모음 분해
        cho_b = self._onset_braille(base_cho)
        if base_cho == 'ㅇ' and self.omit_zero_consonant:
            rules.append("초성 'ㅇ' 점형 생략")
        else:
            rules.append(f"초성 '{cho}' 결합")

        jung_b = self.jungsung_map.get(jung, "")
        rules.append(f"중성 '{jung}' 결합")

        jong_b = self.jongsung_map.get(jong, "") if jong else ""
        if jong:
            rules.append(f"종성 '{jong}' 결합")

        return tenser_prefix + cho_b + jung_b + jong_b, rules

    # -------------------------------------------------------------
    # 2. BRAILLE -> TEXT (역변환 파서)
    # -------------------------------------------------------------
    def braille_to_text(self, braille_str: str) -> str:
        tokens = re.findall(r'[\u2800-\u28FF]+|[^\u2800-\u28FF]+', braille_str)
        result = []
        self._tag_open = {uni: False for uni in self.toggle_tags}

        for token in tokens:
            if not token.strip() or not any('\u2800' <= c <= '\u28FF' for c in token):
                result.append(token)
                continue

            result.append(self._decode_braille_token(token))

        return "".join(result)

    def _decode_braille_token(self, b_token: str) -> str:
        if b_token in self.rev_word_abbr:
            return self.rev_word_abbr[b_token]

        decoded = []
        i = 0
        n = len(b_token)

        max_complete_len = max((len(k) for k in self.rev_complete.keys()), default=1)

        while i < n:
            # 1. 수표 발견 시 숫자 시퀀스 우선 디코딩
            if b_token[i] == self.num_prefix:
                num_str, consumed = self._consume_numeric_sequence(b_token, i)
                decoded.append(num_str)
                i += consumed
                continue

            # 2. 여는 태그와 닫는 태그가 같은 점형이면 나타난 순서로 짝짓는다.
            matched_tag = False
            for uni, (open_tag, close_tag) in self.toggle_tag_sorted:
                if not b_token.startswith(uni, i):
                    continue
                syllable, consumed = self._decode_single_syllable(b_token, i)
                if consumed >= len(uni):
                    break
                decoded.append(close_tag if self._tag_open.get(uni) else open_tag)
                self._tag_open[uni] = not self._tag_open.get(uni)
                i += len(uni)
                matched_tag = True
                break
            if matched_tag:
                continue

            # 3. 완전 음절 약자. 부호 칸보다 음절 문맥이 먼저다.
            matched_complete = False
            for length in range(min(max_complete_len, n - i), 0, -1):
                sub = b_token[i:i+length]
                if sub in self.rev_complete:
                    decoded.append(self.rev_complete[sub])
                    i += length
                    matched_complete = True
                    break
            if matched_complete:
                continue

            # 4. 음절 자리. 두 칸 부호(괄호, 밑줄 등)가 한 칸 자음보다 길면 부호를 먼저 읽는다.
            punct, punct_len = self._match_punct(b_token, i)
            syllable, consumed = self._decode_single_syllable(b_token, i)
            if punct_len > 1 and punct_len > consumed:
                decoded.append(punct)
                i += punct_len
                continue
            if consumed > 0:
                decoded.append(syllable)
                i += consumed
                continue

            # 4b. 음절로 읽히지 않는 ⠁⠎ 등은 단독 단어 약어다.
            word, word_len = self._match_word_abbr(b_token, i)
            if word_len:
                decoded.append(word)
                i += word_len
                continue

            # 5. 음절이 아니면 부호 자리. 같은 점형의 후보는 함께 남긴다.
            if punct_len:
                decoded.append(punct)
                i += punct_len
            else:
                decoded.append(b_token[i])
                i += 1

        return "".join(decoded)

    def _decode_number_body(self, cells: str) -> str:
        res = []
        idx = 0
        n = len(cells)
        while idx < n:
            c = cells[idx]
            if c in self.rev_digits:
                res.append(self.rev_digits[c])
                idx += 1
            elif c in self.rev_num_connectors and idx + 1 < n and cells[idx + 1] in self.rev_digits:
                options = [ch for ch in self.rev_num_connectors[c] if self.connector_persists.get(ch)]
                res.append((options or self.rev_num_connectors[c])[0])
                idx += 1
            else:
                break
        return "".join(res)

    def _is_number_body(self, cells: str) -> bool:
        if not cells or cells[0] not in self.rev_digits:
            return False
        idx = 0
        n = len(cells)
        while idx < n:
            c = cells[idx]
            if c in self.rev_digits:
                idx += 1
                continue
            if c in self.rev_num_connectors and idx + 1 < n and cells[idx + 1] in self.rev_digits:
                idx += 1
                continue
            return False
        return True

    def _load_unit_boundary(self):
        """ko_number_rules.json의 단위 경계와 조사 목록을 읽는다."""
        boundary = (
            self.num_rules.get("collision_resolutions", {})
            .get("trailing_letters", {})
            .get("unit_boundary", {})
        )
        self.unit_boundary_enabled = bool(boundary.get("enabled", False))
        self.josa_sorted = tuple(
            sorted({item for item in boundary.get("josa", []) if item}, key=len, reverse=True)
        )
        self.josa_scan_limit = max((len(item) for item in self.josa_sorted), default=1)

    def _unit_boundary_ok(self, after: str) -> bool:
        """단위 직후가 경계이거나 조사일 때만 참이다.

        조사가 아닌 한글 음절이 바로 이어지면 단위로 보지 않는다.
        '5동에'는 인정하고 '5동안'은 취소한다.
        """
        if not self.unit_boundary_enabled:
            return True
        if not after:
            return True
        head = after[0]
        if not ("가" <= head <= "힣"):
            return True
        return any(after.startswith(josa) for josa in self.josa_sorted)

    def _match_exempt_unit(self, tail_text: str) -> str:
        """가장 긴 단위 후보 중 경계가 맞는 것만 고른다."""
        for unit in self.exempt_units_sorted:
            if unit and tail_text.startswith(unit) and self._unit_boundary_ok(tail_text[len(unit):]):
                return unit
        return ""

    def _following_hangul(self, b_token: str, index: int) -> str:
        """단위 점형 뒤에서 조사 길이만큼 한글 음절을 읽는다."""
        chars = []
        i = index
        for _ in range(self.josa_scan_limit):
            if i >= len(b_token):
                break
            syllable, consumed = self._decode_single_syllable(b_token, i)
            if consumed <= 0 or len(syllable) != 1 or not ("가" <= syllable <= "힣"):
                break
            chars.append(syllable)
            i += consumed
        return "".join(chars)

    def _match_trailing_exempt_unit(self, b_token: str, region_start: int, region_end: int):
        """숫자 칸에 먹힌 단위어를 긴 점형부터 되살린다. 앞에 숫자가 한 칸 이상 남아야 한다."""
        for unit, ub in self.exempt_unit_braille:
            found = None
            pos = region_start
            while pos < region_end:
                found_at = b_token.find(ub, pos)
                if found_at < 0 or found_at >= region_end:
                    break
                if found_at > region_start and self._is_number_body(b_token[region_start:found_at]):
                    after = self._following_hangul(b_token, found_at + len(ub)) if self.unit_boundary_enabled else ""
                    if self._unit_boundary_ok(after):
                        found = found_at
                pos = found_at + 1
            if found is not None:
                return unit, found, len(ub)
        return "", 0, 0

    def _match_exempt_unit_after(self, b_token: str, index: int) -> Tuple[str, int]:
        """숫자 칸 바로 뒤에 붙은 단위어. 리터·센티미터처럼 첫 칸이 숫자가 아닌 경우."""
        for unit, ub in self.exempt_unit_braille:
            if not ub or not b_token.startswith(ub, index):
                continue
            after = self._following_hangul(b_token, index + len(ub)) if self.unit_boundary_enabled else ""
            if self._unit_boundary_ok(after):
                return unit, len(ub)
        return "", 0

    def _read_number_and_roman(self, b_token: str, idx: int, end: int, start_idx: int) -> Tuple[str, int]:
        """숫자 뒤에 로마자 단위를 붙인다. 단위 칸이 숫자와 겹치면 두 읽기를 함께 남긴다."""
        plain = self._decode_number_body(b_token[idx:end])
        primary = plain
        primary_end = end
        for ub in self.sorted_rev_roman_units:
            if b_token.startswith(ub, end):
                primary += self.rev_roman_units[ub]
                primary_end = end + len(ub)
                break
        readings = [primary]
        for ub in self.sorted_rev_roman_units:
            pos = idx + 1
            while pos < end:
                if (
                    b_token.startswith(ub, pos)
                    and pos + len(ub) == primary_end
                    and self._is_number_body(b_token[idx:pos])
                ):
                    alt = self._decode_number_body(b_token[idx:pos]) + self.rev_roman_units[ub]
                    readings.append(alt)
                    break
                pos += 1
        text = readings[0] if len(set(readings)) == 1 else self._join_candidates(readings)
        return text, primary_end - start_idx

    def _consume_numeric_sequence(self, b_token: str, start_idx: int) -> Tuple[str, int]:
        idx = start_idx + 1
        n = len(b_token)
        end = idx

        while end < n:
            c = b_token[end]
            if c in self.rev_digits:
                end += 1
                continue
            if c in self.rev_num_connectors and end + 1 < n and b_token[end + 1] in self.rev_digits:
                end += 1
                continue
            break

        unit, unit_at, unit_len = self._match_trailing_exempt_unit(b_token, idx, end)
        if unit:
            number = self._decode_number_body(b_token[idx:unit_at])
            return number + unit, unit_at + unit_len - start_idx

        if end > idx:
            unit, unit_len = self._match_exempt_unit_after(b_token, end)
            if unit:
                number = self._decode_number_body(b_token[idx:end])
                return number + unit, end + unit_len - start_idx

        return self._read_number_and_roman(b_token, idx, end, start_idx)

    def _match_word_abbr(self, b_token: str, i: int) -> Tuple[str, int]:
        for braille, word in self.rev_word_abbr_sorted:
            if b_token.startswith(braille, i):
                return word, len(braille)
        return "", 0

    def _read_symbol(self, table: dict, token: str, idx: int) -> Tuple[Optional[str], int]:
        """두 칸 자모(ㅒ, ㅄ 등)를 한 칸 자모보다 먼저 읽는다."""
        for length in (2, 1):
            if idx + length <= len(token) and token[idx:idx + length] in table:
                return table[token[idx:idx + length]], length
        return None, 0

    @staticmethod
    def _join_candidates(chars: List[str]) -> str:
        ordered = []
        for char in chars:
            if char not in ordered:
                ordered.append(char)
        return "|".join(ordered)

    def _match_punct(self, b_token: str, i: int) -> Tuple[str, int]:
        n = len(b_token)
        for length in range(min(5, n - i), 0, -1):
            cell = b_token[i:i + length]
            senses = self.punct_senses.get(cell)
            if not senses:
                continue
            at_end = i + length >= n
            at_start = i == 0
            chars = [sense["char"] for sense in senses]
            # ⠦: 문장 끝이면 물음표, 단어 앞이면 여는 따옴표 후보를 모두 남긴다.
            if cell == "⠦":
                if at_end:
                    return "?", length
                if at_start:
                    return self._join_candidates([c for c in chars if c in ("“", "《")]), length
            # ⠴: 부호 자리의 닫는 따옴표. ”와 》를 함께 남긴다.
            if cell == "⠴":
                return self._join_candidates([c for c in chars if c in ("”", "》")]), length
            if cell == "⠴⠴":
                return self._join_candidates([c for c in chars if c in ("×", "○", "△")]), length
            # ⠐: 숫자 사이가 아니고 부호 자리이면 쉼표 또는 아포스트로피.
            if cell == "⠐":
                return self._join_candidates([c for c in chars if c in (",", "'")]), length
            if cell == "⠤⠤":
                return self._join_candidates([c for c in chars if c in ("~", "—", "□")]), length
            if len(set(chars)) > 1:
                return self._join_candidates(chars), length
            return chars[0], length
        return "", 0

    def _decode_single_syllable(self, b_token: str, start_idx: int) -> Tuple[str, int]:
        is_tense = False
        offset = 0

        if self.geot_unicode and self.geot_tensed:
            geot_token = self.TENSER_SIGN + self.geot_unicode
            if b_token.startswith(geot_token, start_idx):
                tensed = "껏" if "껏" in self.geot_tensed else next(iter(self.geot_tensed))
                return tensed, len(geot_token)

        # 1. 6점(⠠) 처리 정밀화: 된소리표 vs 초성 'ㅅ' 구분
        if b_token[start_idx] == self.TENSER_SIGN:
            if start_idx + 1 < len(b_token):
                next_c = b_token[start_idx + 1]
                
                # Case A: 된소리표 뒤에 '가' 계열 약자가 오는 경우 (예: ⠠⠇ -> 싸, ⠠⠫ -> 까)
                # 뒤에 모음이 오면 약자가 아니라 된소리 초성이다 (떠, 뻐, 쩌).
                follows = b_token[start_idx + 2] if start_idx + 2 < len(b_token) else ""
                follows_vowel = bool(follows) and (follows in self.rev_jungsung or follows in self.rev_vowel_coda)
                follows_jong = bool(follows) and follows in self.rev_jongsung
                ga_cho = self._ga_choseong(next_c)
                use_ga = bool(ga_cho) and not (follows_vowel and not follows_jong)
                if follows_vowel and follows_jong and not self.prefer_abbr_over_jungsung:
                    use_ga = False
                if use_ga and follows_jong:
                    jong, jong_len = self._read_symbol(self.rev_jongsung, b_token, start_idx + 2)
                    jong_cells = b_token[start_idx + 2:start_idx + 2 + jong_len]
                    if jong_cells in self.rev_jungsung:
                        more, _ = self._read_symbol(self.rev_jongsung, b_token, start_idx + 2 + jong_len)
                        if more:
                            use_ga = False
                if use_ga:
                    jong, jong_len = self._read_symbol(self.rev_jongsung, b_token, start_idx + 2)
                    if jong:
                        return self._compose_ga(ga_cho, jong, True), 2 + jong_len
                    return self._compose_ga(ga_cho, "", True), 2

                # Case B: 된소리표 뒤에 기본 초성이 오는 경우 (예: ⠠ + ⠈ -> ㄲ, ⠠ + ⠊ + 모음 -> 떠)
                elif next_c in self.rev_ga_series or next_c in self.rev_chosung:
                    is_tense = True
                    offset = 1

                # Case C: 6점 뒤에 바로 중성이 오는 경우 (예: ⠠ + ⠣ -> '사'의 풀어쓰기 형태)
                # 된소리표가 아니라 초성 'ㅅ'으로 단독 해석
                elif next_c in self.rev_jungsung:
                    is_tense = False
                    offset = 0
            else:
                # 6점 단독으로 끝난 경우: 해석 불가 공백이 아니라 초성 'ㅅ'으로 반환
                return "ㅅ", 1

        idx = start_idx + offset
        c1 = b_token[idx]
        c2 = b_token[idx + 1] if idx + 1 < len(b_token) else None

        def apply_tense(cho_char: str) -> str:
            return self.REV_TENSER_MAP.get(cho_char, cho_char) if is_tense else cho_char

        if not is_tense:
            ga_text, ga_len = self._try_ga_syllable(b_token, idx)
            if ga_len:
                return ga_text, ga_len

        # 1. 초성 + 모음받침 약자. '영' 점형은 ㅅ·ㅆ·ㅈ·ㅉ·ㅊ 뒤에서 ㅓ+ㅇ으로 읽는다.
        if c1 in self.rev_chosung and c2 and c2 in self.rev_vowel_coda:
            jung, jong = self.rev_vowel_coda[c2]
            cho = apply_tense(self.rev_chosung[c1])
            if c2 == self.yeong_unicode and cho in self.yeong_override_initials:
                jung = self.yeong_surface_vowel
                jong = self.yeong_surface_jong
            return self.compose(cho, jung, jong), offset + 2

        # 2. 초성 + 중성 + 선택적 종성. ㅒ·ㅙ·ㅄ처럼 두 칸인 자모를 먼저 읽는다.
        if c1 in self.rev_chosung:
            jung, jung_len = self._read_symbol(self.rev_jungsung, b_token, idx + 1)
            if jung:
                cho = apply_tense(self.rev_chosung[c1])
                jong, jong_len = self._read_symbol(self.rev_jongsung, b_token, idx + 1 + jung_len)
                if jong:
                    return self.compose(cho, jung, jong), offset + 1 + jung_len + jong_len
                return self.compose(cho, jung, ""), offset + 1 + jung_len

        if is_tense:
            return "", 0

        # 4. 모음받침 약자 단독
        if c1 in self.rev_vowel_coda:
            jung, jong = self.rev_vowel_coda[c1]
            return self.compose("ㅇ", jung, jong), 1

        # 5. 초성 ㅇ 생략. 두 칸 모음·받침을 한 음절로 읽는다.
        jung, jung_len = self._read_symbol(self.rev_jungsung, b_token, idx)
        if jung:
            jong, jong_len = self._read_symbol(self.rev_jongsung, b_token, idx + jung_len)
            if jong:
                return self.compose("ㅇ", jung, jong), jung_len + jong_len
            return self.compose("ㅇ", jung, ""), jung_len

        # 6. 초성 단독 잔여물. ⠐와 ⠰는 모음이 붙을 때만 ㄹ·ㅊ이고, 아니면 부호 자리다.
        if c1 in self.rev_chosung and c1 not in (self.chosung_map.get("ㄹ"), self.chosung_map.get("ㅊ")):
            return self.rev_chosung[c1], 1

        return "", 0