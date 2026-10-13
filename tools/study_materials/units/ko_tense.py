"""한글 7단원 「쌍자음」. 근거: 제1장 제1절 제2항 (규정집 3~4쪽).

규정집 표와 보기는 점자 ASCII 글꼴로 실려 있어 그대로 옮기고, 앱 카드를 이어 붙인 점형과 같은지 확인한다.
"""
from common import app_cards, asc, braille, cell_labels, dots_text, standard_doc, unit_data

UNIT_ID = 'ko-tense'
# 제2항 표 (규정집 4쪽)
RULE_TABLE = {'ㄲ': ',@', 'ㄸ': ',i', 'ㅃ': ',^', 'ㅆ': ',,', 'ㅉ': ',.'}
NAMES = {'ㄲ': '쌍기역', 'ㄸ': '쌍디귿', 'ㅃ': '쌍비읍', 'ㅆ': '쌍시옷', 'ㅉ': '쌍지읒'}
BASE = {'ㄲ': 'ㄱ', 'ㄸ': 'ㄷ', 'ㅃ': 'ㅂ', 'ㅆ': 'ㅅ', 'ㅉ': 'ㅈ'}
# 제2항 보기 (규정집 4쪽) 가운데 받침이 없는 것, 제6항 보기 코끼리 (규정집 5쪽)
RULE_WORDS = {'꾸러미': ',@m"seo', '두꺼비': 'im,@s~o', '허리띠': 'js"o,io', '뻐꾸기': ',~s,@m@o', '고삐': '@u,~o',
              '쓰기': ',,{@o', '아저씨': '<.s,,o', '쭈르르': ',.m"{"{', '버찌': '~s,.o', '코끼리': 'fu,@o"o'}
CHO = ['ㄲ', 'ㄸ', 'ㅃ', 'ㅆ', 'ㅉ']
JUNG = ['ㅏ', 'ㅑ', 'ㅓ', 'ㅕ', 'ㅗ', 'ㅛ', 'ㅜ', 'ㅠ', 'ㅡ', 'ㅣ']
SHOW_WORDS = ['꾸러미', '두꺼비', '쓰기', '아저씨']
READ_ITEMS = ['허리띠', '뻐꾸기', '고삐', '버찌']
WRITE_ITEMS = ['쭈르르', '코끼리', '토끼', '꼬리']


def compose(cho, jung):
    return chr(0xAC00 + ('ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'.index(cho) * 21 + 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'.index(jung)) * 28)


def build():
    u = unit_data(UNIT_ID)
    mine = app_cards(UNIT_ID)
    cards = {c['letter']: c for c in app_cards('ko-syllable') + mine}  # 낱말에는 5단원 음절도 쓴다
    jamo = {c['letter']: c['dots'] for c in mine if c['kind'] == 'chosung'}
    initial = {c['letter']: c['dots'][0] for c in app_cards('ko-initial')}

    def word(w):
        return [c for syl in w for c in cards[syl]['dots']]

    def labels(w):
        return [l for syl in w for l in cell_labels(cards[syl])]

    # 앱 카드 = 규정집 제2항 표와 보기
    assert set(jamo) == set(RULE_TABLE)
    for ch, a in RULE_TABLE.items():
        assert jamo[ch] == asc(a), ch
    for w, a in RULE_WORDS.items():
        assert word(w) == asc(a), w
    # 안내 문장에 적은 사실 확인
    sign = asc(',')[0]
    assert sign == [6] and initial['ㅅ'] == [6]
    for ch in CHO:
        assert jamo[ch] == [sign, initial[BASE[ch]]], ch
    missing = [compose(c, j) for c in CHO for j in JUNG if compose(c, j) not in cards]
    assert missing == list('까따빠싸짜'), missing
    assert len(word('토끼')) == 5 and len(word('꼬리')) == 5

    def jamo_card(ch):
        return {'name': f'{ch} ({NAMES[ch]})', 'cells': jamo[ch], 'labels': ['된소리표', BASE[ch]], 'line': dots_text(jamo[ch])}

    def card(w):
        return {'name': w, 'cells': word(w), 'labels': labels(w), 'line': dots_text(word(w))}

    rows = []
    for c in CHO:
        row = [c]
        for j in JUNG:
            s = compose(c, j)
            row.append(f'{s} {braille(cards[s]["dots"])}' if s in cards else f'{s} (약자)')
        rows.append(row)

    rules = [('제2항', '된소리 글자 ‘ㄲ, ㄸ, ㅃ, ㅆ, ㅉ’이 첫소리로 쓰일 때에는 ‘ㄱ, ㄷ, ㅂ, ㅅ, ㅈ’ 앞에 된소리표 ⠠을 적어 나타낸다.')]
    learn = [
        {'title': '된소리표', 'blocks': [
            {'t': 'p', 'text': '된소리표는 「다음 자음을 된소리로 읽어라」라는 표시입니다. 쌍자음은 같은 자음을 두 번 적지 않고, 된소리표 뒤에 기본 자음을 한 번 적습니다.'},
            {'t': 'cards', 'items': [{'name': '된소리표', 'cells': [sign], 'labels': ['된소리표'], 'line': f'{dots_text([sign])}. 점칸 오른쪽 아래 점 하나입니다.'}]},
        ]},
        {'title': '쌍자음 5개', 'blocks': [
            {'t': 'p', 'text': '쌍자음은 두 칸입니다. 첫 칸은 된소리표, 둘째 칸은 3단원에서 배운 초성 자음입니다.'},
            {'t': 'cards', 'items': [jamo_card(c) for c in CHO]},
        ]},
        {'title': '헷갈리기 쉬운 ㅆ', 'blocks': [
            {'t': 'cards', 'caption': f'된소리표와 ㅅ은 둘 다 {dots_text([sign])}입니다. 그래서 ㅆ은 6점이 두 번 이어집니다. 앞의 6점은 된소리표, 뒤의 6점은 ㅅ입니다.',
             'items': [jamo_card('ㅆ'), {'name': 'ㅅ', 'cells': [initial['ㅅ']], 'labels': ['ㅅ'], 'line': dots_text([initial['ㅅ']])}]},
        ]},
        {'title': '쌍자음 음절표', 'blocks': [
            {'t': 'p', 'text': '줄은 쌍자음, 칸은 모음입니다. 「약자」라고 적힌 까·따·빠·싸·짜는 약자 단원에서 배웁니다.'},
            {'t': 'table', 'caption': '쌍자음 음절표 (쌍자음 × 기본 모음, 받침 없음)', 'head': ['초성'] + JUNG, 'rows': rows},
        ]},
        {'title': '규정집 보기 낱말', 'blocks': [
            {'t': 'p', 'text': '규정집 제2항의 보기 낱말입니다. 쌍자음이 있는 음절은 세 칸이 됩니다.'},
            {'t': 'cards', 'items': [card(w) for w in SHOW_WORDS]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. 6점 뒤에 자음이 오면 된소리표인지 살펴보세요.', 'blank': '(            )',
             'items': [{'name': dots_text(word(w)), 'cells': word(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '쌍자음은 된소리표와 기본 자음 두 칸으로 칠하세요.',
             'items': [{'ask': w, 'cells': len(word(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제1장 제1절 첫소리로 쓰인 자음자 (규정집 3~4쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            f'된소리표는 {dots_text([sign])}({braille([sign])})입니다.',
            '쌍자음 = 된소리표 + 기본 자음. 예) ㄲ → ' + braille(jamo['ㄲ']) + ' (6점 + 4점)',
            '규정집 표: ' + ', '.join(f'{c} {braille(jamo[c])}' for c in CHO),
        ],
        learn=learn, practice=practice,
        checks=[
            '된소리표의 점 번호(6점)를 말할 수 있다.',
            '쌍자음 5개를 된소리표와 기본 자음으로 읽고 쓸 수 있다.',
            'ㅆ의 6점 두 개 가운데 앞은 된소리표라는 것을 안다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(word(w))} {dots_text(word(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
