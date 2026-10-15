"""영어 2단원 「점자 부호와 문장 부호」.

근거: 「개정 한국 점자 규정」 제28항 [붙임](규정집 20쪽), 제33항(22쪽), 제40항(27쪽), [부록 1] 영어 문장 부호 표(208쪽).
1급 점자표는 한글 규정집에 없어 「통일영어점자 규정」 5.2절(UEB 규정집 57쪽)을 따른다.
부호 점형은 앱 카드에서 가져와 규정집 표(점자 ASCII)와 대조하고, 보기 낱말은 영어 엔진으로 적어 규정집 보기와 대조한다.
"""
from common import app_cards, asc, braille, dots_text, reg_cells, standard_doc, unit_data
from en_common import KO_RULES, cells_of, check_ueb, en_cells, ko_rule

UNIT_ID = 'en-sign'
# [부록 1] 영어 문장 부호 표 (규정집 208쪽, 점자 ASCII)
MARK_TABLE = {',': '1', ';': '2', ':': '3', '.': '4', '?': '8', '!': '6', "'": "'", '“': '8', '”': '0', '‘': ',8', '’': ',0',
              '(': '"<', ')': '">', '[': '.<', ']': '.>', '…': '444', '-': '-', '—': ',-', '_': '.-', '/': '_/', '*': '"9',
              '대문자 기호표': ',', '이탤릭체 기호표': '.2', '굵은 글자체 기호표': '^2'}
# 제28항 [붙임] 대문자 표시 (규정집 20쪽)
CAP_TABLE = {'대문자 기호표': ',', '대문자 단어표': ',,', '대문자 구절표': ',,,', '대문자 종료표': ",'"}
CAP_EXAMPLES = {'New York': ',new`,york', 'NEW YORK': ',,new`,,york', 'McDonald': ',mc,donald', 'IoT': ',io,t', 'iOS': 'i,,os'}
CAP_PASSAGE = ('WELCOME TO KOREA', ",,,welcome`to`korea,'")  # 세 낱말 이상: 대문자 구절표 ~ 대문자 종료표
# 제40항 (규정집 27쪽)
NUM_TABLE = {'1': '#a', '2': '#b', '3': '#c', '4': '#d', '5': '#e', '6': '#f', '7': '#g', '8': '#h', '9': '#i', '0': '#j'}
NUM_EXAMPLES = {'10': '#aj', '99': '#ii', '375': '#cge'}
# UEB 5.2.1 보기 (UEB 규정집 57쪽): 숫자 뒤 소문자 a~j는 숫자로 읽히지 않게 1급 점자표를 붙인다. 대문자·k 이후 글자는 붙이지 않는다.
GRADE1_EXAMPLES = {'22b': '⠼⠃⠃⠰⠃', '22B': '⠼⠃⠃⠠⠃', '22p': '⠼⠃⠃⠏'}

NAMES = {',': '쉼표', '.': '마침표', '?': '물음표', '!': '느낌표', ':': '쌍점', ';': '쌍반점', '‘': '여는 작은따옴표',
         '’': '닫는 작은따옴표', '“': '여는 큰따옴표', '”': '닫는 큰따옴표', "'": '아포스트로피', '(': '여는 소괄호',
         ')': '닫는 소괄호', '[': '여는 대괄호', ']': '닫는 대괄호', '…': '줄임표', '-': '붙임표', '—': '줄표', '/': '빗금',
         '*': '별표', '_': '아래선'}
MARK_GROUPS = [
    ('문장 끝에 쓰는 부호', ['.', '?', '!'], '마침표, 물음표, 느낌표는 모두 한 칸이고 칸의 아래쪽 점만 씁니다.'),
    ('쉼표, 쌍점, 쌍반점', [',', ':', ';'], '세 부호는 「한글 점자」와 점형이 다릅니다. 영어 문장 안에서는 이 점형을 쓰고, 한글 문장 안에서는 한글 점자로 적습니다 (제33항).'),
    ('따옴표와 아포스트로피', ['“', '”', '‘', '’', "'"], '작은따옴표는 큰따옴표 앞에 6점을 더한 두 칸입니다.'),
    ('괄호', ['(', ')', '[', ']'], '소괄호는 5점, 대괄호는 4·6점을 앞에 둡니다.'),
    ('그 밖의 부호', ['…', '-', '—', '/', '*', '_'], '줄표(―)도 「한글 점자」와 점형이 달라, 한글 문장 안에서는 한글 점자로 적습니다 (제33항).'),
]
READ_ITEMS = ['7', '375', '22b', 'Kim', 'TOP', 'Run!', 'Hi, Sam.', 'Help me.']
WRITE_ITEMS = ['10', '99', '22B', 'NEW', 'OK!', 'Yes, no.', 'Tom, run!', 'pop-up']
UEB_RULE = ('UEB 5.2.1', 'The grade 1 symbol indicator sets grade 1 mode for the next symbol. '
                         '(풀이: 1급 점자표는 바로 뒤의 한 기호를 약자나 숫자가 아닌 글자로 읽게 합니다.)')


def build():
    u = unit_data(UNIT_ID)
    raw = app_cards(UNIT_ID)
    cards = {c['letter']: c['dots'] for c in raw}
    letters = {c['letter']: c['dots'] for c in app_cards('en-letter')}
    # 앱 카드 = 규정집 표
    for k, a in MARK_TABLE.items():
        assert cards[k] == asc(a), k
    for k, a in CAP_TABLE.items():
        assert cards[k] == asc(a), k
    assert cards['수표'] == asc('#') and cards['1급 점자표'] == [[5, 6]]  # UEB 5.2 ⠰
    for n, a in NUM_TABLE.items():
        assert cards[n] == asc(a) == en_cells(n), n
        assert cards[n] == cards['수표'] + letters['jabcdefghi'[int(n)]], n  # 숫자 = 수표 + a~j
    for n, a in {**NUM_EXAMPLES}.items():
        assert en_cells(n) == asc(a), n
    for t, a in CAP_EXAMPLES.items():
        assert en_cells(t) == reg_cells(a), t
    check_ueb(GRADE1_EXAMPLES)
    assert len(raw) == 39
    # 안내 문장에 적은 사실 확인
    assert all(len(cards[m]) == 1 and not set(cards[m][0]) & {1, 4} for m in '.?!')
    assert all(cards[q] == [[6]] + cards[d] for q, d in (('‘', '“'), ('’', '”')))
    assert cards['('][0] == cards[')'][0] == [5] and cards['['][0] == cards[']'][0] == [4, 6]
    assert cards['?'] == cards['“']  # 물음표 = 여는 큰따옴표
    ko = {c['letter']: c['dots'] for c in app_cards('ko-mark-pause')}
    assert ko[','] != cards[','] and ko[':'] != cards[':']
    assert cells_of('⠲') == cards['.']  # 로마자 종료표(제29항) = 영어 마침표 점형

    def card(k, name=None):
        return {'name': name or (f'{NAMES[k]} ( {k} )' if k in NAMES else k), 'cells': cards[k], 'labels': None, 'line': dots_text(cards[k])}

    def word(t, cells=None):
        cells = cells or en_cells(t)
        return {'name': t, 'cells': cells, 'labels': None, 'line': dots_text(cells)}

    learn = [
        {'title': '수표와 숫자', 'blocks': [
            {'t': 'p', 'text': '숫자는 수표(3·4·5·6점) 뒤에 a~j의 점형을 적습니다. 1은 a, 2는 b, …, 9는 i, 0은 j와 같은 점형입니다. 한글 점자와 같습니다 (제40항).'},
            {'t': 'cards', 'items': [card('수표')] + [card(n, f'숫자 {n}') for n in '1234567890']},
            {'t': 'cards', 'caption': '여러 자리 숫자는 맨 앞에만 수표를 적습니다. (규정집 제40항 보기)', 'items': [word(n) for n in NUM_EXAMPLES]},
        ]},
        {'title': '1급 점자표', 'blocks': [
            {'t': 'p', 'text': '영어 점자에는 약자가 있어서, 같은 점형이 글자로도 약자로도 읽힐 수 있습니다. 1급 점자표(5·6점)는 바로 뒤 기호를 약자나 숫자가 아닌 '
                               '글자로 읽게 합니다. 예를 들어 숫자 뒤의 소문자 a~j는 숫자로 읽히지 않게 1급 점자표를 붙입니다. 대문자나 k 이후 글자는 붙이지 않습니다. '
                               '한글 규정집에는 이 기호가 없어 「통일영어점자 규정」 5.2절을 따릅니다.'},
            {'t': 'cards', 'items': [card('1급 점자표')] + [word(t) for t in GRADE1_EXAMPLES]},
        ]},
        {'title': '대문자 표시', 'blocks': [
            {'t': 'p', 'text': '대문자 한 글자 앞에는 대문자 기호표, 낱말 전체가 대문자이면 대문자 단어표를 적습니다. 세 낱말 이상이 모두 대문자이면 첫 낱말 앞에 '
                               '대문자 구절표, 마지막 낱말 뒤에 대문자 종료표를 적습니다 (제28항 [붙임]).'},
            {'t': 'cards', 'items': [card(k) for k in CAP_TABLE]},
            {'t': 'cards', 'caption': '규정집 제28항 [붙임]의 보기입니다.',
             'items': [word(t) for t in CAP_EXAMPLES] + [word(CAP_PASSAGE[0], reg_cells(CAP_PASSAGE[1]))]},
        ]},
        {'title': '글자체 기호표', 'blocks': [
            {'t': 'p', 'text': '기울인 글자(이탤릭체)나 굵은 글자 앞에 적습니다. 둘째 칸은 같은 2·3점이고, 첫째 칸으로 구별합니다.'},
            {'t': 'cards', 'items': [card('이탤릭체 기호표'), card('굵은 글자체 기호표')]},
        ]},
    ] + [
        {'title': title, 'blocks': [{'t': 'p', 'text': note}, {'t': 'cards', 'items': [card(m) for m in marks]}]}
        for title, marks, note in MARK_GROUPS
    ] + [
        {'title': '헷갈리기 쉬운 점형', 'blocks': [
            {'t': 'cards', 'caption': '물음표와 여는 큰따옴표는 점형이 같습니다. 문장 끝에 오면 물음표, 낱말 앞에 오면 여는 큰따옴표입니다.',
             'items': [card('?'), card('“')]},
            {'t': 'cards', 'caption': '영어 쉼표와 쌍점은 한글 점자와 점형이 다릅니다. 한글 문장 안에서는 한글 점자로 적습니다 (제33항).',
             'items': [card(','), {'name': '한글 쉼표', 'cells': ko[','], 'labels': None, 'line': dots_text(ko[','])},
                       card(':'), {'name': '한글 쌍점', 'cells': ko[':'], 'labels': None, 'line': dots_text(ko[':'])}]},
            {'t': 'cards', 'caption': '영어 마침표와 로마자 종료표는 점형이 같습니다 (제29항).',
             'items': [card('.'), {'name': '로마자 종료표', 'cells': cells_of('⠲'), 'labels': None, 'line': dots_text(cells_of('⠲'))}]},
        ]},
    ]
    practice = [
        {'title': '읽기 연습: 무엇이라고 썼을까요?', 'blocks': [
            {'t': 'read_ex', 'hint': '점형이나 점 번호를 보고, 숫자·대문자·부호까지 괄호에 쓰세요. 「빈칸」은 띄어쓰기입니다.', 'blank': '(              )',
             'items': [{'name': dots_text(en_cells(t)), 'cells': en_cells(t), 'labels': None} for t in READ_ITEMS]},
        ]},
        {'title': '쓰기 연습: 점자로 적어 보세요', 'blocks': [
            {'t': 'write_ex', 'hint': '수표, 대문자 표시, 부호도 한 칸씩 셉니다. 영어 문장 안의 쉼표는 영어 점형(2점)으로 적으세요.',
             'items': [{'ask': t, 'cells': len(en_cells(t))} for t in WRITE_ITEMS]},
        ]},
    ]
    return standard_doc(
        u, rules=ko_rule('제28항 [붙임]', '제33항', '제40항') + [UEB_RULE],
        rule_src=('「개정 한국 점자 규정」 제28항 [붙임], 제33항 (규정집 20~22쪽), 제40항 (27쪽), [부록 1] 영어 문장 부호 표 (208쪽), '
                  '「통일영어점자 규정」(UEB, 2024) 5.2절 (UEB 규정집 57쪽)'),
        key=u['teach']['line'],
        intro_bullets=[
            '숫자는 수표 ⠼ 뒤에 a~j의 점형을 적습니다. 예) 1 → ' + braille(cards['1']),
            '대문자 기호표 ⠠, 대문자 단어표 ⠠⠠, 대문자 구절표 ⠠⠠⠠, 대문자 종료표 ⠠⠄',
            '1급 점자표 ⠰는 뒤 기호를 약자나 숫자가 아닌 글자로 읽게 합니다.',
            '쉼표, 쌍점, 쌍반점, 줄표는 「한글 점자」와 점형이 달라 한글 문장 안에서는 한글 점자로 적습니다 (제33항).',
        ],
        learn=learn, practice=practice,
        checks=[
            '수표와 숫자 0~9의 점형을 읽고 쓸 수 있다.',
            '대문자 기호표·단어표·구절표·종료표를 구별할 수 있다.',
            '1급 점자표가 무엇을 하는지 안다.',
            '영어 문장 부호의 점형을 읽고 쓸 수 있다.',
            '쉼표·쌍점·쌍반점·줄표는 한글 문장 안에서 한글 점자로 적는다는 것을 안다.',
        ],
        answers=[
            ('읽기 연습', '    '.join(f'({i}) {t}' for i, t in enumerate(READ_ITEMS, 1))),
            ('쓰기 연습', '    '.join(f'({i}) {t} {braille(en_cells(t))} {dots_text(en_cells(t))}' for i, t in enumerate(WRITE_ITEMS, 1))),
        ],
    )


assert KO_RULES['제40항']
