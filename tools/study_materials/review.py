"""완성한 단원 학습자료를 다시 검토한다. 하나라도 틀리면 '고칠 것'을 보여 주고 실패로 끝난다.

  python tools/study_materials/review.py ko-initial --skill <hwpx 스킬 폴더> [--png <그림 폴더>]

검토 항목 (SKILL.md 5절)
  1. 점형: 카드·연습 문제의 점 설명 = 점칸 = 점자 문자 (단원 파일의 규정집 대조 assert는 build()에서 다시 돈다)
  2. 정답: 문제 수와 정답 수, 쓰기 정답의 점형
  3. 읽기 연습 설명에 답이 드러나지 않는지
  4. 화면낭독기 구조: PDF 태그·제목·쪽 수, 제목 순서, 한글 파일의 칸 안 순서(설명 → 점자 → 그림)
  5. 두 파일 일치: 제목, 규정 원문, 카드, 정답이 한글 파일과 PDF에 똑같이 있는지
  6. 겉모양: 거의 빈 쪽이 없는지 (--png로 쪽 그림을 떠서 눈으로도 본다)
  7. 앱 연결: curriculum.json materials 경로의 파일이 있는지
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build import unit_module  # noqa: E402
from common import POS, REPO, braille, doc_title, dots_text, unit_data  # noqa: E402
from render_html import HANGUL_NUM  # noqa: E402

DOTS_ONLY = re.compile(r'^[\d·점 +빈칸]+$')


def sh(*cmd):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, check=True).stdout


def flat(text):
    return re.sub(r'\s+', '', text)


def blocks(doc, kind):
    for part in doc['parts']:
        for sec in part['sections']:
            for b in sec['blocks']:
                if b['t'] == kind:
                    yield b


def review(uid, skill, png=None):
    problems = []
    bad = problems.append
    doc = unit_module(uid).build()  # 단원 파일의 규정집 대조 assert가 여기서 다시 돈다
    pdf = REPO / 'web' / 'materials' / doc['lang'] / f'{uid}.pdf'
    hwpx = pdf.with_suffix('.hwpx')
    for f in (pdf, hwpx):
        if not f.exists():
            bad(f'파일 없음: {f}')
    if problems:
        return problems

    # 1·3. 점형 설명과 읽기 연습
    for b in blocks(doc, 'cards'):
        for c in b['items']:
            line = c.get('line') or ''
            if line[:1].isdigit() and not line.startswith(dots_text(c['cells'])):
                bad(f'카드 {c["name"]}: 점 설명 「{line}」 ≠ 점칸 {dots_text(c["cells"])}')
    reads = [c for b in blocks(doc, 'read_ex') for c in b['items']]
    for i, c in enumerate(reads, 1):
        if c['name'] in POS.values():  # 점의 자리 단원: 자리 이름으로 묻고 점 번호로 답한다
            continue
        if not DOTS_ONLY.match(c['name']) or c['name'] != dots_text(c['cells']):
            bad(f'읽기 ({i}): 설명 「{c["name"]}」이 점 번호만이 아니거나 점칸과 다름 (답이 드러날 수 있음)')
    writes = [w for b in blocks(doc, 'write_ex') for w in b['items']]

    # 2. 정답
    answers = dict(next(blocks(doc, 'answers'))['items'])
    n_read = len(re.findall(r'\(\d+\)', answers.get('읽기 연습', '')))
    n_write = len(re.findall(r'\(\d+\)', answers.get('쓰기 연습', '')))
    if n_read != len(reads):
        bad(f'읽기 연습 문제 {len(reads)}개, 정답 {n_read}개')
    if n_write != len(writes):
        bad(f'쓰기 연습 문제 {len(writes)}개, 정답 {n_write}개')
    segs = dict((int(n), t.strip(' ,')) for n, t in re.findall(r'\((\d+)\) ([^(]*)', answers.get('쓰기 연습', '')))
    for i, w in enumerate(writes, 1):
        seg = segs.get(i, '')
        br = ''.join(re.findall(r'[\u2800-\u28ff]+', seg))
        if not seg:
            bad(f'쓰기 ({i}) 「{w["ask"]}」의 정답이 없음')
        elif br:  # 점자로 답하는 문제: 칸 수와 점 번호 확인
            cells = [[d + 1 for d in range(6) if (ord(ch) - 0x2800) >> d & 1] for ch in br]
            if len(cells) != w['cells']:
                bad(f'쓰기 ({i}) 「{w["ask"]}」: 빈 칸 {w["cells"]}칸인데 정답은 {len(cells)}칸')
            if dots_text(cells) not in seg:
                bad(f'쓰기 ({i}) 「{w["ask"]}」: 정답 「{seg}」의 점 번호가 점자 {br}와 다름')

    # 4. PDF 구조
    info = sh('pdfinfo', pdf)
    if 'Tagged:          yes' not in info:
        bad('PDF에 태그가 없음')
    if f'Title:           {doc_title(doc)}' not in info:
        bad('PDF 문서 제목이 다름')
    pages = int(re.search(r'Pages:\s+(\d+)', info).group(1))
    if pages < 4:
        bad(f'PDF가 {pages}쪽뿐 (네 부분이 새 쪽에서 시작해야 함)')

    pdf_text = sh('pdftotext', '-layout', pdf, '-')
    hwp_text = sh(sys.executable, Path(skill) / 'scripts' / 'text_extract.py', '--include-tables', hwpx)
    fp, fh = flat(pdf_text), flat(hwp_text)

    # 4·5. 제목 순서 (PDF는 번호 붙은 제목, 한글 파일은 개요 제목)
    pos_p = pos_h = 0
    for pi, part in enumerate(doc['parts']):
        heads = [(f'{pi + 1}.{part["title"]}', part['title'])] + [
            (f'{HANGUL_NUM[si]}.{s["title"]}', s['title']) for si, s in enumerate(part['sections'])]
        for hp, hh in heads:
            hp, hh = flat(hp), flat(hh)
            i = fp.find(hp, pos_p)
            j = fh.find(hh, pos_h)
            if i < 0:
                bad(f'PDF: 제목 「{hp}」이 없거나 순서가 다름')
            else:
                pos_p = i
            if j < 0:
                bad(f'한글 파일: 제목 「{hh}」이 없거나 순서가 다름')
            else:
                pos_h = j

    # 5. 두 파일에 같은 내용
    must = [doc['title']]
    must += [x for b in blocks(doc, 'rules') for _, x in b['items']]
    for b in blocks(doc, 'cards'):
        for c in b['items']:
            must += [c['name'], braille(c['cells'])]
    must += [braille(c['cells']) for c in reads]
    must += [w['ask'] for w in writes]
    must += [v for _, v in next(blocks(doc, 'answers'))['items']]
    for text in must:
        t = flat(text)
        if t not in fp:
            bad(f'PDF에 없음: {text[:40]}')
        if t not in fh:
            bad(f'한글 파일에 없음: {text[:40]}')

    # 4. 한글 파일 카드 칸 안 순서: 이름 → 점 번호 → 점자 → 그림
    for b in blocks(doc, 'cards'):
        for c in b['items']:
            name, line, br = flat(c['name']), flat(c.get('line') or dots_text(c['cells'])), braille(c['cells'])
            m = re.search(re.escape(name) + re.escape(line) + re.escape(br) + '[●○]', fh)
            if not m:
                bad(f'한글 파일 카드 「{c["name"]}」: 칸 안 순서가 이름 → 설명 → 점자 → 그림이 아님')

    # 6. 겉모양: 거의 빈 쪽
    for p in range(1, pages + 1):
        t = flat(sh('pdftotext', '-f', p, '-l', p, pdf, '-'))
        t = re.sub(r'-\d+/\d+-', '', t)
        if len(t) < 60:
            bad(f'PDF {p}쪽이 거의 비어 있음 ({len(t)}자)')
    if png:
        Path(png).mkdir(parents=True, exist_ok=True)
        sh('pdftoppm', '-r', '60', '-png', pdf, Path(png) / uid)

    # 7. 앱 연결
    mat = unit_data(uid).get('materials')
    if not mat:
        bad('curriculum.json에 materials가 없음 (로비 버튼이 「준비 중」으로 남음)')
    else:
        for path in mat.values():
            if not (REPO / 'web' / path).exists():
                bad(f'materials 경로의 파일 없음: {path}')
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('units', nargs='+')
    ap.add_argument('--skill', required=True)
    ap.add_argument('--png', help='쪽 그림을 뜰 폴더')
    a = ap.parse_args()
    failed = False
    for uid in a.units:
        problems = review(uid, a.skill, a.png)
        if problems:
            failed = True
            print(f'{uid}: 고칠 것 {len(problems)}개')
            for p in problems:
                print('  -', p)
        else:
            print(f'{uid}: 검토 통과')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
