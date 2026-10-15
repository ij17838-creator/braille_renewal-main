"""영어 단원 학습자료 공통 도구.

영어 점자는 한글 점자 규정을 먼저 따지고, 규정집이 「통일영어점자 규정」(UEB)을 따르라고 한 부분
(제28항, 제30항, 제32항)에만 UEB를 쓴다. 영어 단원 안의 낱말·문장은 로마자표와 로마자 종료표 사이의
표기(제32항)이므로 UEB 약자 규칙을 따른다.

점형은 앱 카드(common.app_cards)와 저장소 영어 점역 엔진(engine/en)에서 가져오고,
규정집 표(UEB 규정집은 점자 문자 그대로 실려 있다)와 보기를 옮겨 적어 assert로 대조한다.
쪽수는 규정집에 인쇄된 쪽 번호다. UEB 규정집은 PDF 쪽에서 28을 빼면 인쇄된 쪽 번호다.
"""
from common import REPO, braille, dots_of, dots_text

KO_SRC = '「개정 한국 점자 규정」'
UEB_SRC = '「통일영어점자 규정」(UEB, 2024)'

# 한글 점자 규정 원문 (규정집 19~25쪽)
KO_RULES = {
    '제28항': '로마자는 「통일영어점자 규정」에 따라 다음과 같이 적는다.',
    '제28항 [붙임]': ('로마자가 한 글자만 대문자일 때에는 대문자 기호표 ⠠을 그 앞에 적고, 단어 전체가 대문자이거나 '
                    '두 글자 이상 연속해서 대문자일 때에는 대문자 단어표 ⠠⠠을 그 앞에 적는다. 세 개 이상의 연속된 단어가 '
                    '모두 대문자일 때에는 첫 단어 앞에 대문자 구절표 ⠠⠠⠠을 적고, 마지막 단어 뒤에 대문자 종료표 ⠠⠄을 적는다.'),
    '제29항': ('국어 문장 안에 로마자가 나올 때에는 그 앞에 로마자표 ⠴을 적고 그 뒤에 로마자 종료표 ⠲을 적는다. '
              '이때 로마자가 둘 이상 연이어 나오면 첫 로마자 앞에 로마자표를 적고 마지막 로마자 뒤에 로마자 종료표를 적는다.'),
    '제32항': '로마자표와 로마자 종료표 사이의 표기는 「통일영어점자 규정」에 따라 적는다.',
    '제33항': ('「통일영어점자 규정」과 「한글 점자」의 점형이 다른 문장 부호(, : ; ―)가 로마자와 한글 사이에 나올 때에는 '
              '로마자 종료표를 적지 않고 문장 부호는 「한글 점자」에 따라 적는다.'),
    '제37항': ('다음 영어 단어 앞에 로마자표가 올 때에는 단어 약자를 쓰지 않고 알파벳과 여러 글자를 나타내는 묶음 약자를 '
              '사용하여 풀어 적는다.'),
    '제37항 [붙임]': '‘be, enough, his, in, was, were’는 로마자 종료표 앞에서도 단어 약자를 쓰지 않고 알파벳과 묶음 약자를 사용하여 풀어 적는다.',
    '제40항': '숫자는 수표 ⠼을 앞세워 다음과 같이 적는다.',
}
KO_PAGES = {'제28항': 19, '제28항 [붙임]': 20, '제29항': 20, '제32항': 21, '제33항': 22, '제37항': 24, '제37항 [붙임]': 25, '제40항': 27}

# 규정집 원문 안의 점자 기호도 규정집 그대로인지 확인 (점자 ASCII: , = 6점, ' = 3점, 0 = 3·5·6점, 4 = 2·5·6점, # = 3·4·5·6점)
_REG_SIGNS = {'⠠': ',', '⠠⠠': ',,', '⠠⠠⠠': ',,,', '⠠⠄': ",'", '⠴': '0', '⠲': '4', '⠼': '#'}

_EN = None


def en_braille(text):
    """저장소 영어 점역 엔진(engine/en)으로 영어 글을 UEB 점자로 바꾼다."""
    global _EN
    if _EN is None:
        import sys
        sys.path.insert(0, str(REPO))
        from engine.en.en_parser import BrailleEngine
        _EN = BrailleEngine()
    return _EN.text_to_braille(text)


def cells_of(br):
    """점자 문자열 → 점칸 목록. 띄어쓰기는 빈칸 []."""
    return [[] if ch in ' ⠀' else dots_of(ch) for ch in br]


def en_cells(text):
    return cells_of(en_braille(text))


def check_ueb(examples):
    """UEB 규정집 보기(글 → 점자)를 엔진이 똑같이 적는지 확인한다."""
    for text, br in examples.items():
        assert en_braille(text) == br, (text, en_braille(text), br)


def word_card(text, line=None):
    cells = en_cells(text)
    return {'name': text, 'cells': cells, 'labels': None, 'line': line or dots_text(cells)}


def sign_card(name, br, line=None):
    cells = cells_of(br)
    return {'name': name, 'cells': cells, 'labels': [name] * len(cells), 'line': line or dots_text(cells)}


def ko_rule(*keys):
    return [(k, KO_RULES[k]) for k in keys]


def ko_src(*keys, where='제4장 제10절 국어 문장 안의 로마자와 그리스 문자'):
    pages = sorted({KO_PAGES[k] for k in keys})
    pg = f'{pages[0]}쪽' if len(pages) == 1 else f'{pages[0]}~{pages[-1]}쪽'
    return f'{KO_SRC} {where} {", ".join(dict.fromkeys(k.split(" ")[0] for k in keys))} (규정집 {pg})'


def read_items(texts):
    """읽기 연습 문제: 점 번호만 보여 주고 답(글)은 정답에만 둔다."""
    return [{'name': dots_text(en_cells(t)), 'cells': en_cells(t), 'labels': None} for t in texts]


def write_items(texts):
    return [{'ask': t, 'cells': len(en_cells(t))} for t in texts]


def answers(read, write):
    return [
        ('읽기 연습', '    '.join(f'({i}) {t}' for i, t in enumerate(read, 1))),
        ('쓰기 연습', '    '.join(f'({i}) {t} {en_braille(t)} {dots_text(en_cells(t))}' for i, t in enumerate(write, 1))),
    ]


def check_reg_signs():
    """KO_RULES 원문에 적은 점자 기호가 규정집 점자 ASCII와 같은지 확인한다."""
    from common import asc
    for br, a in _REG_SIGNS.items():
        assert cells_of(br) == asc(a), br


check_reg_signs()
assert braille(cells_of('⠠⠠')) == '⠠⠠'
