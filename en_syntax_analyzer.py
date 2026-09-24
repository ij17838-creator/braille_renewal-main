import json
import os
import re
from typing import Dict, List, Any, Optional

from data_paths import find_data_file, resolve_data_root

# =====================================================================
# 영어 점자 문장요소 검증 및 결합 규칙 판별기 (Braille Rule Validator)
# =====================================================================
class BrailleRuleValidator:
    """
    UEB(영어 점자 규정) 및 data 폴더의 규칙을 기반으로:
    1. 형태소 경계 침범(Bridge Contraction) 방지 판별 (중복 위치 전수 조사)
    2. 위치 제약(어두/어중/어말/단독) 약어 검증
    3. 축어(Shortform) 불법 접사/합성어 결합 판별
    4. 수표 모드 지속성 및 영숫자 충돌(Grade 1 필요 여부) 판별
    5. 문장/단어 단위 요소 진단 리포트 생성
    """
    def __init__(self, base_data_dir: Optional[str] = None):
        self.base_data_dir = resolve_data_root(base_data_dir)
        self._load_data()

    def _load_lexicon(self, lex_data: Dict[str, Any]):
        """어휘, 형태소 목록 및 철자 변형 규칙 안전 적재"""
        self.prefixes = (lex_data.get("prefixes") or {}).get("items", {})
        self.roots = (lex_data.get("roots") or {}).get("items", {})
        self.inflections = (lex_data.get("inflectional_suffixes") or {}).get("items", {})
        self.derivations = (lex_data.get("derivational_suffixes") or {}).get("items", {})
        
        comb_rules = lex_data.get("combining_rules") or {}
        bridge_rule = comb_rules.get("bridge_rule") or {}
        self.disallow_bridge = bridge_rule.get("disallowCrossMorphemeContraction", True)
        self.spelling_rules = comb_rules.get("spelling_transformations") or {}

    def _load_contractions(self, c_data: Dict[str, Any]):
        """priority 및 세부 위치 규칙을 포함하여 약어 정보 적재"""
        self.contractions = {}
        for group in c_data.get("groups", []):
            group_priority = group.get("priority", 0)
            group_category = group.get("category")
            group_type = group.get("type")
            group_rule = group.get("rule", {})

            for k, v in group.get("items", {}).items():
                self.contractions[k] = {
                    "word": v.get("word", k),
                    "category": group_category,
                    "type": group_type,
                    "priority": group_priority,
                    "rule": group_rule,
                    "unicode": v.get("unicode"),
                    "rootChar": v.get("rootChar")
                }

        for item in self.contractions.values():
            root = item.get("rootChar")
            if not root:
                continue
            root_item = self.contractions.get(root)
            if root_item is None:
                raise ValueError(f"rootChar {root!r}가 en_contractions.json에 없습니다.")
            if root_item["unicode"] not in (item.get("unicode") or ""):
                raise ValueError(
                    f"{item['word']}의 점자 {item.get('unicode')!r}에 강세 약어 {root}({root_item['unicode']})가 없습니다."
                )
            item["rootEntry"] = root_item

    def _load_shortforms(self, sf_path: str):
        """카테고리 규칙 및 항목별 개별 allowedSuffixes 로드"""
        self.shortforms = {}
        if not os.path.exists(sf_path):
            return

        with open(sf_path, "r", encoding="utf-8") as f:
            sf_data = json.load(f)

        for _, sec in sf_data.items():
            sec_rule = sec.get("rule", {})
            for k, v in sec.get("items", {}).items():
                word_key = v.get("word").lower()
                item_suffixes = v.get("allowedSuffixes", sec_rule.get("allowedSuffixes", []))
                entry = {
                    "shortform": k,
                    "rule": sec_rule,
                    "allowedSuffixes": set(item_suffixes),
                    "unicode": v.get("unicode")
                }
                root_chars = v.get("rootChars") or []
                if root_chars:
                    entry["rootEntries"] = [self.contractions[root] for root in root_chars]
                self.shortforms[word_key] = entry

    def _load_number_rules(self, num_rules: Dict[str, Any]):
        """ueb_number_rules.json의 연결자 및 부호 집합 동적 추출"""
        self.continuation_chars = {
            item["char"] for item in num_rules.get("scope_maintenance", {}).get("continuation_connectors", [])
            if "char" in item
        }
        self.terminating_chars = {
            item["char"] for item in num_rules.get("scope_maintenance", {}).get("terminating_connectors", [])
            if "char" in item
        }
        self.grade1_targets = set(
            num_rules.get("collision_resolutions", {}).get("alphanumeric_transition", {}).get("grade1_required_targets", [])
        )

        standing_alone = num_rules.get("standing_alone_rules", {})
        adjacent = standing_alone.get("adjacent_delimiters", {})

        allowed = set(standing_alone.get("surrounding_allowed_symbols", []))
        for group_name in ["neutral_punctuation", "hyphen_and_dashes"]:
            for sym in adjacent.get(group_name, {}).get("symbols", []):
                for ch in sym.get("char", ""):
                    allowed.add(ch)
        self.surrounding_allowed_symbols = allowed

        disallowed = set()
        for sym in adjacent.get("slash_and_symbols", {}).get("symbols", []):
            for ch in sym.get("char", ""):
                disallowed.add(ch)
        self.disallowed_delimiters = disallowed

    def _load_data(self):
        with open(find_data_file("lexicon_en.json", self.base_data_dir), "r", encoding="utf-8") as f:
            self._load_lexicon(json.load(f))

        with open(find_data_file("en_contractions.json", self.base_data_dir), "r", encoding="utf-8") as f:
            self._load_contractions(json.load(f))

        self._load_shortforms(find_data_file("en_shortform.json", self.base_data_dir))

        with open(find_data_file("en_spell.json", self.base_data_dir), "r", encoding="utf-8") as f:
            spell_data = json.load(f)
            self.alphabetic_wordsigns = spell_data.get("alphabetic_wordsign", {}).get("items", {})

        with open(find_data_file("numbers.json", self.base_data_dir), "r", encoding="utf-8") as f:
            num_data = json.load(f)
            self.num_prefix = num_data["numeric_indicators"]["num_prefix"]["unicode"]
            self.grade1_prefix = num_data["grade1_indicators"]["grade1_symbol"]["unicode"]

        with open(find_data_file("ueb_number_rules.json", self.base_data_dir), "r", encoding="utf-8") as f:
            self._load_number_rules(json.load(f))

    # -----------------------------------------------------------------
    # 형태소 분절 및 가교 약어(Bridge Contraction) 검증
    # -----------------------------------------------------------------
    def _restore_stem_candidates(self, stem: str, suffix: str) -> List[str]:
        candidates = [stem]
        silent_e_rule = self.spelling_rules.get("drop_silent_e", {})
        if suffix in silent_e_rule.get("triggerSuffixes", []):
            candidates.append(stem + "e")

        double_rule = self.spelling_rules.get("double_final_consonant", {})
        if suffix in double_rule.get("triggerSuffixes", []) and len(stem) >= 2:
            if stem[-1] == stem[-2] and stem[-1] not in double_rule.get("excludedEndings", ["w", "x", "y"]):
                candidates.append(stem[:-1])

        y_rule = self.spelling_rules.get("y_to_i", {})
        if suffix in y_rule.get("triggerSuffixes", []) and stem.endswith("i"):
            candidates.append(stem[:-1] + "y")

        return candidates

    def segment_morphemes(self, word: str) -> List[str]:
        w = word.lower()
        if w in self.roots:
            return [w]

        prefix = ""
        for p in sorted(self.prefixes.keys(), key=len, reverse=True):
            if w.startswith(p) and len(w) > len(p):
                prefix = p
                w = w[len(p):]
                break

        suffixes = {**self.inflections, **self.derivations}
        matched_suffix = ""
        matched_root = ""

        for s in sorted(suffixes.keys(), key=len, reverse=True):
            if w.endswith(s) and len(w) > len(s):
                stem = w[:-len(s)]
                candidates = self._restore_stem_candidates(stem, s)
                for cand in candidates:
                    if cand in self.roots:
                        matched_suffix = s
                        matched_root = cand
                        w = stem
                        break
                if matched_root:
                    break

        morphemes = []
        if prefix:
            morphemes.append(prefix)
        morphemes.append(w)
        if matched_suffix:
            morphemes.append(matched_suffix)

        return morphemes

    def validate_contraction_placement(self, word: str, contraction: str) -> Dict[str, Any]:
        """Bridge Rule 및 위치 규칙 검증 (중복 등장 위치 전수 검사)"""
        w = word.lower()
        target = contraction.lower()
        c_info = self.contractions.get(target)

        if not c_info:
            return {"valid": False, "reason": f"Unknown contraction: '{target}'"}

        # 단어 내 등장하는 모든 인덱스 수집
        indices = [m.start() for m in re.finditer(re.escape(target), w)]
        if not indices:
            return {"valid": False, "reason": f"'{target}' not found in '{word}'"}

        # 1. 가교 결합 (Bridge Rule) 경계 수집
        boundaries = []
        morphemes = []
        if self.disallow_bridge:
            morphemes = self.segment_morphemes(word)
            accum = 0
            for m in morphemes[:-1]:
                accum += len(m)
                boundaries.append(accum)

        rule = c_info.get("rule", {})

        # 각 위치별 유효성 검사
        for idx in indices:
            # 1-1. Bridge Rule 판별
            for b in boundaries:
                if idx < b < (idx + len(target)):
                    return {
                        "valid": False,
                        "rule": "Bridge Rule Violation",
                        "reason": f"Contraction '{target}' bridges morpheme boundary at {morphemes}"
                    }

            # 1-2. 세부 위치 규칙 판별
            is_initial = (idx == 0)
            is_final = (idx + len(target) == len(w))
            is_medial = (not is_initial and not is_final)

            if rule.get("requiresSurroundingLetters") and not is_medial:
                return {
                    "valid": False,
                    "rule": "Medial Only Violation",
                    "reason": f"Contraction '{target}' must have surrounding letters within word."
                }

            if not rule.get("canFollowLetters", True) and rule.get("requiresFollowingLetters"):
                if not is_initial or is_final:
                    return {
                        "valid": False,
                        "rule": "Prefix Only Violation",
                        "reason": f"Contraction '{target}' can only appear at syllable-initial position."
                    }

            if not rule.get("canPrecedeLetters", True) and not is_final:
                return {
                    "valid": False,
                    "rule": "Suffix/Final Only Violation",
                    "reason": f"Contraction '{target}' can only appear at syllable-final position."
                }

        return {"valid": True, "priority": c_info.get("priority", 0), "details": c_info}

    def validate_shortform_usage(self, token: str) -> Dict[str, Any]:
        lower = token.lower()

        for sf_word, data in self.shortforms.items():
            if lower == sf_word:
                continue

            if lower.startswith(sf_word):
                suffix = lower[len(sf_word):]
                rule = data.get("rule", {})
                allowed_suffixes = data.get("allowedSuffixes", set())

                if suffix == "s" and not rule.get("allowPluralS", False):
                    return {
                        "valid": False,
                        "error": "Plural S Prohibited",
                        "reason": f"Shortform '{sf_word}' cannot take plural -s."
                    }

                if not rule.get("allowSuffix", False):
                    return {
                        "valid": False,
                        "error": "Suffix Prohibited",
                        "reason": f"Shortform '{sf_word}' cannot combine with suffixes ('{suffix}')."
                    }

                if suffix not in allowed_suffixes:
                    return {
                        "valid": False,
                        "error": "Unallowed Suffix",
                        "reason": f"Suffix '-{suffix}' is not permitted for shortform '{sf_word}' (Allowed: {list(allowed_suffixes)})."
                    }

        return {"valid": True}

    def _is_standing_alone(self, tokens: List[str], index: int) -> bool:
        """
        단어 약어(Alphabetic Wordsign)를 위한 Standing Alone(독립 단어) 정밀 판별
        - 하이픈/대시 너머에 문자가 바로 이어지는 복합어(예: b-side) 차단
        """
        disallowed = getattr(self, "disallowed_delimiters", {"/", "&", "@"})
        allowed = getattr(self, "surrounding_allowed_symbols", set())

        # 1. 왼쪽 검사
        prev_is_hyphen = False
        for k in range(index - 1, -1, -1):
            tok = tokens[k]
            if tok.isspace():
                break
            if tok in ["-", "–", "—"]:
                prev_is_hyphen = True
            elif prev_is_hyphen and tok.isalnum():
                return False  # a-b 형태의 하이픈 결합어 차단
            if tok.isalnum() or tok in disallowed or (allowed and tok not in allowed):
                return False

        # 2. 오른쪽 검사
        next_is_hyphen = False
        for k in range(index + 1, len(tokens)):
            tok = tokens[k]
            if tok.isspace():
                break
            if tok in ["-", "–", "—"]:
                next_is_hyphen = True
            elif next_is_hyphen and tok.isalnum():
                return False  # b-side 형태의 하이픈 결합어 차단
            if tok.isalnum() or tok in disallowed or (allowed and tok not in allowed):
                return False

        return True

    # -----------------------------------------------------------------
    # 문장 요소 및 결합 규칙 검증 (Sentence-level Validator)
    # -----------------------------------------------------------------
    def validate_sentence(self, sentence: str) -> Dict[str, Any]:
        """수정된 토큰 정규식, 복수형 소유격 분리 및 엄격 모드 전환 검증"""
        token_pattern = re.compile(
            r"[a-zA-Z]+(?:['’][a-zA-Z]+)?|[0-9]+|[^\w\s]|\s+"
        )
        raw_tokens = token_pattern.findall(sentence)

        tokens = []
        for tok in raw_tokens:
            # 1. 일반 축약형/소유격 분리 (예: he's, they're)
            apostrophe_match = re.match(r"^([a-zA-Z]+)(['’](?i:s|d|re|ve|ll|m|t))$", tok)
            # 2. 복수형 명사 소유격 분리 (예: students')
            plural_possessive = re.match(r"^([a-zA-Z]+s)(['’])$", tok)

            if apostrophe_match:
                tokens.append(apostrophe_match.group(1))
                tokens.append(apostrophe_match.group(2))
            elif plural_possessive:
                tokens.append(plural_possessive.group(1))
                tokens.append(plural_possessive.group(2))
            else:
                tokens.append(tok)

        analysis = []
        in_numeric_mode = False

        for i, token in enumerate(tokens):
            if token.isspace():
                in_numeric_mode = False
                continue

            item_report = {"token": token, "type": "unknown", "validations": []}

            # 1. 숫자 토큰
            if token.isdigit():
                item_report["type"] = "numeric"
                if not in_numeric_mode:
                    item_report["validations"].append({
                        "event": "Numeric Mode Start",
                        "requires": "Numeric Indicator (⠼)"
                    })
                    in_numeric_mode = True
                else:
                    item_report["validations"].append({"event": "Numeric Mode Retained", "requires": None})

            # 2. 아포스트로피 및 스마트 따옴표 축약형 / 소유격 분기
            elif token.startswith(tuple(["'", "’"])) and (len(token) == 1 or token[1:].isalpha()):
                item_report["type"] = "apostrophe_contraction"
                item_report["validations"].append({
                    "event": "Apostrophe Suffix/Contraction",
                    "suffix": token,
                    "requires": "Grade 2 Suffix Resolution"
                })

            # 3. 문장부호 및 연결자 검증
            elif token in self.surrounding_allowed_symbols or token in self.disallowed_delimiters or token in self.terminating_chars:
                item_report["type"] = "punctuation"
                if in_numeric_mode:
                    if token in self.continuation_chars:
                        item_report["validations"].append({"event": "Connector Retains Numeric Mode", "char": token})
                    elif token in self.terminating_chars:
                        item_report["validations"].append({"event": "Connector Terminates Numeric Mode", "char": token})
                        in_numeric_mode = False
                    else:
                        item_report["validations"].append({"event": "Non-numeric Punctuation Terminates Numeric Mode", "glyph": token})
                        in_numeric_mode = False
                else:
                    item_report["validations"].append({"event": "Standard Punctuation", "glyph": token})

            # 4. 알파벳 단어 토큰
            elif token.isalpha():
                item_report["type"] = "word"

                # 대문자 지시표 판별
                if token.isupper() and len(token) > 1:
                    item_report["validations"].append({
                        "indicator": "Capital Word Indicator (⠠⠠)",
                        "scope": f"All caps word: {token}"
                    })
                elif token[0].isupper():
                    item_report["validations"].append({
                        "indicator": "Capital Letter Indicator (⠠)",
                        "scope": f"Initial capital: {token[0]}"
                    })

                lower_token = token.lower()

                # 수표 모드 바로 뒤 알파벳 충돌 검사 (소문자 a~j 등일 때만 Grade 1 요구)
                if in_numeric_mode:
                    if token[0].islower() and lower_token[0] in self.grade1_targets:
                        item_report["validations"].append({
                            "warning": "Alphanumeric Glyph Collision",
                            "resolution": f"Requires Grade 1 Indicator (⠰) before '{token[0]}'"
                        })
                    in_numeric_mode = False

                # 형태소 분절 분석
                morphemes = self.segment_morphemes(lower_token)
                item_report["morphemes"] = morphemes

                # 단독 알파벳 단어약어 체크 (중첩 부호 고려 Standing Alone 검증)
                if lower_token in self.alphabetic_wordsigns:
                    if self._is_standing_alone(tokens, i):
                        item_report["validations"].append({
                            "type": "Alphabetic Wordsign",
                            "representation": self.alphabetic_wordsigns[lower_token]["word"]
                        })
                    else:
                        item_report["validations"].append({
                            "warning": "Wordsign Not Standing Alone",
                            "reason": f"'{token}' does not satisfy standing-alone requirements."
                        })

                # 축어(Shortform) 체크
                if lower_token in self.shortforms:
                    item_report["validations"].append({
                        "type": "Shortform",
                        "expansion": lower_token,
                        "symbol": self.shortforms[lower_token]["shortform"]
                    })

                # 축어 접사 위반 검증
                sf_res = self.validate_shortform_usage(lower_token)
                if not sf_res["valid"]:
                    item_report["validations"].append(sf_res)

                # 포함된 약어의 가교 결합 위반 여부 확인
                for c_key in self.contractions.keys():
                    if c_key in lower_token:
                        res = self.validate_contraction_placement(lower_token, c_key)
                        if not res["valid"]:
                            item_report["validations"].append(res)

            analysis.append(item_report)

        return {"sentence": sentence, "tokens": analysis}


# =====================================================================
# 테스트 실행부
# =====================================================================
if __name__ == "__main__":
    validator = BrailleRuleValidator()

    print("=== 1. 가교 결합(Bridge Rule) 검증 ===")
    print("react (ea):", validator.validate_contraction_placement("react", "ea"))
    print("bubble (bb):", validator.validate_contraction_placement("bubble", "bb"))

    print("\n=== 2. 축어(Shortform) 사용 규칙 검증 ===")
    print("abouts:", validator.validate_shortform_usage("abouts"))
    print("afternoon:", validator.validate_shortform_usage("afternoon"))

    print("\n=== 3. 문장 진단 리포트 ===")
    report = validator.validate_sentence("He's 123a-4 and (b) reacted abouts students' b/c.")
    for token_info in report["tokens"]:
        print(f"[{token_info['token']}] ({token_info['type']}) -> {token_info['validations']}")