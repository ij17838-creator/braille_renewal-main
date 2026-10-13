"""한글 21단원 「드러냄표, 안드러냄표, 기타 부호」.
근거: 제49항 표, 제53항 줄임표, 제56항 드러냄표, 제57·58항 숨김표·빠짐표, 제59~62항 기타 부호 (규정집 31~40쪽).

부호 점형은 앱 카드에서, 문장 점형은 저장소 번역 엔진(engine/ko)에서 가져온다.
규정집 표와 보기(점자 ASCII)를 그대로 옮겨 같은지 확인한다.
"""
from common import app_cards, asc, braille, dots_text, ko_cells, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-mark-etc'
# 부호, 이름, 규정집 점자 ASCII, 항
RULE_TABLE = [
    ('…', '줄임표', ',,,', '제49·53항'), ('_', '드러냄표·밑줄(앞)', ',-', '제49·56항'),
    ('○', '숨김표(동그라미)', '_0l', '제49·57항'), ('×', '숨김표(가위표)', '_xl', '제49·57항'),
    ('△', '숨김표(세모)', '_+l', '제49·57항'), ('□', '빠짐표', '_7l', '제49·58항'),
    (';', '쌍반점', ';2', '제59항'), ('*', '별표', '"9', '제60항'), ("'", '아포스트로피', "'", '제61항'), ('〃', '상동 기호', '00', '제62항'),
]
GROUPS = [
    ('줄임표', ['…'], '할 말을 줄이거나 말이 없음을 나타낼 때 씁니다. 6점 세 칸입니다.'),
    ('드러냄표와 밑줄', ['_'], '강조할 말 앞에 ⠠⠤, 뒤에 ⠤⠄을 적어 묶습니다(제56항). 앱 카드에는 앞 표시만 있습니다.'),
    ('숨김표와 빠짐표', ['○', '×', '△', '□'], '숨기거나 빠진 글자 자리에 씁니다. 모두 4·5·6점으로 시작해 1·2·3점으로 끝나고, 가운데 칸으로 구별합니다.'),
    ('그 밖의 부호', [';', '*', "'", '〃'], '쌍반점은 앞은 붙이고 뒤는 띄어 씁니다. 별표는 앞뒤를 띄어 씁니다. 상동 기호는 「위와 같음」을 나타냅니다.'),
]
# 규정집 보기 (제57·62항, 제49항 보기)
RULE_SENTENCES = {
    '모집 인원: ○명': 'eu.ob`qp3"1`_0le]',
    '김○○ 씨': '@o5_00l`,,o',
    '이 ×××야!': 'o`_xxxl>6',
    '△△도서관': '_++liu,s@v3',
    '제2 〃': '.n#b`00',
}
CLOSE_UNDERLINE = "-'"  # 제56항: 드러냄표 뒤 표시 (앱 데이터에는 없음)
READ_ITEMS = ['이 ××야!', '제3 〃', '네…', '박○○']
WRITE_ITEMS = ['□□□', '음…', '제5 〃', '김○○ 씨']


def build():
    u = unit_data(UNIT_ID)
    marks = {c['letter']: c['dots'] for c in app_cards(UNIT_ID)}
    names = {m: n for m, n, _, _ in RULE_TABLE}
    # 앱 카드 = 규정집 표, 엔진 문장 = 규정집 보기
    assert set(marks) == set(names), sorted(set(marks) ^ set(names))
    for m, _, a, _ in RULE_TABLE:
        assert marks[m] == asc(a), m
    for t, a in RULE_SENTENCES.items():
        assert ko_cells(t) == reg_cells(a), t
    # 안내 문장에 적은 사실 확인
    for m in '○×△□':
        assert marks[m][0] == [4, 5, 6] and marks[m][-1] == [1, 2, 3] and len(marks[m]) == 3
    assert marks['…'] == [[6]] * 3 and braille(marks['_']) == '⠠⠤' and braille(asc(CLOSE_UNDERLINE)) == '⠤⠄'
    assert ko_cells('김○○ 씨')[3:7] == [marks['○'][0], marks['○'][1], marks['○'][1], marks['○'][2]]  # 여러 개면 가운데 칸만 늘어난다
    for t in READ_ITEMS + WRITE_ITEMS:
        assert any(braille(marks[m]) in braille(ko_cells(t)) or m in '○×△□' for m in t if m in marks), t

    def mark_card(m):
        return {'name': f'{m} {names[m]}', 'cells': marks[m], 'labels': [m] * len(marks[m]), 'line': dots_text(marks[m])}

    def sent(t):
        return {'name': t, 'cells': ko_cells(t), 'labels': None, 'line': dots_text(ko_cells(t))}

    rules = [
        ('제53항', '가운뎃점으로 쓴 줄임표(……, …)는 ⠠⠠⠠으로, 마침표로 쓴 줄임표(......, ...)는 ⠲⠲⠲으로 적는다.'),
        ('제56항', '드러냄표나 밑줄로 강조된 글자체는 ⠠⠤ ⠤⠄으로 … 묶어 나타낸다.'),
        ('제57항', '숨김표가 여러 개 붙어 나올 때에는 ⠸과 ⠇ 사이에 해당 숨김표의 점형을 묵자의 개수만큼 적어 나타낸다.'),
        ('제58항', '빠짐표가 여러 개 붙어 나올 때에는 ⠸과 ⠇ 사이에 ⠶을 묵자의 개수만큼 적어 나타낸다.'),
        ('제59항', '쌍반점(;)은 ⠰⠆으로 적으며, 앞은 붙여 쓰고 뒤는 한 칸 띄어 쓴다.'),
        ('제60항', '별표(*)와 참고표(※)는 ⠐⠔으로 적고, 앞뒤를 한 칸씩 띄어 쓴다.'),
        ('제61항', '아포스트로피(’)는 ⠄으로 적는다.'),
        ('제62항', '상동 기호(〃)는 ⠴⠴으로 적는다.'),
    ]
    assert asc(',,,') == marks['…'] and asc('_') == [marks['○'][0]] and asc('l') == [marks['○'][2]] and asc('7') == [marks['□'][1]]
    assert asc(';2') == marks[';'] and asc('"9') == marks['*'] and asc("'") == marks["'"] and asc('00') == marks['〃']
    learn = [
        {'title': title, 'blocks': [{'t': 'p', 'text': note}, {'t': 'cards', 'items': [mark_card(m) for m in ms]}]}
        for title, ms, note in GROUPS
    ] + [
        {'title': '문장에서 써 보기', 'blocks': [
            {'t': 'p', 'text': '숨김표가 여러 개면 4·5·6점과 1·2·3점 사이에 가운데 칸만 개수만큼 적습니다. 아래는 규정집의 보기입니다.'},
            {'t': 'cards', 'items': [sent(t) for t in ['모집 인원: ○명', '김○○ 씨', '제2 〃']]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 부호까지 괄호에 쓰세요.', 'blank': '(                )',
             'items': [{'name': dots_text(ko_cells(t)), 'cells': ko_cells(t), 'labels': None} for t in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '숨김표·빠짐표가 여러 개면 가운데 칸만 늘려 적으세요.',
             'items': [{'ask': t, 'cells': len(ko_cells(t))} for t in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제6장 제13절 문장 부호 제49·53·56~58항, 제14절 기타 부호 제59~62항 (규정집 31~40쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '줄임표 ' + braille(marks['…']) + ', 드러냄표 ' + braille(marks['_']) + ' … ⠤⠄',
            '숨김표 ○ ' + braille(marks['○']) + ', × ' + braille(marks['×']) + ', △ ' + braille(marks['△']) + ', 빠짐표 □ ' + braille(marks['□']),
            '쌍반점 ' + braille(marks[';']) + ', 별표 ' + braille(marks['*']) + ', 아포스트로피 ' + braille(marks["'"]) + ', 상동 기호 ' + braille(marks['〃']),
        ],
        learn=learn, practice=practice,
        checks=[
            '줄임표와 드러냄표를 읽고 쓸 수 있다.',
            '숨김표 ○·×·△와 빠짐표 □를 가운데 칸으로 구별할 수 있다.',
            '쌍반점·별표·아포스트로피·상동 기호를 읽을 수 있다.',
        ],
        answers=[
            ('읽기 연습', '    '.join(f'({i}) {t}' for i, t in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', '    '.join(f'({i}) {t} {braille(ko_cells(t))} {dots_text(ko_cells(t))}' for i, t in enumerate(WRITE_ITEMS, 1))),
        ],
    )
