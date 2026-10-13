"""한글 3단원 「초성 자음」. 근거: 제1장 제1절 제1항과 [다만 1] (규정집 3쪽).

규정집 표는 점자 ASCII 글꼴로 실려 있어 RULE_TABLE에 그대로 옮기고, 앱 카드의 점형과 같은지 확인한다.
"""
from common import app_cards, asc, braille, dots_text, standard_doc, unit_data

UNIT_ID = 'ko-initial'
# 제1항 표 (규정집 3쪽). ㅇ은 [다만 1]에 따라 첫소리에서 적지 않는다.
RULE_TABLE = {'ㄱ': '@', 'ㄴ': 'c', 'ㄷ': 'i', 'ㄹ': '"', 'ㅁ': 'e', 'ㅂ': '^', 'ㅅ': ',',
              'ㅈ': '.', 'ㅊ': ';', 'ㅋ': 'f', 'ㅌ': 'h', 'ㅍ': 'd', 'ㅎ': 'j'}
NAMES = {'ㄱ': '기역', 'ㄴ': '니은', 'ㄷ': '디귿', 'ㄹ': '리을', 'ㅁ': '미음', 'ㅂ': '비읍', 'ㅅ': '시옷',
         'ㅈ': '지읒', 'ㅊ': '치읓', 'ㅋ': '키읔', 'ㅌ': '티읕', 'ㅍ': '피읖', 'ㅎ': '히읗'}

GROUPS = [
    ('점 하나', ['ㄱ', 'ㄹ', 'ㅅ']),
    ('점 두 개', ['ㄴ', 'ㄷ', 'ㅁ', 'ㅂ', 'ㅈ', 'ㅊ']),
    ('점 세 개', ['ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']),
]
LOOK_ALIKE = [
    (['ㄱ', 'ㄹ', 'ㅅ'], '오른쪽 줄에 점이 하나뿐입니다. 높이로 구별합니다. ㄱ은 위(4점), ㄹ은 가운데(5점), ㅅ은 아래(6점)입니다.'),
    (['ㅂ', 'ㅈ', 'ㅊ'], '오른쪽 줄에 점이 두 개입니다. 빠진 점을 보세요. ㅂ은 6점, ㅈ은 5점, ㅊ은 4점이 빠졌습니다.'),
    (['ㄷ', 'ㅁ'], '점 두 개가 비스듬히 놓였습니다. ㄷ은 2·4점(왼쪽 가운데와 오른쪽 위), ㅁ은 1·5점(왼쪽 위와 오른쪽 가운데)입니다.'),
    (['ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'], '모두 위쪽 네 점(1·2·4·5점) 가운데 세 점입니다. 빠진 점을 보세요. ㅋ은 5점, ㅌ은 4점, ㅍ은 2점, ㅎ은 1점이 빠졌습니다.'),
]
READ_ITEMS = ['ㅂ', 'ㅅ', 'ㅋ', 'ㄷ', 'ㅊ', 'ㅍ', 'ㄹ', 'ㅁ']
WRITE_ITEMS = ['ㄱ', 'ㅁ', 'ㅈ', 'ㅎ', 'ㄴ', 'ㅌ', 'ㅅ', 'ㅂ']


def build():
    u = unit_data(UNIT_ID)
    cards = {c['letter']: c['dots'] for c in app_cards(UNIT_ID)}
    # 앱 카드 = 규정집 제1항 표 (ㅇ 빼고 13자)
    assert set(cards) == set(RULE_TABLE), sorted(cards)
    for ch, a in RULE_TABLE.items():
        assert cards[ch] == asc(a), ch
    d = {ch: set(cells[0]) for ch, cells in cards.items()}
    # 안내 문장에 적은 사실 확인
    for title, chars in GROUPS:
        assert all(len(d[c]) == {'점 하나': 1, '점 두 개': 2, '점 세 개': 3}[title] for c in chars), title
    assert sum(len(c) for _, c in GROUPS) == 13 and all(len(cards[c]) == 1 for c in cards)
    assert d['ㄱ'] == {4} and d['ㄹ'] == {5} and d['ㅅ'] == {6}
    assert {c: {4, 5, 6} - d[c] for c in 'ㅂㅈㅊ'} == {'ㅂ': {6}, 'ㅈ': {5}, 'ㅊ': {4}}
    assert d['ㄷ'] == {2, 4} and d['ㅁ'] == {1, 5}
    assert {c: {1, 2, 4, 5} - d[c] for c in 'ㅋㅌㅍㅎ'} == {'ㅋ': {5}, 'ㅌ': {4}, 'ㅍ': {2}, 'ㅎ': {1}}
    assert all(not d[c] & {3} for c in d)  # 첫소리 자음에는 3점이 없다

    def card(ch):
        return {'name': f'{ch} ({NAMES[ch]})', 'cells': cards[ch], 'labels': [ch], 'line': dots_text(cards[ch])}

    rules = [
        ('제1항', '기본 자음자 14개가 첫소리로 쓰일 때에는 다음과 같이 적는다.'),
        ('[다만 1]', '‘ㅇ’이 첫소리로 쓰일 때에는 점자로 이를 표기하지 않는다.'),
    ]
    learn = [
        {'title': f'{title}로 된 초성 자음', 'blocks': [
            {'t': 'p', 'text': f'{", ".join(chars)}은 {title}로 적습니다.'},
            {'t': 'cards', 'items': [card(c) for c in chars]},
        ]} for title, chars in GROUPS
    ] + [
        {'title': '모양이 비슷한 초성 자음', 'blocks': [
            {'t': 'cards', 'caption': note,
             'items': [{'name': c, 'cells': cards[c], 'labels': [c], 'line': dots_text(cards[c])} for c in chars]}
            for chars, note in LOOK_ALIKE
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 초성 자음일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 초성 자음을 괄호에 쓰세요.', 'blank': '(        )',
             'items': [{'name': dots_text(cards[c]), 'cells': cards[c], 'labels': None} for c in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 초성 자음을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '빈 점칸에 알맞은 점을 칠하세요. 초성 자음 하나는 한 칸입니다.',
             'items': [{'ask': c, 'cells': 1} for c in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제1장 제1절 첫소리로 쓰인 자음자 (규정집 3쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '기본 자음자는 14개이지만, ㅇ은 첫소리에서 적지 않으므로 점형으로 익힐 초성 자음은 13개입니다.',
            '초성 자음 하나는 점칸 한 칸에 적습니다. 초성 자음의 점형에는 3점이 없습니다.',
            '예) ㄱ → ' + braille(cards['ㄱ']) + ' (4점), ㄴ → ' + braille(cards['ㄴ']) + ' (1·4점)',
            '규정집 표: ' + ', '.join(f'{c} {braille(cards[c])}' for c in RULE_TABLE),
        ],
        learn=learn, practice=practice,
        checks=[
            '첫소리 ㅇ은 점자로 적지 않는다는 것을 안다.',
            '초성 자음 13개의 점형을 읽고 쓸 수 있다.',
            'ㄱ·ㄹ·ㅅ을 점의 높이로 구별할 수 있다.',
            'ㅋ·ㅌ·ㅍ·ㅎ을 빠진 점으로 구별할 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {c}' for i, c in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {c} {braille(cards[c])} {dots_text(cards[c])}' for i, c in enumerate(WRITE_ITEMS, 1))),
        ],
    )
