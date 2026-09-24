import json
import random
import unicodedata
from typing import Dict, Any, List, Optional, Tuple, Set

from data_paths import find_data_file

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

def decompose_hangul(ch: str) -> Optional[Tuple[str, str, str]]:
    """한글 음절을 (초성, 중성, 종성)으로 분해"""
    if not ('\uac00' <= ch <= '\ud7a3'):
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

# =====================================================================
# 인지과학 기반 점자 오답 생성기 (Cognitive Distractor Engine)
# =====================================================================
class CognitiveDistractorEngine:
    """
    점자 학습자의 인지적 오류 패턴을 모델링한 방해 블록(Distractor) 생성기
    1. 점 누락/추가/이동 오류 (Hamming Distance = 1)
    2. 공간 반전 착오 (좌우 대칭, 상하 반전)
    3. 초성-종성 위치 전이 오류
    4. 약자-풀어쓰기 간섭 오류
    """
    def __init__(self, ko_data: Dict[str, Any]):
        self.ko = ko_data
        self.syllable_abbr = ko_data.get("abbreviation_syllable", {}).get("items", {})
        self.chosung_items = ko_data.get("chosung", {}).get("items", {})
        self.jungsung_items = ko_data.get("jungsung", {}).get("items", {})
        self.jongsung_items = ko_data.get("jongsung", {}).get("items", {})

        # 점자 유니코드 역참조 매핑 구성 (dots_tuple -> hangul/type)
        self._build_reverse_maps()

    def _build_reverse_maps(self):
        self.dot_to_char_map = {}
        for k, v in self.syllable_abbr.items():
            key = tuple(tuple(d) for d in v.get("dots", []))
            self.dot_to_char_map[key] = k

    def generate_confusable_blocks(self, target: str, count: int = 3) -> List[str]:
        distractors: Set[str] = set()
        dec = decompose_hangul(target)

        # 1. 약자 음절의 착오 생성
        if target in self.syllable_abbr:
            dots_list = self.syllable_abbr[target].get("dots", [])
            if dots_list:
                first_cell = dots_list[0]
                # 좌우 반전 (1↔4, 2↔5, 3↔6)
                h_mirror = sorted([({1:4, 4:1, 2:5, 5:2, 3:6, 6:3})[d] for d in first_cell])
                # 상하 반전 (1↔3, 4↔6, 2는 유지)
                v_mirror = sorted([({1:3, 3:1, 4:6, 6:4, 2:2, 5:5})[d] for d in first_cell])
                
                # 유사 약자 탐색
                for candidate_word, cand_val in self.syllable_abbr.items():
                    if cand_val.get("dots", []) == [h_mirror] or cand_val.get("dots", []) == [v_mirror]:
                        if candidate_word != target:
                            distractors.add(candidate_word)

        # 2. 음절 내부의 인지 오류 (초성/중성/종성의 변별 자질 오인)
        if dec:
            cho, jung, jong = dec
            
            # (1) 종성 유무 혼동: 종성이 있으면 탈락, 없으면 유사 종성 결합
            if jong:
                distractors.add(compose_hangul(cho, jung, "") or "")
                # 유사 받침 교체 (ㄴ <-> ㄹ, ㅁ <-> ㅇ)
                batchim_confusions = {'ㄴ': 'ㄹ', 'ㄹ': 'ㄴ', 'ㅁ': 'ㅇ', 'ㅇ': 'ㅁ', 'ㄱ': 'ㅂ', 'ㅂ': 'ㄱ'}
                if jong in batchim_confusions:
                    distractors.add(compose_hangul(cho, jung, batchim_confusions[jong]) or "")
            else:
                distractors.add(compose_hangul(cho, jung, "ㄴ") or "")
                distractors.add(compose_hangul(cho, jung, "ㄹ") or "")

            # (2) 중성(모음) 대칭 혼동 (ㅏ ↔ ㅓ, ㅗ ↔ ㅜ)
            vowel_mirrors = {'ㅏ': 'ㅓ', 'ㅓ': 'ㅏ', 'ㅗ': 'ㅜ', 'ㅜ': 'ㅗ', 'ㅑ': 'ㅕ', 'ㅕ': 'ㅑ', 'ㅐ': 'ㅔ', 'ㅔ': 'ㅐ'}
            if jung in vowel_mirrors:
                distractors.add(compose_hangul(cho, vowel_mirrors[jung], jong) or "")

            # (3) 초성 가획/점 추가 오류 (ㄱ ↔ ㅋ, ㄷ ↔ ㅌ, ㅂ ↔ ㅍ, ㅈ ↔ ㅊ)
            cho_additions = {'ㄱ': 'ㅋ', 'ㅋ': 'ㄱ', 'ㄷ': 'ㅌ', 'ㅌ': 'ㄷ', 'ㅂ': 'ㅍ', 'ㅍ': 'ㅂ', 'ㅈ': 'ㅊ', 'ㅊ': 'ㅈ', 'ㅅ': 'ㅆ'}
            if cho in cho_additions:
                distractors.add(compose_hangul(cho_additions[cho], jung, jong) or "")

        distractors.discard(target)
        distractors.discard("")
        
        # 부족분은 일반 약자나 유사 음절 풀에서 보충
        fallback_keys = list(self.syllable_abbr.keys())
        random.shuffle(fallback_keys)
        for fb in fallback_keys:
            if len(distractors) >= count:
                break
            if fb != target:
                distractors.add(fb)

        result = list(distractors)
        random.shuffle(result)
        return result[:count]


# =====================================================================
# 통제된 슬롯 문장 템플릿 엔진 (Sentence Slot Engine)
# =====================================================================
class SentenceSlotEngine:
    """
    JSON 데이터 풀(ko, lexicon, marks, number_rules)을 100% 결합하여
    문법 규칙 및 점자 표기 규칙을 만족하는 동적 문장 생성 엔진
    """
    def __init__(self, ko_data: Dict[str, Any], lexicon_data: Dict[str, Any], marks_data: Dict[str, Any], num_rules: Dict[str, Any]):
        self.ko = ko_data
        self.lexicon = lexicon_data
        self.marks = marks_data
        self.num_rules = num_rules
        
        self.wordsigns = list(self.ko.get("abbreviation_word", {}).get("items", {}).keys())
        self.syllable_abbrs = list(self.ko.get("abbreviation_syllable", {}).get("items", {}).keys())
        self.exempt_units = self.num_rules["collision_resolutions"]["trailing_letters"]["exempt_units"]
        self.roman_units = list(self.num_rules.get("collision_resolutions", {}).get("trailing_letters", {}).get("roman_unit_symbols", {}).keys())

        # 동사/형용사 어간 및 불규칙 풀 빌드
        self.verbs = self._extract_lexicon_stems()

    def _extract_lexicon_stems(self) -> List[Dict[str, str]]:
        stems = []
        irregulars = self.lexicon.get("irregular_rules", {})
        
        # 1. ㄷ 불규칙
        for item in irregulars.get("digeut", {}).get("transformation", {}).get("example_stems", []):
            stems.append({"base": item["base"], "past": item["vowel_trigger"] + "었다", "present": item["vowel_trigger"] + "어"})
        # 2. ㅂ 불규칙
        stems.append({"base": "돕", "past": "도왔다", "present": "도와"})
        stems.append({"base": "고맙", "past": "고마웠다", "present": "고마워"})
        # 3. ㅅ 불규칙
        for item in irregulars.get("siot", {}).get("transformation", {}).get("example_stems", []):
            stems.append({"base": item["base"], "past": item["transformed"] + "었다", "present": item["transformed"] + "어"})
        # 4. 르 불규칙
        for item in irregulars.get("reu", {}).get("transformation", {}).get("example_stems", []):
            base = item["base"]
            first_char = base[0]
            dec = decompose_hangul(first_char)
            if dec:
                new_first = compose_hangul(dec[0], dec[1], "ㄹ")
                vowel = "라" if dec[1] in ['ㅏ', 'ㅗ'] else "러"
                stems.append({"base": base, "past": f"{new_first}{vowel}다", "present": f"{new_first}{vowel}"})
        # 5. 규칙 용언 보강
        stems.extend([
            {"base": "먹", "past": "먹었다", "present": "먹어"},
            {"base": "가", "past": "갔다", "present": "가"},
            {"base": "보", "past": "보았다", "present": "봐"},
            {"base": "읽", "past": "읽었다", "present": "읽어"}
        ])
        return stems

    def generate_slotted_sentence(self, level: int = 3) -> Dict[str, Any]:
        """
        레벨에 따라 정교하게 슬롯을 채워 의미가 통하는 문장 생성
        Level 3: 주어 + 목적어 + 서술어 (단순 문장)
        Level 4: 접속약어 + 주어 + 부사구(수량/단위) + 서술어
        Level 5: 복합 문장부호(인용구/괄호) + 단위 기호 + 불규칙 활용 서술어
        """
        subjects = ["나", "우리", "친구", "동생", "어머니", "사람"]
        objects = ["사과", "편지", "책", "물", "마음", "길"]

        subj = random.choice(subjects)
        obj = random.choice(objects)
        verb_entry = random.choice(self.verbs)
        verb = verb_entry["past"]

        tokens = []
        meta = {"used_rules": []}

        if level == 3:
            # 기본 구문: [주어]는 [목적어]를 [서술어]
            tokens = [f"{subj}는", f"{obj}를", verb]
            meta["structure"] = "S-O-V"

        elif level == 4:
            # 접속 약어 + 수량 단위 결합 구문
            conn = random.choice(self.wordsigns)
            num = random.randint(1, 10)
            unit = random.choice(self.exempt_units)
            tokens = [conn, f"{subj}는", f"{obj}를", f"{num}{unit}", verb]
            meta["structure"] = "CONJ-S-O-NUM_UNIT-V"
            meta["used_rules"].append("number_exempt_unit")

        else: # Level 5
            # 복합 부호, 로마자 단위 또는 특수 수표 규칙 포함
            conn = random.choice(self.wordsigns)
            quote_open = "“"
            quote_close = "”"
            
            # 수치 + 로마자 단위 또는 특수 구문
            if random.random() < 0.5:
                num = random.randint(5, 50)
                r_unit = random.choice(self.roman_units)
                adv_clause = f"{num}{r_unit}"
                meta["used_rules"].append("roman_unit_direct_append")
            else:
                adv_clause = "빠르게"

            quote_content = f"{obj}를 {adv_clause} {verb_entry['present']}"
            tokens = [conn, f"{subj}가", f"{quote_open}{quote_content}{quote_close}하고", "말했다"]
            meta["structure"] = "CONJ-S-QUOTATION-V"
            meta["used_rules"].append("quote_marks")

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
        num_rules_path: Optional[str] = None
    ):
        ko_path = ko_path or find_data_file("ko.json")
        lexicon_path = lexicon_path or find_data_file("lexicon_ko.json")
        marks_path = marks_path or find_data_file("ko_marks.json")
        num_rules_path = num_rules_path or find_data_file("ko_number_rules.json")

        with open(ko_path, 'r', encoding='utf-8') as f:
            self.ko_data = json.load(f)
        with open(lexicon_path, 'r', encoding='utf-8') as f:
            self.lexicon_data = json.load(f)
        with open(marks_path, 'r', encoding='utf-8') as f:
            self.marks_data = json.load(f)
        with open(num_rules_path, 'r', encoding='utf-8') as f:
            self.num_rules_data = json.load(f)

        self.distractor_engine = CognitiveDistractorEngine(self.ko_data)
        self.slot_engine = SentenceSlotEngine(
            self.ko_data, self.lexicon_data, self.marks_data, self.num_rules_data
        )

        if KoreanBrailleEngine is not None:
            self.braille_engine = KoreanBrailleEngine(
                ko_data=self.ko_data,
                marks_data=self.marks_data,
                numbers_data={},
                number_rules=self.num_rules_data,
                lexicon_data=self.lexicon_data
            )
        else:
            self.braille_engine = None

        # 풀 캐싱
        self.wordsigns = list(self.ko_data.get("abbreviation_word", {}).get("items", {}).keys())
        self.syllable_abbrs = list(self.ko_data.get("abbreviation_syllable", {}).get("items", {}).keys())

    def _generate_raw_data(self, level: int) -> Dict[str, Any]:
        """레벨별 통제된 원천 토큰 데이터 생성"""
        if level == 1:
            # Level 1: 핵심 단독 약자 및 접속 약어 풀에서 출제
            word = random.choice(self.wordsigns + self.syllable_abbrs)
            return {"tokens": [word], "category": "word", "meta": {"type": "abbreviation_single"}}

        elif level == 2:
            # Level 2: 약자 + 일반 음절 결합 복합 단어
            abbr = random.choice(self.syllable_abbrs)
            extra_syllable = random.choice(["물", "산", "집", "밥", "별", "길", "차", "소리"])
            word = f"{abbr}{extra_syllable}" if random.random() < 0.5 else f"{extra_syllable}{abbr}"
            return {"tokens": [word], "category": "word", "meta": {"type": "compound_syllable"}}

        else:
            # Level 3, 4, 5: 슬롯 엔진을 통한 문장 생성
            sentence_data = self.slot_engine.generate_slotted_sentence(level=level)
            return {
                "tokens": sentence_data["tokens"],
                "category": "sentence",
                "meta": sentence_data["meta"]
            }

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

        # 완성 문장 및 종결부호 규격 처리
        target_text = " ".join(tokens)
        if category == "sentence" and not any(target_text.endswith(p) for p in [".", "?", "!", "”"]):
            target_text += "."

        target_braille = ""
        if hasattr(self, 'braille_engine') and self.braille_engine is not None:
            try:
                res = self.braille_engine.text_to_braille(target_text)
                target_braille = res.get("braille", "") if isinstance(res, dict) else res
            except Exception:
                target_braille = ""

        # 1. KEYBOARD 모드: 완성 텍스트 중심
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

        # 2. BLOCK 모드: 인지과학적 방해 블록 세트 구성
        elif input_mode.upper() == "BLOCK":
            granularity = block_granularity.upper()

            if category == "word" or granularity == "SYLLABLE":
                # 글자(음절/부호) 단위 블록 분해
                correct_blocks = [ch for ch in target_text if ch != " "]
                
                # 인지과학 엔진을 통한 유사 점형/착오 음절 기반 오답 생성
                distractors = []
                for b in correct_blocks:
                    confusables = self.distractor_engine.generate_confusable_blocks(b, count=1)
                    distractors.extend(confusables)

                # 지정 개수 맞춤 조절
                while len(distractors) < distractor_count:
                    distractors.extend(self.distractor_engine.generate_confusable_blocks(random.choice(correct_blocks), count=1))
                distractors = list(set(distractors))[:distractor_count]

            else:
                # 어절(단어) 단위 분해
                correct_blocks = list(tokens)
                if category == "sentence" and target_text.endswith(".") and not correct_blocks[-1].endswith("."):
                    correct_blocks.append(".")

                # 어절 단위 방해 블록 생성 (단어 변형 및 약자 간섭 활용)
                distractors = []
                for token in tokens[:distractor_count]:
                    # 어절 내 한 글자를 인지 착오 글자로 치환하여 매력적인 오답 어절 생성
                    if len(token) > 0:
                        idx = random.randint(0, len(token) - 1)
                        target_ch = token[idx]
                        alt_list = self.distractor_engine.generate_confusable_blocks(target_ch, count=1)
                        alt_ch = alt_list[0] if alt_list else "것"
                        distractor_token = token[:idx] + alt_ch + token[idx+1:]
                        distractors.append(distractor_token)

                while len(distractors) < distractor_count:
                    distractors.append(random.choice(self.wordsigns))
                distractors = list(set(distractors))[:distractor_count]

            # 블록 리스트 패키징 및 셔플
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

        elif input_mode.upper() == "TRIANGLE":
            granularity = block_granularity.upper()
            distractors_text = self.distractor_engine.generate_confusable_blocks(target_text[:1] if target_text else "가", count=2)
            
            distractors_braille = []
            if hasattr(self, 'braille_engine') and self.braille_engine is not None:
                for dt in distractors_text:
                    res = self.braille_engine.text_to_braille(dt)
                    db = res.get("braille", "") if isinstance(res, dict) else res
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

        else:
            raise ValueError(f"Unsupported input_mode: {input_mode}")


# =====================================================================
# 실행 및 검증 예시
# =====================================================================
if __name__ == "__main__":
    generator = KoreanBrailleQuizGenerator(
        ko_path="ko.json",
        lexicon_path="lexicon_ko.json",
        marks_path="ko_marks.json",
        num_rules_path="ko_number_rules.json"
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