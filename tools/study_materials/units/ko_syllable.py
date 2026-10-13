"""한글 5단원 「기본 음절표와 낱말」. 근거: 제1항과 [다만 1] (규정집 3쪽), 제6항 (규정집 5쪽).

낱말은 규정집 제1항·[다만 1]의 보기 가운데 받침과 약자가 없는 것만 쓴다.
보기의 점자 ASCII를 그대로 옮겨, 앱 음절 카드를 이어 붙인 점형과 같은지 확인한다.
"""
from common import app_cards, asc, braille, dots_text, standard_doc, unit_data

UNIT_ID = 'ko-syllable'
CHO = ['ㄱ', 'ㄴ', 'ㄷ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅅ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ', 'ㅇ']
JUNG = ['ㅏ', 'ㅑ', 'ㅓ', 'ㅕ', 'ㅗ', 'ㅛ', 'ㅜ', 'ㅠ', 'ㅡ', 'ㅣ']
# 제1항·[다만 1] 보기 (규정집 3쪽, 점자 글꼴 그대로)
RULE_WORDS = {
    '거리': '@s"o', '너비': 'cs~o', '두더지': 'imis.o', '리코더': '"ofuis', '미소': 'eo,u', '보리': '~u"o',
    '셔츠': ',:;{', '저고리': '.s@u"o', '추수': ';m,m', '커피': 'fsdo', '터무니': 'hsemco', '피리': 'do"o',
    '호수': 'ju,m', '아버지': '<~s.o', '야구': '>@m', '어머니': 'sesco', '여우': ':m', '오이': 'uo', '요리': '+"o',
    '우유': 'm%', '유리': '%"o', '으스스': '{,{,{', '이모': 'oeu', '피아노': 'do<cu', '도우미': 'iumeo', '러시아': '"s,o<',
}
SHOW_WORDS = ['저고리', '두더지', '아버지', '피아노', '러시아', '도우미', '셔츠', '요리']
READ_ITEMS = ['거리', '미소', '우유', '호수', '이모', '터무니']
WRITE_ITEMS = ['보리', '추수', '오이', '너비', '어머니', '리코더']


def compose(cho, jung):
    return chr(0xAC00 + ('ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'.index(cho) * 21 + 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'.index(jung)) * 28)


def build():
    u = unit_data(UNIT_ID)
    app = {c['letter']: c for c in app_cards(UNIT_ID)}
    cells = {k: c['dots'] for k, c in app.items()}

    def labels(syl):
        return [s['label'] for s in app[syl]['steps'] if s['cells']]

    def word(w):
        return [c for syl in w for c in cells[syl]]

    # 앱 음절을 이어 붙인 점형 = 규정집 보기
    for w, a in RULE_WORDS.items():
        assert word(w) == asc(a), w
    # 약자로 적어 이 단원에서 빠지는 음절은 가·나·다·마·바·사·자·카·타·파·하 11개
    missing = [compose(c, j) for c in CHO for j in JUNG if compose(c, j) not in cells]
    assert missing == list('가나다마바사자카타파하'), missing
    assert len(cells) == 14 * 10 - 11
    # 첫소리 ㅇ 음절은 모음 한 칸
    assert all(len(cells[compose('ㅇ', j)]) == 1 for j in JUNG)
    assert all(len(cells[compose(c, j)]) == 2 for c in CHO[:-1] for j in JUNG if compose(c, j) in cells)

    def card(w):
        lab = [l for syl in w for l in labels(syl)]
        return {'name': w, 'cells': word(w), 'labels': lab, 'line': dots_text(word(w))}

    def syl_card(syl, name=None):
        return {'name': name or syl, 'cells': cells[syl], 'labels': labels(syl), 'line': dots_text(cells[syl])}

    table_rows = []
    for c in CHO:
        row = [c if c != 'ㅇ' else 'ㅇ(생략)']
        for j in JUNG:
            s = compose(c, j)
            row.append(f'{s} {braille(cells[s])}' if s in cells else f'{s} (약자)')
        table_rows.append(row)

    rules = [
        ('제1항', '기본 자음자 14개가 첫소리로 쓰일 때에는 다음과 같이 적는다.'),
        ('[다만 1]', '‘ㅇ’이 첫소리로 쓰일 때에는 점자로 이를 표기하지 않는다.'),
        ('제6항', '기본 모음자 10개는 다음과 같이 적는다.'),
    ]
    learn = [
        {'title': '음절 만들기: 초성 + 모음', 'blocks': [
            {'t': 'p', 'text': '받침 없는 음절은 초성 자음 한 칸 뒤에 모음 한 칸을 이어 적습니다. 3단원의 초성과 4단원의 모음을 그대로 잇습니다.'},
            {'t': 'cards', 'items': [syl_card('고'), syl_card('수'), syl_card('미'), syl_card('투')]},
        ]},
        {'title': '첫소리 ㅇ은 적지 않아요', 'blocks': [
            {'t': 'p', 'text': '아, 오, 이처럼 첫소리가 ㅇ인 음절은 ㅇ을 적지 않고 모음 한 칸만 적습니다.'},
            {'t': 'cards', 'items': [syl_card(compose('ㅇ', j), f'{compose("ㅇ", j)} (ㅇ 생략)') for j in JUNG]},
        ]},
        {'title': '기본 음절표', 'blocks': [
            {'t': 'p', 'text': '줄은 초성, 칸은 모음입니다. 칸마다 음절과 점자 문자를 적었습니다. 「약자」라고 적힌 가·나·다·마·바·사·자·카·타·파·하는 약자로 적으므로 약자 단원에서 배웁니다.'},
            {'t': 'table', 'caption': '기본 음절표 (초성 × 기본 모음, 받침 없음)', 'head': ['초성'] + JUNG, 'rows': table_rows},
        ]},
        {'title': '규정집 보기 낱말', 'blocks': [
            {'t': 'p', 'text': '규정집 제1항의 보기 낱말입니다. 음절을 차례로 이어 적고, 첫소리 ㅇ은 적지 않습니다.'},
            {'t': 'cards', 'items': [card(w) for w in SHOW_WORDS]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. 모음 한 칸만 있는 음절은 첫소리 ㅇ이 생략된 것입니다.',
             'blank': '(            )',
             'items': [{'name': dots_text(word(w)), 'cells': word(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '음절마다 초성 한 칸, 모음 한 칸을 칠하세요. 첫소리 ㅇ은 칸을 쓰지 않습니다.',
             'items': [{'ask': w, 'cells': len(word(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제1장 제1절 제1항 (규정집 3쪽), 제3절 제6항 (규정집 5쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '받침 없는 음절 = 초성 한 칸 + 모음 한 칸. 예) 고 → ' + braille(cells['고']) + ' (4점 + 1·3·6점)',
            '첫소리 ㅇ은 적지 않으므로 모음 한 칸만 적습니다. 예) 오 → ' + braille(cells['오']),
            '가·나·다·마·바·사·자·카·타·파·하는 약자로 적으므로 이 단원에서는 다루지 않습니다.',
        ],
        learn=learn, practice=practice,
        checks=[
            '받침 없는 음절을 초성과 모음으로 풀어 적을 수 있다.',
            '첫소리 ㅇ은 적지 않고 모음만 적는다는 것을 안다.',
            '두세 음절 낱말을 읽고 쓸 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(word(w))} {dots_text(word(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
