"""영어 4단원 「온칸 약자」.

근거: 「개정 한국 점자 규정」 제32항(규정집 21쪽), 「통일영어점자 규정」 10.2절(UEB 규정집 116쪽), 10.3절(118쪽).
점형은 앱 카드에서 가져와 UEB 표(점자 문자 그대로 실림)와 대조한다.
"""
from en_common import STANDING_ALONE, cells_of, contraction_doc, ko_rule

UNIT_ID = 'en-strong-word'
# UEB 10.2 표 (116쪽), 10.3 표 (118쪽)
STRONG_WORDSIGN = {'child': '⠡', 'shall': '⠩', 'this': '⠹', 'which': '⠱', 'out': '⠳', 'still': '⠌'}
STRONG_CONTRACTION = {'and': '⠯', 'for': '⠿', 'of': '⠷', 'the': '⠮', 'with': '⠾'}
# UEB 10.3.1 보기 (118~119쪽)
UEB_EXAMPLES = {'roof': '⠗⠕⠷', 'sofa': '⠎⠷⠁', 'tofu': '⠞⠷⠥', 'forgo': '⠿⠛⠕', 'grandad': '⠛⠗⠯⠁⠙', 'thee': '⠮⠑',
                'with a knowledge of and respect for the rules': '⠾ ⠁ ⠅ ⠷ ⠯ ⠗⠑⠎⠏⠑⠉⠞ ⠿ ⠮ ⠗⠥⠇⠑⠎'}
READ_ITEMS = ['this', 'out', 'the', 'sofa', 'for the child', 'out of the box']
WRITE_ITEMS = ['which', 'still', 'and', 'roof', 'This is for you.', 'with the child']
RULES = [
    ('UEB 10.2.1', 'Use the strong wordsign when the word it represents is "standing alone". '
                   '(풀이: child, shall, this, which, out, still은 홀로 쓰일 때 한 칸으로 줄입니다.)'),
    ('UEB 10.3.1', 'Use the strong contraction wherever the letters it represents occur unless other rules limit its use. '
                   '(풀이: and, for, of, the, with는 그 글자들이 나오는 곳이면 어디서나 한 칸으로 줄입니다.)'),
]


def build():
    d = {w: set(cells_of(b)[0]) for w, b in {**STRONG_WORDSIGN, **STRONG_CONTRACTION}.items()}
    # 안내 문장에 적은 사실 확인
    assert all(x & {1, 4} and x & {3, 6} for x in d.values())  # 위·아래 점을 함께 쓴다
    assert {1, 2, 3, 4, 5, 6} - d['of'] == {4} and {1, 2, 3, 4, 5, 6} - d['with'] == {1}
    assert {1, 2, 3, 4, 5, 6} - d['and'] == {5} and d['for'] == {1, 2, 3, 4, 5, 6} and d['the'] == {2, 3, 4, 6}
    assert cells_of('⠸⠌')[1] == sorted(d['still'])  # 빗금 둘째 칸 = still
    return contraction_doc(
        UNIT_ID, table={**STRONG_WORDSIGN, **STRONG_CONTRACTION},
        groups=[
            ('홀로 쓰일 때만 줄이는 약자', list(STRONG_WORDSIGN),
             'child, shall, this, which, out, still은 낱말이 홀로 쓰일 때만 한 칸으로 적습니다.'),
            ('어디서나 줄이는 약자', list(STRONG_CONTRACTION),
             'and, for, of, the, with는 낱말로 쓰일 때도, 다른 낱말 안에 들어 있을 때도 한 칸으로 적습니다.'),
        ],
        look_alike=[
            (['of', 'with'], 'of(1·2·3·5·6점)와 with(2·3·4·5·6점)는 모두 점이 다섯 개입니다. of는 4점, with는 1점이 빠졌습니다.'),
            (['and', 'for', 'the'], 'and는 5점, for는 점 여섯 개 모두, the는 1·5점이 빠진 2·3·4·6점입니다.'),
            (['still', ('en-sign', '/')], 'still(3·4점)은 빗금의 둘째 칸과 같은 점형입니다. 빗금은 앞에 4·5·6점이 있는 두 칸입니다.'),
        ],
        examples=UEB_EXAMPLES,
        example_note=('「통일영어점자 규정」 10.3절의 보기입니다. roof의 of, forgo의 for처럼 낱말 안에 든 글자도 줄입니다. '
                      '여러 약자를 이어 쓰면 칸 수가 크게 줄어듭니다.'),
        read=READ_ITEMS, write=WRITE_ITEMS,
        rules=ko_rule('제32항') + RULES,
        rule_src='「개정 한국 점자 규정」 제32항 (규정집 21쪽), 「통일영어점자 규정」(UEB, 2024) 10.2절 (UEB 규정집 116쪽), 10.3절 (118쪽)',
        bullets=[
            '모두 한 칸을 꽉 채우는(위·아래 점을 함께 쓰는) 약자입니다.',
            'child ⠡, shall ⠩, this ⠹, which ⠱, out ⠳, still ⠌는 홀로 쓰일 때만 씁니다.',
            'and ⠯, for ⠿, of ⠷, the ⠮, with ⠾는 낱말 안에서도 씁니다. 예) roof → ⠗⠕⠷',
            STANDING_ALONE,
        ],
        checks=[
            '온칸 약자 11개를 읽고 쓸 수 있다.',
            'child·shall·this·which·out·still은 홀로 쓰일 때만 줄인다는 것을 안다.',
            'and·for·of·the·with는 낱말 안에서도 줄인다는 것을 안다.',
        ],
    )
