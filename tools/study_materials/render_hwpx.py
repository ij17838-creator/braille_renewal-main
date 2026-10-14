"""단원 문서(dict) → 한글 파일(.hwpx).

hwpx 스킬의 report 템플릿(header.xml, section0.xml)을 바탕으로 쓰고, 조립·검사는 스킬의 스크립트를 부른다.
화면낭독기용 구조:
  - 부분 제목은 '개요 1', 절 제목은 '개요 2' → 한글 개요 보기·낭독기 제목 이동
  - 표 머리행 표시, 칸 안에서는 설명 → 점자 문자 → ●○ 그림 순서로 읽힌다
"""
import hashlib
import re
from xml.sax.saxutils import escape

from common import braille, doc_title, dots_of, dots_text, lang_label, rows

# 글자 모양 (report 템플릿 0~15 + 추가 16~19)
CP_BODY, CP_SANS, CP_TITLE, CP_BOLD, CP_SMALL, CP_PART = 0, 1, 7, 9, 11, 13
CP_DOT, CP_GRAY, CP_DOT_S, CP_SEC = 16, 17, 18, 19
# 문단 모양 (report 템플릿 0~27 + 추가 28~29)
PP_BODY, PP_CENTER, PP_CELL_C, PP_CELL_J, PP_RIGHT, PP_ITEM = 0, 20, 21, 22, 23, 24
PP_PART, PP_SEC = 28, 29
# 테두리/배경 (report 3~5 + 추가 6)
BF_LINE, BF_HEAD, BF_SOFT = 3, 4, 6
TEXT_WIDTH = 42520  # A4 본문 폭
# 점자 문자(⠿ 등)는 글자 대신 6점 칸 그림으로 넣는다. 한글 프로그램은 점자 문자를 8점 칸(맨 아래 빈 점 2개)으로
# 그리는 글꼴로 대신 보여 주고, 파일 안에 넣은 글꼴은 쓰지 않기 때문이다 (2026-10-14 중연님 화면으로 확인).
BRAILLE_RUN = re.compile(r'([\u2800-\u283f](?:[\u2800-\u283f ]*[\u2800-\u283f])?)')
CELL_W, CELL_H = 640, 780       # 점칸 하나의 크기 (그림 단위)
DOT_X, DOT_Y = (170, 420), (140, 390, 640)
R_FILL, R_RING, RING = 92, 88, 26
PIC_SCALE = {16: 1.6}           # 글자 모양별 그림 배율 (큰 점자 칸). 나머지는 1.1
IMAGES = {}                     # build_section이 채운다: 그림 id → PNG 바이트
LONG_CELLS = 5  # 이만큼 긴 낱말·문장은 ●○ 그림을 넣지 않는다 (칸 너비를 넘쳐 줄이 섞이므로)
BRAILLE_LINE = 10  # 넓은 칸에서 점자 문자 한 줄에 넣는 최대 점칸 수


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
        self.explained_long = False  # 그림 없는 긴 카드 안내도 처음 한 번만

    def nid(self):
        self.next_id += 1
        return str(self.next_id)

    def para(self, runs, pp=PP_BODY, style=0, page_break=False):
        if isinstance(runs, str):
            runs = [(CP_BODY, runs)]
        r = ''
        for c, t in runs:
            if not t:
                r += f'<hp:run charPrIDRef="{c}"><hp:t/></hp:run>'
                continue
            for i, x in enumerate(BRAILLE_RUN.split(t)):
                if i % 2 == 0:
                    if x:
                        r += f'<hp:run charPrIDRef="{c}"><hp:t>{escape(x)}</hp:t></hp:run>'
                    continue
                # 점자 부분: 낱말마다 그림 하나, 띄어쓰기는 글자로 두어 줄바꿈이 낱말 사이에서만 일어나게
                for j, w in enumerate(x.split(' ')):
                    if j:
                        r += f'<hp:run charPrIDRef="{c}"><hp:t> </hp:t></hp:run>'
                    if w:
                        r += f'<hp:run charPrIDRef="{c}">{self.braille_pic(w, PIC_SCALE.get(c, 1.1))}</hp:run>'
        return (f'<hp:p id="{self.nid()}" paraPrIDRef="{pp}" styleIDRef="{style}" pageBreak="{int(page_break)}" '
                f'columnBreak="0" merged="0">{r}</hp:p>')

    def braille_pic(self, word, scale):
        """점자 낱말 → 글자처럼 놓이는 6점 칸 그림. 그림 설명에는 점 번호를 적어 화면낭독기가 읽게 한다."""
        key = 'braille' + hashlib.md5(word.encode('utf-8')).hexdigest()[:12]
        if key not in IMAGES:
            IMAGES[key] = braille_png(word)
        w, h = round(CELL_W * len(word) * scale), round(CELL_H * scale)
        desc = '점자 그림: ' + dots_text([dots_of(ch) for ch in word])
        pid = self.nid()
        return (f'<hp:pic id="{pid}" zOrder="0" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
                f'dropcapstyle="None" href="" groupLevel="0" instid="{pid}" reverse="0">'
                f'<hp:offset x="0" y="0"/><hp:orgSz width="{w}" height="{h}"/><hp:curSz width="{w}" height="{h}"/>'
                f'<hp:flip horizontal="0" vertical="0"/><hp:rotationInfo angle="0" centerX="{w // 2}" centerY="{h // 2}" rotateimage="1"/>'
                '<hp:renderingInfo><hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
                '<hc:scaMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/><hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/></hp:renderingInfo>'
                f'<hp:imgRect><hc:pt0 x="0" y="0"/><hc:pt1 x="{w}" y="0"/><hc:pt2 x="{w}" y="{h}"/><hc:pt3 x="0" y="{h}"/></hp:imgRect>'
                f'<hp:imgClip left="0" right="{w}" top="0" bottom="{h}"/><hp:inMargin left="0" right="0" top="0" bottom="0"/>'
                f'<hp:imgDim dimwidth="{w}" dimheight="{h}"/>'
                f'<hc:img binaryItemIDRef="{key}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/><hp:effects/>'
                f'<hp:sz width="{w}" widthRelTo="ABSOLUTE" height="{h}" heightRelTo="ABSOLUTE" protect="0"/>'
                '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" '
                'horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
                f'<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:shapeComment>{escape(desc)}</hp:shapeComment></hp:pic>')

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


def braille_png(word, px=0.2):
    """점자 낱말 → PNG. 칸마다 2열 3줄, 볼록한 점은 ●, 빈 자리는 ○."""
    import io
    from PIL import Image, ImageDraw
    ss = 4  # 크게 그린 뒤 줄여 테두리를 매끄럽게
    k = px * ss
    im = Image.new('RGB', (round(CELL_W * len(word) * k), round(CELL_H * k)), 'white')
    d = ImageDraw.Draw(im)
    for i, ch in enumerate(word):
        dots = dots_of(ch)
        for n in range(1, 7):
            cx, cy = (i * CELL_W + DOT_X[(n - 1) // 3]) * k, DOT_Y[(n - 1) % 3] * k
            if n in dots:
                d.ellipse([cx - R_FILL * k, cy - R_FILL * k, cx + R_FILL * k, cy + R_FILL * k], fill='black')
            else:
                d.ellipse([cx - R_RING * k, cy - R_RING * k, cx + R_RING * k, cy + R_RING * k], outline='black', width=round(RING * k))
    im = im.resize((im.width // ss, im.height // ss), Image.LANCZOS).convert('L').quantize(8)  # 회색 8단계로 작게
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def embed_images(hwpx, images):
    """만든 한글 파일에 점자 그림을 넣는다 (BinData/<id>.png + content.hpf 목록). mimetype은 맨 앞에 그대로 둔다."""
    import shutil
    import tempfile
    import zipfile
    items = ''.join(f'<opf:item id="{k}" href="BinData/{k}.png" media-type="image/png" isEmbeded="1"/>' for k in images)
    tmp = tempfile.NamedTemporaryFile(suffix='.hwpx', delete=False).name
    with zipfile.ZipFile(hwpx) as zin, zipfile.ZipFile(tmp, 'w') as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == 'Contents/content.hpf':
                data = data.decode('utf-8').replace('</opf:manifest>', items + '</opf:manifest>').encode('utf-8')
            zout.writestr(info, data)
        for k, png in images.items():
            zout.writestr(f'BinData/{k}.png', png, compress_type=zipfile.ZIP_STORED)
    shutil.move(tmp, hwpx)


def dot_cp(cells):
    return CP_DOT if len(cells) <= 2 else CP_DOT_S


def is_long(cells):
    return len(cells) >= LONG_CELLS


def braille_lines(cells, per=BRAILLE_LINE):
    """점자 문자를 띄어쓰기 자리에서 끊어 한 줄에 per칸 이하로 나눈다. 낱말 하나가 per칸보다 길면 그 낱말만 칸 수로 끊는다."""
    words, w = [], []
    for c in cells:
        if c:
            w.append(c)
        elif w:
            words.append(w)
            w = []
    if w:
        words.append(w)
    lines, cur = [], []
    for w in words:
        for part in chunk(w, per):
            if cur and len(cur) + 1 + len(part) > per:
                lines.append(cur)
                cur = []
            cur = cur + [[]] + part if cur else part
    if cur:
        lines.append(cur)
    return [braille(l) for l in lines]


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
        # 짧은 점형은 이름·설명·점자·그림 4칸 표, 긴 낱말·문장은 그림 없이 점자 칸을 넓힌 3칸 표. 순서는 그대로 둔다.
        groups = []
        for c in b['items']:
            if groups and is_long(groups[-1][-1]['cells']) == is_long(c['cells']):
                groups[-1].append(c)
            else:
                groups.append([c])
        for g in groups:
            if is_long(g[0]['cells']):
                if not s.explained_long:
                    s.add([(CP_SMALL, '긴 낱말과 문장은 점칸 그림 없이 점 번호와 점자 문자로 적습니다.')])
                    s.explained_long = True
                grid = [[[(C, CP_BOLD, '이름')], [(C, CP_BOLD, '점 번호와 설명')], [(C, CP_BOLD, '점자')]]]
                for c in g:
                    line = c.get('line') or dots_text(c['cells'])
                    grid.append([[(C, CP_PART, c['name'])], [(J, CP_BODY, line)],
                                 [(PP_CELL_J, CP_DOT, l) for l in braille_lines(c['cells'])]])
                h = [1500] + [3600] * len(g)
                s.table(grid, [6000, 15520, 21000], h, bfs=[[BF_HEAD] * 3] + [[BF_LINE] * 3] * len(g), header_row=True)
                continue
            grid = [[[(C, CP_BOLD, '이름')], [(C, CP_BOLD, '점 번호와 설명')], [(C, CP_BOLD, '점자')], [(C, CP_BOLD, '점칸 그림')]]]
            for c in g:
                line = c.get('line') or dots_text(c['cells'])
                label = ' · '.join(c['labels']) if c.get('labels') and len(c['cells']) > 1 else ''
                pic = [(C, dot_cp(c['cells']), l) for l in dot_lines(c['cells'])] + ([(C, CP_GRAY, label)] if label else [])
                grid.append([[(C, CP_PART, c['name'])], [(J, CP_BODY, line)], [(C, dot_cp(c['cells']), braille(c['cells']))], pic])
            h = [1500] + [3600 if len(c['cells']) > 1 else 3300 for c in g]
            s.table(grid, [6000, 15520, 6000, 15000], h, bfs=[[BF_HEAD] * 4] + [[BF_LINE] * 4] * len(g), header_row=True)
    elif t == 'read_ex':
        s.add([(CP_SMALL, b['hint'] + ' 칸마다 문제 번호, 점 설명, 점자 문자, 그림, 답 칸 순서입니다.')])
        k = grid_cols(max(len(c['cells']) for c in b['items']))
        items = list(enumerate(b['items'], 1))
        for row in chunk(items, k):
            cells = [[(C, CP_SMALL, f'({i})'), (C, CP_BODY, c['name'])]
                     + ([(C, CP_DOT, l) for l in braille_lines(c['cells'])] if is_long(c['cells'])
                        else [(C, CP_DOT, braille(c['cells']))] + [(C, dot_cp(c['cells']), l) for l in dot_lines(c['cells'])])
                     + [(C, CP_BODY, b.get('blank', '(    )'))]
                     for i, c in row]
            cells += [[]] * (k - len(row))
            s.table([cells], even(k), [7600])
    elif t == 'write_ex':
        s.add([(CP_SMALL, b['hint'])])
        k = grid_cols(max(w['cells'] for w in b['items']))
        items = list(enumerate(b['items'], 1))
        for row in chunk(items, k):
            cells = [[(C, CP_SMALL, f'({i})'), (C, CP_PART, w['ask']), (C, CP_SMALL, f'빈 점칸 {w["cells"]}칸')]
                     + ([] if w['cells'] >= LONG_CELLS
                        else [(C, dot_cp([[]] * w['cells']), l) for l in dot_lines([[]] * w['cells'], blank=True)])
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

    IMAGES.clear()
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
