"""한글 20단원 「따옴표, 묶음표, 이음표」. 근거: 제6장 제13절 제49항 (규정집 31~33쪽).

부호 점형은 앱 카드에서, 문장 점형은 저장소 번역 엔진(engine/ko)에서 가져온다.
규정집 표와 보기 문장(점자 ASCII)을 그대로 옮겨 같은지 확인한다.
"""
from common import app_cards, asc, braille, dots_text, ko_cells, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-mark-pair'
# 제49항 표 (규정집 31쪽): 부호, 이름, 점자 ASCII
RULE_TABLE = [
    ('“', '여는 큰따옴표', '8'), ('”', '닫는 큰따옴표', '0'), ('‘', '여는 작은따옴표', ',8'), ('’', '닫는 작은따옴표', "0'"),
    ('(', '여는 소괄호', "8'"), (')', '닫는 소괄호', ',0'), ('{', '여는 중괄호', '81'), ('}', '닫는 중괄호', '"0'),
    ('[', '여는 대괄호', '82'), (']', '닫는 대괄호', ';0'),
    ('『', '여는 겹낫표', ';8'), ('』', '닫는 겹낫표', '02'), ('「', '여는 홑낫표', '"8'), ('」', '닫는 홑낫표', '01'),
    ('《', '여는 겹화살괄호', ';7'), ('》', '닫는 겹화살괄호', '72'), ('〈', '여는 홑화살괄호', '"7'), ('〉', '닫는 홑화살괄호', '71'),
    ('—', '줄표', '--'), ('-', '붙임표', '-'), ('~', '물결표', '@9'),
]
GROUPS = [
    ('따옴표', '“”‘’', '남의 말이나 생각을 옮길 때 씁니다.'),
    ('괄호', '(){}[]', '설명을 덧붙이거나 여러 말을 묶을 때 씁니다.'),
    ('낫표와 화살괄호', '『』「」《》〈〉', '책·신문 이름(겹), 노래·작품 이름(홑) 같은 제목을 나타낼 때 씁니다.'),
    ('이음표', '—-~', '줄표는 덧붙이는 말 앞뒤에, 붙임표는 낱말을 이을 때, 물결표는 「몇부터 몇까지」를 나타낼 때 씁니다.'),
]
# 제49항 보기 문장 (규정집 32~33쪽)
RULE_SENTENCES = {
    '국가의 성립 요소 {영토, 국민, 주권}': '@ma$w`,]"ob`+,u`81]hu"`@maeq"`.m@p3"0',
    '이 곡은 베르디가 작곡한 「축배의 노래」이다.': 'o`@xz`^n"[io$`.a@xj3`"8;ma^rw`cu"r01oi4',
    '드디어 서울-호치민의 항로가 열렸다.': 'i[ios`,s&-ju;oeqw`j7"u$`|":/i4',
    '9월 15일~9월 25일': '#ip1`#aeo1@9#ip1`#beo1',
    '예로부터 “민심은 천심이다.”라고 하였다.': '/"u^mhs`8eq,o5z`;),o5oi40"<@u`j<:/i4',
}
SHOW = ['이 곡은 베르디가 작곡한 「축배의 노래」이다.', '드디어 서울-호치민의 항로가 열렸다.', '9월 15일~9월 25일']
READ_ITEMS = ['“네.”', '(웃음)', '「봄」', '서울-부산']
WRITE_ITEMS = ['‘예’', '[주의]', '『구운몽』', '1~3']


def build():
    u = unit_data(UNIT_ID)
    marks = {c['letter']: c['dots'] for c in app_cards(UNIT_ID)}
    names = {m: n for m, n, _ in RULE_TABLE}
    # 앱 카드 = 규정집 제49항 표, 엔진 문장 = 규정집 보기
    assert set(marks) == set(names), sorted(set(marks) ^ set(names))
    for m, _, a in RULE_TABLE:
        assert marks[m] == asc(a), m
    for t, a in RULE_SENTENCES.items():
        assert ko_cells(t) == reg_cells(a), t
    # 안내 문장에 적은 사실 확인
    assert marks['“'] == asc('8') and marks['—'] == marks['-'] * 2
    for t in READ_ITEMS + WRITE_ITEMS:
        assert any(braille(marks[m]) in braille(ko_cells(t)) for m in t if m in marks), t

    def mark_card(m):
        return {'name': f'{m} {names[m]}', 'cells': marks[m], 'labels': [m] * len(marks[m]), 'line': dots_text(marks[m])}

    def sent(t):
        return {'name': t, 'cells': ko_cells(t), 'labels': None, 'line': dots_text(ko_cells(t))}

    rules = [('제49항', '문장 부호는 다음과 같이 적는다. 띄어쓰기는 묵자를 따르되, 「한글 맞춤법」의 [부록] 문장 부호의 규정을 준수한다.')]
    learn = [
        {'title': title, 'blocks': [
            {'t': 'p', 'text': note + (' 여는 표와 닫는 표를 짝지어 적습니다.' if title != '이음표' else '')},
            {'t': 'cards', 'items': [mark_card(m) for m in ms]},
        ]} for title, ms, note in GROUPS
    ] + [
        {'title': '헷갈리기 쉬운 점형', 'blocks': [
            {'t': 'p', 'text': f'여는 큰따옴표는 물음표와 점형이 같습니다({dots_text(marks["“"])}). 줄표는 붙임표({dots_text(marks["-"])})를 두 번 적은 모양입니다.'},
        ]},
        {'title': '문장에서 써 보기', 'blocks': [
            {'t': 'p', 'text': '아래는 규정집의 보기 문장입니다. 여는 표는 뒤 글자에, 닫는 표는 앞 글자에 붙여 적습니다.'},
            {'t': 'cards', 'items': [sent(t) for t in SHOW]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 부호까지 괄호에 쓰세요.', 'blank': '(                )',
             'items': [{'name': dots_text(ko_cells(t)), 'cells': ko_cells(t), 'labels': None} for t in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '여는 표와 닫는 표를 모두 적으세요.',
             'items': [{'ask': t, 'cells': len(ko_cells(t))} for t in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제6장 제13절 문장 부호 제49항 (규정집 31~33쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '따옴표·괄호·낫표·화살괄호는 여는 표와 닫는 표가 짝입니다.',
            '여는 표는 뒤 글자에, 닫는 표는 앞 글자에 붙여 적습니다.',
            '예) “네.” → ' + braille(ko_cells('“네.”')),
        ],
        learn=learn, practice=practice,
        checks=[
            '따옴표와 괄호의 여는 표·닫는 표를 읽고 쓸 수 있다.',
            '낫표와 화살괄호를 구별할 수 있다.',
            '붙임표·줄표·물결표를 읽고 쓸 수 있다.',
        ],
        answers=[
            ('읽기 연습', '    '.join(f'({i}) {t}' for i, t in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', '    '.join(f'({i}) {t} {braille(ko_cells(t))} {dots_text(ko_cells(t))}' for i, t in enumerate(WRITE_ITEMS, 1))),
        ],
    )
