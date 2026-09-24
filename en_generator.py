import json
import os
import random
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from data_paths import find_data_file, resolve_data_root


class EnglishBrailleQuizGenerator:
    """
    UEB(Unified English Braille) 학습을 위한 고도화된 영어 점자 퀴즈 생성기.
    - JSON 데이터 풀 100% 로드 및 연동 (어근, 접두사, 접미사, 축어, 단어약어, 약어군, 숫자/기호)
    - 통제된 랜덤(Controlled Random): 문법 템플릿 슬롯 기반 자연스러운 문장 생성
    - 인지과학 기반 오답(Distractor) 생성: 좌우 대칭, 상하 반전, 1비트 변이(오탈자), 규정 위반형(1급 기호표/축어 결합 오류)
    """

    PUNCTUATION = {".", ",", "!", "?", ";", ":"}

    # 인지과학적 6점 점형 변형 맵 (1~6번 점)
    H_MIRROR = {1: 4, 2: 5, 3: 6, 4: 1, 5: 2, 6: 3}
    V_INVERT = {1: 3, 2: 2, 3: 1, 4: 6, 5: 5, 6: 4}

    def __init__(
        self,
        data_dir: Optional[str] = None,
        segmenter: Optional[Any] = None,
        braille_engine: Optional[Any] = None
    ):
        self.data_dir = resolve_data_root(data_dir)

        self.segmenter = segmenter
        self.braille_engine = braille_engine

        # JSON 데이터 풀 저장소
        self.roots: List[str] = []
        self.roots_data: Dict[str, Dict[str, Any]] = {}
        self.prefixes: List[str] = []
        self.inflections: List[str] = []
        self.derivations: List[str] = []
        self.shortforms_standalone: Dict[str, str] = {}
        self.shortforms_inflected: Dict[str, Dict[str, Any]] = {}
        self.shortforms_compound: Dict[str, Dict[str, Any]] = {}
        self.alphabetic_wordsigns: Dict[str, str] = {}
        self.contractions: Dict[str, Dict[str, Any]] = {}
        self.single_letters: Dict[str, str] = {}
        self.digits: Dict[str, str] = {}

        # 데이터 풀 100% 로드
        self._load_all_json_data()

    def _find_file(self, filename: str, _search_dirs: Optional[List[str]] = None) -> str:
        return find_data_file(filename, self.data_dir)

    def _safe_extract_items(self, items_container: Union[Dict, List, Any]) -> List[Dict[str, Any]]:
        """JSON items가 dict 형태(key-value)이든 list 형태이든 안전하게 추출"""
        if isinstance(items_container, dict):
            return list(items_container.values())
        elif isinstance(items_container, list):
            return items_container
        return []

    def _load_shortforms(self, data: Dict[str, Any]) -> None:
        """en_shortform.json 파싱: 스키마 유연성 보장 및 개별 단위 allowedSuffixes 준수"""
        # 1. 단독 축어
        standalone_items = self._safe_extract_items(data.get("shortform_standalone_only", {}).get("items", {}))
        for item in standalone_items:
            if "word" in item and "unicode" in item:
                self.shortforms_standalone[item["word"].lower()] = item["unicode"]

        # 2. 굴절 허용 축어
        default_inf_rule = data.get("shortform_inflected", {}).get("rule", {})
        default_suffixes = default_inf_rule.get("allowedSuffixes", [])
        inflected_items = self._safe_extract_items(data.get("shortform_inflected", {}).get("items", {}))

        for item in inflected_items:
            if "word" in item and "unicode" in item:
                word_key = item["word"].lower()
                allowed = item.get("allowedSuffixes", default_suffixes)
                self.shortforms_inflected[word_key] = {
                    "unicode": item["unicode"],
                    "suffixes": allowed
                }

        # 3. 복합어/파생 허용 축어
        compound_items = self._safe_extract_items(data.get("shortform_compound_allowed", {}).get("items", {}))
        for item in compound_items:
            if "word" in item and "unicode" in item:
                word_key = item["word"].lower()
                allowed = item.get("allowedSuffixes", [])
                self.shortforms_compound[word_key] = {
                    "unicode": item["unicode"],
                    "suffixes": allowed
                }

    def _load_all_json_data(self) -> None:
        """모든 UEB 관련 JSON 리소스를 로드하여 메모리 풀 구축"""
        # 1. lexicon_en.json
        lex_path = self._find_file("lexicon_en.json")
        if os.path.exists(lex_path):
            with open(lex_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                roots_items = d.get("roots", {}).get("items", {})
                self.roots_data = roots_items if isinstance(roots_items, dict) else {}
                self.roots = list(self.roots_data.keys()) if self.roots_data else [item.get("word") for item in self._safe_extract_items(roots_items) if "word" in item]
                self.prefixes = list(d.get("prefixes", {}).get("items", {}).keys())
                self.inflections = list(d.get("inflectional_suffixes", {}).get("items", {}).keys())
                self.derivations = list(d.get("derivational_suffixes", {}).get("items", {}).keys())

        if not self.roots:
            self.roots = ["friend", "react", "bubble", "time", "day", "work", "world", "light", "hand", "water"]

        # 2. en_shortform.json
        sf_path = self._find_file("en_shortform.json")
        if os.path.exists(sf_path):
            with open(sf_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                self._load_shortforms(d)

        # 3. en_spell.json
        spell_path = self._find_file("en_spell.json")
        if os.path.exists(spell_path):
            with open(spell_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                self.single_letters = {k: v["unicode"] for k, v in d.get("single_letter", {}).get("items", {}).items()}
                self.alphabetic_wordsigns = {v["word"].lower(): v["unicode"] for _, v in d.get("alphabetic_wordsign", {}).get("items", {}).items() if "word" in v}

        # 4. en_contractions.json
        c_path = self._find_file("en_contractions.json")
        if os.path.exists(c_path):
            with open(c_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                for g in d.get("groups", []):
                    cat = g.get("category", "contraction")
                    rule = g.get("rule", {})
                    prio = g.get("priority", 50)
                    for text_val, item in g.get("items", {}).items():
                        self.contractions[text_val.lower()] = {
                            "unicode": item["unicode"],
                            "category": cat,
                            "rule": rule,
                            "priority": prio
                        }

        # 5. numbers.json
        num_path = self._find_file("numbers.json")
        if os.path.exists(num_path):
            with open(num_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                self.digits = {k: v["unicode"] for k, v in d.get("digits", {}).items()}

    def _apply_spelling_transformations(self, root: str, suffix: str) -> str:
        """lexicon_en.json combining_rules 기반 어미 결합 철자 변환 연산"""
        root_meta = self.roots_data.get(root, {})
        has_silent_e = root_meta.get("hasSilentE", False)
        double_allowed = root_meta.get("doubleConsonantAllowed", False)

        vowels = set("aeiou")
        vowel_suffixes = {"ing", "ed", "er", "est", "able", "ist", "ize"}

        # 1. Drop silent 'e'
        if has_silent_e and root.endswith("e") and suffix in vowel_suffixes:
            return root[:-1] + suffix

        # 2. Duplicate final consonant
        if double_allowed and len(root) >= 3 and suffix in {"ing", "ed", "er", "est"}:
            c1, v, c2 = root[-3], root[-2], root[-1]
            if c1 not in vowels and v in vowels and c2 not in vowels and c2 not in {"w", "x", "y"}:
                return root + c2 + suffix

        # 3. Replace 'y' with 'i'
        if root.endswith("y") and len(root) > 1 and root[-2] not in vowels:
            if suffix in {"es", "ed", "er", "est", "ly", "ful"}:
                return root[:-1] + "i" + suffix

        return root + suffix

    @staticmethod
    def unicode_to_dots(braille_char: str) -> List[int]:
        if not braille_char or len(braille_char) != 1:
            return []
        code = ord(braille_char) - 0x2800
        dots = []
        masks = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20]
        for i, m in enumerate(masks):
            if code & m:
                dots.append(i + 1)
        return dots

    @staticmethod
    def dots_to_unicode(dots: List[int]) -> str:
        code = 0
        masks = {1: 0x01, 2: 0x02, 3: 0x04, 4: 0x08, 5: 0x10, 6: 0x20}
        for d in set(dots):
            if d in masks:
                code |= masks[d]
        return chr(0x2800 + code)

    def braille_to_dot_cells(self, braille_str: str) -> List[List[int]]:
        cells: List[List[int]] = []
        for char in braille_str:
            dots = self.unicode_to_dots(char)
            if dots:
                cells.append(dots)
        return cells

    def generate_cognitive_braille_distractors(self, correct_braille: str, count: int = 2) -> List[str]:
        if not correct_braille:
            return ["⠁", "⠃"][:count]

        distractors: Set[str] = set()

        # 1. 좌우 대칭
        h_mirrored = []
        for ch in correct_braille:
            dots = self.unicode_to_dots(ch)
            if dots:
                m_dots = sorted(self.H_MIRROR[d] for d in dots)
                h_mirrored.append(self.dots_to_unicode(m_dots))
            else:
                h_mirrored.append(ch)
        h_str = "".join(h_mirrored)
        if h_str != correct_braille:
            distractors.add(h_str)

        # 2. 상하 반전
        v_inverted = []
        for ch in correct_braille:
            dots = self.unicode_to_dots(ch)
            if dots:
                i_dots = sorted(self.V_INVERT[d] for d in dots)
                v_inverted.append(self.dots_to_unicode(i_dots))
            else:
                v_inverted.append(ch)
        v_str = "".join(v_inverted)
        if v_str != correct_braille:
            distractors.add(v_str)

        # 3. 1비트 변이
        for _ in range(5):
            if len(distractors) >= count:
                break
            mutated = list(correct_braille)
            target_idx = random.randint(0, len(mutated) - 1)
            target_ch = mutated[target_idx]
            dots = self.unicode_to_dots(target_ch)
            if dots:
                if random.choice([True, False]) and len(dots) > 1:
                    dots.remove(random.choice(dots))
                else:
                    avail = list(set([1, 2, 3, 4, 5, 6]) - set(dots))
                    if avail:
                        dots.append(random.choice(avail))
                mutated[target_idx] = self.dots_to_unicode(sorted(dots))
                m_str = "".join(mutated)
                if m_str != correct_braille:
                    distractors.add(m_str)

        # Fallback
        fallback_pool = ["⠰" + correct_braille, correct_braille + "⠰", "⠼" + correct_braille]
        for fb in fallback_pool:
            if len(distractors) >= count:
                break
            if fb != correct_braille:
                distractors.add(fb)

        return list(distractors)[:count]

    def generate_ueb_rule_distractors(self, text: str, braille: str, count: int = 2) -> List[str]:
        """숫자/규칙 위반 및 1급 점형 오답 생성 로직 고도화"""
        distractors: Set[str] = set()
        grade1_indicator = "⠰"
        num_prefix = "⠼"

        # 1. 숫자 뒤 a~j 충돌 오류
        for i, ch in enumerate(text[:-1]):
            next_ch = text[i + 1]
            if ch.isdigit() and next_ch.lower() in "abcdefghij":
                corrupted = braille.replace(grade1_indicator, "", 1)
                if corrupted != braille:
                    distractors.add(corrupted)
                distractors.add(braille + grade1_indicator)

        # 2. 수표 누락 및 중복 선언
        if num_prefix in braille:
            distractors.add(braille.replace(num_prefix, "", 1))
            distractors.add(braille.replace(num_prefix, num_prefix + num_prefix, 1))

        # 3. 1급 기호 미사용 전개형 오류 (Grade 2 단어에 불필요한 Grade 1 지시표 부여)
        if not text.isdigit() and grade1_indicator not in braille:
            distractors.add(grade1_indicator + braille)

        # 부족한 개수는 물리 변이로 보충
        if len(distractors) < count:
            extra = self.generate_cognitive_braille_distractors(braille, count=count - len(distractors))
            distractors.update(extra)

        return list(distractors)[:count]

    def _generate_shortform_word(self) -> Tuple[str, str]:
        """축어 풀의 빈 데이터 여부를 방어하며 유효한 카테고리만 무작위 추첨"""
        valid_pools = []
        if self.shortforms_standalone:
            valid_pools.append("standalone")
        if self.shortforms_inflected:
            valid_pools.append("inflected")
        if self.shortforms_compound:
            valid_pools.append("compound")

        if not valid_pools:
            return random.choice(self.roots), "EN_BASIC_LETTER"

        category_choice = random.choice(valid_pools)

        if category_choice == "standalone":
            word = random.choice(list(self.shortforms_standalone.keys()))
            return word, "EN_SHORTFORM_STANDALONE"

        elif category_choice == "inflected":
            word, meta = random.choice(list(self.shortforms_inflected.items()))
            suffixes = meta.get("suffixes", [])
            sfx = random.choice(suffixes) if suffixes else ""
            return word + sfx, "EN_SHORTFORM_INFLECTED"

        else:  # compound
            word, meta = random.choice(list(self.shortforms_compound.items()))
            suffixes = meta.get("suffixes", [])
            if suffixes and random.random() < 0.5:
                sfx = random.choice(suffixes)
                return word + sfx, "EN_SHORTFORM_COMPOUND"
            return word, "EN_SHORTFORM_COMPOUND"

    def _generate_controlled_word(self, level: int = 1) -> Tuple[str, str]:
        if level == 1:
            if random.random() < 0.5 and self.alphabetic_wordsigns:
                return random.choice(list(self.alphabetic_wordsigns.keys())), "EN_STANDALONE"
            elif self.shortforms_standalone:
                return random.choice(list(self.shortforms_standalone.keys())), "EN_SHORTFORM"
            return random.choice(self.roots), "EN_BASIC_LETTER"

        elif level == 2:
            root = random.choice(self.roots)
            if random.random() < 0.5 and self.inflections:
                sfx = random.choice(self.inflections)
                return self._apply_spelling_transformations(root, sfx), "EN_INFLECTION"
            elif self.prefixes:
                pfx = random.choice(self.prefixes)
                return pfx + root, "EN_PREFIX_RULE"
            return root, "EN_BASIC_LETTER"

        elif level == 3:
            contract_pool = [w for w in self.roots if any(c in w for c in self.contractions.keys())]
            if contract_pool:
                return random.choice(contract_pool), "EN_BRIDGE_RULE"
            return random.choice(self.roots), "EN_BRIDGE_RULE"

        else:
            return self._generate_shortform_word()

    def _generate_controlled_sentence(self, level: int = 3) -> Tuple[str, str]:
        subjects = ["I", "You", "We", "They", "The friend", "A child"]
        verbs = ["can see", "will have", "like", "found", "received", "want"]
        objects = ["the letter", "about it", "good knowledge", "more time", "every day", "a little hope"]
        prepositions = ["in time", "for good", "with friends", "about work", "together"]

        subj = random.choice(subjects)
        verb = random.choice(verbs)
        obj = random.choice(objects)

        if level >= 4:
            prep = random.choice(prepositions)
            sentence = f"{subj} {verb} {obj} {prep}."
        else:
            sentence = f"{subj} {verb} {obj}."

        return sentence, "EN_SENTENCE_SYNTAX"

    def _fallback_text_to_braille(self, text: str) -> str:
        """braille_engine이 없을 때 축어 및 약어를 고려한 향상된 점역 폴백"""
        lower_text = text.lower()
        if lower_text in self.shortforms_standalone:
            return self.shortforms_standalone[lower_text]
        if lower_text in self.alphabetic_wordsigns:
            return self.alphabetic_wordsigns[lower_text]

        # 단어 단위 매핑 시도 후 문자별 매핑
        return "".join(self.single_letters.get(ch.lower(), ch) for ch in text)

    def generate_quiz(
        self,
        input_mode: str = "KEYBOARD",
        level: int = 1,
        distractor_count: int = 3,
        block_granularity: str = "WORD"
    ) -> Dict[str, Any]:
        mode = input_mode.upper()
        is_sentence = (level >= 4)

        if is_sentence:
            target_text, rule_type = self._generate_controlled_sentence(level=level)
            category = "문장/어절"
        else:
            target_text, rule_type = self._generate_controlled_word(level=level)
            category = "핵심 단어"

        if self.braille_engine:
            target_braille = self.braille_engine.text_to_braille(target_text)
        else:
            target_braille = self._fallback_text_to_braille(target_text)

        if mode == "KEYBOARD":
            dot_cells = self.braille_to_dot_cells(target_braille)
            first_cell = dot_cells[0] if dot_cells else [1]
            sample_char = target_text[0]

            return {
                "input_mode": "KEYBOARD",
                "level": level,
                "category": category,
                "rule_type": rule_type,
                "target_text": target_text,
                "target_braille": target_braille,
                "char": sample_char,
                "dots": dot_cells,
                "first_cell_dots": first_cell,
                "meaning": f"{sample_char} ({rule_type})",
                "typeKey": rule_type,
                "prompt_audio": f"Question. Translate {target_text} into braille."
            }

        elif mode == "TRIANGLE":
            distractors_braille = self.generate_ueb_rule_distractors(target_text, target_braille, count=2)
            distractors_text = [
                target_text + "s",
                "un" + target_text if not target_text.startswith("un") else target_text[2:]
            ]

            return {
                "input_mode": "TRIANGLE",
                "level": level,
                "category": category,
                "rule_type": rule_type,
                "target_text": target_text,
                "target_braille": target_braille,
                "text": target_text,
                "braille": target_braille,
                "distractors_braille": distractors_braille,
                "distractors_text": distractors_text,
                "prompt_audio": f"Choose the correct braille for {target_text}."
            }

        elif mode == "BLOCK":
            granularity = block_granularity.upper()

            if granularity == "SYLLABLE" or not is_sentence:
                if self.segmenter:
                    correct_blocks = self.segmenter.segment_word(target_text)
                else:
                    correct_blocks = list(target_text.replace(" ", ""))
            else:
                correct_blocks = target_text.split(" ")

            distractor_candidates = ["re", "ing", "ed", "un", "ly", "dis", "tion", "er", "s"]
            distractors = [d for d in distractor_candidates if d not in correct_blocks][:distractor_count]
            while len(distractors) < distractor_count:
                distractors.append(f"_{len(distractors) + 1}")

            all_blocks = [{"text": b, "is_distractor": False} for b in correct_blocks]
            all_blocks.extend([{"text": d, "is_distractor": True} for d in distractors])
            random.shuffle(all_blocks)

            return {
                "input_mode": "BLOCK",
                "block_granularity": granularity,
                "level": level,
                "category": category,
                "rule_type": rule_type,
                "target_text": target_text,
                "target_braille": target_braille,
                "correct_sequence": correct_blocks,
                "available_blocks": [b["text"] for b in all_blocks],
                "block_details": all_blocks,
                "prompt_audio": f"Assemble the braille blocks for {target_text}."
            }

        raise ValueError(f"Unsupported input_mode: {input_mode}")