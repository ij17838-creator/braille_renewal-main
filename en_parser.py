import json
import os
import re
from typing import List, Optional

from data_paths import find_data_file


# =====================================================================
# 1. 형태소 분절기 (Morpheme Segmenter)
# =====================================================================
class MorphemeSegmenter:
    """
    lexicon_en.json 규칙을 기반으로 단어를 (접두사)-(어근)-(접미사)로 분절하여
    형태소 경계(Morpheme Boundary)를 가로지르는 잘못된 약어 적용을 방지합니다.
    사전에 등록되지 않은 단어라도 일반적인 접두사/접미사 규칙을 기반으로 완화 분절합니다.
    """
    DEFAULT_PREFIXES = ["re", "un", "dis", "pre", "mis", "in", "im", "non"]
    DEFAULT_SUFFIXES = ["ing", "ed", "ly", "tion", "ment", "ness", "ful", "less", "able", "ible", "er", "est", "s", "es"]

    def __init__(self, lexicon_path: str):
        if not os.path.exists(lexicon_path):
            raise FileNotFoundError(f"Lexicon file not found: {lexicon_path}")

        with open(lexicon_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.prefixes = data.get("prefixes", {}).get("items", {})
        self.roots = data.get("roots", {}).get("items", {})
        self.inflectional_suffixes = data.get("inflectional_suffixes", {}).get("items", {})
        self.derivational_suffixes = data.get("derivational_suffixes", {}).get("items", {})

    def segment_word(self, word: str) -> List[str]:
        w = word.lower()

        # 어근 자체와 일치하는 경우
        if w in self.roots:
            return [w]

        matched_prefix = ""
        rest_after_prefix = w

        # 1. 접두사 분리 검사 (사전 기반 긴 접두사 우선)
        sorted_prefixes = sorted(self.prefixes.keys(), key=len, reverse=True)
        for p in sorted_prefixes:
            if w.startswith(p) and len(w) > len(p):
                matched_prefix = p
                rest_after_prefix = w[len(p):]
                break

        # 2. 어근 및 접미사 분리 탐색 (사전 기반)
        tokens = self._match_root_and_suffix(rest_after_prefix)
        if tokens:
            return [matched_prefix] + tokens if matched_prefix else tokens

        # 접두사 없이 전체 단어로 재시도
        if matched_prefix:
            tokens_without_prefix = self._match_root_and_suffix(w)
            if tokens_without_prefix:
                return tokens_without_prefix

        # 3. 사전 미포함 단어 Fallback 분절 완화 규칙
        fallback_tokens = self._fallback_segment(w)
        if fallback_tokens:
            return fallback_tokens

        # 분절 규칙에 걸리지 않는 일반 어휘
        return [w]

    def _match_root_and_suffix(self, sub_word: str) -> Optional[List[str]]:
        if sub_word in self.roots:
            return [sub_word]

        all_suffixes = {**self.inflectional_suffixes, **self.derivational_suffixes}
        sorted_suffixes = sorted(all_suffixes.keys(), key=len, reverse=True)

        for s in sorted_suffixes:
            if sub_word.endswith(s):
                stem_candidate = sub_word[:-len(s)]
                # 어근 직접 매칭
                if stem_candidate in self.roots:
                    return [stem_candidate, s]

                # silent 'e' 탈락 복원 (care + ing -> caring)
                if (stem_candidate + "e") in self.roots and self.roots[stem_candidate + "e"].get("hasSilentE"):
                    return [stem_candidate + "e", s]

                # 자음 중복 복원 (run + ing -> running)
                if len(stem_candidate) > 2 and stem_candidate[-1] == stem_candidate[-2]:
                    if stem_candidate[:-1] in self.roots:
                        return [stem_candidate[:-1], s]

                # y -> i 변환 복원 (carry + ed -> carried)
                if stem_candidate.endswith("i"):
                    y_stem = stem_candidate[:-1] + "y"
                    if y_stem in self.roots:
                        return [y_stem, s]

        return None

    def _fallback_segment(self, w: str) -> Optional[List[str]]:
        """사전에 등록되지 않은 단어의 접두사/접미사 완화 분절"""
        all_prefixes = sorted(set(list(self.prefixes.keys()) + self.DEFAULT_PREFIXES), key=len, reverse=True)
        all_suffixes = sorted(set(list(self.inflectional_suffixes.keys()) + list(self.derivational_suffixes.keys()) + self.DEFAULT_SUFFIXES), key=len, reverse=True)

        matched_p = ""
        core = w

        for p in all_prefixes:
            if core.startswith(p) and len(core) - len(p) >= 3:
                matched_p = p
                core = core[len(p):]
                break

        matched_s = ""
        for s in all_suffixes:
            if core.endswith(s) and len(core) - len(s) >= 2:
                matched_s = s
                core = core[:-len(s)]
                break

        res = []
        if matched_p:
            res.append(matched_p)
        if core:
            res.append(core)
        if matched_s:
            res.append(matched_s)

        return res if len(res) > 1 else None


# =====================================================================
# 2. 통합 점자 ↔ 텍스트 변환 엔진 (Braille Engine)
# =====================================================================
class BrailleEngine:
    """
    UEB 규정에 따른 양방향 변환 엔진.
    수표 모드(⠼), 1급 기호표(⠰), 형태소 경계 검사, 약어 우선순위를 처리합니다.
    """
    def __init__(self, base_data_dir: Optional[str] = None):
        self.base_data_dir = base_data_dir
        lexicon_path = find_data_file("lexicon_en.json", base_data_dir)
        self.segmenter = MorphemeSegmenter(lexicon_path)
        self._load_all_rules()

    def _find_file(self, filename: str, _search_dirs: Optional[List[str]] = None) -> str:
        return find_data_file(filename, self.base_data_dir)

    def _load_all_rules(self):
                # 1. 알파벳 기본 및 단어약어
        spell_path = self._find_file("en_spell.json")
        with open(spell_path, "r", encoding="utf-8") as f:
            spell_data = json.load(f)
            self.spelling = {}
            for k, v in spell_data["single_letter"]["items"].items():
                item_key = v.get("char") or v.get("word") or v.get("letter") or k
                self.spelling[item_key] = v["unicode"]
            self.rev_spelling = {v: k for k, v in self.spelling.items()}

            items = spell_data["alphabetic_wordsign"]["items"]
            self.wordsigns = {k: v["unicode"] for k, v in items.items()}
            self.word_to_wordsign = {v["word"].lower(): v["unicode"] for k, v in items.items()}
            self.braille_to_wordsign = {v["unicode"]: v["word"].lower() for k, v in items.items()}

        # 2. 숫자 및 기호 규칙 (ueb_number_rules.json 우선 로드)
        num_path = self._find_file("ueb_number_rules.json")
        with open(num_path, "r", encoding="utf-8") as f:
            num_data = json.load(f)

        # 알파벳-숫자 대응표 (a->1, b->2, ..., j->0) 매핑
        digit_keys = ["j", "a", "b", "c", "d", "e", "f", "g", "h", "i"]
        self.digits = {str(i): self.spelling[digit_keys[i]] for i in range(10)}
        self.rev_digits = {v: str(i) for i, v in enumerate(self.digits.values())}

        # 수표 및 1급 기호표 로드
        self.num_prefix = num_data["initiator_condition"]["braille"]
        self.grade1_prefix = num_data["collision_resolutions"]["alphanumeric_transition"]["grade1_indicator"]

        # 숫자 모드 유지 커넥터 및 종료 커넥터 로드
        self.connectors = {}
        for conn in num_data.get("scope_maintenance", {}).get("continuation_connectors", []):
            self.connectors[conn["char"]] = conn["braille"]

        self.terminating_connectors = {}
        for conn in num_data.get("scope_maintenance", {}).get("terminating_connectors", []):
            self.terminating_connectors[conn["char"]] = conn["braille"]

        # 긴 점열(엔대시·엠대시)을 한 칸 기호보다 먼저 맞춘다.
        self.numeric_sequences = []
        for char, braille in self.terminating_connectors.items():
            self.numeric_sequences.append((braille, char, True))
        for char, braille in self.connectors.items():
            self.numeric_sequences.append((braille, char, False))
        self.numeric_sequences.sort(key=lambda item: (-len(item[0]), item[2]))

        # 같은 점형은 문맥 태그와 함께 쌓는다. 나중 기호가 앞 기호를 덮지 않는다.
        self.rev_symbol_senses = {}
        for char, braille in self.connectors.items():
            self._add_symbol_sense(braille, char, "numeric")
        for char, braille in self.terminating_connectors.items():
            self._add_symbol_sense(braille, char, "numeric_terminating")
        for group in num_data.get("standing_alone_rules", {}).get("adjacent_delimiters", {}).values():
            for sym in group.get("symbols", []):
                context = "numeric_or_punctuation" if sym["char"] in ",.!" else "punctuation"
                self._add_symbol_sense(sym["braille"], sym["char"], context)

        # 3. 통합 축어(Shortforms)
        self.shortforms_standalone = {}
        self.shortforms_inflected = {}
        self.shortforms_compound = {}
        self.rev_shortforms = {}
        self.shortform_root_chars = {}

        sf_path = self._find_file("en_shortform.json")
        if os.path.exists(sf_path):
            with open(sf_path, "r", encoding="utf-8") as f:
                sf_data = json.load(f)
                for k, v in sf_data.get("shortform_standalone_only", {}).get("items", {}).items():
                    word = v["word"].lower()
                    self.shortforms_standalone[word] = v["unicode"]
                    self.rev_shortforms[v["unicode"]] = word
                    if v.get("rootChars"):
                        self.shortform_root_chars[word] = list(v["rootChars"])

                inflected_rule = sf_data.get("shortform_inflected", {}).get("rule", {})
                for k, v in sf_data.get("shortform_inflected", {}).get("items", {}).items():
                    word = v["word"].lower()
                    self.shortforms_inflected[word] = {
                        "unicode": v["unicode"],
                        "suffixes": inflected_rule.get("allowedSuffixes", [])
                    }
                    self.rev_shortforms[v["unicode"]] = word

                for k, v in sf_data.get("shortform_compound_allowed", {}).get("items", {}).items():
                    word = v["word"].lower()
                    self.shortforms_compound[word] = v["unicode"]
                    self.rev_shortforms[v["unicode"]] = word

        # 4. 통합 약어(Contractions) 및 독립 사용 가능 약어 캐시
        self.groupsigns = []
        self.standalone_contractions = {}
        self.rev_groupsign_senses = {}
        self.contraction_items = {}

        c_path = self._find_file("en_contractions.json")
        if os.path.exists(c_path):
            with open(c_path, "r", encoding="utf-8") as f:
                c_data = json.load(f)
                for group in c_data.get("groups", []):
                    prio = group.get("priority", 50)
                    rule = group.get("rule", {})
                    can_standalone = rule.get("canStandAlone", False)

                    for text_val, item in group.get("items", {}).items():
                        self.contraction_items[text_val] = item
                        self.groupsigns.append((text_val, item["unicode"], prio, rule))
                        self.rev_groupsign_senses.setdefault(item["unicode"], []).append({
                            "text": text_val,
                            "rule": rule,
                            "priority": prio,
                            "unicode": item["unicode"],
                            "rootChar": item.get("rootChar"),
                        })
                        if can_standalone:
                            self.standalone_contractions[text_val] = item["unicode"]

                for senses in self.rev_groupsign_senses.values():
                    for sense in senses:
                        root = sense.get("rootChar")
                        if not root:
                            continue
                        root_item = self.contraction_items.get(root)
                        if root_item is None:
                            raise ValueError(f"rootChar {root!r}가 en_contractions.json에 없습니다.")
                        if root_item["unicode"] not in sense["unicode"]:
                            raise ValueError(
                                f"{sense['text']}의 점자 {sense['unicode']!r}에 강세 약어 {root}({root_item['unicode']})가 없습니다."
                            )
                        sense["rootEntry"] = root_item
                        sense["rootUnicode"] = root_item["unicode"]

                for word, roots in self.shortform_root_chars.items():
                    uni = self.shortforms_standalone[word]
                    for root in roots:
                        root_item = self.contraction_items.get(root)
                        if root_item is None:
                            raise ValueError(f"{word}의 rootChars {root!r}가 en_contractions.json에 없습니다.")
                        if not uni.startswith(root_item["unicode"]):
                            raise ValueError(
                                f"{word}의 점자 {uni!r}가 강세 약어 {root}({root_item['unicode']})로 시작하지 않습니다."
                            )

        self.groupsigns.sort(key=lambda x: (x[2], -len(x[0])))

    def _add_symbol_sense(self, braille: str, char: str, context: str):
        if not braille:
            return
        bucket = self.rev_symbol_senses.setdefault(braille, [])
        if any(item["char"] == char and item["context"] == context for item in bucket):
            return
        bucket.append({"char": char, "context": context})

    # ------------------ TEXT -> BRAILLE ------------------ #
    def text_to_braille(self, text: str) -> str:
        # 단어, 숫자, 특수문자 분리 정규식
        tokens = re.findall(r"[0-9]+|[a-zA-Z]+(?:'(?:d|ll|re|s|t|ve|m))?|'(?:[a-zA-Z]+)|[^\w\s]|[\s]", text)
        result = []
        in_numeric_mode = False

        CAP_LETTER = "\u2820"  # ⠠
        CAP_WORD = "\u2820\u2820"  # ⠠⠠

        for index, token in enumerate(tokens):
            if not token:
                continue

            # 아라비아 숫자 처리
            if token.isdigit():
                prefix = "" if in_numeric_mode else self.num_prefix
                in_numeric_mode = True
                converted = "".join(self.digits[d] for d in token)
                result.append(prefix + converted)
                continue

            # 쉼표·온점·쌍점·분수선·숫자 빈칸은 뒤에 숫자가 이어질 때만 수표를 유지한다.
            if in_numeric_mode and token in self.connectors:
                if self._continuation_reaches_digit(tokens, index + 1):
                    result.append(self.connectors[token])
                    continue
                result.append(" " if token == " " else self.connectors[token])
                in_numeric_mode = False
                continue

            # 하이픈·대시는 수표를 끝내므로 다음 숫자는 수표를 다시 붙인다.
            if in_numeric_mode and token in self.terminating_connectors:
                result.append(self.terminating_connectors[token])
                in_numeric_mode = False
                continue

            # 영문 단어 및 아포스트로피 결합형 처리
            if re.match(r"^[a-zA-Z]+(?:'[a-zA-Z]+)?$", token) or re.match(r"^'[a-zA-Z]+$", token):
                cap_indicator = ""
                if token.isupper() and len(token) > 1:
                    cap_indicator = CAP_WORD
                elif token[0].isupper():
                    cap_indicator = CAP_LETTER

                lower_token = token.lower()
                prefix_indicator = ""

                # 숫자 직후 a~j 글자가 올 경우 1급 기호표 삽입
                if in_numeric_mode:
                    clean_start = lower_token.lstrip("'")
                    if clean_start and clean_start[0] in "abcdefghij":
                        prefix_indicator = self.grade1_prefix
                    in_numeric_mode = False

                apostrophe_match = re.match(r"^([a-zA-Z]+)('(?=[a-zA-Z]+).+)$", lower_token)
                if apostrophe_match:
                    stem, apostrophe_part = apostrophe_match.groups()
                    braille_word = self._translate_word(stem) + "".join(self.spelling.get(ch, ch) for ch in apostrophe_part)
                else:
                    braille_word = self._translate_word(lower_token)

                result.append(prefix_indicator + cap_indicator + braille_word)
            else:
                in_numeric_mode = False
                result.append(token)

        return "".join(result)

    def _continuation_reaches_digit(self, tokens: List[str], start: int) -> bool:
        index = start
        while index < len(tokens):
            token = tokens[index]
            if token.isdigit():
                return True
            if token not in self.connectors:
                return False
            index += 1
        return False

    def _translate_word(self, word: str) -> str:
        # 1. 알파벳 단어 약어 (Alphabetic Wordsigns: but, can, do 등)
        if word in self.word_to_wordsign:
            return self.word_to_wordsign[word]

        # 2. 독립 사용 가능한 약어 (Initial Contractions 및 en/in 등)
        if word in self.standalone_contractions:
            return self.standalone_contractions[word]

        # 3. 축어 처리 (Shortforms)
        # 3-1. 단독형 축어
        if word in self.shortforms_standalone:
            return self.shortforms_standalone[word]

        # 3-2. 굴절 허용 축어
        for root_word, info in self.shortforms_inflected.items():
            if word == root_word:
                return info["unicode"]
            for sfx in info["suffixes"]:
                if word == root_word + sfx:
                    return info["unicode"] + "".join(self.spelling.get(c, c) for c in sfx)

        # 3-3. 복합어 축어 치환
        for root_word, b_code in self.shortforms_compound.items():
            if word == root_word:
                return b_code
            if root_word in word:
                idx = word.find(root_word)
                prefix_part = word[:idx]
                suffix_part = word[idx + len(root_word):]

                braille_prefix = self._translate_word(prefix_part) if prefix_part else ""
                braille_suffix = self._translate_word(suffix_part) if suffix_part else ""
                return braille_prefix + b_code + braille_suffix

        # 4. 형태소 분절 후 묶음자 약어 변환
        morphemes = self.segmenter.segment_word(word)
        return "".join(self._translate_morpheme(m) for m in morphemes)

    def _translate_morpheme(self, morph: str) -> str:
        segments = [[morph, False]]

        for pattern, braille_unicode, _, rule in self.groupsigns:
            new_segments = []
            for text_chunk, is_converted in segments:
                if is_converted:
                    new_segments.append([text_chunk, True])
                    continue

                req_surrounding = rule.get("requiresSurroundingLetters", False)
                requires_following = rule.get("requiresFollowingLetters", False)
                can_follow = rule.get("canFollowLetters", True)

                # 1. 어중 전용 (ea, bb, cc, ff, gg 등)
                if req_surrounding:
                    regex = re.compile(rf'(?<=[a-zA-Z])({re.escape(pattern)})(?=[a-zA-Z])')
                    last_idx = 0
                    for m in regex.finditer(text_chunk):
                        start, end = m.span(1)
                        if start > last_idx:
                            new_segments.append([text_chunk[last_idx:start], False])
                        new_segments.append([braille_unicode, True])
                        last_idx = end
                    if last_idx < len(text_chunk):
                        new_segments.append([text_chunk[last_idx:], False])

                # 2. 접두 전용 약어 (be, con, dis 등): 분절된 단독 접두사 토큰이거나 접두어 형태일 때 매칭
                elif not can_follow and requires_following:
                    if text_chunk.startswith(pattern) and len(text_chunk) > len(pattern):
                        new_segments.append([braille_unicode, True])
                        new_segments.append([text_chunk[len(pattern):], False])
                    else:
                        new_segments.append([text_chunk, False])

                # 3. 일반 묶음자 및 초성/종성 약어
                else:
                    if pattern in text_chunk:
                        parts = text_chunk.split(pattern)
                        for i, p in enumerate(parts):
                            if p:
                                new_segments.append([p, False])
                            if i < len(parts) - 1:
                                new_segments.append([braille_unicode, True])
                    else:
                        new_segments.append([text_chunk, False])

            segments = new_segments

        # 미변환된 영문 텍스트 세그먼트만 1:1 점자 변환
        result = []
        for text_chunk, is_converted in segments:
            if is_converted:
                result.append(text_chunk)
            else:
                result.append("".join(self.spelling.get(ch, ch) for ch in text_chunk))

        return "".join(result)

    # ------------------ BRAILLE -> TEXT ------------------ #
    def braille_to_text(self, braille_str: str) -> str:
        tokens = re.findall(r'[\u2800-\u28FF]+|[^\u2800-\u28FF]+', braille_str)
        result = []

        for token in tokens:
            if not token.strip() or not any('\u2800' <= c <= '\u28FF' for c in token):
                result.append(token)
                continue

            result.append(self._translate_braille_token(token))

        return "".join(result)

    def _translate_braille_token(self, b_token: str) -> str:
        # 1. 단독 단어약어 매핑 (⠃ -> but)
        if b_token in self.braille_to_wordsign:
            return self.braille_to_wordsign[b_token]

        # 2. 축어 역매핑 (⠁⠃ -> about)
        if b_token in self.rev_shortforms:
            return self.rev_shortforms[b_token]

        # 3. 수표 포함 토큰 디코딩
        if self.num_prefix in b_token:
            return self._decode_braille_with_numeric_mode(b_token)

        return self._decode_contracted(b_token)

    def _groupsign_context_ok(self, token: str, i: int, blen: int, rule: dict) -> bool:
        end = i + blen
        prev_letter = i > 0 and token[i - 1] in self.rev_spelling
        next_letter = end < len(token) and token[end] in self.rev_spelling
        # 어중이고 앞뒤에 글자가 있으면 bb/cc/dd. 어두이면 be/con/dis.
        if rule.get("requiresSurroundingLetters"):
            return prev_letter and next_letter
        if rule.get("requiresFollowingLetters") and not rule.get("canFollowLetters", True):
            return i == 0 and end < len(token)
        return True

    def _punctuation_mode(self, token: str, i: int) -> bool:
        prev_letter = i > 0 and token[i - 1] in self.rev_spelling
        next_letter = i + 1 < len(token) and token[i + 1] in self.rev_spelling
        if prev_letter and next_letter:
            return False
        if i == 0 and next_letter:
            return False
        return True

    def _mark_in_mode(self, cell: str, contexts: tuple) -> Optional[str]:
        for sense in self.rev_symbol_senses.get(cell, []):
            if sense["context"] in contexts:
                return sense["char"]
        return None

    def _decode_contracted(self, token: str) -> str:
        i = 0
        n = len(token)
        out = []
        while i < n:
            match_text = None
            match_len = 0
            match_prio = 10 ** 9
            for braille, senses in self.rev_groupsign_senses.items():
                if not token.startswith(braille, i):
                    continue
                blen = len(braille)
                for sense in senses:
                    if not self._groupsign_context_ok(token, i, blen, sense["rule"]):
                        continue
                    prio = sense["priority"]
                    if blen > match_len or (blen == match_len and prio < match_prio):
                        match_text = sense["text"]
                        match_len = blen
                        match_prio = prio
            if match_text:
                out.append(match_text)
                i += match_len
                continue
            # ⠂ ⠲ ⠖는 문장부호 모드일 때만 쉼표, 마침표, 느낌표다.
            if token[i] in ("⠂", "⠲", "⠖") and self._punctuation_mode(token, i):
                mark = self._mark_in_mode(token[i], ("numeric_or_punctuation", "punctuation", "numeric"))
                if mark:
                    out.append(mark)
                    i += 1
                    continue
            out.append(self.rev_spelling.get(token[i], token[i]))
            i += 1
        return "".join(out)

    def _decode_braille_with_numeric_mode(self, token: str) -> str:
        res = []
        in_num = False
        i = 0
        n = len(token)
        g1_len = len(self.grade1_prefix)

        while i < n:
            # 1급 기호표 확인 (가변 길이 대응)
            if self.grade1_prefix and token[i:i + g1_len] == self.grade1_prefix:
                in_num = False
                i += g1_len
                continue

            ch = token[i]
            if ch == self.num_prefix:
                in_num = True
                i += 1
                continue

            if in_num:
                matched = False
                for braille, char, ends_mode in self.numeric_sequences:
                    if token.startswith(braille, i):
                        res.append(char)
                        i += len(braille)
                        if ends_mode:
                            in_num = False
                        matched = True
                        break
                if matched:
                    continue
                if ch in self.rev_digits:
                    res.append(self.rev_digits[ch])
                else:
                    in_num = False
                    res.append(self.rev_spelling.get(ch, ch))
            else:
                if ch in ("⠂", "⠲", "⠖") and self._punctuation_mode(token, i):
                    mark = self._mark_in_mode(ch, ("numeric_or_punctuation", "punctuation"))
                    res.append(mark or self.rev_spelling.get(ch, ch))
                else:
                    res.append(self.rev_spelling.get(ch, ch))
            i += 1

        return "".join(res)