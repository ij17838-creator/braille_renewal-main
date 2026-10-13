"""단원 문서(dict) → 한글 파일(.hwpx).

hwpx 스킬의 report 템플릿(header.xml, section0.xml)을 바탕으로 쓰고, 조립·검사는 스킬의 스크립트를 부른다.
화면낭독기용 구조:
  - 부분 제목은 '개요 1', 절 제목은 '개요 2' → 한글 개요 보기·낭독기 제목 이동
  - 표 머리행 표시, 칸 안에서는 설명 → 점자 문자 → ●○ 그림 순서로 읽힌다
"""
import re
from xml.sax.saxutils import escape

from common import braille, doc_title, dots_text, lang_label, rows

# 글자 모양 (report 템플릿 0~15 + 추가 16~19)
CP_BODY, CP_SANS, CP_TITLE, CP_BOLD, CP_SMALL, CP_PART = 0, 1, 7, 9, 11, 13
CP_DOT, CP_GRAY, CP_DOT_S, CP_SEC = 16, 17, 18, 19
# 문단 모양 (report 템플릿 0~27 + 추가 28~29)
PP_BODY, PP_CENTER, PP_CELL_C, PP_CELL_J, PP_RIGHT, PP_ITEM = 0, 20, 21, 22, 23, 24
PP_PART, PP_SEC = 28, 29
# 테두리/배경 (report 3~5 + 추가 6)
BF_LINE, BF_HEAD, BF_SOFT = 3, 4, 6
TEXT_WIDTH = 42520  # A4 본문 폭


def build_header(skill):
    hdr = (skill / 'templates/report/header.xml').read_text(encoding='utf-8')

    def grab(kind, i):
        return re.search(rf'<hh:{kind} id="{i}".*?</hh:{kind}>', hdr, re.S).group(0)

    sans = grab('charPr', 1)
    add_cp = [
        sans.replace('id="1"', f'id="{CP_DOT}"', 1).replace('height="1000"', 'height="1600"'),
        sans.replace('id="1"', f'id="{CP_GRAY}"', 1).replace('height="1000"', 'height="900"').replace('textColor="#000000"', 'textColor="#555555"'),
        sans.replace('id="1"', f'id="{CP_DOT_S}"', 1),
        grab('charPr', 13).replace('id="13"', f'id="{CP_SEC}"', 1).replace('height="1200"', 'height="1100"'),
    ]
    hdr = hdr.replace('</hh:charProperties>', ''.join(add_cp) + '</hh:charProperties>')
    soft = grab('borderFill', 4).replace('id="4"', f'id="{BF_SOFT}"', 1).replace('#DAEEF3', '#E8F7EF')
    hdr = hdr.replace('</hh:borderFills>', soft + '</hh:borderFills>')
    none = '<hh:heading type="NONE" idRef="0" level="0"/>'
    part = grab('paraPr', 27).replace('id="27"', f'id="{PP_PART}"', 1).replace(none, '<hh:heading type="OUTLINE" idRef="0" level="0"/>')
    sec = grab('paraPr', 0).replace('id="0"', f'id="{PP_SEC}"', 1).replace(none, '<hh:heading type="OUTLINE" idRef="0" level="1"/>')
    hdr = hdr.replace('</hh:paraProperties>', part + sec + '</hh:paraProperties>')
    for kind in ('charProperties', 'paraProperties', 'borderFills'):
        child = {'charProperties': 'charPr', 'paraProperties': 'paraPr', 'borderFills': 'borderFill'}[kind]
        body = re.search(rf'<hh:{kind}[^>]*>(.*?)</hh:{kind}>', hdr, re.S).group(1)
        n = len(re.findall(rf'<hh:{child} id=', body))
        hdr = re.sub(rf'<hh:{kind} itemCnt="\d+"', f'<hh:{kind} itemCnt="{n}"', hdr)
    return hdr


class Section:
    def __init__(self):
        self.next_id = 1000000100
        self.out = []
        self.explained_cards = False  # 표 읽는 순서 안내는 처음 한 번만

    def nid(self):
        self.next_id += 1
        return str(self.next_id)

    def para(self, runs, pp=PP_BODY, style=0, page_break=False):
        if isinstance(runs, str):
            runs = [(CP_BODY, runs)]
        r = ''.join(f'<hp:run charPrIDRef="{c}"><hp:t>{escape(t)}</hp:t></hp:run>' if t else f'<hp:run charPrIDRef="{c}"><hp:t/></hp:run>'
                    for c, t in runs)
        return (f'<hp:p id="{self.nid()}" paraPrIDRef="{pp}" styleIDRef="{style}" pageBreak="{int(page_break)}" '
                f'columnBreak="0" merged="0">{r}</hp:p>')

    def add(self, *args, **kw):
        self.out.append(self.para(*args, **kw))

    def table(self, grid, widths, heights, bfs=None, header_row=False):
        """grid: 행 목록, 행 = 칸 목록, 칸 = [(문단모양, 글자모양, 글)]"""
        trs = []
        for ri, row in enumerate(grid):
            tcs = []
            for ci, cell in enumerate(row):
                bf = bfs[ri][ci] if bfs else BF_LINE
                ps = ''.join(self.para([(cp, t)], pp) for pp, cp, t in cell) or self.para([(CP_BODY, '')], PP_CELL_C)
                head = int(header_row and ri == 0)
                tcs.append(f'<hp:tc name="" header="{head}" hasMargin="1" protect="0" editable="0" dirty="1" borderFillIDRef="{bf}">'
                           '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" '
                           f'linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">{ps}</hp:subList>'
                           f'<hp:cellAddr colAddr="{ci}" rowAddr="{ri}"/><hp:cellSpan colSpan="1" rowSpan="1"/>'
                           f'<hp:cellSz width="{widths[ci]}" height="{heights[ri]}"/>'
                           '<hp:cellMargin left="425" right="425" top="283" bottom="283"/></hp:tc>')
            trs.append('<hp:tr>' + ''.join(tcs) + '</hp:tr>')
        tbl = (f'<hp:tbl id="{self.nid()}" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" '
               f'lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="{int(header_row)}" rowCnt="{len(grid)}" '
               f'colCnt="{len(widths)}" cellSpacing="0" borderFillIDRef="{BF_LINE}" noAdjust="0">'
               f'<hp:sz width="{sum(widths)}" widthRelTo="ABSOLUTE" height="{sum(heights)}" heightRelTo="ABSOLUTE" protect="0"/>'
               '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" '
               'horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
               '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:inMargin left="0" right="0" top="0" bottom="0"/>'
               + ''.join(trs) + '</hp:tbl>')
        self.out.append(f'<hp:p id="{self.nid()}" paraPrIDRef="{PP_CELL_C}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                        f'<hp:run charPrIDRef="0">{tbl}</hp:run><hp:run charPrIDRef="0"><hp:t/></hp:run></hp:p>')


def dot_lines(cells, blank=False):
    """●○ 그림 3줄. 칸 사이는 넓게 띄운다. 빈 점칸 []은 띄어쓰기 자리로 비워 두고, blank=True(쓰기 연습)면 ○로 그린다."""
    return ['  '.join(f'{"●" if a else "○"} {"●" if b else "○"}' if c or blank else '   ' for c, (a, b) in [(c, rows(c)[r]) for c in cells])
            for r in range(3)]


def dot_cp(cells):
    return CP_DOT if len(cells) <= 2 else CP_DOT_S


def even(n, total=TEXT_WIDTH):
    w = [total // n] * n
    w[-1] += total - sum(w)
    return w


def grid_cols(max_cells):
    return max(2, min(6, int(150 / (max_cells * 16 + 10))))


def chunk(items, k):
    return [items[i:i + k] for i in range(0, len(items), k)]


def write_block(s, b):
    C, J = PP_CELL_C, PP_CELL_J
    t = b['t']
    if t == 'p':
        s.add(b['text'])
    elif t == 'bullets':
        for i in b['items']:
            s.add('- ' + i, PP_ITEM)
    elif t == 'rules':
        for n, x in b['items']:
            s.add([(CP_BOLD, n + ' '), (CP_BODY, x)], PP_ITEM)
        s.add([(CP_GRAY, '출처: ' + b['src'])], PP_ITEM)
    elif t == 'key':
        s.table([[[(J, CP_BOLD, b['text'])]]], [TEXT_WIDTH], [1800], bfs=[[BF_SOFT]])
    elif t == 'big_cell':
        grid = [[[(C, CP_PART, f'{r + 1}점')], [(C, CP_PART, f'{r + 4}점')]] for r in range(3)]
        s.table(grid, [5000, 5000], [1800] * 3, bfs=[[BF_SOFT] * 2] * 3)
    elif t == 'cards':
        if b.get('caption'):
            s.add([(CP_BOLD, b['caption'])])
        if not s.explained_cards:
            s.add([(CP_SMALL, '표는 이름, 점 번호, 점자 문자, 점칸 그림 순서입니다. 그림의 ●는 볼록한 점, ○는 빈 자리입니다.')])
            s.explained_cards = True
        grid = [[[(C, CP_BOLD, '이름')], [(C, CP_BOLD, '점 번호와 설명')], [(C, CP_BOLD, '점자')], [(C, CP_BOLD, '점칸 그림')]]]
        for c in b['items']:
            line = c.get('line') or dots_text(c['cells'])
            label = ' · '.join(c['labels']) if c.get('labels') and len(c['cells']) > 1 else ''
            pic = [(C, dot_cp(c['cells']), l) for l in dot_lines(c['cells'])] + ([(C, CP_GRAY, label)] if label else [])
            grid.append([[(C, CP_PART, c['name'])], [(J, CP_BODY, line)], [(C, CP_DOT, braille(c['cells']))], pic])
        h = [1500] + [3600 if len(c['cells']) > 1 else 3300 for c in b['items']]
        s.table(grid, [6000, 15520, 6000, 15000], h, bfs=[[BF_HEAD] * 4] + [[BF_LINE] * 4] * len(b['items']), header_row=True)
    elif t == 'read_ex':
        s.add([(CP_SMALL, b['hint'] + ' 칸마다 문제 번호, 점 설명, 점자 문자, 그림, 답 칸 순서입니다.')])
        k = grid_cols(max(len(c['cells']) for c in b['items']))
        items = list(enumerate(b['items'], 1))
        for row in chunk(items, k):
            cells = [[(C, CP_SMALL, f'({i})'), (C, CP_BODY, c['name']), (C, CP_DOT, braille(c['cells']))]
                     + [(C, dot_cp(c['cells']), l) for l in dot_lines(c['cells'])] + [(C, CP_BODY, b.get('blank', '(    )'))]
                     for i, c in row]
            cells += [[]] * (k - len(row))
            s.table([cells], even(k), [7600])
    elif t == 'write_ex':
        s.add([(CP_SMALL, b['hint'])])
        k = grid_cols(max(w['cells'] for w in b['items']))
        items = list(enumerate(b['items'], 1))
        for row in chunk(items, k):
            cells = [[(C, CP_SMALL, f'({i})'), (C, CP_PART, w['ask']), (C, CP_SMALL, f'빈 점칸 {w["cells"]}칸')]
                     + [(C, dot_cp([[]] * w['cells']), l) for l in dot_lines([[]] * w['cells'], blank=True)]
                     for i, w in row]
            cells += [[]] * (k - len(row))
            s.table([cells], even(k), [6000])
    elif t == 'table':
        if b.get('caption'):
            s.add([(CP_SMALL, b['caption'])])

        def cell(text, bold=False):
            # 글자와 점자를 줄을 나눠 적는다. 예) '고 ⠈⠥' → 고 / ⠈⠥
            parts = re.split(r'\s+(?=[\u2800-\u28ff])', text, maxsplit=1)
            out = [(C, CP_BOLD if bold else CP_BODY, parts[0])]
            if len(parts) > 1:
                out.append((C, CP_DOT_S, parts[1]))
            return out
        n = len(b['head'])
        first = min(6000, TEXT_WIDTH // n)
        widths = [first] + even(n - 1, TEXT_WIDTH - first)
        grid = [[cell(h, True) for h in b['head']]] + [[cell(r[0], True)] + [cell(c) for c in r[1:]] for r in b['rows']]
        bfs = [[BF_HEAD] * n] + [[BF_HEAD] + [BF_LINE] * (n - 1) for _ in b['rows']]
        s.table(grid, widths, [1300] + [2000] * len(b['rows']), bfs=bfs, header_row=True)
    elif t == 'checks':
        for i in b['items']:
            s.add('□ ' + i, PP_ITEM)
    elif t == 'next':
        s.add([(CP_BOLD, b['text'])])
    elif t == 'answers':
        for k_, v in b['items']:
            s.add([(CP_BOLD, k_ + ': '), (CP_BODY, v)], PP_ITEM)
    else:
        raise ValueError(t)


def build_section(doc, skill):
    tpl = (skill / 'templates/report/section0.xml').read_text(encoding='utf-8')
    first = re.search(r'<hp:p id="1000000001".*?</hp:p>', tpl, re.S).group(0)
    first = re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', first, flags=re.S)
    # 쪽 번호 (아래 가운데, - 1 -)
    first = first.replace('</hp:ctrl>', '</hp:ctrl><hp:ctrl><hp:pageNum pos="BOTTOM_CENTER" formatType="DIGIT" sideChar="-"/></hp:ctrl>', 1)
    head = tpl[:tpl.index('<hp:p id="1000000001"')]

    s = Section()
    u = doc
    s.add([(CP_SANS, f'{lang_label(u)} 점자 {u["num"]}단원 · {u["part"]}')])
    s.add([(CP_TITLE, u['title'])], PP_CENTER)
    s.add('게임 전 학습자료 · 이름: ____________', PP_RIGHT)
    for pi, part in enumerate(doc['parts']):
        s.add([(CP_PART, part['title'])], PP_PART, style=2, page_break=pi > 0)
        for sec in part['sections']:
            s.add([(CP_SEC, sec['title'])], PP_SEC, style=3)
            for b in sec['blocks']:
                write_block(s, b)
    return head + first + ''.join(s.out) + '</hs:sec>'


def title_of(doc):
    return doc_title(doc)
