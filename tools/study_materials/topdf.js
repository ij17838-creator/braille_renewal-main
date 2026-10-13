// HTML → 태그 있는 PDF (화면낭독기용 구조, 책갈피, 쪽 번호)
// 사용: node topdf.js <입력.html> <출력.pdf>
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const [src, out] = process.argv.slice(2);
  const browser = await chromium.launch({ env: { ...process.env, LANG: 'C.UTF-8' } });
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(src), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({
    path: out, format: 'A4', printBackground: true, preferCSSPageSize: true, tagged: true, outline: true,
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="width:100%;text-align:center;font-size:8px;color:#666">- <span class="pageNumber"></span> / <span class="totalPages"></span> -</div>'
  });
  await browser.close();
})();
