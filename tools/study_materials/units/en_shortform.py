"""영어 8단원 「축어」.

근거: 「개정 한국 점자 규정」 제32항(규정집 21쪽), 「통일영어점자 규정」 10.9절(UEB 규정집 145~153쪽).
점형은 앱 카드에서 가져와 UEB 10.9 표(점자 문자 그대로 실림)와 대조한다.
"""
from en_common import STANDING_ALONE, contraction_doc, ko_rule

UNIT_ID = 'en-shortform'
# UEB 10.9 표 (145~146쪽)
UEB_TABLE = {
    'about': '⠁⠃', 'above': '⠁⠃⠧', 'according': '⠁⠉', 'across': '⠁⠉⠗', 'after': '⠁⠋', 'afternoon': '⠁⠋⠝', 'afterward': '⠁⠋⠺',
    'again': '⠁⠛', 'against': '⠁⠛⠌', 'also': '⠁⠇', 'almost': '⠁⠇⠍', 'already': '⠁⠇⠗', 'altogether': '⠁⠇⠞', 'although': '⠁⠇⠹',
    'always': '⠁⠇⠺', 'blind': '⠃⠇', 'braille': '⠃⠗⠇', 'could': '⠉⠙', 'declare': '⠙⠉⠇', 'declaring': '⠙⠉⠇⠛', 'deceive': '⠙⠉⠧',
    'deceiving': '⠙⠉⠧⠛', 'either': '⠑⠊', 'friend': '⠋⠗', 'first': '⠋⠌', 'good': '⠛⠙', 'great': '⠛⠗⠞', 'him': '⠓⠍',
    'himself': '⠓⠍⠋', 'herself': '⠓⠻⠋', 'immediate': '⠊⠍⠍', 'little': '⠇⠇', 'letter': '⠇⠗', 'myself': '⠍⠽⠋', 'much': '⠍⠡',
    'must': '⠍⠌', 'necessary': '⠝⠑⠉', 'neither': '⠝⠑⠊', 'paid': '⠏⠙', 'perceive': '⠏⠻⠉⠧', 'perceiving': '⠏⠻⠉⠧⠛',
    'perhaps': '⠏⠻⠓', 'quick': '⠟⠅', 'receive': '⠗⠉⠧', 'receiving': '⠗⠉⠧⠛', 'rejoice': '⠗⠚⠉', 'rejoicing': '⠗⠚⠉⠛',
    'said': '⠎⠙', 'such': '⠎⠡', 'today': '⠞⠙', 'together': '⠞⠛⠗', 'tomorrow': '⠞⠍', 'tonight': '⠞⠝', 'itself': '⠭⠋',
    'its': '⠭⠎', 'your': '⠽⠗', 'yourself': '⠽⠗⠋', 'yourselves': '⠽⠗⠧⠎', 'themselves': '⠮⠍⠧⠎', 'children': '⠡⠝',
    'should': '⠩⠙', 'thyself': '⠹⠽⠋', 'ourselves': '⠳⠗⠧⠎', 'would': '⠺⠙', 'because': '⠆⠉', 'before': '⠆⠋', 'behind': '⠆⠓',
    'below': '⠆⠇', 'beneath': '⠆⠝', 'beside': '⠆⠎', 'between': '⠆⠞', 'beyond': '⠆⠽', 'conceive': '⠒⠉⠧',
    'conceiving': '⠒⠉⠧⠛', 'oneself': '⠐⠕⠋'}
# UEB 10.9 보기 (146~153쪽)
UEB_EXAMPLES = {'You should receive your letter tomorrow afternoon.': '⠠⠽ ⠩⠙ ⠗⠉⠧ ⠽⠗ ⠇⠗ ⠞⠍ ⠁⠋⠝⠲',
                'aboveground': '⠁⠃⠧⠛⠗⠨⠙', 'godchildren': '⠛⠕⠙⠡⠝', 'abouts': '⠁⠃⠳⠞⠎'}
READ_ITEMS = ['good', 'little', 'friend', 'today', 'would', 'It was good.']
WRITE_ITEMS = ['about', 'could', 'after', 'quick', 'said', 'You should go today.']
RULES = [
    ('UEB 10.9.1', 'Use the shortform whenever the word it represents is "standing alone", regardless of meaning or pronunciation, '
                   'and regardless of whether the word is used as an ordinary word or as a proper name. '
                   '(풀이: 축어는 낱말이 홀로 쓰이면 뜻이나 발음과 상관없이 씁니다.)'),
    ('UEB 10.9.2', 'Use the shortform within a longer word provided that the longer word is "standing alone" and that the longer word: '
                   '(a) appears on the Shortforms List given in Appendix 1; or (b) satisfies the provisions of rules 10.9.3, 10.9.4 or 10.9.5. '
                   '(풀이: 더 긴 낱말 안의 축어는 그 낱말이 축어 목록[부록 1]에 있거나 정해진 조건에 맞을 때만 씁니다.)'),
]
RANGES = [('a로 시작하는 축어', 'a'), ('b~d로 시작하는 축어', 'bcd'), ('e~l로 시작하는 축어', 'efghijkl'),
          ('m~r로 시작하는 축어', 'mnopqr'), ('s~y로 시작하는 축어', 'stuvwxy')]


def build():
    from common import app_cards
    word = {c['letter']: c['dots'] for c in app_cards('en-word')}
    strong = {c['letter']: c['dots'] for c in app_cards('en-strong-word')}
    assert len(UEB_TABLE) == 75
    # 안내 문장에 적은 사실 확인
    assert UEB_TABLE['its'][0] == UEB_TABLE['itself'][0] == '⠭' and word['it'] == [[1, 3, 4, 6]]
    assert strong['child'] == [[1, 6]] and UEB_TABLE['children'] == '⠡⠝'
    groups = [(t, sorted(w for w in UEB_TABLE if w[0] in ls), '축어는 낱말의 중요한 글자 몇 개만 남겨 적습니다. 남긴 글자에도 약자를 씁니다.')
              for t, ls in RANGES]
    return contraction_doc(
        UNIT_ID, table=UEB_TABLE, groups=groups,
        look_alike=[
            (['its', 'itself', ('en-word', 'it')], 'it은 한 칸(x), its는 it + s, itself는 it + f입니다.'),
            (['children', ('en-strong-word', 'child')], 'children은 child(1·6점) 뒤에 n을 더합니다.'),
            (['about', 'above', 'also', 'always'], 'a로 시작하는 축어는 둘째·셋째 칸으로 구별합니다.'),
        ],
        examples=UEB_EXAMPLES,
        example_note=('「통일영어점자 규정」 10.9절의 보기입니다. aboveground, godchildren은 축어 목록에 있어 축어를 쓰고, '
                      'abouts는 목록에 없어 풀어 적습니다.'),
        read=READ_ITEMS, write=WRITE_ITEMS,
        rules=ko_rule('제32항') + RULES,
        rule_src='「개정 한국 점자 규정」 제32항 (규정집 21쪽), 「통일영어점자 규정」(UEB, 2024) 10.9절 (UEB 규정집 145~153쪽)',
        bullets=[
            '축어 75개는 자주 쓰는 낱말을 두세 칸으로 줄여 적은 것입니다. 예) about → ⠁⠃, good → ⠛⠙',
            '축어 안에도 약자가 들어갑니다. 예) children → ⠡⠝ (child의 ⠡)',
            '더 긴 낱말 안에서는 축어 목록에 있는 낱말일 때만 축어를 씁니다.',
            STANDING_ALONE,
        ],
        checks=[
            '축어 75개 가운데 자주 쓰는 것을 읽고 쓸 수 있다.',
            '축어는 홀로 쓰일 때 쓴다는 것을 안다.',
            '긴 낱말 안에서는 목록에 있을 때만 축어를 쓴다는 것을 안다.',
        ],
    )
