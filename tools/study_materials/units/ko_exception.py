"""한글 24단원 「숫자 뒤 띄어쓰기」. 근거: 제2장 제11절 제44항·[다만] (규정집 28~29쪽).

카드는 앱(cardsFor)에서, 낱말 점형은 번역 엔진에서 가져와 규정집 보기(점자 ASCII)와 같은지 확인한다.
"""
from common import app_cards, asc, braille, cell_labels, dots_text, ko_cells, ko_labeled, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-exception'
# 제44항 보기: 붙여 쓰는 것 (규정집 28쪽)
JOINED = {'1가': '#a$', '3반': '#c^3', '5월': '#ep1', '7자루': '#g."m', '2권': '#b@p3', '4선': '#d,)', '6일': '#fo1', '8꾸러미': '#h,@m"seo'}
# 제44항 [다만] 보기: 띄어 쓰는 것 (규정집 28~29쪽)
SPACED = {'1년': '#a`c*', '3명': '#c`e]', '5톤': '#e`h(', '7항': '#g`j7', '2도': '#b`iu', '4칸': '#d`f3', '6평': '#f`d]', '5운6기': '#e`g#f@o'}
# 숫자와 혼동되는 첫소리 글자·약자 = 같은 점형의 숫자 (제40항 숫자 표의 a~j = 1~0)
CONFUSE = {'ㄴ': 'c', 'ㄷ': 'i', 'ㅁ': 'e', 'ㅋ': 'f', 'ㅌ': 'h', 'ㅍ': 'd', 'ㅎ': 'j', '운': 'g'}
DIGIT = dict(zip('abcdefghij', '1234567890'))
SHOW_JOINED = ['3반', '5월', '2권', '6일']
SHOW_SPACED = ['1년', '3명', '5톤', '7항', '2도', '4칸', '6평', '5운6기']
READ_ITEMS = ['2도', '3반', '4칸', '6일']
WRITE_ITEMS = ['6평', '4선', '5톤', '7자루']


def build():
    u = unit_data(UNIT_ID)
    app = {c['letter']: c for c in app_cards(UNIT_ID)}
    initial = {c['letter']: c['dots'] for c in app_cards('ko-initial')}
    eok = {c['letter']: c['dots'] for c in app_cards('ko-eok')}
    for k, c in app.items():
        assert c['dots'] == ko_cells(k), k
        assert '띄어쓰기' in cell_labels(c), k
    for w, a in {**JOINED, **SPACED}.items():
        assert ko_cells(w) == reg_cells(a), w
    for k, a in CONFUSE.items():
        assert (initial.get(k) or eok[k]) == asc(a), k
    # 혼동되지 않는 첫소리(ㄱ·ㅂ·ㅅ·ㅈ…)는 숫자 점형이 아님
    for k in 'ㄱㄹㅂㅅㅈㅊ':
        assert initial[k] not in [asc(x) for x in DIGIT], k

    def card(k):
        return {'name': k, 'cells': app[k]['dots'], 'labels': cell_labels(app[k]), 'line': dots_text(app[k]['dots'])}

    def word(w):
        cells, labels = ko_labeled(w)
        return {'name': w, 'cells': cells, 'labels': labels, 'line': dots_text(cells)}

    rules = [
        ('제44항', '숫자 뒤에 이어 나오는 한글의 띄어쓰기는 묵자를 따른다.'),
        ('[다만]', '숫자와 혼동되는 ‘ㄴ, ㄷ, ㅁ, ㅋ, ㅌ, ㅍ, ㅎ’의 첫소리 글자와 ‘운’의 약자는 숫자 뒤에 붙어 나오더라도 숫자와 한글을 띄어 쓴다.'),
    ]
    pairs = [{'name': f'{k} = 숫자 {DIGIT[a]}', 'cells': asc(a), 'labels': [f'{k} / {DIGIT[a]}'], 'line': dots_text(asc(a))} for k, a in CONFUSE.items()]
    learn = [
        {'title': '숫자와 점형이 같은 글자', 'blocks': [
            {'t': 'p', 'text': '첫소리 ㄴ·ㄷ·ㅁ·ㅋ·ㅌ·ㅍ·ㅎ과 운 약자는 숫자와 점형이 같습니다. 수표 뒤에 바로 붙이면 숫자로 읽히므로 숫자 뒤에서 한 칸 띄어 씁니다(제44항 [다만]).'},
            {'t': 'cards', 'items': pairs},
        ]},
        {'title': '띄어 쓰는 보기', 'blocks': [
            {'t': 'cards', 'items': [word(w) for w in SHOW_SPACED]},
        ]},
        {'title': '붙여 쓰는 보기', 'blocks': [
            {'t': 'p', 'text': '그 밖의 글자는 묵자(글자)에서 붙여 썼으면 점자도 숫자 뒤에 붙여 씁니다(제44항).'},
            {'t': 'cards', 'items': [word(w) for w in SHOW_JOINED]},
        ]},
        {'title': '게임 카드 보기', 'blocks': [
            {'t': 'cards', 'items': [card(k) for k in ('1 나', '8 운')]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. 수표 뒤 빈칸이 있는지 살펴보세요.', 'blank': '(            )',
             'items': [{'name': dots_text(ko_cells(w)), 'cells': ko_cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '숫자 뒤 첫소리가 숫자와 혼동되면 한 칸 띄우세요. 빈칸도 한 칸으로 셉니다.',
             'items': [{'ask': w, 'cells': len(ko_cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제2장 제11절 제44항·[다만] (규정집 28~29쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            f'1년 → {braille(ko_cells("1년"))} (수표 1, 빈칸, 년)',
            f'3반 → {braille(ko_cells("3반"))} (ㅂ은 숫자와 혼동되지 않아 붙여 씀)',
            f'5운6기 → {braille(ko_cells("5운6기"))} (운 약자 앞에서 띄어 씀)',
        ],
        learn=learn, practice=practice,
        checks=[
            '숫자와 점형이 같은 첫소리 글자와 운 약자를 안다.',
            '숫자 뒤에 그 글자가 오면 한 칸 띄어 쓸 수 있다.',
            '그 밖의 글자는 숫자 뒤에 붙여 쓸 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(ko_cells(w))} {dots_text(ko_cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
