"""
ko_syntax_analyzer.py
한글 점자 문장요소 유효성 검증 및 음운/문맥 결합 규칙 판별기
"""

import json
from typing import List, Dict, Any, Optional, Tuple

from data_paths import find_data_file, resolve_data_root


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
        # 1. 숫자 뒤 충돌 주의 초성 (ㄴ, ㄷ, ㅁ, ㅋ, ㅌ, ㅍ, ㅎ)
        self.affected_initials = set(
            self.ko_data.get("special_rules", {})
            .get("number_prefix_rule", {})
            .get("affected_initials", ["ㄴ", "ㄷ", "ㅁ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"])
        )

        # 2. 숫자 뒤 단위어 예외 목록 (다음절 단위어 추가 및 길이 역순 정렬)
        raw_units = (
            self.number_rules.get("collision_resolutions", {})
            .get("trailing_letters", {})
            .get("exempt_units", [])
        )
        self.exempt_units = set(raw_units)
        # 긴 단위어를 먼저 매칭할 수 있도록 길이 기준 내림차순 정렬 튜플 구성
        self.exempt_units_sorted = tuple(sorted(self.exempt_units, key=len, reverse=True))

        # 3. 문장부호 쌍 매핑 (여는 부호 -> 닫는 부호)
        self.bracket_pairs = {
            "“": "”",
            "‘": "’",
            "《": "》",
            "〈": "〉",
            "(": ")",
            "[": "]"
        }

        # [수정 3] ko_marks.json 기준 글씨체 및 점역자주 태그 쌍 매핑 정비
        self.tag_pairs = {
            "<tn>": "</tn>",
            "<i>": "<b>"  # ko_marks.json 스펙: <i>(글씨체표 시작) -> <b>(글씨체표 종료)
        }

        # 4. 불규칙 활용 규칙
        self.irregular_rules = self.lexicon.get("irregular_rules", {})

    @classmethod
    def decompose(cls, char: str) -> Optional[Tuple[str, str, str]]:
        """한글 음절(가~힣)을 초성, 중성, 종성으로 분해"""
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

    # -------------------------------------------------------------
    # 1. 숫자-한글 음절 충돌 감지
    # -------------------------------------------------------------
    def check_number_letter_collision(self, text: str) -> List[Dict[str, Any]]:
        """
        숫자 바로 뒤에 공백 없이 충돌 주의 한글 초성이 올 때 1급 기호표(⠰) 필요 여부를 탐지.
        점자 규정 제17항 단위어(년, 월, 일, 미터 등)는 예외 처리하여 불필요한 오류 제외.
        """
        issues = []
        for i in range(len(text) - 1):
            curr_ch = text[i]
            next_ch = text[i + 1]

            if curr_ch.isdigit() and ('가' <= next_ch <= '힣'):
                tail_text = text[i + 1:]
                
                # 다음절/단음절 단위어 접두사 일치 검사
                if tail_text.startswith(self.exempt_units_sorted):
                    continue

                decomp = self.decompose(next_ch)
                if decomp and decomp[0] in self.affected_initials:
                    issues.append({
                        "type": "NUMBER_HANGUL_COLLISION",
                        "index": i + 1,
                        "trigger": f"{curr_ch}{next_ch}",
                        "initial": decomp[0],
                        "rule": "1급 기호표(⠰) 삽입 필요",
                        "message": f"숫자 '{curr_ch}' 뒤에 초성 '{decomp[0]}'이(가) 오는 음절 '{next_ch}'이 결합되어 1급 기호표(⠰)가 필요합니다."
                    })
        return issues

    # -------------------------------------------------------------
    # 2. 문장부호 및 점역 태그 정합성 검사
    # -------------------------------------------------------------
    def validate_delimiters_and_tags(self, text: str) -> List[Dict[str, Any]]:
        """태그와 괄호의 매칭 및 미닫힘 유효성 검증"""
        errors = []
        stack = []

        all_tags = list(self.tag_pairs.keys()) + list(self.tag_pairs.values())
        all_tags.sort(key=len, reverse=True)

        i = 0
        n = len(text)
        while i < n:
            # 1. 태그 매칭 검사
            matched_tag = None
            for tag in all_tags:
                if text[i:i + len(tag)] == tag:
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

            # 2. 괄호 및 따옴표 검사
            ch = text[i]
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

        # 3. 닫히지 않은 잔여 요소 처리
        while stack:
            unclosed, pos = stack.pop()
            errors.append({
                "type": "UNCLOSED_ELEMENT",
                "index": pos,
                "element": unclosed,
                "message": f"부호/태그 '{unclosed}'이(가) 닫히지 않은 채 문장이 종료되었습니다."
            })

        return errors

    # -------------------------------------------------------------
    # 3. 불규칙 활용 어간 결합 판별
    # -------------------------------------------------------------
    def analyze_conjugation_form(self, stem: str, eomi: str) -> Dict[str, Any]:
        """어간(stem)과 어미(eomi) 결합 시 불규칙/규칙 변동 판정."""
        if not stem:
            return {"rule_applied": "입력 오류", "surface_form": eomi, "braille_instruction": ""}

        # 1) ㄷ 불규칙
        d_rule = self.irregular_rules.get("digeut", {})
        regular_d = [item["base"] for item in d_rule.get("transformation", {}).get("regular_exceptions", [])]
        if stem[-1] in ["듣", "걷", "묻"] and stem[-1] not in regular_d:
            if eomi.startswith(('아', '어', '으')):
                transformed = stem[:-1] + ('들' if stem[-1] == '듣' else '걸' if stem[-1] == '걷' else '물')
                return {
                    "rule_applied": "ㄷ 불규칙",
                    "surface_form": f"{transformed}{eomi}",
                    "braille_instruction": "변형된 받침(ㄹ) 표기에 맞는 점형으로 결합"
                }

        # 2) ㅂ 불규칙
        b_rule = self.irregular_rules.get("bieup", {})
        regular_b = [item["base"] for item in b_rule.get("transformation", {}).get("regular_exceptions", [])]
        decomp_last = self.decompose(stem[-1])
        if decomp_last and decomp_last[2] == 'ㅂ' and stem[-1] not in regular_b:
            cho, jung, _ = decomp_last
            base_syl = self.compose(cho, jung, '')
            stem_prefix = stem[:-1]

            if eomi.startswith(("아", "어")):
                if stem[-1] in ["돕", "곱"]:
                    vowel_tail = "와"
                else:
                    vowel_tail = "워"
                return {
                    "rule_applied": "ㅂ 불규칙",
                    "surface_form": f"{stem_prefix}{base_syl}{vowel_tail}{eomi[1:]}",
                    "braille_instruction": "축약 모음(ㅘ/ㅝ) 점형 단독 결합"
                }
            elif eomi.startswith("으"):
                return {
                    "rule_applied": "ㅂ 불규칙 (으 모음 흡수)",
                    "surface_form": f"{stem_prefix}{base_syl}우{eomi[1:]}",
                    "braille_instruction": "어간 종성 탈락 후 '우' 음절 약자/모음 결합"
                }

        # 3) ㅅ 불규칙
        s_rule = self.irregular_rules.get("siot", {})
        regular_s = [item["base"] for item in s_rule.get("transformation", {}).get("regular_exceptions", [])]
        if decomp_last and decomp_last[2] == 'ㅅ' and stem[-1] not in regular_s:
            if eomi.startswith(('아', '어', '으')):
                cho, jung, _ = decomp_last
                base_syl = self.compose(cho, jung, '')
                return {
                    "rule_applied": "ㅅ 불규칙",
                    "surface_form": f"{stem[:-1]}{base_syl}{eomi}",
                    "braille_instruction": "어간 종성(ㅅ) 탈락 표기 및 축약 없이 독립 음절 점자 유지"
                }

        # 4) ㅡ 탈락
        if decomp_last and decomp_last[1] == 'ㅡ' and decomp_last[2] == '':
            if eomi.startswith(('아', '어')):
                cho = decomp_last[0]
                prev_char = stem[-2] if len(stem) >= 2 else None
                new_jung = 'ㅓ'
                if prev_char:
                    p_decomp = self.decompose(prev_char)
                    if p_decomp and p_decomp[1] in ['ㅏ', 'ㅗ', 'ㅑ', 'ㅘ']:
                        new_jung = 'ㅏ'
                transformed_syl = self.compose(cho, new_jung, '')
                return {
                    "rule_applied": "ㅡ 탈락",
                    "surface_form": f"{stem[:-1]}{transformed_syl}{eomi[1:]}",
                    "braille_instruction": "어간 모음 'ㅡ' 탈락 후 모음조화에 따른 단일 음절 점형 결합"
                }

        # 5) 르 불규칙
        if stem.endswith("르") and (eomi.startswith("아") or eomi.startswith("어")):
            prev = stem[-2] if len(stem) >= 2 else ""
            if prev:
                prev_decomp = self.decompose(prev)
                if prev_decomp and prev_decomp[2] == '':
                    p_cho, p_jung, _ = prev_decomp
                    new_prev = self.compose(p_cho, p_jung, 'ㄹ')
                    vowel_tail = "라" if p_jung in ['ㅏ', 'ㅗ'] else "러"
                    return {
                        "rule_applied": "르 불규칙",
                        "surface_form": f"{stem[:-2]}{new_prev}{vowel_tail}{eomi[1:]}",
                        "braille_instruction": "앞 음절에 받침 ㄹ(⠂) 추가 및 뒷음절 모음조화 점형 결합"
                    }

        return {
            "rule_applied": "규칙 결합",
            "surface_form": f"{stem}{eomi}",
            "braille_instruction": "기본 음소 및 약자 규칙 적용"
        }

    # -------------------------------------------------------------
    # 4. 종합 텍스트 검증 실행
    # -------------------------------------------------------------
    def validate_text(self, text: str) -> Dict[str, Any]:
        """점역 전 텍스트의 구문 규칙 및 충돌 요소를 전수 검사합니다."""
        collision_issues = self.check_number_letter_collision(text)
        delimiter_issues = self.validate_delimiters_and_tags(text)

        is_valid = len(collision_issues) == 0 and len(delimiter_issues) == 0

        return {
            "is_valid": is_valid,
            "total_issues": len(collision_issues) + len(delimiter_issues),
            "collisions": collision_issues,
            "delimiters": delimiter_issues
        }


if __name__ == "__main__":
    validator = BrailleRuleValidator()

    # 1. 숫자-단위어 예외 및 태그 매칭 테스트
    test_text = "제2차 세계대전은 <tn>1945년에 끝났다. 결과는 <i>승리<b>였다. 5월 12일 3미터 앞."
    result = validator.validate_text(test_text)

    print("=== 구문 정합성 검사 결과 ===")
    print(f"검증 통과 여부: {result['is_valid']}")
    print(f"발견된 이슈 수: {result['total_issues']}")
    for col in result["collisions"]:
        print(f" - [충돌 경고]: {col['message']}")
    for delim in result["delimiters"]:
        print(f" - [구문 오류]: {delim['message']}")

    # 2. 불규칙 활용 판정 테스트
    print("\n=== 용언 활용 결합 판정 ===")
    print("1. ㅂ 불규칙 (돕다 + 아):", validator.analyze_conjugation_form("돕", "아"))
    print("2. ㅂ 불규칙 (눕다 + 어):", validator.analyze_conjugation_form("눕", "어"))
    print("3. ㅅ 불규칙 (짓다 + 어):", validator.analyze_conjugation_form("짓", "어"))
    print("4. ㅡ 탈락   (쓰다 + 어):", validator.analyze_conjugation_form("쓰", "어"))
    print("5. 르 불규칙 (부르다 + 어):", validator.analyze_conjugation_form("부르", "어"))