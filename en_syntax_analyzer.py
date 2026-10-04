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
        self.pipeline_order = lex_data.get("pipeline_order") or [
            "inflectional_suffix",
            "derivational_suffix",
            "root",
            "prefix",
        ]

        comb_rules = lex_data.get("combining_rules") or {}
        bridge_rule = comb_rules.get("bridge_rule") or {}
        self.disallow_bridge = bridge_rule.get("disallowCrossMorphemeContraction", True)
        self.spelling_rules = comb_rules.get("spelling_transformations") or {}

        rank = {name: index for index, name in enumerate(self.pipeline_order)}
        catalog = []
        for key, kind in (
            (self.inflections, "inflectional_suffix"),
            (self.derivations, "derivational_suffix"),
        ):
            for suffix in key:
                catalog.append((suffix, kind))
        catalog.sort(key=lambda item: (-len(item[0]), rank.get(item[1], 9)))
        self.suffix_catalog = catalog

    def _load_spell(self, spell_data: Dict[str, Any]):
        """알파벳 칸과 단어약어. rootChar의 한 글자는 약어가 아니라 철자표에 있다."""
        self.letter_glyphs = {}
        for key, item in (spell_data.get("single_letter") or {}).get("items", {}).items():
            letter = (item.get("char") or item.get("word") or key).lower()
            self.letter_glyphs[letter] = {
                "word": letter,
                "unicode": item.get("unicode"),
                "category": "letter",
            }

        wordsign = spell_data.get("alphabetic_wordsign") or {}
        self.wordsign_rule = wordsign.get("rule") or {}
        self.alphabetic_wordsigns = wordsign.get("items") or {}
        self.word_to_wordsign = {}
        for letter, item in self.alphabetic_wordsigns.items():
            word = (item.get("word") or letter).lower()
            self.word_to_wordsign[word] = {**item, "letter": letter}

        isolated = spell_data.get("isolated_letter") or {}
        isolated_rule = isolated.get("rule") or {}
        self.letter_grade1_indicator = isolated_rule.get("grade1IndicatorUnicode") or ""
        self.isolated_letters = {}
        for key, item in (isolated.get("items") or {}).items():
            letter = (item.get("word") or key).lower()
            self.isolated_letters[letter] = item

    def _resolve_root_glyph(self, root: str) -> Dict[str, Any]:
        """강세 약어(ch, the) 또는 철자표의 한 글자(d, c)를 점형으로 찾는다."""
        if root in self.contractions:
            return self.contractions[root]
        letter = self.letter_glyphs.get(root.lower())
        if letter and letter.get("unicode"):
            return letter
        raise ValueError(
            f"rootChar {root!r}가 en_contractions.json 또는 en_spell.json에 없습니다."
        )

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
            root_item = self._resolve_root_glyph(root)
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
            if not isinstance(sec, dict) or "items" not in sec:
                continue
            sec_rule = sec.get("rule", {})
            for k, v in sec.get("items", {}).items():
                word_key = v.get("word").lower()
                specified = "allowedSuffixes" in v
                item_suffixes = v.get("allowedSuffixes", sec_rule.get("allowedSuffixes", []))
                entry = {
                    "shortform": k,
                    "rule": sec_rule,
                    "allowedSuffixes": set(item_suffixes),
                    "suffixesSpecified": specified,
                    "unicode": v.get("unicode")
                }
                root_chars = v.get("rootChars") or []
                if root_chars:
                    root_entries = []
                    for root in root_chars:
                        root_item = self._resolve_root_glyph(root)
                        if not (entry["unicode"] or "").startswith(root_item["unicode"]):
                            raise ValueError(
                                f"{word_key}의 점자 {entry['unicode']!r}가 강세 약어 {root}({root_item['unicode']})로 시작하지 않습니다."
                            )
                        root_entries.append(root_item)
                    entry["rootEntries"] = root_entries
                self.shortforms[word_key] = entry

    def _suffixes_from_pattern(self, pattern: str) -> List[str]:
        body = pattern.split("+", 1)[1].strip() if "+" in pattern else pattern.strip()
        return [part.strip().replace("’", "'") for part in body.split("|") if part.strip()]

    def _load_number_rules(self, num_rules: Dict[str, Any]):
        """ueb_number_rules.json의 연결자, 1급 점자표, 독립 단어 경계를 적재"""
        self.continuation_chars = {
            item["char"] for item in num_rules.get("scope_maintenance", {}).get("continuation_connectors", [])
            if "char" in item
        }
        self.terminating_chars = {
            item["char"] for item in num_rules.get("scope_maintenance", {}).get("terminating_connectors", [])
            if "char" in item
        }
        transition = (num_rules.get("collision_resolutions") or {}).get("alphanumeric_transition") or {}
        self.grade1_targets = set(transition.get("grade1_required_targets", []))
        if transition.get("grade1_indicator"):
            self.grade1_prefix = transition["grade1_indicator"]
        self.grade1_dots = transition.get("grade1_dots") or [2, 3]
        suppression = (num_rules.get("collision_resolutions") or {}).get("wordsign_suppression") or {}
        self.wordsign_suppression = suppression.get("rule", "")

        standing_alone = num_rules.get("standing_alone_rules", {})
        adjacent = standing_alone.get("adjacent_delimiters", {})

        allowed = set(standing_alone.get("surrounding_allowed_symbols", []))
        disallowed = set()
        for group in adjacent.values():
            if not isinstance(group, dict):
                continue
            chars = set()
            for sym in group.get("symbols", []):
                for ch in sym.get("char", ""):
                    chars.add(ch)
            if group.get("allows_contraction"):
                allowed.update(chars)
            elif "allows_contraction" in group:
                disallowed.update(chars)
        self.surrounding_allowed_symbols = allowed
        self.disallowed_delimiters = disallowed

        self.apostrophe_word_suffixes = set()
        self.numeric_apostrophe_blocks = set()
        self.apostrophe_suffix_bodies = []
        for rule in (adjacent.get("apostrophe_exceptions") or {}).get("rules", []):
            pattern = rule.get("pattern", "")
            suffixes = set(self._suffixes_from_pattern(pattern))
            if pattern.startswith("word"):
                if rule.get("allows_contraction"):
                    self.apostrophe_word_suffixes.update(suffixes)
                    self.apostrophe_suffix_bodies.extend(
                        suffix[1:] for suffix in suffixes if suffix.startswith("'")
                    )
            elif pattern.startswith("numeric"):
                if not rule.get("allows_contraction", True):
                    self.numeric_apostrophe_blocks.update(suffixes)
        self.apostrophe_suffix_bodies = sorted(set(self.apostrophe_suffix_bodies), key=len, reverse=True)

    def _load_data(self):
        with open(find_data_file("lexicon_en.json", self.base_data_dir), "r", encoding="utf-8") as f:
            self._load_lexicon(json.load(f))

        with open(find_data_file("en_spell.json", self.base_data_dir), "r", encoding="utf-8") as f:
            self._load_spell(json.load(f))

        with open(find_data_file("en_contractions.json", self.base_data_dir), "r", encoding="utf-8") as f:
            self._load_contractions(json.load(f))

        self._load_shortforms(find_data_file("en_shortform.json", self.base_data_dir))

        with open(find_data_file("numbers.json", self.base_data_dir), "r", encoding="utf-8") as f:
            num_data = json.load(f)
            self.num_prefix = num_data["numeric_indicators"]["num_prefix"]["unicode"]
            self.grade1_prefix = num_data["grade1_indicators"]["grade1_symbol"]["unicode"]

        with open(find_data_file("ueb_number_rules.json", self.base_data_dir), "r", encoding="utf-8") as f:
            self._load_number_rules(json.load(f))

    # -----------------------------------------------------------------
    # 형태소 분절 및 가교 약어(Bridge Contraction) 검증
    # -----------------------------------------------------------------
    def _is_monosyllable(self, stem: str) -> bool:
        return len(re.findall(r"[aeiouy]+", stem)) <= 1

    def _restore_stem_candidates(self, stem: str, suffix: str) -> List[str]:
        candidates = [stem]
        silent_e_rule = self.spelling_rules.get("drop_silent_e", {})
        if suffix in silent_e_rule.get("triggerSuffixes", []):
            restored = stem + "e"
            keep = silent_e_rule.get("keepSilentE") or {}
            blocked = suffix in keep.get("beforeSuffixes", []) and any(
                restored.endswith(ending) for ending in keep.get("whenStemEndsWith", [])
            )
            if not blocked:
                candidates.append(restored)

        double_rule = self.spelling_rules.get("double_final_consonant", {})
        if suffix in double_rule.get("triggerSuffixes", []):
            excluded = set(double_rule.get("excludedEndings", ["w", "x", "y"]))
            if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in excluded:
                undoubled = stem[:-1]
                pattern = double_rule.get("pattern")
                if not pattern or re.search(pattern, undoubled):
                    candidates.append(undoubled)
            final_c = double_rule.get("finalC") or {}
            ending = final_c.get("ending")
            if ending and stem.endswith("k") and stem[:-1].endswith(ending):
                candidates.append(stem[:-1])

        y_rule = self.spelling_rules.get("y_to_i", {})
        if suffix in y_rule.get("triggerSuffixes", []) and stem.endswith("i"):
            y_stem = stem[:-1] + "y"
            keep = y_rule.get("keepY") or {}
            keep_y = (
                suffix in keep.get("monosyllableBeforeSuffixes", [])
                and self._is_monosyllable(y_stem)
            )
            pattern = y_rule.get("pattern")
            if not keep_y and (not pattern or re.search(pattern, y_stem)):
                candidates.append(y_stem)

        return candidates

    def _root_spelling_ok(self, cand: str, stem: str, suffix: str) -> bool:
        root = self.roots.get(cand)
        if not root:
            return False
        if cand == stem + "e":
            prop = (self.spelling_rules.get("drop_silent_e") or {}).get("requiresStemProperty")
            if prop and not root.get(prop):
                return False
        double_rule = self.spelling_rules.get("double_final_consonant") or {}
        if len(stem) >= 2 and stem[-1] == stem[-2] and cand == stem[:-1]:
            prop = double_rule.get("requiresStemProperty")
            if prop and not root.get(prop):
                return False
        return True

    def _segment_core(self, w: str, depth: int = 0) -> Optional[List[Dict[str, Any]]]:
        """접미사를 바깥쪽부터 벗긴 뒤 어근 또는 접두사+어근만 인정한다."""
        if depth > 8:
            return None
        if w in self.roots:
            return [{"lexical": w, "surface_len": len(w)}]
        if not w:
            return None

        for suffix, _kind in self.suffix_catalog:
            if not w.endswith(suffix) or len(w) <= len(suffix):
                continue
            stem = w[:-len(suffix)]
            for cand in self._restore_stem_candidates(stem, suffix):
                if cand in self.roots and self._root_spelling_ok(cand, stem, suffix):
                    return [
                        {"lexical": cand, "surface_len": len(stem)},
                        {"lexical": suffix, "surface_len": len(suffix)},
                    ]
                inner_source = stem if cand == stem else cand
                inner = self._segment_core(inner_source, depth + 1)
                if not inner:
                    continue
                adjusted = [dict(part) for part in inner]
                if cand != stem:
                    extra = len(cand) - len(stem)
                    if not adjusted or adjusted[0]["surface_len"] < extra:
                        continue
                    adjusted[0]["surface_len"] -= extra
                if sum(part["surface_len"] for part in adjusted) != len(stem):
                    continue
                return adjusted + [{"lexical": suffix, "surface_len": len(suffix)}]

        for prefix in sorted(self.prefixes.keys(), key=len, reverse=True):
            if not w.startswith(prefix) or len(w) <= len(prefix):
                continue
            rest = self._segment_core(w[len(prefix):], depth + 1)
            if not rest:
                continue
            if sum(part["surface_len"] for part in rest) != len(w) - len(prefix):
                continue
            return [{"lexical": prefix, "surface_len": len(prefix)}] + rest
        return None

    def _segment_parts(self, word: str) -> List[Dict[str, Any]]:
        w = word.lower()
        parts = self._segment_core(w)
        if parts and sum(part["surface_len"] for part in parts) == len(w):
            return parts
        return [{"lexical": w, "surface_len": len(w)}]

    def segment_morphemes(self, word: str) -> List[str]:
        return [part["lexical"] for part in self._segment_parts(word)]

    def validate_contraction_placement(self, word: str, contraction: str) -> Dict[str, Any]:
        """Bridge Rule 및 위치 규칙 검증 (중복 등장 위치 전수 검사)"""
        w = word.lower()
        target = contraction.lower()
        c_info = self.contractions.get(target)

        if not c_info:
            return {"valid": False, "reason": f"Unknown contraction: '{target}'"}

        indices = [m.start() for m in re.finditer(re.escape(target), w)]
        if not indices:
            return {"valid": False, "reason": f"'{target}' not found in '{word}'"}

        parts = self._segment_parts(word)
        morphemes = [part["lexical"] for part in parts]
        boundaries = []
        if self.disallow_bridge:
            accum = 0
            for part in parts[:-1]:
                accum += part["surface_len"]
                boundaries.append(accum)

        rule = c_info.get("rule", {})

        for idx in indices:
            for b in boundaries:
                if idx < b < (idx + len(target)):
                    return {
                        "valid": False,
                        "rule": "Bridge Rule Violation",
                        "reason": f"Contraction '{target}' bridges morpheme boundary at {morphemes}"
                    }

            is_initial = (idx == 0)
            is_final = (idx + len(target) == len(w))
            is_medial = (not is_initial and not is_final)
            whole = (w == target)

            if rule.get("standingAloneOnly"):
                if not whole:
                    return {
                        "valid": False,
                        "rule": "Standing Alone Violation",
                        "reason": f"Contraction '{target}' is only used when it stands alone."
                    }
                continue

            if whole and rule.get("avoidWhenStandingAlone"):
                return {
                    "valid": False,
                    "rule": "Standing Alone Collision",
                    "reason": f"Contraction '{target}' is not used when those letters stand alone."
                }

            if whole and not rule.get("canStandAlone", False):
                return {
                    "valid": False,
                    "rule": "Standing Alone Violation",
                    "reason": f"Contraction '{target}' cannot stand alone."
                }

            if whole:
                continue

            if not rule.get("canFollowLetters", True) and not is_initial:
                return {
                    "valid": False,
                    "rule": "Prefix Only Violation",
                    "reason": f"Contraction '{target}' cannot follow letters."
                }

            if rule.get("requiresFollowingLetters") and is_final:
                return {
                    "valid": False,
                    "rule": "Prefix Only Violation",
                    "reason": f"Contraction '{target}' requires following letters."
                }

            if not rule.get("canPrecedeLetters", True) and not is_final:
                return {
                    "valid": False,
                    "rule": "Suffix/Final Only Violation",
                    "reason": f"Contraction '{target}' can only appear at syllable-final position."
                }

            if rule.get("requiresSurroundingLetters") and not is_medial:
                return {
                    "valid": False,
                    "rule": "Medial Only Violation",
                    "reason": f"Contraction '{target}' must have surrounding letters within word."
                }

        return {"valid": True, "priority": c_info.get("priority", 0), "details": c_info}

    def _is_closed_affix(self, suffix: str) -> bool:
        return suffix in self.inflections or suffix in self.derivations or suffix in {"s", "'s"}

    def _shortform_suffix_error(self, sf_word: str, suffix: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rule = data.get("rule", {})
        allowed = data.get("allowedSuffixes", set())
        specified = data.get("suffixesSpecified", False)

        if suffix in {"'s", "’s"}:
            suffix = "'s"
            if rule.get("allowApostropheS", False) and (not specified or suffix in allowed):
                return None

        if suffix == "s" and not rule.get("allowPluralS", False):
            return {
                "valid": False,
                "error": "Plural S Prohibited",
                "reason": f"Shortform '{sf_word}' cannot take plural -s."
            }

        if suffix in allowed and (rule.get("allowSuffix", False) or specified):
            return None

        if rule.get("allowCompound", False) and suffix and not self._is_closed_affix(suffix):
            return None

        if not rule.get("allowSuffix", False):
            return {
                "valid": False,
                "error": "Suffix Prohibited",
                "reason": f"Shortform '{sf_word}' cannot combine with suffixes ('{suffix}')."
            }

        return {
            "valid": False,
            "error": "Unallowed Suffix",
            "reason": (
                f"Suffix '-{suffix}' is not permitted for shortform '{sf_word}' "
                f"(Allowed: {sorted(allowed)})."
            )
        }

    def validate_shortform_usage(self, token: str) -> Dict[str, Any]:
        lower = token.lower().replace("’", "'")
        if lower in self.shortforms:
            return {"valid": True}

        candidates = []
        for sf_word, data in self.shortforms.items():
            start = 0
            while True:
                idx = lower.find(sf_word, start)
                if idx < 0:
                    break
                start = idx + 1
                if idx == 0 and idx + len(sf_word) == len(lower):
                    continue
                head = lower[:idx]
                tail = lower[idx + len(sf_word):]
                if head and head not in self.prefixes:
                    continue
                candidates.append((len(sf_word), sf_word, data, head, tail))

        if not candidates:
            return {"valid": True}

        best_len = max(item[0] for item in candidates)
        errors = []
        for length, sf_word, data, head, tail in candidates:
            if length != best_len:
                continue
            rule = data.get("rule", {})
            if head and not rule.get("allowPrefix", False):
                errors.append({
                    "valid": False,
                    "error": "Prefix Prohibited",
                    "reason": f"Shortform '{sf_word}' cannot take a prefix ('{head}')."
                })
                continue
            if tail:
                suffix_error = self._shortform_suffix_error(sf_word, tail, data)
                if suffix_error:
                    errors.append(suffix_error)
                    continue
            return {"valid": True}

        return errors[0]

    def _normalize_apostrophe(self, token: str) -> str:
        return token.replace("’", "'").replace("‘", "'").lower()

    def _is_word_apostrophe_suffix(self, token: str) -> bool:
        return self._normalize_apostrophe(token) in self.apostrophe_word_suffixes

    def _numeric_apostrophe_follow(self, tokens: List[str], index: int) -> Optional[str]:
        """숫자 뒤 's. 빈 문자열이면 글자가 이 토큰 안에 있고, None이면 해당 패턴이 아니다."""
        token = tokens[index]
        norm = self._normalize_apostrophe(token)
        if norm in self.numeric_apostrophe_blocks:
            return ""
        if norm == "'" and index + 1 < len(tokens):
            nxt = tokens[index + 1]
            if nxt.isalpha() and ("'" + nxt.lower()) in self.numeric_apostrophe_blocks:
                return nxt.lower()
        return None

    def _is_standing_alone(self, tokens: List[str], index: int) -> bool:
        """인접 구분 부호가 독립 단어(standing alone)를 유지하는지 판별한다."""
        return (
            self._side_stands_alone(tokens, index, -1)
            and self._side_stands_alone(tokens, index, 1)
        )

    def _side_stands_alone(self, tokens: List[str], index: int, step: int) -> bool:
        neighbor = index + step
        if neighbor < 0 or neighbor >= len(tokens):
            return True
        tok = tokens[neighbor]
        if tok.isspace():
            return True
        if self._is_word_apostrophe_suffix(tok):
            return True
        if tok in self.disallowed_delimiters:
            return False
        if tok in self.surrounding_allowed_symbols:
            return True
        if any(ch.isalnum() for ch in tok):
            return False
        return False

    def _needs_grade1(self, token: str) -> bool:
        if not token:
            return False
        first = token[0]
        return (
            first in self.grade1_targets
            or first.lower() in self.grade1_targets
            or first.upper() in self.grade1_targets
        )

    def _wordsign_entry(self, lower_token: str) -> Optional[Dict[str, Any]]:
        """알파벳 단어약어는 but, can처럼 단어에만 대응한다. 한 글자 b는 철자표의 단독 글자다."""
        if lower_token in self.word_to_wordsign:
            return self.word_to_wordsign[lower_token]
        return None

    def _wordsign_suffix_issue(self, lower_token: str) -> Optional[Dict[str, Any]]:
        if self.wordsign_rule.get("allowSuffix", True):
            return None
        if lower_token in self.shortforms:
            return None
        for word in sorted(self.word_to_wordsign, key=len, reverse=True):
            if not lower_token.startswith(word) or len(lower_token) == len(word):
                continue
            suffix = lower_token[len(word):].replace("’", "'")
            if suffix == "'s" and self.wordsign_rule.get("allowApostropheS", False):
                return None
            if suffix in self.inflections or suffix in self.derivations:
                return {
                    "valid": False,
                    "error": "Wordsign Suffix Prohibited",
                    "reason": f"Alphabetic wordsign '{word}' cannot combine with suffix '{suffix}'."
                }
            break
        return None

    def _continuation_reaches_digit(self, tokens: List[str], start: int) -> bool:
        """쉼표·소수점·쌍점·분수선은 바로 뒤 숫자까지, 숫자 빈칸은 다음 숫자만 모드를 유지한다."""
        index = start
        while index < len(tokens):
            token = tokens[index]
            if token.isdigit():
                return True
            if token.isspace() or token not in self.continuation_chars:
                return False
            index += 1
        return False

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
            suffix_body = "|".join(re.escape(body) for body in self.apostrophe_suffix_bodies)
            apostrophe_match = (
                re.match(rf"^([a-zA-Z]+)(['’](?i:{suffix_body}))$", tok)
                if suffix_body else None
            )
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
        pending_plain = None
        grade1_dots = "-".join(str(dot) for dot in self.grade1_dots)

        for i, token in enumerate(tokens):
            if token.isspace():
                pending_plain = None
                if (
                    in_numeric_mode
                    and token in self.continuation_chars
                    and self._continuation_reaches_digit(tokens, i + 1)
                ):
                    analysis.append({
                        "token": token,
                        "type": "numeric_space",
                        "validations": [{
                            "event": "Connector Retains Numeric Mode",
                            "char": token
                        }]
                    })
                    continue
                in_numeric_mode = False
                continue

            item_report = {"token": token, "type": "unknown", "validations": []}

            if pending_plain:
                if token.lower() == pending_plain:
                    item_report["type"] = "plain_letter"
                    item_report["validations"].append({
                        "event": "Letter After Numeric Apostrophe",
                        "letter": token,
                        "requires": "Plain letter, not a grade-2 wordsign or contraction"
                    })
                    pending_plain = None
                    analysis.append(item_report)
                    continue
                pending_plain = None

            if token.isdigit():
                item_report["type"] = "numeric"
                if not in_numeric_mode:
                    item_report["validations"].append({
                        "event": "Numeric Mode Start",
                        "requires": f"Numeric Indicator ({self.num_prefix})"
                    })
                    in_numeric_mode = True
                else:
                    item_report["validations"].append({"event": "Numeric Mode Retained", "requires": None})

            elif in_numeric_mode and self._numeric_apostrophe_follow(tokens, i) is not None:
                follow = self._numeric_apostrophe_follow(tokens, i)
                item_report["type"] = "apostrophe_after_number"
                item_report["validations"].append({
                    "event": "Numeric Apostrophe Terminates Numeric Mode",
                    "suffix": token,
                    "requires": "Plain letter, not a grade-2 contraction"
                })
                in_numeric_mode = False
                if follow:
                    pending_plain = follow

            elif token.startswith(("'", "’")) and (len(token) == 1 or token[1:].isalpha()):
                item_report["type"] = "apostrophe_contraction"
                item_report["validations"].append({
                    "event": "Apostrophe Suffix/Contraction",
                    "suffix": token,
                    "requires": "Grade 2 Suffix Resolution"
                })
                in_numeric_mode = False

            elif (
                token in self.surrounding_allowed_symbols
                or token in self.disallowed_delimiters
                or token in self.terminating_chars
                or token in self.continuation_chars
            ):
                item_report["type"] = "punctuation"
                if in_numeric_mode:
                    if token in self.continuation_chars and self._continuation_reaches_digit(tokens, i + 1):
                        item_report["validations"].append({
                            "event": "Connector Retains Numeric Mode",
                            "char": token
                        })
                    elif token in self.terminating_chars:
                        item_report["validations"].append({
                            "event": "Connector Terminates Numeric Mode",
                            "char": token
                        })
                        in_numeric_mode = False
                    else:
                        item_report["validations"].append({
                            "event": "Non-numeric Punctuation Terminates Numeric Mode",
                            "glyph": token
                        })
                        in_numeric_mode = False
                else:
                    item_report["validations"].append({"event": "Standard Punctuation", "glyph": token})

            elif token.isalpha():
                item_report["type"] = "word"

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
                wordsign_suppressed = False

                if in_numeric_mode:
                    if self._needs_grade1(token):
                        item_report["validations"].append({
                            "warning": "Alphanumeric Glyph Collision",
                            "resolution": (
                                f"Requires Grade 1 Indicator ({self.grade1_prefix}, "
                                f"dots {grade1_dots}) before '{token[0]}'"
                            )
                        })
                    if self.wordsign_suppression and self._wordsign_entry(lower_token):
                        wordsign_suppressed = True
                        item_report["validations"].append({
                            "warning": "Wordsign Suppressed In Numeric Mode",
                            "rule": self.wordsign_suppression,
                            "reason": f"'{token}' is not read as a wordsign while numeric mode is active."
                        })
                    in_numeric_mode = False

                morphemes = self.segment_morphemes(lower_token)
                item_report["morphemes"] = morphemes

                isolated = self.isolated_letters.get(lower_token) if len(lower_token) == 1 else None
                if isolated:
                    note = {
                        "type": "Isolated Letter",
                        "letter": lower_token,
                        "unicode": isolated.get("unicode"),
                    }
                    if isolated.get("requiresGrade1") and self._is_standing_alone(tokens, i):
                        note["indicator"] = self.letter_grade1_indicator
                        note["reason"] = (
                            f"Standing-alone letter '{lower_token}' uses the grade-1 symbol "
                            f"indicator ({self.letter_grade1_indicator}) before the letter cell."
                        )
                    item_report["validations"].append(note)

                if not wordsign_suppressed and not isolated:
                    wordsign = self._wordsign_entry(lower_token)
                    if wordsign:
                        if self._is_standing_alone(tokens, i):
                            item_report["validations"].append({
                                "type": "Alphabetic Wordsign",
                                "representation": wordsign["word"]
                            })
                        else:
                            item_report["validations"].append({
                                "warning": "Wordsign Not Standing Alone",
                                "reason": f"'{token}' does not satisfy standing-alone requirements."
                            })
                    else:
                        suffix_issue = self._wordsign_suffix_issue(lower_token)
                        if suffix_issue:
                            item_report["validations"].append(suffix_issue)

                if lower_token in self.shortforms:
                    item_report["validations"].append({
                        "type": "Shortform",
                        "expansion": lower_token,
                        "symbol": self.shortforms[lower_token]["shortform"]
                    })

                sf_res = self.validate_shortform_usage(lower_token)
                if not sf_res["valid"]:
                    item_report["validations"].append(sf_res)

                for c_key in self.contractions.keys():
                    if c_key in lower_token:
                        res = self.validate_contraction_placement(lower_token, c_key)
                        if not res["valid"]:
                            item_report["validations"].append(res)

            elif in_numeric_mode:
                item_report["validations"].append({
                    "event": "Non-numeric Symbol Terminates Numeric Mode",
                    "glyph": token
                })
                in_numeric_mode = False

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
