"""한글 17단원 「약어」. 근거: 제2장 제7절 제18항과 [붙임]·[다만] (규정집 12~13쪽).

규정집 표와 보기는 점자 ASCII 글꼴로 실려 있어 그대로 옮기고, 저장소 데이터로 이어 붙인 점형과 같은지 확인한다.
"""
from common import app_cards, asc, braille, dots_text, load_json, standard_doc, unit_data

UNIT_ID = 'ko-word'
ORDER = ['그래서', '그러나', '그러면', '그러므로', '그런데', '그리고', '그리하여']
# 제18항 표 (규정집 12쪽)
RULE_TABLE = {'그래서': 'as', '그러나': 'ac', '그러면': 'a3', '그러므로': 'a5', '그런데': 'an', '그리고': 'au', '그리하여': 'a:'}
# 낱말을 이루는 조각: ('w', 약어) ('a', 약자) ('c', 첫소리) ('v', 모음)
PARTS = {
    '그래서인지': [('w', '그래서'), ('a', '인'), ('c', 'ㅈ'), ('v', 'ㅣ')],
    '그런데도': [('w', '그런데'), ('c', 'ㄷ'), ('v', 'ㅗ')],
    '그러면서': [('w', '그러면'), ('c', 'ㅅ'), ('v', 'ㅓ')],
    '그리하여도': [('w', '그리하여'), ('c', 'ㄷ'), ('v', 'ㅗ')],
    '그리고서': [('w', '그리고'), ('c', 'ㅅ'), ('v', 'ㅓ')],
    '오그리고': [('v', 'ㅗ'), ('c', 'ㄱ'), ('v', 'ㅡ'), ('c', 'ㄹ'), ('v', 'ㅣ'), ('c', 'ㄱ'), ('v', 'ㅗ')],
    '쭈그리고': [('t', 'ㅉ'), ('v', 'ㅜ'), ('c', 'ㄱ'), ('v', 'ㅡ'), ('c', 'ㄹ'), ('v', 'ㅣ'), ('c', 'ㄱ'), ('v', 'ㅗ')],
}
# 제18항 [붙임]·[다만]과 보기 문장 속 낱말 (규정집 13쪽)
RULE_WORDS = {'그래서인지': 'asq.o', '그런데도': 'aniu', '그러면서': 'a3,s', '그리하여도': 'a:iu', '그리고서': 'au,s',
              '오그리고': 'u@{"o@u', '쭈그리고': ',.m@{"o@u'}
READ_ITEMS = ['그러면', '그리하여', '그래서', '그런데도', '그러나', '그리고']
WRITE_ITEMS = ['그러므로', '그런데', '그러나', '그리고서', '그러면서', '그리하여도']


def build():
    u = unit_data(UNIT_ID)
    words = {c['letter']: c['dots'] for c in app_cards(UNIT_ID)}
    ko = load_json('data', 'ko', 'ko.json')

    def one(item):
        d = item['dots']
        return [d] if isinstance(d[0], int) else d

    def piece(kind, key):
        if kind == 'w':
            return words[key]
        if kind == 'a':
            return one(ko['abbreviation_syllable']['items'][key])
        if kind in ('c', 't'):
            return one(ko['chosung']['items'][key])
        return one(ko['jungsung']['items'][key])

    def cells(w):
        if w in words:
            return words[w]
        return [c for k, key in PARTS[w] for c in piece(k, key)]

    def labels(w):
        if w in words:
            return ['약어', '약어']
        out = []
        for k, key in PARTS[w]:
            if k == 'w':
                out += ['약어', '약어']
            elif k == 'a':
                out.append(f'{key} 약자')
            elif k == 't':
                out += ['된소리표', 'ㅈ']
            else:
                out.append(key)
        return out

    # 저장소 = 규정집 표와 보기
    assert list(words) == ORDER
    for w, a in {**RULE_TABLE, **RULE_WORDS}.items():
        assert cells(w) == asc(a), w
    # 안내 문장에 적은 사실 확인
    assert all(len(words[w]) == 2 and words[w][0] == [1] for w in ORDER)
    assert cells('오그리고')[1:2] != [[1]]  # 앞에 글자가 붙으면 약어 첫 칸(1점)이 나오지 않는다

    def card(w, line=None):
        return {'name': w, 'cells': cells(w), 'labels': labels(w), 'line': line or dots_text(cells(w))}

    rules = [
        ('제18항', '다음 단어들은 약어를 사용하여 적는다. 그래서 그러나 그러면 그러므로 그런데 그리고 그리하여'),
        ('[붙임]', '약어 뒤에 다른 글자가 붙어 나올 때에도 약어를 사용하여 적는다.'),
        ('[다만]', '약어 앞에 다른 글자가 붙어 나올 때에는 약어를 사용하지 않는다.'),
    ]
    learn = [
        {'title': '약어 7개', 'blocks': [
            {'t': 'p', 'text': '약어는 낱말 하나를 두 칸으로 줄여 적는 것입니다. 일곱 개 모두 첫 칸이 1점입니다. 둘째 칸으로 어떤 약어인지 구별합니다.'},
            {'t': 'cards', 'items': [card(w) for w in ORDER]},
        ]},
        {'title': '뒤에 글자가 붙어도 약어를 써요', 'blocks': [
            {'t': 'p', 'text': '약어 뒤에 다른 글자가 붙으면, 약어를 먼저 적고 뒤 글자를 이어 적습니다(제18항 [붙임]).'},
            {'t': 'cards', 'items': [card(w) for w in ['그래서인지', '그런데도', '그리하여도']]},
        ]},
        {'title': '앞에 글자가 붙으면 약어를 쓰지 않아요', 'blocks': [
            {'t': 'p', 'text': '오그리고, 쭈그리고처럼 약어 앞에 다른 글자가 붙으면 약어를 쓰지 않고 글자를 하나하나 적습니다(제18항 [다만]).'},
            {'t': 'cards', 'items': [card(w) for w in ['오그리고', '쭈그리고']]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 어떤 낱말일까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 낱말을 괄호에 쓰세요. 1점으로 시작하는 두 칸이면 약어인지 살펴보세요.', 'blank': '(            )',
             'items': [{'name': dots_text(cells(w)), 'cells': cells(w), 'labels': None} for w in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 낱말을 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '약어는 두 칸으로 적고, 뒤에 붙은 글자는 이어 적으세요.',
             'items': [{'ask': w, 'cells': len(cells(w))} for w in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=rules, rule_src='「개정 한국 점자 규정」 제2장 제7절 약어 제18항 (규정집 12~13쪽)',
        key=u['teach']['line'],
        intro_bullets=[
            '약어 7개: ' + ', '.join(f'{w} {braille(words[w])}' for w in ORDER),
            '뒤에 글자가 붙어도 약어를 씁니다. 예) 그런데도 → ' + braille(cells('그런데도')),
            '앞에 글자가 붙으면 약어를 쓰지 않습니다. 예) 오그리고 → ' + braille(cells('오그리고')),
        ],
        learn=learn, practice=practice,
        checks=[
            '약어 7개를 읽고 쓸 수 있다.',
            '약어 뒤에 글자가 붙어도 약어를 쓴다는 것을 안다.',
            '약어 앞에 글자가 붙으면 약어를 쓰지 않는다는 것을 안다.',
        ],
        answers=[
            ('읽기 연습', ', '.join(f'({i}) {w}' for i, w in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', ', '.join(f'({i}) {w} {braille(cells(w))} {dots_text(cells(w))}' for i, w in enumerate(WRITE_ITEMS, 1))),
        ],
    )
