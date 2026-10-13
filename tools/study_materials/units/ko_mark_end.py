"""한글 18단원 「마침표, 물음표, 느낌표」. 근거: 제6장 제13절 제49항 (규정집 31~32쪽).

부호 점형은 앱 카드에서, 문장 점형은 저장소 번역 엔진(engine/ko)에서 가져온다.
규정집 표와 보기 문장(점자 ASCII)을 그대로 옮겨 같은지 확인한다.
"""
from common import app_cards, asc, braille, dots_text, ko_cells, load_json, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-mark-end'
MARKS = ['.', '?', '!']
NAMES = {'.': '마침표', '?': '물음표', '!': '느낌표'}
RULE_TABLE = {'.': '4', '?': '8', '!': '6'}  # 제49항 표 (규정집 31쪽)
# 규정집 보기 문장 (제49항 32쪽, 제14항 [붙임] 10쪽, 제16항 [붙임] 12쪽, 제18항 12쪽)
RULE_SENTENCES = {
    '이번에 가시면 언제 돌아오세요?': 'o^)n`$,oe*`).n`iu1<u,n+8',
    '이거 정말 큰일이 났구나!': 'o@s`.]e1`fzo1o`c/@mc6',
    '땅을 팠다.': ',i7!`d</i4',
    '불을 껐다.': '~&!`,@s/i4',
    '비가 왔다.': '~o$`v/i4',
    '그림을 그리고 있다.': '@["o5!`au`o/i4',
}
SHOW = ['그림을 그리고 있다.', '이번에 가시면 언제 돌아오세요?', '이거 정말 큰일이 났구나!']
READ_ITEMS = ['비가 왔다.', '정말?', '불을 껐다.', '와!']
WRITE_ITEMS = ['땅을 팠다.', '어디?', '나비!', '누구니?']


def build():
    u = unit_data(UNIT_ID)
    marks = {c['letter']: c['dots'] for c in app_cards(UNIT_ID)}
    quote = load_json('data', 'ko', 'ko_marks.json')['opening_delimiters']['items']['“']['dots']
    # 앱 카드 = 규정집 제49항 표, 엔진 문장 = 규정집 보기
    assert list(marks) == MARKS
    for m, a in RULE_TABLE.items():
        assert marks[m] == asc(a), m
    for t, a in RULE_SENTENCES.items():
        assert ko_cells(t) == reg_cells(a), t
    # 안내 문장에 적은 사실 확인
    assert marks['?'] == quote == asc('8')  # 물음표와 여는 큰따옴표는 점형이 같다
    for t in READ_ITEMS + WRITE_ITEMS:
        assert ko_cells(t)[-1:] == marks[t[-1]] and [] not in ko_cells(t)[-2:], t  # 부호는 앞 글자에 붙여 적는다

    def mark_card(m):
        return {'name': f'{NAMES[m]} ( {m} )', 'cells': marks[m], 'labels': [m], 'line': dots_text(marks[m])}

    def sent(t):
        return {'name': t, 'cells': ko_cells(t), 'labels': None, 'line': dots_text(ko_cells(t))}

    rules = [('제49항', '문장 부호는 다음과 같이 적는다. 띄어쓰기는 묵자를 따르되, 「한글 맞춤법」의 [부록] 문장 부호의 규정을 준수한다.')]
    learn = [
        {'title': '문장 끝에 쓰는 부호 3개', 'blocks': [
            {'t': 'p', 'text': '마침표는 설명하거나 시키는 문장 끝에, 물음표는 묻는 문장 끝에, 느낌표는 느낌을 나타내는 문장 끝에 적습니다. 세 부호 모두 한 칸입니다.'},
            {'t': 'cards', 'items': [mark_card(m) for m in MARKS]},
        ]},
        {'title': '헷갈리기 쉬운 부호', 'blocks': [
            {'t': 'cards', 'caption': f'물음표와 여는 큰따옴표는 점형이 같습니다({dots_text(marks["?"])}). 물음표는 낱말 뒤 문장 끝에, 여는 큰따옴표는 말이 시작하는 앞에 옵니다.',
             'items': [mark_card('?'), {'name': '여는 큰따옴표 ( “ )', 'cells': quote, 'labels': ['“'], 'line': dots_text(quote)}]},
        ]},
        {'title': '문장에서 써 보기', 'blocks': [
            {'t': 'p', 'text': '부호는 앞 글자에 붙여 적습니다. 낱말 사이는 한 칸 띄웁니다. 아래는 규정집의 보기 문장입니다.'},
            {'t': 'cards', 'items': [sent(t) for t in SHOW]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 문장일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 문장을 부호까지 괄호에 쓰세요. 「빈칸」은 띄어쓰기입니다.', 'blank': '(                )',
             'items': [{'name': dots_text(ko_cells(t)), 'cells': ko_cells(t), 'labels': None} for t in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 문장을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '띄어쓰기도 한 칸입니다. 문장 끝 부호는 앞 글자에 붙여 적으세요.',
             'items': [{'ask': t, 'cells': len(ko_cells(t))} for t in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제6장 제13절 문장 부호 제49항 (규정집 31~32쪽)',
        key=u['teach']['line'],
        intro_bullets=[f'{NAMES[m]}( {m} ) → {braille(marks[m])} ({dots_text(marks[m])})' for m in MARKS] + [
            '문장 부호는 앞 글자에 붙여 적고, 띄어쓰기는 묵자(글자)와 같게 합니다.',
        ],
        learn=learn, practice=practice,
        checks=[
            '마침표·물음표·느낌표의 점형을 읽고 쓸 수 있다.',
            '물음표와 여는 큰따옴표의 점형이 같다는 것을 안다.',
            '문장 끝 부호를 앞 글자에 붙여 적을 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {t}' for i, t in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {t} {braille(ko_cells(t))} {dots_text(ko_cells(t))}' for i, t in enumerate(WRITE_ITEMS, 1))),
        ],
    )
