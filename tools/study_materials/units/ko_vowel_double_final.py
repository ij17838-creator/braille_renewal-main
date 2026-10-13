"""한글 15단원 「'모음+겹받침' 글자」. 근거: 제2장 제4·5항 (규정집 7~8쪽), 제6절 제15항 [붙임] (규정집 11쪽).

글자 카드는 앱(cardsFor)에서, 낱말 점형은 번역 엔진에서 가져와 규정집 보기(점자 ASCII)와 같은지 확인한다.
쌍받침·겹받침의 앞 받침이 모음과 함께 약자(억·언·얼·열·옥·울·은·을)를 이루면 약자를 쓰고 남은 받침을 뒤에 적는다.
"""
from common import app_cards, braille, cell_labels, dots_text, ko_cells, ko_labeled, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-vowel-double-final'
# 제15항 [붙임] 보기 (규정집 11쪽)
RULE_WORDS = {'꺾다': ',@?ai', '넋': "c?'", '얹다': ')ki', '얽다': 'tai', '젊다': '.t5i', '넓다': 'ctbi', '엷다': '|bi',
              '볶다': '~xai', '붉다': '^&ai', '굶다': '@&5i', '훑다': 'j&8i', '끊다': ',@z0i', '긁다': '@!ai',
              '읊다': '!4i', '끓다': ',@!0i'}
ALLOWED = {f'{k} 약자' for k in '가나다마바사자카타파하것억언얼연열영옥온옹운울은을인'}
GROUPS = [('억 약자가 든 글자', ['얶', '섞', '꺾', '넋']), ('언·얼·열 약자가 든 글자', ['얹', '얽', '얾', '엷', '젊', '넓']),
          ('옥·울 약자가 든 글자', ['볶', '굵', '굶']), ('을 약자가 든 글자', ['끓', '긁', '늙', '흙', '읊'])]
SHOW = ['얽다', '젊다', '꺾다', '끊다']
READ_ITEMS = ['붉다', '굶다', '긁다', '엷다']
WRITE_ITEMS = ['넓다', '볶다', '읊다', '끓다']


def build():
    u = unit_data(UNIT_ID)
    app = {c['letter']: c for c in app_cards(UNIT_ID)}
    assert sorted(app) == sorted(k for _, ks in GROUPS for k in ks)
    for k, c in app.items():
        labels = cell_labels(c)
        assert c['dots'] == ko_cells(k), k
        # 약자 한 칸 + 남은 받침 한 칸으로 끝남
        assert labels[-2].endswith('약자') and labels[-1].startswith('받침'), k
    for w, a in RULE_WORDS.items():
        assert ko_cells(w) == reg_cells(a), w
    for w in SHOW + READ_ITEMS + WRITE_ITEMS:
        assert set(l for l in ko_labeled(w)[1] if l.endswith('약자')) <= ALLOWED, w
    assert ko_labeled('얽')[1] == ['얼 약자', '받침 ㄱ'] and ko_labeled('꺾')[1][-2:] == ['억 약자', '받침 ㄱ']

    def card(k):
        return {'name': k, 'cells': app[k]['dots'], 'labels': cell_labels(app[k]), 'line': dots_text(app[k]['dots'])}

    def word(w):
        cells, labels = ko_labeled(w)
        return {'name': w, 'cells': cells, 'labels': labels, 'line': dots_text(cells)}

    rules = [
        ('제4항', '쌍받침 ‘ㄲ’은 ⠁⠁으로 적고, 쌍받침 ‘ㅆ’은 약자인 ⠌으로 적는다.'),
        ('제5항', '겹받침은 각 받침 글자를 어울러 적는다.'),
        ('제15항 [붙임]', '‘억, 언, 얼, 연, 열, 영, 옥, 온, 옹, 운, 울, 은, 을, 인, 것’이 포함되어 있는 글자에도 약자를 사용하여 적는다.'),
    ]
    learn = [
        {'title': '약자 + 남은 받침', 'blocks': [
            {'t': 'p', 'text': '얽은 ㅓ + ㄹ + ㄱ입니다. 앞의 ‘ㅓ+ㄹ’이 얼 약자가 되므로, 얼 약자를 쓰고 남은 받침 ㄱ을 뒤에 적습니다. 쌍받침 ㄲ도 ㄱ 두 개로 보아, 꺾은 억 약자 + 받침 ㄱ으로 적습니다.'},
            {'t': 'cards', 'items': [card('얽'), card('꺾')]},
        ]},
    ] + [
        {'title': t, 'blocks': [{'t': 'cards', 'items': [card(k) for k in ks if k not in ('얽', '꺾')]}]} for t, ks in GROUPS
    ] + [
        {'title': '규정집 보기 낱말', 'blocks': [
            {'t': 'cards', 'items': [word(w) for w in SHOW]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. 약자 칸 바로 뒤의 받침을 함께 읽어 보세요.', 'blank': '(            )',
             'items': [{'name': dots_text(ko_cells(w)), 'cells': ko_cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '약자를 먼저 적고, 남은 받침을 약자 뒤에 적으세요.',
             'items': [{'ask': w, 'cells': len(ko_cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제2장 제4·5항, 제6절 약자 제15항 [붙임] (규정집 7~11쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            f'얽 → {braille(app["얽"]["dots"])} (얼 약자 + 받침 ㄱ)',
            f'꺾 → {braille(app["꺾"]["dots"])} (된소리표 + ㄱ + 억 약자 + 받침 ㄱ)',
            f'읊 → {braille(app["읊"]["dots"])} (을 약자 + 받침 ㅍ)',
        ],
        learn=learn, practice=practice,
        checks=[
            '겹받침 글자에서 약자가 되는 부분을 찾을 수 있다.',
            '약자 뒤에 남은 받침을 적을 수 있다.',
            '쌍받침 ㄲ도 ㄱ 두 개로 나누어 약자를 쓸 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(ko_cells(w))} {dots_text(ko_cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
