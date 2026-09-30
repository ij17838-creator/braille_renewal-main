/**
 * 단원표. 화면은 쓰지 않고, 단원 목록과 학습 카드만 돌려준다.
 * 점의 자리만 정적 카드이고 나머지는 JSON 구간을 자른다.
 *
 * 카드 하나는 조립 순서(steps)를 함께 가진다.
 * 예) ㄱ 4점 ⠈ + ㅏ 1·2·6점 ⠣
 */

const CHO = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
const JUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'];
const JONG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
const TENSE = { 'ㄲ': 'ㄱ', 'ㄸ': 'ㄷ', 'ㅃ': 'ㅂ', 'ㅆ': 'ㅅ', 'ㅉ': 'ㅈ' };

const BUNDLE_NAMES = new Set([
  'ko.json',
  'ko_marks.json',
  'numbers.json',
  'en_spell.json',
  'en_shortform.json',
  'en_contractions.json'
]);

async function readJson(name) {
  const url = new URL(name, import.meta.url);
  try {
    const { readFileSync } = await import('node:fs');
    const { fileURLToPath } = await import('node:url');
    return JSON.parse(readFileSync(fileURLToPath(url), 'utf8'));
  } catch {
    const res = await fetch(url);
    if (!res.ok) throw new Error(name);
    return res.json();
  }
}

const table = await readJson('curriculum.json');

export function unitsFor(lang) {
  const key = String(lang || '').toLowerCase();
  return table.units
    .filter((unit) => unit.lang === key)
    .sort((a, b) => a.order - b.order);
}

const UNIT_ALIAS = { 'ko-cho': 'ko-initial' };

export function unitById(id) {
  const key = UNIT_ALIAS[id] || id;
  return table.units.find((unit) => unit.id === key) || null;
}

export function isComposeUnit(unit) {
  return unit?.source?.kind === 'compose';
}

export function cardsFor(unit, data) {
  if (!unit) return [];
  if (unit.source?.kind === 'static') {
    return (unit.source.cards || []).map(staticCard);
  }
  const slices = unit.source?.slices || [];
  const cards = [];
  for (const slice of slices) cards.push(...cardsFromSlice(slice, data));
  return cards;
}

/**
 * 이 단원과 앞 단원의 재료. 생성기는 여기 있는 것만 쓴다.
 * 문장 단원처럼 재료를 이어 붙이는 단원은 재료를 갖지 않는다.
 */
export function materialsFor(unit, data) {
  if (!unit) return [];
  return unitsFor(unit.lang)
    .filter((item) => item.order <= unit.order && !isComposeUnit(item))
    .map((item) => ({ unit: item, cards: cardsFor(item, data) }));
}

function cardsFromSlice(slice, data) {
  if (slice.ranges) return syllableCards(slice, data);
  if (slice.role === 'exception') return exceptionCards(slice, data);
  const node = nodeAt(data, slice.bundle, slice.path || []);
  const prefix = prefixStep(slice, data);
  if (slice.role === 'contraction' && Array.isArray(node)) return contractionCards(node, slice);
  return glyphEntries(node)
    .filter(([, item]) => acceptItem(item, slice.filter))
    .map(([key, item]) => glyphCard(key, item, slice.role, prefix));
}

function nodeAt(data, bundle, path) {
  if (!bundle) return null;
  const root = resolveBundle(data, bundle);
  if (!root) return null;
  return path.reduce((node, key) => (node == null ? undefined : node[key]), root);
}

function resolveBundle(data, bundle) {
  if (!data || typeof data !== 'object') return null;
  if (Object.prototype.hasOwnProperty.call(data, bundle)) return data[bundle];
  const keys = Object.keys(data);
  if (keys.some((key) => BUNDLE_NAMES.has(key))) return null;
  return data;
}

function acceptItem(item, filter) {
  if (!filter) return true;
  if (filter.type) {
    const types = Array.isArray(filter.type) ? filter.type : [filter.type];
    if (!types.includes(item.type)) return false;
  }
  if (filter.has && item[filter.has] == null) return false;
  return true;
}

function isGlyph(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  return Array.isArray(value.dots) || typeof value.unicode === 'string';
}

function glyphEntries(node) {
  if (isGlyph(node)) return [['', node]];
  if (Array.isArray(node)) {
    const out = [];
    for (const group of node) {
      if (group && group.items) out.push(...glyphEntries(group.items));
    }
    return out;
  }
  if (!node || typeof node !== 'object') return [];
  if (node.items && typeof node.items === 'object' && !Array.isArray(node.items)) {
    return glyphEntries(node.items);
  }
  return Object.entries(node).filter(([, value]) => isGlyph(value));
}

// ---------------------------------------------------------------------------
// 점과 조립 순서
// ---------------------------------------------------------------------------

const DOT_BIT = { 1: 0x01, 2: 0x02, 3: 0x04, 4: 0x08, 5: 0x10, 6: 0x20 };

export function cellGlyph(cell) {
  let pattern = 0;
  for (const dot of cell || []) pattern |= DOT_BIT[dot] || 0;
  return String.fromCharCode(0x2800 + pattern);
}

export function cellsOf(dots) {
  if (!Array.isArray(dots) || dots.length === 0) return [];
  const cells = typeof dots[0] === 'number' ? [dots] : dots;
  return cells
    .filter((cell) => Array.isArray(cell))
    .map((cell) => cell.slice());
}

function dotTextFromCells(cells) {
  if (!cells.length) return '생략';
  return cells.map((cell) => (cell.length ? `${cell.join('·')}점` : '빈 칸')).join(' + ');
}

function stepPattern(step) {
  return step.pattern != null && step.pattern !== '' ? step.pattern : step.cells.map(cellGlyph).join('');
}

function stepText(step) {
  if (!step.cells.length) return `${step.label} ${step.note || '적지 않음'}`;
  const cells = step.cells.map((cell) => (cell.length ? `${cell.join('·')}점 ${cellGlyph(cell)}` : '빈 칸'));
  return `${step.label} ${cells.join(' ')}`;
}

export function stepsPattern(steps) {
  return (steps || []).map(stepPattern).join('');
}

/** 조립 순서 해설. 예) ㄱ 4점 ⠈ + ㅏ 1·2·6점 ⠣ */
export function assemblyText(steps) {
  return (steps || []).map(stepText).join(' + ');
}

export function makeStep(label, dots, pattern, note) {
  return { label, cells: cellsOf(dots), pattern: pattern || '', note: note || '' };
}

export function makeCard({ letter, steps, line, kind, extra }) {
  const cells = steps.flatMap((step) => step.cells);
  return {
    letter,
    kind,
    pattern: steps.map(stepPattern).join(''),
    dots: cells,
    dotText: dotTextFromCells(cells),
    line: line || '',
    steps,
    explain: assemblyText(steps),
    ...(extra || {})
  };
}

function staticCard(card) {
  const step = makeStep(card.letter, card.dots, card.pattern);
  const made = makeCard({ letter: card.letter, steps: [step], line: card.line, kind: 'static' });
  if (card.pattern) made.pattern = card.pattern;
  return made;
}

// ---------------------------------------------------------------------------
// 글 한 조각 카드
// ---------------------------------------------------------------------------

function letterOf(key, item, role) {
  if (role === 'mark' || role === 'digit') return key;
  if (role === 'wordsign' || role === 'shortform' || role === 'contraction') return item.word || key;
  if (role === 'indicator') return item.name || key;
  return item.char || item.syllable || item.word || item.name || key;
}

function lineFor(role, letter, text, item, key) {
  if (item.isOmitted || (role === 'chosung' && cellsOf(item.dots).length === 0)) {
    return `첫소리 ${letter}은 적지 않고 모음만 적습니다.`;
  }
  if (role === 'mark') return `${item.word}의 점형은 ${text}입니다.`;
  const label = {
    chosung: `첫소리 ${letter}`,
    jungsung: `모음 ${letter}`,
    jongsung: `받침 ${letter}`,
    ga: `약자 ${letter}`,
    eok: `약자 ${letter}`,
    word: `단어 약어 ${letter}`,
    digit: `숫자 ${letter}`,
    indicator: item.name || letter,
    alphabet: `알파벳 ${letter}`,
    wordsign: `${item.word} (${key})`,
    shortform: `${item.word} (${key})`,
    contraction: `축약 ${item.word || letter}`
  }[role] || letter;
  return `${label}의 점형은 ${text}입니다.`;
}

function prefixStep(slice, data) {
  if (!slice.prefix) return null;
  const node = nodeAt(data, slice.prefix.bundle, slice.prefix.path || []);
  if (!isGlyph(node)) return null;
  return makeStep(node.name || '수표', node.dots, node.unicode);
}

function glyphCard(key, item, role, prefix) {
  const letter = letterOf(key, item, role);
  const omitted = item.isOmitted || (role === 'chosung' && cellsOf(item.dots).length === 0);
  const main = makeStep(letter, item.dots, item.unicode, omitted ? '적지 않음' : '');
  const steps = prefix && role === 'digit' ? [prefix, main] : [main];
  const card = makeCard({ letter, steps, kind: role });
  card.line = lineFor(role, letter, card.dotText, item, key);
  return card;
}

function contractionCards(groups, slice) {
  const cards = [];
  for (const group of groups) {
    if (!group || !group.items) continue;
    const rule = group.rule || {};
    const standalone = !!(rule.canStandAlone || rule.standingAloneOnly) && !rule.requiresFollowingLetters;
    for (const [key, item] of glyphEntries(group.items)) {
      if (!acceptItem(item, slice.filter)) continue;
      const card = glyphCard(key, item, 'contraction', null);
      card.standalone = standalone;
      cards.push(card);
    }
  }
  return cards;
}

// ---------------------------------------------------------------------------
// 한글 음절: 풀어 쓰기와 약자 판별
// ---------------------------------------------------------------------------

export function composeSyllable(cho, jung, jong) {
  const ci = CHO.indexOf(cho);
  const ji = JUNG.indexOf(jung);
  const ki = JONG.indexOf(jong || '');
  if (ci < 0 || ji < 0 || ki < 0) return '';
  return String.fromCharCode(0xAC00 + (ci * 21 + ji) * 28 + ki);
}

export function decomposeSyllable(ch) {
  const code = String(ch || '').charCodeAt(0) - 0xAC00;
  if (code < 0 || code > 11171) return null;
  return [CHO[Math.floor(code / 588)], JUNG[Math.floor((code % 588) / 28)], JONG[code % 28]];
}

/**
 * 약자가 대신 적히는 조합을 가려낸다.
 * 풀어 쓴 음절 카드에는 여기에 걸리는 조합이 들어가지 않는다.
 *   - abbreviation_syllable에 있는 음절
 *   - 가·나·다 계열 첫소리 + ㅏ (된소리 포함, 받침이 붙어도 약자 + 받침)
 *   - 모음 + 받침이 억·언·얼 계열인 경우
 */
export function abbreviationIndex(ko) {
  const items = ko?.abbreviation_syllable?.items || {};
  const syllables = new Set();
  const gaOnsets = new Set();
  const vowelCoda = new Set();
  for (const [syllable, item] of Object.entries(items)) {
    syllables.add(syllable);
    const parts = decomposeSyllable(syllable);
    if (!parts) continue;
    if (item.type === 'ga_series' && parts[1] === 'ㅏ' && !parts[2]) gaOnsets.add(parts[0]);
    if (item.type === 'vowel_coda_series' && parts[2]) vowelCoda.add(`${parts[1]}|${parts[2]}`);
  }
  return {
    syllables,
    gaOnsets,
    vowelCoda,
    applies(cho, jung, jong) {
      const syllable = composeSyllable(cho, jung, jong);
      if (syllable && syllables.has(syllable)) return true;
      if (jung === 'ㅏ' && gaOnsets.has(TENSE[cho] || cho)) return true;
      if (jong && vowelCoda.has(`${jung}|${jong}`)) return true;
      return false;
    }
  };
}

function jamoMaps(ko) {
  return {
    cho: ko?.chosung?.items,
    jung: ko?.jungsung?.items,
    jong: ko?.jongsung?.items
  };
}

function spellSteps(cho, jung, jong, maps) {
  const choItem = maps.cho?.[cho];
  const jungItem = maps.jung?.[jung];
  const jongItem = jong ? maps.jong?.[jong] : null;
  if (!choItem || !jungItem || (jong && !jongItem)) return null;
  const steps = [];
  if (choItem.isOmitted || cellsOf(choItem.dots).length === 0) {
    steps.push(makeStep(cho, [], '', '생략'));
  } else {
    steps.push(makeStep(cho, choItem.dots, choItem.unicode));
  }
  steps.push(makeStep(jung, jungItem.dots, jungItem.unicode));
  if (jongItem) steps.push(makeStep(jong, jongItem.dots, jongItem.unicode));
  return steps;
}

function syllableCards(slice, data) {
  const ko = resolveBundle(data, slice.bundle);
  const maps = jamoMaps(ko);
  if (!maps.cho || !maps.jung || !maps.jong) return [];
  const abbreviation = abbreviationIndex(ko);
  const ranges = slice.ranges || {};
  const cards = [];
  for (const cho of ranges.cho || []) {
    for (const jung of ranges.jung || []) {
      for (const jong of ranges.jong || ['']) {
        const syllable = composeSyllable(cho, jung, jong);
        if (!syllable || abbreviation.applies(cho, jung, jong)) continue;
        const steps = spellSteps(cho, jung, jong, maps);
        if (!steps) continue;
        const card = makeCard({ letter: syllable, steps, kind: 'syllable' });
        card.line = `풀어 적은 ${syllable}(${steps.map((step) => step.label).join('+')})의 점형은 ${card.dotText}입니다.`;
        cards.push(card);
      }
    }
  }
  return cards;
}

// ---------------------------------------------------------------------------
// 예외: 약자와 풀어 쓴 형태를 같이 보여 준다
// ---------------------------------------------------------------------------

function exceptionCards(slice, data) {
  const ko = resolveBundle(data, slice.bundle);
  const items = ko?.abbreviation_syllable?.items;
  if (!items) return [];
  const maps = jamoMaps(ko);
  const numbers = resolveBundle(data, 'numbers.json');
  const prefix = numbers?.numeric_indicators?.num_prefix;
  const grade1 = numbers?.grade1_indicators?.grade1_symbol;
  const digitItem = (digit) => numbers?.digits?.[digit];
  const cards = [];

  const numberSteps = (digit) => {
    const item = digitItem(digit);
    if (!prefix || !item) return null;
    return [makeStep(prefix.name || '수표', prefix.dots, prefix.unicode), makeStep(digit, item.dots, item.unicode)];
  };

  const push = (letter, steps, wrongSteps, note, line) => {
    const card = makeCard({ letter, steps, kind: 'exception' });
    const wrong = wrongSteps.map(stepPattern).join('');
    card.contrast = wrong;
    card.explain = `${card.explain}. ${note}`;
    card.line = line(card.pattern, wrong);
    cards.push(card);
  };

  for (const [syllable, item] of Object.entries(items)) {
    if (!item.exception_rules) continue;
    const parts = decomposeSyllable(syllable);
    if (!parts) continue;
    const abbrStep = makeStep(`${syllable} 약자`, item.dots, item.unicode);
    const spelled = spellSteps(parts[0], parts[1], parts[2], maps);
    if (!spelled) continue;

    for (const follower of slice.followers || []) {
      const fp = decomposeSyllable(follower);
      if (!fp || fp[0] !== 'ㅇ') continue;
      const fsteps = spellSteps(fp[0], fp[1], fp[2], maps);
      if (!fsteps) continue;
      push(
        `${syllable}${follower}`,
        [...spelled, ...fsteps],
        [abbrStep, ...fsteps],
        `${syllable} 뒤에 모음이 바로 이어지므로 약자를 쓰지 않고 풀어 적습니다.`,
        (right, wrong) => `${syllable}${follower}: 약자 ${wrong}(×), 풀어 쓴 ${right}(○)`
      );
    }

    for (const digit of slice.digits || []) {
      const num = numberSteps(digit);
      if (!num) continue;
      push(
        `${digit}${syllable}`,
        [...num, ...spelled],
        [...num, abbrStep],
        `숫자 뒤의 ${syllable}는 약자를 쓰지 않고 풀어 적습니다.`,
        (right, wrong) => `${digit}${syllable}: 약자 ${wrong}(×), 풀어 쓴 ${right}(○)`
      );
    }
  }

  const rule = ko?.special_rules?.number_prefix_rule;
  const ruleDigit = slice.ruleDigit;
  const num = ruleDigit ? numberSteps(ruleDigit) : null;
  if (rule && num && grade1) {
    const affected = new Set(rule.affected_initials || []);
    for (const [syllable, item] of Object.entries(items)) {
      if (item.exception_rules || item.type !== 'ga_series') continue;
      const parts = decomposeSyllable(syllable);
      if (!parts || !affected.has(parts[0])) continue;
      const mark = makeStep(grade1.name || '1급 기호표', grade1.dots, grade1.unicode);
      const abbr = makeStep(`${syllable} 약자`, item.dots, item.unicode);
      push(
        `${ruleDigit}${syllable}`,
        [...num, mark, abbr],
        [...num, abbr],
        `숫자 뒤에 ${parts[0]}이 오면 숫자로 읽히지 않도록 사이에 ${mark.label}를 넣습니다.`,
        (right, wrong) => `${ruleDigit}${syllable}: 그대로 이으면 ${wrong}(×), ${mark.label} 넣은 ${right}(○)`
      );
    }
  }
  return cards;
}

async function demoIfMain() {
  if (typeof process === 'undefined' || !process.argv?.[1]) return;
  const { pathToFileURL } = await import('node:url');
  const href = pathToFileURL(process.argv[1]).href;
  if (import.meta.url.toLowerCase() !== href.toLowerCase()) return;

  const ko = await readJson('ko.json');
  const numbers = await readJson('numbers.json');
  const bundles = { 'ko.json': ko, 'numbers.json': numbers };
  console.log('한글 단원');
  for (const unit of unitsFor('ko')) {
    console.log(`${unit.order}. ${unit.title}`);
  }
  console.log('');
  for (const id of ['ko-initial', 'ko-syllable', 'ko-exception']) {
    console.log(id);
    for (const card of cardsFor(unitById(id), bundles).slice(0, 6)) {
      console.log(`${card.letter} → ${card.pattern || '(없음)'}  ${card.explain}`);
    }
  }
}

await demoIfMain();
