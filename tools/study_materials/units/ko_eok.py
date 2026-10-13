"""한글 14단원 「'모음+받침' 약자」. 근거: 제2장 제6절 제15항·[붙임], 제17항 (규정집 10~12쪽).

약자 카드는 앱(cardsFor)에서, 낱말 점형은 번역 엔진에서 가져와 규정집 보기(점자 ASCII)와 같은지 확인한다.
이 단원의 낱말에는 '모음+받침' 약자와 앞 단원에서 배운 약자(ㅏ 붙은 약자, 것) 말고 다른 약자를 넣지 않는다.
"""
from common import app_cards, asc, braille, cell_labels, dots_text, ko_cells, ko_labeled, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-eok'
# 제15항 표 (규정집 10쪽)
RULE_TABLE = {'억': '?', '언': ')', '얼': 't', '연': '*', '열': '|', '영': '}', '옥': 'x', '온': '(', '옹': '=',
              '운': 'g', '울': '&', '은': 'z', '을': '!', '인': 'q'}
# 제15항·[붙임], 제17항 보기 (규정집 10~12쪽)
RULE_WORDS = {
    '억새': '?,r', '연필': '*do1', '옥수수': 'x,m,m', '운동장': 'gi=.7', '겨울': '@:&', '인내': 'qcr',
    '추억': ';m?', '온도': '(iu', '은하수': 'zj,m', '가을': '$!', '열매': '|er', '영어': '}s',
    '덕망': 'i?e7', '건전지': '@).).o', '별자리': '~|."o', '순두부': ',gim~m', '불고기': '~&@u@o', '진실': '.q,o1',
    '근로': '@z"u', '용돈': '+7i(',
    '성가': ',}$', '정성': '.},}', '청년': ';}c*', '말썽': 'e1,,]', '얄라셩': '>1"<,:7',
}
ALLOWED = {f'{k} 약자' for k in '가나다마바사자카타파하것'} | {f'{k} 약자' for k in RULE_TABLE}
SHOW = ['억새', '연필', '옥수수', '운동장', '겨울', '인내']
SHOW_CHO = ['덕망', '건전지', '별자리', '순두부', '불고기', '진실']
SHOW_SEONG = ['성가', '정성', '청년', '얄라셩']
READ_ITEMS = ['추억', '온도', '은하수', '가을']
WRITE_ITEMS = ['열매', '영어', '근로', '용돈']


def abbr_ok(w):
    used = [l for l in ko_labeled(w)[1] if l.endswith('약자') or l == '약어']
    return set(used) <= ALLOWED


def build():
    u = unit_data(UNIT_ID)
    app = {c['letter']: c for c in app_cards(UNIT_ID)}
    assert list(app)[:14] == list(RULE_TABLE)
    for k, a in RULE_TABLE.items():
        assert app[k]['dots'] == asc(a), k
    for k in list(app)[14:]:  # 자음 + 약자 카드 = 엔진 = 초성 + 약자
        assert app[k]['dots'] == ko_cells(k) and len(app[k]['dots']) == 2, k
    for w, a in RULE_WORDS.items():
        assert ko_cells(w) == reg_cells(a), w
    for w in SHOW + SHOW_CHO + SHOW_SEONG + READ_ITEMS + WRITE_ITEMS:
        assert abbr_ok(w), w
    # 제17항: 성·정·청은 ㅅ·ㅈ·ㅊ + 영 약자, 셩은 약자를 쓰지 않음
    for k in ('성', '정', '청'):
        assert ko_labeled(k)[1][1] == '영 약자', k
    assert not any(l.endswith('약자') for l in ko_labeled('얄라셩')[1])

    def card(k):
        return {'name': k, 'cells': app[k]['dots'], 'labels': cell_labels(app[k]), 'line': dots_text(app[k]['dots'])}

    def word(w):
        cells, labels = ko_labeled(w)
        return {'name': w, 'cells': cells, 'labels': labels, 'line': dots_text(cells)}

    rules = [
        ('제15항', '다음 글자들은 약자를 사용하여 적는다. 억 언 얼 연 열 영 옥 온 옹 운 울 은 을 인 것'),
        ('[붙임]', '‘억, 언, 얼, 연, 열, 영, 옥, 온, 옹, 운, 울, 은, 을, 인, 것’이 포함되어 있는 글자에도 약자를 사용하여 적는다.'),
        ('제17항', '‘성, 썽, 정, 쩡, 청’을 적을 때에는 ‘ㅅ, ㅆ, ㅈ, ㅉ, ㅊ’ 다음에 ‘영’의 약자 ⠻을 적어 나타낸다.'),
    ]
    learn = [
        {'title': '모음+받침 약자 열네 개', 'blocks': [
            {'t': 'p', 'text': '억·언·얼·연·열·영·옥·온·옹·운·울·은·을·인은 모음과 받침을 한 칸으로 적습니다.'},
            {'t': 'cards', 'items': [card(k) for k in RULE_TABLE]},
        ]},
        {'title': '규정집 보기 낱말', 'blocks': [
            {'t': 'cards', 'items': [word(w) for w in SHOW]},
        ]},
        {'title': '앞에 초성이 오는 글자', 'blocks': [
            {'t': 'p', 'text': '먹·건·물처럼 약자 앞에 초성이 오면, 초성을 먼저 적고 약자를 붙입니다(제15항 [붙임]).'},
            {'t': 'cards', 'items': [card(k) for k in ('먹', '건', '명', '손', '문', '글')]},
            {'t': 'cards', 'items': [word(w) for w in SHOW_CHO]},
        ]},
        {'title': '성·정·청', 'blocks': [
            {'t': 'p', 'text': 'ㅅ·ㅆ·ㅈ·ㅉ·ㅊ 뒤의 영 약자는 성·썽·정·쩡·청으로 읽습니다(제17항). ‘셩’은 성이 아니므로 약자를 쓰지 않고 풀어 적습니다(규정집 보기 ‘얄라셩’).'},
            {'t': 'cards', 'items': [word(w) for w in SHOW_SEONG]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. 한 칸에 모음과 받침이 함께 든 약자를 찾아보세요.', 'blank': '(            )',
             'items': [{'name': dots_text(ko_cells(w)), 'cells': ko_cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '약자가 있는 글자는 약자로, 초성이 있으면 초성 뒤에 약자를 적으세요.',
             'items': [{'ask': w, 'cells': len(ko_cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제2장 제6절 약자 제15항·[붙임], 제17항 (규정집 10~12쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            f'억 → {braille(app["억"]["dots"])}, 은 → {braille(app["은"]["dots"])}, 을 → {braille(app["을"]["dots"])} (한 칸 약자)',
            f'먹 → {braille(app["먹"]["dots"])} (초성 ㅁ + 억 약자)',
            f'정 → {braille(ko_cells("정"))} (ㅈ + 영 약자)',
        ],
        learn=learn, practice=practice,
        checks=[
            '모음+받침 약자 열네 개를 읽고 쓸 수 있다.',
            '초성 뒤에 약자를 붙여 적을 수 있다.',
            '성·정·청은 ㅅ·ㅈ·ㅊ 뒤에 영 약자를 적는다는 것을 안다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(ko_cells(w))} {dots_text(ko_cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
