"""학습자료 공통 틀.

단원 자료는 모두 같은 네 부분으로 짠다. 단원이 커지면 각 부분의 쪽수만 늘어난다.

  1. 들어가기   (1쪽)      사용 안내, 이번 단원에서 배울 것, 규정 알아보기, 핵심 정리
  2. 점형 익히기 (새 쪽)    점형 카드, 헷갈리기 쉬운 점형
  3. 연습하기   (새 쪽)    읽기 연습, 쓰기 연습
  4. 마무리     (새 쪽)    스스로 확인하기, 다음 단원 예고, 정답

한 단원 문서는 dict 하나다. 단원 파일(units/*.py)은 build(repo) -> dict 를 돌려준다.

  {
    'id', 'lang', 'order', 'part', 'title',
    'parts': [{'title', 'sections': [{'title', 'blocks': [...]}]}],
  }

블록 종류 (render_html.py, render_hwpx.py가 같은 종류를 그린다)
  {'t': 'p', 'text'}                         문단
  {'t': 'bullets', 'items', 'style'?}       점 목록 (style='guide'는 안내 상자)
  {'t': 'rules', 'items': [(항, 원문)], 'src'}  규정 원문
  {'t': 'key', 'text'}                       핵심 정리 상자
  {'t': 'big_cell'}                          점 번호를 적은 큰 점칸 (점의 자리 단원)
  {'t': 'cards', 'items': [card], 'caption'} 점형 카드
  {'t': 'read_ex', 'hint', 'items': [card]}  읽기 연습: 점형을 보고 답 쓰기
  {'t': 'write_ex', 'hint', 'items': [{'ask', 'cells'}]}  쓰기 연습: 빈 점칸 n개
  {'t': 'table', 'caption', 'head', 'rows'}  표 (첫 열은 행 제목, '고 ⠈⠥'처럼 글 뒤 점자는 줄을 나눔)
  {'t': 'checks', 'items'}                   스스로 확인하기
  {'t': 'next', 'text'}                      다음 단원 예고
  {'t': 'answers', 'items': [(이름, 답)]}

card = {'name', 'cells': [[점 번호…], …], 'labels': [칸 이름…], 'line'(설명, 선택)}
"""
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

POS = {1: '왼쪽 위', 2: '왼쪽 가운데', 3: '왼쪽 아래', 4: '오른쪽 위', 5: '오른쪽 가운데', 6: '오른쪽 아래'}

GUIDE = [
    '이 자료는 화면낭독기로 읽을 수 있게 만들었습니다. 제목(개요)으로 단원 안을 옮겨 다닐 수 있습니다.',
    '점칸 그림마다 점 번호를 글로 함께 적었습니다. 점자 문자(예: ⠁)는 점자정보단말기에서 대개 실제 점형으로 나옵니다.',
    '쓰기 연습은 종이에 칠해도 되고, 점판과 점필이나 점자 타자기로 직접 찍어도 됩니다.',
    '정답은 맨 끝 「정답」 제목 아래에 있습니다.',
]

PART_TITLES = ['들어가기', '점형 익히기', '연습하기', '마무리']


def load_json(*parts):
    return json.loads((REPO.joinpath(*parts)).read_text(encoding='utf-8'))


def unit_data(unit_id):
    for u in load_json('data', 'curriculum', 'curriculum.json')['units']:
        if u['id'] == unit_id:
            return u
    raise SystemExit(f'단원 없음: {unit_id}')


def unit_after(unit):
    """같은 언어에서 순서가 바로 다음인 단원 (12 → 12.1 → 13)."""
    later = sorted((u for u in load_json('data', 'curriculum', 'curriculum.json')['units']
                    if u['lang'] == unit['lang'] and u['order'] > unit['order']), key=lambda u: u['order'])
    return later[0] if later else None


def app_cards(unit_id):
    """앱(web/js/curriculum.js cardsFor)이 만드는 카드를 그대로 받아 온다."""
    out = subprocess.run(['node', str(Path(__file__).with_name('cards.mjs')), unit_id],
                         capture_output=True, text=True, check=True, cwd=REPO).stdout
    return json.loads(out)


# 규정집 PDF의 보기는 점자 ASCII 글꼴로 추출된다 (북미 Braille ASCII). ~는 ^와 같은 4·5점.
BRAILLE_ASCII = {
    '!': '2346', '"': '5', '#': '3456', '$': '1246', '%': '146', '&': '12346', "'": '3', '(': '12356',
    ')': '23456', '*': '16', '+': '346', ',': '6', '-': '36', '.': '46', '/': '34', '0': '356', '1': '2',
    '2': '23', '3': '25', '4': '256', '5': '26', '6': '235', '7': '2356', '8': '236', '9': '35', ':': '156',
    ';': '56', '<': '126', '=': '123456', '>': '345', '?': '1456', '@': '4', 'a': '1', 'b': '12', 'c': '14',
    'd': '145', 'e': '15', 'f': '124', 'g': '1245', 'h': '125', 'i': '24', 'j': '245', 'k': '13', 'l': '123',
    'm': '134', 'n': '1345', 'o': '135', 'p': '1234', 'q': '12345', 'r': '1235', 's': '234', 't': '2345',
    'u': '136', 'v': '1236', 'w': '2456', 'x': '1346', 'y': '13456', 'z': '1356', '[': '246', '\\': '1256',
    ']': '12456', '^': '45', '~': '45', '_': '456', '{': '246', '|': '1256', '}': '12456',
}


def asc(text):
    """규정집 점자 ASCII → 점칸 목록. 예) '#a' → [[3,4,5,6],[1]]"""
    return [[int(d) for d in BRAILLE_ASCII[ch]] for ch in text.replace(' ', '')]


def braille(cells):
    """점칸 → 점자 문자. 빈 점칸 [](띄어쓰기)은 보통 띄어쓰기로 둔다."""
    return ''.join(chr(0x2800 + sum(1 << (d - 1) for d in c)) if c else ' ' for c in cells)


def dots_of(ch):
    v = ord(ch) - 0x2800
    return [i + 1 for i in range(6) if v >> i & 1]


def cell_text(dots):
    return '·'.join(str(d) for d in sorted(dots)) + '점' if dots else '빈칸'


def dots_text(cells):
    return ' + '.join(cell_text(c) for c in cells)


def rows(dots):
    """점칸을 3줄(왼쪽 점, 오른쪽 점)로 나눈다."""
    return [(r + 1 in dots, r + 4 in dots) for r in range(3)]


def lang_label(unit):
    return '영어' if unit['lang'] == 'en' else '한글'


def num(unit):
    """화면에 보이는 단원 번호. 12.1단원은 label '12-1'을 쓴다."""
    return unit.get('label') or unit.get('num') or str(unit['order'])


def part_of(unit):
    """단원에 part가 없으면(12-1단원) 바로 앞 단원의 part를 쓴다."""
    if unit.get('part'):
        return unit['part']
    before = sorted((u for u in load_json('data', 'curriculum', 'curriculum.json')['units']
                     if u['lang'] == unit['lang'] and u['order'] < unit['order'] and u.get('part')), key=lambda u: u['order'])
    return before[-1]['part'] if before else ''


def file_stem(unit):
    return f"{lang_label(unit)}점자_{num(unit)}단원_{unit['title'].replace(' ', '')}"


def doc_title(unit):
    return f"{lang_label(unit)} 점자 {num(unit)}단원 {unit['title']} 학습자료"


def check_card(card):
    assert card['cells'] and all(1 <= d <= 6 for c in card['cells'] for d in c), card
    assert len(card.get('labels') or card['cells']) == len(card['cells']), card
    return card


def standard_doc(unit, *, rules, rule_src, key, intro_bullets, learn, practice, checks, answers, extra_intro=None):
    """네 부분 틀에 단원 내용을 끼운다."""
    nxt = unit_after(unit)
    intro = [
        {'title': '이 자료 사용 안내', 'blocks': [{'t': 'bullets', 'items': GUIDE, 'style': 'guide'}]},
        {'title': '이번 단원에서 배울 것', 'blocks': [{'t': 'bullets', 'items': [
            f"읽기: {unit['skill']['read']}", f"쓰기: {unit['skill']['write']}"]}]},
        {'title': '규정 알아보기', 'blocks': [{'t': 'rules', 'items': rules, 'src': rule_src}]},
        {'title': '핵심 정리', 'blocks': [{'t': 'key', 'text': key}, {'t': 'bullets', 'items': intro_bullets}] + (extra_intro or [])},
    ]
    closing = [{'title': '게임 전에 스스로 확인하기', 'blocks': [{'t': 'checks', 'items': checks}]}]
    if nxt:
        closing.append({'title': '다음 단원 예고', 'blocks': [{'t': 'next', 'text': f"다음은 {num(nxt)}단원 「{nxt['title']}」입니다."}]})
    closing.append({'title': '정답', 'blocks': [{'t': 'answers', 'items': answers}]})
    for sec in learn + practice:
        for b in sec['blocks']:
            for c in b.get('items', []) if b['t'] in ('cards', 'read_ex') else []:
                check_card(c)
    return {
        'id': unit['id'], 'lang': unit['lang'], 'order': unit['order'], 'num': num(unit), 'part': part_of(unit), 'title': unit['title'],
        'parts': [
            {'title': PART_TITLES[0], 'sections': intro},
            {'title': PART_TITLES[1], 'sections': learn},
            {'title': PART_TITLES[2], 'sections': practice},
            {'title': PART_TITLES[3], 'sections': closing},
        ],
    }


TENSE_BASE = {'ㄲ': 'ㄱ', 'ㄸ': 'ㄷ', 'ㅃ': 'ㅂ', 'ㅆ': 'ㅅ', 'ㅉ': 'ㅈ'}


def cell_labels(card):
    """앱 카드의 조립 순서(steps)로 칸마다 이름을 붙인다. 쌍자음 첫소리는 「된소리표, ㄱ」처럼 나눈다."""
    out = []
    for s in card['steps']:
        n = len(s['cells'])
        if n == 2 and s['label'] in TENSE_BASE and s['cells'][0] == [6]:
            out += ['된소리표', TENSE_BASE[s['label']]]
        else:
            out += [s['label']] * n
    return out


_ENGINE = None


def ko_braille(text):
    """저장소 번역 엔진(engine/ko)으로 한글 문장을 점자로 바꾼다. 띄어쓰기는 빈칸(⠀ 없이 ' ')으로 둔다."""
    global _ENGINE
    if _ENGINE is None:
        import sys
        sys.path.insert(0, str(REPO))
        from tests.test_ko_rule_changes import load_engine
        _ENGINE = load_engine()
    return _ENGINE.text_to_braille(text)['braille'].strip()


def ko_cells(text):
    """문장 → 점칸 목록. 띄어쓴 자리는 빈칸 []."""
    return [[] if ch == ' ' else dots_of(ch) for ch in ko_braille(text)]


def reg_cells(ascii_line):
    """규정집 보기 한 줄(점자 ASCII, `는 빈칸) → 점칸 목록."""
    return [[] if ch == '`' else [int(d) for d in BRAILLE_ASCII[ch]] for ch in ascii_line.strip('`')]


def ko_uses_abbr(text):
    """엔진이 이 글에 약자·약어를 썼으면 그 글자들을 돌려준다 (정자 단원에서 피하려고)."""
    ko_braille('')
    tr = _ENGINE.text_to_braille(text)['traces']
    return [x['token'] for x in tr if '약자' in (x.get('explanation') or '') or x.get('rule') == 'Word Abbreviation']


def jamo_spell(text):
    """약자 없이 자모를 풀어 적은 점칸과 칸 이름. 첫소리 ㅇ은 적지 않는다 (제1항 [다만 1])."""
    ko = load_json('data', 'ko', 'ko.json')

    def one(item):
        d = item['dots']
        return [d] if isinstance(d[0], int) else d
    cells, labels = [], []
    for ch in text:
        if ch == ' ':
            cells.append([])
            labels.append('빈칸')
            continue
        code = ord(ch) - 0xAC00
        cho, jung, jong = ('ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'[code // 588], 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'[code % 588 // 28],
                           ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'][code % 28])
        if cho != 'ㅇ':
            c = one(ko['chosung']['items'][cho])
            cells += c
            labels += ['된소리표', TENSE_BASE[cho]] if cho in TENSE_BASE else [cho]
        c = one(ko['jungsung']['items'][jung])
        cells += c
        labels += [jung] * len(c)
        if jong:
            c = one(ko['jongsung']['items'][jong])
            cells += c
            labels += [f'받침 {jong}'] * len(c)
    return cells, labels


PENDING_JAMO = set('ㅚㅋㅌㅍㄲㄳㄵㄶㄺㄻㄼㄽㄾㄿㅀㅄ')


def pending_jamo(text):
    """허락 대기 중인 점형(모음 ㅚ, 받침 ㅋ·ㅌ·ㅍ, 쌍받침·겹받침)이 글에 있으면 그 자모를 돌려준다."""
    out = set()
    for ch in text:
        code = ord(ch) - 0xAC00
        if not 0 <= code < 11172:
            continue
        jung = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'[code % 588 // 28]
        jong = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'][code % 28]
        out |= {jung, jong} & PENDING_JAMO
    return out


def _decompose(ch):
    code = ord(ch) - 0xAC00
    if not 0 <= code < 11172:
        return None
    return ('ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'[code // 588], 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'[code % 588 // 28],
            ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'][code % 28])


def ko_labeled(text):
    """엔진 점칸과 칸 이름. 약자는 「가 약자」「억 약자」처럼, 받침은 「받침 ㄱ」처럼 이름을 붙인다.

    엔진이 남긴 규칙 설명(traces)으로 어떤 약자를 썼는지 알아내고, 칸 수가 맞는지 확인한다.
    """
    ko_braille('')
    ko = load_json('data', 'ko', 'ko.json')
    jong_n = {k: (1 if isinstance(v['dots'][0], int) else len(v['dots'])) for k, v in ko['jongsung']['items'].items()}
    split = {'ㄲ': 'ㄱㄱ', 'ㄳ': 'ㄱㅅ', 'ㄵ': 'ㄴㅈ', 'ㄶ': 'ㄴㅎ', 'ㄺ': 'ㄹㄱ', 'ㄻ': 'ㄹㅁ', 'ㄼ': 'ㄹㅂ', 'ㄽ': 'ㄹㅅ',
             'ㄾ': 'ㄹㅌ', 'ㄿ': 'ㄹㅍ', 'ㅀ': 'ㄹㅎ', 'ㅄ': 'ㅂㅅ'}
    cells, labels = [], []
    for tr in _ENGINE.text_to_braille(text)['traces']:
        tok, b, ex = tr['token'], tr['braille'], tr.get('explanation') or ''
        cs = [[] if c in ' ⠀' else dots_of(c) for c in b]
        if tr.get('rule') == 'Word Abbreviation':
            lab = ['약어'] * len(cs)
        elif tr.get('rule') != 'Hangul Syllable':
            lab = ['빈칸' if not c else tok for c in cs]
            if tok.isdigit() and len(cs) > 1 and cs[0] == [3, 4, 5, 6]:  # 제40항: 수표 + 숫자
                lab[0] = '수표'
        else:
            cho, jung, jong = _decompose(tok)
            tense = cho in TENSE_BASE
            base = TENSE_BASE.get(cho, cho)
            head = (['된소리표'] if tense else [])
            jl = lambda j: [f'받침 {j}'] * jong_n[j] if j else []
            if '완전 일치 음절 약자' in ex or "'것' 약자 결합" in ex:
                lab = head + ['것 약자'] * 2
            elif '가 계열 약자' in ex:
                lab = head + [f'{chr(0xAC00 + "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ".index(base) * 588)} 약자'] + jl(jong)
            elif "뒤 '영' 약자는" in ex:
                lab = head + [base, '영 약자']
            elif '제15항 [붙임]' in ex:
                part = chr(0xAC00 + 11 * 588 + 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'.index(jung) * 28 + ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ'].index(split[jong][0]))
                lab = head + ([] if base == 'ㅇ' else [base]) + [f'{part} 약자'] + jl(split[jong][1])
            elif '모음+받침 약자' in ex:
                whole = chr(0xAC00 + 11 * 588 + 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'.index(jung) * 28 + ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ'].index(jong))
                lab = head + ([] if base == 'ㅇ' else [base]) + [f'{whole} 약자']
            else:
                lab = jamo_spell(tok)[1]
            if len(lab) < len(cs):  # 구분표·숫자 뒤 빈칸 등 앞에 붙은 칸
                lab = ['구분표' if c == [3, 6] else '빈칸' for c in cs[:len(cs) - len(lab)]] + lab
        assert len(lab) == len(cs), (tok, b, lab)
        cells += cs
        labels += lab
    while cells and cells[-1] == []:
        cells.pop(); labels.pop()
    return cells, labels
