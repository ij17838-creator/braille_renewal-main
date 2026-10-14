// 발음 검사 확인: 한글 단원마다 문제를 많이 만들어, 끝소리 규칙이 든 문제나 소리로 헷갈리는 보기가 없는지 본다.
// 실행: node tests/js/check_sound_confusion.mjs
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const store = { };
globalThis.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; }
};
globalThis.fetch = async (url) => {
  const body = readFileSync(fileURLToPath(url), 'utf8');
  return { ok: true, json: async () => JSON.parse(body) };
};

const shell = await import('../../web/js/shell.js');
shell.saveStudyMode('free');
const { loadQuizEngine } = await import('../../web/js/quiz_combo.js');
const { unitsFor } = await import('../../web/js/curriculum.js');
const { soundsAsWritten, soundsConfusable } = await import('../../web/js/ko_pronounce.js');

const engine = await loadQuizEngine();
const N = Number(process.argv[2] || 200);
let bad = 0;
const singleNeutral = new Set();
const few = {};
const samples = {};
for (const unit of unitsFor('ko')) {
  let made = 0;
  for (let i = 0; i < N; i += 1) {
    const item = engine.next({ lang: 'KO', unitId: unit.id });
    if (!item) continue;
    made += 1;
    const target = item.target_text;
    // 카드 하나를 그대로 낸 문제(단원 주제 자체, 규정집 보기 낱말)는 그대로 둔다. 무작위 조합만 검사한다.
    const single = item.parts.length === 1;
    if (single && !soundsAsWritten(target)) singleNeutral.add(`${unit.id}: ${target}`);
    if (!single && !soundsAsWritten(target)) { bad += 1; console.log(`[끝소리] ${unit.id}: ${target}`); }
    for (const option of item.meaning_options.concat(item.available_blocks)) {
      if (option === target) continue;
      if (soundsConfusable(target, option)) { bad += 1; console.log(`[보기] ${unit.id}: ${target} / ${option}`); }
      if (!single && Array.from(option).length > 1 && !soundsAsWritten(option)) { bad += 1; console.log(`[보기 끝소리] ${unit.id}: ${target} / ${option}`); }
    }
    const others = item.meaning_options.filter((o) => o !== target);
    if (others.length < 2) few[unit.id] = (few[unit.id] || 0) + 1;
    (samples[unit.id] = samples[unit.id] || new Set()).add(`${target} → 보기: ${item.meaning_options.filter((o) => o !== target).join(', ')}`);
  }
  if (!made) console.log(`(문제 없음) ${unit.id}`);
}
if (process.argv.includes('--samples')) {
  for (const [id, set] of Object.entries(samples)) console.log(id, '\n  ' + Array.from(set).slice(0, 4).join('\n  '));
}
if (Object.keys(few).length) console.log('(참고) 보기가 둘보다 적은 문제 수:', JSON.stringify(few));
if (singleNeutral.size) console.log(`(참고) 카드 하나로 낸 문제 중 끝소리 규칙이 걸리는 것 ${singleNeutral.size}개:`, Array.from(singleNeutral).slice(0, 12).join(' / '));
console.log(bad ? `문제 ${bad}건` : '통과');
process.exit(bad ? 1 : 0);
