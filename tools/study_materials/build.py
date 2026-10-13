"""단원 학습자료 만들기: 한글 파일(.hwpx)과 PDF를 같은 내용으로 만든다.

  python tools/study_materials/build.py ko-number --skill <hwpx 스킬 폴더> --out web/materials/ko

필요한 것: hwpx 스킬(report 템플릿과 build/validate 스크립트), Node Playwright(Chromium), 인터넷(구글 글꼴).
새 단원은 units/에 파일을 하나 더하고 UNITS에 등록한다.
"""
import argparse
import importlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import doc_title, file_stem  # noqa: E402
import render_html  # noqa: E402
import render_hwpx  # noqa: E402

UNITS = {
    'ko-dots': 'units.ko_dots',
    'ko-number': 'units.ko_number',
}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'실패: {" ".join(map(str, cmd))}\n{r.stdout}\n{r.stderr}')
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('units', nargs='+', help='단원 id (예: ko-dots ko-number)')
    ap.add_argument('--skill', required=True, type=Path, help='hwpx 스킬 폴더')
    ap.add_argument('--out', type=Path, default=HERE.parents[1] / 'web' / 'materials' / 'ko')
    ap.add_argument('--copy-to', type=Path, help='사람이 읽는 이름(한글점자_2단원_숫자.*)으로도 복사할 폴더')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    scripts = a.skill / 'scripts'
    for uid in a.units:
        doc = importlib.import_module(UNITS[uid]).build()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            html = tmp / 'doc.html'
            html.write_text(render_html.render(doc), encoding='utf-8')
            pdf = a.out / f'{uid}.pdf'
            run(['node', str(HERE / 'topdf.js'), str(html), str(pdf)])

            (tmp / 'header.xml').write_text(render_hwpx.build_header(a.skill), encoding='utf-8')
            (tmp / 'section0.xml').write_text(render_hwpx.build_section(doc, a.skill), encoding='utf-8')
            hwpx = a.out / f'{uid}.hwpx'
            hwpx.unlink(missing_ok=True)
            run([sys.executable, scripts / 'build_hwpx.py', '--template', 'report', '--header', tmp / 'header.xml',
                 '--section', tmp / 'section0.xml', '--title', doc_title(doc), '--creator', '점자 학습 프로그램', '--output', hwpx])
            run([sys.executable, scripts / 'fix_namespaces.py', hwpx])
            run([sys.executable, scripts / 'finalize_hwpx.py', hwpx, '--strip-linesegarray'])
            print(run([sys.executable, scripts / 'validate.py', hwpx]).strip())
        if a.copy_to:
            a.copy_to.mkdir(parents=True, exist_ok=True)
            for ext in ('hwpx', 'pdf'):
                shutil.copy(a.out / f'{uid}.{ext}', a.copy_to / f'{file_stem(doc)}.{ext}')
        print(f'{uid}: {pdf.name}, {hwpx.name}')


if __name__ == '__main__':
    main()
