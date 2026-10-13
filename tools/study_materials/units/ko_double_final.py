"""한글 9단원 「쌍받침, 겹받침」. 근거: 제1장 제2절 제4항·제5항 (규정집 4~5쪽).

규정집 표와 보기는 점자 ASCII 글꼴로 실려 있어 그대로 옮기고, 앱 카드와 번역 엔진의 점형이 같은지 확인한다.
겹받침 ㄾ·ㄿ은 제5항대로 ⠂⠦·⠂⠲이다 (2026-10-13 저장소 데이터를 규정대로 고침).
약자(다·하·사, 받침 ㅆ)를 쓰는 보기(겪다, 핥다, 품삯, 있다)는 약자 단원에서 다룬다.
"""
from common import app_cards, asc, braille, cell_labels, dots_text, jamo_spell, ko_cells, ko_uses_abbr, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-double-final'
# 제4항 ㄲ, 제5항 표 (규정집 4~5쪽)
RULE_TABLE = {'ㄲ': 'aa', 'ㄳ': "a'", 'ㄵ': '3k', 'ㄶ': '30', 'ㄺ': '1a', 'ㄻ': '15', 'ㄼ': '1b', 'ㄽ': "1'",
              'ㄾ': '18', 'ㄿ': '14', 'ㅀ': '10', 'ㅄ': "b'"}
PARTS = {'ㄲ': 'ㄱㄱ', 'ㄳ': 'ㄱㅅ', 'ㄵ': 'ㄴㅈ', 'ㄶ': 'ㄴㅎ', 'ㄺ': 'ㄹㄱ', 'ㄻ': 'ㄹㅁ', 'ㄼ': 'ㄹㅂ', 'ㄽ': 'ㄹㅅ',
         'ㄾ': 'ㄹㅌ', 'ㄿ': 'ㄹㅍ', 'ㅀ': 'ㄹㅎ', 'ㅄ': 'ㅂㅅ'}
# 제4·5항 보기 가운데 약자가 없는 낱말
RULE_WORDS = {'묶음': 'emaa[5', '외곬': "y@u1'"}
SHOW = ['겪', '않', '옳', '곬']
READ_ITEMS = ['잃', '싫', '옮', '칡']
WRITE_ITEMS = ['읽', '없', '앉', '묶', '외곬']


def build():
    u = unit_data(UNIT_ID)
    cards = app_cards(UNIT_ID)
    jong = {c['letter']: c['dots'] for c in cards if c['kind'] == 'jongsung'}
    syl = {c['letter']: c for c in cards if c['kind'] != 'jongsung'}
    single = {c['letter']: c['dots'][0] for c in app_cards('ko-final') if c['kind'] == 'jongsung'}
    # 앱 카드 = 규정집 표, 엔진 = 규정집 보기
    assert list(jong) == list(RULE_TABLE)
    for k, a in RULE_TABLE.items():
        assert jong[k] == asc(a), k
        assert jong[k] == [single[p] for p in PARTS[k]], k  # 받침 두 개를 이어 적는다
    for w, a in RULE_WORDS.items():
        assert ko_cells(w) == reg_cells(a), w
    for s in SHOW + READ_ITEMS + WRITE_ITEMS:
        assert ko_uses_abbr(s) == [] and jamo_spell(s)[0] == ko_cells(s), s
        if s in syl:
            assert syl[s]['dots'] == ko_cells(s), s

    def jcard(k):
        return {'name': f'받침 {k}', 'cells': jong[k], 'labels': list(PARTS[k]), 'line': dots_text(jong[k])}

    def scard(s):
        if s in syl:
            return {'name': s, 'cells': syl[s]['dots'], 'labels': cell_labels(syl[s]), 'line': dots_text(syl[s]['dots'])}
        cells, labels = jamo_spell(s)
        return {'name': s, 'cells': cells, 'labels': labels, 'line': dots_text(cells)}

    rules = [
        ('제4항', '쌍받침 ‘ㄲ’은 ⠁⠁으로 적고, 쌍받침 ‘ㅆ’은 약자인 ⠌으로 적는다.'),
        ('제5항', '겹받침은 각 받침 글자를 어울러 다음과 같이 적는다.'),
    ]
    keys = list(RULE_TABLE)
    learn = [
        {'title': '쌍받침 ㄲ과 겹받침 11개', 'blocks': [
            {'t': 'p', 'text': '쌍받침과 겹받침은 8단원에서 배운 받침 두 개를 차례로 이어 두 칸으로 적습니다. 쌍받침 ㄲ은 받침 ㄱ을 두 번 적습니다.'},
            {'t': 'cards', 'items': [jcard(k) for k in keys[:6]]},
            {'t': 'cards', 'items': [jcard(k) for k in keys[6:]]},
        ]},
        {'title': '쌍받침 ㅆ', 'blocks': [
            {'t': 'p', 'text': '쌍받침 ㅆ은 받침 ㅅ을 두 번 적지 않고 약자 ' + braille(asc('/')) + '(' + dots_text(asc('/')) + ') 한 칸으로 적습니다(제4항). 13단원 「것과 받침 ㅆ 약자」에서 자세히 배웁니다.'},
        ]},
        {'title': '쌍받침·겹받침이 있는 글자', 'blocks': [
            {'t': 'p', 'text': '첫소리, 모음, 받침 두 칸 순서로 적습니다. 묶음은 규정집 제4항의 보기 낱말입니다.'},
            {'t': 'cards', 'items': [scard(s) for s in SHOW]},
            {'t': 'cards', 'items': [scard('묶음')]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 글자일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 글자를 괄호에 쓰세요. 모음 뒤에 받침이 두 칸 있는지 살펴보세요.', 'blank': '(          )',
             'items': [{'name': dots_text(ko_cells(s)), 'cells': ko_cells(s), 'labels': None} for s in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '겹받침은 앞 받침과 뒤 받침을 차례로 두 칸에 적으세요.',
             'items': [{'ask': s, 'cells': len(ko_cells(s))} for s in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제1장 제2절 받침으로 쓰인 자음자 제4항·제5항 (규정집 4~5쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '쌍받침 ㄲ = 받침 ㄱ + 받침 ㄱ → ' + braille(jong['ㄲ']),
            '겹받침 = 앞 받침 + 뒤 받침. 예) ㄺ = ㄹ + ㄱ → ' + braille(jong['ㄺ']),
            '쌍받침 ㅆ은 약자 한 칸으로 적으며 13단원에서 배웁니다.',
        ],
        learn=learn, practice=practice,
        checks=[
            '쌍받침 ㄲ과 겹받침 11개를 받침 두 칸으로 적을 수 있다.',
            '쌍받침·겹받침이 있는 글자를 읽고 쓸 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {s}' for i, s in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {s} {braille(ko_cells(s))} {dots_text(ko_cells(s))}' for i, s in enumerate(WRITE_ITEMS, 1))),
        ],
    )
