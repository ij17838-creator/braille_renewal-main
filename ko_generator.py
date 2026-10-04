import json
import random
import re
from typing import Dict, Any, List, Optional, Tuple, Set

from data_paths import find_data_file
from ko_syntax_analyzer import BrailleRuleValidator

try:
    from ko_parser import KoreanBrailleEngine
except ImportError:
    KoreanBrailleEngine = None

# =====================================================================
# 한글 음절 분해 / 결합 유틸리티
# =====================================================================
CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
JUNGSUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
JONGSUNG_LIST = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

_MIRROR_H = {1: 4, 4: 1, 2: 5, 5: 2, 3: 6, 6: 3}
_MIRROR_V = {1: 3, 3: 1, 4: 6, 6: 4, 2: 2, 5: 5}
_RIEUL_DROP_FIELDS = ("with_ni", "with_neun", "with_b_nida", "with_si", "with_so")
_RIEUL_KEEP_FIELDS = ("with_myeon",)


def decompose_hangul(ch: str) -> Optional[Tuple[str, str, str]]:
    """한글 음절을 (초성, 중성, 종성)으로 분해"""
    if not ch or not ('\uac00' <= ch <= '\ud7a3'):
        return None
    code = ord(ch) - 0xac00
    jong_idx = code % 28
    code //= 28
    jung_idx = code % 21
    cho_idx = code // 21
    return CHOSUNG_LIST[cho_idx], JUNGSUNG_LIST[jung_idx], JONGSUNG_LIST[jong_idx]


def compose_hangul(cho: str, jung: str, jong: str = "") -> Optional[str]:
    """초성, 중성, 종성을 조합하여 한글 음절 생성"""
    try:
        cho_idx = CHOSUNG_LIST.index(cho)
        jung_idx = JUNGSUNG_LIST.index(jung)
        jong_idx = JONGSUNG_LIST.index(jong) if jong else 0
        code = 0xac00 + (cho_idx * 21 + jung_idx) * 28 + jong_idx
        return chr(code)
    except (ValueError, IndexError):
        return None


def _dot_seq(dots: Any) -> Tuple[Tuple[int, ...], ...]:
    """점형 목록을 칸 단위 튜플로 정규화. 빈 점형은 초성 ㅇ처럼 칸이 없다."""
    if not dots:
        return tuple()
    if isinstance(dots[0], int):
        return (tuple(sorted(dots)),)
    return tuple(tuple(sorted(cell)) for cell in dots if isinstance(cell, list))


def _mirror_cell(cell: Tuple[int, ...], table: Dict[int, int]) -> Tuple[int, ...]:
    return tuple(sorted(table[d] for d in cell if d in table))


def _variant_seqs(seq: Tuple[Tuple[int, ...], ...]) -> List[Tuple[Tuple[int, ...], ...]]:
    """한 칸의 점 추가/누락, 좌우 대칭, 상하 반전으로 이웃 점형을 만든다."""
    variants: List[Tuple[Tuple[int, ...], ...]] = []
    if not seq:
        for dot in range(1, 7):
            variants.append(((dot,),))
        return variants
    variants.append(tuple(_mirror_cell(cell, _MIRROR_H) for cell in seq))
    variants.append(tuple(_mirror_cell(cell, _MIRROR_V) for cell in seq))
    for index, cell in enumerate(seq):
        present = set(cell)
        for dot in range(1, 7):
            nxt = set(present)
            if dot in nxt:
                nxt.remove(dot)
            else:
                nxt.add(dot)
            if not nxt:
                continue
            changed = tuple(sorted(nxt))
            if changed == cell:
                continue
            variants.append(seq[:index] + (changed,) + seq[index + 1:])
    return variants


def _example_token(text: str) -> Optional[str]:
    """규칙 문장의 '예: 4사분기'처럼 적힌 첫 예시를 읽는다."""
    if not text:
        return None
    matched = re.search(r"예:\s*([0-9A-Za-z가-힣]+)", text)
    return matched.group(1) if matched else None


def _tenser_of(ko_data: Dict[str, Any]) -> Dict[str, str]:
    """초성 점형이 ⠠ + 기본 자음이면 기본 자음 -> 된소리 초성을 돌려준다."""
    items = ko_data.get("chosung", {}).get("items", {})
    sign = "⠠"
    plain: Dict[str, str] = {}
    tensed: Dict[str, str] = {}
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
            mapping[base] = char
    return mapping


def _geot_spell_out(ko_data: Dict[str, Any]) -> Optional[str]:
    """'껐'은 것 약자에 된소리표를 붙이지 않고 꺼 뒤에 받침 ㅆ을 적는다."""
    geot = ko_data.get("abbreviation_syllable", {}).get("items", {}).get("것", {})
    if not geot.get("ssang_jong_exception"):
        return None
    parts = decompose_hangul("것")
    tense_cho = _tenser_of(ko_data).get(parts[0]) if parts else None
    if not parts or not tense_cho:
        return None
    return compose_hangul(tense_cho, parts[1], "ㅆ")


def _delimiter_pairs(marks: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """ko_marks.json의 여는/닫는 부호를 이름 기준으로 짝짓는다."""
    opens = marks.get("opening_delimiters", {}).get("items", {})
    closes = marks.get("closing_delimiters", {}).get("items", {})
    close_by_label = {}
    for ch, item in closes.items():
        label = str(item.get("word", "")).replace("닫는", "").strip()
        close_by_label[label] = ch
    pairs = []
    for ch, item in opens.items():
        label = str(item.get("word", "")).replace("여는", "").strip()
        if label in close_by_label:
            pairs.append((ch, close_by_label[label], label))
    if len(pairs) != len(opens) and len(opens) == len(closes):
        pairs = [(op, cl, "") for op, cl in zip(opens, closes)]
    return pairs


def dots_to_braille_char(dots: List[int]) -> str:
    """점 번호 리스트([1, 2, 4] 등)를 점자 유니코드 한 글자로 변환"""
    mask = 0
    for d in dots:
        if 1 <= d <= 6:
            mask |= (1 << (d - 1))
    return chr(0x2800 + mask)


def braille_char_to_dots(b_char: str) -> List[int]:
    """점자 유니코드 한 글자를 점 번호 리스트로 역변환"""
    val = ord(b_char) - 0x2800
    if not (0 <= val <= 63):
        return []
    return [i + 1 for i in range(6) if (val & (1 << i))]


def _has_batchim(text: str) -> bool:
    parts = decompose_hangul(text[-1]) if text else None
    return bool(parts and parts[2])


def _jongseong(text: str) -> str:
    parts = decompose_hangul(text[-1]) if text else None
    return parts[2] if parts else ""


# =====================================================================
# 인지과학 기반 점자 오답 생성기 (Cognitive Distractor Engine)
# =====================================================================
class CognitiveDistractorEngine:
    """
    점자 학습자의 인지적 오류 패턴을 모델링한 방해 블록(Distractor) 생성기.
    이웃 점형은 ko.json / ko_marks.json / numbers.json / ko_number_rules.json의
    실제 점 번호에서 만든다.
    1. 점 누락/추가 (해밍 거리 1)
    2. 좌우 대칭, 상하 반전
    3. 초성 점형과 종성 점형을 뒤바꾼 자리
    4. 약자 예외: 사 풀어쓰기, 영 약자 덮어쓰기, 것/껏/껐
    """

    def __init__(
        self,
        ko_data: Dict[str, Any],
        marks_data: Optional[Dict[str, Any]] = None,
        numbers_data: Optional[Dict[str, Any]] = None,
        num_rules: Optional[Dict[str, Any]] = None,
    ):
        self.ko = ko_data
        self.marks = marks_data or {}
        self.numbers = numbers_data or {}
        self.num_rules = num_rules or {}
        self.syllable_abbr = ko_data.get("abbreviation_syllable", {}).get("items", {})
        self.char_alts: Dict[str, Set[str]] = {}
        self.single_pool: List[str] = []
        self._build_alts()

    def _add_alt(self, source: str, other: str) -> None:
        if not source or not other or source == other or len(other) != 1:
            return
        self.char_alts.setdefault(source, set()).add(other)

    def _index_role(self, items: Dict[str, Any]) -> Dict[str, Set[str]]:
        """같은 역할(초성/중성/종성) 안에서 점형이 이웃인 글자를 묶는다."""
        by_seq: Dict[Tuple[Tuple[int, ...], ...], List[str]] = {}
        seqs: Dict[str, Tuple[Tuple[int, ...], ...]] = {}
        for char, item in items.items():
            if not char:
                continue
            seq = _dot_seq(item.get("dots"))
            seqs[char] = seq
            by_seq.setdefault(seq, []).append(char)
        alts: Dict[str, Set[str]] = {char: set() for char in seqs}
        for char, seq in seqs.items():
            for variant in _variant_seqs(seq):
                for other in by_seq.get(variant, []):
                    if other != char:
                        alts[char].add(other)
        return alts

    def _build_alts(self) -> None:
        cho_items = self.ko.get("chosung", {}).get("items", {})
        jung_items = self.ko.get("jungsung", {}).get("items", {})
        jong_items = self.ko.get("jongsung", {}).get("items", {})
        self.cho_alts = self._index_role(cho_items)
        self.jung_alts = self._index_role(jung_items)
        self.jong_alts = self._index_role(jong_items)

        cho_seq = {char: _dot_seq(item.get("dots")) for char, item in cho_items.items()}
        jong_seq = {char: _dot_seq(item.get("dots")) for char, item in jong_items.items()}
        cho_by_seq: Dict[Tuple, List[str]] = {}
        jong_by_seq: Dict[Tuple, List[str]] = {}
        for char, seq in cho_seq.items():
            cho_by_seq.setdefault(seq, []).append(char)
        for char, seq in jong_seq.items():
            jong_by_seq.setdefault(seq, []).append(char)
        for char, seq in cho_seq.items():
            final_seq = jong_seq.get(char)
            if not final_seq:
                continue
            for other in cho_by_seq.get(final_seq, []):
                self.cho_alts.setdefault(char, set()).add(other)
        for char, seq in jong_seq.items():
            initial_seq = cho_seq.get(char)
            if not initial_seq:
                continue
            for other in jong_by_seq.get(initial_seq, []):
                self.jong_alts.setdefault(char, set()).add(other)

        self.single_dot_jongs = [
            char for char, seq in jong_seq.items()
            if len(seq) == 1 and len(seq[0]) == 1
        ]

        abbr_by_seq: Dict[Tuple, List[str]] = {}
        for char, item in self.syllable_abbr.items():
            abbr_by_seq.setdefault(_dot_seq(item.get("dots")), []).append(char)
            self.single_pool.append(char)
        for char, item in self.syllable_abbr.items():
            for variant in _variant_seqs(_dot_seq(item.get("dots"))):
                for other in abbr_by_seq.get(variant, []):
                    self._add_alt(char, other)

        self._add_yeong_pairs()
        self._add_geot_pairs()
        self._add_mark_and_digit_alts()

    def _add_yeong_pairs(self) -> None:
        yeong = self.syllable_abbr.get("영", {})
        override = yeong.get("initial_vowel_override") or {}
        initials = override.get("initials") or []
        surface_vowel = override.get("surface_vowel") or ""
        surface_jong = override.get("surface_jong") or ""
        yeong_parts = decompose_hangul("영")
        spell_jung = yeong_parts[1] if yeong_parts else ""
        if not initials or not surface_vowel or not surface_jong or not spell_jung:
            return
        if spell_jung == surface_vowel:
            return
        for cho in initials:
            abbreviated = compose_hangul(cho, surface_vowel, surface_jong)
            spelled = compose_hangul(cho, spell_jung, surface_jong)
            if not abbreviated or not spelled:
                continue
            self._add_alt(abbreviated, spelled)
            self._add_alt(spelled, abbreviated)
            self.single_pool.extend([abbreviated, spelled])

    def _add_geot_pairs(self) -> None:
        geot = self.syllable_abbr.get("것", {})
        family = ["것"] if "것" in self.syllable_abbr else []
        family.extend(ch for ch in geot.get("tensed_same_abbreviation", []) if len(ch) == 1)
        spelled = _geot_spell_out(self.ko)
        if spelled:
            family.append(spelled)
        for left in family:
            for right in family:
                self._add_alt(left, right)
            self.single_pool.append(left)

    def _add_mark_and_digit_alts(self) -> None:
        for category in (
            "terminal_punctuation",
            "pausal_punctuation",
            "opening_delimiters",
            "closing_delimiters",
            "connectors_and_symbols",
            "placeholder_marks",
        ):
            chars = [ch for ch in self.marks.get(category, {}).get("items", {}) if len(ch) == 1]
            for ch in chars:
                for other in chars:
                    self._add_alt(ch, other)
                self.single_pool.append(ch)
        for char, alts in self._index_role(self.numbers.get("digits", {})).items():
            if len(char) != 1:
                continue
            for other in alts:
                self._add_alt(char, other)
        roman = (
            self.num_rules.get("collision_resolutions", {})
            .get("trailing_letters", {})
            .get("roman_unit_symbols", {})
        )
        letters = sorted({ch for unit in roman for ch in unit if ch.isalpha()})
        for ch in letters:
            for other in letters:
                self._add_alt(ch, other)

    def generate_confusable_blocks(self, target: str, count: int = 3) -> List[str]:
        pool: Set[str] = set(self.char_alts.get(target, set()))
        parts = decompose_hangul(target) if len(target) == 1 else None
        if parts:
            cho, jung, jong = parts
            for alt_cho in self.cho_alts.get(cho, ()):
                composed = compose_hangul(alt_cho, jung, jong)
                if composed:
                    pool.add(composed)
            for alt_jung in self.jung_alts.get(jung, ()):
                composed = compose_hangul(cho, alt_jung, jong)
                if composed:
                    pool.add(composed)
            if jong:
                pool.add(compose_hangul(cho, jung, "") or "")
                for alt_jong in self.jong_alts.get(jong, ()):
                    composed = compose_hangul(cho, jung, alt_jong)
                    if composed:
                        pool.add(composed)
            else:
                for coda in self.single_dot_jongs:
                    composed = compose_hangul(cho, jung, coda)
                    if composed:
                        pool.add(composed)

        pool.discard(target)
        pool.discard("")
        pool = {item for item in pool if item and len(item) == 1}

        fallback = [item for item in self.single_pool if item and item != target and len(item) == 1]
        random.shuffle(fallback)
        for item in fallback:
            if len(pool) >= count:
                break
            pool.add(item)

        result = list(pool)
        random.shuffle(result)
        return result[:count]


# =====================================================================
# 통제된 슬롯 문장 템플릿 엔진 (Sentence Slot Engine)
# =====================================================================
class SentenceSlotEngine:
    """
    ko.json, lexicon_ko.json, ko_marks.json, ko_number_rules.json의 규칙만으로
    약어 위치, 약자 예외, 단위 경계, 문장부호 자리, 불규칙 활용을 맞춘다.
    """

    def __init__(
        self,
        ko_data: Dict[str, Any],
        lexicon_data: Dict[str, Any],
        marks_data: Dict[str, Any],
        num_rules: Dict[str, Any],
        numbers_data: Optional[Dict[str, Any]] = None,
    ):
        self.ko = ko_data
        self.lexicon = lexicon_data
        self.marks = marks_data
        self.num_rules = num_rules
        self.numbers = numbers_data or {}

        self.validator = BrailleRuleValidator()
        self.validator.ko_data = ko_data
        self.validator.marks_data = marks_data
        self.validator.number_rules = num_rules
        self.validator.lexicon = lexicon_data
        self.validator._init_rules()

        word_block = self.ko.get("abbreviation_word", {})
        self.word_abbr_standalone = word_block.get("rule", {}).get("position") == "standalone"
        self.wordsigns = list(word_block.get("items", {}).keys())
        syllable_items = self.ko.get("abbreviation_syllable", {}).get("items", {})
        self.syllable_items = syllable_items
        self.syllable_abbrs = list(syllable_items.keys())
        self.ga_series = [key for key, item in syllable_items.items() if item.get("type") == "ga_series"]
        self.vowel_coda = [key for key, item in syllable_items.items() if item.get("type") == "vowel_coda_series"]

        trailing = num_rules.get("collision_resolutions", {}).get("trailing_letters", {})
        self.exempt_units = list(trailing.get("exempt_units", []))
        boundary = trailing.get("unit_boundary", {})
        self.josa = {item for item in boundary.get("josa", []) if item}
        self.roman_units = list(trailing.get("roman_unit_symbols", {}).keys())
        self.connector_chars = {
            item.get("char")
            for item in num_rules.get("symbols", {}).values()
            if item.get("char") and item.get("persists_numeric_mode")
        }
        prefix_rule = self.ko.get("special_rules", {}).get("number_prefix_rule", {})
        self.affected_initials = set(prefix_rule.get("affected_initials", []))
        self.affected_abbreviations = set(prefix_rule.get("affected_abbreviations", []))
        self.number_gap = " " if prefix_rule.get("action", "terminate_number_with_space") == "terminate_number_with_space" else ""

        sa_rules = syllable_items.get("사", {}).get("exception_rules") or {}
        self.sa_vowel_example = _example_token(sa_rules.get("vowel_connection", "")) if "vowel_connection" in sa_rules else None
        self.sa_number_example = _example_token(sa_rules.get("after_number", "")) if "after_number" in sa_rules else None
        self.geot_tensed = [
            ch for ch in syllable_items.get("것", {}).get("tensed_same_abbreviation", []) if len(ch) == 1
        ]
        self.geot_spell_out = _geot_spell_out(ko_data)
        yeong = syllable_items.get("영", {})
        override = yeong.get("initial_vowel_override") or {}
        self.yeong_initials = list(override.get("initials") or [])
        self.yeong_surface_vowel = override.get("surface_vowel") or ""
        self.yeong_surface_jong = override.get("surface_jong") or ""
        yeong_parts = decompose_hangul("영")
        self.yeong_spell_jung = yeong_parts[1] if yeong_parts else ""

        self.delimiter_pairs = _delimiter_pairs(marks_data)
        self.terminal_marks = list(self.marks.get("terminal_punctuation", {}).get("items", {}).keys())
        self.pausal_comma = "," if "," in self.marks.get("pausal_punctuation", {}).get("items", {}) else ""
        self.chosung_keys = [key for key in self.ko.get("chosung", {}).get("items", {}) if key]
        self.jungsung_keys = [key for key in self.ko.get("jungsung", {}).get("items", {}) if key]
        self.jongsung_keys = [key for key in self.ko.get("jongsung", {}).get("items", {}) if key]
        self.tenser_of = _tenser_of(ko_data)
        self.verbs = self._extract_lexicon_stems()

        self.subjects = ["나", "우리", "친구", "동생", "어머니", "사람"]
        self.objects = ["사과", "편지", "책", "물", "마음", "길"]

    def _extract_lexicon_stems(self) -> List[Dict[str, str]]:
        """lexicon_ko.json의 예외 어간을 검사기와 같은 활용형으로 펼친다."""
        stems: List[Dict[str, str]] = []
        seen = set()

        def add(
            base: str,
            sense_id: Optional[str] = None,
            meaning: Optional[str] = None,
            present_override: Optional[str] = None,
            present_rule: Optional[str] = None,
        ) -> None:
            if not base:
                return
            key = (base, sense_id or "", meaning or "", present_override or "")
            if key in seen:
                return
            present_eomi, past_eomi = self._eomi_pair(base)
            present = self.validator.analyze_conjugation_form(base, present_eomi, sense_id=sense_id, meaning=meaning)
            past = self.validator.analyze_conjugation_form(base, past_eomi, sense_id=sense_id, meaning=meaning)
            present_form = present_override or present.get("surface_form")
            past_form = past.get("surface_form")
            if not present_form or not past_form or past.get("ambiguous"):
                return
            if not present_override and present.get("ambiguous"):
                return
            seen.add(key)
            past_rule = past.get("rule_applied") or ""
            entry = {
                "base": base,
                "past": past_form,
                "present": present_form,
                "past_rule": past_rule,
                "present_rule": present_rule or present.get("rule_applied") or "",
                "rule": past_rule,
            }
            if sense_id:
                entry["sense_id"] = sense_id
            if meaning:
                entry["meaning"] = meaning
            stems.append(entry)

        for rule in self.lexicon.get("irregular_rules", {}).values():
            transform = rule.get("transformation") or {}
            target = rule.get("target_stem")
            if isinstance(target, str) and target:
                add(target)
            for item in transform.get("example_stems") or []:
                base = item.get("base")
                if not base:
                    continue
                add(base, item.get("sense_id"), item.get("meaning"))
                for field in _RIEUL_DROP_FIELDS:
                    surface = item.get(field)
                    if isinstance(surface, str) and surface and "가" <= surface[0] <= "힣" and not surface.endswith("-"):
                        add(base, item.get("sense_id"), item.get("meaning"), surface, "ㄹ 탈락")
                for field in _RIEUL_KEEP_FIELDS:
                    surface = item.get(field)
                    if isinstance(surface, str) and surface and "가" <= surface[0] <= "힣" and not surface.endswith("-"):
                        add(base, item.get("sense_id"), item.get("meaning"), surface, "ㄹ 유지")
            for bucket in (rule.get("regular_exceptions"), transform.get("regular_exceptions")):
                for item in bucket or []:
                    if item.get("base"):
                        add(item["base"])
            inserted = (transform.get("inserted_vowel") or {}).get("yang_vowel_monosyllabic_exception") or {}
            for item in inserted.get("examples") or []:
                if item.get("base"):
                    add(item["base"])
            groups = transform.get("contrasting_rules") or {}
            for group in groups.values():
                if not isinstance(group, dict):
                    continue
                for item in group.get("examples") or []:
                    if item.get("base"):
                        add(item["base"], item.get("sense_id"), item.get("meaning"))

        hieut = self.lexicon.get("irregular_rules", {}).get("hieut", {})
        h_text = json.dumps(hieut.get("transformation") or {}, ensure_ascii=False)
        for stem in re.findall(r"([가-힣]{1,6})다", h_text):
            parts = decompose_hangul(stem[-1])
            if parts and parts[2] == hieut.get("target_final_consonant", "ㅎ"):
                add(stem)
        return stems

    def _eomi_pair(self, stem: str) -> Tuple[str, str]:
        """어간 마지막 모음이 양성이면 아/았다, 아니면 어/었다."""
        parts = decompose_hangul(stem[-1]) if stem else None
        jung = parts[1] if parts else ""
        if jung in self.validator.yang_vowels:
            return "아", "았다"
        return "어", "었다"

    def _attach(self, word: str, with_batchim: str, without_batchim: str) -> str:
        particle = with_batchim if _has_batchim(word) else without_batchim
        if particle not in self.josa:
            return word
        if word == "나" and particle == "가":
            return "내가"
        return word + particle

    def _topic(self, word: str) -> str:
        return self._attach(word, "은", "는")

    def _object(self, word: str) -> str:
        return self._attach(word, "을", "를")

    def _subject(self, word: str) -> str:
        return self._attach(word, "이", "가")

    def _pick_verb(self, irregular_only: bool = False) -> Dict[str, str]:
        pool = self.verbs
        if irregular_only:
            narrowed = [
                item for item in self.verbs
                if item.get("present_rule") and not str(item["present_rule"]).startswith("규칙")
            ]
            pool = narrowed or self.verbs
        if not pool:
            raise ValueError("lexicon_ko.json에서 활용할 어간을 찾지 못했습니다.")
        return random.choice(pool)

    def _number_literal(self) -> str:
        kinds = ["int"]
        if "," in self.connector_chars:
            kinds.append("comma")
        if "." in self.connector_chars:
            kinds.append("decimal")
        if "-" in self.connector_chars:
            kinds.append("range")
        if "/" in self.connector_chars:
            kinds.append("fraction")
        kind = "int" if random.random() < 0.45 else random.choice(kinds)
        if kind == "comma":
            value = random.randint(1000, 9999)
            return f"{value:,}"
        if kind == "decimal":
            return f"{random.randint(1, 9)}.{random.randint(1, 9)}"
        if kind == "range":
            start = random.randint(1, 8)
            return f"{start}-{start + 1}"
        if kind == "fraction":
            return f"{random.randint(1, 3)}/{random.randint(1, 4)}"
        return str(random.randint(1, 12))

    def _hangul_tail(self, phrase: str) -> str:
        index = 0
        while index < len(phrase) and (phrase[index].isdigit() or phrase[index] in self.connector_chars):
            index += 1
        return phrase[index:]

    def _unit_josa_options(self, unit: str) -> List[str]:
        if _has_batchim(unit):
            directional = "로" if _jongseong(unit) == "ㄹ" else "으로"
            options = ["은", "을", "이", directional, "에", "에서", "도", "만"]
        else:
            options = ["는", "를", "가", "로", "에", "에서", "도", "만"]
        return [item for item in options if item in self.josa]

    def _exempt_unit_tokens(self) -> Tuple[List[str], List[str]]:
        number = self._number_literal()
        unit = random.choice(self.exempt_units)
        josa_options = [""] + self._unit_josa_options(unit)
        random.shuffle(josa_options)
        for josa in josa_options:
            phrase = f"{number}{unit}{josa}"
            tail = self._hangul_tail(phrase)
            if self.validator._match_exempt_unit(tail) != unit:
                continue
            if self.validator.check_number_letter_collision(phrase):
                continue
            return [phrase], ["number_exempt_unit"]
        phrase = f"{number}{unit}"
        return [phrase], ["number_exempt_unit"]

    def _roman_unit_tokens(self) -> Tuple[List[str], List[str]]:
        number = str(random.randint(1, 20))
        unit = random.choice(self.roman_units)
        phrase = f"{number}{unit}"
        return [phrase], ["roman_unit_direct_append"]

    def _sa_after_number_tokens(self) -> Tuple[List[str], List[str]]:
        if self.sa_number_example:
            return [self.sa_number_example], ["sa_after_number"]
        return [f"{random.randint(1, 9)}사"], ["sa_after_number"]

    def _collision_gap_tokens(self) -> Tuple[List[str], List[str]]:
        """충돌 초성·약자 운은 단위가 아니면 숫자 뒤에 띄어 숫자 입력을 끝낸다."""
        options = [ch for ch in self.affected_abbreviations if ch not in self.exempt_units]
        for syllable in self.ga_series:
            parts = decompose_hangul(syllable)
            if not parts or parts[0] not in self.affected_initials:
                continue
            if syllable in self.exempt_units:
                continue
            options.append(syllable)
        syllable = random.choice(options) if options else "운"
        number = str(random.randint(0, 9))
        if self.number_gap:
            return [number, syllable], ["number_prefix_gap"]
        return [f"{number}{self.number_gap}{syllable}"], ["number_prefix_gap"]

    def _quantity_tokens(self) -> Tuple[List[str], List[str]]:
        roll = random.random()
        if roll < 0.5 and self.exempt_units:
            return self._exempt_unit_tokens()
        if roll < 0.72 and self.roman_units:
            return self._roman_unit_tokens()
        if roll < 0.86:
            return self._sa_after_number_tokens()
        return self._collision_gap_tokens()

    def _embeds_word_abbr(self, word: str) -> bool:
        if not self.word_abbr_standalone:
            return False
        for abbr in self.wordsigns:
            start = 0
            while True:
                index = word.find(abbr, start)
                if index < 0:
                    break
                prev_c = word[index - 1] if index else ""
                next_c = word[index + len(abbr):index + len(abbr) + 1]
                if ("가" <= prev_c <= "힣") or ("가" <= next_c <= "힣"):
                    return True
                start = index + len(abbr)
        return False

    def _extra_syllable(self, avoid_vowel_onset: bool = False) -> str:
        for _ in range(30):
            cho = random.choice(self.chosung_keys)
            jung = random.choice(self.jungsung_keys)
            if avoid_vowel_onset and cho == "ㅇ":
                continue
            syllable = compose_hangul(cho, jung, "")
            if syllable:
                return syllable
        return "길"

    def _word_ga_with_coda(self) -> Tuple[str, List[str]]:
        base = random.choice(self.ga_series)
        parts = decompose_hangul(base)
        if not parts:
            return base, ["ga_series"]
        cho, jung, _ = parts
        if random.random() < 0.35 and cho in self.tenser_of:
            cho = self.tenser_of[cho]
        jong = "" if random.random() < 0.4 else random.choice(self.jongsung_keys)
        syllable = compose_hangul(cho, jung, jong) or base
        return syllable, ["ga_series_with_coda"]

    def _word_onset_vowel_coda(self) -> Tuple[str, List[str]]:
        base = random.choice(self.vowel_coda)
        parts = decompose_hangul(base)
        if not parts:
            return base, ["vowel_coda_series"]
        _, jung, jong = parts
        cho = random.choice(self.chosung_keys)
        syllable = compose_hangul(cho, jung, jong) or base
        return syllable, ["vowel_coda_with_onset"]

    def _word_sa(self) -> Tuple[str, List[str]]:
        if self.sa_vowel_example and random.random() < 0.5:
            return self.sa_vowel_example, ["sa_vowel_connection"]
        extra = self._extra_syllable(avoid_vowel_onset=True)
        if random.random() < 0.5:
            return "사" + extra, ["sa_abbreviation"]
        return extra + "사", ["sa_abbreviation"]

    def _word_yeong(self) -> Tuple[str, List[str]]:
        cho = random.choice(self.yeong_initials)
        if random.random() < 0.5:
            syllable = compose_hangul(cho, self.yeong_surface_vowel, self.yeong_surface_jong)
            return syllable or "성", ["yeong_abbreviation"]
        syllable = compose_hangul(cho, self.yeong_spell_jung, self.yeong_surface_jong)
        return syllable or "셩", ["yeong_spell_out"]

    def _word_geot(self) -> Tuple[str, List[str]]:
        family = ["것"] + self.geot_tensed
        if self.geot_spell_out and random.random() < 0.34:
            return self.geot_spell_out, ["geot_ssang_jong_exception"]
        head = random.choice(family)
        if random.random() < 0.5:
            return head, ["geot_abbreviation"]
        return head + self._extra_syllable(avoid_vowel_onset=False), ["geot_abbreviation"]

    def _word_simple_compound(self) -> Tuple[str, List[str]]:
        abbr = random.choice(self.syllable_abbrs)
        avoid_vowel = abbr == "사" and self.sa_vowel_example is not None
        extra = self._extra_syllable(avoid_vowel_onset=avoid_vowel)
        word = f"{abbr}{extra}" if random.random() < 0.5 else f"{extra}{abbr}"
        return word, ["compound_syllable"]

    def generate_compound_word(self) -> Dict[str, Any]:
        builders = [self._word_simple_compound]
        if self.ga_series:
            builders.append(self._word_ga_with_coda)
        if self.vowel_coda:
            builders.append(self._word_onset_vowel_coda)
        if "사" in self.syllable_items:
            builders.append(self._word_sa)
        if self.yeong_initials and self.yeong_surface_vowel and self.yeong_spell_jung:
            builders.append(self._word_yeong)
        if "것" in self.syllable_items:
            builders.append(self._word_geot)

        word, rules = self.syllable_abbrs[0], ["abbreviation_syllable"]
        for _ in range(16):
            candidate, candidate_rules = random.choice(builders)()
            if candidate and not self._embeds_word_abbr(candidate):
                word, rules = candidate, candidate_rules
                break
        return {"word": word, "used_rules": rules}

    def generate_slotted_sentence(self, level: int = 3) -> Dict[str, Any]:
        """
        Level 3: 주어 + 목적어 + 서술어
        Level 4: 단독 접속 약어 + 수량(단위/충돌 띄어쓰기/사 풀어쓰기) + 서술어
        Level 5: 문장부호 짝 + 단위 기호 + 불규칙 활용
        """
        subj = random.choice(self.subjects)
        obj = random.choice(self.objects)
        irregular_only = level >= 5
        verb_entry = self._pick_verb(irregular_only=irregular_only)
        if level >= 5:
            verb_rules = [verb_entry.get("present_rule", ""), verb_entry.get("past_rule", "")]
        else:
            verb_rules = [verb_entry.get("past_rule", "")]
        meta: Dict[str, Any] = {"used_rules": verb_rules, "conjugation": verb_entry}
        tokens: List[str] = []

        if level <= 3:
            tokens = [self._topic(subj), self._object(obj), verb_entry["past"]]
            meta["structure"] = "S-O-V"
        elif level == 4:
            conn = random.choice(self.wordsigns)
            quantity, quantity_rules = self._quantity_tokens()
            subject = self._topic(subj)
            if self.pausal_comma and random.random() < 0.25:
                subject += self.pausal_comma
                meta["used_rules"].append("pausal_comma")
            tokens = [conn, subject, self._object(obj), *quantity, verb_entry["past"]]
            meta["structure"] = "CONJ-S-O-QUANTITY-V"
            meta["used_rules"].extend(quantity_rules)
        else:
            conn = random.choice(self.wordsigns)
            quantity, quantity_rules = self._quantity_tokens()
            inner = " ".join([self._object(obj), *quantity, verb_entry["present"]])
            opener, closer, label = random.choice(self.delimiter_pairs) if self.delimiter_pairs else ("“", "”", "큰따옴표")
            quoted = f"{opener}{inner}{closer}"
            if "따옴표" in label or "낫표" in label:
                tokens = [conn, self._subject(subj), quoted, "하고", "말했다"]
                meta["structure"] = "CONJ-S-QUOTATION-V"
            else:
                tokens = [conn, self._topic(subj), quoted, verb_entry["past"]]
                meta["structure"] = "CONJ-S-BRACKET-V"
            meta["used_rules"].extend(quantity_rules)
            meta["used_rules"].append("delimiter_pair")

        deduped = []
        for rule in meta["used_rules"]:
            if rule and rule not in deduped:
                deduped.append(rule)
        meta["used_rules"] = deduped
        return {"tokens": tokens, "meta": meta}


# =====================================================================
# 고도화된 한국어 점자 퀴즈 생성기 (KoreanBrailleQuizGenerator)
# =====================================================================
class KoreanBrailleQuizGenerator:
    def __init__(
        self,
        ko_path: Optional[str] = None,
        lexicon_path: Optional[str] = None,
        marks_path: Optional[str] = None,
        num_rules_path: Optional[str] = None,
        numbers_path: Optional[str] = None,
    ):
        ko_path = ko_path or find_data_file("ko.json")
        lexicon_path = lexicon_path or find_data_file("lexicon_ko.json")
        marks_path = marks_path or find_data_file("ko_marks.json")
        num_rules_path = num_rules_path or find_data_file("ko_number_rules.json")
        numbers_path = numbers_path or find_data_file("numbers.json")

        with open(ko_path, 'r', encoding='utf-8') as f:
            self.ko_data = json.load(f)
        with open(lexicon_path, 'r', encoding='utf-8') as f:
            self.lexicon_data = json.load(f)
        with open(marks_path, 'r', encoding='utf-8') as f:
            self.marks_data = json.load(f)
        with open(num_rules_path, 'r', encoding='utf-8') as f:
            self.num_rules_data = json.load(f)
        with open(numbers_path, 'r', encoding='utf-8') as f:
            self.numbers_data = json.load(f)

        self.distractor_engine = CognitiveDistractorEngine(
            self.ko_data, self.marks_data, self.numbers_data, self.num_rules_data
        )
        self.slot_engine = SentenceSlotEngine(
            self.ko_data, self.lexicon_data, self.marks_data, self.num_rules_data, self.numbers_data
        )

        if KoreanBrailleEngine is not None:
            self.braille_engine = KoreanBrailleEngine(
                ko_data=self.ko_data,
                marks_data=self.marks_data,
                numbers_data=self.numbers_data,
                number_rules=self.num_rules_data,
                lexicon_data=self.lexicon_data
            )
        else:
            self.braille_engine = None

        self.wordsigns = list(self.ko_data.get("abbreviation_word", {}).get("items", {}).keys())
        self.syllable_abbrs = list(self.ko_data.get("abbreviation_syllable", {}).get("items", {}).keys())
        geot = self.ko_data.get("abbreviation_syllable", {}).get("items", {}).get("것", {})
        self.level1_pool = self.wordsigns + self.syllable_abbrs + [
            ch for ch in geot.get("tensed_same_abbreviation", []) if len(ch) == 1
        ]
        self.terminal_marks = list(self.marks_data.get("terminal_punctuation", {}).get("items", {}).keys())

    def _finish_sentence(self, text: str, category: str) -> str:
        if category != "sentence":
            return text
        if any(text.endswith(mark) for mark in self.terminal_marks):
            return text
        if "." in self.terminal_marks:
            return text + "."
        if self.terminal_marks:
            return text + self.terminal_marks[0]
        return text

    def _translate(self, text: str) -> str:
        if self.braille_engine is None or not text:
            return ""
        try:
            res = self.braille_engine.text_to_braille(text)
        except Exception:
            return ""
        return res.get("braille", "") if isinstance(res, dict) else res

    def _generate_raw_data(self, level: int) -> Dict[str, Any]:
        """레벨별 통제된 원천 토큰 데이터 생성"""
        if level == 1:
            word = random.choice(self.level1_pool)
            return {"tokens": [word], "category": "word", "meta": {"type": "abbreviation_single"}}

        if level == 2:
            compound = self.slot_engine.generate_compound_word()
            return {
                "tokens": [compound["word"]],
                "category": "word",
                "meta": {"type": "compound_syllable", "used_rules": compound["used_rules"]},
            }

        sentence_data = self.slot_engine.generate_slotted_sentence(level=level)
        return {
            "tokens": sentence_data["tokens"],
            "category": "sentence",
            "meta": sentence_data["meta"],
        }

    def _unique_distractors(self, pool: List[str], banned: Set[str], count: int, single_char: bool = False) -> List[str]:
        found: List[str] = []
        seen = set()

        def accept(item: str) -> bool:
            if not item or item in banned or item in seen:
                return False
            if single_char and len(item) != 1:
                return False
            return True

        for item in pool:
            if not accept(item):
                continue
            seen.add(item)
            found.append(item)
            if len(found) >= count:
                break
        filler = [
            item for item in self.level1_pool + self.distractor_engine.single_pool
            if accept(item)
        ]
        random.shuffle(filler)
        for extra in filler:
            if len(found) >= count:
                break
            if extra in seen:
                continue
            seen.add(extra)
            found.append(extra)
        return found[:count]

    def _mutate_token(self, token: str) -> List[str]:
        mutated = []
        indexes = [i for i, ch in enumerate(token) if decompose_hangul(ch) or ch in self.distractor_engine.char_alts]
        if not indexes:
            indexes = list(range(len(token)))
        random.shuffle(indexes)
        for index in indexes[:4]:
            for alt in self.distractor_engine.generate_confusable_blocks(token[index], count=3):
                if len(alt) != 1 or alt == token[index]:
                    continue
                candidate = token[:index] + alt + token[index + 1:]
                if candidate != token:
                    mutated.append(candidate)
        return mutated

    def generate_quiz(
        self,
        input_mode: str = "KEYBOARD",
        level: int = 1,
        distractor_count: int = 3,
        block_granularity: str = "WORD"
    ) -> Dict[str, Any]:
        """
        입력 모드 및 인지과학 기반 오답 생성 규칙을 적용한 퀴즈 생성
        """
        raw = self._generate_raw_data(level=level)
        tokens = raw["tokens"]
        category = raw["category"]
        target_text = self._finish_sentence(" ".join(tokens), category)
        target_braille = self._translate(target_text)

        if input_mode.upper() == "KEYBOARD":
            return {
                "input_mode": "KEYBOARD",
                "level": level,
                "category": category,
                "target_text": target_text,
                "target_braille": target_braille,
                "tokens": tokens,
                "token_length": len(tokens),
                "char_length": len(target_text),
                "meta": raw.get("meta", {})
            }

        if input_mode.upper() == "BLOCK":
            granularity = block_granularity.upper()
            if category == "word" or granularity == "SYLLABLE":
                correct_blocks = [ch for ch in target_text if ch != " "]
                pool: List[str] = []
                for block in correct_blocks:
                    pool.extend(self.distractor_engine.generate_confusable_blocks(block, count=2))
                distractors = self._unique_distractors(pool, set(correct_blocks), distractor_count, single_char=True)
            else:
                correct_blocks = list(tokens)
                if category == "sentence" and self.terminal_marks:
                    ending = next((mark for mark in self.terminal_marks if target_text.endswith(mark)), "")
                    if ending and (not correct_blocks or not correct_blocks[-1].endswith(ending)):
                        correct_blocks.append(ending)
                pool = []
                for token in correct_blocks:
                    pool.extend(self._mutate_token(token))
                distractors = self._unique_distractors(pool, set(correct_blocks), distractor_count)

            all_blocks = [{"text": b, "is_distractor": False} for b in correct_blocks]
            all_blocks.extend([{"text": d, "is_distractor": True} for d in distractors])
            random.shuffle(all_blocks)

            return {
                "input_mode": "BLOCK",
                "block_granularity": granularity,
                "level": level,
                "category": category,
                "target_text": target_text,
                "target_braille": target_braille,
                "correct_sequence": correct_blocks,
                "available_blocks": [b["text"] for b in all_blocks],
                "block_details": all_blocks,
                "meta": raw.get("meta", {})
            }

        if input_mode.upper() == "TRIANGLE":
            seed = target_text[:1] if target_text else "가"
            distractors_text = self.distractor_engine.generate_confusable_blocks(seed, count=2)
            distractors_braille = []
            for dt in distractors_text:
                db = self._translate(dt)
                if db:
                    distractors_braille.append(db)

            return {
                "input_mode": "TRIANGLE",
                "level": level,
                "category": category,
                "target_text": target_text,
                "target_braille": target_braille,
                "distractors_braille": distractors_braille,
                "distractors_text": distractors_text,
                "prompt_audio": f"제시어 {target_text}에 알맞은 올바른 점자를 선택하세요.",
                "meta": raw.get("meta", {})
            }

        raise ValueError(f"Unsupported input_mode: {input_mode}")


# =====================================================================
# 실행 및 검증 예시
# =====================================================================
if __name__ == "__main__":
    generator = KoreanBrailleQuizGenerator(
        ko_path="ko.json",
        lexicon_path="lexicon_ko.json",
        marks_path="ko_marks.json",
        num_rules_path="ko_number_rules.json",
        numbers_path="numbers.json",
    )

    print("--- [TEST 1] Level 1: 블록 모드 (인지과학 오답 추출) ---")
    quiz1 = generator.generate_quiz(input_mode="BLOCK", level=1, distractor_count=3, block_granularity="SYLLABLE")
    print("정답 문장:", quiz1["target_text"])
    print("정답 시퀀스:", quiz1["correct_sequence"])
    print("제공 블록 (오답 포함):", quiz1["available_blocks"])

    print("\n--- [TEST 2] Level 4: 키보드 모드 (수량/단위 규정 반영) ---")
    quiz2 = generator.generate_quiz(input_mode="KEYBOARD", level=4)
    print("생성 문장:", quiz2["target_text"])
    print("메타 데이터:", quiz2["meta"])

    print("\n--- [TEST 3] Level 5: 블록 모드 (부호 및 복합 어절) ---")
    quiz3 = generator.generate_quiz(input_mode="BLOCK", level=5, distractor_count=3, block_granularity="WORD")
    print("정답 문장:", quiz3["target_text"])
    print("어절 블록:", quiz3["correct_sequence"])
    print("제공 블록:", quiz3["available_blocks"])
