"""한글 6단원 「이중 모음」. 근거: 제1장 제3절 제7항 (규정집 5~6쪽).

규정집 표와 보기는 점자 ASCII 글꼴로 실려 있어 그대로 옮기고, 앱 카드와 번역 엔진의 점형이 같은지 확인한다.
ㅚ는 제7항대로 한 칸 ⠽이다 (2026-10-13 저장소 데이터를 규정대로 고침).
"""
from common import app_cards, asc, braille, cell_labels, dots_text, jamo_spell, ko_cells, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-double-vowel'
# 제7항 표 (규정집 5쪽)
RULE_TABLE = {'ㅐ': 'r', 'ㅒ': '>r', 'ㅔ': 'n', 'ㅖ': '/', 'ㅘ': 'v', 'ㅙ': 'vr', 'ㅚ': 'y', 'ㅝ': 'p', 'ㅞ': 'pr', 'ㅟ': 'mr', 'ㅢ': 'w'}
TWO_CELL = {'ㅒ': 'ㅑ', 'ㅙ': 'ㅘ', 'ㅞ': 'ㅝ', 'ㅟ': 'ㅜ'}  # 앞 모음 + ㅐ
# 제7항 보기 (규정집 6쪽) 가운데 받침이 없는 낱말
RULE_WORDS = {'매미': 'ereo', '얘기': '>r@o', '지혜': '.oj/', '무늬': 'emcw'}
CHO = ['ㄱ', 'ㅁ', 'ㅅ', 'ㅇ', 'ㅎ']
READ_ITEMS = ['매미', '무늬', '과', '쇠', '위', '계']
WRITE_ITEMS = ['얘기', '지혜', '외', '귀', '뭐', '해']


def compose(cho, jung):
    return chr(0xAC00 + ('ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'.index(cho) * 21 + 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'.index(jung)) * 28)


def build():
    u = unit_data(UNIT_ID)
    app = {c['letter']: c for c in app_cards(UNIT_ID)}
    vowel = {k: app[k]['dots'] for k in RULE_TABLE}
    basic = {c['letter']: c['dots'] for c in app_cards('ko-vowel')}
    # 앱 카드 = 규정집 제7항 표, 엔진 = 규정집 보기
    for k, a in RULE_TABLE.items():
        assert vowel[k] == asc(a), k
    for w, a in RULE_WORDS.items():
        assert ko_cells(w) == reg_cells(a), w
    # 안내 문장에 적은 사실 확인
    one = [k for k in RULE_TABLE if len(vowel[k]) == 1]
    assert one == ['ㅐ', 'ㅔ', 'ㅖ', 'ㅘ', 'ㅚ', 'ㅝ', 'ㅢ'] and len(vowel['ㅚ']) == 1
    for k, front in TWO_CELL.items():
        assert vowel[k] == (basic.get(front) or vowel[front]) + vowel['ㅐ'], k
    for cho in CHO:
        for j in RULE_TABLE:
            s = compose(cho, j)
            assert s in app and app[s]['dots'] == ko_cells(s), s
    for w in READ_ITEMS + WRITE_ITEMS:
        assert jamo_spell(w)[0] == ko_cells(w), w

    def vcard(k):
        labels = [TWO_CELL[k], 'ㅐ'] if k in TWO_CELL else [k]
        return {'name': k, 'cells': vowel[k], 'labels': labels, 'line': dots_text(vowel[k])}

    def word(w):
        cells, labels = jamo_spell(w)
        return {'name': w, 'cells': cells, 'labels': labels, 'line': dots_text(cells)}

    def syl(s):
        return {'name': s, 'cells': app[s]['dots'], 'labels': cell_labels(app[s]), 'line': dots_text(app[s]['dots'])}

    rows = [[c if c != 'ㅇ' else 'ㅇ(생략)'] + [f'{compose(c, j)} {braille(app[compose(c, j)]["dots"])}' for j in RULE_TABLE] for c in CHO]
    rules = [('제7항', '그 밖의 모음자 11개는 다음과 같이 적는다.')]
    learn = [
        {'title': '한 칸으로 쓰는 이중 모음 7개', 'blocks': [
            {'t': 'p', 'text': 'ㅐ·ㅔ·ㅖ·ㅘ·ㅚ·ㅝ·ㅢ는 기본 모음처럼 한 칸에 적습니다. 점의 수는 모음마다 다릅니다.'},
            {'t': 'cards', 'items': [vcard(k) for k in one]},
        ]},
        {'title': '두 칸으로 쓰는 이중 모음 4개', 'blocks': [
            {'t': 'p', 'text': 'ㅒ·ㅙ·ㅞ·ㅟ는 앞 모음 뒤에 ㅐ(' + dots_text(vowel['ㅐ']) + ')를 붙여 두 칸으로 적습니다. ㅒ = ㅑ + ㅐ, ㅙ = ㅘ + ㅐ, ㅞ = ㅝ + ㅐ, ㅟ = ㅜ + ㅐ입니다.'},
            {'t': 'cards', 'items': [vcard(k) for k in TWO_CELL]},
        ]},
        {'title': '이중 모음 음절표', 'blocks': [
            {'t': 'p', 'text': '줄은 초성, 칸은 이중 모음입니다. 초성 한 칸 뒤에 모음을 이어 적고, 첫소리 ㅇ은 적지 않습니다.'},
            {'t': 'table', 'caption': '이중 모음 음절표 (초성 ㄱ·ㅁ·ㅅ·ㅇ·ㅎ)', 'head': ['초성'] + list(RULE_TABLE), 'rows': rows},
        ]},
        {'title': '규정집 보기 낱말', 'blocks': [
            {'t': 'p', 'text': '규정집 제7항의 보기 가운데 받침이 없는 낱말입니다.'},
            {'t': 'cards', 'items': [word(w) for w in RULE_WORDS] + [syl('괴'), syl('귀')]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 글자일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말이나 음절을 괄호에 쓰세요. 1·2·3·5점(ㅐ)이 붙어 있으면 두 칸 모음인지 살펴보세요.', 'blank': '(            )',
             'items': [{'name': dots_text(ko_cells(w)), 'cells': ko_cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': 'ㅒ·ㅙ·ㅞ·ㅟ는 두 칸, 나머지 이중 모음은 한 칸입니다.',
             'items': [{'ask': w, 'cells': len(ko_cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제1장 제3절 모음자 제7항 (규정집 5~6쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '한 칸: ' + ', '.join(f'{k} {braille(vowel[k])}' for k in one),
            '두 칸(앞 모음 + ㅐ): ' + ', '.join(f'{k} {braille(vowel[k])}' for k in TWO_CELL),
            'ㅚ는 한 칸 ' + braille(vowel['ㅚ']) + '(' + dots_text(vowel['ㅚ']) + ')입니다. ㅗ와 ㅐ를 이어 적지 않습니다.',
        ],
        learn=learn, practice=practice,
        checks=[
            '한 칸으로 쓰는 이중 모음 7개를 읽고 쓸 수 있다.',
            'ㅒ·ㅙ·ㅞ·ㅟ는 앞 모음 뒤에 ㅐ를 붙인다는 것을 안다.',
            '이중 모음이 든 음절과 낱말을 읽고 쓸 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(ko_cells(w))} {dots_text(ko_cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
