"""영어 5단원 「온칸 묶음 약자」.

근거: 「개정 한국 점자 규정」 제32항(규정집 21쪽), 「통일영어점자 규정」 10.4절(UEB 규정집 119~122쪽).
점형은 앱 카드에서 가져와 UEB 10.4 표(점자 문자 그대로 실림)와 대조한다.
"""
from en_common import cells_of, contraction_doc, ko_rule

UNIT_ID = 'en-strong-group'
# UEB 10.4 표 (119쪽)
UEB_TABLE = {'ch': '⠡', 'gh': '⠣', 'sh': '⠩', 'th': '⠹', 'wh': '⠱', 'ed': '⠫', 'er': '⠻', 'ou': '⠳', 'ow': '⠪',
             'st': '⠌', 'ing': '⠬', 'ar': '⠜'}
# UEB 10.4 보기 (120~122쪽)
UEB_EXAMPLES = {'cheddar': '⠡⠫⠙⠜', 'cough': '⠉⠳⠣', 'freedom': '⠋⠗⠑⠫⠕⠍', 'mistake': '⠍⠊⠌⠁⠅⠑', 'sheer': '⠩⠑⠻',
                'toward': '⠞⠪⠜⠙', 'wharf': '⠱⠜⠋', 'finger': '⠋⠬⠻', 'sting': '⠌⠬'}
READ_ITEMS = ['chat', 'ship', 'her', 'loud', 'king', 'night']
WRITE_ITEMS = ['bed', 'cow', 'stop', 'car', 'thou', 'sting']
RULES = [
    ('UEB 10.4.1', 'Use the strong groupsign wherever the letters it represents occur unless other rules limit its use. '
                   '(풀이: 이 철자 묶음이 나오면 어디서나 한 칸으로 줄입니다.)'),
    ('UEB 10.4.3', 'Use the strong groupsign for "ing" wherever the letters it represents occur except at the beginning of a word. '
                   '(풀이: ing는 낱말 맨 앞이 아닐 때 줄입니다.)'),
]
SAME = {'ch': 'child', 'sh': 'shall', 'th': 'this', 'wh': 'which', 'ou': 'out', 'st': 'still'}


def build():
    from common import app_cards
    words = {c['letter']: c['dots'] for c in app_cards('en-strong-word')}
    for g, w in SAME.items():
        assert cells_of(UEB_TABLE[g]) == words[w], g  # 4단원 단어 약자와 같은 점형
    d = {g: cells_of(b)[0] for g, b in UEB_TABLE.items()}
    assert (d['ed'], d['er'], d['ow'], d['ar'], d['wh'], d['ou']) == ([1, 2, 4, 6], [1, 2, 4, 5, 6], [2, 4, 6], [3, 4, 5], [1, 5, 6], [1, 2, 5, 6])
    return contraction_doc(
        UNIT_ID, table=UEB_TABLE,
        groups=[
            ('4단원 약자와 점형이 같은 묶음', list(SAME),
             'ch, sh, th, wh, ou, st는 4단원의 child, shall, this, which, out, still과 점형이 같습니다. 홀로 쓰인 한 칸이면 낱말, 낱말 안에 있으면 철자 묶음입니다.'),
            ('그 밖의 묶음', ['gh', 'ed', 'er', 'ow', 'ar', 'ing'],
             'gh, ed, er, ow, ar, ing도 한 칸으로 줄입니다. ing는 낱말 맨 앞에서는 줄이지 않습니다.'),
        ],
        look_alike=[
            (['ch', ('en-strong-word', 'child'), 'st', ('en-strong-word', 'still')],
             '점형이 같습니다. ⠡이 홀로 있으면 child, chat처럼 낱말 안에 있으면 ch입니다.'),
            (['ed', 'er', 'ow', 'ar'], 'ed(1·2·4·6점)와 er(1·2·4·5·6점)는 5점, ow(2·4·6점)와 ar(3·4·5점)는 점의 자리로 구별합니다.'),
            (['wh', 'ou'], 'wh(1·5·6점)와 ou(1·2·5·6점)는 2점으로 구별합니다.'),
        ],
        examples=UEB_EXAMPLES,
        example_note='「통일영어점자 규정」 10.4절의 보기입니다. 한 낱말 안에서 여러 묶음 약자를 함께 씁니다.',
        read=READ_ITEMS, write=WRITE_ITEMS,
        rules=ko_rule('제32항') + RULES,
        rule_src='「개정 한국 점자 규정」 제32항 (규정집 21쪽), 「통일영어점자 규정」(UEB, 2024) 10.4절 (UEB 규정집 119~122쪽)',
        bullets=[
            '자주 쓰는 철자 묶음 12개를 한 칸으로 줄입니다.',
            'ch ⠡, sh ⠩, th ⠹, wh ⠱, ou ⠳, st ⠌는 4단원 약자와 점형이 같습니다.',
            'ing ⠬는 낱말 맨 앞이 아닐 때만 줄입니다. 예) sting → ⠌⠬',
        ],
        checks=[
            '온칸 묶음 약자 12개를 읽고 쓸 수 있다.',
            '같은 점형이 홀로 쓰이면 낱말, 낱말 안에서는 철자 묶음이라는 것을 안다.',
            'ing는 낱말 맨 앞에서 줄이지 않는다는 것을 안다.',
        ],
    )
