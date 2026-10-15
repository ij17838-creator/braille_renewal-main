"""영어 3단원 「알파벳 단어 약자」.

근거: 「개정 한국 점자 규정」 제32항(규정집 21쪽), 제37항(24쪽), 「통일영어점자 규정」 10.1절(UEB 규정집 113쪽), 2.6절(15쪽).
점형은 앱 카드에서 가져와 UEB 10.1 표(점자 문자 그대로 실림)와 대조한다.
"""
from common import app_cards, asc, dots_text
from en_common import KO_RULES, STANDING_ALONE, contraction_doc, ko_rule

UNIT_ID = 'en-word'
# UEB 10.1 표 (UEB 규정집 113쪽)
UEB_TABLE = {'but': '⠃', 'can': '⠉', 'do': '⠙', 'every': '⠑', 'from': '⠋', 'go': '⠛', 'have': '⠓', 'just': '⠚',
             'knowledge': '⠅', 'like': '⠇', 'more': '⠍', 'not': '⠝', 'people': '⠏', 'quite': '⠟', 'rather': '⠗',
             'so': '⠎', 'that': '⠞', 'us': '⠥', 'very': '⠧', 'it': '⠭', 'you': '⠽', 'as': '⠵', 'will': '⠺'}
# UEB 10.1 보기 (UEB 규정집 113~115쪽)
UEB_EXAMPLES = {'As You Like It': '⠠⠵ ⠠⠽ ⠠⠇ ⠠⠭', 'peoples': '⠏⠑⠕⠏⠇⠑⠎', 'it\'d': '⠭⠄⠙', 'you\'ll': '⠽⠄⠇⠇'}
# 제37항 표 (규정집 24쪽): 국어 문장 안(로마자표 뒤)에서는 풀어 적는다
KO_TABLE = {'can': 'can', 'do': 'do', 'that': '?at', 'you': 'y\\'}
READ_ITEMS = ['but', 'go', 'it', 'as', 'I do not like that.', 'You can go.']
WRITE_ITEMS = ['from', 'very', 'you', 'people', 'Just do it.', 'So can you.']
RULES = [('UEB 10.1.1', 'Use the alphabetic wordsign when the word it represents is "standing alone". '
                        '(풀이: 낱말이 홀로 쓰일 때 알파벳 단어 약자를 씁니다.)')]


def build():
    letters = {c['letter']: c['dots'] for c in app_cards('en-letter')}
    shape = {c['letter']: next(l for l, d in letters.items() if d == c['dots']) for c in app_cards(UNIT_ID)}
    assert set(letters) - set(shape.values()) == set('aio')  # a, i, o에는 단어 약자가 없다
    assert shape['it'] == 'x' and shape['as'] == 'z'
    assert all(shape[w] == w[0] for w in UEB_TABLE if w not in ('it', 'as'))
    assert len(UEB_TABLE) == 23
    for w, a in KO_TABLE.items():
        assert len(asc(a)) > 1, w
    rows = [('a~j 줄', 'bcdefghj'), ('k~t 줄', 'klmnpqrst'), ('u~z 줄', 'uvwxyz')]
    groups = [(f'{t}의 단어 약자', [w for w in UEB_TABLE if shape[w] in ls],
               '모두 알파벳 한 칸입니다. ' + ', '.join(f'{w}는 {shape[w]}' for w in UEB_TABLE if shape[w] in ls) + '의 점형입니다.')
              for t, ls in rows]
    ko_cards = [{'name': f'국어 문장 안의 {w}', 'cells': asc(a), 'labels': None, 'line': dots_text(asc(a))} for w, a in KO_TABLE.items()]
    return contraction_doc(
        UNIT_ID, table=UEB_TABLE, groups=groups,
        name=lambda w: f'{w} ({shape[w]})',
        look_alike=[
            (['it', ('en-letter', 'x'), 'as', ('en-letter', 'z')], 'it는 x, as는 z의 점형입니다. 첫 글자와 점형의 알파벳이 다르니 따로 외웁니다.'),
            (['will', 'you', 'us'], 'will은 w, you는 y, us는 u의 점형입니다. 홀로 쓰인 한 칸이면 낱말로 읽습니다.'),
        ],
        examples=UEB_EXAMPLES,
        example_note=('「통일영어점자 규정」 10.1절의 보기입니다. 홀로 쓰인 낱말은 한 칸으로 줄이지만, peoples처럼 다른 글자가 붙으면 풀어 적습니다. '
                      'it\'d, you\'ll처럼 아포스트로피 뒤에 d, ll, re, s, t, ve가 붙을 때는 약자를 씁니다 (10.1.2).'),
        extra_learn=[{'title': '한글 문장 안에서는 풀어 적기', 'blocks': [
            {'t': 'p', 'text': '한글 문장 안에서 로마자표 뒤에 이 낱말이 오면 단어 약자를 쓰지 않고 풀어 적습니다 (제37항). '
                               '아래는 규정집 제37항 표의 일부입니다. that의 th, you의 ou는 5단원에서 배우는 묶음 약자입니다.'},
            {'t': 'cards', 'items': ko_cards}]}],
        read=READ_ITEMS, write=WRITE_ITEMS,
        rules=ko_rule('제32항', '제37항') + RULES,
        rule_src=('「개정 한국 점자 규정」 제32항, 제37항 (규정집 21~24쪽), 「통일영어점자 규정」(UEB, 2024) 10.1절 (UEB 규정집 113쪽), '
                  '2.6절 (15쪽)'),
        bullets=[
            '알파벳 23자는 홀로 쓰이면 낱말 하나를 뜻합니다. 예) ⠃ but, ⠉ can, ⠽ you',
            'a, i, o에는 단어 약자가 없습니다. it는 x, as는 z의 점형입니다.',
            STANDING_ALONE,
            '한글 문장 안(로마자표 뒤)에서는 단어 약자를 쓰지 않고 풀어 적습니다 (제37항).',
        ],
        checks=[
            '알파벳 단어 약자 23개를 읽고 쓸 수 있다.',
            'it(x)와 as(z)의 점형을 안다.',
            '홀로 쓰일 때만 단어 약자를 쓴다는 것을 안다.',
            '한글 문장 안에서는 단어 약자를 풀어 적는다는 것을 안다.',
        ],
    )


assert KO_RULES['제37항']
