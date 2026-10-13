"""한글 10단원 「정자 점자의 활용」. 근거: 한국 점자 표기의 기본 원칙 제3항 (규정집 1쪽), 제1·2·3항 (규정집 3~4쪽), 제6항 (규정집 5쪽).

정자 = 약자·약어를 쓰지 않고 자모를 하나하나 풀어 적은 점자.
낱말은 규정집 제2·3항 보기 가운데 약자가 없는 것만 쓰고, 점자 ASCII를 그대로 옮겨 엔진 결과와 같은지 확인한다.
문장은 엔진(engine/ko)으로 만들고, 저장소 자모 점형을 풀어 이은 것과 같은지, 약자가 하나도 없는지 확인한다.
허락 대기 중인 점형(ㅚ, 받침 ㅋ·ㅌ·ㅍ, 겹받침)과 받침 ㅆ(약자)은 넣지 않는다.
"""
from common import braille, dots_text, jamo_spell, ko_cells, ko_uses_abbr, reg_cells, standard_doc, unit_data

UNIT_ID = 'ko-plain-sentence'
# 제2항·제3항 보기 (규정집 3~4쪽, 점자 글꼴 그대로)
RULE_WORDS = {
    '국보': '@ma~u', '놀이': 'cu1o', '향기': 'j>7@o', '솜씨': ',u5,,o', '넙치': 'csb;o', '윤리': '%3"o', '싣고': ',o9@u',
    '뚜껑': ',im,@s7', '아저씨': '<.s,,o', '두꺼비': 'im,@s~o', '허리띠': 'js"o,io', '뻐꾸기': ',~s,@m@o',
}
SHOW_WORDS = ['국보', '놀이', '향기', '뚜껑', '아저씨', '넙치']
SHOW_SENTENCES = ['우리 고양이 귀여워요', '아기 오리 헤엄쳐요', '두꺼비 뛰어요']
READ_ITEMS = ['호랑이 무서워요', '우유 주세요', '솜씨 좋아요', '뻐꾸기 노래해요']
WRITE_ITEMS = ['개구리 뛰어요', '국수 주세요', '모두 모여요', '허리띠 매요']
AVOID = {'ㅚ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅆ'}  # 받침 ㅋ·ㅌ·ㅍ·ㅆ, 모음 ㅚ


def finals_and_vowels(text):
    out = set()
    for ch in text.replace(' ', ''):
        code = ord(ch) - 0xAC00
        out.add('ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'[code % 588 // 28])
        out.add(['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'][code % 28] or 'ㅇ')
    return out


def build():
    u = unit_data(UNIT_ID)
    # 엔진 = 규정집 보기
    for w, a in RULE_WORDS.items():
        assert ko_cells(w) == reg_cells(a), w
    for t in list(RULE_WORDS) + SHOW_SENTENCES + READ_ITEMS + WRITE_ITEMS:
        assert ko_uses_abbr(t) == [], t  # 약자·약어 없음
        assert jamo_spell(t)[0] == ko_cells(t), t  # 자모를 풀어 이은 것과 같음
        bad = finals_and_vowels(t) & AVOID
        assert not bad, (t, bad)
        assert not (finals_and_vowels(t) & set('ㄲㄳㄵㄶㄺㄻㄼㄽㄾㄿㅀㅄ')), t  # 쌍받침·겹받침 없음
    assert jamo_spell('아저씨')[1][0] == 'ㅏ' and '받침 ㅇ' in jamo_spell('향기')[1]  # 첫소리 ㅇ은 안 적고 받침 ㅇ은 적는다

    def word_card(w):
        cells, labels = jamo_spell(w)
        return {'name': w, 'cells': cells, 'labels': labels, 'line': dots_text(cells)}

    def sent(t):
        return {'name': t, 'cells': ko_cells(t), 'labels': None, 'line': dots_text(ko_cells(t))}

    rules = [
        ('기본 원칙 제3항', '한국 점자는 풀어쓰기 방식으로 적는다.'),
        ('제1항 [다만 1]', '‘ㅇ’이 첫소리로 쓰일 때에는 점자로 이를 표기하지 않는다.'),
        ('제2항', '된소리 글자 ‘ㄲ, ㄸ, ㅃ, ㅆ, ㅉ’이 첫소리로 쓰일 때에는 ‘ㄱ, ㄷ, ㅂ, ㅅ, ㅈ’ 앞에 된소리표 ⠠을 적어 나타낸다.'),
        ('제3항', '기본 자음자 14개가 받침으로 쓰일 때에는 다음과 같이 적는다.'),
    ]
    learn = [
        {'title': '풀어쓰기: 자모를 차례로 적어요', 'blocks': [
            {'t': 'p', 'text': '점자는 글자를 모아 쓰지 않고 첫소리, 모음, 받침 순서로 한 칸씩 풀어 적습니다. 첫소리 ㅇ은 적지 않지만 받침 ㅇ은 적습니다. 쌍자음은 된소리표 뒤에 자음을 적습니다. 아래는 규정집의 보기 낱말입니다.'},
            {'t': 'cards', 'items': [word_card(w) for w in SHOW_WORDS]},
        ]},
        {'title': '낱말을 이어 문장 만들기', 'blocks': [
            {'t': 'p', 'text': '낱말과 낱말 사이는 글자와 똑같이 한 칸 띄웁니다. 빈칸도 한 칸입니다.'},
            {'t': 'cards', 'items': [sent(t) for t in SHOW_SENTENCES]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 문장일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 문장을 괄호에 쓰세요. 「빈칸」은 띄어쓰기입니다.', 'blank': '(                )',
             'items': [{'name': dots_text(ko_cells(t)), 'cells': ko_cells(t), 'labels': None} for t in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 문장을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '첫소리, 모음, 받침 순서로 적고, 낱말 사이는 한 칸 띄우세요.',
             'items': [{'ask': t, 'cells': len(ko_cells(t))} for t in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules,
        rule_src='「개정 한국 점자 규정」 한국 점자 표기의 기본 원칙 제3항 (규정집 1쪽), 제1장 제1절 제1·2항, 제2절 제3항 (규정집 3~4쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '점자는 풀어쓰기로 적습니다. 예) 국보 → ' + braille(ko_cells('국보')) + ' (ㄱ ㅜ 받침ㄱ ㅂ ㅗ)',
            '첫소리 ㅇ은 적지 않고, 받침 ㅇ은 적습니다. 예) 향기 → ' + braille(ko_cells('향기')),
            '낱말 사이는 한 칸 띄웁니다. 예) 우유 주세요 → ' + braille(ko_cells('우유 주세요')),
            '이 단원의 낱말과 문장에는 약자가 없습니다. 약자는 다음 단원부터 배웁니다.',
        ],
        learn=learn, practice=practice,
        checks=[
            '첫소리, 모음, 받침을 차례로 풀어 적을 수 있다.',
            '첫소리 ㅇ은 적지 않고 받침 ㅇ은 적는다는 것을 안다.',
            '낱말 사이를 한 칸 띄워 짧은 문장을 읽고 쓸 수 있다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {t}' for i, t in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {t} {braille(ko_cells(t))} {dots_text(ko_cells(t))}' for i, t in enumerate(WRITE_ITEMS, 1))),
        ],
    )
