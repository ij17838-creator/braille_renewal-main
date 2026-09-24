"""
ko_parser.py
한글 점자 양방향 변환 엔진 (Text <-> Braille)

주요 기능:
1. Text -> Braille (정방향 점역): 약어, 초성 ㅇ 생략, 수표 및 1급 기호표 규칙 적용, 된소리표(⠠) 처리, 영문 단위 기호 결합
2. Braille -> Text (역방향 복원): 점자 토큰 분해 및 음절/숫자 모드 복원, 된소리 역변환, 영문 단위 기호 역변환
3. 규정 준수: 한국 점자 규정 제17항(단위어 앞 1급 기호표 생략) 및 숫자 뒤 단위 기호 로마자표 생략 반영
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

        # 1. 단어 약어 (그리고, 그러나 등)
        self.word_abbr = {k: v["unicode"] for k, v in self.ko.get("abbreviation_word", {}).get("items", {}).items()}
        self.rev_word_abbr = {v: k for k, v in self.word_abbr.items()}

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

        # 3. 기본 자모음 매핑
        self.chosung_map = {k: v["unicode"] for k, v in self.ko.get("chosung", {}).get("items", {}).items()}
        self.rev_chosung = {v: k for k, v in self.chosung_map.items() if v}  # ㅇ(빈 문자열) 제외
        self.jungsung_map = {k: v["unicode"] for k, v in self.ko.get("jungsung", {}).get("items", {}).items()}
        self.rev_jungsung = {v: k for k, v in self.jungsung_map.items()}
        self.jongsung_map = {k: v["unicode"] for k, v in self.ko.get("jongsung", {}).get("items", {}).items() if k}
        self.rev_jongsung = {v: k for k, v in self.jongsung_map.items()}

        # 4. 숫자 및 지시표
        self.num_prefix = self.numbers.get("numeric_indicators", {}).get("num_prefix", {}).get("unicode", "⠼")
        self.grade1_prefix = self.numbers.get("grade1_indicators", {}).get("grade1_symbol", {}).get("unicode", "⠰")
        self.digits = {k: v["unicode"] for k, v in self.numbers.get("digits", {}).items()}
        self.rev_digits = {v: k for k, v in self.digits.items()}

        conn_data = self.numbers.get("connectors", {})
        self.num_connectors = {
            ",": conn_data.get("comma", {}).get("unicode", "⠂"),
            ".": conn_data.get("period", {}).get("unicode", "⠲"),
            "-": conn_data.get("hyphen", {}).get("unicode", "⠤"),
            "/": conn_data.get("fraction_slash", {}).get("unicode", "⠌")
        }
        self.numeric_space = conn_data.get("numeric_space", {}).get("unicode", "⠐")
        self.rev_num_connectors = {v: k for k, v in self.num_connectors.items()}

        self.affected_initials = set(
            self.ko.get("special_rules", {})
            .get("number_prefix_rule", {})
            .get("affected_initials", ["ㄴ", "ㄷ", "ㅁ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"])
        )

        # 한글 단위어 예외 목록 (한글 음절 충돌 방지용)
        self.exempt_units = set(
            self.num_rules.get("collision_resolutions", {})
            .get("trailing_letters", {})
            .get("exempt_units", ["년", "월", "일", "시", "분", "초", "동", "호", "층", "개", "명", "원", "미터", "킬로미터", "센티미터", "밀리미터", "그램", "킬로그램", "리터", "밀리리터"])
        )
        self.exempt_units_sorted = tuple(sorted(self.exempt_units, key=len, reverse=True))

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

        # 5. 문장부호
        self._init_punctuation()

    def _init_punctuation(self):
        self.punct_map = {}
        for cat in ["terminal_punctuation", "pausal_punctuation", "connectors_and_symbols", "placeholder_marks", "transcriber_and_formatting_tags"]:
            for k, v in self.marks.get(cat, {}).get("items", {}).items():
                self.punct_map[k] = v["unicode"]

        self.open_delims = {k: v["unicode"] for k, v in self.marks.get("opening_delimiters", {}).get("items", {}).items()}
        self.close_delims = {k: v["unicode"] for k, v in self.marks.get("closing_delimiters", {}).get("items", {}).items()}
        self.rev_punct = {v: k for k, v in self.punct_map.items()}
        for k, v in {**self.open_delims, **self.close_delims}.items():
            self.rev_punct[v] = k

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
        single_quote_open = False

        while i < n:
            ch = text[i]

            # 1. 공백 및 개행
            if ch in (' ', '\n', '\r'):
                out.append(ch)
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
                    in_number_mode = False
                    traces.append({"token": sub, "braille": b, "rule": "Multi-char Mark/Tag", "scope": "Reset numeric mode"})
                    i += length
                    matched_punct = True
                    break
            if matched_punct:
                continue

            # 3. 단어 약어 (독립 단어 여부 확인)
            matched_word = False
            for w, b_code in self.word_abbr.items():
                w_len = len(w)
                if text[i:i+w_len] == w:
                    next_c = text[i+w_len:i+w_len+1]
                    if not (next_c and '가' <= next_c <= '힣'):
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

            # 숫자 커넥터 (, . - /)
            if in_number_mode and ch in self.num_connectors:
                if i + 1 < n and text[i+1].isdigit():
                    b_conn = self.num_connectors[ch]
                    out.append(b_conn)
                    traces.append({"token": ch, "braille": b_conn, "rule": "Numeric Connector", "explanation": "수표 모드 유지 커넥터"})
                    i += 1
                    continue
                else:
                    in_number_mode = False

            # 6. 따옴표 열림/닫힘 판별
            if ch == '"':
                b_q = self.open_delims.get("“", "⠦") if not quote_open else self.close_delims.get("”", "⠴")
                quote_open = not quote_open
                out.append(b_q)
                in_number_mode = False
                traces.append({"token": ch, "braille": b_q, "rule": "Quote Delimiter", "explanation": "여는/닫는 큰따옴표"})
                i += 1
                continue
            elif ch == "'":
                b_sq = self.open_delims.get("‘", "⠠⠦") if not single_quote_open else self.close_delims.get("’", "⠴⠄")
                single_quote_open = not single_quote_open
                out.append(b_sq)
                in_number_mode = False
                traces.append({"token": ch, "braille": b_sq, "rule": "Single Quote Delimiter", "explanation": "여는/닫는 작은따옴표"})
                i += 1
                continue

            # 7. 일반 단일 문장부호
            if ch in self.punct_map:
                b = self.punct_map[ch]
                out.append(b)
                in_number_mode = False
                traces.append({"token": ch, "braille": b, "rule": "Punctuation", "explanation": "문장부호"})
                i += 1
                continue

                        # 8. 한글 음절 변환
            if '가' <= ch <= '힣':
                decomp = self.decompose(ch)
                cho, jung, jong = decomp
                prefix_indicator = ""
                rules_applied = []

                # 한국 점자 규정 제18항: 음절 약어 '사' 예외(풀어쓰기) 판별
                # 제18항 제2호: 숫자 바로 뒤에 '사'가 올 경우 풀어 적음 (예: "4사분기")
                # 제18항 제1호: '사' 뒤에 바로 모음으로 시작하는 음절이 이어지는 경우 풀어 적음 (예: "사이")
                is_sa_exception = False
                if ch == '사':
                    # 예외 1: 직전 위치가 숫자이거나 수표 모드 유지 상태였던 경우
                    if in_number_mode or (i > 0 and text[i-1].isdigit()):
                        is_sa_exception = True
                        rules_applied.append("제18항 제2호 적용: 숫자 뒤 '사' 예외 풀어쓰기('⠈⠣') 적용")

                    # 예외 2: 다음 글자가 초성 'ㅇ'으로 시작하여 모음으로 이어지는 음절인 경우
                    elif i + 1 < n and '가' <= text[i+1] <= '힣':
                        next_decomp = self.decompose(text[i+1])
                        if next_decomp and next_decomp[0] == 'ㅇ':
                            is_sa_exception = True
                            rules_applied.append("제18항 제1호 적용: 모음 연접 '사' 예외 풀어쓰기('⠈⠣') 적용")

                # 수표 뒤 초성 충돌 해결 시 한글 단위어 예외 적용 (슬라이싱 접두어 검사)
                if in_number_mode:
                    tail_text = text[i:]
                    is_exempt = tail_text.startswith(self.exempt_units_sorted)

                    if cho in self.affected_initials and not is_exempt:
                        prefix_indicator = self.grade1_prefix
                        rules_applied.append(f"수표 해제 및 초성 '{cho}' 충돌 방지 1급 기호표(⠰) 삽입")
                    in_number_mode = False

                if is_sa_exception:
                    # 초성 'ㅅ'(⠠, U+2804) + 모음 'ㅏ'(⠣, U+2823) -> "⠈⠣"
                    braille_syllable = self.chosung_map.get('ㅅ', '⠈') + self.jungsung_map.get('ㅏ', '⠣')
                    if jong:
                        braille_syllable += self.jongsung_map.get(jong, '')
                else:
                    braille_syllable, syl_rules = self._translate_hangul_syllable_with_trace(cho, jung, jong, ch)
                    rules_applied.extend(syl_rules)

                final_b = prefix_indicator + braille_syllable
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

        # A. 완전 일치 음절 ('것' 등)
        if raw_char in self.complete_syllables:
            rules.append(f"완전 일치 음절 약자 '{raw_char}' 적용")
            return self.complete_syllables[raw_char], rules

        # B. 초성 된소리 접두표(⠠) 분리 처리
        tenser_prefix = ""
        base_cho = cho
        if cho in self.TENSER_MAP:
            tenser_prefix = self.TENSER_SIGN
            base_cho = self.TENSER_MAP[cho]
            rules.append(f"된소리 초성 '{cho}' 된소리표(⠠) 적용")

        # C. '가' 계열 약자 (초성 + 'ㅏ')
        base_ga = base_cho + 'ㅏ'
        if jung == 'ㅏ' and base_ga in self.ga_series:
            ga_b = self.ga_series[base_ga]
            jong_b = self.jongsung_map[jong] if jong else ""
            rules.append(f"가 계열 약자 '{base_ga}' 적용" + (f" + 종성 '{jong}' 결합" if jong else ""))
            return tenser_prefix + ga_b + jong_b, rules

        # D. '모음+받침' 약자
        if (jung, jong) in self.vowel_coda_series:
            vc_b = self.vowel_coda_series[(jung, jong)]
            if base_cho == 'ㅇ':
                rules.append(f"초성 'ㅇ' 생략 및 모음+받침 약자 적용 (중성:{jung}, 종성:{jong})")
                return tenser_prefix + vc_b, rules
            else:
                cho_b = self.chosung_map.get(base_cho, "")
                rules.append(f"초성 '{cho}' + 모음+받침 약자 적용 (중성:{jung}, 종성:{jong})")
                return tenser_prefix + cho_b + vc_b, rules

        # E. 일반 자모음 분해
        cho_b = "" if base_cho == 'ㅇ' else self.chosung_map.get(base_cho, "")
        if base_cho == 'ㅇ':
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

                # 숫자 시퀀스 직후 영문 단위 기호 매칭 검사 (최장 일치)
                matched_unit = False
                for b_unit in self.sorted_rev_roman_units:
                    if b_token[i:].startswith(b_unit):
                        decoded.append(self.rev_roman_units[b_unit])
                        i += len(b_unit)
                        matched_unit = True
                        break
                if matched_unit:
                    continue

                continue

            # 2. 독립된 1급 기호표(⠰) 건너뛰기
            if b_token[i] == self.grade1_prefix:
                i += 1
                continue

            # 3. 2셀 문장부호 우선 매칭
            if i + 1 < n and b_token[i:i+2] in self.rev_punct:
                decoded.append(self.rev_punct[b_token[i:i+2]])
                i += 2
                continue
            if b_token[i] in self.rev_punct:
                decoded.append(self.rev_punct[b_token[i]])
                i += 1
                continue

            # 4. 완전 음절 약자 ('것' 등 다중 칸 지원)
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

            # 5. 한글 음절 단위 정밀 디코딩 (된소리표 포함)
            syllable, consumed = self._decode_single_syllable(b_token, i)
            if consumed > 0:
                decoded.append(syllable)
                i += consumed
            else:
                decoded.append(b_token[i])
                i += 1

        return "".join(decoded)

    def _consume_numeric_sequence(self, b_token: str, start_idx: int) -> Tuple[str, int]:
        res = []
        idx = start_idx + 1
        n = len(b_token)

        while idx < n:
            c = b_token[idx]
            if c in self.rev_digits:
                res.append(self.rev_digits[c])
                idx += 1
            elif c in self.rev_num_connectors and self.rev_num_connectors[c] in [",", "."]:
                if idx + 1 < n and b_token[idx + 1] in self.rev_digits:
                    res.append(self.rev_num_connectors[c])
                    idx += 1
                else:
                    break
            elif c in self.rev_num_connectors and self.rev_num_connectors[c] == "-":
                res.append("-")
                idx += 1
                break
            elif c == self.grade1_prefix:
                # 1급 기호표는 숫자 모드 종결자이므로 소비하고 종료
                idx += 1
                break
            else:
                break

        return "".join(res), idx - start_idx

    def _decode_single_syllable(self, b_token: str, start_idx: int) -> Tuple[str, int]:
        is_tense = False
        offset = 0

        # 1. 6점(⠠) 처리 정밀화: 된소리표 vs 초성 'ㅅ' 구분
        if b_token[start_idx] == self.TENSER_SIGN:
            if start_idx + 1 < len(b_token):
                next_c = b_token[start_idx + 1]
                
                # Case A: 된소리표 뒤에 '가' 계열 약자가 오는 경우 (예: ⠠⠇ -> 싸, ⠠⠫ -> 까)
                if next_c in self.rev_ga_series:
                    base_syl = self.rev_ga_series[next_c] # '사', '가' 등
                    base_cho = base_syl[0]
                    tense_cho = self.REV_TENSER_MAP.get(base_cho, base_cho)
                    # 3셀(된소리+약자+받침) 검사
                    if start_idx + 2 < len(b_token) and b_token[start_idx + 2] in self.rev_jongsung:
                        jong = self.rev_jongsung[b_token[start_idx + 2]]
                        return self.compose(tense_cho, 'ㅏ', jong), 3
                    return self.compose(tense_cho, 'ㅏ', ""), 2

                # Case B: 된소리표 뒤에 기본 초성이 오는 경우 (예: ⠠ + ⠈ -> ㄲ)
                elif next_c in self.rev_chosung:
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
        c3 = b_token[idx + 2] if idx + 2 < len(b_token) else None

        def apply_tense(cho_char: str) -> str:
            return self.REV_TENSER_MAP.get(cho_char, cho_char) if is_tense else cho_char

        # --- 아래는 기존 초/중/종성 매칭 로직 유지 ---
        # 1. 초성 + 중성 + 종성 (3셀)
        if c1 in self.rev_chosung and c2 and c2 in self.rev_jungsung and c3 and c3 in self.rev_jongsung:
            cho = apply_tense(self.rev_chosung[c1])
            return self.compose(cho, self.rev_jungsung[c2], self.rev_jongsung[c3]), offset + 3

        # 2. 초성 + 모음받침약자 (2셀)
        if c1 in self.rev_chosung and c2 and c2 in self.rev_vowel_coda:
            jung, jong = self.rev_vowel_coda[c2]
            cho = apply_tense(self.rev_chosung[c1])
            return self.compose(cho, jung, jong), offset + 2

        # 3. '가' 계열 약자 + 종성 (2셀)
        if c1 in self.rev_ga_series and c2 and c2 in self.rev_jongsung:
            cho = apply_tense(self.rev_ga_series[c1][0])
            return self.compose(cho, 'ㅏ', self.rev_jongsung[c2]), offset + 2

        # 4. 초성 + 중성 (2셀)
        if c1 in self.rev_chosung and c2 and c2 in self.rev_jungsung:
            cho = apply_tense(self.rev_chosung[c1])
            return self.compose(cho, self.rev_jungsung[c2], ""), offset + 2

        if is_tense:
            return "", 0

        # 5. 'ㅇ' 생략 모음 + 종성 (2셀)
        if c1 in self.rev_jungsung and c2 and c2 in self.rev_jongsung:
            return self.compose('ㅇ', self.rev_jungsung[c1], self.rev_jongsung[c2]), 2

        # 6. '가' 계열 약자 단독 (1셀)
        if c1 in self.rev_ga_series:
            return self.rev_ga_series[c1], 1

        # 7. 모음받침약자 단독 (1셀)
        if c1 in self.rev_vowel_coda:
            jung, jong = self.rev_vowel_coda[c1]
            return self.compose('ㅇ', jung, jong), 1

        # 8. 'ㅇ' 생략 모음 단독 (1셀)
        if c1 in self.rev_jungsung:
            return self.compose('ㅇ', self.rev_jungsung[c1], ""), 1

        # 9. 초성 단독 잔여물 (예: 초성 'ㅅ' 단독 6점)
        if c1 in self.rev_chosung:
            return self.rev_chosung[c1], 1

        return "", 0