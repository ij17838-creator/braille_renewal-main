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
    return ''.join(chr(0x2800 + sum(1 << (d - 1) for d in c)) for c in cells)


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


def file_stem(unit):
    return f"{lang_label(unit)}점자_{unit['order']}단원_{unit['title'].replace(' ', '')}"


def doc_title(unit):
    return f"{lang_label(unit)} 점자 {unit['order']}단원 {unit['title']} 학습자료"


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
        closing.append({'title': '다음 단원 예고', 'blocks': [{'t': 'next', 'text': f"다음은 {nxt['order']}단원 「{nxt['title']}」입니다."}]})
    closing.append({'title': '정답', 'blocks': [{'t': 'answers', 'items': answers}]})
    for sec in learn + practice:
        for b in sec['blocks']:
            for c in b.get('items', []) if b['t'] in ('cards', 'read_ex') else []:
                check_card(c)
    return {
        'id': unit['id'], 'lang': unit['lang'], 'order': unit['order'], 'part': unit['part'], 'title': unit['title'],
        'parts': [
            {'title': PART_TITLES[0], 'sections': intro},
            {'title': PART_TITLES[1], 'sections': learn},
            {'title': PART_TITLES[2], 'sections': practice},
            {'title': PART_TITLES[3], 'sections': closing},
        ],
    }
