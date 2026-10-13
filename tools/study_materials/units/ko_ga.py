"""한글 12단원 「'자음+ㅏ'에서 'ㅏ'를 생략한 약자」. 근거: 제2장 제6절 제13항·[붙임], 제14항·[붙임] (규정집 9~10쪽).

약자 카드는 앱(cardsFor)에서, 낱말 점형은 번역 엔진에서 가져와 규정집 보기(점자 ASCII)와 같은지 확인한다.
이 단원의 낱말에는 'ㅏ'가 붙은 약자(가·사 포함, 앞 단원에서 배움) 말고 다른 약자를 넣지 않는다.
"""
from common import app_cards, asc, braille, cell_labels, dots_text, ko_cells, ko_labeled, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-ga'
# 제13항 표 (규정집 9쪽)
RULE_TABLE = {'나': 'c', '다': 'i', '마': 'e', '바': '^', '자': '.', '카': 'f', '타': 'h', '파': 'd', '하': 'j'}
# 제13항·[붙임], 제14항·[붙임] 보기 (규정집 9~10쪽)
RULE_WORDS = {
    '파도': 'diu', '나비': 'c~o', '다리미': 'i"oeo', '고구마': '@u@me', '바느질': '~c{.o1', '도자기': 'iu.@o',
    '카메라': 'fen"<', '실타래': ',o1h"r', '하루': 'j"m',
    '낮잠': 'ck.5', '만찬': 'e3;<3', '안방': '<3~7', '갈비탕': '$1~oh7', '판소리': 'd3,u"o',
    '따님': ',ico5', '오빠': 'u,~', '짜장': ',..7',
    '나이': 'c<o', '바위': '^<mr', '하얀': 'j<>3', '넥타이': 'cnah<o',
    '팠다.': 'd</i4',
}
ALLOWED = {f'{k} 약자' for k in '가나다마바사자카타파하'}
SHOW = ['나비', '다리미', '고구마', '하루']
SHOW_JONG = ['안방', '판소리']
SHOW_TENSE = ['따님', '오빠']
SHOW_VOWEL = ['나이', '바위']
READ_ITEMS = ['파도', '도자기', '카메라', '만찬']
WRITE_ITEMS = ['바느질', '낮잠', '갈비탕', '짜장']


def abbr_ok(w):
    labels = ko_labeled(w)[1]
    used = [l for l in labels if l.endswith('약자') or l == '약어']
    return used and set(used) <= ALLOWED


def build():
    u = unit_data(UNIT_ID)
    app = {c['letter']: c for c in app_cards(UNIT_ID)}
    initial = {c['letter']: c['dots'] for c in app_cards('ko-initial')}
    assert list(app) == ['나', '다', '마', '바', '자', '카', '타', '파', '하', '따', '빠', '짜']
    for k, a in RULE_TABLE.items():
        assert app[k]['dots'] == asc(a), k
    for k, base in (('따', 'i'), ('빠', '^'), ('짜', '.')):
        assert app[k]['dots'] == asc(',' + base), k  # 제13항 [붙임]: 된소리표 + 약자
    for w, a in RULE_WORDS.items():
        assert ko_cells(w) == reg_cells(a), w
    for w in SHOW + SHOW_JONG + SHOW_TENSE + READ_ITEMS + WRITE_ITEMS:
        assert abbr_ok(w), w
    # 안내 문장 확인: 약자 = 초성 자음 점형 그대로, 제14항 낱말은 약자를 쓰지 않음, 팠은 ㅏ를 적음
    for k in RULE_TABLE:
        cho = 'ㄴㄷㅁㅂㅈㅋㅌㅍㅎ'['나다마바자카타파하'.index(k)]
        assert app[k]['dots'] == initial[cho], k
    for w in SHOW_VOWEL:
        assert not any(l.endswith('약자') for l in ko_labeled(w)[1]), w
    assert ko_labeled('팠다.')[1][:2] == ['ㅍ', 'ㅏ']

    def card(k):
        return {'name': k, 'cells': app[k]['dots'], 'labels': cell_labels(app[k]), 'line': dots_text(app[k]['dots'])}

    def word(w):
        cells, labels = ko_labeled(w)
        return {'name': w, 'cells': cells, 'labels': labels, 'line': dots_text(cells)}

    rules = [
        ('제13항', '다음 글자들은 약자를 사용하여 적는다. 가 나 다 마 바 사 자 카 타 파 하'),
        ('[붙임]', '위의 글자들에 받침이 있거나 첫소리가 된소리일 때에도 약자를 사용하여 적는다.'),
        ('제14항', '‘나, 다, 마, 바, 자, 카, 타, 파, 하’에 모음이 붙어 나올 때에는 약자를 사용하지 않는다.'),
        ('[붙임]', '‘팠’을 적을 때에는 ‘ㅏ’를 생략하지 않고 적는다.'),
    ]
    learn = [
        {'title': '초성만 적는 약자 아홉 개', 'blocks': [
            {'t': 'p', 'text': '나·다·마·바·자·카·타·파·하는 ㅏ를 적지 않고 초성 자음 한 칸만 적습니다. 점형은 초성 ㄴ·ㄷ·ㅁ·ㅂ·ㅈ·ㅋ·ㅌ·ㅍ·ㅎ과 같습니다.'},
            {'t': 'cards', 'items': [card(k) for k in RULE_TABLE]},
        ]},
        {'title': '따·빠·짜', 'blocks': [
            {'t': 'p', 'text': '첫소리가 된소리여도 약자를 쓰고, 앞에 된소리표를 붙입니다(제13항 [붙임]).'},
            {'t': 'cards', 'items': [card(k) for k in ('따', '빠', '짜')]},
        ]},
        {'title': '규정집 보기 낱말', 'blocks': [
            {'t': 'cards', 'items': [word(w) for w in SHOW]},
        ]},
        {'title': '받침이 있을 때와 된소리일 때', 'blocks': [
            {'t': 'p', 'text': '받침이 있어도 약자를 쓰고 받침은 뒤에 적습니다.'},
            {'t': 'cards', 'items': [word(w) for w in SHOW_JONG + SHOW_TENSE]},
        ]},
        {'title': '약자를 쓰지 않는 경우', 'blocks': [
            {'t': 'p', 'text': '나·다·마·바·자·카·타·파·하 바로 뒤에 모음으로 시작하는 글자(이·위·얀 등)가 오면 약자를 쓰지 않고 ㅏ를 적습니다(제14항).'},
            {'t': 'cards', 'items': [word(w) for w in SHOW_VOWEL]},
            {'t': 'p', 'text': '‘팠’도 ㅏ를 생략하지 않고 적습니다(제14항 [붙임]).'},
            {'t': 'cards', 'items': [word('팠다.')]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. 초성만 있는 칸은 ㅏ를 붙여 읽어 보세요.', 'blank': '(            )',
             'items': [{'name': dots_text(ko_cells(w)), 'cells': ko_cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': 'ㅏ가 붙은 글자는 약자로, 받침은 약자 뒤에 적으세요.',
             'items': [{'ask': w, 'cells': len(ko_cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제2장 제6절 약자 제13항·[붙임], 제14항·[붙임] (규정집 9~10쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            f'나 → {braille(app["나"]["dots"])}, 하 → {braille(app["하"]["dots"])} (초성 자음 한 칸)',
            f'따 → {braille(app["따"]["dots"])} (된소리표 + 다 약자)',
            '뒤에 모음 글자가 오면 약자를 쓰지 않습니다. 예) 나이 → ' + braille(ko_cells('나이')),
        ],
        learn=learn, practice=practice,
        checks=[
            '나·다·마·바·자·카·타·파·하 약자를 읽고 쓸 수 있다.',
            '따·빠·짜는 된소리표 뒤에 약자를 적는다는 것을 안다.',
            '뒤에 모음 글자가 오거나 ‘팠’을 적을 때는 약자를 쓰지 않는다는 것을 안다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(ko_cells(w))} {dots_text(ko_cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
