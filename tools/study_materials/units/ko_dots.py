"""한글 1단원 「점의 자리」. 근거: 한국 점자 표기의 기본 원칙 제1·2항 (규정집 1쪽)."""
from common import POS, braille, standard_doc, unit_data

UNIT_ID = 'ko-dots'
READ_ORDER = [3, 5, 1, 6, 2, 4]
WRITE_ORDER = [4, 2, 6, 1, 5, 3]


def build():
    u = unit_data(UNIT_ID)
    cards = u['source']['cards']
    for c in cards:  # 카드의 번호·점·점자 문자가 서로 맞는지 확인
        assert c['dots'] == [int(c['letter'])] and c['pattern'] == braille([c['dots']]), c

    rules = [
        ('제1항', '한국 점자는 한 칸을 구성하는 점 여섯 개(세로 3개, 가로 2개)를 조합하여 만드는 예순세 가지의 점형으로 적는다.'),
        ('제2항', '한 칸을 구성하는 점의 번호는 왼쪽 위에서 아래로 1점, 2점, 3점, 오른쪽 위에서 아래로 4점, 5점, 6점으로 한다.'),
    ]
    learn = [
        {'title': '점칸 한눈에 보기', 'blocks': [
            {'t': 'p', 'text': '아래 그림과 표는 점칸 모양 그대로 점 번호를 적은 것입니다. 3줄 2칸이며 줄마다 왼쪽, 오른쪽 순서로 읽습니다.'},
            {'t': 'big_cell'},
        ]},
        {'title': '여섯 점 카드', 'blocks': [
            {'t': 'cards', 'items': [{'name': f"{c['letter']}점", 'cells': [c['dots']], 'labels': [f"{c['letter']}점"], 'line': c['line']} for c in cards]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 볼록한 점은 몇 점일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점의 자리나 그림을 보고, 그 점의 번호를 괄호에 쓰세요.', 'blank': '(    )점',
             'items': [{'name': POS[n], 'cells': [[n]], 'labels': [POS[n]]} for n in READ_ORDER]},
        ]},
        {'title': '쓰기 연습: 불러 준 점만 찍으세요', 'blocks': [
            {'t': 'write_ex', 'hint': '빈 점칸에서 해당하는 점 하나만 칠하세요. 점판과 점필이나 점자 타자기로 찍어도 됩니다.',
             'items': [{'ask': f'{n}점', 'cells': 1} for n in WRITE_ORDER]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 한국 점자 표기의 기본 원칙 (규정집 1쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '세로로 3개, 가로로 2개, 모두 여섯 점이 한 칸입니다.',
            '왼쪽 줄은 위에서 아래로 1점, 2점, 3점입니다.',
            '오른쪽 줄은 위에서 아래로 4점, 5점, 6점입니다.',
            f"여섯 점이 모두 볼록한 점칸은 {u['teach']['pattern']} 입니다.",
            '이 여섯 점을 조합해 예순세 가지 점형을 만듭니다.',
        ],
        learn=learn, practice=practice,
        checks=[
            '한 칸에 점이 모두 몇 개인지 말할 수 있다. (6개, 세로 3개 · 가로 2개)',
            '왼쪽 줄 위에서부터 1·2·3점, 오른쪽 줄 위에서부터 4·5·6점을 짚을 수 있다.',
            '점 번호를 들으면 그 점 하나만 찍을 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {n}점' for i, n in enumerate(READ_ORDER, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {POS[n]}' for i, n in enumerate(WRITE_ORDER, 1))),
        ],
    )
