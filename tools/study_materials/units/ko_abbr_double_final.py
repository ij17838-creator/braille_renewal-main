"""한글 16단원 「'약자+겹받침' 글자」. 근거: 제2장 제4·5항 (규정집 7~8쪽), 제6절 제13항 [붙임] (규정집 9쪽).

글자 카드는 앱(cardsFor)에서, 낱말 점형은 번역 엔진에서 가져와 규정집 보기(점자 ASCII)와 같은지 확인한다.
가·나·다… 약자에 쌍받침·겹받침이 붙으면 약자를 쓰고 받침 두 칸을 그대로 이어 적는다.
"""
from common import app_cards, asc, braille, cell_labels, dots_text, ko_cells, ko_labeled, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-abbr-double-final'
# 규정집 보기: 품삯 (제5항, 8쪽), 값 (수학 점자 보기 '일반항의 값')
RULE_WORDS = {'품삯': "dm5la'", '값': "$b'"}
ABBR = {'가', '나', '다', '마', '바', '사', '자'}
ALLOWED = {f'{k} 약자' for k in '가나다마바사자카타파하것억언얼연열영옥온옹운울은을인'}
SHOW = ['값', '품삯', '많다', '닭']
READ_ITEMS = ['밖', '닦다', '맑다', '삶']
WRITE_ITEMS = ['낚시', '밟다', '짧다', '깎다']


def build():
    u = unit_data(UNIT_ID)
    jong = {c['letter']: c['dots'] for c in app_cards('ko-double-final')}
    app = {c['letter']: c for c in app_cards(UNIT_ID)}
    assert len(app) == 18
    for k, c in app.items():
        labels = cell_labels(c)
        assert c['dots'] == ko_cells(k), k
        abbr = labels[-3]
        assert abbr.endswith('약자') and abbr[0] in ABBR, k
        # 받침 두 칸 = 9단원에서 배운 쌍받침·겹받침 점형 그대로
        dj = labels[-1].split()[-1]
        assert c['dots'][-2:] == jong[dj], k
    assert app['깎']['dots'][-2:] == asc('aa')  # 제4항
    for w, a in RULE_WORDS.items():
        assert ko_cells(w) == reg_cells(a), w
    for w in SHOW + READ_ITEMS + WRITE_ITEMS:
        assert set(l for l in ko_labeled(w)[1] if l.endswith('약자')) <= ALLOWED, w

    def card(k):
        return {'name': k, 'cells': app[k]['dots'], 'labels': cell_labels(app[k]), 'line': dots_text(app[k]['dots'])}

    def word(w):
        cells, labels = ko_labeled(w)
        return {'name': w, 'cells': cells, 'labels': labels, 'line': dots_text(cells)}

    groups = {}
    for k, c in app.items():
        groups.setdefault(cell_labels(c)[-3], []).append(k)
    rules = [
        ('제13항 [붙임]', '위의 글자들(가 나 다 마 바 사 자 카 타 파 하)에 받침이 있거나 첫소리가 된소리일 때에도 약자를 사용하여 적는다.'),
        ('제4항', '쌍받침 ‘ㄲ’은 ⠁⠁으로 적고, 쌍받침 ‘ㅆ’은 약자인 ⠌으로 적는다.'),
        ('제5항', '겹받침은 각 받침 글자를 어울러 적는다.'),
    ]
    learn = [
        {'title': '약자 + 받침 두 칸', 'blocks': [
            {'t': 'p', 'text': '값은 가 약자 뒤에 겹받침 ㅄ(ㅂ과 ㅅ 두 칸)을 이어 적습니다. 받침이 쌍받침·겹받침이어도 약자는 그대로 씁니다(제13항 [붙임]).'},
            {'t': 'cards', 'items': [card('값'), card('깎')]},
        ]},
    ] + [
        {'title': f'{g} 뒤에 받침', 'blocks': [{'t': 'cards', 'items': [card(k) for k in ks if k not in ('값', '깎')]}]}
        for g, ks in groups.items() if [k for k in ks if k not in ('값', '깎')]
    ] + [
        {'title': '낱말 보기', 'blocks': [
            {'t': 'p', 'text': '값과 품삯은 규정집에 나오는 보기입니다.'},
            {'t': 'cards', 'items': [word(w) for w in SHOW]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. 약자 뒤 받침 두 칸을 함께 읽어 보세요.', 'blank': '(            )',
             'items': [{'name': dots_text(ko_cells(w)), 'cells': ko_cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '약자를 먼저 적고, 쌍받침·겹받침을 두 칸으로 이어 적으세요.',
             'items': [{'ask': w, 'cells': len(ko_cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제2장 제4·5항, 제6절 약자 제13항 [붙임] (규정집 7~9쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            f'값 → {braille(app["값"]["dots"])} (가 약자 + 받침 ㅄ)',
            f'닭 → {braille(app["닭"]["dots"])} (다 약자 + 받침 ㄺ)',
            f'깎 → {braille(app["깎"]["dots"])} (된소리표 + 가 약자 + 받침 ㄲ)',
        ],
        learn=learn, practice=practice,
        checks=[
            '약자 뒤에 쌍받침·겹받침을 두 칸으로 적을 수 있다.',
            '된소리로 시작하는 글자(깎·짧)도 된소리표 뒤에 약자를 쓴다는 것을 안다.',
            '약자와 겹받침이 든 낱말을 읽을 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(ko_cells(w))} {dots_text(ko_cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
