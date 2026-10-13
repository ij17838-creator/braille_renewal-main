"""한글 8단원 「홑받침」. 근거: 제1장 제2절 제3항 (규정집 4쪽).

규정집 표와 보기는 점자 ASCII 글꼴로 실려 있어 그대로 옮기고, 앱 카드와 번역 엔진의 점형이 같은지 확인한다.
받침 ㅋ·ㅌ·ㅍ은 제3항대로 ⠖·⠦·⠲이다 (2026-10-13 저장소 데이터를 규정대로 고침).
"""
from common import app_cards, asc, braille, dots_text, jamo_spell, ko_cells, ko_uses_abbr, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-final'
# 제3항 표 (규정집 4쪽)
RULE_TABLE = {'ㄱ': 'a', 'ㄴ': '3', 'ㄷ': '9', 'ㄹ': '1', 'ㅁ': '5', 'ㅂ': 'b', 'ㅅ': "'",
              'ㅇ': '7', 'ㅈ': 'k', 'ㅊ': '2', 'ㅋ': '6', 'ㅌ': '8', 'ㅍ': '4', 'ㅎ': '0'}
# 제3항 보기 (규정집 4쪽)
RULE_WORDS = {
    '국보': '@ma~u', '윤리': '%3"o', '놀이': 'cu1o', '솜씨': ',u5,,o', '놋그릇': "cu'@{\"{'", '향기': 'j>7@o',
    '윷놀이': '%2cu1o', '부엌': '~ms6', '앞집': '<4.ob', '히읗': 'jo{0', '싣고': ',o9@u', '넙치': 'csb;o',
    '엊저녁': 'sk.sc:a', '겉보리': '@s8~u"o',
}
SHOW = ['놀이', '부엌', '놋그릇', '앞집']
READ_ITEMS = ['솜씨', '윤리', '히읗', '싣고']
WRITE_ITEMS = ['국보', '향기', '넙치', '겉보리', '엊저녁', '윷놀이']


def build():
    u = unit_data(UNIT_ID)
    jong = {c['letter']: c['dots'] for c in app_cards(UNIT_ID) if c['kind'] == 'jongsung'}
    cho = {c['letter']: c['dots'] for c in app_cards('ko-initial')}
    # 앱 카드 = 규정집 제3항 표, 엔진 = 규정집 보기
    assert list(jong) == list(RULE_TABLE)
    for k, a in RULE_TABLE.items():
        assert jong[k] == asc(a), k
    for w, a in RULE_WORDS.items():
        assert ko_cells(w) == reg_cells(a), w
        assert ko_uses_abbr(w) == [] and jamo_spell(w)[0] == ko_cells(w), w  # 약자 없이 풀어 쓴 낱말
    # 안내 문장에 적은 사실 확인: 받침은 모두 한 칸이고 같은 자음의 초성과 점형이 다르다
    assert all(len(jong[k]) == 1 for k in RULE_TABLE)
    assert all(jong[k] != cho[k] for k in RULE_TABLE if k in cho)

    def jcard(k):
        return {'name': f'받침 {k}', 'cells': jong[k], 'labels': [k], 'line': dots_text(jong[k])}

    def word(w):
        cells, labels = jamo_spell(w)
        return {'name': w, 'cells': cells, 'labels': labels, 'line': dots_text(cells)}

    rows = [[k, f'{braille(cho[k])} {dots_text(cho[k])}' if k in cho and cho[k] else '(적지 않음)', f'{braille(jong[k])} {dots_text(jong[k])}']
            for k in RULE_TABLE]
    keys = list(RULE_TABLE)
    rules = [('제3항', '기본 자음자 14개가 받침으로 쓰일 때에는 다음과 같이 적는다.')]
    learn = [
        {'title': '받침 14개', 'blocks': [
            {'t': 'p', 'text': '받침은 모음 뒤에 한 칸으로 적습니다. 규정집 표의 순서대로 보입니다.'},
            {'t': 'cards', 'items': [jcard(k) for k in keys[:7]]},
            {'t': 'cards', 'items': [jcard(k) for k in keys[7:]]},
        ]},
        {'title': '초성과 받침 비교', 'blocks': [
            {'t': 'p', 'text': '같은 자음이라도 첫소리(초성)와 받침의 점형이 다릅니다. 첫소리 ㅇ은 적지 않지만 받침 ㅇ은 적습니다.'},
            {'t': 'table', 'caption': '자음별 초성과 받침 점형', 'head': ['자음', '초성', '받침'], 'rows': rows},
        ]},
        {'title': '받침이 있는 낱말', 'blocks': [
            {'t': 'p', 'text': '첫소리, 모음, 받침 순서로 한 칸씩 적습니다. 아래는 규정집 제3항의 보기 낱말입니다.'},
            {'t': 'cards', 'items': [word(w) for w in SHOW]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. 모음 뒤의 칸이 받침인지 살펴보세요.', 'blank': '(            )',
             'items': [{'name': dots_text(ko_cells(w)), 'cells': ko_cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '받침은 초성과 점형이 다릅니다. 첫소리, 모음, 받침 순서로 적으세요.',
             'items': [{'ask': w, 'cells': len(ko_cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제1장 제2절 받침으로 쓰인 자음자 제3항 (규정집 4쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '받침 14개: ' + ', '.join(f'{k} {braille(jong[k])}' for k in keys),
            '같은 자음이라도 초성과 받침의 점형이 다릅니다. 예) 초성 ㄱ ' + braille(cho['ㄱ']) + ', 받침 ㄱ ' + braille(jong['ㄱ']),
            '받침이 있는 글자는 첫소리, 모음, 받침 순서로 적습니다. 예) 국보 → ' + braille(ko_cells('국보')),
        ],
        learn=learn, practice=practice,
        checks=[
            '받침 14개의 점형을 읽고 쓸 수 있다.',
            '초성과 받침의 점형이 다르다는 것을 안다.',
            '받침이 있는 낱말을 읽고 쓸 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(ko_cells(w))} {dots_text(ko_cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
