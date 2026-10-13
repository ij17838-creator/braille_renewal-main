"""한글 23단원 「점자의 활용」. 근거: 제40항·제44항 (규정집 27~28쪽), 제2장 약자와 약어 (규정집 9~13쪽), 제49항 (규정집 31쪽).

숫자 낱말은 규정집 제44항 보기(점자 ASCII)를 그대로 옮겨 엔진 결과와 같은지 확인한다.
문장은 저장소 번역 엔진(engine/ko)으로 만든다.
허락 대기 중인 것(ㅚ, 받침 ㅋ·ㅌ·ㅍ, 쌍받침·겹받침, 숫자 뒤 ㄴ·ㄷ·ㅁ·ㅋ·ㅌ·ㅍ·ㅎ·운)은 넣지 않는다.
"""
from common import asc, braille, dots_text, ko_cells, ko_uses_abbr, pending_jamo, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-use'
# 제44항 보기 (규정집 28쪽), 제49항 보기 (규정집 33쪽)
RULE_WORDS = {'3반': '#c^3', '5월': '#ep1', '7자루': '#g."m', '6일': '#fo1', '5 개': '#e`@r'}
RULE_SENTENCES = {'9월 15일~9월 25일': '#ip1`#aeo1@9#ip1`#beo1'}
SHOW_NUM = ['3반', '5월', '7자루', '6일']
SHOW = ['그런데 5월에 비가 왔다.', '“사과 3개 주세요.”', '그리고 6일에 만나요.', '9월 15일~9월 25일']
READ_ITEMS = ['오늘은 7월 4일이다.', '그러나 비가 와요!', '사과 5개, 배 2개', '정말? 8일이야!']
WRITE_ITEMS = ['우리 반은 3반이에요.', '그래서 4시에 갔다.', '연필 2자루, 공책 3권', '나는 5월이 좋아요.']
NOT_AFTER_NUMBER = set('ㄴㄷㅁㅋㅌㅍㅎ')  # 제44항 [다만] — 24단원에서 배운다


def initial(ch):
    code = ord(ch) - 0xAC00
    return 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'[code // 588] if 0 <= code < 11172 else ''


def build():
    u = unit_data(UNIT_ID)
    # 엔진 = 규정집 보기
    for t, a in {**RULE_WORDS, **RULE_SENTENCES}.items():
        assert ko_cells(t) == reg_cells(a), t
    num = asc('#')[0]
    for t in SHOW + READ_ITEMS + WRITE_ITEMS:
        assert not pending_jamo(t), t
        for i, ch in enumerate(t[:-1]):  # 숫자 바로 뒤에 [다만]의 글자나 운이 오지 않는다
            nxt = t[i + 1]
            assert not (ch.isdigit() and (initial(nxt) in NOT_AFTER_NUMBER or nxt == '운')), t
        assert ko_cells(t).count(num) == sum(1 for i, ch in enumerate(t) if ch.isdigit() and (i == 0 or not t[i - 1].isdigit())), t
    # 안내 문장에 적은 사실 확인: 첫 보기 문장 = 약어 + 수표·숫자 + 가·다 약자 + 받침 ㅆ 약자 + 마침표
    first = ko_uses_abbr(SHOW[0])
    assert first == ['그런데', '가', '다'] and ko_cells('왔')[-1:] == asc('/') and ko_cells(SHOW[0])[-1:] == asc('4'), first
    for t in SHOW[:-1] + READ_ITEMS + WRITE_ITEMS:
        assert ko_uses_abbr(t), t  # 문장마다 약자나 약어가 하나 이상 있다

    def card(t):
        return {'name': t, 'cells': ko_cells(t), 'labels': None, 'line': dots_text(ko_cells(t))}

    rules = [
        ('제40항', '숫자는 수표 ⠼을 앞세워 다음과 같이 적는다.'),
        ('제44항', '숫자 뒤에 이어 나오는 한글의 띄어쓰기는 묵자를 따른다.'),
        ('제49항', '문장 부호는 다음과 같이 적는다. 띄어쓰기는 묵자를 따르되, 「한글 맞춤법」의 [부록] 문장 부호의 규정을 준수한다.'),
    ]
    learn = [
        {'title': '숫자 뒤에 한글 이어 적기', 'blocks': [
            {'t': 'p', 'text': '숫자 앞에는 수표를 적고, 숫자 뒤 한글은 글자(묵자)와 똑같이 붙이거나 띄어 적습니다. 아래는 규정집 제44항의 보기입니다. 숫자 뒤에 붙여 쓰지 않는 글자도 있는데, 24단원에서 배웁니다.'},
            {'t': 'cards', 'items': [card(t) for t in SHOW_NUM]},
        ]},
        {'title': '모두 섞은 문장', 'blocks': [
            {'t': 'p', 'text': '「그런데 5월에 비가 왔다.」에는 약어(그런데), 수표와 숫자(5), 가·다 약자, 받침 ㅆ 약자(왔), 마침표가 모두 들어 있습니다. 마지막 문장은 규정집 제49항의 보기입니다.'},
            {'t': 'cards', 'items': [card(t) for t in SHOW]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 문장일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 문장을 숫자와 부호까지 괄호에 쓰세요. 「빈칸」은 띄어쓰기입니다.', 'blank': '(                )',
             'items': [{'name': dots_text(ko_cells(t)), 'cells': ko_cells(t), 'labels': None} for t in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 문장을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '숫자 앞에는 수표, 약자와 약어는 배운 대로, 띄어쓰기는 글자와 같게 적으세요.',
             'items': [{'ask': t, 'cells': len(ko_cells(t))} for t in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules,
        rule_src='「개정 한국 점자 규정」 제5장 제11절 제40항·제44항 (규정집 27~28쪽), 제2장 약자와 약어 (규정집 9~13쪽), 제6장 제13절 제49항 (규정집 31쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '숫자 앞에는 수표를 적습니다. 예) 5월 → ' + braille(ko_cells('5월')),
            '숫자 뒤 한글의 띄어쓰기는 글자(묵자)와 같습니다.',
            '약자와 약어, 문장 부호는 배운 대로 적습니다. 예) 그러나 비가 와요! → ' + braille(ko_cells('그러나 비가 와요!')),
        ],
        learn=learn, practice=practice,
        checks=[
            '숫자와 한글이 섞인 낱말을 읽고 쓸 수 있다.',
            '약자, 약어, 문장 부호가 섞인 문장을 읽을 수 있다.',
            '배운 점자를 모두 써서 짧은 문장을 적을 수 있다.',
        ],
        answers=[
            ('읽기 연습', '    '.join(f'({i}) {t}' for i, t in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', '    '.join(f'({i}) {t} {braille(ko_cells(t))} {dots_text(ko_cells(t))}' for i, t in enumerate(WRITE_ITEMS, 1))),
        ],
    )
