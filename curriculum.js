/**
 * 단원표. 화면은 쓰지 않고, 단원 목록과 학습 카드만 돌려준다.
 * 점의 자리만 정적 카드이고 나머지는 JSON 구간을 자른다.
 */

const CHO = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
const JUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'];
const JONG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];

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

function cardsFromSlice(slice, data) {
  if (slice.ranges) return syllableCards(slice, data);
  const node = nodeAt(data, slice.bundle, slice.path || []);
  if (slice.role === 'exception') return exceptionCards(node);
  if (slice.role === 'rule') {
    const card = ruleCard(node, nodeAt(data, slice.patternFrom?.bundle, slice.patternFrom?.path || []));
    return card ? [card] : [];
  }
  return glyphEntries(node)
    .filter(([, item]) => acceptItem(item, slice.filter))
    .map(([key, item]) => glyphCard(key, item, slice.role));
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

function cellsOf(dots) {
  if (!Array.isArray(dots) || dots.length === 0) return [];
  const cells = typeof dots[0] === 'number' ? [dots] : dots;
  return cells
    .filter((cell) => Array.isArray(cell) && cell.length > 0)
    .map((cell) => cell.slice());
}

function dotTextFromCells(cells) {
  if (!cells.length) return '생략';
  return cells.map((cell) => `${cell.join('·')}점`).join(' + ');
}

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

function glyphCard(key, item, role) {
  const dots = cellsOf(item.dots);
  const pattern = item.unicode || '';
  const letter = letterOf(key, item, role);
  const dotText = dotTextFromCells(dots);
  return {
    letter,
    pattern,
    dots,
    dotText,
    line: lineFor(role, letter, dotText, item, key)
  };
}

function staticCard(card) {
  const dots = cellsOf(card.dots);
  return {
    letter: card.letter,
    pattern: card.pattern || '',
    dots,
    dotText: dotTextFromCells(dots),
    line: card.line || ''
  };
}

function exceptionCards(items) {
  if (!items || typeof items !== 'object') return [];
  const cards = [];
  for (const [key, item] of Object.entries(items)) {
    if (!item || !item.exception_rules) continue;
    const dots = cellsOf(item.expanded_dots || item.dots);
    const pattern = item.expanded_unicode || item.unicode || '';
    const dotText = dotTextFromCells(dots);
    for (const text of Object.values(item.exception_rules)) {
      cards.push({
        letter: item.syllable || key,
        pattern,
        dots,
        dotText,
        line: String(text)
      });
    }
  }
  return cards;
}

function ruleCard(rule, glyph) {
  if (!rule || typeof rule !== 'object') return null;
  const dots = glyph ? cellsOf(glyph.dots) : [];
  const pattern = glyph?.unicode || '';
  return {
    letter: '숫자 뒤',
    pattern,
    dots,
    dotText: dotTextFromCells(dots),
    line: rule.note || ''
  };
}

function composeSyllable(cho, jung, jong) {
  const ci = CHO.indexOf(cho);
  const ji = JUNG.indexOf(jung);
  const ki = JONG.indexOf(jong || '');
  if (ci < 0 || ji < 0 || ki < 0) return '';
  return String.fromCharCode(0xAC00 + (ci * 21 + ji) * 28 + ki);
}

function syllableCards(slice, data) {
  const ko = resolveBundle(data, slice.bundle);
  const choMap = ko?.chosung?.items;
  const jungMap = ko?.jungsung?.items;
  const jongMap = ko?.jongsung?.items;
  if (!choMap || !jungMap || !jongMap) return [];
  const abbreviations = new Set(Object.keys(ko.abbreviation_syllable?.items || {}));
  const ranges = slice.ranges || {};
  const cards = [];
  for (const cho of ranges.cho || []) {
    for (const jung of ranges.jung || []) {
      for (const jong of ranges.jong || ['']) {
        const syllable = composeSyllable(cho, jung, jong);
        if (!syllable || abbreviations.has(syllable)) continue;
        const card = spellSyllable(syllable, cho, jung, jong, choMap, jungMap, jongMap);
        if (card) cards.push(card);
      }
    }
  }
  return cards;
}

function spellSyllable(syllable, cho, jung, jong, choMap, jungMap, jongMap) {
  const choItem = choMap[cho];
  const jungItem = jungMap[jung];
  const jongItem = jong ? jongMap[jong] : null;
  if (!choItem || !jungItem || (jong && !jongItem)) return null;
  const cells = [];
  const patterns = [];
  const parts = [];
  if (choItem.isOmitted || cellsOf(choItem.dots).length === 0) {
    parts.push(`${cho}(생략)`);
  } else {
    cells.push(...cellsOf(choItem.dots));
    if (choItem.unicode) patterns.push(choItem.unicode);
    parts.push(cho);
  }
  cells.push(...cellsOf(jungItem.dots));
  if (jungItem.unicode) patterns.push(jungItem.unicode);
  parts.push(jung);
  if (jongItem) {
    cells.push(...cellsOf(jongItem.dots));
    if (jongItem.unicode) patterns.push(jongItem.unicode);
    parts.push(jong);
  }
  const dotText = dotTextFromCells(cells);
  return {
    letter: syllable,
    pattern: patterns.join(''),
    dots: cells,
    dotText,
    line: `풀어 적은 ${syllable}(${parts.join('+')})의 점형은 ${dotText}입니다.`
  };
}

async function demoIfMain() {
  if (typeof process === 'undefined' || !process.argv?.[1]) return;
  const { pathToFileURL } = await import('node:url');
  const href = pathToFileURL(process.argv[1]).href;
  if (import.meta.url.toLowerCase() !== href.toLowerCase()) return;

  const ko = await readJson('ko.json');
  console.log('한글 단원');
  for (const unit of unitsFor('ko')) {
    console.log(`${unit.order}. ${unit.title}`);
  }
  console.log('');
  console.log('초성 카드');
  for (const card of cardsFor(unitById('ko-initial'), { 'ko.json': ko })) {
    console.log(`${card.letter} → ${card.pattern || '(없음)'}, ${card.dotText}`);
  }
}

await demoIfMain();
