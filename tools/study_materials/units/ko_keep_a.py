"""한글 12-1단원 「ㅏ를 생략하지 않는 경우」. 근거: 제2장 제6절 제14항과 [붙임] (규정집 9~10쪽), 제13항 (규정집 9쪽).

규정집 보기는 점자 ASCII 글꼴로 실려 있어 그대로 옮기고, 앱 카드의 점형과 같은지 확인한다.
"""
from common import app_cards, asc, braille, cell_labels, dots_text, standard_doc, unit_data

UNIT_ID = 'ko-keep-a'
# 제14항·[붙임] 보기 (규정집 9~10쪽) 가운데 앱 카드에 있는 낱말
RULE_WORDS = {'나이': 'c<o', '다음': 'i<[5', '바위': '^<mr', '하얀': 'j<>3', '팠다': 'd</i'}
SAME_AS_INITIAL = ['나', '다', '마', '바', '자', '카', '타', '파', '하']  # 약자 점형 = 첫소리 점형
READ_ITEMS = ['마음', '자유', '타이어', '나무', '파일', '팠어']
WRITE_ITEMS = ['나이', '하얀', '바다', '자연', '가요', '팠다']


def build():
    u = unit_data(UNIT_ID)
    cards = {c['letter']: c for c in app_cards(UNIT_ID)}
    initial = {c['letter']: c['dots'][0] for c in app_cards('ko-initial')}
    abbr = {'나': 'c', '다': 'i', '마': 'e', '바': '^', '자': '.', '카': 'f', '타': 'h', '파': 'd', '하': 'j', '가': '$'}

    def cells(w):
        return cards[w]['dots']

    # 앱 카드 = 규정집 보기
    for w, a in RULE_WORDS.items():
        assert cells(w) == asc(a), w
    # 안내 문장에 적은 사실 확인: 나~하 약자는 첫소리와 점형이 같고, 가 약자는 다르다 (제1항·제13항 표)
    cho = dict(zip(SAME_AS_INITIAL, 'ㄴㄷㅁㅂㅈㅋㅌㅍㅎ'))
    for syl in SAME_AS_INITIAL:
        assert asc(abbr[syl]) == [initial[cho[syl]]], syl
    assert asc(abbr['가']) != [initial['ㄱ']]
    assert asc('c<o')[:1] == asc('c') and cells('나무')[0] == asc('c')[0]  # 나무의 나는 약자 그대로
    for w in READ_ITEMS + WRITE_ITEMS:
        assert w in cards, w

    def card(w, line=None):
        return {'name': w, 'cells': cells(w), 'labels': cell_labels(cards[w]), 'line': line or dots_text(cells(w))}

    groups = {k: [c['letter'] for c in app_cards(UNIT_ID) if c['letter'] in ws] for k, ws in (
        ('vowel', ['나이', '나와', '다음', '마음', '마을', '바위', '바이올린', '자연', '자유', '카운터', '타이어', '타원', '파일', '파업', '하얀', '따오기']),
        ('pat', ['팠다', '팠어']), ('keep', ['가위', '가요', '나무', '바다', '하늘']))}

    rules = [
        ('제13항', '다음 글자들은 약자를 사용하여 적는다. 가 나 다 마 바 사 자 카 타 파 하'),
        ('제14항', '‘나, 다, 마, 바, 자, 카, 타, 파, 하’에 모음이 붙어 나올 때에는 약자를 사용하지 않는다.'),
        ('[붙임]', '‘팠’을 적을 때에는 ‘ㅏ’를 생략하지 않고 적는다.'),
    ]
    learn = [
        {'title': '왜 ㅏ를 적을까요?', 'blocks': [
            {'t': 'p', 'text': '나·다·마·바·자·카·타·파·하의 약자는 첫소리 자음과 점형이 같습니다. 그래서 뒤에 모음이 바로 오면 「자음 + 모음」 한 글자로 잘못 읽힙니다. 예를 들어 나이를 약자로 ⠉⠕라고 쓰면 「니」로 읽힙니다. 그래서 이때는 ㅏ를 적습니다.'},
            {'t': 'cards', 'items': [card('나이', cards['나이']['line'])]},
        ]},
        {'title': '모음 앞에서 ㅏ를 적는 낱말', 'blocks': [
            {'t': 'p', 'text': '아래 낱말은 나·다·마·바·자·카·타·파·하 뒤에 모음으로 시작하는 글자가 옵니다. 첫소리 ㅇ은 적지 않으므로 ㅏ 뒤에 모음이 바로 이어집니다.'},
            {'t': 'cards', 'items': [card(w) for w in groups['vowel']]},
        ]},
        {'title': '팠은 늘 ㅏ를 적어요', 'blocks': [
            {'t': 'p', 'text': '팠은 뒤에 무엇이 오든 ㅏ를 생략하지 않습니다(제14항 [붙임]).'},
            {'t': 'cards', 'items': [card(w, cards[w]['line']) for w in groups['pat']]},
        ]},
        {'title': '약자를 그대로 쓰는 낱말', 'blocks': [
            {'t': 'p', 'text': '가는 약자 점형이 첫소리 ㄱ과 달라서 모음 앞에서도 약자를 씁니다. 나·바·하도 뒤에 자음이 오면 약자를 그대로 씁니다.'},
            {'t': 'cards', 'items': [card(w, cards[w]['line']) for w in groups['keep']]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. ㅏ가 적혀 있는지 살펴보세요.', 'blank': '(            )',
             'items': [{'name': dots_text(cells(w)), 'cells': cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '모음 앞의 나·다·마·바·자·카·타·파·하와 팠은 ㅏ를 적고, 그 밖에는 약자를 쓰세요.',
             'items': [{'ask': w, 'cells': len(cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제2장 제6절 약자 제13항·제14항 (규정집 9~10쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '나·다·마·바·자·카·타·파·하 + 모음 → ㅏ를 적습니다. 예) 나이 → ' + braille(cells('나이')),
            '팠은 언제나 ㅏ를 적습니다. 예) 팠다 → ' + braille(cells('팠다')),
            '가 약자, 그리고 뒤에 자음이 오는 경우는 약자를 그대로 씁니다. 예) 가요 → ' + braille(cells('가요')) + ', 나무 → ' + braille(cells('나무')),
        ],
        learn=learn, practice=practice,
        checks=[
            '나·다·마·바·자·카·타·파·하 약자가 첫소리와 점형이 같다는 것을 안다.',
            '모음 앞에서는 ㅏ를 적어야 한다는 것을 안다.',
            '팠은 늘 ㅏ를 적는다는 것을 안다.',
            '가 약자와 자음 앞의 약자는 그대로 쓴다는 것을 안다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(cells(w))} {dots_text(cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
