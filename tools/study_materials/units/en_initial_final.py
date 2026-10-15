"""영어 7단원 「어두·어미 묶음 약자」.

근거: 「개정 한국 점자 규정」 제32항(규정집 21쪽), 「통일영어점자 규정」 10.7절(UEB 규정집 134~142쪽), 10.8절(142~145쪽).
점형은 앱 카드에서 가져와 UEB 표(점자 문자 그대로 실림)와 대조한다.
"""
from common import app_cards
from en_common import cells_of, contraction_doc, ko_rule

UNIT_ID = 'en-initial-final'
# UEB 10.7 표 (134~135쪽)
INITIAL = {'upon': '⠘⠥', 'these': '⠘⠮', 'those': '⠘⠹', 'whose': '⠘⠱', 'word': '⠘⠺',
           'cannot': '⠸⠉', 'had': '⠸⠓', 'many': '⠸⠍', 'spirit': '⠸⠎', 'their': '⠸⠮', 'world': '⠸⠺',
           'day': '⠐⠙', 'ever': '⠐⠑', 'father': '⠐⠋', 'here': '⠐⠓', 'know': '⠐⠅', 'lord': '⠐⠇', 'mother': '⠐⠍',
           'name': '⠐⠝', 'one': '⠐⠕', 'part': '⠐⠏', 'question': '⠐⠟', 'right': '⠐⠗', 'some': '⠐⠎', 'time': '⠐⠞',
           'under': '⠐⠥', 'young': '⠐⠽', 'there': '⠐⠮', 'character': '⠐⠡', 'through': '⠐⠹', 'where': '⠐⠱',
           'ought': '⠐⠳', 'work': '⠐⠺'}
# UEB 10.8 표 (142쪽)
FINAL = {'ound': '⠨⠙', 'ance': '⠨⠑', 'sion': '⠨⠝', 'less': '⠨⠎', 'ount': '⠨⠞',
         'ence': '⠰⠑', 'ong': '⠰⠛', 'ful': '⠰⠇', 'tion': '⠰⠝', 'ness': '⠰⠎', 'ment': '⠰⠞', 'ity': '⠰⠽'}
# UEB 10.7·10.8 보기 (135~145쪽)
UEB_EXAMPLES = {'upon these shores': '⠘⠥ ⠘⠮ ⠩⠕⠗⠑⠎', 'knowing': '⠐⠅⠬', 'working': '⠐⠺⠬', 'youngest': '⠐⠽⠑⠌',
                'somebody': '⠐⠎⠃⠕⠙⠽', 'sound': '⠎⠨⠙', 'amount': '⠁⠍⠨⠞', 'unless': '⠥⠝⠨⠎', 'cement': '⠉⠑⠰⠞'}
READ_ITEMS = ['day', 'one', 'these', 'many', 'party', 'found']
WRITE_ITEMS = ['time', 'some', 'cannot', 'pity', 'nation', 'useful']
PREFIX = {(5,): '5점', (4, 5): '4·5점', (4, 5, 6): '4·5·6점', (4, 6): '4·6점', (5, 6): '5·6점'}
RULES = [
    ('UEB 10.7.1', 'Use the initial-letter contraction as a wordsign and wherever the letters it represents occur; except for the '
                   'specific provisions given below; and unless other rules limit its use. '
                   '(풀이: 어두 약자는 낱말로도, 낱말 안에서도 씁니다.)'),
    ('UEB 10.8.1', 'Use the final-letter groupsign when the letters it represents follow a letter, a contraction, a modified letter '
                   'or a ligatured letter unless other rules limit its use. (풀이: 어미 묶음 약자는 앞에 글자가 있을 때, 곧 낱말 맨 앞이 아닐 때 씁니다.)'),
]


def build():
    pre = {w: tuple(cells_of(b)[0]) for w, b in {**INITIAL, **FINAL}.items()}
    groups = []
    for p, name in PREFIX.items():
        ws = [w for w in pre if pre[w] == p]
        kind = '어두 약자' if ws[0] in INITIAL else '어미 묶음 약자'
        groups.append((f'{name}을 앞에 둔 {kind}', ws,
                       f'{name} 뒤에 둘째 칸을 적습니다. 둘째 칸은 대개 낱말의 첫 글자({", ".join(ws[:3])} …)입니다.'
                       if kind == '어두 약자' else f'{name} 뒤에 둘째 칸을 적습니다. 둘째 칸은 철자 묶음의 마지막 글자입니다.'))
    assert {pre[w] for w in INITIAL} == {(5,), (4, 5), (4, 5, 6)} and {pre[w] for w in FINAL} == {(4, 6), (5, 6)}
    letters = {c['letter']: c['dots'] for c in app_cards('en-letter')}
    assert all(cells_of(b)[1] == letters[w[-1]][0] for w, b in FINAL.items())  # 둘째 칸 = 마지막 글자
    assert len(INITIAL) == 33 and len(FINAL) == 12
    return contraction_doc(
        UNIT_ID, table={**INITIAL, **FINAL}, groups=groups,
        look_alike=[
            (['some', 'less', 'ness', 'spirit'], '둘째 칸이 모두 s(2·3·4점)입니다. 첫째 칸으로 구별합니다. 5점 some, 4·6점 less, 5·6점 ness, 4·5·6점 spirit'),
            (['time', 'ount', 'ment'], '둘째 칸이 모두 t(2·3·4·5점)입니다. 5점 time, 4·6점 ount, 5·6점 ment'),
            (['through', 'those'], '둘째 칸이 모두 th(1·4·5·6점)입니다. 5점 through, 4·5점 those'),
        ],
        examples=UEB_EXAMPLES,
        example_note=('「통일영어점자 규정」 10.7절과 10.8절의 보기입니다. 어두 약자는 knowing, somebody처럼 긴 낱말 안에서도 쓰고, '
                      '어미 묶음 약자는 sound, amount처럼 앞에 글자가 있을 때 씁니다.'),
        read=READ_ITEMS, write=WRITE_ITEMS,
        rules=ko_rule('제32항') + RULES,
        rule_src='「개정 한국 점자 규정」 제32항 (규정집 21쪽), 「통일영어점자 규정」(UEB, 2024) 10.7절 (UEB 규정집 134~142쪽), 10.8절 (142~145쪽)',
        bullets=[
            '어두 약자: 5점, 4·5점, 4·5·6점 뒤에 한 칸을 더해 낱말을 두 칸으로 줄입니다. 예) day → ⠐⠙',
            '어미 묶음 약자: 4·6점, 5·6점 뒤에 한 칸을 더해 낱말 끝 철자를 두 칸으로 줄입니다. 예) sound → ⠎⠨⠙',
            '어두 약자는 낱말로도, 낱말 안에서도 씁니다. 어미 묶음 약자는 낱말 맨 앞에는 쓰지 않습니다.',
            '둘째 칸이 같은 약자가 많으니 첫째 칸의 점을 꼭 확인합니다.',
        ],
        checks=[
            '어두 약자 33개와 어미 묶음 약자 12개를 읽고 쓸 수 있다.',
            '첫째 칸(5점, 4·5점, 4·5·6점, 4·6점, 5·6점)으로 약자를 구별할 수 있다.',
            '어미 묶음 약자는 낱말 맨 앞에 쓰지 않는다는 것을 안다.',
        ],
    )
