"""영어 1단원 「알파벳」. 근거: 「개정 한국 점자 규정」 제28항(규정집 19쪽), 제29항(20쪽), [부록 1] 영어 일람표(208쪽).

알파벳 점형은 앱 카드에서 가져와 제28항 표(점자 ASCII)와 대조한다.
국어 문장 안의 로마자 보기(제29항)는 규정집 보기 줄을 그대로 옮긴다(한글 엔진은 로마자를 점역하지 않는다).
"""
from common import app_cards, asc, braille, dots_text, reg_cells, standard_doc, unit_data
from en_common import en_cells, ko_rule, ko_src

UNIT_ID = 'en-letter'
LETTERS = 'abcdefghijklmnopqrstuvwxyz'
# 제28항 표 (규정집 19쪽): 소문자 점형은 점자 ASCII로 글자 그대로, 명칭
NAMES = {'a': '에이', 'b': '비', 'c': '시', 'd': '디', 'e': '이', 'f': '에프', 'g': '지', 'h': '에이치', 'i': '아이',
         'j': '제이', 'k': '케이', 'l': '엘', 'm': '엠', 'n': '엔', 'o': '오', 'p': '피', 'q': '큐', 'r': '아르',
         's': '에스', 't': '티', 'u': '유', 'v': '브이', 'w': '더블유', 'x': '엑스', 'y': '와이', 'z': '제트'}
RULE_WORDS = ['book', 'moon', 'tea', 'happy', 'purple', 'welcome']  # 제28항 보기 (규정집 19쪽)
# 제29항 보기 (규정집 20쪽)
KO_SENTENCE = ('그는 Canada로 여행을 떠났다.', '``@{cz`0,canada4"u`:jr7!`,isc/i4')

GROUPS = [
    ('a부터 j까지', 'abcdefghij', '칸의 위쪽 네 점(1·2·4·5점)만 씁니다.'),
    ('k부터 t까지', 'klmnopqrst', 'a~j의 점형에 3점을 더합니다.'),
    ('u, v, x, y, z', 'uvxyz', 'a~e의 점형에 3·6점을 더합니다.'),
    ('w', 'w', 'w는 j의 점형에 6점을 더합니다. w만 이 규칙에서 벗어납니다.'),
]
LOOK_ALIKE = [
    ('ei', 'e(1·5점)와 i(2·4점)는 서로 좌우를 뒤집은 모양입니다.'),
    ('dfhj', '모두 위쪽 네 점 가운데 세 점입니다. 빠진 점을 보세요. d는 2점, f는 5점, h는 4점, j는 1점이 빠졌습니다.'),
    ('ak', 'k는 a에 3점을 더한 모양입니다. 왼쪽 아래 3점이 있는지 꼭 확인하세요.'),
]
READ_ITEMS = ['e', 'i', 'k', 'w', 'x', 'z', 'moon', 'happy']
WRITE_ITEMS = ['b', 'f', 'm', 'p', 'u', 'y', 'book', 'tea']


def build():
    u = unit_data(UNIT_ID)
    cards = {c['letter']: c['dots'] for c in app_cards(UNIT_ID)}
    # 앱 카드 = 제28항 표 = [부록 1] 영어 알파벳 (점자 ASCII는 글자 그대로)
    assert list(cards) == list(LETTERS)
    for ch in LETTERS:
        assert cards[ch] == asc(ch), ch
    d = {ch: set(cells[0]) for ch, cells in cards.items()}
    # 안내 문장에 적은 사실 확인
    assert all(d[c] <= {1, 2, 4, 5} for c in 'abcdefghij')
    for a, k in zip('abcdefghij', 'klmnopqrst'):
        assert d[k] == d[a] | {3}, k
    for a, k in zip('abcde', 'uvxyz'):
        assert d[k] == d[a] | {3, 6}, k
    assert d['w'] == d['j'] | {6}
    assert d['e'] == {1, 5} and d['i'] == {2, 4}
    assert {c: {1, 2, 4, 5} - d[c] for c in 'dfhj'} == {'d': {2}, 'f': {5}, 'h': {4}, 'j': {1}}
    # 제28항 보기 낱말 = 엔진, 연습 낱말에는 약자가 없어 글자 수 = 칸 수
    for w in RULE_WORDS:
        assert en_cells(w) == reg_cells(w), w
    def cells(w):  # 알파벳 하나는 점형 카드 그대로, 낱말은 엔진 (연습 낱말에는 약자가 없어 글자 수 = 칸 수)
        return cards[w] if len(w) == 1 else en_cells(w)
    for w in READ_ITEMS + WRITE_ITEMS:
        assert cells(w) == [cards[c][0] for c in w], w
    ko_cells = reg_cells(KO_SENTENCE[1])
    assert braille(ko_cells).count('⠴') == 1 and '⠴⠠⠉⠁⠝⠁⠙⠁⠲' in braille(ko_cells)  # 로마자표 + Canada + 종료표

    def card(ch):
        return {'name': f'{ch} ({NAMES[ch]})', 'cells': cards[ch], 'labels': [ch], 'line': dots_text(cards[ch])}

    def word(w):
        return {'name': w, 'cells': en_cells(w), 'labels': list(w), 'line': dots_text(en_cells(w))}

    learn = [
        {'title': f'{title}', 'blocks': [
            {'t': 'p', 'text': f'{", ".join(chars)}: {note}'},
            {'t': 'cards', 'items': [card(c) for c in chars]},
        ]} for title, chars, note in GROUPS
    ] + [
        {'title': '모양이 비슷한 알파벳', 'blocks': [
            {'t': 'cards', 'caption': note, 'items': [card(c) for c in chars]} for chars, note in LOOK_ALIKE
        ]},
        {'title': '알파벳으로 낱말 쓰기', 'blocks': [
            {'t': 'p', 'text': '알파벳을 한 칸씩 이어 적으면 낱말이 됩니다. 아래는 규정집 제28항의 보기 낱말입니다.'},
            {'t': 'cards', 'items': [word(w) for w in RULE_WORDS]},
        ]},
        {'title': '한글 문장 안에서 알파벳 쓰기', 'blocks': [
            {'t': 'p', 'text': '한글 문장 안에 로마자가 나오면 앞에 로마자표(⠴, 3·5·6점)를, 뒤에 로마자 종료표(⠲, 2·5·6점)를 적습니다. '
                               '아래는 규정집 제29항의 보기 문장입니다. 대문자 C 앞의 6점은 다음 단원에서 배웁니다.'},
            {'t': 'cards', 'items': [{'name': KO_SENTENCE[0], 'cells': ko_cells, 'labels': None, 'line': dots_text(ko_cells)}]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 알파벳일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 알파벳이나 낱말을 괄호에 쓰세요.', 'blank': '(          )',
             'items': [{'name': dots_text(cells(w)), 'cells': cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 알파벳을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '빈 점칸에 알맞은 점을 칠하세요. 알파벳 하나는 한 칸입니다.',
             'items': [{'ask': w, 'cells': len(cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=ko_rule('제28항', '제29항'), rule_src=ko_src('제28항', '제29항') + ', [부록 1] 외국어 점자 일람표 영어 (규정집 208쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '알파벳 하나는 점칸 한 칸에 적습니다. 영어 점자는 「통일영어점자 규정」(UEB)을 따릅니다.',
            'a~j는 위쪽 네 점, k~t는 a~j에 3점, u·v·x·y·z는 a~e에 3·6점을 더합니다. w만 따로 외웁니다.',
            '예) a → ' + braille(cards['a']) + ' (1점), k → ' + braille(cards['k']) + ' (1·3점), u → ' + braille(cards['u']) + ' (1·3·6점)',
            '한글 문장 안에서는 로마자 앞에 로마자표 ⠴, 뒤에 로마자 종료표 ⠲를 적습니다 (제29항).',
        ],
        learn=learn, practice=practice,
        checks=[
            '알파벳 26자의 점형을 읽고 쓸 수 있다.',
            'a~j에 3점, 3·6점을 더해 k~t, u~z를 만들 수 있다.',
            'w가 규칙에서 벗어난다는 것을 안다.',
            '한글 문장 안의 로마자 앞뒤에 로마자표와 로마자 종료표를 적는다는 것을 안다.',
        ],
        answers=[
            ('읽기 연습', '    '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', '    '.join(f'({i}) {w} {braille(cells(w))} {dots_text(cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
