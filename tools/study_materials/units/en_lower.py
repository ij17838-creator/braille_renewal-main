"""영어 6단원 「하위 약자」.

근거: 「개정 한국 점자 규정」 제32항(규정집 21쪽), 제37항 [붙임](25쪽),
「통일영어점자 규정」 10.5절(UEB 규정집 122~126쪽), 10.6절(126~134쪽).
점형은 앱 카드에서 가져와 UEB 표(점자 문자 그대로 실림)와 대조한다.
"""
from common import app_cards
from en_common import STANDING_ALONE, cells_of, contraction_doc, ko_rule

UNIT_ID = 'en-lower'
# UEB 10.5 표 (122~123쪽), 10.6 표 (126쪽)
LOWER_WORDSIGN = {'be': '⠆', 'enough': '⠢', 'were': '⠶', 'his': '⠦', 'in': '⠔', 'was': '⠴'}
LOWER_GROUPSIGN = {'ea': '⠂', 'be': '⠆', 'bb': '⠆', 'con': '⠒', 'cc': '⠒', 'dis': '⠲', 'en': '⠢', 'ff': '⠖', 'gg': '⠶', 'in': '⠔'}
# UEB 10.5·10.6 보기 (123~134쪽)
UEB_EXAMPLES = {'to be': '⠞⠕ ⠆', 'it was enough': '⠭ ⠴ ⠢', 'In or out?': '⠠⠔ ⠕⠗ ⠳⠦', 'rabbi': '⠗⠁⠆⠊',
                'deny': '⠙⠢⠽', 'head': '⠓⠂⠙', 'muffin': '⠍⠥⠖⠔', 'dislike': '⠲⠇⠊⠅⠑', 'tea': '⠞⠑⠁'}
READ_ITEMS = ['his', 'were', 'head', 'muffin', 'dislike', 'to be']
WRITE_ITEMS = ['was', 'enough', 'create', 'begin', 'concept', 'into']
# 같은 점형의 영어 문장 부호 (2단원)
SAME_MARK = {'ea': ',', 'bb': ';', 'cc': ':', 'dis': '.', 'ff': '!', 'his': '?', 'was': '”'}
RULES = [
    ('UEB 10.5.1', 'Use the lower wordsign for "be", "were", "his" or "was" when the word it represents is "standing alone". '
                   'However, the lower wordsign is not used when in contact with any punctuation sign, including the hyphen and dash, '
                   'that has only lower dots. (풀이: be, were, his, was는 홀로 쓰일 때 줄이되, 아래쪽 점만 있는 문장 부호에 붙으면 풀어 씁니다.)'),
    ('UEB 10.6.1', 'Use the lower groupsign for "be", "con" or "dis" when the letters it represents form the first syllable of a word. '
                   '(풀이: be, con, dis는 낱말의 첫 음절일 때 줄입니다.)'),
    ('UEB 10.6.5', 'Use the lower groupsign for "ea", "bb", "cc", "ff", or "gg" when the letters it represents are both preceded and '
                   'followed by a letter, a contraction, a modified letter or a ligatured letter unless other rules limit its use. '
                   '(풀이: ea, bb, cc, ff, gg는 앞뒤에 글자가 있을 때, 곧 낱말 가운데에서만 줄입니다.)'),
    ('UEB 10.6.8', 'Use the lower groupsign for "en" or "in" wherever the letters it represents occur unless other rules limit its use. '
                   '(풀이: en, in은 어디서나 줄입니다.)'),
]


def build():
    marks = {c['letter']: c['dots'] for c in app_cards('en-sign')}
    table = {**LOWER_GROUPSIGN, **LOWER_WORDSIGN}
    for k, m in SAME_MARK.items():
        assert cells_of(table[k]) == marks[m], k
    assert all(not set(cells_of(b)[0]) & {1, 4} for b in table.values())  # 위쪽 점(1·4점)이 없다
    assert table['were'] == table['gg'] and table['en'] == table['enough'] and table['be'] == table['bb']
    return contraction_doc(
        UNIT_ID, table=table,
        groups=[
            ('홀로 쓰일 때 줄이는 단어 약자', ['be', 'were', 'his', 'was', 'enough', 'in'],
             'be, were, his, was, enough, in은 홀로 쓰일 때 한 칸으로 적습니다. be, were, his, was는 아래쪽 점만 있는 문장 부호(따옴표 포함)에 붙으면 풀어 씁니다.'),
            ('낱말 첫 음절에 쓰는 묶음 약자', ['con', 'dis'],
             'be, con, dis가 낱말의 첫 음절이면 줄여 적습니다. 예) begin, concept, dislike'),
            ('어디서나 쓰는 묶음 약자', ['en'],
             'en과 in은 낱말 어디에 있어도 줄여 적습니다. 예) deny, into'),
            ('낱말 가운데에서만 쓰는 묶음 약자', ['ea', 'bb', 'cc', 'ff', 'gg'],
             'ea, bb, cc, ff, gg는 앞뒤에 글자가 있을 때만 줄입니다. 그래서 tea처럼 낱말 끝에 오면 줄이지 않습니다.'),
        ],
        look_alike=[
            ([k if i == 0 else ('en-sign', SAME_MARK[k]) for k in ks for i in (0, 1)],
             cap) for ks, cap in [
                (['ea', 'bb', 'cc'], 'ea는 쉼표, bb·be는 쌍반점, cc·con은 쌍점과 점형이 같습니다. 낱말 가운데 있으면 약자, 낱말 뒤에 붙으면 문장 부호입니다.'),
                (['dis', 'ff'], 'dis는 마침표, ff는 느낌표와 점형이 같습니다.'),
                (['his', 'was'], 'his는 물음표·여는 큰따옴표, was는 닫는 큰따옴표와 점형이 같습니다.'),
            ]
        ] + [(['were', 'gg', 'en', 'enough'], '같은 점형이 두 가지로 쓰입니다. 홀로 쓰이면 were·enough, 낱말 안에서는 gg·en입니다.')],
        examples=UEB_EXAMPLES,
        example_note='「통일영어점자 규정」 10.5절과 10.6절의 보기입니다. 칸의 아래쪽 점만 쓰는 약자이므로, 위쪽 점이 있는 칸과 함께 읽어 위치를 잡습니다.',
        read=READ_ITEMS, write=WRITE_ITEMS,
        rules=ko_rule('제32항', '제37항 [붙임]') + RULES,
        rule_src=('「개정 한국 점자 규정」 제32항, 제37항 [붙임] (규정집 21~25쪽), 「통일영어점자 규정」(UEB, 2024) 10.5절 (UEB 규정집 122~126쪽), '
                  '10.6절 (126~134쪽)'),
        bullets=[
            '하위 약자는 칸의 아래쪽 점(2·3·5·6점)만 씁니다.',
            '단어 약자: be ⠆, enough ⠢, were ⠶, his ⠦, in ⠔, was ⠴ (홀로 쓰일 때)',
            '묶음 약자: be·con·dis(첫 음절), en·in(어디서나), ea·bb·cc·ff·gg(낱말 가운데)',
            '영어 문장 부호와 점형이 같은 것이 많으니 낱말 안의 자리로 구별합니다.',
            '한글 문장 안에서는 be, enough, his, in, was, were를 줄이지 않고 풀어 적습니다 (제37항 [붙임]).',
            STANDING_ALONE,
        ],
        checks=[
            '하위 약자 14개를 읽고 쓸 수 있다.',
            '단어 약자와 묶음 약자가 쓰이는 자리(홀로, 첫 음절, 어디서나, 낱말 가운데)를 구별할 수 있다.',
            '문장 부호와 점형이 같은 하위 약자를 자리로 구별할 수 있다.',
        ],
    )
