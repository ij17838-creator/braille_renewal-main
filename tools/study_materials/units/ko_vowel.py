"""한글 4단원 「기본 모음」. 근거: 제1장 제3절 제6항 (규정집 5쪽).

규정집 표는 점자 ASCII 글꼴로 실려 있어 RULE_TABLE에 그대로 옮기고, 앱 카드의 점형과 같은지 확인한다.
"""
from common import app_cards, asc, braille, dots_text, standard_doc, unit_data

UNIT_ID = 'ko-vowel'
# 제6항 표 (규정집 5쪽)
RULE_TABLE = {'ㅏ': '<', 'ㅑ': '>', 'ㅓ': 's', 'ㅕ': ':', 'ㅗ': 'u', 'ㅛ': '+', 'ㅜ': 'm', 'ㅠ': '%', 'ㅡ': '[', 'ㅣ': 'o'}
PAIRS = [('ㅏ', 'ㅑ'), ('ㅓ', 'ㅕ'), ('ㅗ', 'ㅛ'), ('ㅜ', 'ㅠ'), ('ㅡ', 'ㅣ')]
LR = {1: 4, 2: 5, 3: 6, 4: 1, 5: 2, 6: 3}  # 왼쪽 줄 ↔ 오른쪽 줄
UD = {1: 3, 2: 2, 3: 1, 4: 6, 5: 5, 6: 4}  # 위 ↔ 아래
READ_ITEMS = ['ㅓ', 'ㅛ', 'ㅣ', 'ㅏ', 'ㅠ', 'ㅗ', 'ㅡ', 'ㅕ']
WRITE_ITEMS = ['ㅏ', 'ㅜ', 'ㅑ', 'ㅡ', 'ㅕ', 'ㅗ', 'ㅣ', 'ㅠ']


def flip(dots, table):
    return sorted(table[d] for d in dots)


def build():
    u = unit_data(UNIT_ID)
    cards = {c['letter']: c['dots'] for c in app_cards(UNIT_ID)}
    # 앱 카드 = 규정집 제6항 표
    assert set(cards) == set(RULE_TABLE), sorted(cards)
    for ch, a in RULE_TABLE.items():
        assert cards[ch] == asc(a), ch
    d = {ch: cells[0] for ch, cells in cards.items()}
    # 안내 문장에 적은 사실 확인
    assert all(len(cells) == 1 and len(cells[0]) == 3 for cells in cards.values())
    for a, b in PAIRS:
        assert flip(d[a], LR) == d[b], (a, b)  # 짝은 좌우로 뒤집은 모양
    assert flip(d['ㅏ'], UD) == d['ㅓ'] and flip(d['ㅗ'], UD) == d['ㅜ']  # 위아래로 뒤집은 모양
    assert flip(d['ㅑ'], UD) == d['ㅕ'] and flip(d['ㅛ'], UD) == d['ㅠ']

    def card(ch, labels=True):
        return {'name': ch, 'cells': cards[ch], 'labels': [ch], 'line': dots_text(cards[ch])}

    rules = [('제6항', '기본 모음자 10개는 다음과 같이 적는다.')]
    learn = [
        {'title': '기본 모음 10개', 'blocks': [
            {'t': 'p', 'text': '기본 모음은 모두 점 세 개로 된 한 칸입니다. 규정집 표의 순서대로 보입니다.'},
            {'t': 'cards', 'items': [card(c) for c in RULE_TABLE]},
        ]},
        {'title': '짝으로 익히기: 좌우로 뒤집은 모양', 'blocks': [
            {'t': 'p', 'text': 'ㅏ와 ㅑ처럼 짝이 되는 모음은 점칸의 왼쪽 줄과 오른쪽 줄을 맞바꾼 모양입니다. 하나를 알면 짝도 알 수 있습니다.'},
        ] + [
            {'t': 'cards', 'caption': f'{a}({dots_text(cards[a])})의 왼쪽과 오른쪽을 바꾸면 {b}({dots_text(cards[b])})입니다.',
             'items': [card(a), card(b)]} for a, b in PAIRS
        ]},
        {'title': '헷갈리기 쉬운 모음: 위아래로 뒤집은 모양', 'blocks': [
            {'t': 'cards', 'caption': f'ㅏ({dots_text(cards["ㅏ"])})를 위아래로 뒤집으면 ㅓ({dots_text(cards["ㅓ"])})입니다. 1점이 있으면 ㅏ, 3점이 있으면 ㅓ입니다.',
             'items': [card('ㅏ'), card('ㅓ')]},
            {'t': 'cards', 'caption': f'ㅗ({dots_text(cards["ㅗ"])})를 위아래로 뒤집으면 ㅜ({dots_text(cards["ㅜ"])})입니다. 6점이 있으면 ㅗ, 4점이 있으면 ㅜ입니다.',
             'items': [card('ㅗ'), card('ㅜ')]},
        ]},
    ]
    assert 1 in d['ㅏ'] and 1 not in d['ㅓ'] and 3 in d['ㅓ'] and 3 not in d['ㅏ']
    assert 6 in d['ㅗ'] and 6 not in d['ㅜ'] and 4 in d['ㅜ'] and 4 not in d['ㅗ']
    practice = [
        {'title': '읽기 연습: 어떤 모음일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 모음을 괄호에 쓰세요.', 'blank': '(        )',
             'items': [{'name': dots_text(cards[c]), 'cells': cards[c], 'labels': None} for c in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 모음을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '빈 점칸에 알맞은 점을 칠하세요. 기본 모음 하나는 한 칸입니다.',
             'items': [{'ask': c, 'cells': 1} for c in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제1장 제3절 모음자 (규정집 5쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '기본 모음 하나는 점 세 개로 된 한 칸입니다.',
            '짝(ㅏ·ㅑ, ㅓ·ㅕ, ㅗ·ㅛ, ㅜ·ㅠ, ㅡ·ㅣ)은 왼쪽 줄과 오른쪽 줄을 맞바꾼 모양입니다.',
            '규정집 표: ' + ', '.join(f'{c} {braille(cards[c])}' for c in RULE_TABLE),
        ],
        learn=learn, practice=practice,
        checks=[
            '기본 모음 10개의 점형을 읽고 쓸 수 있다.',
            '짝이 되는 모음은 좌우로 뒤집은 모양이라는 것을 안다.',
            'ㅏ와 ㅓ, ㅗ와 ㅜ를 구별할 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {c}' for i, c in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {c} {braille(cards[c])} {dots_text(cards[c])}' for i, c in enumerate(WRITE_ITEMS, 1))),
        ],
    )
