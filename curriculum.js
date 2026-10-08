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
  if (slice.ranges || slice.syllables) return syllableCards(slice, data);
  if (slice.role === 'abbr') return abbrCards(slice, data);
  if (slice.role === 'exception') return exceptionCards(slice, data);
  const node = nodeAt(data, slice.bundle, slice.path || []);
  const prefix = prefixStep(slice, data);
  if (slice.role === 'contraction' && Array.isArray(node)) return contractionCards(node, slice);
  return glyphEntries(node)
    .filter(([key, item]) => acceptItem(item, slice.filter, key))
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

function acceptItem(item, filter, key) {
  if (!filter) return true;
  if (Array.isArray(filter.keys) && !filter.keys.includes(key)) return false;
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
      if (!acceptItem(item, slice.filter, key)) continue;
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
 *   - 모음 + 받침이 억·언·얼 계열인 경우 (ㅅ·ㅈ·ㅊ 뒤 성·정·청 포함)
 */
export function abbreviationIndex(ko) {
  const items = ko?.abbreviation_syllable?.items || {};
  const syllables = new Set();
  const gaOnsets = new Set();
  const vowelCoda = new Set();
  const vowelCodaKeys = new Set();
  for (const [syllable, item] of Object.entries(items)) {
    syllables.add(syllable);
    const parts = decomposeSyllable(syllable);
    if (!parts) continue;
    if (item.type === 'ga_series' && parts[1] === 'ㅏ' && !parts[2]) gaOnsets.add(parts[0]);
    if (item.type === 'vowel_coda_series' && parts[2]) {
      vowelCoda.add(`${parts[1]}|${parts[2]}`);
      vowelCodaKeys.add(syllable);
    }
  }
  const override = items['영']?.initial_vowel_override || {};
  const yeongInitials = new Set(override.initials || []);
  const yeongVowel = override.surface_vowel || 'ㅓ';

  // 모음 + 받침 자리에 억·언·얼 계열 약자가 들어가는지 본다.
  function usesVowelCoda(cho, jung, jong) {
    if (!jong) return false;
    if (yeongInitials.has(cho) && jong === 'ㅇ') {
      if (jung === yeongVowel) return true;
      if (jung === 'ㅕ') return false;
    }
    return vowelCoda.has(`${jung}|${jong}`);
  }

  return {
    syllables,
    gaOnsets,
    vowelCoda,
    vowelCodaKeys,
    usesVowelCoda,
    applies(cho, jung, jong) {
      const syllable = composeSyllable(cho, jung, jong);
      if (syllable && syllables.has(syllable)) return true;
      if (jung === 'ㅏ' && gaOnsets.has(TENSE[cho] || cho)) return true;
      return usesVowelCoda(cho, jung, jong);
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
  const cards = [];
  const seen = new Set();
  const push = (cho, jung, jong) => {
    const syllable = composeSyllable(cho, jung, jong);
    if (!syllable || seen.has(syllable) || abbreviation.applies(cho, jung, jong)) return;
    const steps = spellSteps(cho, jung, jong, maps);
    if (!steps) return;
    seen.add(syllable);
    const card = makeCard({ letter: syllable, steps, kind: 'syllable' });
    card.line = `풀어 적은 ${syllable}(${steps.map((step) => step.label).join('+')})의 점형은 ${card.dotText}입니다.`;
    cards.push(card);
  };
  // 낱말에 자주 나오는 음절을 골라 둔 목록. 약자가 걸리는 음절은 건너뛴다.
  for (const syllable of slice.syllables || []) {
    const parts = decomposeSyllable(syllable);
    if (parts) push(parts[0], parts[1], parts[2]);
  }
  const ranges = slice.ranges || {};
  for (const cho of ranges.cho || []) {
    for (const jung of ranges.jung || []) {
      for (const jong of ranges.jong || ['']) push(cho, jung, jong);
    }
  }
  return cards;
}

// ---------------------------------------------------------------------------
// 약자가 들어간 음절: 된소리표, 첫소리, 약자, 뒤 받침을 차례로 잇는다.
//   까 = 된소리표 + 가 약자, 값 = 가 약자 + 받침 ㅄ
//   걱 = ㄱ + 억 약자, 성 = ㅅ + 영 약자
// ---------------------------------------------------------------------------

function abbrSyllableSteps(syllable, items, maps) {
  const parts = decomposeSyllable(syllable);
  if (!parts) return null;
  const [cho, jung, jong] = parts;
  const base = TENSE[cho] || cho;
  const tenseItem = TENSE[cho] ? maps.cho?.[cho] : null;
  const tense = tenseItem ? [makeStep('된소리표', [cellsOf(tenseItem.dots)[0] || [6]])] : [];
  const abbr = (key) => makeStep(`${key} 약자`, items[key].dots, items[key].unicode);
  const jongStep = (key) => {
    const item = maps.jong?.[key];
    return item ? makeStep(`받침 ${key}`, item.dots, item.unicode) : null;
  };
  const choSteps = () => {
    if (base === 'ㅇ') return [];
    const item = maps.cho?.[base];
    return item ? [...tense, makeStep(base, item.dots, item.unicode)] : null;
  };

  if (items[syllable]?.type === 'complete_syllable') return { kind: 'eok', steps: [abbr(syllable)] };
  for (const [key, item] of Object.entries(items)) {
    if (item.type === 'complete_syllable' && (item.tensed_same_abbreviation || []).includes(syllable)) {
      return { kind: 'eok', steps: [...tense, abbr(key)] };
    }
  }

  const ga = composeSyllable(base, 'ㅏ', '');
  if (jung === 'ㅏ' && items[ga]?.type === 'ga_series') {
    const tail = jong ? jongStep(jong) : null;
    if (jong && !tail) return null;
    return { kind: 'ga', steps: [...tense, abbr(ga), ...(tail ? [tail] : [])] };
  }

  if (!jong) return null;
  const override = items['영']?.initial_vowel_override;
  if (override && (override.initials || []).includes(cho) && jong === 'ㅇ') {
    if (jung === (override.surface_vowel || 'ㅓ') && items['영']) {
      const head = choSteps();
      return head ? { kind: 'eok', steps: [...head, abbr('영')] } : null;
    }
    if (jung === 'ㅕ') return null;
  }
  const whole = composeSyllable('ㅇ', jung, jong);
  if (items[whole]?.type !== 'vowel_coda_series') return null;
  const head = choSteps();
  return head ? { kind: 'eok', steps: [...head, abbr(whole)] } : null;
}

function abbrCards(slice, data) {
  const ko = resolveBundle(data, slice.bundle);
  const items = ko?.abbreviation_syllable?.items;
  const maps = jamoMaps(ko);
  if (!items || !maps.cho || !maps.jong) return [];
  const cards = [];
  const seen = new Set();
  for (const syllable of slice.syllables || []) {
    if (seen.has(syllable)) continue;
    const made = abbrSyllableSteps(syllable, items, maps);
    if (!made) continue;
    seen.add(syllable);
    const card = makeCard({ letter: syllable, steps: made.steps, kind: made.kind });
    card.line = `${syllable}(${made.steps.map((step) => step.label).join(' + ')})의 점형은 ${card.dotText}입니다.`;
    cards.push(card);
  }
  return cards;
}

// ---------------------------------------------------------------------------
// 예외: 약자와 풀어 쓴 형태를 같이 보여 준다.
// 같은 틀을 숫자·음절만 바꿔 쌓지 않고, 규칙이 걸리는 자리를 앞·가운데·뒤로 옮긴다.
// ---------------------------------------------------------------------------

function exceptionCards(slice, data) {
  const ko = resolveBundle(data, slice.bundle);
  const items = ko?.abbreviation_syllable?.items;
  if (!items) return [];
  const maps = jamoMaps(ko);
  const numbers = resolveBundle(data, 'numbers.json');
  const prefix = numbers?.numeric_indicators?.num_prefix;
  const digitItem = (digit) => numbers?.digits?.[digit];
  const cards = [];
  const seen = new Set();

  const numberSteps = (digit) => {
    const item = digitItem(String(digit));
    if (!prefix || !item) return null;
    return [makeStep(prefix.name || '수표', prefix.dots, prefix.unicode), makeStep(String(digit), item.dots, item.unicode)];
  };

  const push = (letter, steps, wrongSteps, note, line, family) => {
    if (!letter || seen.has(letter) || !steps?.length || !wrongSteps?.length) return;
    seen.add(letter);
    const card = makeCard({ letter, steps, kind: 'exception' });
    const wrong = wrongSteps.map(stepPattern).join('');
    card.contrast = wrong;
    card.family = family;
    card.explain = `${card.explain}. ${note}`;
    card.line = line(card.pattern, wrong);
    cards.push(card);
  };

  const abbrSteps = (syllable) => {
    const item = items[syllable];
    if (!item) return null;
    return [makeStep(`${syllable} 약자`, item.dots, item.unicode)];
  };

  const spelledSteps = (syllable) => {
    const parts = decomposeSyllable(syllable);
    if (!parts) return null;
    return spellSteps(parts[0], parts[1], parts[2], maps);
  };

  const rule = ko?.special_rules?.number_prefix_rule;
  const affected = new Set(rule?.affected_initials || []);
  const affectedAbbr = new Set(rule?.affected_abbreviations || []);
  const pads = [];
  const affectedSyllables = [];
  for (const [syllable, item] of Object.entries(items)) {
    if (item.exception_rules || item.type !== 'ga_series') continue;
    const parts = decomposeSyllable(syllable);
    if (!parts) continue;
    if (affected.has(parts[0])) affectedSyllables.push(syllable);
    else pads.push(syllable);
  }
  for (const syllable of affectedAbbr) {
    if (items[syllable]) affectedSyllables.push(syllable);
  }

  const padRun = (count, start) => {
    if (count <= 0) return [];
    if (!pads.length) return null;
    const out = [];
    for (let i = 0; i < count; i += 1) {
      const syllable = pads[(start + i) % pads.length];
      const steps = abbrSteps(syllable);
      if (!steps) return null;
      out.push({ syllable, steps });
    }
    return out;
  };

  const space = makeStep('띄어쓰기', [[]], ' ');
  const followers = (slice.followers || []).filter((follower) => {
    const parts = decomposeSyllable(follower);
    return parts && parts[0] === 'ㅇ' && spelledSteps(follower);
  });
  const digits = (slice.digits || []).map(String).filter((digit) => numberSteps(digit));
  const digitBank = [];
  for (const digit of digits.concat(slice.ruleDigit ? [String(slice.ruleDigit)] : [], Object.keys(numbers?.digits || {}))) {
    if (digit === '0' || digitBank.includes(digit) || !numberSteps(digit)) continue;
    digitBank.push(digit);
  }

  // 모음 앞 '사': 첫 문제만 맨 앞에서 시작하고, 나머지는 앞뒤에 아는 음절을 붙인다.
  const vowelFrames = [
    { before: 0, after: 0 },
    { before: 1, after: 0 },
    { before: 1, after: 1 },
    { before: 2, after: 1 }
  ];
  // 숫자 뒤 '사': 숫자 점형이 맨 앞에 오는 것은 하나뿐이고, 마지막은 모음 규칙도 같이 본다.
  const numberFrames = [
    { before: 0, after: 0, withFollower: false },
    { before: 1, after: 0, withFollower: false },
    { before: 1, after: 1, withFollower: false },
    { before: 1, after: 0, withFollower: true }
  ];
  // 숫자 뒤 혼동 초성: 띄어쓰기 자리를 번갈아 옮긴다.
  const spaceFrames = [
    { before: 0, after: 0 },
    { before: 1, after: 1 },
    { before: 2, after: 0 },
    { before: 1, after: 0 },
    { before: 2, after: 1 },
    { before: 1, after: 1 },
    { before: 2, after: 0 }
  ];

  const texts = (run) => (run || []).map((item) => item.syllable).join('');
  const stepsOf = (run) => (run || []).map((item) => item.steps);

  for (const [syllable] of Object.entries(items)) {
    if (!items[syllable].exception_rules) continue;
    const spelled = spelledSteps(syllable);
    const abbr = abbrSteps(syllable);
    if (!spelled || !abbr) continue;

    followers.forEach((follower, index) => {
      const frame = vowelFrames[index % vowelFrames.length];
      const fsteps = spelledSteps(follower);
      const before = padRun(frame.before, index);
      const after = padRun(frame.after, index + frame.before);
      if (!fsteps || !before || !after) return;
      const letter = `${texts(before)}${syllable}${follower}${texts(after)}`;
      push(
        letter,
        [...stepsOf(before).flat(), ...spelled, ...fsteps, ...stepsOf(after).flat()],
        [...stepsOf(before).flat(), ...abbr, ...fsteps, ...stepsOf(after).flat()],
        `${syllable} 뒤에 모음이 바로 이어지므로 약자를 쓰지 않고 풀어 적습니다.`,
        (right, wrong) => `${letter}: 약자 ${wrong}(×), 풀어 쓴 ${right}(○)`,
        'vowel'
      );
    });

    digits.forEach((digit, index) => {
      const frame = numberFrames[index % numberFrames.length];
      const num = numberSteps(digit);
      const follower = frame.withFollower ? followers[index % followers.length] : '';
      const fsteps = follower ? spelledSteps(follower) : null;
      const before = padRun(frame.before, index + 1);
      const after = padRun(frame.after, index + 1 + frame.before);
      if (!num || !before || !after || (follower && !fsteps)) return;
      const letter = `${texts(before)}${digit}${syllable}${follower}${texts(after)}`;
      const note = follower
        ? `숫자 뒤의 ${syllable}와, ${syllable} 뒤에 바로 이어지는 모음은 약자를 쓰지 않고 풀어 적습니다.`
        : `숫자 뒤의 ${syllable}는 약자를 쓰지 않고 풀어 적습니다.`;
      push(
        letter,
        [...stepsOf(before).flat(), ...num, ...spelled, ...(fsteps || []), ...stepsOf(after).flat()],
        [...stepsOf(before).flat(), ...num, ...abbr, ...(fsteps || []), ...stepsOf(after).flat()],
        note,
        (right, wrong) => `${letter}: 약자 ${wrong}(×), 풀어 쓴 ${right}(○)`,
        'after-number'
      );
    });
  }

  if (rule) {
    affectedSyllables.forEach((syllable, index) => {
      const frame = spaceFrames[index % spaceFrames.length];
      const digit = digitBank[index % digitBank.length];
      const num = digit ? numberSteps(digit) : null;
      const abbr = abbrSteps(syllable);
      const parts = decomposeSyllable(syllable);
      const before = padRun(frame.before, index);
      const after = padRun(frame.after, index + frame.before);
      if (!num || !abbr || !parts || !before || !after) return;
      const letter = `${texts(before)}${digit} ${syllable}${texts(after)}`;
      const collision = affectedAbbr.has(syllable) ? `약자 ${syllable}` : parts[0];
      push(
        letter,
        [...stepsOf(before).flat(), ...num, space, ...abbr, ...stepsOf(after).flat()],
        [...stepsOf(before).flat(), ...num, ...abbr, ...stepsOf(after).flat()],
        `숫자 뒤에 ${collision}이 오면 숫자로 읽히지 않도록 띄어쓰기로 숫자 입력을 끝냅니다.`,
        (right, wrong) => `${letter}: 붙여 적으면 ${wrong}(×), 띄어 쓴 ${right}(○)`,
        'space'
      );
    });
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
