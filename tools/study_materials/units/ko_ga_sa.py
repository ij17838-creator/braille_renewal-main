"""한글 11단원 「'가'와 '사'의 약자」. 근거: 제2장 제6절 제13항과 [붙임] (규정집 9쪽), 제16항 (규정집 11쪽).

약자 카드는 앱(cardsFor)에서, 낱말 점형은 번역 엔진에서 가져와 규정집 보기(점자 ASCII)와 같은지 확인한다.
이 단원의 낱말에는 가·사·까·싸 말고 다른 약자를 넣지 않는다.
"""
from common import app_cards, asc, braille, cell_labels, dots_text, ko_cells, ko_labeled, ko_uses_abbr, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-ga-sa'
RULE_TABLE = {'가': '$', '사': 'l'}  # 제13항 표 (규정집 9쪽)
# 제13항·[붙임]·제16항 보기 (규정집 9~11쪽)
RULE_WORDS = {'가지': '$.o', '사위': 'lmr', '강산': '$7l3', '찹쌀': ';<b,l1', '까치': ',$;o', '싸구려': ',l@m":'}
SHOW = ['가지', '사위']
SHOW_JONG = ['강산', '찹쌀']
READ_ITEMS = ['까치', '싸구려', '가수', '사과']
WRITE_ITEMS = ['가게', '감기', '산수', '싸움']


def ga_sa_only(word):
    """약자를 쓴 글자가 모두 가·사(까·싸, 받침 붙은 것 포함)인지."""
    for s in ko_uses_abbr(word):
        code = ord(s) - 0xAC00
        if code % 588 // 28 != 0 or 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'[code // 588] not in 'ㄱㄲㅅㅆ':
            return False
    return True


def build():
    u = unit_data(UNIT_ID)
    app = {c['letter']: c for c in app_cards(UNIT_ID)}
    initial = {c['letter']: c['dots'] for c in app_cards('ko-initial')}
    # 앱 카드 = 규정집 표, 엔진 = 규정집 보기
    assert list(app) == ['가', '사', '까', '싸']
    for k, a in RULE_TABLE.items():
        assert app[k]['dots'] == asc(a), k
    assert app['까']['dots'] == asc(',$') and app['싸']['dots'] == asc(',l')  # 제16항: 된소리표 + 약자
    for w, a in RULE_WORDS.items():
        assert ko_cells(w) == reg_cells(a), w
    for w in list(RULE_WORDS) + READ_ITEMS + WRITE_ITEMS:
        assert ko_uses_abbr(w) and ga_sa_only(w), w
    # 안내 문장에 적은 사실 확인: 가·사 약자는 초성 ㄱ·ㅅ과 점형이 다른 한 칸
    assert app['가']['dots'] != initial['ㄱ'] and app['사']['dots'] != initial['ㅅ']
    assert len(app['가']['dots']) == len(app['사']['dots']) == 1

    def card(k):
        return {'name': k, 'cells': app[k]['dots'], 'labels': cell_labels(app[k]), 'line': dots_text(app[k]['dots'])}

    def word(w):
        cells, labels = ko_labeled(w)
        return {'name': w, 'cells': cells, 'labels': labels, 'line': dots_text(cells)}

    rules = [
        ('제13항', '다음 글자들은 약자를 사용하여 적는다. 가 나 다 마 바 사 자 카 타 파 하'),
        ('[붙임]', '위의 글자들에 받침이 있거나 첫소리가 된소리일 때에도 약자를 사용하여 적는다.'),
        ('제16항', '‘까, 싸, 껏’을 적을 때에는 ‘가, 사, 것’의 약자 앞에 된소리표를 적어 나타낸다.'),
    ]
    learn = [
        {'title': '가와 사의 약자', 'blocks': [
            {'t': 'p', 'text': f'가는 {dots_text(app["가"]["dots"])}, 사는 {dots_text(app["사"]["dots"])} 한 칸으로 적습니다. 초성 ㄱ({dots_text(initial["ㄱ"])})이나 ㅅ({dots_text(initial["ㅅ"])})과는 점형이 다르니 따로 익힙니다.'},
            {'t': 'cards', 'items': [card('가'), card('사')]},
        ]},
        {'title': '까와 싸', 'blocks': [
            {'t': 'p', 'text': '까·싸는 가·사 약자 앞에 된소리표를 붙여 적습니다(제16항).'},
            {'t': 'cards', 'items': [card('까'), card('싸')]},
        ]},
        {'title': '받침이 붙어도 약자를 써요', 'blocks': [
            {'t': 'p', 'text': '강·산·쌀처럼 받침이 있어도 약자를 쓰고, 받침은 약자 뒤에 적습니다(제13항 [붙임]).'},
            {'t': 'cards', 'items': [word(w) for w in SHOW_JONG]},
        ]},
        {'title': '규정집 보기 낱말', 'blocks': [
            {'t': 'cards', 'items': [word(w) for w in SHOW]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. 가·사 약자 칸을 먼저 찾아보세요.', 'blank': '(            )',
             'items': [{'name': dots_text(ko_cells(w)), 'cells': ko_cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '가·사는 약자 한 칸으로, 받침은 약자 뒤에 적으세요.',
             'items': [{'ask': w, 'cells': len(ko_cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제2장 제6절 약자 제13항·[붙임], 제16항 (규정집 9~11쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            f'가 → {braille(app["가"]["dots"])} ({dots_text(app["가"]["dots"])}), 사 → {braille(app["사"]["dots"])} ({dots_text(app["사"]["dots"])})',
            f'까 → {braille(app["까"]["dots"])}, 싸 → {braille(app["싸"]["dots"])} (된소리표 + 약자)',
            '받침이 있어도 약자를 씁니다. 예) 강산 → ' + braille(ko_cells('강산')),
        ],
        learn=learn, practice=practice,
        checks=[
            '가·사 약자를 읽고 쓸 수 있다.',
            '까·싸는 된소리표 뒤에 약자를 적는다는 것을 안다.',
            '받침이 있는 가·사도 약자로 적을 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(ko_cells(w))} {dots_text(ko_cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
