import json
import os
import re
from typing import Dict, List, Optional, Tuple

from engine.data_paths import find_data_file


# =====================================================================
# 1. 형태소 분절기 (Morpheme Segmenter)
# =====================================================================
class MorphemeSegmenter:
    """
    lexicon_en.json에 실제로 있는 접두사·어근·접미사만 분절한다.
    사전에 없는 접미 모양(er, tion 등)으로 경계를 만들면 other의 the, reading의 ea처럼
    허용된 약어까지 막는다.
    """

    def __init__(self, lexicon_path: str):
        if not os.path.exists(lexicon_path):
            raise FileNotFoundError(f"Lexicon file not found: {lexicon_path}")

        with open(lexicon_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.prefixes = data.get("prefixes", {}).get("items", {})
        self.roots = data.get("roots", {}).get("items", {})
        self.inflectional_suffixes = data.get("inflectional_suffixes", {}).get("items", {})
        self.derivational_suffixes = data.get("derivational_suffixes", {}).get("items", {})
        bridge = (data.get("combining_rules") or {}).get("bridge_rule") or {}
        self.disallow_bridge = bridge.get("disallowCrossMorphemeContraction", True)

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

        # reaction = re + action 처럼, 접두 뒤가 등록된 어근으로 시작하면 그 경계만 남긴다.
        rooted = self._prefix_on_root(w)
        if rooted:
            return rooted

        return [w]

    def _prefix_on_root(self, word: str) -> Optional[List[str]]:
        for prefix in sorted(self.prefixes, key=len, reverse=True):
            if not word.startswith(prefix) or len(word) == len(prefix):
                continue
            rest = word[len(prefix):]
            if any(rest == root or rest.startswith(root) for root in self.roots):
                return [prefix, rest]
        return None

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


# =====================================================================
# 2. 통합 점자 ↔ 텍스트 변환 엔진 (Braille Engine)
# =====================================================================
class BrailleEngine:
    """
    UEB 규정에 따른 양방향 변환 엔진.
    수표 모드(⠼), 1급 점자표(⠰, 5·6점), 형태소 경계 검사, 약어 우선순위를 처리합니다.
    """
    # 대문자표는 영어 JSON에 따로 없고, 점역과 역점역이 같은 칸을 쓴다.
    CAP_LETTER = "\u2820"
    CAP_WORD = "\u2820\u2820"
    # UEB 7.6.8: 홀로 놓인 큰따옴표(와 그 짝)는 두 칸 따옴표로 적어 his·was로 읽히지 않게 한다.
    TWO_CELL_DOUBLE_QUOTES = {"“": "\u2818\u2826", "”": "\u2818\u2834"}
    # 낱말 앞에 붙은 부호는 여는 부호로 읽는다 (UEB 7.6.7: 낱말 앞 ⠦는 여는 큰따옴표).
    OPENING_MARKS = "“‘(["
    # UEB 10.5.1: 아래 점만 쓰는 부호(따옴표 포함)에 붙으면 이 약자를 쓰지 않고 풀어 쓴다.
    LOWER_WORDSIGN_WORDS = {"be", "were", "his", "was"}
    UPPER_DOTS = 0x01 | 0x08  # 1점, 4점
    # UEB 10.9.3: 축어 목록에 없는 긴 낱말에서도 쓰는 축어. (b) children은 뒤에 모음·y가 없을 때,
    # (c)의 일곱 개는 낱말 맨 앞이고 뒤에 모음·y가 없을 때만 축어로 읽는다.
    SHORTFORM_ANYWHERE = ("braille", "great")
    SHORTFORM_ANYWHERE_BEFORE_CONSONANT = ("children",)
    SHORTFORM_WORD_START = ("blind", "first", "friend", "good", "letter", "little", "quick")
    # UEB 10.9.5: s를 붙여도 축어로 쓰지 않는 세 낱말 (abouts, almosts, hims)
    SHORTFORM_NO_S = ("about", "almost", "him")
    SHORTFORM_10_9_3 = ("braille", "great", "children", "blind", "first", "friend", "good", "letter", "little", "quick")
    VOWELS_Y = set("aeiouy")
    CAP_WORD_TERMINATOR = "\u2820\u2804"
    WORD_BEGINNING_SIGNS = ("ing", "be", "con", "dis")
    OPENING_PUNCTUATION = "([{\"'“‘«"
    WORD_BEGINNING_BREAKS = "-‐‑–—―"
    PREFIX_ABBREVIATIONS = ("cont", "contd", "dist", "cons", "conn")
    DIS_H_PREFIXED = ("hon", "hea", "har", "hab")
    _word_beginning = True
    def __init__(self, base_data_dir: Optional[str] = None):
        self.base_data_dir = base_data_dir
        lexicon_path = find_data_file("lexicon_en.json", base_data_dir)
        self.segmenter = MorphemeSegmenter(lexicon_path)
        self._load_all_rules()

    def _find_file(self, filename: str, _search_dirs: Optional[List[str]] = None) -> str:
        return find_data_file(filename, self.base_data_dir)

    def _load_all_rules(self):
        self._load_spell()
        self._load_digits()
        self._load_number_rules()
        self._load_shortforms()
        self._load_contractions()
        self.closed_affixes = (
            set(self.segmenter.inflectional_suffixes)
            | set(self.segmenter.derivational_suffixes)
            | {"s", "'s"}
        )
        self.lexicon_prefixes = set(self.segmenter.prefixes)
        self._build_token_pattern()

    def _load_spell(self):
        spell_path = self._find_file("en_spell.json")
        with open(spell_path, "r", encoding="utf-8") as f:
            spell_data = json.load(f)

        self.spelling = {}
        for key, item in spell_data["single_letter"]["items"].items():
            item_key = item.get("char") or item.get("word") or item.get("letter") or key
            self.spelling[item_key] = item["unicode"]
        self.rev_spelling = {braille: letter for letter, braille in self.spelling.items()}

        items = spell_data["alphabetic_wordsign"]["items"]
        self.wordsign_rule = spell_data["alphabetic_wordsign"].get("rule") or {}
        self.wordsigns = {key: item["unicode"] for key, item in items.items()}
        self.word_to_wordsign = {item["word"].lower(): item["unicode"] for item in items.values()}
        self.braille_to_wordsign = {item["unicode"]: item["word"].lower() for item in items.values()}

        isolated = spell_data.get("isolated_letter") or {}
        isolated_rule = isolated.get("rule") or {}
        self.letter_grade1_indicator = isolated_rule.get("grade1IndicatorUnicode") or ""
        self.isolated_letters = {}
        self.isolated_braille_to_letter = {}
        for key, item in (isolated.get("items") or {}).items():
            letter = (item.get("word") or key).lower()
            self.isolated_letters[letter] = item
            braille = item.get("unicode")
            if braille and item.get("requiresGrade1"):
                self.isolated_braille_to_letter[braille] = letter
        self.isolated_prefixes = sorted(
            self.isolated_braille_to_letter.items(),
            key=lambda pair: -len(pair[0]),
        )

    def _load_digits(self):
        """숫자 칸은 numbers.json이 기준이다. 같은 칸의 알파벳은 철자표와 맞아야 한다."""
        with open(self._find_file("numbers.json"), "r", encoding="utf-8") as f:
            number_glyphs = json.load(f)
        self.digits = {}
        self.rev_digits = {}
        for digit, item in number_glyphs["digits"].items():
            braille = item["unicode"]
            self.digits[str(digit)] = braille
            self.rev_digits[braille] = str(digit)
            homoglyph = (item.get("homoglyph_letter") or "").lower()
            if homoglyph and self.spelling.get(homoglyph) != braille:
                raise ValueError(
                    f"숫자 {digit}의 점자 {braille!r}가 철자 {homoglyph!r}"
                    f"({self.spelling.get(homoglyph)!r})와 다릅니다."
                )

    def _load_number_rules(self):
        with open(self._find_file("ueb_number_rules.json"), "r", encoding="utf-8") as f:
            num_data = json.load(f)

        transition = num_data["collision_resolutions"]["alphanumeric_transition"]
        self.num_prefix = num_data["initiator_condition"]["braille"]
        self.grade1_prefix = transition["grade1_indicator"]
        self.grade1_letters = {char.lower() for char in transition.get("grade1_required_targets", [])}
        self.grade1_cells = {self.spelling[letter] for letter in self.grade1_letters if letter in self.spelling}

        self.connectors = {}
        for conn in num_data.get("scope_maintenance", {}).get("continuation_connectors", []):
            self.connectors[conn["char"]] = conn["braille"]
        self.terminating_connectors = {}
        for conn in num_data.get("scope_maintenance", {}).get("terminating_connectors", []):
            self.terminating_connectors[conn["char"]] = conn["braille"]

        self.numeric_sequences = []
        for char, braille in self.terminating_connectors.items():
            self.numeric_sequences.append((braille, char, True))
        for char, braille in self.connectors.items():
            self.numeric_sequences.append((braille, char, False))
        self.numeric_sequences.sort(key=lambda item: (-len(item[0]), item[2]))

        self.rev_symbol_senses = {}
        for char, braille in self.connectors.items():
            self._add_symbol_sense(braille, char, "numeric")
        for char, braille in self.terminating_connectors.items():
            self._add_symbol_sense(braille, char, "numeric_terminating")

        self.punctuation = {}
        self.surrounding_allowed_symbols = set()
        self.disallowed_delimiters = set()
        adjacent = num_data.get("standing_alone_rules", {}).get("adjacent_delimiters", {})
        # UEB 2.6.1: 빈칸처럼 "단독"의 경계가 되는 붙임표·줄표
        self.standing_alone_delimiters = {
            sym.get("char", "")
            for sym in (adjacent.get("hyphen_and_dashes") or {}).get("symbols", [])
            if sym.get("char")
        }
        for group in adjacent.values():
            if not isinstance(group, dict):
                continue
            chars = set()
            for sym in group.get("symbols", []):
                char = sym.get("char", "")
                braille = sym.get("braille", "")
                for piece in char:
                    chars.add(piece)
                if not char or char.isspace():
                    continue
                context = (
                    "numeric_or_punctuation"
                    if char in self.connectors or char in self.terminating_connectors
                    else "punctuation"
                )
                self._add_symbol_sense(braille, char, context)
                self.punctuation[char] = braille
            if group.get("allows_contraction"):
                self.surrounding_allowed_symbols.update(chars)
            elif "allows_contraction" in group:
                self.disallowed_delimiters.update(chars)
        for char, braille in self.terminating_connectors.items():
            if char and not char.isspace():
                self.punctuation.setdefault(char, braille)

        self.punctuation_sequences = sorted(
            ((braille, char) for char, braille in self.punctuation.items() if braille),
            key=lambda item: (-len(item[0]), item[1]),
        )
        self.grade1_quote_chars = {
            char for char, braille in self.punctuation.items()
            if char in "‘’" and braille
        }
        # 단독 따옴표 표기(UEB 7.6.8 두 칸 큰따옴표, 7.6.10 1급 점자표 + 작은따옴표)도 되돌리기에서 읽는다.
        standalone_quotes = [(braille, char) for char, braille in self.TWO_CELL_DOUBLE_QUOTES.items()]
        if self.letter_grade1_indicator:
            standalone_quotes += [
                (self.letter_grade1_indicator + self.punctuation[char], char)
                for char in self.grade1_quote_chars
            ]
        self.standalone_quote_decode = dict(standalone_quotes)
        self.punctuation_sequences = sorted(
            set(self.punctuation_sequences) | set(standalone_quotes),
            key=lambda item: (-len(item[0]), item[1]),
        )
        # 같은 점형이면 낱말 앞에서는 여는 부호를 먼저 고른다 (⠦: “ / ?).
        self.leading_punctuation_sequences = sorted(
            self.punctuation_sequences,
            key=lambda item: (-len(item[0]), item[1] not in self.OPENING_MARKS, item[1]),
        )

        self.apostrophe_word_suffixes = set()
        self.apostrophe_suffix_bodies = []
        for rule in (adjacent.get("apostrophe_exceptions") or {}).get("rules", []):
            pattern = rule.get("pattern", "")
            if not pattern.startswith("word") or not rule.get("allows_contraction"):
                continue
            for suffix in self._suffixes_from_pattern(pattern):
                self.apostrophe_word_suffixes.add(suffix)
                if suffix.startswith("'"):
                    self.apostrophe_suffix_bodies.append(suffix[1:])
        self.apostrophe_suffix_bodies = sorted(set(self.apostrophe_suffix_bodies), key=len, reverse=True)

    def _suffixes_from_pattern(self, pattern: str) -> List[str]:
        body = pattern.split("+", 1)[1].strip() if "+" in pattern else pattern.strip()
        return [part.strip().replace("’", "'") for part in body.split("|") if part.strip()]

    def _build_token_pattern(self):
        bodies = "|".join(re.escape(body) for body in self.apostrophe_suffix_bodies)
        apostrophe = rf"(?:['’](?:{bodies}))?" if bodies else ""
        self._token_re = re.compile(
            rf"[0-9]+|[a-zA-Z]+{apostrophe}|['’][a-zA-Z]+|[^\w\s]|_|\s"
        )

    def _load_shortforms(self):
        self.shortforms_standalone = {}
        self.shortforms_inflected = {}
        self.shortforms_compound = {}
        self.rev_shortforms = {}
        self.shortform_index = {}
        self.shortform_root_chars = {}
        self.shortform_letters = {}
        self.shortform_list = {}
        self.shortform_list_no_s = set()
        list_path = self._find_file("en_shortform_list.json")
        if os.path.exists(list_path):
            with open(list_path, "r", encoding="utf-8") as f:
                list_data = json.load(f)
            # 낱말 → 그 낱말에 쓰는 축어들 (UEB 부록 1)
            for sf_word, words in list_data.get("words", {}).items():
                for listed in words:
                    self.shortform_list.setdefault(listed, []).append(sf_word)
            self.shortform_list_no_s = set(list_data.get("noS", []))

        sf_path = self._find_file("en_shortform.json")
        if not os.path.exists(sf_path):
            return
        with open(sf_path, "r", encoding="utf-8") as f:
            sf_data = json.load(f)

        buckets = {
            "shortform_standalone_only": self.shortforms_standalone,
            "shortform_inflected": self.shortforms_inflected,
            "shortform_compound_allowed": self.shortforms_compound,
        }
        for section_name, bucket in buckets.items():
            section = sf_data.get(section_name) or {}
            section_rule = section.get("rule") or {}
            for key, item in (section.get("items") or {}).items():
                word = item["word"].lower()
                self.shortform_letters[word] = key.lower()
                specified = "allowedSuffixes" in item
                suffixes = item.get("allowedSuffixes", section_rule.get("allowedSuffixes", []))
                bucket[word] = item["unicode"]
                if section_name == "shortform_inflected":
                    bucket[word] = {"unicode": item["unicode"], "suffixes": list(suffixes)}
                self.rev_shortforms[item["unicode"]] = word
                self.shortform_index[word] = {
                    "word": word,
                    "unicode": item["unicode"],
                    "rule": section_rule,
                    "allowedSuffixes": set(suffixes),
                    "suffixesSpecified": specified,
                }
                if item.get("rootChars"):
                    self.shortform_root_chars[word] = list(item["rootChars"])

    def _resolve_root_glyph(self, root: str) -> Dict[str, str]:
        """강세 약어(ch, the) 또는 철자표의 한 글자(d, c)를 점형으로 찾는다."""
        item = self.contraction_items.get(root)
        if item and item.get("unicode"):
            return item
        letter = self.spelling.get(root) or self.spelling.get(root.lower())
        if letter:
            return {"unicode": letter, "word": root.lower()}
        raise ValueError(
            f"rootChar {root!r}가 en_contractions.json 또는 en_spell.json에 없습니다."
        )

    def _load_contractions(self):
        self.groupsigns = []
        self.standalone_contractions = {}
        self.contraction_rules = {}
        self.rev_groupsign_senses = {}
        self.contraction_items = {}
        self.groupsign_cells = set()
        self.ambiguous_medial_cells = set()

        c_path = self._find_file("en_contractions.json")
        if not os.path.exists(c_path):
            return
        with open(c_path, "r", encoding="utf-8") as f:
            c_data = json.load(f)

        for group in c_data.get("groups", []):
            priority = group.get("priority", 50)
            rule = group.get("rule", {})
            for text_val, item in group.get("items", {}).items():
                self.contraction_items[text_val] = item
                self.contraction_rules[text_val] = rule
                if not rule.get("standingAloneOnly"):
                    self.groupsigns.append((text_val, item["unicode"], priority, rule))
                self.rev_groupsign_senses.setdefault(item["unicode"], []).append({
                    "text": text_val,
                    "rule": rule,
                    "priority": priority,
                    "unicode": item["unicode"],
                    "rootChar": item.get("rootChar"),
                })
                if rule.get("canStandAlone"):
                    self.standalone_contractions[text_val] = item["unicode"]

        for senses in self.rev_groupsign_senses.values():
            for sense in senses:
                root = sense.get("rootChar")
                if not root:
                    continue
                root_item = self._resolve_root_glyph(root)
                if root_item["unicode"] not in sense["unicode"]:
                    raise ValueError(
                        f"{sense['text']}의 점자 {sense['unicode']!r}에 "
                        f"강세 약어 {root}({root_item['unicode']})가 없습니다."
                    )
                sense["rootEntry"] = root_item
                sense["rootUnicode"] = root_item["unicode"]

        for word, roots in self.shortform_root_chars.items():
            uni = self.shortform_index[word]["unicode"]
            for root in roots:
                root_item = self._resolve_root_glyph(root)
                if not uni.startswith(root_item["unicode"]):
                    raise ValueError(
                        f"{word}의 점자 {uni!r}가 강세 약어 {root}({root_item['unicode']})로 시작하지 않습니다."
                    )

        self.groupsigns.sort(key=lambda item: (item[2], -len(item[0])))
        self.groupsign_cells = {cell for braille in self.rev_groupsign_senses for cell in braille}
        punct_exact = {braille for braille, _char in self.punctuation_sequences}
        self.ambiguous_medial_cells = punct_exact & set(self.rev_groupsign_senses)

    def _add_symbol_sense(self, braille: str, char: str, context: str):
        if not braille:
            return
        bucket = self.rev_symbol_senses.setdefault(braille, [])
        if any(item["char"] == char and item["context"] == context for item in bucket):
            return
        bucket.append({"char": char, "context": context})

    def _spell_chars(self, text: str) -> str:
        out = []
        for char in text:
            if char in self.spelling:
                out.append(self.spelling[char])
            elif char in self.punctuation:
                out.append(self.punctuation[char])
            else:
                out.append(char)
        return "".join(out)

    def _is_apostrophe_suffix(self, token: str) -> bool:
        return token.replace("’", "'").lower() in self.apostrophe_word_suffixes

    def _token_stands_alone(self, tokens: List[str], index: int) -> bool:
        return self._side_stands_alone(tokens, index, -1) and self._side_stands_alone(tokens, index, 1)

    def _side_stands_alone(self, tokens: List[str], index: int, step: int) -> bool:
        """UEB 2.6.1~2.6.3: 부호를 건너 빈칸·붙임표·줄표·글 끝에 닿아야 단독이다.
        A.B.나 e.g.처럼 마침표 너머에 글자가 이어지면 단독이 아니다."""
        neighbor = index + step
        while 0 <= neighbor < len(tokens):
            token = tokens[neighbor]
            if token.isspace():
                return True
            if step > 0 and self._is_apostrophe_suffix(token):
                return True
            if token in self.standing_alone_delimiters:
                return True
            if token in self.disallowed_delimiters:
                return False
            if token in self.surrounding_allowed_symbols:
                neighbor += step
                continue
            return False
        return True

    def _touches_lower_punctuation(self, tokens: List[str], index: int) -> bool:
        """UEB 10.5.1: 낱말에 붙은 부호 중 아래 점(2·3·5·6점)만 쓰는 것이 있는가. 따옴표는 모두 아래 점으로 본다."""
        for step in (-1, 1):
            neighbor = index + step
            while 0 <= neighbor < len(tokens):
                token = tokens[neighbor]
                if token.isspace() or any(char.isalnum() for char in token):
                    break
                if token in "“”‘’'\"":
                    return True
                braille = self.punctuation.get(token, "")
                if braille and all(
                    "\u2800" <= cell <= "\u28ff" and not (ord(cell) - 0x2800) & self.UPPER_DOTS
                    for cell in braille
                ):
                    return True
                neighbor += step
        return False

    def _continuation_reaches_digit(self, tokens: List[str], start: int) -> bool:
        """쉼표·소수점·쌍점·분수선은 바로 뒤 숫자까지, 숫자 빈칸은 다음 숫자만 모드를 유지한다."""
        index = start
        while index < len(tokens):
            token = tokens[index]
            if token.isdigit():
                return True
            if token.isspace() or token not in self.connectors:
                return False
            index += 1
        return False

    def text_to_braille(self, text: str) -> str:
        # 곧은 큰따옴표(")는 놓인 자리로 여는·닫는 따옴표를 가린다 (UEB 예시 "Belinda!" ⠦⠠⠆⠇⠔⠙⠁⠖⠴).
        text = re.sub(r'(^|(?<=[\s(\[{]))"', "“", text).replace('"', "”")
        tokens = self._token_re.findall(text)
        two_cell_quotes = self._two_cell_quote_indexes(tokens)
        result = []
        in_numeric_mode = False
        cap_letter = self.CAP_LETTER
        cap_word = self.CAP_WORD

        for index, token in enumerate(tokens):
            if not token:
                continue

            if token.isdigit():
                prefix = "" if in_numeric_mode else self.num_prefix
                in_numeric_mode = True
                result.append(prefix + "".join(self.digits[digit] for digit in token))
                continue

            if in_numeric_mode and token in self.connectors:
                if self._continuation_reaches_digit(tokens, index + 1):
                    result.append(self.connectors[token])
                    continue
                in_numeric_mode = False
                if token.isspace():
                    result.append(token)
                else:
                    result.append(self.punctuation.get(token, self.connectors[token]))
                    # UEB 6.5.2 (4.b ⠼⠙⠲⠰⠃): 마침표 등에 글자가 바로 붙으면 숫자 모드가 이어진다.
                    following = tokens[index + 1] if index + 1 < len(tokens) else ""
                    if following[:1].isalpha():
                        in_numeric_mode = True
                continue

            if in_numeric_mode and token in self.terminating_connectors:
                result.append(self.terminating_connectors[token])
                in_numeric_mode = False
                continue

            if re.match(r"^[A-Za-z]+(?:['’][A-Za-z]+)?$", token) and self._has_interior_capital(token):
                in_numeric_mode = False
                self._word_beginning = self._at_word_beginning(tokens, index)
                result.append(self._translate_mixed_case(token, standing=self._token_stands_alone(tokens, index)))
                self._word_beginning = True
                continue

            if re.match(r"^[A-Za-z]+(?:['’][A-Za-z]+)?$", token):
                came_from_numeric = in_numeric_mode
                in_numeric_mode = False
                cap_indicator = ""
                if token.isupper() and len(token) > 1:
                    cap_indicator = cap_word
                elif token[0].isupper():
                    cap_indicator = cap_letter
                lower = token.lower().replace("’", "'")
                standing = self._token_stands_alone(tokens, index)
                self._word_beginning = self._at_word_beginning(tokens, index)
                apostrophe = re.match(r"^([a-z]+)('[a-z]+)$", lower)
                if apostrophe and apostrophe.group(2) in self.apostrophe_word_suffixes:
                    stem, suffix = apostrophe.groups()
                    braille_word = self._translate_word(stem, standing_alone=standing) + self._spell_chars(suffix)
                else:
                    braille_word = self._translate_word(lower, standing_alone=standing)
                    if lower in self.LOWER_WORDSIGN_WORDS and self._touches_lower_punctuation(tokens, index):
                        braille_word = self._contract_surface(lower, whole_word=True, standing_alone=False)
                if came_from_numeric and (
                    braille_word.startswith(self.grade1_prefix)
                    or self._leading_numeric_continuation(braille_word)
                ):
                    braille_word = self._contract_surface(
                        lower,
                        whole_word=True,
                        standing_alone=standing,
                        avoid_numeric_prefix=True,
                        avoid_grade1_prefix=True,
                    )
                prefix_indicator = ""
                if came_from_numeric and not cap_indicator and braille_word and braille_word[0] in self.grade1_cells:
                    prefix_indicator = self.grade1_prefix
                elif standing and not came_from_numeric:
                    prefix_indicator, braille_word = self._avoid_shortform_reading(lower, braille_word)
                if (
                    cap_indicator
                    and lower in self.isolated_letters
                    and self.letter_grade1_indicator
                    and braille_word.startswith(self.letter_grade1_indicator)
                ):
                    # UEB 5.2 (J. ⠰⠠⠚⠲): 1급 점자표가 대문자 표시보다 앞에 온다.
                    prefix_indicator = self.letter_grade1_indicator
                    braille_word = braille_word[len(self.letter_grade1_indicator):]
                result.append(prefix_indicator + cap_indicator + braille_word)
                self._word_beginning = True
                continue

            if re.fullmatch(r"['’][A-Za-z]+", token):
                in_numeric_mode = False
                lower = token.lower().replace("’", "'")
                previous = tokens[index - 1] if index else ""
                if previous[-1:].isalpha():
                    # UEB 10.6.2 (dis'armony ⠙⠊⠎⠄⠜⠍⠕⠝⠽): 낱말 안 아포스트로피 뒤에도 약자를 쓰되 낱말 처음은 아니다.
                    self._word_beginning = False
                    if token[1:].islower():
                        word = self._contract_surface(lower[1:], whole_word=True, standing_alone=False)
                    else:
                        word = self._translate_mixed_case(token[1:], first=False, standing=False)  # O'Connor ⠠⠕⠄⠠⠉⠕⠝⠝⠕⠗
                else:
                    # UEB 10.6.2 ('display ⠄⠲⠏⠇⠁⠽): 여는 작은따옴표 뒤는 낱말 처음이다.
                    self._word_beginning = self._at_word_beginning(tokens, index)
                    word = self._translate_word(lower[1:], standing_alone=self._token_stands_alone(tokens, index))
                self._word_beginning = True
                result.append(self._spell_chars(lower[0]) + word)
                continue

            in_numeric_mode = False
            if index in two_cell_quotes:
                result.append(self.TWO_CELL_DOUBLE_QUOTES[token])
                continue
            braille = self.punctuation.get(token, token)
            if token in self.grade1_quote_chars and self._token_stands_alone(tokens, index):
                # UEB 7.6.10: 홀로 놓인 ⠠⠦·⠠⠴는 His·Was로 읽히므로 1급 점자표를 붙인다.
                braille = self.letter_grade1_indicator + braille
            result.append(braille)

        return "".join(result)

    def _two_cell_quote_indexes(self, tokens: List[str]) -> set:
        """UEB 7.6.8: 홀로 놓인 큰따옴표와 그 짝은 두 칸 따옴표(⠘⠦ ⠘⠴)로 적는다."""
        pairs = {}
        opened = []
        for index, token in enumerate(tokens):
            if token == "“":
                opened.append(index)
            elif token == "”" and opened:
                start = opened.pop()
                pairs[start] = index
                pairs[index] = start
        marked = set()
        for index, token in enumerate(tokens):
            if token not in self.TWO_CELL_DOUBLE_QUOTES or not self._token_stands_alone(tokens, index):
                continue
            marked.add(index)
            if index in pairs:
                marked.add(pairs[index])
        return marked

    def _has_interior_capital(self, token: str) -> bool:
        return bool(re.search(r"[a-z]['’]?[A-Z]|[A-Z]['’]?[A-Z]+['’]?[a-z]|[A-Z]['’][A-Z]", token))

    def _translate_mixed_case(self, token: str, first: bool = True, standing: bool = True) -> str:
        """UEB 10.12.12: 낱말 안 대문자 표시가 있어도 기본 약자 규칙을 따른다. 대문자 표시 뒤에서는
        be·con·dis(10.6.3)·ea 등(10.6.6)·어미 약자(10.8.2)를 쓰지 않고, 축어는 10.9.3 조건일 때만 쓴다(10.9.4)."""
        token = token.replace("’", "'")
        parts = []
        for part in re.findall(r"[A-Z]+|[a-z]+|'", token):
            if part.isupper() and len(part) == 2 and token.find(part) + 2 < len(token) and token[token.find(part) + 2].islower():
                parts.extend([part[0], part[1]])
            else:
                parts.append(part)
        segments = []
        for part in parts:
            if part.islower() and segments and len(segments[-1]) == 1 and segments[-1].isupper():
                # 대문자 한 글자 뒤 소문자는 같은 덩이 (Connell, Ed). 두 글자 대문자 뒤 소문자면 첫 글자만 뗀다
                # (ELesson ⠠⠑⠠⠇⠑⠎⠎⠕⠝, BEd ⠠⠃⠠⠫). 세 글자 이상이면 대문자 단어+종료표 (TEAspoon ⠠⠠⠞⠑⠁⠠⠄⠎⠏⠕⠕⠝).
                segments[-1] += part
                continue
            segments.append(part)
        # UEB 10.9.4(a): 대문자 표시까지 똑같이 목록에 올라 있어야 한다 (DeafBlind).
        listed = self._listed_shortforms(token)
        out = []
        for number, segment in enumerate(segments):
            if segment == "'":
                out.append(self._spell_chars("'"))
                first = False
                continue
            lower = segment.lower()
            following = "".join(segments[number + 1:]).replace("'", "")
            next_letter = following[:1].lower()
            if segment.isupper() and len(segment) > 1:
                cap = self.CAP_WORD
            elif segment[0].isupper():
                cap = self.CAP_LETTER
            else:
                cap = ""
            word_beginning = self._word_beginning
            if not first:
                self._word_beginning = False
            body = self._mixed_case_shortform(lower, first, next_letter, listed) if standing else None
            if body is None:
                body = self._contract_surface(lower, whole_word=True, standing_alone=False)
            self._word_beginning = word_beginning
            out.append(cap + body)
            if cap == self.CAP_WORD and following[:1].islower():
                out.append(self.CAP_WORD_TERMINATOR)
            first = False
        return "".join(out)

    def _mixed_case_shortform(self, word: str, first: bool, next_letter: str, listed: set = frozenset()) -> Optional[str]:
        """UEB 10.9.4: 대문자가 섞인 낱말에서는 목록에 오른 낱말(DeafBlind)이거나 10.9.3 조건을 갖춘 축어만 쓴다
        (QuickTime ⠠⠟⠅⠠⠐⠞)."""
        data = self.shortform_index.get(word)
        if not data:
            return None
        if word in listed:
            return data["unicode"]
        if word in self.SHORTFORM_ANYWHERE:
            return data["unicode"]
        if next_letter in self.VOWELS_Y:
            return None
        if word in self.SHORTFORM_ANYWHERE_BEFORE_CONSONANT or (word in self.SHORTFORM_WORD_START and first):
            return data["unicode"]
        return None

    def _avoid_shortform_reading(self, word: str, braille: str) -> Tuple[str, str]:
        """축어가 아닌 글자 묶음이 축어로 읽히지 않게 한다. (1급 표시, 고친 점자)를 돌려준다.
        UEB 10.9.6: 묶음 약자 때문에 축어와 같아지면 그 약자를 쓰지 않고 글자로 적는다 (mst, shd).
        UEB 10.9.7·5.7.2: 홀로 쓰인 글자 묶음이 축어와 같으면 앞에 1급 점자표 ⠰ (al, hm, CD).
        UEB 10.9.8: 낱말 맨 앞이 축어를 품은 낱말로 읽히면 앞에 ⠰ (Blvd, LLC).
        UEB 10.9.9: 낱말 중간이 축어로 읽히면 앞에 1급 단어표 ⠰⠰를 적고 약자를 쓰지 않는다 (ozbrl)."""
        stem, tail = word, ""
        apostrophe = re.match(r"^([a-z]+)('[a-z]+)$", word)
        if apostrophe and apostrophe.group(2) in self.apostrophe_word_suffixes:
            stem, tail = apostrophe.groups()
        if not stem.isalpha() or stem in self.shortform_index:
            return "", braille
        tail_braille = self._spell_chars(tail)
        if tail and not braille.endswith(tail_braille):
            return "", braille
        core = braille[: len(braille) - len(tail_braille)]
        letters = self._spell_chars(stem)

        def reads_as_shortform(cells: str) -> bool:
            if cells in self.rev_shortforms:
                return True
            # UEB 10.9.8: 목록 낱말 등 축어를 품은 낱말로 읽히는가 (UNSD를 unsaid로)
            composed = self._decode_composed_shortform(cells)
            if composed is not None and composed != stem and any(
                cells.startswith(data["unicode"]) and composed.startswith(sf_word)
                for sf_word, data in self.shortform_index.items()
            ):
                return True
            # UEB 10.9.5: 축어 + s (abouts, almosts, hims는 빼고)
            base = cells[:-1]
            return (
                cells.endswith(self.spelling.get("s", "\0"))
                and base in self.rev_shortforms
                and self.rev_shortforms[base] not in self.SHORTFORM_NO_S
                and stem != self.rev_shortforms[base] + "s"
            )

        if reads_as_shortform(core):
            if core != letters and not reads_as_shortform(letters):
                return "", letters + tail_braille
            return self.grade1_prefix, letters + tail_braille
        for sf_word in self.SHORTFORM_WORD_START + self.SHORTFORM_ANYWHERE + self.SHORTFORM_ANYWHERE_BEFORE_CONSONANT:
            abbr = self.shortform_letters.get(sf_word)
            data = self.shortform_index.get(sf_word)
            if not abbr or not data or sf_word in stem:
                continue
            needs_consonant = sf_word not in self.SHORTFORM_ANYWHERE
            if core.startswith(data["unicode"]) and stem.startswith(abbr):
                following = stem[len(abbr):len(abbr) + 1]
                if following and not (needs_consonant and following in self.VOWELS_Y):
                    return self.grade1_prefix, braille
            if sf_word in self.SHORTFORM_WORD_START:
                continue
            index = stem.find(abbr, 1)
            while index > 0:
                following = stem[index + len(abbr):index + len(abbr) + 1]
                if data["unicode"] in core and not (needs_consonant and following in self.VOWELS_Y):
                    return self.grade1_prefix * 2, letters + tail_braille
                index = stem.find(abbr, index + 1)
        composed = self._decode_composed_shortform(core)
        if composed is not None and composed != stem:
            # UEB 10.9.9 (UNSD ⠰⠰⠠⠠⠥⠝⠎⠙): 낱말 중간이 목록 낱말의 축어로 읽히면 ⠰⠰ + 글자
            return self.grade1_prefix * 2, letters + tail_braille
        return "", braille

    def _translate_word(self, word: str, standing_alone: bool = True) -> str:
        if (
            standing_alone
            and len(word) == 1
            and word in self.isolated_letters
        ):
            return self.isolated_letters[word]["unicode"]

        if standing_alone and not self._wordsign_blocked(word) and word in self.word_to_wordsign:
            return self.word_to_wordsign[word]

        rule = self.contraction_rules.get(word) or {}
        if (
            word in self.standalone_contractions
            and not (rule.get("standingAloneOnly") and not standing_alone)
            and not (rule.get("requiresFollowingLetters") and not standing_alone)
        ):
            return self.standalone_contractions[word]

        if standing_alone:
            shortform = self._render_shortform(word)
            if shortform is not None:
                return shortform

        return self._contract_surface(word, whole_word=True, standing_alone=standing_alone)

    def _wordsign_blocked(self, word: str) -> bool:
        """en_spell.json은 알파벳 단어약어 뒤에 일반 접미를 붙이지 않는다. 's만 예외다."""
        if self.wordsign_rule.get("allowSuffix", True):
            return False
        for base in sorted(self.word_to_wordsign, key=len, reverse=True):
            if word.startswith(base) and len(word) > len(base):
                suffix = word[len(base):]
                if suffix == "'s" and self.wordsign_rule.get("allowApostropheS"):
                    return False
                return True
        return False

    def _render_shortform(self, word: str) -> Optional[str]:
        """UEB 10.9.2: 축어는 그 낱말, s·'s를 붙인 꼴(10.9.5), 부록 1 목록 낱말, 10.9.3 조건에 맞는 낱말에만 쓴다."""
        exact = self.shortform_index.get(word)
        if exact:
            return exact["unicode"]
        for suffix in ("'s", "s"):
            stem = word[: -len(suffix)]
            if word.endswith(suffix) and stem in self.shortform_index and stem not in self.SHORTFORM_NO_S:
                return self.shortform_index[stem]["unicode"] + self._spell_chars(suffix)
        return self._compose_shortforms(word, self._listed_shortforms(word))

    def _listed_shortforms(self, word: str) -> set:
        """부록 1 목록에서 이 낱말(또는 s·'s를 뗀 꼴)이 오른 축어들."""
        found = set(self.shortform_list.get(word, ()))
        for suffix in ("'s", "s"):
            if word.endswith(suffix) and word not in self.shortform_list_no_s:
                found |= set(self.shortform_list.get(word[: -len(suffix)], ()))
        return found

    def _shortform_10_9_3_ok(self, sf_word: str, word: str, index: int) -> bool:
        """UEB 10.9.3: 목록에 없는 낱말에서 쓸 수 있는 열 축어의 조건."""
        if sf_word in self.SHORTFORM_ANYWHERE:
            return True
        following = word[index + len(sf_word): index + len(sf_word) + 1]
        if following in self.VOWELS_Y and following:
            return False
        if sf_word in self.SHORTFORM_ANYWHERE_BEFORE_CONSONANT:
            return True
        return sf_word in self.SHORTFORM_WORD_START and index == 0

    def _compose_shortforms(self, word: str, listed: set) -> Optional[str]:
        out, plain, index, used = [], "", 0, False
        candidates = sorted(listed | set(self.SHORTFORM_10_9_3), key=len, reverse=True)
        while index < len(word):
            for sf_word in candidates:
                if not word.startswith(sf_word, index):
                    continue
                if sf_word not in listed and not self._shortform_10_9_3_ok(sf_word, word, index):
                    continue
                if plain:
                    # 축어 앞 글자: 낱말 처음이면 be·con·dis를 쓸 수 있다 (belittle ⠆⠇⠇).
                    out.append(self._contract_surface(plain, whole_word=not out, more_follows=True))
                    plain = ""
                out.append(self.shortform_index[sf_word]["unicode"])
                index += len(sf_word)
                used = True
                break
            else:
                plain += word[index]
                index += 1
        if not used:
            return None
        if plain:
            out.append(self._contract_surface(plain, whole_word=False))
        return "".join(out)

    def _shortform_parts_ok(self, head: str, tail: str, data: Dict) -> bool:
        if not head and not tail:
            return False
        rule = data["rule"]
        if head and (head not in self.lexicon_prefixes or not rule.get("allowPrefix")):
            return False
        if tail and not self._shortform_suffix_ok(tail, data):
            return False
        return True

    def _shortform_suffix_ok(self, suffix: str, data: Dict, allow_open_compound: bool = True) -> bool:
        rule = data["rule"]
        allowed = data["allowedSuffixes"]
        specified = data["suffixesSpecified"]
        if suffix in {"'s", "’s"}:
            suffix = "'s"
            return bool(rule.get("allowApostropheS")) and (not specified or suffix in allowed)
        if suffix == "s" and not rule.get("allowPluralS", False):
            return False
        if suffix in allowed and (rule.get("allowSuffix") or specified):
            return True
        if allow_open_compound and rule.get("allowCompound") and suffix and suffix not in self.closed_affixes:
            # UEB 10.9.3 (b)(c): 목록에 없는 긴 낱말에서는 뒤에 모음·y가 오면 축어로 쓰지 않는다
            # (blunder는 blind+under가 아니다). braille·great는 어디서나 쓴다.
            sf_word = data.get("word", "")
            if sf_word not in self.SHORTFORM_ANYWHERE and suffix[0] in self.VOWELS_Y:
                return False
            return True
        return False

    def _surface_boundaries(self, word: str) -> set:
        if not self.segmenter.disallow_bridge:
            return set()
        parts = self.segmenter.segment_word(word)
        if len(parts) <= 1 or "".join(parts) != word:
            return set()
        bounds = set()
        cursor = 0
        for part in parts[:-1]:
            cursor += len(part)
            bounds.add(cursor)
        return bounds

    def _contract_surface(
        self,
        text: str,
        whole_word: bool,
        standing_alone: bool = True,
        avoid_numeric_prefix: bool = False,
        avoid_grade1_prefix: bool = False,
        more_follows: bool = False,
    ) -> str:
        """왼쪽부터 가장 긴 유효 약어를 고른다. 길이가 같으면 priority가 작은 쪽을 쓴다.
        more_follows: 뒤에 축어가 이어진다 (belittle ⠆⠇⠇의 be)."""
        if not text:
            return ""
        boundaries = self._surface_boundaries(text) if whole_word else set()
        out = []
        index = 0
        while index < len(text):
            best = None
            for pattern, braille, priority, rule in self.groupsigns:
                if not pattern or not text.startswith(pattern, index):
                    continue
                end = index + len(pattern)
                if avoid_numeric_prefix and index == 0 and self._leading_numeric_continuation(braille):
                    continue
                if avoid_grade1_prefix and index == 0 and braille.startswith(self.grade1_prefix):
                    continue
                if not self._print_span_ok(
                    text, index, end, rule, whole_word, boundaries, standing_alone, more_follows
                ):
                    continue
                rank = (len(pattern), -priority)
                if best is None or rank > best[0]:
                    best = (rank, braille, end)
            if best:
                out.append(best[1])
                index = best[2]
                continue
            out.append(self._spell_chars(text[index]))
            index += 1
        return "".join(out)

    def _print_span_ok(
        self,
        text: str,
        start: int,
        end: int,
        rule: dict,
        whole_word: bool,
        boundaries: set,
        standing_alone: bool = True,
        more_follows: bool = False,
    ) -> bool:
        if any(start < bound < end for bound in boundaries):
            return False
        at_start = start == 0
        at_end = end == len(text) and not more_follows
        whole = at_start and at_end
        if rule.get("avoidWhenStandingAlone") and whole and standing_alone:
            return False
        if rule.get("standingAloneOnly"):
            return False
        if whole and whole_word and standing_alone and not rule.get("canStandAlone", False):
            return False
        if rule.get("requiresSurroundingLetters") and not (start > 0 and end < len(text)):
            return False
        if not rule.get("canFollowLetters", True) and not at_start:
            return False
        if rule.get("requiresFollowingLetters") and at_end:
            return False
        if at_start and whole_word and text[start:end] in self.WORD_BEGINNING_SIGNS:
            # UEB 10.4.3: ing는 낱말 처음에 쓰지 않는다.
            if text[start:end] == "ing" and self._word_beginning:
                return False
            # UEB 10.6.2: be·con·dis는 낱말 처음(빈칸·붙임표·대시 뒤)에서, 뒤에 글자가 올 때만 쓴다.
            if text[start:end] != "ing" and (
                not self._word_beginning
                or (end < len(text) and not text[end].isalpha())
                or (not more_follows and not self._prefix_is_first_syllable(text, end))
            ):
                return False
        if rule.get("requiresPrecedingLetters") and at_start and whole_word:
            # UEB 10.8.1: 어미 약자는 앞에 글자가 있을 때만 쓴다 (낱말 맨 앞의 ⠰는 1급 점자표).
            return False
        if not rule.get("canPrecedeLetters", True) and not at_end:
            return False
        return True

    def _prefix_is_first_syllable(self, text: str, end: int) -> bool:
        """UEB 10.6.1: be·con·dis가 첫 음절일 때만 쓴다. 철자로 확실히 가려지는 경우만 본다."""
        prefix, rest = text[:end], text[end:]
        if text in self.PREFIX_ABBREVIATIONS:
            return True  # UEB 10.6.4: cont(continued)·dist(district)처럼 원래 낱말에 약자를 쓰는 줄임말
        if rest and not any(char in self.VOWELS_Y for char in rest):
            return False  # best ⠃⠑⠌, conch ⠉⠕⠝⠡, disc ⠙⠊⠎⠉: 한 음절 낱말
        if prefix == "be" and rest[:1] == "e":
            return False  # been ⠃⠑⠢
        if prefix == "be" and len(rest) > 1 and rest[0] == rest[1] and rest[0] not in self.VOWELS_Y:
            return False  # better ⠃⠑⠞⠞⠻, belligerent ⠃⠑⠇⠇⠊⠛⠻⠢⠞, begging ⠃⠑⠶⠬
        if prefix == "con" and re.fullmatch(r"e(s|d|y|ys)?", rest):
            return False  # cone ⠉⠐⠕, coneys ⠉⠐⠕⠽⠎
        if prefix == "dis" and rest[:1] == "h" and not rest.startswith(self.DIS_H_PREFIXED):
            return False  # dish ⠙⠊⠩, dishevel ⠙⠊⠩⠑⠧⠑⠇ (dishonest ⠲⠓⠐⠕⠌는 씀)
        return True

    def _at_word_beginning(self, tokens: List[str], index: int) -> bool:
        """UEB 10.4.3·10.6.2 붙임: 낱말 처음은 빈칸·붙임표·대시 뒤이며, 그 사이에 여는 문장부호만 올 수 있다."""
        before = []
        for token in reversed(tokens[:index]):
            if not token or token.isspace():
                break
            before.append(token)
        text = "".join(reversed(before)).rstrip(self.OPENING_PUNCTUATION)
        return not text or text[-1] in self.WORD_BEGINNING_BREAKS

    def _leading_numeric_continuation(self, braille: str) -> bool:
        """⠐+a~j처럼 숫자 연결자로 읽히는 앞부분은 단어 약어로 두지 않는다."""
        if not braille:
            return False
        for conn, _char, ends_mode in self.numeric_sequences:
            if ends_mode or not conn or not braille.startswith(conn):
                continue
            if self._braille_continuation_reaches_digit(braille, len(conn)):
                return True
        return False

    def _braille_continuation_reaches_digit(self, token: str, index: int) -> bool:
        while index < len(token):
            if token[index] in self.rev_digits:
                return True
            stepped = False
            for braille, _char, ends_mode in self.numeric_sequences:
                if not braille or not token.startswith(braille, index):
                    continue
                if ends_mode:
                    return False
                index += len(braille)
                stepped = True
                break
            if not stepped:
                return False
        return False

    def braille_to_text(self, braille_str: str) -> str:
        tokens = re.findall(r"[\u2800-\u28FF]+|[^\u2800-\u28FF]+", braille_str)
        result = []
        for token in tokens:
            if not token.strip() or not any("\u2800" <= char <= "\u28FF" for char in token):
                result.append(token)
                continue
            result.append(self._translate_braille_token(token))
        return "".join(result)

    def _translate_braille_token(self, b_token: str) -> str:
        if self.num_prefix in b_token:
            return self._decode_braille_with_numeric_mode(b_token)
        return self._decode_word_token(b_token)

    def _strip_capital(self, token: str) -> Tuple[str, Optional[str]]:
        grade1_cap_word = self.letter_grade1_indicator + self.CAP_WORD
        if self.letter_grade1_indicator and token.startswith(grade1_cap_word) and len(token) > len(grade1_cap_word):
            # UEB 5.8.1: ⠰⠠⠠ = 1급 점자표 + 대문자 단어표 (CD ⠰⠠⠠⠉⠙)
            return self.letter_grade1_indicator + token[len(grade1_cap_word):], "word"
        grade1_cap = self.letter_grade1_indicator + self.CAP_LETTER
        if self.letter_grade1_indicator and token.startswith(grade1_cap) and len(token) > len(grade1_cap):
            # UEB 5.2: ⠰⠠⠃ = 1급 점자표 + 대문자 B
            return self.letter_grade1_indicator + token[len(grade1_cap):], "letter"
        if token.startswith(self.CAP_WORD):
            return token[len(self.CAP_WORD):], "word"
        if token.startswith(self.CAP_LETTER):
            return token[len(self.CAP_LETTER):], "letter"
        return token, None

    def _apply_capital(self, text: str, mode: Optional[str]) -> str:
        if mode == "word":
            return text.upper()
        if mode == "letter" and text:
            return text[0].upper() + text[1:]
        return text

    def _decode_word_token(self, token: str, standing_alone: bool = True) -> str:
        if standing_alone and token in self.braille_to_wordsign:
            return self.braille_to_wordsign[token]
        if token in self.standalone_quote_decode:
            return self.standalone_quote_decode[token]
        bare, bare_cap = self._strip_capital(token)
        if standing_alone and bare_cap:
            # UEB 7.6.10·10.5.1: 홀로 놓인 ⠠⠦·⠠⠴·⠠⠆는 부호가 아니라 His·Was·Be
            for sense in self.rev_groupsign_senses.get(bare, []):
                if sense["rule"].get("standingAloneOnly") or sense["text"] in self.LOWER_WORDSIGN_WORDS:
                    return self._apply_capital(sense["text"], bare_cap)
        leading, core, trailing = self._peel_edge_punctuation(token)
        target = core or token
        target, cap_mode = self._strip_capital(target)

        def finish(text: str) -> str:
            return leading + self._apply_capital(text, cap_mode) + trailing

        hyphen = self.punctuation.get("-", "-")
        parts = target.split(hyphen)
        if len(parts) > 1 and all(len(part) > 1 for part in parts) and cap_mode != "word" and not any(
            part.endswith(self.CAP_LETTER) for part in parts[:-1]
        ):
            # 붙임표로 이은 낱말은 낱말마다 읽는다 (Marcillat-en-Combraille ⠉⠕⠍⠃⠗⠇).
            words = [self._decode_word_token(part) for part in parts]
            if not any("\u2800" <= char <= "\u28FF" for word in words for char in word):
                return leading + self._apply_capital("-".join(words), cap_mode) + trailing

        mixed = self._decode_mixed_case(target, cap_mode)
        if mixed is not None:
            return leading + mixed + trailing

        grade1 = self._decode_grade1_letters(target)
        if grade1 is not None:
            text, inner_cap = grade1
            return leading + self._apply_capital(text, cap_mode or inner_cap) + trailing

        # UEB 2.6.2 ('e 'as ⠄⠰⠑ ⠄⠵): 앞에 붙은 아포스트로피는 단독을 막지 않는다.
        glued_apostrophe = "'" in trailing
        if standing_alone and not glued_apostrophe and target in self.braille_to_wordsign:
            return finish(self.braille_to_wordsign[target])
        if standing_alone and not glued_apostrophe:
            with_suffix = self._decode_wordsign_suffix(target)
            if with_suffix is not None:
                return finish(with_suffix)
        if standing_alone:
            shortform = self._decode_shortform_token(target)
            if shortform is None:
                shortform = self._decode_prefixed_shortform(target)
            if shortform is not None and self._translate_word(shortform) != target:
                shortform = self._decode_composed_shortform(target) or shortform
            if shortform is None:
                shortform = self._decode_composed_shortform(target)
            if shortform is not None:
                return finish(shortform)
        decoded = self._decode_contracted(
            target, allow_shortform=False, standing_alone=standing_alone
        )
        apostrophe = self.punctuation.get("'", "")
        if apostrophe and apostrophe in target[1:-1] and any("\u2800" <= char <= "\u28FF" for char in decoded):
            # UEB 10.6.2 (m'lord ⠍⠄⠐⠇): 낱말 안 아포스트로피 뒤에서 다시 약자를 읽는다.
            head, *tails = target.split(apostrophe)
            parts = [self._decode_contracted(head, allow_shortform=False, standing_alone=standing_alone)]
            parts += [self._decode_contracted(tail, allow_shortform=False, standing_alone=False) for tail in tails]
            decoded = "'".join(parts)
        if core and core != token:
            return finish(decoded)
        return self._apply_capital(decoded, cap_mode)

    def _decode_mixed_case(self, target: str, cap_mode: Optional[str], allow_any_shortform: bool = True) -> Optional[str]:
        """낱말 안 대문자 표시(⠠ ⠠⠠)와 대문자 종료표(⠠⠄)로 나눠 읽는다 (McConnell, TEAspoon)."""
        cap = self.CAP_LETTER
        if self.punctuation.get("-", "-") in target:
            return None  # 붙임표로 이은 낱말은 낱말마다 따로 읽는다.
        pieces = []  # (대문자 방식, 점자)
        mode, start, index = cap_mode, 0, 0
        while index < len(target):
            if not target.startswith(cap, index):
                index += 1
                continue
            following = target[index + 1:index + 2]
            if following in ("⠤", "⠦", "⠴") or not following:
                return None
            pieces.append((mode, target[start:index]))
            if target.startswith(self.CAP_WORD_TERMINATOR, index):
                mode, index = None, index + 2
            elif target.startswith(self.CAP_WORD, index):
                mode, index = "word", index + 2
            else:
                mode, index = "letter", index + 1
            start = index
        if not pieces:
            return None
        pieces.append((mode, target[start:]))
        out = []
        for number, (mode, braille) in enumerate(pieces):
            if not braille:
                continue
            text = None
            stem, apostrophe, suffix = braille.partition(self.punctuation.get("'", "'"))
            word = self.rev_shortforms.get(stem)
            if word and (
                allow_any_shortform
                or word in self.SHORTFORM_ANYWHERE
                or word in self.SHORTFORM_ANYWHERE_BEFORE_CONSONANT
                or (word in self.SHORTFORM_WORD_START and number == 0)
            ):
                text = word + (apostrophe and "'" + self._decode_contracted(suffix, allow_shortform=False, standing_alone=False))
            if text is None:
                text = self._decode_contracted(braille, allow_shortform=False, standing_alone=False)
            if any("\u2800" <= char <= "\u28FF" for char in text):
                return None
            out.append(self._apply_capital(text, mode))
        result = "".join(out)
        if allow_any_shortform:
            # 목록 낱말(DeafBlind ⠠⠙⠂⠋⠠⠃⠇)은 다시 점역해 같을 때만 받는다.
            expected = {"word": self.CAP_WORD, "letter": self.CAP_LETTER}.get(cap_mode, "") + target
            if self._translate_mixed_case(result) != expected:
                return self._decode_mixed_case(target, cap_mode, allow_any_shortform=False)
        return result

    def _decode_grade1_letters(self, target: str) -> Optional[Tuple[str, Optional[str]]]:
        """UEB 10.9.7~10.9.9: ⠰ 뒤 글자 묶음은 축어가 아니고, ⠰⠰ 뒤는 약자 없이 글자로만 적었다."""
        g1 = self.grade1_prefix
        if not g1 or not target.startswith(g1):
            return None
        word_mode = target.startswith(g1 * 2)
        rest = target[len(g1) * (2 if word_mode else 1):]
        rest, cap_mode = self._strip_capital(rest)
        hyphen = self.punctuation.get("-", "-")
        cut = rest.find(hyphen)
        if cut > 0 and rest[cut - 1] == self.CAP_LETTER:
            return None  # 줄표(⠠⠤)는 원래 방식대로 읽는다.
        if hyphen in rest and not word_mode:
            # Al-Azar ⠰⠠⠁⠇⠤⠠⠁⠵⠜: 1급 점자표는 붙임표 앞 낱말에만 걸린다.
            head, _, tail = rest.partition(hyphen)
            first = self._decode_grade1_letters(g1 + head)
            if first is None or not tail:
                return None
            return first[0] + "-" + self._decode_word_token(tail), cap_mode
        letter_of = {braille: char for char, braille in self.spelling.items() if char.isalpha() and len(braille) == 1}
        if len(rest) < 2 or rest[0] not in letter_of or g1 in rest or hyphen in rest:
            return None
        if word_mode:
            letters = []
            for cell in rest:
                if cell in letter_of:
                    letters.append(letter_of[cell])
                    continue
                if cell == self.CAP_LETTER:
                    letters.append(None)  # 다음 글자를 대문자로
                    continue
                return None
            out = []
            upper_next = False
            for char in letters:
                if char is None:
                    upper_next = True
                    continue
                out.append(char.upper() if upper_next else char)
                upper_next = False
            return "".join(out), cap_mode
        first = letter_of[rest[0]]
        tail = self._decode_contracted(rest[1:], allow_shortform=False, final_fragment=True)
        return first + tail, cap_mode

    def _peel_edge_punctuation(self, token: str) -> Tuple[str, str, str]:
        """뒤쪽 부호를 먼저 떼어 his. / his?처럼 약어와 같은 칸이 부호로 읽히지 않게 한다."""
        leading = []
        trailing = []
        changed = True
        while changed and token:
            changed = False
            for braille, char in self.punctuation_sequences:
                if len(braille) >= len(token):
                    continue
                if not token.endswith(braille):
                    continue
                start = len(token) - len(braille)
                if self._groupsign_matches(token, start, braille):
                    continue
                trailing.append(char)
                token = token[:-len(braille)]
                changed = True
                break
            if changed:
                continue
            for braille, char in self.leading_punctuation_sequences:
                if len(braille) >= len(token):
                    continue
                if token.startswith(braille) and not self._groupsign_matches(token, 0, braille):
                    leading.append(char)
                    token = token[len(braille):]
                    changed = True
                    break
        trailing.reverse()
        return "".join(leading), token, "".join(trailing)

    def _groupsign_matches(self, token: str, index: int, braille: str) -> bool:
        return self._best_groupsign(token, index, exact_braille=braille) is not None

    def _decode_wordsign_suffix(self, token: str) -> Optional[str]:
        """알파벳 단어약어 뒤의 'd, 'll, 're, 's, 't, 've는 독립 단어를 유지한다."""
        for braille, word in self.braille_to_wordsign.items():
            if not token.startswith(braille) or len(token) == len(braille):
                continue
            suffix = self._decode_contracted(token[len(braille):], allow_shortform=False, final_fragment=True)
            if suffix in self.apostrophe_word_suffixes:
                return word + suffix
        return None

    def _decode_shortform_token(self, token: str) -> Optional[str]:
        if token in self.rev_shortforms:
            return self.rev_shortforms[token]
        best = None
        for word, data in self.shortform_index.items():
            braille = data["unicode"]
            if not braille or not token.startswith(braille) or len(token) == len(braille):
                continue
            if best and len(braille) <= len(best[0]):
                continue
            suffix = self._decode_contracted(token[len(braille):], allow_shortform=False, final_fragment=True)
            if self._shortform_suffix_ok(suffix, data):
                best = (braille, word + suffix)
        return None if best is None else best[1]

    def _decode_composed_shortform(self, target: str) -> Optional[str]:
        """부록 1 목록·10.9.3 낱말처럼 축어가 낱말 안에 든 점자를 읽는다 (⠁⠃⠧⠛⠗⠨⠙ aboveground).
        다시 점역해 똑같은 점자가 나오는 풀이만 받는다."""
        braille_to_word = {data["unicode"]: word for word, data in self.shortform_index.items()}
        if not any(cells in target for cells in braille_to_word):
            return None
        budget = [200]

        def search(index: int, pieces: List[Tuple[str, str]]) -> Optional[str]:
            budget[0] -= 1
            if budget[0] < 0:
                return None
            if index == len(target):
                if not any(kind == "sf" for kind, _ in pieces):
                    return None
                words, plain, start = [], "", 0
                prefix_signs = {braille: pattern for pattern, braille, _p, _r in self.groupsigns if pattern in ("be", "con", "dis")}
                for kind, value in pieces:
                    if kind == "sf":
                        if plain and not start and plain[0] in prefix_signs:
                            # 낱말 처음 be·con·dis 뒤에 축어 (belittle ⠆⠇⠇)
                            words.append(prefix_signs[plain[0]])
                            plain = plain[1:]
                        if plain:
                            words.append(self._decode_contracted(
                                plain, allow_shortform=False, standing_alone=False, final_fragment=start > 0))
                            plain = ""
                        words.append(value)
                        start = 1
                    else:
                        plain += value
                if plain:
                    words.append(self._decode_contracted(
                        plain, allow_shortform=False, standing_alone=False, final_fragment=start > 0))
                candidate = "".join(words)
                if any("\u2800" <= char <= "\u28FF" for char in candidate):
                    return None
                return candidate if self._translate_word(candidate) == target else None
            for cells in sorted(braille_to_word, key=len, reverse=True):
                if target.startswith(cells, index):
                    found = search(index + len(cells), pieces + [("sf", braille_to_word[cells])])
                    if found:
                        return found
            return search(index + 1, pieces + [("plain", target[index])])

        return search(0, [])

    def _decode_prefixed_shortform(self, token: str) -> Optional[str]:
        """접두사 뒤의 축어(unblind)는 글자 b+l과 점열이 같으므로, 허용된 접두일 때만 단어를 복원한다."""
        for prefix in sorted(self.lexicon_prefixes, key=len, reverse=True):
            prefix_braille = self._contract_surface(prefix, whole_word=False)
            if not prefix_braille or not token.startswith(prefix_braille) or len(token) == len(prefix_braille):
                continue
            rest = token[len(prefix_braille):]
            best = None
            for word, data in self.shortform_index.items():
                uni = data["unicode"]
                if not data["rule"].get("allowPrefix") or not uni or not rest.startswith(uni):
                    continue
                if best and len(uni) <= len(best[0]):
                    continue
                suffix_braille = rest[len(uni):]
                suffix = ""
                if suffix_braille:
                    suffix = self._decode_contracted(
                        suffix_braille, allow_shortform=False, final_fragment=True
                    )
                    if not self._shortform_suffix_ok(suffix, data, allow_open_compound=False):
                        continue
                candidate = prefix + word + suffix
                if self._translate_word(candidate, standing_alone=True) == token:
                    best = (uni, candidate)
            if best:
                return best[1]
        return None

    def _decode_contracted(
        self,
        token: str,
        allow_shortform: bool = True,
        final_fragment: bool = False,
        standing_alone: bool = True,
    ) -> str:
        if allow_shortform:
            shortform = self._decode_shortform_token(token)
            if shortform is not None:
                return shortform
        if not final_fragment and token in self.isolated_braille_to_letter:
            claimed = self._best_groupsign(token, 0, final_fragment=False, standing_alone=standing_alone)
            if not claimed or claimed[1] != len(token):
                return self.isolated_braille_to_letter[token]
        out = []
        index = 0
        while index < len(token):
            groupsign = self._best_groupsign(
                token, index, final_fragment=final_fragment, standing_alone=standing_alone
            )
            if groupsign:
                out.append(groupsign[0])
                index += groupsign[1]
                continue
            punctuation = self._punctuation_at(token, index)
            if punctuation:
                out.append(punctuation[0])
                index += punctuation[1]
                continue
            if token.startswith(self.CAP_WORD, index) and index + len(self.CAP_WORD) < len(token):
                rest = self._decode_contracted(
                    token[index + len(self.CAP_WORD):],
                    allow_shortform=True,
                    standing_alone=standing_alone,
                )
                out.append(rest.upper())
                break
            if token.startswith(self.CAP_LETTER, index) and index + len(self.CAP_LETTER) < len(token):
                unit = self._plain_unit(
                    token, index + len(self.CAP_LETTER), final_fragment, standing_alone
                )
                if unit:
                    out.append(self._apply_capital(unit[0], "letter"))
                    index = unit[1]
                    continue
            isolated = self._isolated_letter_at(token, index)
            if isolated:
                out.append(isolated[0])
                index += isolated[1]
                continue
            out.append(self.rev_spelling.get(token[index], token[index]))
            index += 1
        return "".join(out)

    def _isolated_letter_at(self, token: str, index: int):
        for braille, letter in self.isolated_prefixes:
            if token.startswith(braille, index):
                return letter, len(braille)
        return None

    def _plain_unit(self, token: str, index: int, final_fragment: bool, standing_alone: bool):
        groupsign = self._best_groupsign(
            token, index, final_fragment=final_fragment, standing_alone=standing_alone
        )
        if groupsign:
            return groupsign[0], index + groupsign[1]
        isolated = self._isolated_letter_at(token, index)
        if isolated:
            return isolated[0], index + isolated[1]
        cell = token[index]
        if cell in self.rev_spelling:
            return self.rev_spelling[cell], index + 1
        return None

    def _side_is_word(self, token: str, index: int) -> bool:
        """이웃 칸이 글자이거나, 글자 약어의 시작이면 단어가 이어진 것이다."""
        if index < 0 or index >= len(token):
            return False
        cell = token[index]
        if cell == self.letter_grade1_indicator:
            return False
        if cell in self.rev_spelling:
            return True
        return any(token.startswith(braille, index) for braille in self.rev_groupsign_senses)

    def _preceded_by_word(self, token: str, index: int) -> bool:
        if index <= 0:
            return False
        prev = token[index - 1]
        if prev in self.rev_spelling:
            return True
        if prev in self.ambiguous_medial_cells:
            return False
        return prev in self.groupsign_cells

    def _best_groupsign(
        self,
        token: str,
        index: int,
        final_fragment: bool = False,
        exact_braille: Optional[str] = None,
        standing_alone: bool = True,
    ):
        match_text = None
        match_len = 0
        match_priority = 10 ** 9
        senses_by_braille = self.rev_groupsign_senses
        if exact_braille is not None:
            senses_by_braille = {exact_braille: self.rev_groupsign_senses.get(exact_braille, [])}
        for braille, senses in senses_by_braille.items():
            if not token.startswith(braille, index):
                continue
            length = len(braille)
            for sense in senses:
                if not self._groupsign_context_ok(
                    token, index, length, sense["rule"], final_fragment, standing_alone
                ):
                    continue
                priority = sense["priority"]
                if length > match_len or (length == match_len and priority < match_priority):
                    match_text = sense["text"]
                    match_len = length
                    match_priority = priority
        if match_text is None:
            return None
        return match_text, match_len

    def _groupsign_context_ok(
        self,
        token: str,
        index: int,
        length: int,
        rule: dict,
        final_fragment: bool = False,
        standing_alone: bool = True,
    ) -> bool:
        end = index + length
        follows = end < len(token)
        precedes = index > 0
        whole = index == 0 and end == len(token)
        span = token[index:end]
        if (
            self.letter_grade1_indicator
            and span.startswith(self.letter_grade1_indicator)
            and not rule.get("canStandAlone", False)
            and not final_fragment
        ):
            preceded = self._preceded_by_word(token, index)
            followed = follows and self._side_is_word(token, end)
            if not preceded and not followed:
                return False
        if whole:
            if rule.get("avoidWhenStandingAlone") and standing_alone:
                return False
            if rule.get("standingAloneOnly"):
                return standing_alone
            if rule.get("canStandAlone") and standing_alone:
                return True
            if (
                not standing_alone
                and not rule.get("requiresSurroundingLetters")
                and not rule.get("requiresFollowingLetters")
            ):
                return True
            if (
                final_fragment
                and not rule.get("requiresSurroundingLetters")
                and not rule.get("requiresFollowingLetters")
            ):
                return True
            return False
        if rule.get("standingAloneOnly"):
            return False
        if rule.get("requiresSurroundingLetters"):
            return (
                precedes
                and follows
                and self._side_is_word(token, index - 1)
                and self._side_is_word(token, end)
            )
        if not rule.get("canFollowLetters", True) and precedes:
            return False
        if rule.get("requiresFollowingLetters") and not follows:
            return False
        if not rule.get("canPrecedeLetters", True) and follows:
            return False
        return True

    def _punctuation_at(self, token: str, index: int):
        for braille, char in self.punctuation_sequences:
            if token.startswith(braille, index):
                return char, len(braille)
        return None

    def _decode_braille_with_numeric_mode(self, token: str) -> str:
        res = []
        in_num = False
        index = 0
        grade1_len = len(self.grade1_prefix)
        while index < len(token):
            if in_num and self.grade1_prefix and token.startswith(self.grade1_prefix, index):
                res.append(self._finish_as_text(token[index + grade1_len:]))
                return "".join(res)
            if token[index] == self.num_prefix:
                in_num = True
                index += 1
                continue
            if in_num:
                matched = False
                for braille, char, ends_mode in self.numeric_sequences:
                    if not token.startswith(braille, index):
                        continue
                    if (
                        not ends_mode
                        and not self._braille_continuation_reaches_digit(token, index + len(braille))
                    ):
                        continue
                    res.append(char)
                    index += len(braille)
                    if ends_mode:
                        in_num = False
                    matched = True
                    break
                if matched:
                    continue
                if token[index] in self.rev_digits:
                    res.append(self.rev_digits[token[index]])
                    index += 1
                    continue
                punctuation = self._punctuation_at(token, index)
                if punctuation:
                    # 숫자 뒤 ⠲는 dis가 아니라 마침표다 (UEB 6.5.2: 4.b ⠼⠙⠲⠰⠃).
                    res.append(punctuation[0])
                    index += punctuation[1]
                    in_num = False
                    continue
                res.append(self._finish_as_text(token[index:]))
                return "".join(res)
            next_num = token.find(self.num_prefix, index)
            if next_num < 0:
                res.append(self._decode_word_token(token[index:]))
                return "".join(res)
            if next_num > index:
                res.append(self._decode_word_token(token[index:next_num]))
            index = next_num
        return "".join(res)

    def _finish_as_text(self, token: str) -> str:
        if not token:
            return ""
        if self.num_prefix in token:
            return self._decode_braille_with_numeric_mode(token)
        return self._decode_word_token(token, standing_alone=False)
