/**
 * 사전 조합으로 퀴즈를 만든다.
 * morpheme, blank, builders는 형태소 하나만을 문제로 낸다.
 * select는 형태소를 자유롭게 결합한 심화 문제만 낸다.
 * unitId가 있으면 그 단원 source의 카드만 낸다. 읽기는 morpheme·select·builders, 쓰기는 blank.
 */
import { cardsFor, unitById } from './curriculum.js';
import { STAGE_SIZE, wrongItemKeys } from './shell.js';

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
  const grade1 = numbers.grade1_indicators?.grade1_symbol?.unicode || '⠰';
  const digits = {};
  Object.entries(numbers.digits || {}).forEach(([k, v]) => { digits[k] = v.unicode; });
  const affected = ko.special_rules?.number_prefix_rule?.affected_initials || ['ㄴ', 'ㄷ', 'ㅁ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
  const exempt = rules.collision_resolutions?.trailing_letters?.exempt_units || ['년', '월', '일', '시', '분', '초', '개', '명', '원'];

  const punct = [];
  Object.values(marks).forEach(block => {
    Object.entries(block?.items || {}).forEach(([ch, item]) => {
      if (ch.length === 1 && item.unicode) punct.push({ ch, name: item.word || ch, unicode: item.unicode });
    });
  });

  function translateSyllable(ch, nextCh, afterNumber, rest) {
    const parts = decompose(ch);
    if (!parts) return null;
    const [cho, jung, jong] = parts;
    const labels = [];
    const exemptHit = !!(rest && exempt.some(unit => rest.startsWith(unit)));

    if (ch === '사' && (afterNumber || (nextCh && decompose(nextCh)?.[0] === 'ㅇ'))) {
      let braille = saExpanded + (jong ? (jongMap[jong] || '') : '');
      if (afterNumber && affected.includes(cho) && !exemptHit) braille = grade1 + braille;
      return {
        braille,
        label: afterNumber ? "숫자 뒤 '사' 풀어쓰기" : "모음 앞 '사' 풀어쓰기"
      };
    }

    let head = '';
    if (afterNumber && affected.includes(cho) && !exemptHit) {
      head = grade1;
      labels.push(`수표 뒤 '${cho}' 앞에 한글표`);
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

    if (jung === 'ㅏ' && gaByOnset[baseCho]) {
      const tail = jong ? (jongMap[jong] || '') : '';
      labels.push(`'${baseCho}ㅏ' 약자` + (jong ? ` + 받침 ${jong}` : ''));
      return { braille: head + tenser + gaByOnset[baseCho] + tail, label: labels.join(', ') };
    }

    if (jong && vc[`${jung}|${jong}`]) {
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

  function translate(text) {
    if (wordAbbr[text]) {
      return {
        braille: wordAbbr[text],
        parts: [{ text, braille: wordAbbr[text], label: `단어 약어 '${text}'` }],
        rule: '단어 약어'
      };
    }

    let braille = '';
    const parts = [];
    let inNumber = false;
    let i = 0;
    while (i < text.length) {
      const ch = text[i];
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

      const afterNumber = inNumber;
      inNumber = false;
      if (ch >= '가' && ch <= '힣') {
        const piece = translateSyllable(ch, text[i + 1] || '', afterNumber, text.slice(i));
        if (!piece || !piece.braille) return null;
        braille += piece.braille;
        parts.push({ text: ch, braille: piece.braille, label: piece.label });
        i += 1;
        continue;
      }

      const mark = punct.find(p => p.ch === ch);
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
    return { braille, parts, rule };
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

  return { byRecipe, translate };
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
    const fallbackSuffixes = block?.rule?.allowSuffix ? (block.rule.allowedSuffixes || []) : [];
    Object.values(block?.items || {}).forEach(item => {
      if (!item.word || !item.unicode) return;
      const suffixes = Array.isArray(item.allowedSuffixes) ? item.allowedSuffixes : fallbackSuffixes;
      shortformItems.push({ word: item.word, unicode: item.unicode, suffixes });
    });
  });

  const wholeWords = alphaWords.map(item => ({ ...item }));
  const groups = [];

  (contractions.groups || []).forEach(group => {
    const type = group.type || '';
    Object.entries(group.items || {}).forEach(([key, item]) => {
      const text = (item.word || key || '').toLowerCase();
      if (!text || !item.unicode) return;
      if (group.rule?.standingAloneOnly) {
        wholeWords.push({ word: item.word || key, unicode: item.unicode, rule: '하점 단어약어' });
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
    hasSilentE: !!item.hasSilentE
  })).filter(item => item.stem);
  const plainSuffixes = ['s', 'ed', 'ing', 'er', 'est', 'ly'];

  const numPrefix = numbers.numeric_indicators?.num_prefix?.unicode || '⠼';
  const digits = {};
  Object.entries(numbers.digits || {}).forEach(([k, v]) => { digits[k] = v.unicode; });

  function greedy(word) {
    let i = 0;
    let out = '';
    const lower = word.toLowerCase();
    while (i < lower.length) {
      let matched = null;
      for (const group of groups) {
        if (!lower.startsWith(group.text, i)) continue;
        const atStart = i === 0;
        const atEnd = i + group.text.length === lower.length;
        if (group.where === 'medial' && (atStart || atEnd)) continue;
        if (group.avoidStandingAlone && atStart && atEnd) continue;
        if (group.where === 'prefix' && !(atStart && !atEnd)) continue;
        if (group.where === 'final' && !(atEnd && !atStart)) continue;
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
      if (useSuffix && root.hasSilentE && SILENT_E_SUFFIXES.includes(suffix) && stem.endsWith('e')) {
        stem = stem.slice(0, -1);
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

  function translateWord(word) {
    const known = wholeByWord.get(word.toLowerCase()) || shortformByWord.get(word.toLowerCase());
    if (known && known.unicode) {
      return { braille: known.unicode, parts: [{ text: word, braille: known.unicode, label: word }], rule: '단어' };
    }
    const braille = greedy(word);
    if (!braille) return null;
    return { braille, parts: [{ text: word, braille, label: word }], rule: '철자' };
  }

  return { byRecipe, translateWord };
}

function recipesFor(lang, game) {
  const koAtom = ['wordsign', 'syllable', 'number', 'punct'];
  const enAtom = ['wordsign', 'shortform', 'number', 'punct'];
  const koCombo = ['pair', 'triple', 'number_unit'];
  const enCombo = ['shortform_suffix', 'affix'];
  if (game === 'select') return lang === 'EN' ? enCombo : koCombo;
  return lang === 'EN' ? enAtom : koAtom;
}

function distractorBraille(correct) {
  const found = new Set();
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
  const hint = raw.parts.map(part => part.label).filter(Boolean).join(' · ');
  const explanation = raw.dotText
    ? `${target}은 ${raw.dotText}, 점형 ${raw.braille}`
    : (hint || target);
  const seqText = raw.parts.map(part => part.text);
  const extras = [];
  for (let i = 0; i < 4; i++) extras.push(distractorText(seqText[i % seqText.length] || target, lang));
  const blocks = shuffle(seqText.concat(extras.filter(item => item && !seqText.includes(item)).slice(0, 3)));
  const meanings = meaningOptions(target, lang);
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
    prompt_audio: hint || target,
    distractors_braille: distractorBraille(raw.braille),
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
    rule_analysis: { rule_name: raw.rule, detail: hint || target },
    meta: { type: raw.rule }
  };
}

export function createEngine(data) {
  const ko = buildKorean(data);
  const en = buildEnglish(data);
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
  let seq = 0;

  function buildRound(unitId, lang, cards) {
    const wrong = new Set(wrongItemKeys(lang, unitId));
    const keyOf = (card) => `${unitId}:${card.letter}`;
    const wrongCards = shuffle(cards.filter((card) => wrong.has(keyOf(card))));
    const others = shuffle(cards.filter((card) => !wrong.has(keyOf(card))));
    const round = [];
    const seen = new Set();
    for (const card of wrongCards.concat(others)) {
      const key = keyOf(card);
      if (seen.has(key)) continue;
      seen.add(key);
      round.push(card);
      if (round.length >= STAGE_SIZE) break;
    }
    if (round.length < STAGE_SIZE && cards.length) {
      const fill = shuffle(cards);
      let i = 0;
      while (round.length < STAGE_SIZE) {
        round.push(fill[i % fill.length]);
        i += 1;
      }
    }
    return round;
  }

  function fromUnit(unitId, lang) {
    const unit = unitById(unitId);
    if (!unit) return null;
    const cards = cardsFor(unit, bundles).filter((card) => card.letter && card.pattern);
    if (!cards.length) return null;
    let queue = rounds.get(unitId);
    if (!queue || !queue.length) {
      queue = buildRound(unitId, lang, cards);
      rounds.set(unitId, queue);
    }
    const card = queue.shift();
    const key = `${unitId}:${card.letter}`;
    seq += 1;
    return finishItem({
      key,
      text: card.letter,
      braille: card.pattern,
      dotText: card.dotText,
      parts: [{ text: card.letter, braille: card.pattern, label: card.letter }],
      rule: unit.title
    }, lang, seq);
  }

  function next(opts = {}) {
    const lang = (opts.lang || 'KO').toUpperCase() === 'EN' ? 'EN' : 'KO';
    const game = opts.game || 'select';
    const unitId = opts.unitId || '';
    if (unitId) return fromUnit(unitId, lang);
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

  return { next, translateKo: ko.translate, translateEn: en.translateWord };
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
