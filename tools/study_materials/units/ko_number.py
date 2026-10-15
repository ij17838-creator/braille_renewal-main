"""한글 2단원 「숫자」. 근거: 제5장 제11절 제40항 (규정집 27쪽).

규정집의 보기는 점자 글꼴(#=수표, a~j=숫자 1~0)로 실려 있어, 아래 RULE_EXAMPLES에 그대로 옮기고
저장소 numbers.json의 점형과 같은지 확인한다.
"""
from common import braille, dots_text, load_json, standard_doc, unit_data

UNIT_ID = 'ko-number'
ASCII = {'#': [3, 4, 5, 6], 'a': [1], 'b': [1, 2], 'c': [1, 4], 'd': [1, 4, 5], 'e': [1, 5],
         'f': [1, 2, 4], 'g': [1, 2, 4, 5], 'h': [1, 2, 5], 'i': [2, 4], 'j': [2, 4, 5]}
# 제40항 보기 (규정집 27쪽, 점자 글꼴 그대로)
RULE_EXAMPLES = {'1': '#a', '2': '#b', '3': '#c', '4': '#d', '5': '#e', '6': '#f', '7': '#g', '8': '#h',
                 '9': '#i', '0': '#j', '10': '#aj', '99': '#ii', '375': '#cge'}

READ_ITEMS = ['4', '9', '0', '8', '31', '506']
WRITE_ITEMS = ['7', '2', '5', '6', '18', '309']
LOOK_ALIKE = [
    (['5', '9'], '점 두 개가 비스듬히 놓였습니다. 5는 1·5점, 9는 2·4점입니다.'),
    (['2', '3'], '점 두 개입니다. 2는 왼쪽 줄 위아래(1·2점), 3은 위쪽 가로(1·4점)입니다.'),
    (['4', '6', '8', '0'], '모두 위쪽 네 점(1·2·4·5점) 가운데 세 점입니다. 빠진 한 점이 어디인지 보세요. 4는 2점, 6은 5점, 8은 4점, 0은 1점이 빠졌습니다.'),
]


def build():
    u = unit_data(UNIT_ID)
    nums = load_json('data', 'common', 'numbers.json')
    prefix = nums['numeric_indicators']['num_prefix']['dots'][0]
    digits = {k: v['dots'][0] for k, v in nums['digits'].items()}

    def cells(number):
        return [prefix] + [digits[ch] for ch in number]

    # 저장소 점형 = 규정집 보기
    for number, asc in RULE_EXAMPLES.items():
        assert cells(number) == [ASCII[ch] for ch in asc], number
    assert nums['numeric_indicators']['num_prefix']['unicode'] == braille([prefix])
    # 안내 문장에 적은 사실 확인
    assert all(set(d) <= {1, 2, 4, 5} for d in digits.values())
    assert digits['5'] == [1, 5] and digits['9'] == [2, 4] and digits['2'] == [1, 2] and digits['3'] == [1, 4]
    assert all({1, 2, 4, 5} - set(digits[n]) == {m} for n, m in {'4': 2, '6': 5, '8': 4, '0': 1}.items())

    def card(number, line=None):
        return {'name': number, 'cells': cells(number), 'labels': ['수표'] + list(number),
                'line': line or f'{dots_text(cells(number))}'}

    order = list('1234567890')
    rules = [('제40항', '숫자는 수표 ⠼을 앞세워 다음과 같이 적는다.')]
    rule_examples = '보기: ' + ', '.join(f'{n} {braille(cells(n))}' for n in order + ['10', '99', '375'])

    learn = [
        {'title': '수표', 'blocks': [
            {'t': 'p', 'text': '수표는 「여기부터 숫자」라는 표시입니다. 숫자를 시작할 때 맨 앞에 적습니다.'},
            {'t': 'cards', 'items': [{'name': '수표', 'cells': [prefix], 'labels': ['수표'], 'line': f'{dots_text([prefix])}. 점칸 아래쪽과 오른쪽 줄을 채운 모양입니다.'}]},
        ]},
        {'title': '숫자 1부터 0까지', 'blocks': [
            {'t': 'p', 'text': '숫자 카드는 수표와 숫자를 함께 보여 줍니다. 숫자의 점형은 모두 점칸 위쪽 네 점(1·2·4·5점) 안에서 만들어집니다.'},
            {'t': 'cards', 'items': [card(n) for n in order]},
        ]},
        {'title': '여러 자리 숫자', 'blocks': [
            {'t': 'p', 'text': '여러 자리 숫자는 맨 앞에 수표를 한 번만 적고, 숫자를 차례로 이어 적습니다. 아래는 규정집 제40항의 보기입니다.'},
            {'t': 'cards', 'items': [card(n) for n in ['10', '99', '375']]},
        ]},
        {'title': '모양이 비슷한 숫자', 'blocks': [
            blk for nums_, note in LOOK_ALIKE for blk in (
                {'t': 'cards', 'caption': note,
                 'items': [{'name': n, 'cells': [digits[n]], 'labels': [n], 'line': dots_text([digits[n]])} for n in nums_]},
            )
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 숫자일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 숫자를 괄호에 쓰세요. 첫 칸은 수표입니다.', 'blank': '(          )',
             'items': [{'name': dots_text(cells(n)), 'cells': cells(n), 'labels': None} for n in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 숫자를 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '수표부터 차례로 칠하세요. 숫자 한 자리마다 한 칸입니다.',
             'items': [{'ask': n, 'cells': len(n) + 1} for n in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제5장 제11절 국어 문장 안의 숫자 (규정집 27쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            f'수표는 {dots_text([prefix])}({braille([prefix])})입니다.',
            '숫자가 시작될 때 맨 앞에 수표를 적습니다. 예) 1 → ⠼⠁',
            '여러 자리 숫자는 맨 앞에 수표를 한 번만 적습니다. 예) 10 → ⠼⠁⠚',
            rule_examples,
        ],
        learn=learn, practice=practice,
        checks=[
            '수표의 점 번호(3·4·5·6점)를 말할 수 있다.',
            '숫자 1부터 0까지 점형을 읽고 쓸 수 있다.',
            '여러 자리 숫자는 맨 앞에 수표를 한 번만 적는다는 것을 안다.',
            '모양이 비슷한 숫자(5와 9, 2와 3, 4·6·8·0)를 구별할 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {n}' for i, n in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {braille(cells(n))} {dots_text(cells(n))}' for i, n in enumerate(WRITE_ITEMS, 1))),
        ],
    )
