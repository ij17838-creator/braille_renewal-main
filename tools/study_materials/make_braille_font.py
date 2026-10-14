"""한글 파일용 6점 점자 글꼴(Braille6Dot.ttf)을 만든다.

윈도에서 한글 프로그램은 점자 문자(⠿ 등)를 8점 칸(4줄)으로 그리는 글꼴로 대신 보여 주어,
6점 점자인데도 맨 아래에 빈 점 2개가 더 보인다. 이 글꼴은 U+2800~283F(6점 점형 64개)만
2열 3줄로 그린다. 볼록한 점은 ●, 빈 자리는 ○. 점형 데이터는 바꾸지 않고 보이는 모양만 바꾼다.

  python tools/study_materials/make_braille_font.py   # → tools/study_materials/fonts/Braille6Dot.ttf
"""
import math
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

FAMILY = 'Braille6Dot'
OUT = Path(__file__).resolve().parent / 'fonts' / f'{FAMILY}.ttf'
UPM = 1000
ADV = 640                      # 칸 하나의 폭 (칸 사이가 점 사이보다 넓게)
COLS = (170, 420)              # 왼쪽(1·2·3점), 오른쪽(4·5·6점) 점의 가운데
ROWS = (640, 390, 140)         # 위·가운데·아래 줄
R_FILL, R_OUT, R_IN = 92, 88, 62


def circle(pen, cx, cy, r, clockwise=True):
    """2차 곡선 8조각으로 원을 그린다 (TrueType 바깥 윤곽은 시계 방향)."""
    k = r / math.cos(math.pi / 8)
    angles = [i * math.pi / 4 for i in range(8)]
    if clockwise:
        angles = angles[::-1]
    pen.qCurveTo(*[(round(cx + k * math.cos(a)), round(cy + k * math.sin(a))) for a in angles], None)
    pen.closePath()


def cell_glyph(dots):
    pen = TTGlyphPen(None)
    for d in range(1, 7):
        cx, cy = COLS[(d - 1) // 3], ROWS[(d - 1) % 3]
        if d in dots:
            circle(pen, cx, cy, R_FILL)
        else:
            circle(pen, cx, cy, R_OUT)
            circle(pen, cx, cy, R_IN, clockwise=False)
    return pen.glyph()


def build():
    names = ['.notdef', 'space'] + [f'uni{0x2800 + v:04X}' for v in range(64)]
    glyphs = {'.notdef': TTGlyphPen(None).glyph(), 'space': TTGlyphPen(None).glyph()}
    cmap = {0x20: 'space'}
    for v in range(64):
        n = f'uni{0x2800 + v:04X}'
        glyphs[n] = cell_glyph([i + 1 for i in range(6) if v >> i & 1])
        cmap[0x2800 + v] = n
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (ADV, 0) for n in names})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({'familyName': FAMILY, 'styleName': 'Regular', 'copyright': '점자 학습 프로그램, 자유 사용',
                       'uniqueFontIdentifier': FAMILY + '-Regular', 'fullName': FAMILY, 'psName': FAMILY + '-Regular'})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200, fsType=0)
    fb.setupPost()
    OUT.parent.mkdir(exist_ok=True)
    fb.save(OUT)
    return OUT


if __name__ == '__main__':
    print(build())
