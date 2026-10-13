"""한글 22단원 「문장 부호가 들어 있는 문장 쓰기 연습」. 근거: 제6장 제13절 제49항 (규정집 31쪽)과 18~21단원의 각 항.

부호 점형은 저장소 데이터(ko_marks.json)에서, 문장 점형은 저장소 번역 엔진(engine/ko)에서 가져온다.
보기 문장은 규정집 보기(점자 ASCII)를 그대로 옮겨 엔진 결과와 같은지 확인한다.
허락 대기 중인 점형(ㅚ, 받침 ㅋ·ㅌ·ㅍ, 쌍받침·겹받침)이 든 문장은 쓰지 않는다.
"""
from common import asc, braille, dots_text, ko_cells, load_json, pending_jamo, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-sentence'
# 제49항 보기 문장 (규정집 32~33쪽)
RULE_SENTENCES = {
    '이번에 가시면 언제 돌아오세요?': 'o^)n`$,oe*`).n`iu1<u,n+8',
    '근면, 검소, 협동은 우리 겨레의 미덕이다.': '@ze*"`@s5,u"`j:bi=z`m"o`@:"nw`eoi?oi4',
    '예로부터 “민심은 천심이다.”라고 하였다.': '/"u^mhs`8eq,o5z`;),o5oi40"<@u`j<:/i4',
    '이 곡은 베르디가 작곡한 「축배의 노래」이다.': 'o`@xz`^n"[io$`.a@xj3`"8;ma^rw`cu"r01oi4',
}
SHOW = list(RULE_SENTENCES)
READ_ITEMS = ['어디 가니?', '“안녕!”', '봄·여름·가을·겨울', '사과, 배, 포도를 샀다.']
WRITE_ITEMS = ['정말 좋아요!', '엄마, 고마워요.', '누가 왔니?', '나는 「어린 왕자」를 좋아해.']
# 표에 넣는 부호: (이름, 부호, 규정집 점자 ASCII) — 제49항 표 (규정집 31~32쪽)
TABLE = [
    ('마침표', '.', '4'), ('물음표', '?', '8'), ('느낌표', '!', '6'), ('쉼표', ',', '"'), ('가운뎃점', '·', '"2'),
    ('쌍점', ':', '"1'), ('빗금', '/', '_/'), ('여는 큰따옴표', '“', '8'), ('닫는 큰따옴표', '”', '0'),
    ('여는 작은따옴표', '‘', ',8'), ('닫는 작은따옴표', '’', "0'"), ('여는 홑낫표', '「', '"8'), ('닫는 홑낫표', '」', '01'),
    ('붙임표', '-', '-'),
]


def build():
    u = unit_data(UNIT_ID)
    marks = {}
    for group in load_json('data', 'ko', 'ko_marks.json').values():
        if isinstance(group, dict) and 'items' in group:
            for k, v in group['items'].items():
                marks.setdefault(k, v['dots'])
    # 저장소 부호 = 규정집 표, 엔진 문장 = 규정집 보기
    for name, m, a in TABLE:
        assert marks[m] == asc(a), name
    for t, a in RULE_SENTENCES.items():
        assert ko_cells(t) == reg_cells(a), t
    for t in SHOW + READ_ITEMS + WRITE_ITEMS:
        assert not pending_jamo(t), t
    # 안내 문장에 적은 사실 확인: 부호는 앞 글자에 붙고, 낱말 사이 빈칸은 글자와 같다
    for t in READ_ITEMS + WRITE_ITEMS:
        assert ko_cells(t).count([]) == t.count(' '), t

    def sent(t):
        return {'name': t, 'cells': ko_cells(t), 'labels': None, 'line': dots_text(ko_cells(t))}

    rows = [[name, m, braille(marks[m]), dots_text(marks[m]).replace(' ', '')] for name, m, _ in TABLE]
    rules = [('제49항', '문장 부호는 다음과 같이 적는다. 띄어쓰기는 묵자를 따르되, 「한글 맞춤법」의 [부록] 문장 부호의 규정을 준수한다.')]
    learn = [
        {'title': '지금까지 배운 문장 부호', 'blocks': [
            {'t': 'p', 'text': '18~21단원에서 배운 부호 가운데 자주 쓰는 것입니다. 물음표와 여는 큰따옴표는 점형이 같으므로, 문장 끝인지 말이 시작하는 앞인지로 구별합니다.'},
            {'t': 'table', 'caption': '자주 쓰는 문장 부호', 'head': ['이름', '부호', '점자', '점 번호'], 'rows': rows},
        ]},
        {'title': '규정집 보기 문장', 'blocks': [
            {'t': 'p', 'text': '띄어쓰기는 글자(묵자)와 같습니다. 마침표·물음표·쉼표 같은 부호는 앞 글자에 붙여 적고, 따옴표와 홑낫표는 감싸는 말에 붙여 적습니다.'},
            {'t': 'cards', 'items': [sent(t) for t in SHOW]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 문장일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 문장을 부호까지 괄호에 쓰세요. 「빈칸」은 띄어쓰기입니다.', 'blank': '(                )',
             'items': [{'name': dots_text(ko_cells(t)), 'cells': ko_cells(t), 'labels': None} for t in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 문장을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '띄어쓰기는 글자와 같게 하고, 부호는 앞이나 뒤 글자에 붙여 적으세요.',
             'items': [{'ask': t, 'cells': len(ko_cells(t))} for t in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제6장 제13절 문장 부호 제49항 (규정집 31쪽), 18~21단원의 각 항',
        key=u['teach']['line'],
        intro_bullets=[
            '띄어쓰기는 글자(묵자)와 같게 합니다.',
            '마침표·물음표·느낌표·쉼표는 앞 글자에 붙여 적습니다. 예) 어디 가니? → ' + braille(ko_cells('어디 가니?')),
            '따옴표와 홑낫표는 감싸는 말 앞뒤에 붙여 적습니다.',
            '물음표와 여는 큰따옴표는 점형이 같습니다(' + dots_text(marks['?']) + ').',
        ],
        learn=learn, practice=practice,
        checks=[
            '자주 쓰는 문장 부호의 점형을 읽고 쓸 수 있다.',
            '부호가 든 문장을 띄어쓰기에 맞게 읽을 수 있다.',
            '부호를 넣어 짧은 문장을 점자로 적을 수 있다.',
        ],
        answers=[
            ('읽기 연습', '    '.join(f'({i}) {t}' for i, t in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', '    '.join(f'({i}) {t} {braille(ko_cells(t))} {dots_text(ko_cells(t))}' for i, t in enumerate(WRITE_ITEMS, 1))),
        ],
    )
