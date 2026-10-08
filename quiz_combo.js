/**
 * 사전 조합으로 퀴즈를 만든다.
 * morpheme, blank, builders는 형태소 하나만을 문제로 낸다.
 * select는 형태소를 자유롭게 결합한 심화 문제만 낸다.
 * unitId가 있으면 그 단원 source의 카드만 낸다. 읽기는 morpheme·select·builders, 쓰기는 blank.
 * 단원 문제는 그 단원과 앞 단원의 재료만 쓰고, 앞 단원을 통과하지 못했으면 내지 않는다.
 * 1단원 다음부터는 그 단원 주제를 문제의 앞, 중간, 뒤에 번갈아 넣는다.
 * 짧은 문장은 순차에서 통과한 앞 단원 재료만 잇는다. 자유 학습에서는 통과하지 않아도 앞 단원 재료를 전부 잇는다.
 * 통과한 단원에서 틀린 항목은 다음 단원 10문제 가운데 둘이나 셋으로 다시 낸다.
 * 해설은 조립 순서다. 예) ㄱ 4점 ⠈ + ㅏ 1·2·6점 ⠣
 */
import {
  cardsFor,
  unitById,
  unitsFor,
  materialsFor,
  isComposeUnit,
  assemblyText,
  makeStep,
  stepsPattern,
  abbreviationIndex
} from './curriculum.js';
import { STAGE_SIZE, wrongItemKeys, isUnitOpen, isUnitPassed, loadStudyMode } from './shell.js';

const SPACE_STEP = makeStep('띄어쓰기', [], ' ', '단어 사이');
const NUMERIC_SPACE = '⠐';
const NUMERIC_SPACE_STEP = makeStep('숫자 빈칸', [[5]], NUMERIC_SPACE);
const LANG_CODE = { ko: 'KO', en: 'EN' };

/** 앞 단원을 모두 통과해야 열리는 단원인지 본다. 게임 화면이 들어가기 전에 쓴다. */
export function canOpenUnit(unitId, lang) {
  const unit = unitById(unitId);
  if (!unit) return false;
  const code = LANG_CODE[unit.lang];
  if (lang && String(lang).toUpperCase() !== code) return false;
  const ids = unitsFor(unit.lang).map((item) => item.id);
  return isUnitOpen(code, unit.id, ids);
}

const CHOSUNG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
const JUNGSUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'];
const JONGSUNG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
const TENSER = { 'ㄲ': 'ㄱ', 'ㄸ': 'ㄷ', 'ㅃ': 'ㅂ', 'ㅆ': 'ㅅ', 'ㅉ': 'ㅈ' };

const EN_PUNCT = [
  { ch: '.', name: 'period', unicode: '⠲' },
  { ch: '?', name: 'question mark', unicode: '⠦' },
  { ch: '!', name: 'exclamation', unicode: '⠖' },
  { ch: ',', name: 'comma', unicode: '⠂' },
  { ch: ';', name: 'semicolon', unicode: '⠆' },
  { ch: ':', name: 'colon', unicode: '⠒' }
];

const SUFFIX_BRAILLE = {
  s: '⠎',
  "'s": '⠄⠎',
  ed: '⠫',
  d: '⠙',
  ing: '⠬',
  er: '⠻',
  est: '⠑⠌',
  ly: '⠇⠽',
  ness: '⠰⠎',
  ful: '⠰⠇',
  ment: '⠰⠞',
  ity: '⠰⠽',
  ally: '⠁⠇⠇⠽',
  tion: '⠰⠝',
  less: '⠨⠎',
  ence: '⠰⠑',
  ance: '⠨⠑'
};

const SILENT_E_SUFFIXES = ['ing', 'ed', 'er', 'est', 'able', 'ist', 'ize'];

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function compose(cho, jung, jong = '') {
  const ci = CHOSUNG.indexOf(cho);
  const ji = JUNGSUNG.indexOf(jung);
  const ki = jong ? JONGSUNG.indexOf(jong) : 0;
  if (ci < 0 || ji < 0 || ki < 0) return '';
  return String.fromCharCode(0xAC00 + (ci * 21 + ji) * 28 + ki);
}

function decompose(ch) {
  const code = ch.charCodeAt(0) - 0xAC00;
  if (code < 0 || code > 11171) return null;
  return [CHOSUNG[Math.floor(code / 588)], JUNGSUNG[Math.floor((code % 588) / 28)], JONGSUNG[code % 28]];
}

function unicodeToDots(ch) {
  const code = ch.codePointAt(0);
  if (code < 0x2800 || code > 0x28FF) return null;
  const pattern = code - 0x2800;
  const dots = [];
  if (pattern & 0x01) dots.push(1);
  if (pattern & 0x02) dots.push(2);
  if (pattern & 0x04) dots.push(3);
  if (pattern & 0x08) dots.push(4);
  if (pattern & 0x10) dots.push(5);
  if (pattern & 0x20) dots.push(6);
  return dots;
}

function dotsToUnicode(dots) {
  const bit = { 1: 0x01, 2: 0x02, 3: 0x04, 4: 0x08, 5: 0x10, 6: 0x20 };
  let pattern = 0;
  dots.forEach(d => { pattern |= bit[d] || 0; });
  return String.fromCharCode(0x2800 + pattern);
}

function partsToSteps(parts) {
  const steps = [];
  (parts || []).forEach((part) => {
    let cells = part.braille || '';
    if (cells.startsWith(' ')) {
      steps.push(makeStep('띄어쓰기', [], ' ', '수표 종료'));
      cells = cells.slice(1);
    }
    if (!cells) return;
    if (cells === NUMERIC_SPACE) {
      steps.push(NUMERIC_SPACE_STEP);
      return;
    }
    const dotCells = Array.from(cells).map((ch) => unicodeToDots(ch) || []);
    steps.push(makeStep(part.label || part.text, dotCells, cells));
  });
  return steps;
}

function mutateBraille(braille) {
  const chars = Array.from(braille);
  if (!chars.length) return '';
  const idx = Math.floor(Math.random() * chars.length);
  const dots = unicodeToDots(chars[idx]);
  if (!dots || !dots.length) return '';
  if (Math.random() < 0.5 && dots.length > 1) {
    dots.splice(Math.floor(Math.random() * dots.length), 1);
  } else {
    const avail = [1, 2, 3, 4, 5, 6].filter(d => !dots.includes(d));
    if (!avail.length) return '';
    dots.push(pick(avail));
  }
  chars[idx] = dotsToUnicode(dots);
  return chars.join('');
}

function mirrorBraille(braille, map) {
  return Array.from(braille).map(ch => {
    const dots = unicodeToDots(ch);
    if (!dots) return ch;
    return dotsToUnicode(dots.map(d => map[d]));
  }).join('');
}

function loadJson(name) {
  return fetch(new URL(name, import.meta.url)).then(res => {
    if (!res.ok) throw new Error(name);
    return res.json();
  });
}

function buildKorean(data) {
  const ko = data.ko || {};
  const marks = data.marks || {};
  const numbers = data.numbers || {};
  const rules = data.numberRules || {};

  const wordAbbr = {};
  Object.entries(ko.abbreviation_word?.items || {}).forEach(([word, item]) => {
    if (item.unicode) wordAbbr[word] = item.unicode;
  });
  const wordAbbrSorted = Object.entries(wordAbbr).sort((a, b) => b[0].length - a[0].length);

  const gaByOnset = {};
  const vc = {};
  const complete = {};
  let saExpanded = '⠠⠣';
  Object.entries(ko.abbreviation_syllable?.items || {}).forEach(([syllable, item]) => {
    if (item.expanded_unicode) saExpanded = item.expanded_unicode;
    const parts = decompose(syllable);
    if (!parts || !item.unicode) return;
    if (item.type === 'ga_series' && parts[1] === 'ㅏ' && !parts[2]) gaByOnset[parts[0]] = item.unicode;
    else if (item.type === 'vowel_coda_series' && parts[2]) vc[`${parts[1]}|${parts[2]}`] = item.unicode;
    else if (item.type === 'complete_syllable') complete[syllable] = item.unicode;
  });

  const choMap = {};
  const jungMap = {};
  const jongMap = {};
  Object.entries(ko.chosung?.items || {}).forEach(([k, v]) => { choMap[k] = v.unicode || ''; });
  Object.entries(ko.jungsung?.items || {}).forEach(([k, v]) => { jungMap[k] = v.unicode || ''; });
  Object.entries(ko.jongsung?.items || {}).forEach(([k, v]) => { jongMap[k] = v.unicode || ''; });

  const numPrefix = numbers.numeric_indicators?.num_prefix?.unicode || '⠼';
  const digits = {};
  Object.entries(numbers.digits || {}).forEach(([k, v]) => { digits[k] = v.unicode; });
  const numberRule = ko.special_rules?.number_prefix_rule || {};
  const affected = numberRule.affected_initials || ['ㄴ', 'ㄷ', 'ㅁ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
  const affectedAbbr = new Set(numberRule.affected_abbreviations || []);
  const yeong = ko.abbreviation_syllable?.items?.['영'] || {};
  const yeongOverride = new Set(yeong.initial_vowel_override?.initials || []);
  const yeongVowel = yeong.initial_vowel_override?.surface_vowel || 'ㅓ';
  const yeongCell = yeong.unicode || '';
  const geotTensed = new Set(ko.abbreviation_syllable?.items?.['것']?.tensed_same_abbreviation || []);
  // 제17항 [붙임]·[다만]: 첫소리와 점형이 같은 약자는 모음 앞에서 ㅏ를 적는다. '팠'도 ㅏ를 적는다.
  const keepA = ko.abbreviation_syllable?.rule?.keep_a || {};
  const keepAOnsets = new Set();
  (keepA.vowel_connection?.syllables || []).forEach((syllable) => {
    const parts = decompose(syllable);
    if (parts) keepAOnsets.add(parts[0]);
  });
  if (keepA.vowel_connection?.include_tensed) {
    Object.entries(TENSER).forEach(([tensed, base]) => { if (keepAOnsets.has(base)) keepAOnsets.add(tensed); });
  }
  const keepASpell = new Set(Object.keys(keepA.spell_out || {}));

  function keepsA(ch, nextCh) {
    const parts = decompose(ch);
    if (!parts || parts[1] !== 'ㅏ') return false;
    if (keepASpell.has(ch)) return true;
    return !parts[2] && keepAOnsets.has(parts[0]) && !!nextCh && decompose(nextCh)?.[0] === 'ㅇ';
  }
  const exempt = (rules.collision_resolutions?.trailing_letters?.exempt_units || ['년', '월', '일', '시', '분', '초', '개', '명', '원'])
    .slice()
    .sort((a, b) => b.length - a.length);
  const unitBoundary = rules.collision_resolutions?.trailing_letters?.unit_boundary || {};
  const unitBoundaryOn = !!unitBoundary.enabled;
  const josa = (unitBoundary.josa || []).slice().sort((a, b) => b.length - a.length);
  const romanUnits = Object.entries(
    rules.collision_resolutions?.trailing_letters?.roman_unit_symbols || {}
  ).sort((a, b) => b[0].length - a[0].length);

  function unitBoundaryOk(after) {
    if (!unitBoundaryOn) return true;
    if (!after) return true;
    const head = after[0];
    if (head < '가' || head > '힣') return true;
    return josa.some(item => after.startsWith(item));
  }

  function isExemptUnit(rest) {
    if (!rest) return false;
    return exempt.some(unit => rest.startsWith(unit) && unitBoundaryOk(rest.slice(unit.length)));
  }

  // 검사기와 같이, 숫자 바로 뒤의 혼동 초성·약자는 단위가 아니면 띄어 적는다.
  function separateCollisions(text) {
    let out = '';
    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      const prev = out[out.length - 1] || '';
      if (prev >= '0' && prev <= '9' && ch >= '가' && ch <= '힣') {
        const rest = text.slice(i);
        const parts = decompose(ch);
        const cho = parts ? parts[0] : '';
        if (!isExemptUnit(rest) && (affected.includes(cho) || affectedAbbr.has(ch))) out += ' ';
      }
      out += ch;
    }
    return out;
  }

  const punct = [];
  Object.values(marks).forEach(block => {
    Object.entries(block?.items || {}).forEach(([ch, item]) => {
      if (item.unicode) punct.push({ ch, name: item.word || ch, unicode: item.unicode });
    });
  });
  punct.sort((a, b) => b.ch.length - a.ch.length);

  const connectors = {};
  Object.values(rules.symbols || {}).forEach((item) => {
    if (!item.char || !item.unicode || item.char === ' ') return;
    connectors[item.char] = {
      unicode: item.unicode,
      persists: item.persists_numeric_mode !== false
    };
  });

  function translateSyllable(ch, nextCh, afterNumber, rest) {
    const parts = decompose(ch);
    if (!parts) return null;
    const [cho, jung, jong] = parts;
    const labels = [];
    const exemptHit = isExemptUnit(rest);

    if (ch === '사' && (afterNumber || (nextCh && decompose(nextCh)?.[0] === 'ㅇ'))) {
      let braille = saExpanded + (jong ? (jongMap[jong] || '') : '');
      if (afterNumber && affected.includes(cho) && !exemptHit) braille = ` ${braille}`;
      return {
        braille,
        label: afterNumber ? "숫자 뒤 '사' 풀어쓰기" : "모음 앞 '사' 풀어쓰기"
      };
    }

    let head = '';
    if (afterNumber && (affected.includes(cho) || affectedAbbr.has(ch)) && !exemptHit) {
      head = ' ';
      labels.push(affectedAbbr.has(ch)
        ? `수표 뒤 약자 '${ch}' 앞 띄어쓰기로 숫자 종료`
        : `수표 뒤 '${cho}' 앞 띄어쓰기로 숫자 종료`);
    }

    if (keepsA(ch, nextCh)) {
      const jongB = jong ? (jongMap[jong] || '') : '';
      return {
        braille: head + (choMap[cho] || '') + (jungMap[jung] || '') + jongB,
        label: keepASpell.has(ch) ? `'${ch}' ㅏ 적기` : `모음 앞 '${ch}' ㅏ 적기`,
        keepA: true
      };
    }

    if (complete[ch]) {
      return { braille: head + complete[ch], label: `음절 약자 '${ch}'` };
    }

    let tenser = '';
    let baseCho = cho;
    if (TENSER[cho]) {
      tenser = '⠠';
      baseCho = TENSER[cho];
      labels.push(`된소리 ${cho}`);
    }

    if (geotTensed.has(ch) && complete['것']) {
      labels.push("된소리 + '것' 약자");
      return { braille: head + tenser + complete['것'], label: labels.join(', ') };
    }

    if (yeongCell && yeongOverride.has(cho) && jong === 'ㅇ' && jung === yeongVowel) {
      const choB = baseCho === 'ㅇ' ? '' : (choMap[baseCho] || '');
      labels.push(`'${cho}' 뒤 '영' 약자는 '${ch}'`);
      return { braille: head + tenser + choB + yeongCell, label: labels.join(', ') };
    }

    if (jung === 'ㅏ' && gaByOnset[baseCho]) {
      const tail = jong ? (jongMap[jong] || '') : '';
      labels.push(`'${baseCho}ㅏ' 약자` + (jong ? ` + 받침 ${jong}` : ''));
      return { braille: head + tenser + gaByOnset[baseCho] + tail, label: labels.join(', ') };
    }

    const spellYeong = yeongOverride.has(cho) && jung === 'ㅕ' && jong === 'ㅇ';
    if (!spellYeong && jong && vc[`${jung}|${jong}`]) {
      if (baseCho === 'ㅇ') {
        labels.push('모음·받침 약자');
        return { braille: head + tenser + vc[`${jung}|${jong}`], label: labels.join(', ') };
      }
      labels.push(`초성 ${baseCho} + 모음·받침 약자`);
      return { braille: head + tenser + (choMap[baseCho] || '') + vc[`${jung}|${jong}`], label: labels.join(', ') };
    }

    const choB = baseCho === 'ㅇ' ? '' : (choMap[baseCho] || '');
    const jungB = jungMap[jung] || '';
    const jongB = jong ? (jongMap[jong] || '') : '';
    if (!choB && baseCho !== 'ㅇ') return null;
    if (!jungB) return null;
    if (jong && !jongB) return null;
    if (baseCho === 'ㅇ') labels.push('초성 ㅇ 생략');
    else labels.push(`초성 ${baseCho}`);
    labels.push(`모음 ${jung}`);
    if (jong) labels.push(`받침 ${jong}`);
    return { braille: head + tenser + choB + jungB + jongB, label: labels.join(' + ') };
  }

  function hangulChar(ch) {
    return !!ch && ch >= '가' && ch <= '힣';
  }

  function translate(text) {
    let braille = '';
    const parts = [];
    let inNumber = false;
    let i = 0;
    while (i < text.length) {
      const ch = text[i];
      if (ch === ' ' || ch === '\n' || ch === '\r') {
        const gap = ch === '\n' || ch === '\r' ? ch : ' ';
        braille += gap;
        inNumber = false;
        parts.push({ text: gap, braille: gap, label: '띄어쓰기' });
        i += 1;
        continue;
      }

      const longMark = punct.find((item) => item.ch.length > 1 && text.startsWith(item.ch, i));
      if (longMark) {
        braille += longMark.unicode;
        inNumber = false;
        parts.push({ text: longMark.ch, braille: longMark.unicode, label: longMark.name });
        i += longMark.ch.length;
        continue;
      }

      let matchedWord = null;
      for (const [word, cells] of wordAbbrSorted) {
        if (!text.startsWith(word, i)) continue;
        const prev = i ? text[i - 1] : '';
        const next = text[i + word.length] || '';
        if (hangulChar(prev) || hangulChar(next)) break;
        matchedWord = { word, cells };
        break;
      }
      if (matchedWord) {
        braille += matchedWord.cells;
        inNumber = false;
        parts.push({ text: matchedWord.word, braille: matchedWord.cells, label: `단어 약어 '${matchedWord.word}'` });
        i += matchedWord.word.length;
        continue;
      }

      if (ch >= '0' && ch <= '9') {
        let token = '';
        let tokenBraille = '';
        while (i < text.length && text[i] >= '0' && text[i] <= '9') {
          const digit = text[i];
          if (!digits[digit]) return null;
          tokenBraille += (inNumber ? '' : numPrefix) + digits[digit];
          inNumber = true;
          token += digit;
          i += 1;
        }
        braille += tokenBraille;
        parts.push({ text: token, braille: tokenBraille, label: `수표 + ${token}` });
        continue;
      }

      if (inNumber && connectors[ch] && i + 1 < text.length && text[i + 1] >= '0' && text[i + 1] <= '9') {
        const link = connectors[ch];
        braille += link.unicode;
        if (!link.persists) inNumber = false;
        parts.push({ text: ch, braille: link.unicode, label: '수표 연결' });
        i += 1;
        continue;
      }

      if (inNumber) {
        const unit = romanUnits.find(([name]) => text.startsWith(name, i));
        if (unit) {
          braille += unit[1];
          inNumber = false;
          parts.push({ text: unit[0], braille: unit[1], label: `단위 ${unit[0]}` });
          i += unit[0].length;
          continue;
        }
      }

      const afterNumber = inNumber;
      inNumber = false;
      if (ch >= '가' && ch <= '힣') {
        const piece = translateSyllable(ch, text[i + 1] || '', afterNumber, text.slice(i));
        if (!piece || !piece.braille) return null;
        braille += piece.braille;
        parts.push(piece.keepA
          ? { text: ch, braille: piece.braille, label: piece.label, keepA: true }
          : { text: ch, braille: piece.braille, label: piece.label });
        i += 1;
        continue;
      }

      const mark = punct.find((item) => item.ch === ch);
      if (mark) {
        braille += mark.unicode;
        parts.push({ text: ch, braille: mark.unicode, label: mark.name });
        i += 1;
        continue;
      }
      return null;
    }

    if (!braille || !parts.length) return null;
    const hasDigit = parts.some(part => /^\d+$/.test(part.text));
    const hasHangul = parts.some(part => /[가-힣]/.test(part.text));
    let rule = '음절';
    if (hasDigit && hasHangul) rule = '수표 결합';
    else if (hasDigit) rule = '수표';
    else if (parts.length > 1) rule = '형태소 결합';
    return { braille, parts, rule, keepA: parts.some(part => part.keepA) };
  }

  function randomSyllable() {
    const roll = Math.random();
    const onsets = Object.keys(gaByOnset);
    const vcKeys = Object.keys(vc);
    if (roll < 0.34 && onsets.length) {
      const onset = pick(onsets);
      const jong = Math.random() < 0.55 ? '' : pick(JONGSUNG.filter(Boolean));
      return compose(onset, 'ㅏ', jong);
    }
    if (roll < 0.67 && vcKeys.length) {
      const [jung, jong] = pick(vcKeys).split('|');
      return compose(pick(CHOSUNG), jung, jong);
    }
    const completes = Object.keys(complete);
    if (roll < 0.74 && completes.length) return pick(completes);
    const jong = Math.random() < 0.4 ? '' : pick(JONGSUNG.filter(Boolean));
    return compose(pick(CHOSUNG), pick(JUNGSUNG), jong);
  }

  function randomNumber() {
    const len = 1 + Math.floor(Math.random() * 3);
    let text = '';
    for (let i = 0; i < len; i++) text += String(Math.floor(Math.random() * 10));
    if (text.length > 1) text = String(Number(text));
    return text || '0';
  }

  function byRecipe(recipe) {
    if (recipe === 'wordsign') {
      const words = Object.keys(wordAbbr);
      if (!words.length) return null;
      return translate(pick(words));
    }
    if (recipe === 'syllable') return translate(randomSyllable());
    if (recipe === 'pair') return translate(randomSyllable() + randomSyllable());
    if (recipe === 'triple') return translate(randomSyllable() + randomSyllable() + randomSyllable());
    if (recipe === 'number') return translate(randomNumber());
    if (recipe === 'number_unit') {
      const units = exempt.filter(unit => /^[가-힣]+$/.test(unit));
      if (!units.length) return translate(randomNumber());
      return translate(randomNumber() + pick(units));
    }
    if (recipe === 'punct') {
      if (!punct.length) return null;
      const mark = pick(punct);
      return {
        braille: mark.unicode,
        parts: [{ text: mark.ch, braille: mark.unicode, label: mark.name }],
        rule: '문장부호'
      };
    }
    return translate(randomSyllable());
  }

  return { byRecipe, translate, separateCollisions };
}

function buildEnglish(data) {
  const spell = data.spell || {};
  const shortforms = data.shortforms || {};
  const contractions = data.contractions || {};
  const lexicon = data.lexicon || {};
  const numbers = data.numbers || {};

  const letters = {};
  Object.entries(spell.single_letter?.items || {}).forEach(([k, v]) => { letters[k] = v.unicode; });

  const alphaWords = [];
  Object.values(spell.alphabetic_wordsign?.items || {}).forEach(item => {
    if (item.word && item.unicode) alphaWords.push({ word: item.word, unicode: item.unicode, rule: '알파벳 단어약어' });
  });

  const shortformItems = [];
  Object.values(shortforms).forEach(block => {
    const sectionRule = block?.rule || {};
    const fallbackSuffixes = Array.isArray(sectionRule.allowedSuffixes) ? sectionRule.allowedSuffixes : [];
    Object.values(block?.items || {}).forEach(item => {
      if (!item.word || !item.unicode) return;
      const specified = Array.isArray(item.allowedSuffixes);
      const suffixes = specified ? item.allowedSuffixes : fallbackSuffixes;
      shortformItems.push({
        word: item.word,
        unicode: item.unicode,
        suffixes,
        suffixesSpecified: specified,
        rule: sectionRule
      });
    });
  });
  const closedAffixes = new Set([
    ...Object.keys(lexicon.inflectional_suffixes?.items || {}),
    ...Object.keys(lexicon.derivational_suffixes?.items || {}),
    's',
    "'s"
  ]);
  const lexiconPrefixes = new Set(Object.keys(lexicon.prefixes?.items || {}));

  const wholeWords = alphaWords.map(item => ({ ...item }));
  const groups = [];

  (contractions.groups || []).forEach(group => {
    const type = group.type || '';
    Object.entries(group.items || {}).forEach(([key, item]) => {
      const text = (item.word || key || '').toLowerCase();
      if (!text || !item.unicode) return;
      if (group.rule?.standingAloneOnly) {
        const ruleName = group.category === 'strong_wordsign' ? '강세 단어약어' : '하점 단어약어';
        wholeWords.push({ word: item.word || key, unicode: item.unicode, rule: ruleName });
        return;
      }
      if (type === 'initial_contractions' || type === 'strong_wordsign' || group.rule?.canStandAlone) {
        wholeWords.push({ word: item.word || key, unicode: item.unicode, rule: '단어약어' });
      }
      let where = 'anywhere';
      if (group.rule?.requiresSurroundingLetters) where = 'medial';
      else if (type === 'prefix_groupsign') where = 'prefix';
      else if (type === 'final_contractions') where = 'final';
      else if (type === 'initial_contractions') return;
      groups.push({
        text,
        unicode: item.unicode,
        where,
        avoidStandingAlone: !!group.rule?.avoidWhenStandingAlone
      });
    });
  });
  groups.sort((a, b) => b.text.length - a.text.length);

  const shortformByWord = new Map(shortformItems.map(item => [item.word.toLowerCase(), item]));
  const wholeByWord = new Map(wholeWords.map(item => [item.word.toLowerCase(), item]));

  const prefixes = Object.keys(lexicon.prefixes?.items || {});
  const roots = Object.values(lexicon.roots?.items || {}).map(item => ({
    stem: item.stem,
    hasSilentE: !!item.hasSilentE,
    doubleConsonant: !!item.doubleConsonantAllowed
  })).filter(item => item.stem);
  const plainSuffixes = ['s', 'ed', 'ing', 'er', 'est', 'ly'];

  const numPrefix = numbers.numeric_indicators?.num_prefix?.unicode || '⠼';
  const digits = {};
  Object.entries(numbers.digits || {}).forEach(([k, v]) => { digits[k] = v.unicode; });
  const grade1Indicator = numbers.grade1_indicators?.grade1_symbol?.unicode || '⠆';
  const grade1Cells = new Set(Object.values(digits));
  const isolatedLetter = {};
  Object.entries(spell.isolated_letter?.items || {}).forEach(([key, item]) => {
    const letter = String(item.word || key).toLowerCase();
    if (item.unicode) isolatedLetter[letter] = item.unicode;
  });

  function standingLetter(letter) {
    return isolatedLetter[String(letter || '').toLowerCase()] || '';
  }

  const APOSTROPHE_CELL = '⠄';
  const APOSTROPHE_SUFFIXES = ["'d", "'ll", "'re", "'s", "'t", "'ve"];

  function spellPlain(text) {
    let out = '';
    for (const ch of text) {
      if (ch === "'") out += APOSTROPHE_CELL;
      else if (letters[ch]) out += letters[ch];
      else return '';
    }
    return out;
  }

  const rootItems = lexicon.roots?.items || {};
  const prefixList = Object.keys(lexicon.prefixes?.items || {}).sort((a, b) => b.length - a.length);
  const suffixList = [
    ...Object.keys(lexicon.inflectional_suffixes?.items || {}),
    ...Object.keys(lexicon.derivational_suffixes?.items || {})
  ].sort((a, b) => b.length - a.length);
  const disallowBridge = (lexicon.combining_rules?.bridge_rule?.disallowCrossMorphemeContraction) !== false;

  function surfaceParts(sub) {
    if (rootItems[sub]) return [sub];
    for (const suffix of suffixList) {
      if (!sub.endsWith(suffix)) continue;
      const stem = sub.slice(0, -suffix.length);
      if (stem && rootItems[stem]) return [stem, suffix];
    }
    return null;
  }

  // 사전에 있는 접두·어근·접미가 이어진 단어만 경계를 만든다. 경계를 가로지르는 약어는 쓰지 않는다.
  function morphemeBounds(word) {
    if (!disallowBridge) return new Set();
    let matched = '';
    let rest = word;
    for (const prefix of prefixList) {
      if (word.startsWith(prefix) && word.length > prefix.length) {
        matched = prefix;
        rest = word.slice(prefix.length);
        break;
      }
    }
    let parts = surfaceParts(rest);
    if (parts) parts = matched ? [matched, ...parts] : parts;
    else if (matched) parts = surfaceParts(word);
    if (!parts) {
      for (const prefix of prefixList) {
        if (!word.startsWith(prefix) || word.length === prefix.length) continue;
        const tail = word.slice(prefix.length);
        if (Object.keys(rootItems).some((root) => tail === root || tail.startsWith(root))) {
          parts = [prefix, tail];
          break;
        }
      }
    }
    if (!parts || parts.length < 2 || parts.join('') !== word) return new Set();
    const bounds = new Set();
    let cursor = 0;
    parts.slice(0, -1).forEach((part) => {
      cursor += part.length;
      bounds.add(cursor);
    });
    return bounds;
  }

  function crossesBoundary(bounds, start, end) {
    for (const bound of bounds) {
      if (start < bound && bound < end) return true;
    }
    return false;
  }

  function greedy(word, opts = {}) {
    let i = 0;
    let out = '';
    const lower = word.toLowerCase();
    const bounds = opts.bridge === false ? new Set() : morphemeBounds(lower);
    while (i < lower.length) {
      let matched = null;
      for (const group of groups) {
        if (!lower.startsWith(group.text, i)) continue;
        const atStart = i === 0;
        const atEnd = i + group.text.length === lower.length;
        if (crossesBoundary(bounds, i, i + group.text.length)) continue;
        if (group.where === 'medial' && (atStart || atEnd)) continue;
        if (group.avoidStandingAlone && atStart && atEnd) continue;
        if (group.where === 'prefix' && !(atStart && !atEnd)) continue;
        if (group.where === 'final' && !(atEnd && (!atStart || opts.finalAtStart))) continue;
        matched = group;
        break;
      }
      if (matched) {
        out += matched.unicode;
        i += matched.text.length;
      } else {
        const cell = letters[lower[i]];
        if (!cell) return '';
        out += cell;
        i += 1;
      }
    }
    return out;
  }

  function encodeChunk(text, role) {
    const lower = text.toLowerCase();
    if (role === 'suffix' && SUFFIX_BRAILLE[lower]) return SUFFIX_BRAILLE[lower];
    if ((role === 'word' || role === 'shortform') && wholeByWord.has(lower)) return wholeByWord.get(lower).unicode;
    if (role === 'shortform' && shortformByWord.has(lower)) return shortformByWord.get(lower).unicode;
    return greedy(lower);
  }

  function pack(chunks, rule) {
    const parts = [];
    let braille = '';
    let text = '';
    for (const chunk of chunks) {
      const cell = encodeChunk(chunk.text, chunk.role);
      if (!cell) return null;
      parts.push({ text: chunk.text, braille: cell, label: chunk.label || chunk.text });
      braille += cell;
      text += chunk.text;
    }
    if (!text || !braille) return null;
    return { braille, parts, rule, text };
  }

  function byRecipe(recipe) {
    if (recipe === 'wordsign') {
      if (!wholeWords.length) return null;
      const item = pick(wholeWords);
      return pack([{ text: item.word, role: 'word', label: item.rule }], item.rule);
    }
    if (recipe === 'shortform') {
      if (!shortformItems.length) return null;
      const item = pick(shortformItems);
      return pack([{ text: item.word, role: 'shortform', label: '축어' }], '축어');
    }
    if (recipe === 'shortform_suffix') {
      const pool = shortformItems.filter(item => item.suffixes.length);
      if (!pool.length) return null;
      const item = pick(pool);
      const suffix = pick(item.suffixes);
      const surface = `${item.word}${suffix}`.toLowerCase();
      const own = shortformByWord.get(surface);
      if (own && own.unicode) {
        return pack([{ text: own.word, role: 'shortform', label: '축어' }], '축어');
      }
      return pack([
        { text: item.word, role: 'shortform', label: '축어' },
        { text: suffix, role: 'suffix', label: `어미 ${suffix}` }
      ], '축어 + 어미');
    }
    if (recipe === 'affix') {
      if (!roots.length) return null;
      const mode = pick(prefixes.length ? ['pr', 'rs', 'prs'] : ['rs']);
      const root = pick(roots);
      const suffix = pick(plainSuffixes);
      const useSuffix = mode.includes('s');
      let stem = root.stem;
      if (useSuffix && /[^aeiou]y$/i.test(stem) && ['es', 'ed', 'er', 'est', 'ly'].includes(suffix)) {
        const oneBeat = (stem.toLowerCase().match(/[aeiouy]+/g) || []).length <= 1;
        if (!(suffix === 'ly' && oneBeat)) stem = `${stem.slice(0, -1)}i`;
      } else if (useSuffix && root.hasSilentE && SILENT_E_SUFFIXES.includes(suffix) && /e$/i.test(stem)) {
        const keepE = /[cg]e$/i.test(stem) && suffix === 'able';
        if (!keepE) stem = stem.slice(0, -1);
      } else if (
        useSuffix && root.doubleConsonant && ['ing', 'ed', 'er', 'est'].includes(suffix)
        && /[^aeiou][aeiou][bcdfghjklmnpqrstvz]$/i.test(stem)
      ) {
        stem += stem.slice(-1);
      }
      const chunks = [];
      if (mode.includes('p') && prefixes.length) {
        const prefix = pick(prefixes);
        chunks.push({ text: prefix, role: 'prefix', label: `접두사 ${prefix}` });
      }
      chunks.push({ text: stem, role: 'root', label: `어근 ${stem}` });
      if (useSuffix) chunks.push({ text: suffix, role: 'suffix', label: `어미 ${suffix}` });
      return pack(chunks, '형태소 결합');
    }
    if (recipe === 'number') {
      const len = 1 + Math.floor(Math.random() * 3);
      let text = '';
      for (let i = 0; i < len; i++) text += String(Math.floor(Math.random() * 10));
      text = String(Number(text));
      const braille = numPrefix + text.split('').map(d => digits[d] || '').join('');
      if (braille.length !== text.length + 1) return null;
      return {
        text,
        braille,
        parts: [{ text, braille, label: `number ${text}` }],
        rule: '숫자'
      };
    }
    if (recipe === 'punct') {
      const mark = pick(EN_PUNCT);
      return {
        text: mark.ch,
        braille: mark.unicode,
        parts: [{ text: mark.ch, braille: mark.unicode, label: mark.name }],
        rule: '문장부호'
      };
    }
    return null;
  }

  function shortformSuffixOk(suffix, data) {
    const rule = data.rule || {};
    const allowed = new Set(data.suffixes || []);
    const specified = !!data.suffixesSpecified;
    if (suffix === "'s" || suffix === '’s') {
      return !!rule.allowApostropheS && (!specified || allowed.has("'s"));
    }
    if (suffix === 's' && !rule.allowPluralS) return false;
    if (allowed.has(suffix) && (rule.allowSuffix || specified)) return true;
    if (rule.allowCompound && suffix && !closedAffixes.has(suffix)) return true;
    return false;
  }

  function shortformPartsOk(head, tail, data) {
    if (!head && !tail) return false;
    const rule = data.rule || {};
    if (head && (!lexiconPrefixes.has(head) || !rule.allowPrefix)) return false;
    if (tail && !shortformSuffixOk(tail, data)) return false;
    return true;
  }

  function renderShortform(word) {
    const exact = shortformByWord.get(word);
    if (exact) return exact.unicode;
    const keys = Array.from(shortformByWord.keys()).sort((a, b) => b.length - a.length);
    for (const key of keys) {
      const data = shortformByWord.get(key);
      let start = 0;
      while (start <= word.length) {
        const idx = word.indexOf(key, start);
        if (idx < 0) break;
        start = idx + 1;
        const head = word.slice(0, idx);
        const tail = word.slice(idx + key.length);
        if (!shortformPartsOk(head, tail, data)) continue;
        const prefix = head ? greedy(head, { bridge: false }) : '';
        const suffix = tail ? greedy(tail, { finalAtStart: true, bridge: false }) : '';
        if ((head && !prefix) || (tail && !suffix)) continue;
        return prefix + data.unicode + suffix;
      }
    }
    return '';
  }

  function translateWord(word, opts = {}) {
    const lower = word.toLowerCase();
    const standing = opts.standingAlone !== false;
    const apostrophe = lower.match(/^([a-z]+)('[a-z]+)$/);
    if (apostrophe && APOSTROPHE_SUFFIXES.includes(apostrophe[2])) {
      const stem = translateWord(apostrophe[1], opts);
      const tail = spellPlain(apostrophe[2]);
      if (stem && tail) {
        return {
          braille: stem.braille + tail,
          parts: stem.parts.concat([{ text: apostrophe[2], braille: tail, label: apostrophe[2] }]),
          rule: '어미'
        };
      }
    }
    if (standing && lower.length === 1 && isolatedLetter[lower]) {
      const cell = isolatedLetter[lower];
      return { braille: cell, parts: [{ text: word, braille: cell, label: word }], rule: '단독 알파벳' };
    }
    const known = wholeByWord.get(lower);
    if (known && known.unicode) {
      return { braille: known.unicode, parts: [{ text: word, braille: known.unicode, label: word }], rule: '단어' };
    }
    const shortform = renderShortform(lower);
    if (shortform) {
      return { braille: shortform, parts: [{ text: word, braille: shortform, label: word }], rule: '축어' };
    }
    const braille = greedy(lower);
    if (!braille) return null;
    return { braille, parts: [{ text: word, braille, label: word }], rule: '철자' };
  }

  // 띄어쓴 숫자열은 수표를 반복하지 않고 숫자 빈칸(⠐)으로 잇는다. 글자 앞 띄어쓰기는 수표를 끝낸다.
  function translateText(text) {
    let braille = '';
    const parts = [];
    let inNumber = false;
    let i = 0;
    while (i < text.length) {
      const ch = text[i];
      if (ch >= '0' && ch <= '9') {
        let token = '';
        let tokenBraille = inNumber ? '' : numPrefix;
        while (i < text.length && text[i] >= '0' && text[i] <= '9') {
          if (!digits[text[i]]) return null;
          token += text[i];
          tokenBraille += digits[text[i]];
          i += 1;
        }
        inNumber = true;
        braille += tokenBraille;
        parts.push({ text: token, braille: tokenBraille, label: `number ${token}` });
        continue;
      }
      if (ch === ' ') {
        const next = text[i + 1] || '';
        if (inNumber && next >= '0' && next <= '9') {
          braille += NUMERIC_SPACE;
          parts.push({ text: ' ', braille: NUMERIC_SPACE, label: '숫자 빈칸' });
          i += 1;
          continue;
        }
        inNumber = false;
        braille += ' ';
        parts.push({ text: ' ', braille: ' ', label: 'space' });
        i += 1;
        continue;
      }
      const cameFromNumber = inNumber;
      inNumber = false;
      const mark = EN_PUNCT.find((item) => item.ch === ch);
      if (mark) {
        braille += mark.unicode;
        parts.push({ text: mark.ch, braille: mark.unicode, label: mark.name });
        i += 1;
        continue;
      }
      let word = '';
      while (i < text.length && /[A-Za-z'’]/.test(text[i])) {
        word += text[i] === '’' ? "'" : text[i];
        i += 1;
      }
      if (!word) return null;
      const piece = translateWord(word, { standingAlone: !cameFromNumber });
      if (!piece) return null;
      let wordBraille = piece.braille;
      if (cameFromNumber && wordBraille && grade1Cells.has(Array.from(wordBraille)[0])) {
        wordBraille = grade1Indicator + wordBraille;
        braille += wordBraille;
        parts.push({ text: word, braille: wordBraille, label: `1급 점자표 + ${word}` });
      } else {
        braille += wordBraille;
        parts.push(...piece.parts);
      }
    }
    if (!braille || !parts.length) return null;
    return { braille, parts, rule: parts.length > 1 ? '형태소 결합' : (parts[0].label || '단어'), text };
  }

  return { byRecipe, translateWord, translateText, standingLetter };
}

function recipesFor(lang, game) {
  const koAtom = ['wordsign', 'syllable', 'number', 'punct'];
  const enAtom = ['wordsign', 'shortform', 'number', 'punct'];
  const koCombo = ['pair', 'triple', 'number_unit'];
  const enCombo = ['shortform_suffix', 'affix'];
  if (game === 'select') return lang === 'EN' ? enCombo : koCombo;
  return lang === 'EN' ? enAtom : koAtom;
}

function patternDistance(a, b) {
  const x = Array.from(a);
  const y = Array.from(b);
  if (x.length !== y.length) return 99;
  let distance = 0;
  for (let i = 0; i < x.length; i++) {
    let diff = (x[i].codePointAt(0) ^ y[i].codePointAt(0)) & 0xFF;
    while (diff) {
      distance += diff & 1;
      diff >>= 1;
    }
  }
  return distance;
}

// 같은 재료 안에서 점 모양이 가장 닮은 점형을 고른다. 약자와 풀어 쓴 형태가 짝이면 그 짝이 먼저다.
function nearPatterns(card, scope) {
  const out = [];
  const seen = new Set([card.pattern]);
  if (card.contrast && !seen.has(card.contrast)) {
    seen.add(card.contrast);
    out.push(card.contrast);
  }
  const ranked = [];
  scope.forEach(({ cards }) => {
    cards.forEach((other) => {
      if (!other.pattern || seen.has(other.pattern)) return;
      seen.add(other.pattern);
      const distance = patternDistance(card.pattern, other.pattern);
      if (distance < 99) ranked.push({ pattern: other.pattern, score: distance + Math.random() * 1.5 });
    });
  });
  ranked.sort((a, b) => a.score - b.score).forEach((item) => out.push(item.pattern));
  return out.slice(0, 3);
}

// 뜻 보기와 블록은 이 단원과 앞 단원의 글자만 쓴다. 점형이 같은 글자는 정답과 구분이 안 되므로 뺀다.
function nearTexts(unit, card, scope) {
  const current = new Set();
  const before = new Set();
  scope.forEach(({ unit: owner, cards }) => {
    const bucket = owner.id === unit.id ? current : before;
    cards.forEach((other) => {
      if (!other.letter || other.letter === card.letter || other.pattern === card.pattern) return;
      bucket.add(other.letter);
    });
  });
  const list = shuffle(Array.from(current));
  shuffle(Array.from(before)).forEach((letter) => {
    if (!current.has(letter)) list.push(letter);
  });
  return list.slice(0, 3);
}

function distractorBraille(correct, preferred = []) {
  const found = new Set(preferred.filter((item) => item && item !== correct));
  if (found.size >= 3) return Array.from(found).slice(0, 3);
  const mirroredH = mirrorBraille(correct, { 1: 4, 2: 5, 3: 6, 4: 1, 5: 2, 6: 3 });
  const mirroredV = mirrorBraille(correct, { 1: 3, 2: 2, 3: 1, 4: 6, 5: 5, 6: 4 });
  [mirroredH, mirroredV].forEach(item => {
    if (item && item !== correct) found.add(item);
  });
  for (let i = 0; i < 10 && found.size < 3; i++) {
    const mutated = mutateBraille(correct);
    if (mutated && mutated !== correct) found.add(mutated);
  }
  return Array.from(found).slice(0, 3);
}

function distractorText(text, lang) {
  for (let attempt = 0; attempt < 6; attempt++) {
    const chars = Array.from(text);
    if (!chars.length) return `${text}?`;
    const idx = Math.floor(Math.random() * chars.length);
    if (lang === 'KO' && chars[idx] >= '가' && chars[idx] <= '힣') {
      const parts = decompose(chars[idx]);
      if (parts) {
        const jong = Math.random() < 0.5 ? '' : pick(JONGSUNG.filter(Boolean));
        chars[idx] = compose(pick(CHOSUNG), parts[1], jong) || chars[idx];
      }
    } else if (chars[idx] >= '0' && chars[idx] <= '9') {
      chars[idx] = String((Number(chars[idx]) + 1 + Math.floor(Math.random() * 8)) % 10);
    } else if (/[a-z]/i.test(chars[idx])) {
      chars[idx] = pick('abcdefghijklmnopqrstuvwxyz'.split(''));
    } else {
      chars[idx] = lang === 'KO' ? '가' : 'a';
    }
    const next = chars.join('');
    if (next !== text) return next;
  }
  return `${text}${lang === 'KO' ? '가' : 's'}`;
}

function meaningOptions(target, lang) {
  const found = [];
  const seen = new Set([target]);
  for (let i = 0; i < 24 && found.length < 3; i++) {
    const next = distractorText(target, lang);
    if (next && !seen.has(next)) {
      seen.add(next);
      found.push(next);
    }
  }
  return shuffle([target, ...found]);
}

function finishItem(raw, lang, seq) {
  const target = raw.text || raw.parts.map(part => part.text).join('');
  const hint = raw.hint || raw.parts.map(part => part.label).filter(Boolean).join(' · ');
  const explanation = raw.explanation || hint || target;
  const seqText = raw.parts.map(part => part.text);
  let blocks;
  let meanings;
  if (Array.isArray(raw.distractTexts)) {
    // 단원 문제: 재료 밖의 글자(잠긴 약자·약어)가 보기에 끼지 않게 재료에서만 고른다.
    const extras = raw.distractTexts.filter(item => item && item !== target);
    meanings = shuffle([target, ...extras.slice(0, 3)]);
    blocks = shuffle(seqText.concat(extras.filter(item => !seqText.includes(item)).slice(0, 3)));
  } else {
    const extras = [];
    for (let i = 0; i < 4; i++) extras.push(distractorText(seqText[i % seqText.length] || target, lang));
    blocks = shuffle(seqText.concat(extras.filter(item => item && !seqText.includes(item)).slice(0, 3)));
    meanings = meaningOptions(target, lang);
  }
  return {
    id: raw.key || `combo_${seq}`,
    lang,
    category: raw.rule,
    type_label: raw.rule,
    rule_type: raw.rule,
    target_text: target,
    target_braille: raw.braille,
    text: target,
    braille: raw.braille,
    hint: hint || target,
    explanation,
    prompt_audio: raw.hint ? `${target}. ${raw.hint}` : (hint || target),
    distractors_braille: distractorBraille(raw.braille, raw.distractBraille || []),
    distractors_text: meanings.filter(item => item !== target),
    meaning_options: meanings,
    parts: raw.parts,
    tokens: seqText,
    correct_sequence: seqText,
    available_blocks: blocks,
    blocks,
    block_granularity: lang === 'KO' ? 'SYLLABLE' : 'WORD',
    sentence_pre: lang === 'KO' ? '제시어' : 'Prompt',
    sentence_post: lang === 'KO' ? '의 점자' : 'in braille',
    clue: `${target}. ${hint || ''}`.trim(),
    rule_analysis: { rule_name: raw.rule, detail: explanation },
    meta: { type: raw.rule }
  };
}

// ---------------------------------------------------------------------------
// 짧은 문장. 재료 카드의 점형을 그대로 이어 붙이고, 재료 밖의 것은 쓰지 않는다.
// ---------------------------------------------------------------------------

function tokenOf(kind, text, braille, steps, label) {
  return { kind, text, braille, steps, label: label || kind };
}

function groupByKind(cards) {
  const by = {};
  cards.forEach((card) => {
    (by[card.kind] = by[card.kind] || []).push(card);
  });
  return by;
}

// 수표는 한 번만 붙이고 숫자만 잇는다. 첫 자리는 0으로 시작하지 않는다.
function numberToken(digitCards) {
  const pool = digitCards.filter((card) => card.steps && card.steps.length === 2);
  if (!pool.length) return null;
  const lead = pool.filter((card) => card.letter !== '0');
  const chosen = [pick(lead.length ? lead : pool)];
  if (Math.random() < 0.5) chosen.push(pick(pool));
  const steps = [chosen[0].steps[0], ...chosen.map((card) => card.steps[1])];
  return tokenOf('number', chosen.map((card) => card.letter).join(''), stepsPattern(steps), steps, '숫자');
}

function assembleSentence(tokens, mark, lang) {
  const parts = [];
  const steps = [];
  let text = '';
  let braille = '';
  tokens.forEach((token, index) => {
    if (index > 0) {
      text += ' ';
      const prev = tokens[index - 1];
      if (lang === 'en' && prev.kind === 'number' && token.kind === 'number' && token.braille.startsWith('⠼')) {
        const body = token.braille.slice(1);
        text += token.text;
        braille += NUMERIC_SPACE + body;
        steps.push(NUMERIC_SPACE_STEP, ...token.steps.slice(1));
        parts.push({ text: token.text, braille: NUMERIC_SPACE + body, label: token.label });
        return;
      }
      braille += ' ';
      steps.push(SPACE_STEP);
    }
    text += token.text;
    braille += token.braille;
    steps.push(...token.steps);
    parts.push({ text: token.text, braille: token.braille, label: token.label });
  });
  if (mark) {
    text += mark.letter;
    braille += mark.pattern;
    steps.push(...mark.steps);
    parts.push({ text: mark.letter, braille: mark.pattern, label: mark.letter });
  }
  return { text, braille, steps, parts, tokens, mark };
}

function sentenceMaker(generators, marks, lang) {
  const kinds = Object.keys(generators);
  if (!kinds.length) return null;

  function token(kind) {
    for (let attempt = 0; attempt < 6; attempt++) {
      const made = generators[kind]();
      if (made && made.text && made.braille) return made;
    }
    return null;
  }

  return {
    sentence() {
      const count = 2 + Math.floor(Math.random() * 2);
      const tokens = [];
      for (let i = 0; i < count; i++) {
        const made = token(pick(kinds));
        if (!made) return null;
        tokens.push(made);
      }
      return assembleSentence(tokens, marks.length ? pick(marks) : null, lang);
    },
    // 한 칸 조각만 바꾼 문장. 점형이 겹치면 뜻 보기에서 정답이 둘이 되므로 점형이 다른 것만 모은다.
    variants(sentence) {
      const out = [];
      const seenBraille = new Set([sentence.braille]);
      const seenText = new Set([sentence.text]);
      for (let i = 0; i < 30 && out.length < 3; i++) {
        const index = Math.floor(Math.random() * sentence.tokens.length);
        const old = sentence.tokens[index];
        const swapped = generators[old.kind] ? token(old.kind) : null;
        if (!swapped || swapped.braille === old.braille) continue;
        const tokens = sentence.tokens.slice();
        tokens[index] = swapped;
        const alt = assembleSentence(tokens, sentence.mark, lang);
        if (seenBraille.has(alt.braille) || seenText.has(alt.text)) continue;
        seenBraille.add(alt.braille);
        seenText.add(alt.text);
        out.push({ text: alt.text, braille: alt.braille });
      }
      return out;
    }
  };
}

// 음절을 이은 뒤 ko_parser와 같은 규칙으로 다시 점역한다.
// '사' 뒤 모음은 풀어 쓰고, 받침이 붙으면 약자(억·언·얼, 가 계열)를 그대로 쓴다.
// 억·언·얼 계열 약자를 아직 배우지 않았으면, 받침을 붙여 그 약자가 생기는 음절은 만들지 않는다.
function koreanWord(pieces, jongs, translate, jongOk = () => true) {
  const count = 1 + Math.floor(Math.random() * 3);
  let text = '';
  for (let i = 0; i < count; i++) {
    const piece = pick(pieces);
    if (!piece || !piece.letter) break;
    let syllable = piece.letter;
    const parts = decompose(piece.letter);
    if (jongs.length && parts && !parts[2] && (piece.kind === 'syllable' || piece.kind === 'ga') && Math.random() < 0.35) {
      const jong = pick(jongs);
      const composed = compose(parts[0], parts[1], jong.letter);
      if (composed && jongOk(parts[0], parts[1], jong.letter)) syllable = composed;
    }
    text += syllable;
  }
  if (!text) return null;
  const made = translate(text);
  if (!made || !made.braille) return null;
  return tokenOf('word', text, made.braille, partsToSteps(made.parts), '낱말');
}

function koreanTokens(cards, translate, abbr) {
  const by = groupByKind(cards);
  const pieces = [].concat(by.syllable || [], by.ga || [], by.eok || []);
  const jongs = (by.jongsung || []).filter((card) => JONGSUNG.includes(card.letter));
  const knowsVowelCoda = !abbr || (by.eok || []).some((card) => abbr.vowelCodaKeys.has(card.letter));
  const jongOk = (cho, jung, jong) => knowsVowelCoda || !abbr.usesVowelCoda(cho, jung, jong);
  const generators = {};
  if (pieces.length) generators.word = () => koreanWord(pieces, jongs, translate, jongOk);
  if (by.word && by.word.length) {
    generators.wordsign = () => {
      const card = pick(by.word);
      return tokenOf('wordsign', card.letter, card.pattern, card.steps, '단어 약어');
    };
  }
  if (by.digit && by.digit.length) generators.number = () => numberToken(by.digit);
  const marks = (by.mark || []).filter((card) => ['.', '?', '!'].includes(card.letter));
  return sentenceMaker(generators, marks, 'ko');
}

function englishTokens(cards) {
  const by = groupByKind(cards);
  const words = [].concat(by.wordsign || [], by.shortform || [], (by.contraction || []).filter((card) => card.standalone));
  const generators = {};
  if (words.length) {
    generators.word = () => {
      const card = pick(words);
      return tokenOf('word', card.letter, card.pattern, card.steps, card.kind);
    };
  }
  if (by.digit && by.digit.length) generators.number = () => numberToken(by.digit);
  return sentenceMaker(generators, [], 'en');
}

export function createEngine(data) {
  const ko = buildKorean(data);
  const en = buildEnglish(data);
  const koAbbr = abbreviationIndex(data.ko);
  const bundles = {
    'ko.json': data.ko,
    'ko_marks.json': data.marks,
    'numbers.json': data.numbers,
    'en_spell.json': data.spell,
    'en_shortform.json': data.shortforms,
    'en_contractions.json': data.contractions
  };
  const recent = new Set();
  const rounds = new Map();
  const recentRounds = new Map();
  const placeCursor = new Map();
  let seq = 0;

  function itemKey(owner, card) {
    return `${owner.id}:${card.letter}`;
  }

  // 통과한 앞 단원의 오답 키만 모은다. 날짜로 거르지 않는다.
  function reviewEntries(unit, lang) {
    const found = [];
    scopeOf(unit).forEach(({ unit: owner, cards }) => {
      if (owner.id === unit.id || !isUnitPassed(lang, owner.id)) return;
      const wrong = new Set(wrongItemKeys(lang, owner.id));
      cards.forEach((card) => {
        if (wrong.has(itemKey(owner, card))) found.push({ card, owner });
      });
    });
    return found;
  }

  // 규칙 종류가 여러 개면 한 스테이지에 같은 종류가 몰리지 않게 나누고,
  // 바로 앞 스테이지에 나온 문제는 아직 안 나온 문제가 있을 때 뒤로 미룬다.
  function spreadCards(unit, cards, need, wrong) {
    const families = new Set(cards.map((card) => card.family).filter(Boolean));
    if (families.size < 2) return null;
    const recentKeys = recentRounds.get(unit.id) || new Set();
    const cap = Math.max(2, Math.ceil(need / families.size));
    const order = shuffle(cards);
    const picked = [];
    const seen = new Set();
    const counts = {};

    function take(opts) {
      for (const card of order) {
        if (picked.length >= need) return;
        const key = itemKey(unit, card);
        if (seen.has(key)) continue;
        const family = card.family || '_';
        if (!opts.ignoreCap && (counts[family] || 0) >= cap) continue;
        if (!opts.ignoreRecent && recentKeys.has(key)) continue;
        const isWrong = wrong.has(key);
        if (opts.wrong === true && !isWrong) continue;
        if (opts.wrong === false && isWrong) continue;
        seen.add(key);
        counts[family] = (counts[family] || 0) + 1;
        picked.push(card);
      }
    }

    take({ wrong: true, ignoreRecent: true });
    take({ wrong: false });
    take({ wrong: false, ignoreRecent: true });
    take({ ignoreCap: true, ignoreRecent: true });
    recentRounds.set(unit.id, new Set(picked.map((card) => itemKey(unit, card))));
    return picked.map((card) => ({ card, owner: unit }));
  }

  function buildRound(unit, lang) {
    const cards = scopeOf(unit).find((item) => item.unit.id === unit.id)?.cards || [];
    const pool = shuffle(reviewEntries(unit, lang));
    const reviewN = pool.length ? 2 + Math.floor(Math.random() * 2) : 0;
    const review = [];
    for (let i = 0; i < reviewN; i += 1) review.push(pool[i % pool.length]);

    const wrong = new Set(wrongItemKeys(lang, unit.id));
    const need = STAGE_SIZE - review.length;
    let fresh = spreadCards(unit, cards, need, wrong);
    if (!fresh) {
      const wrongCards = shuffle(cards.filter((card) => wrong.has(itemKey(unit, card))));
      const others = shuffle(cards.filter((card) => !wrong.has(itemKey(unit, card))));
      fresh = [];
      const seen = new Set();
      for (const card of wrongCards.concat(others)) {
        const key = itemKey(unit, card);
        if (seen.has(key)) continue;
        seen.add(key);
        fresh.push({ card, owner: unit });
        if (fresh.length >= need) break;
      }
    }
    if (fresh.length < need && cards.length) {
      const fill = shuffle(cards);
      let i = 0;
      while (fresh.length < need) {
        fresh.push({ card: fill[i % fill.length], owner: unit });
        i += 1;
      }
    }
    return shuffle(review.concat(fresh));
  }

  // 단원마다 카드는 한 번만 자른다. 재료는 그 단원과 앞 단원이다.
  const scopes = new Map();

  function scopeOf(unit) {
    if (!scopes.has(unit.id)) {
      const scope = materialsFor(unit, bundles).map(({ unit: owner, cards }) => ({
        unit: owner,
        cards: cards.filter((card) => card.letter && card.pattern)
      }));
      scopes.set(unit.id, scope);
    }
    return scopes.get(unit.id);
  }

  const HANGUL_KINDS = new Set(['syllable', 'ga', 'eok']);
  const WORD_KINDS = new Set(['word', 'wordsign', 'shortform', 'contraction']);
  const OPEN_MARKS = new Set(['“', '‘', '《', '〈', '(', '[', '<tn>', '<i>']);
  const END_MARKS = new Set(['”', '’', '》', '〉', ')', ']', '</tn>', '<b>', '.', '?', '!']);

  function hangulCard(card) {
    return HANGUL_KINDS.has(card.kind);
  }

  // 글자 사이의 띄어쓰기만 넣는다. 숫자와 겹치는 한글은 separateCollisions가 검사기대로 띄운다.
  function printSpace(left, right) {
    if (left.kind === 'digit' && right.kind === 'digit') return false;
    if (left.kind === 'digit' && (hangulCard(right) || right.kind === 'word')) return false;
    if ((hangulCard(left) || left.kind === 'word') && (hangulCard(right) || right.kind === 'word')) {
      return left.kind === 'word' || right.kind === 'word';
    }
    if (left.kind === 'mark' || right.kind === 'mark') return false;
    return true;
  }

  // 'ㅏ를 생략하지 않는 경우'는 그 단원(ko-keep-a)부터 낸다. 앞 단원에서는 이런 조합을 만들지 않는다.
  const keepAUnit = unitById('ko-keep-a');

  function allowsKeepA(unit) {
    return !!keepAUnit && unit.lang === keepAUnit.lang && unit.order >= keepAUnit.order;
  }

  function koTranslateFor(unit) {
    if (allowsKeepA(unit)) return ko.translate;
    return (text) => {
      const made = ko.translate(text);
      return made && made.keepA ? null : made;
    };
  }

  function renderSeq(seq, unit) {
    const lang = unit.lang;
    let text = '';
    seq.forEach((card, index) => {
      if (index > 0 && printSpace(seq[index - 1], card)) text += ' ';
      text += card.letter;
    });
    if (lang !== 'en') text = ko.separateCollisions(text);
    const made = lang === 'en' ? en.translateText(text) : koTranslateFor(unit)(text);
    if (!made || !made.braille) return null;
    return {
      text,
      braille: made.braille,
      steps: partsToSteps(made.parts),
      parts: made.parts
    };
  }

  function arrangeTopic(topic, fillers, slot) {
    const [a, b] = fillers;
    if (!b) return slot === 0 ? [topic, a] : [a, topic];
    if (slot === 0) return [topic, a, b];
    if (slot === 1) return [a, topic, b];
    return [a, b, topic];
  }

  function fillerKindOk(topic, card) {
    if (!card.letter || !card.pattern || card.letter === topic.letter) return false;
    if (card.kind === 'contraction' && !card.standalone) return false;
    if (HANGUL_KINDS.has(topic.kind) || topic.kind === 'word' || topic.kind === 'mark') {
      return HANGUL_KINDS.has(card.kind);
    }
    if (topic.kind === 'digit') {
      return topic.langHint === 'ko' ? HANGUL_KINDS.has(card.kind) : card.kind === 'digit';
    }
    if (WORD_KINDS.has(topic.kind)) return WORD_KINDS.has(card.kind) || card.kind === 'digit';
    return false;
  }

  // 1단원은 글자 한 조각만 낸다. 그 뒤 단원은 주제를 앞·중간·뒤로 옮긴다.
  function placeTopic(unit, card) {
    if (!unit || unit.order <= 1 || card.family) return null;
    if (card.kind === 'contraction' && !card.standalone) return null;
    const placeable = HANGUL_KINDS.has(card.kind) || card.kind === 'word' || card.kind === 'digit'
      || card.kind === 'mark' || WORD_KINDS.has(card.kind);
    if (!placeable) return null;

    const topic = { ...card, langHint: unit.lang };
    const earlier = [];
    const same = [];
    const alts = [];
    scopeOf(unit).forEach(({ unit: owner, cards }) => {
      cards.forEach((item) => {
        if (owner.id === unit.id && item.kind === card.kind && item.letter !== card.letter) alts.push(item);
        if (!fillerKindOk(topic, item)) return;
        (owner.id === unit.id ? same : earlier).push(item);
      });
    });
    const pool = earlier.length >= 2 ? earlier : earlier.concat(same);
    if (!pool.length) return null;

    let slot = (placeCursor.get(unit.id) || 0) % 3;
    if (card.kind === 'mark') {
      if (OPEN_MARKS.has(card.letter)) slot = 0;
      else if (END_MARKS.has(card.letter)) slot = 2;
      else slot = 1;
    }

    let fillers = null;
    const bag = shuffle(pool);
    for (let attempt = 0; attempt < 12 && !fillers; attempt += 1) {
      const picked = [];
      for (let i = 0; i < bag.length && picked.length < 2; i += 1) {
        const item = bag[(attempt + i) % bag.length];
        if (picked.some((chosen) => chosen.letter === item.letter)) continue;
        picked.push(item);
      }
      if (!picked.length) break;
      const seq = arrangeTopic(card, picked, slot);
      if (renderSeq(seq, unit)) fillers = picked;
    }
    if (!fillers) return null;

    const made = renderSeq(arrangeTopic(card, fillers, slot), unit);
    if (!made || !made.text || made.text === card.letter) return null;

    const distractBraille = [];
    const distractTexts = [];
    for (const alt of shuffle(alts)) {
      if (distractBraille.length >= 3) break;
      const seq = arrangeTopic(alt, fillers, slot);
      const other = renderSeq(seq, unit);
      if (!other || !other.braille || other.braille === made.braille || other.text === made.text) continue;
      distractBraille.push(other.braille);
      distractTexts.push(other.text);
    }

    if (card.kind !== 'mark') placeCursor.set(unit.id, (placeCursor.get(unit.id) || 0) + 1);
    return { ...made, distractBraille, distractTexts };
  }

  function fromCard(unit, card, owner = unit) {
    const scope = scopeOf(unit);
    const review = owner.id !== unit.id;
    const placed = review ? null : placeTopic(unit, card);
    if (placed) {
      return {
        key: itemKey(owner, card),
        text: placed.text,
        braille: placed.braille,
        parts: placed.parts,
        rule: owner.title,
        hint: `${unit.title} 단원`,
        explanation: assemblyText(placed.steps) || card.explain || card.dotText,
        distractBraille: placed.distractBraille,
        distractTexts: placed.distractTexts
      };
    }
    let text = card.letter;
    let braille = card.pattern;
    let explanation = card.explain || card.dotText;
    const distractBraille = nearPatterns(card, scope);
    if (card.kind === 'alphabet') {
      const alone = en.standingLetter(card.letter);
      if (alone && alone !== braille) {
        distractBraille.unshift(braille);
        braille = alone;
        explanation = `단독 알파벳 ${card.letter}은 단어 약어와 겹치므로 앞에 1급 기호표 ⠰를 붙입니다. ${explanation}`;
      }
    }
    return {
      key: itemKey(owner, card),
      text,
      braille,
      parts: [{ text, braille, label: owner.title }],
      rule: owner.title,
      hint: review ? `${owner.title} 복습` : `${unit.title} 단원`,
      explanation,
      distractBraille,
      distractTexts: nearTexts(unit, card, scope)
    };
  }

  // 짧은 문장: 순차에서는 통과한 단원만, 자유 학습에서는 앞 단원 재료를 전부 이어 붙인다.
  const recentSentences = new Map();

  function sentenceCards(unit) {
    const code = LANG_CODE[unit.lang];
    const free = loadStudyMode() === 'free';
    const cards = [];
    scopeOf(unit).forEach(({ unit: owner, cards: list }) => {
      if (owner.id === unit.id) return;
      if (free || isUnitPassed(code, owner.id)) cards.push(...list);
    });
    return cards;
  }

  function fromSentence(unit) {
    const cards = sentenceCards(unit);
    const maker = unit.lang === 'en' ? englishTokens(cards) : koreanTokens(cards, koTranslateFor(unit), koAbbr);
    if (!maker) return null;
    const recentList = recentSentences.get(unit.id) || [];
    let sentence = null;
    for (let attempt = 0; attempt < 12 && !sentence; attempt++) {
      const made = maker.sentence();
      if (made && !recentList.includes(made.text)) sentence = made;
    }
    if (!sentence) sentence = maker.sentence();
    if (!sentence) return null;
    recentList.push(sentence.text);
    if (recentList.length > 5) recentList.shift();
    recentSentences.set(unit.id, recentList);
    const variants = maker.variants(sentence);
    return {
      key: `${unit.id}:문장`,
      text: sentence.text,
      braille: sentence.braille,
      parts: sentence.parts,
      rule: unit.title,
      hint: `${unit.title} 단원`,
      explanation: assemblyText(sentence.steps),
      distractBraille: variants.map((item) => item.braille),
      distractTexts: variants.map((item) => item.text)
    };
  }

  function fromUnit(unitId) {
    const unit = unitById(unitId);
    if (!unit) return null;
    const lang = LANG_CODE[unit.lang] || 'KO';
    if (!canOpenUnit(unit.id, lang)) return null;
    seq += 1;
    if (isComposeUnit(unit)) {
      const raw = fromSentence(unit);
      return raw ? finishItem(raw, lang, seq) : null;
    }
    const cards = scopeOf(unit).find((item) => item.unit.id === unit.id)?.cards || [];
    if (!cards.length) return null;
    let queue = rounds.get(unit.id);
    if (!queue || !queue.length) {
      queue = buildRound(unit, lang);
      rounds.set(unit.id, queue);
    }
    const picked = queue.shift();
    return finishItem(fromCard(unit, picked.card, picked.owner), lang, seq);
  }

  function next(opts = {}) {
    const lang = (opts.lang || 'KO').toUpperCase() === 'EN' ? 'EN' : 'KO';
    const game = opts.game || 'select';
    const unitId = opts.unitId || '';
    if (unitId) return fromUnit(unitId);
    const recipes = recipesFor(lang, game);
    const bank = lang === 'EN' ? en : ko;

    for (let attempt = 0; attempt < 40; attempt++) {
      const raw = bank.byRecipe(pick(recipes));
      if (!raw || !raw.braille || !raw.parts?.length) continue;
      const text = raw.text || raw.parts.map(part => part.text).join('');
      const key = `${lang}:${text}`;
      if (recent.has(key)) continue;
      recent.add(key);
      if (recent.size > 48) recent.delete(recent.values().next().value);
      seq += 1;
      return finishItem({ ...raw, text }, lang, seq);
    }

    seq += 1;
    const raw = bank.byRecipe(pick(recipes)) || bank.byRecipe(lang === 'EN' ? 'wordsign' : 'syllable');
    return finishItem(raw || {
      text: lang === 'EN' ? 'can' : '가',
      braille: lang === 'EN' ? '⠉' : '⠫',
      parts: [{ text: lang === 'EN' ? 'can' : '가', braille: lang === 'EN' ? '⠉' : '⠫', label: 'fallback' }],
      rule: 'fallback'
    }, lang, seq);
  }

  return { next, translateKo: ko.translate, translateEn: en.translateText };
}

export async function loadQuizEngine() {
  const [ko, marks, numberRules, numbers, spell, shortforms, contractions, lexicon] = await Promise.all([
    loadJson('ko.json'),
    loadJson('ko_marks.json'),
    loadJson('ko_number_rules.json'),
    loadJson('numbers.json'),
    loadJson('en_spell.json'),
    loadJson('en_shortform.json'),
    loadJson('en_contractions.json'),
    loadJson('lexicon_en.json')
  ]);
  return createEngine({ ko, marks, numberRules, numbers, spell, shortforms, contractions, lexicon });
}
