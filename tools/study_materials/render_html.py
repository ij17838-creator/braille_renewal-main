"""단원 문서(dict) → 화면낭독기용 HTML. PDF는 topdf.js가 이 HTML을 태그 있는 PDF로 찍는다."""
import re
from html import escape as _escape

from common import POS, braille, doc_title, dots_text, lang_label, rows

HANGUL_NUM = '가나다라마바사아자차카타파하'


def escape(text):
    """글 안의 점자 문자는 점자 글꼴로 크게 보이게 감싼다."""
    return re.sub('([\u2800-\u28ff]+)', r'<span class="br">\1</span>', _escape(str(text)))


def span(cells):
    """여러 칸 점형은 칸 수에 맞춰 격자 칸을 더 차지한다."""
    n = len(cells)
    return ' style="grid-column: span 4"' if n > 5 else ' style="grid-column: span 2"' if n > 2 else ''


def cell_svg(dots, size=1.0, labels=False, dashed=False):
    """점칸 하나. 그림은 화면낭독기가 건너뛰고(aria-hidden), 옆의 글 설명을 읽는다."""
    r = 9 * size
    g = 30 * size
    w, h = g + 2 * r + 24 * size, 2 * g + 2 * r + 24 * size
    o = 12 * size + r
    out = [f'<svg aria-hidden="true" focusable="false" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}">',
           f'<rect x="1" y="1" width="{w-2:.0f}" height="{h-2:.0f}" rx="{8*size:.0f}" fill="#fff" stroke="#c9d3df"/>']
    for n in range(1, 7):
        col, row = (0, n - 1) if n <= 3 else (1, n - 4)
        cx, cy = o + col * g, o + row * g
        if n in dots:
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="#1f2a44"/>')
        else:
            dash = ' stroke-dasharray="3 3"' if dashed else ''
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="none" stroke="#7d8ca0" stroke-width="1.6"{dash}/>')
        if labels:
            fill = '#fff' if n in dots else '#5b6b80'
            out.append(f'<text x="{cx:.1f}" y="{cy + 5*size:.1f}" text-anchor="middle" font-size="{13*size:.0f}" font-weight="700" fill="{fill}">{n}</text>')
    out.append('</svg>')
    return ''.join(out)


def cell_row(cells, labels=None, size=0.62, dashed=False):
    parts = []
    for i, c in enumerate(cells):
        lab = f'<span class="cl">{escape(labels[i])}</span>' if labels and len(cells) > 1 else ''
        parts.append(f'<span class="cw">{cell_svg(c, size, dashed=dashed)}{lab}</span>')
    return f'<span class="cells" aria-hidden="true">{"".join(parts)}</span>'


CSS = """
@page { size: A4; margin: 14mm 15mm 16mm 15mm; }
* { box-sizing: border-box; }
body { font-family: 'Noto Sans KR', sans-serif; color: #1f2a44; font-size: 10.5pt; line-height: 1.6; margin: 0; }
header.doc { display:flex; justify-content:space-between; align-items:flex-end; border-bottom: 3px solid #10b981; padding-bottom: 6px; }
.kicker { font-size: 10pt; color:#0f766e; font-weight:700; margin:0; }
h1 { font-size: 24pt; margin: 2px 0 0; line-height:1.2; }
.meta { font-size: 9pt; color:#4a586c; text-align:right; margin:0; }
h2 { font-size: 15pt; margin: 14px 0 6px; padding: 4px 10px; background:#10b981; color:#fff; border-radius:6px; line-height:1.3; }
h3 { break-after: avoid; font-size: 12pt; margin: 14px 0 6px; padding-left: 10px; border-left: 5px solid #10b981; line-height:1.3; }
section.part.newpage { break-before: page; }
section.part.newpage > h2 { margin-top: 0; }
p { margin: 4px 0; }
ul.b { margin: 4px 0; padding-left: 20px; }
.guide { background:#fff8e6; border-radius:8px; padding: 6px 12px 6px 30px; font-size: 9.5pt; }
blockquote.reg { background:#f6f8fb; border:1px solid #dbe3ec; border-radius: 8px; padding: 8px 14px; margin:0; }
.reg .n { font-weight:700; color:#0f766e; margin-right:6px; }
.src { font-size: 8.5pt; color:#4a586c; }
.key { background:#ecfdf5; border-left: 5px solid #10b981; border-radius: 6px; padding: 8px 12px; font-weight:700; font-size: 11.5pt; margin: 4px 0 6px; }
.big { display:flex; gap: 20px; align-items:center; }
.caption { font-size: 9.5pt; color:#3c4a60; margin: 8px 0 4px; }
.cards { display:grid; grid-template-columns: repeat(4, 1fr); gap: 8px; list-style:none; padding:0; margin:0; }
.cards li { border:1px solid #dbe3ec; border-radius: 10px; padding: 4px 8px; break-inside: avoid; }
.cards .nm { font-weight:700; font-size: 12pt; line-height:1.3; margin:0; }
.cards .ln { font-size: 9pt; color:#3c4a60; margin:0; }
.cells { display:flex; gap:4px; align-items:flex-start; margin: 2px 0; }
.cw { display:flex; flex-direction:column; align-items:center; }
.cl { font-size: 8pt; color:#4a586c; line-height:1.2; }
.br { font-family: 'DejaVu Sans', sans-serif; font-size: 14pt; letter-spacing: 1px; }
.hint { font-size: 9.5pt; color:#4a586c; margin: 0 0 6px; }
.ex { display:grid; grid-template-columns: repeat(4, 1fr); gap: 8px; list-style:none; padding:0; margin:0; }
.ex li { border:1px solid #dbe3ec; border-radius:10px; padding: 4px 6px 6px; text-align:center; break-inside: avoid; display:flex; flex-direction:column; align-items:center; }
.ex .no { font-size: 9pt; color:#4a586c; }
.ex .ask { font-size: 15pt; font-weight:700; }
.ex .desc { font-size: 8.5pt; color:#3c4a60; line-height:1.35; }
.ex .blank { margin-top: 4px; }
.checks { list-style:none; padding-left: 4px; margin: 0; }
.checks li::before { content: '□'; margin-right: 8px; font-size: 12pt; }
.next { background:#eff6ff; border-radius:8px; padding: 8px 12px; }
.keep { break-inside: avoid; }
.answers p { font-size: 9.5pt; }
table.tbl { width: calc(100% - 2px); table-layout: fixed; border-collapse: collapse; font-size: 9.5pt; margin: 4px 0; }
table.tbl caption { text-align:left; font-size: 9.5pt; color:#3c4a60; margin-bottom: 4px; }
table.tbl th, table.tbl td { border:1px solid #dbe3ec; padding: 2px 3px; text-align:center; line-height:1.3; }
table.tbl thead th, table.tbl tbody th { background:#ecfdf5; }
table.tbl tr { break-inside: avoid; }
table.tbl td .br { font-size: 12pt; display:block; }
.muted { color:#7d8ca0; font-size: 8.5pt; }
"""


def block_html(b):
    t = b['t']
    if t == 'p':
        return f'<p>{escape(b["text"])}</p>'
    if t == 'bullets':
        cls = ' class="b guide"' if b.get('style') == 'guide' else ' class="b"'
        return f'<ul{cls}>' + ''.join(f'<li>{escape(i)}</li>' for i in b['items']) + '</ul>'
    if t == 'rules':
        body = ''.join(f'<p><span class="n">{escape(n)}</span>{escape(x)}</p>' for n, x in b['items'])
        return f'<blockquote class="reg">{body}<p class="src">출처: {escape(b["src"])}</p></blockquote>'
    if t == 'key':
        return f'<p class="key">{escape(b["text"])}</p>'
    if t == 'big_cell':
        return (f'<div class="big">{cell_svg(range(1, 7), 1.9, labels=True)}'
                '<ul class="b">' + ''.join(f'<li>{n}점: {POS[n]}</li>' for n in range(1, 7)) + '</ul></div>')
    if t == 'cards':
        cap = f'<p class="caption">{escape(b["caption"])}</p>' if b.get('caption') else ''
        items = []
        for c in b['items']:
            line = c.get('line') or dots_text(c['cells'])
            items.append(f'<li{span(c["cells"])}><p class="nm">{escape(c["name"])}</p>{cell_row(c["cells"], c.get("labels"))}'
                         f'<p class="ln">{escape(line)}</p><p class="ln">점자: {escape(braille(c["cells"]))}</p></li>')
        grid = '<ul class="cards">' + ''.join(items) + '</ul>'
        # 설명 글이 카드와 다른 쪽으로 떨어지지 않게 묶는다
        return f'<div class="keep">{cap}{grid}</div>' if cap else grid
    if t == 'read_ex':
        items = []
        for i, c in enumerate(b['items'], 1):
            items.append(f'<li{span(c["cells"])}><span class="no">({i})</span>{cell_row(c["cells"], c.get("labels"))}'
                         f'<span class="desc">{escape(c["name"])}<br>{escape(braille(c["cells"]))}</span>'
                         f'<span class="blank">{escape(b.get("blank", "(    )"))}</span></li>')
        return f'<p class="hint">{escape(b["hint"])}</p><ol class="ex">' + ''.join(items) + '</ol>'
    if t == 'write_ex':
        items = []
        for i, w in enumerate(b['items'], 1):
            items.append(f'<li{span([[]] * w["cells"])}><span class="no">({i})</span><span class="ask">{escape(w["ask"])}</span>'
                         f'<span class="desc">빈 점칸 {w["cells"]}칸</span>{cell_row([[]] * w["cells"], dashed=True)}</li>')
        return f'<p class="hint">{escape(b["hint"])}</p><ol class="ex">' + ''.join(items) + '</ol>'
    if t == 'table':
        def td(c):  # '고 ⠈⠥' → 고 / ⠈⠥ 두 줄
            head, _, rest = c.partition(' ')
            if not rest:
                return escape(head)
            return escape(head) + (escape(rest) if rest[0] >= '\u2800' else f'<span class="muted" style="display:block">{escape(rest)}</span>')
        cap = f'<caption>{escape(b["caption"])}</caption>' if b.get('caption') else ''
        head = '<tr>' + ''.join(f'<th scope="col">{escape(h)}</th>' for h in b['head']) + '</tr>'
        body = ''.join('<tr>' + f'<th scope="row">{escape(r[0])}</th>' + ''.join(f'<td>{td(c)}</td>' for c in r[1:]) + '</tr>'
                       for r in b['rows'])
        return f'<table class="tbl">{cap}<thead>{head}</thead><tbody>{body}</tbody></table>'
    if t == 'checks':
        return '<ul class="checks">' + ''.join(f'<li>{escape(i)}</li>' for i in b['items']) + '</ul>'
    if t == 'next':
        return f'<p class="next">{escape(b["text"])}</p>'
    if t == 'answers':
        return '<div class="answers">' + ''.join(f'<p><b>{escape(k)}</b>: {escape(v)}</p>' for k, v in b['items']) + '</div>'
    raise ValueError(t)


def render(doc):
    u = doc
    title = doc_title(u)
    h = ['<!doctype html><html lang="ko"><head><meta charset="utf-8">', f'<title>{escape(title)}</title>',
         '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=block" rel="stylesheet">',
         f'<style>{CSS}</style></head><body><main>',
         f'<header class="doc"><div><p class="kicker">{lang_label(u)} 점자 {u["num"]}단원 · {escape(u["part"])}</p>'
         f'<h1>{escape(u["title"])}</h1></div><p class="meta">게임 전 학습자료<br>이름: ____________</p></header>']
    for pi, part in enumerate(doc['parts']):
        cls = 'part newpage' if pi else 'part'
        h.append(f'<section class="{cls}"><h2>{pi + 1}. {escape(part["title"])}</h2>')
        for si, sec in enumerate(part['sections']):
            blocks = [block_html(b) for b in sec['blocks']]
            # 제목이 쪽 끝에 홀로 남지 않게 첫 블록과 붙여 둔다 (큰 카드 묶음은 붙이지 않아 빈 공간이 덜 생긴다)
            lead = 1
            h.append(f'<section><div class="keep"><h3>{HANGUL_NUM[si]}. {escape(sec["title"])}</h3>{"".join(blocks[:lead])}</div>')
            h.extend(blocks[lead:])
            h.append('</section>')
        h.append('</section>')
    h.append('</main></body></html>')
    return '\n'.join(h)
