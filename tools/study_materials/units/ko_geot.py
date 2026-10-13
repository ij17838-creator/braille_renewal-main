"""한글 13단원 「'것'과 '받침 ㅆ' 약자」. 근거: 제2장 제4항 (규정집 7쪽), 제6절 제15항·제16항·[붙임] (규정집 10~12쪽).

약자 카드는 앱(cardsFor)에서, 낱말 점형은 번역 엔진에서 가져와 규정집 보기(점자 ASCII)와 같은지 확인한다.
이 단원의 낱말에는 것·껏과 'ㅏ'가 붙은 약자(앞 단원에서 배움) 말고 다른 약자를 넣지 않는다.
"""
from common import app_cards, asc, braille, cell_labels, dots_text, ko_cells, ko_labeled, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-geot'
# 제4항·제15항·제16항·[붙임] 보기 (규정집 7~12쪽)
RULE_WORDS = {'있다': 'o/i', '보았다': '^u</i', '것이다': '_soi', '이것': 'o_s', '힘껏': 'jo5,_s', '마음껏': 'e<{5,_s', '불을 껐다.': '~&!`,@s/i4'}
ALLOWED = {f'{k} 약자' for k in '가나다마바사자카타파하것'}
SHOW_GEOT = ['것이다', '이것', '힘껏']
SHOW_SS = ['있다', '보았다', '갔다', '했다']
READ_ITEMS = ['갔다', '샀다', '이것', '잤다']
WRITE_ITEMS = ['있다', '왔다', '마음껏', '했다']


def abbr_ok(w):
    used = [l for l in ko_labeled(w)[1] if l.endswith('약자') or l == '약어']
    return set(used) <= ALLOWED


def build():
    u = unit_data(UNIT_ID)
    cards = app_cards(UNIT_ID)
    app = {c['letter']: c for c in cards}
    assert app['것']['dots'] == asc('_s') and app['껏']['dots'] == asc(',_s')  # 제15항 표, 제16항
    assert app['ㅆ']['dots'] == asc('/')  # 제4항: 받침 ㅆ은 약자 /
    for k in ('갔', '났', '샀', '잤'):
        assert app[k]['dots'] == ko_cells(k) and app[k]['dots'][-1] == asc('/')[0], k
    for w, a in RULE_WORDS.items():
        assert ko_cells(w) == reg_cells(a), w
    for w in SHOW_GEOT + SHOW_SS + READ_ITEMS + WRITE_ITEMS:
        assert abbr_ok(w), w
    # 껐: '꺼' + 받침 ㅆ (제16항 [붙임]) — 껏 약자를 쓰지 않음
    assert '것 약자' not in ko_labeled('껐다')[1]

    def card(k):
        return {'name': k, 'cells': app[k]['dots'], 'labels': cell_labels(app[k]), 'line': dots_text(app[k]['dots'])}

    def word(w):
        cells, labels = ko_labeled(w)
        return {'name': w, 'cells': cells, 'labels': labels, 'line': dots_text(cells)}

    rules = [
        ('제4항', '쌍받침 ‘ㄲ’은 ⠁⠁으로 적고, 쌍받침 ‘ㅆ’은 약자인 ⠌으로 적는다.'),
        ('제15항', '다음 글자들은 약자를 사용하여 적는다. (… 것)'),
        ('제16항', '‘까, 싸, 껏’을 적을 때에는 ‘가, 사, 것’의 약자 앞에 된소리표를 적어 나타낸다.'),
        ('[붙임]', '‘껐’을 적을 때에는 ‘꺼’와 받침 ‘ㅆ’ 약자를 어울러 적는다.'),
    ]
    learn = [
        {'title': '것과 껏', 'blocks': [
            {'t': 'p', 'text': f'것은 두 칸 약자({dots_text(app["것"]["dots"])})로 적습니다. 껏은 그 앞에 된소리표를 붙입니다(제16항).'},
            {'t': 'cards', 'items': [card('것'), card('껏')]},
            {'t': 'cards', 'items': [word(w) for w in SHOW_GEOT]},
        ]},
        {'title': '받침 ㅆ', 'blocks': [
            {'t': 'p', 'text': f'받침 ㅆ은 ㅅ을 두 번 적지 않고 약자 한 칸({dots_text(app["ㅆ"]["dots"])})으로 적습니다(제4항).'},
            {'t': 'cards', 'items': [card('ㅆ')]},
            {'t': 'p', 'text': '가·나·사·자 약자에 받침 ㅆ이 붙으면 약자 뒤에 ㅆ 약자를 적습니다.'},
            {'t': 'cards', 'items': [card(k) for k in ('갔', '났', '샀', '잤')]},
        ]},
        {'title': '받침 ㅆ이 든 낱말', 'blocks': [
            {'t': 'cards', 'items': [word(w) for w in SHOW_SS]},
        ]},
        {'title': '껐은 껏 약자를 쓰지 않아요', 'blocks': [
            {'t': 'p', 'text': '‘껐’은 ‘꺼’를 적고 받침 ㅆ 약자를 붙입니다(제16항 [붙임]).'},
            {'t': 'cards', 'items': [word('껐다')]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. 3·4점 칸은 받침 ㅆ입니다.', 'blank': '(            )',
             'items': [{'name': dots_text(ko_cells(w)), 'cells': ko_cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '것은 두 칸 약자로, 받침 ㅆ은 3·4점 한 칸으로 적으세요.',
             'items': [{'ask': w, 'cells': len(ko_cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제2장 제4항, 제6절 약자 제15항·제16항·[붙임] (규정집 7~12쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            f'것 → {braille(app["것"]["dots"])} ({dots_text(app["것"]["dots"])}), 껏 → {braille(app["껏"]["dots"])}',
            f'받침 ㅆ → {braille(app["ㅆ"]["dots"])} ({dots_text(app["ㅆ"]["dots"])}). 예) 있다 → {braille(ko_cells("있다"))}',
            '껐은 꺼 + 받침 ㅆ으로 적습니다. 예) 껐다 → ' + braille(ko_cells('껐다')),
        ],
        learn=learn, practice=practice,
        checks=[
            '것·껏 약자를 읽고 쓸 수 있다.',
            '받침 ㅆ을 한 칸 약자로 적을 수 있다.',
            '껐은 꺼와 받침 ㅆ으로 적는다는 것을 안다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(ko_cells(w))} {dots_text(ko_cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
