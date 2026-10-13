"""한글 19단원 「쉼표, 가운뎃점, 쌍점, 빗금」. 근거: 제6장 제13절 제49항 (규정집 31~32쪽).

부호 점형은 앱 카드에서, 문장 점형은 저장소 번역 엔진(engine/ko)에서 가져온다.
규정집 표와 보기 문장(점자 ASCII)을 그대로 옮겨 같은지 확인한다.
"""
from common import app_cards, asc, braille, dots_text, ko_cells, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-mark-pause'
MARKS = [',', '·', ':', '/']
NAMES = {',': '쉼표', '·': '가운뎃점', ':': '쌍점', '/': '빗금'}
USE = {',': '같은 자격의 낱말을 늘어놓거나 문장 안에서 잠깐 쉴 때',
       '·': '짝을 이루는 말을 하나로 묶을 때',
       ':': '앞의 말을 풀어 설명할 때',
       '/': '맞서는 말이나 시의 행을 나눌 때'}
RULE_TABLE = {',': '"', '·': '"2', ':': '"1', '/': '_/'}  # 제49항 표 (규정집 31쪽)
# 제49항 보기 문장 (규정집 32쪽)
RULE_SENTENCES = {
    '근면, 검소, 협동은 우리 겨레의 미덕이다.': '@ze*"`@s5,u"`j:bi=z`m"o`@:"nw`eoi?oi4',
    '우리는 그 일의 참·거짓을 따질 겨를도 없었다.': 'm"ocz`@[`o1w`;<5"2@s.o\'!`,i.o1`@:"!iu`sb\'s/i4',
    '문방사우: 종이, 붓, 먹, 벼루': 'eg^7lm"1`.=o"`^m\'"`e?"`^:"m',
    '남반구/북반구': 'c5^3@m_/^ma^3@m',
}
SHOW = ['근면, 검소, 협동은 우리 겨레의 미덕이다.', '문방사우: 종이, 붓, 먹, 벼루', '남반구/북반구']
READ_ITEMS = ['나비, 벌', '봄·가을', '이름: 지수', '남/여']
WRITE_ITEMS = ['오이, 가지', '상·하', '때: 밤', '예/아니요']


def build():
    u = unit_data(UNIT_ID)
    marks = {c['letter']: c['dots'] for c in app_cards(UNIT_ID)}
    initial = {c['letter']: c['dots'] for c in app_cards('ko-initial')}
    # 앱 카드 = 규정집 제49항 표, 엔진 문장 = 규정집 보기
    assert list(marks) == MARKS
    for m, a in RULE_TABLE.items():
        assert marks[m] == asc(a), m
    for t, a in RULE_SENTENCES.items():
        assert ko_cells(t) == reg_cells(a), t
    # 안내 문장에 적은 사실 확인
    assert marks[','] == initial['ㄹ']  # 쉼표와 첫소리 ㄹ은 같은 5점
    assert marks['·'][0] == marks[':'][0] == marks[','][0]  # 가운뎃점·쌍점은 5점으로 시작
    for t in READ_ITEMS + WRITE_ITEMS:
        m = next(ch for ch in t if ch in marks)
        cells = ko_cells(t)
        assert braille(marks[m]) in braille(cells), t

    def mark_card(m):
        return {'name': f'{NAMES[m]} ( {m} )', 'cells': marks[m], 'labels': [m] * len(marks[m]), 'line': dots_text(marks[m])}

    def sent(t):
        return {'name': t, 'cells': ko_cells(t), 'labels': None, 'line': dots_text(ko_cells(t))}

    rules = [('제49항', '문장 부호는 다음과 같이 적는다. 띄어쓰기는 묵자를 따르되, 「한글 맞춤법」의 [부록] 문장 부호의 규정을 준수한다.')]
    learn = [
        {'title': '부호 4개', 'blocks': [
            {'t': 'p', 'text': '쉼표는 한 칸, 가운뎃점·쌍점·빗금은 두 칸입니다. ' + ' '.join(f'{NAMES[m]}는 {USE[m]} 씁니다.' for m in MARKS)},
            {'t': 'cards', 'items': [mark_card(m) for m in MARKS]},
        ]},
        {'title': '헷갈리기 쉬운 점형', 'blocks': [
            {'t': 'cards', 'caption': '쉼표는 첫소리 ㄹ과 같은 5점입니다. 쉼표는 낱말 뒤에 붙고, 뒤에 한 칸을 띄웁니다. 가운뎃점과 쌍점도 5점으로 시작하니 둘째 칸까지 보세요.',
             'items': [mark_card(','), {'name': '첫소리 ㄹ', 'cells': initial['ㄹ'], 'labels': ['ㄹ'], 'line': dots_text(initial['ㄹ'])},
                       mark_card('·'), mark_card(':')]},
        ]},
        {'title': '문장에서 써 보기', 'blocks': [
            {'t': 'p', 'text': '부호는 앞 글자에 붙여 적고, 띄어쓰기는 글자와 같게 합니다. 아래는 규정집의 보기 문장입니다.'},
            {'t': 'cards', 'items': [sent(t) for t in SHOW]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 부호까지 괄호에 쓰세요. 「빈칸」은 띄어쓰기입니다.', 'blank': '(                )',
             'items': [{'name': dots_text(ko_cells(t)), 'cells': ko_cells(t), 'labels': None} for t in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '띄어쓰기도 한 칸입니다. 부호는 앞 글자에 붙여 적으세요.',
             'items': [{'ask': t, 'cells': len(ko_cells(t))} for t in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제6장 제13절 문장 부호 제49항 (규정집 31~32쪽)',
        key=u['teach']['line'],
        intro_bullets=[f'{NAMES[m]}( {m} ) → {braille(marks[m])} ({dots_text(marks[m])})' for m in MARKS] + [
            '부호는 앞 글자에 붙여 적고, 띄어쓰기는 묵자(글자)와 같게 합니다.',
        ],
        learn=learn, practice=practice,
        checks=[
            '쉼표·가운뎃점·쌍점·빗금의 점형을 읽고 쓸 수 있다.',
            '쉼표와 첫소리 ㄹ이 같은 5점이라는 것을 안다.',
            '가운뎃점과 쌍점을 둘째 칸으로 구별할 수 있다.',
        ],
        answers=[
            ('읽기 연습', '    '.join(f'({i}) {t}' for i, t in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', '    '.join(f'({i}) {t} {braille(ko_cells(t))} {dots_text(ko_cells(t))}' for i, t in enumerate(WRITE_ITEMS, 1))),
        ],
    )
