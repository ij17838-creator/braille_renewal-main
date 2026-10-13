/**
 * 문제와 보기가 소리로 헷갈리지 않게 거르는 발음 검사. 점형·점자 규칙과는 상관없고, 어떤 글자를 낼지만 고른다.
 * - 끝소리 규칙(받침이 대표음으로 바뀜, 겹받침이 하나만 소리 남)과 받침 ㅎ이 사라지는 경우는 문제로 내지 않는다. 연음은 괜찮다.
 * - 그 밖의 발음 변화(비음화·유음화·된소리·거센소리·구개음화)는 문제로 내되,
 *   앞 받침 때문에 첫소리가 바뀐 뒤 글자 자리에서는 보기 소리가 정답 소리와 초성·중성·종성 가운데 하나까지만 같아야 한다.
 * - ㅐ/ㅔ, ㅒ/ㅖ, ㅙ/ㅞ/ㅚ는 같은 소리로 보고, 정답과 이것만 다른 보기는 뺀다.
 */

const CHO = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
const JUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'];
const JONG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];

// 받침 일곱 소리 (표준 발음법 제8~11항)
const REPRESENTATIVE = {
  'ㄱ': 'ㄱ', 'ㄲ': 'ㄱ', 'ㅋ': 'ㄱ', 'ㄳ': 'ㄱ', 'ㄺ': 'ㄱ',
  'ㄴ': 'ㄴ', 'ㄵ': 'ㄴ', 'ㄶ': 'ㄴ',
  'ㄷ': 'ㄷ', 'ㅅ': 'ㄷ', 'ㅆ': 'ㄷ', 'ㅈ': 'ㄷ', 'ㅊ': 'ㄷ', 'ㅌ': 'ㄷ', 'ㅎ': 'ㄷ',
  'ㄹ': 'ㄹ', 'ㄼ': 'ㄹ', 'ㄽ': 'ㄹ', 'ㄾ': 'ㄹ', 'ㅀ': 'ㄹ',
  'ㅁ': 'ㅁ', 'ㄻ': 'ㅁ',
  'ㅂ': 'ㅂ', 'ㅍ': 'ㅂ', 'ㅄ': 'ㅂ', 'ㄿ': 'ㅂ',
  'ㅇ': 'ㅇ'
};
// 겹받침: 모음 앞에서 앞 것은 남고 뒤 것이 넘어간다.
const CLUSTER = {
  'ㄳ': ['ㄱ', 'ㅅ'], 'ㄵ': ['ㄴ', 'ㅈ'], 'ㄶ': ['ㄴ', 'ㅎ'], 'ㄺ': ['ㄹ', 'ㄱ'], 'ㄻ': ['ㄹ', 'ㅁ'],
  'ㄼ': ['ㄹ', 'ㅂ'], 'ㄽ': ['ㄹ', 'ㅅ'], 'ㄾ': ['ㄹ', 'ㅌ'], 'ㄿ': ['ㄹ', 'ㅍ'], 'ㅀ': ['ㄹ', 'ㅎ'], 'ㅄ': ['ㅂ', 'ㅅ']
};
const TENSE = { 'ㄱ': 'ㄲ', 'ㄷ': 'ㄸ', 'ㅂ': 'ㅃ', 'ㅅ': 'ㅆ', 'ㅈ': 'ㅉ' };
const ASPIRATE = { 'ㄱ': 'ㅋ', 'ㄷ': 'ㅌ', 'ㅂ': 'ㅍ', 'ㅈ': 'ㅊ' };
const NASAL = { 'ㄱ': 'ㅇ', 'ㄷ': 'ㄴ', 'ㅂ': 'ㅁ' };
// 화면낭독기로 들으면 구별이 어려운 모음
const VOWEL_GROUP = { 'ㅐ': 'ㅔ', 'ㅒ': 'ㅖ', 'ㅙ': 'ㅞ', 'ㅚ': 'ㅞ' };

function split(ch) {
  const code = ch.charCodeAt(0) - 0xAC00;
  if (code < 0 || code > 11171) return null;
  return { cho: CHO[Math.floor(code / 588)], jung: JUNG[Math.floor((code % 588) / 28)], jong: JONG[code % 28] };
}

function join(s) {
  const ci = CHO.indexOf(s.cho);
  const ji = JUNG.indexOf(s.jung);
  const ki = JONG.indexOf(s.jong);
  if (ci < 0 || ji < 0 || ki < 0) return '?';
  return String.fromCharCode(0xAC00 + (ci * 21 + ji) * 28 + ki);
}

// 한 낱말(한글 음절만 이어진 덩어리)의 발음.
// liaison: 연음만 한 소리, full: 표준 발음, neutral: 끝소리 규칙이나 ㅎ 탈락이 일어났는지.
function pronounceRun(run) {
  const syl = run.map((ch) => ({ ...split(ch) }));
  const liaison = syl.map((s) => ({ ...s }));
  const full = syl.map((s) => ({ ...s }));
  let neutral = false;

  for (let i = 0; i < syl.length; i += 1) {
    const jong = syl[i].jong;
    if (!jong) continue;
    const next = syl[i + 1];
    const nextCho = next ? next.cho : '';

    if (nextCho === 'ㅇ') {
      if (jong === 'ㅇ') continue;
      if (jong === 'ㅎ' || jong === 'ㄶ' || jong === 'ㅀ') {
        // 좋아[조아], 않아[아나]: ㅎ 소리가 사라진다.
        neutral = true;
        const keep = jong === 'ㅎ' ? '' : CLUSTER[jong][0];
        liaison[i].jong = ''; full[i].jong = '';
        if (keep) { liaison[i + 1].cho = keep; full[i + 1].cho = keep; }
        continue;
      }
      let stay = '';
      let move = jong;
      if (CLUSTER[jong]) [stay, move] = CLUSTER[jong];
      liaison[i].jong = stay; liaison[i + 1].cho = move;
      full[i].jong = stay;
      let moved = move;
      if (jong === 'ㄳ' || jong === 'ㅄ') moved = 'ㅆ'; // 넋이[넉씨], 값이[갑씨]
      if (next.jung === 'ㅣ' && (move === 'ㄷ' || move === 'ㅌ')) moved = move === 'ㄷ' ? 'ㅈ' : 'ㅊ'; // 굳이[구지]
      full[i + 1].cho = moved;
      continue;
    }

    // 받침 ㅎ 뒤 ㄱ·ㄷ·ㅈ·ㅅ: 거센소리·된소리 (좋고[조코], 좋소[조쏘])
    if ((jong === 'ㅎ' || jong === 'ㄶ' || jong === 'ㅀ') && next && (ASPIRATE[nextCho] || nextCho === 'ㅅ')) {
      full[i].jong = jong === 'ㅎ' ? '' : CLUSTER[jong][0];
      full[i + 1].cho = nextCho === 'ㅅ' ? 'ㅆ' : ASPIRATE[nextCho];
      continue;
    }
    // 받침 ㅈ·ㅊ 뒤 ㅎ: 꽂히다[꼬치다]
    if ((jong === 'ㅈ' || jong === 'ㅊ') && nextCho === 'ㅎ') {
      full[i].jong = '';
      full[i + 1].cho = 'ㅊ';
      continue;
    }

    const rep = REPRESENTATIVE[jong];
    if (rep !== jong) neutral = true;
    full[i].jong = rep;
    if (!next) continue;

    if (nextCho === 'ㅎ' && ASPIRATE[rep]) { // 국화[구콰]
      full[i].jong = '';
      full[i + 1].cho = ASPIRATE[rep];
    } else if (NASAL[rep] && (nextCho === 'ㄴ' || nextCho === 'ㅁ')) { // 국물[궁물]
      full[i].jong = NASAL[rep];
    } else if (nextCho === 'ㄹ' && (rep === 'ㅁ' || rep === 'ㅇ')) { // 침략[침냑]
      full[i + 1].cho = 'ㄴ';
    } else if (nextCho === 'ㄹ' && (rep === 'ㄱ' || rep === 'ㅂ')) { // 국립[궁닙]
      full[i].jong = NASAL[rep];
      full[i + 1].cho = 'ㄴ';
    } else if (rep === 'ㄴ' && nextCho === 'ㄹ') { // 신라[실라]
      full[i].jong = 'ㄹ';
    } else if (rep === 'ㄹ' && nextCho === 'ㄴ') { // 칼날[칼랄]
      full[i + 1].cho = 'ㄹ';
    } else if ((rep === 'ㄱ' || rep === 'ㄷ' || rep === 'ㅂ') && TENSE[nextCho]) { // 국보[국뽀]
      full[i + 1].cho = TENSE[nextCho];
    }
  }
  return { written: syl, liaison, full, neutral };
}

function runsOf(text) {
  const runs = [];
  let current = [];
  Array.from(text || '').forEach((ch) => {
    if (split(ch)) current.push(ch);
    else {
      if (current.length) runs.push(current);
      current = [];
    }
  });
  if (current.length) runs.push(current);
  return runs;
}

/** 글자 전체의 소리. 낱말 사이는 끊어 읽는다. */
export function pronounce(text) {
  const written = [];
  const liaison = [];
  const full = [];
  let neutral = false;
  runsOf(text).forEach((run) => {
    const made = pronounceRun(run);
    written.push(...made.written);
    liaison.push(...made.liaison);
    full.push(...made.full);
    neutral = neutral || made.neutral;
  });
  return { written, liaison, full, neutral, text: full.map(join).join('') };
}

/** 문제로 내도 되는지: 끝소리 규칙(겹받침 포함)이나 받침 ㅎ 탈락이 없어야 한다. 연음은 괜찮다. */
export function soundsAsWritten(text) {
  return !pronounce(text).neutral;
}

// 받침이 이 글자 하나뿐이면, 뒤에 ㅇ으로 시작하는 글자가 와야 끝소리 규칙을 피한다.
export function needsLiaison(jong) {
  return !!jong && jong !== 'ㅎ' && REPRESENTATIVE[jong] !== jong;
}

function vowelKey(jung) {
  return VOWEL_GROUP[jung] || jung;
}

function soundKey(s) {
  return `${s.cho}${vowelKey(s.jung)}${s.jong}`;
}

// 자모 하나짜리 카드(모음 ㅚ 등)는 모음만 묶어 비교한다.
function jamoKey(text) {
  return Array.from(text).map((ch) => VOWEL_GROUP[ch] || ch).join('');
}

/**
 * 보기(option)가 정답(target)과 소리로 헷갈리는지.
 * 1) 비슷한 모음을 같게 보고 소리가 같으면 헷갈린다.
 * 2) 정답에서 앞 받침 때문에 첫소리가 바뀐 뒤 글자(국보[국뽀]의 '보') 자리에 보기가 다른 글자를 두었다면,
 *    그 자리 소리는 초성·중성·종성 가운데 하나까지만 같아야 한다. 연음으로 넘어온 소리는 바뀐 것으로 보지 않는다.
 */
export function soundsConfusable(target, option) {
  if (!target || !option || target === option) return false;
  const a = pronounce(target);
  const b = pronounce(option);
  if (!a.full.length || !b.full.length) {
    return !a.full.length && !b.full.length && jamoKey(target) === jamoKey(option);
  }
  const restA = target.replace(/[가-힣]/g, '');
  const restB = option.replace(/[가-힣]/g, '');
  if (restA === restB && a.full.map(soundKey).join('|') === b.full.map(soundKey).join('|')) return true;
  if (a.full.length !== b.full.length) return false;
  for (let i = 0; i < a.full.length; i += 1) {
    const changed = a.full[i].cho !== a.liaison[i].cho;
    if (!changed || join(a.written[i]) === join(b.written[i])) continue;
    const x = a.full[i];
    const y = b.full[i];
    const same = (x.cho === y.cho) + (vowelKey(x.jung) === vowelKey(y.jung)) + (x.jong === y.jong);
    if (same >= 2) return true;
  }
  return false;
}
