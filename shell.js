const KEYS = {
  lang: 'braille_lang',
  level: 'braille_level',
  mode: 'braille_input_mode',
  theme: 'braille_theme',
  scale: 'braille_text_scale',
  tts: 'braille_tts',
  pitch: 'braille_pitch',
  sfx: 'braille_sfx',
  emboss: 'braille_emboss_mode',
  ruleStats: 'braille_rule_stats',
  history: 'braille_global_history',
  progress: 'braille_progress'
};

const LEGACY_KEYS = ['braille_select_stats', 'braille_builder_stats'];

function readJson(key, fallback) {
  try {
    const parsed = JSON.parse(localStorage.getItem(key) || '');
    return parsed == null ? fallback : parsed;
  } catch {
    return fallback;
  }
}

export function loadSettings() {
  return {
    lang: (localStorage.getItem(KEYS.lang) || 'KO').toUpperCase(),
    level: parseInt(localStorage.getItem(KEYS.level) || '1', 10) || 1,
    mode: localStorage.getItem(KEYS.mode) || 'KEYBOARD',
    theme: localStorage.getItem(KEYS.theme) || 'off',
    scale: localStorage.getItem(KEYS.scale) || 'normal',
    tts: localStorage.getItem(KEYS.tts) !== 'false',
    pitch: localStorage.getItem(KEYS.pitch) !== 'false',
    sfx: localStorage.getItem(KEYS.sfx) !== 'false',
    emboss: localStorage.getItem(KEYS.emboss) || 'embossed'
  };
}

export function saveSettings(partial = {}) {
  const next = loadSettings();
  if (partial.lang) next.lang = String(partial.lang).toUpperCase();
  if (partial.level != null && partial.level !== '') next.level = parseInt(partial.level, 10) || 1;
  if (partial.mode) next.mode = partial.mode;
  const theme = partial.theme ?? partial.contrastTheme;
  if (theme != null) next.theme = theme;
  const scale = partial.scale ?? partial.textScale;
  if (scale != null) next.scale = scale;
  if (typeof partial.tts === 'boolean') next.tts = partial.tts;
  if (typeof partial.pitch === 'boolean') next.pitch = partial.pitch;
  if (typeof partial.sfx === 'boolean') next.sfx = partial.sfx;
  if (partial.emboss) next.emboss = partial.emboss;

  localStorage.setItem(KEYS.lang, next.lang);
  localStorage.setItem(KEYS.level, String(next.level));
  localStorage.setItem(KEYS.mode, next.mode);
  localStorage.setItem(KEYS.theme, next.theme);
  localStorage.setItem(KEYS.scale, next.scale);
  localStorage.setItem(KEYS.tts, String(next.tts));
  localStorage.setItem(KEYS.pitch, String(next.pitch));
  localStorage.setItem(KEYS.sfx, String(next.sfx));
  localStorage.setItem(KEYS.emboss, next.emboss);
  applyVisualSettings(next);
  return next;
}

export function normalizeTheme(theme) {
  if (theme === 'yellow') return 'hc-yellow';
  if (theme === 'bw') return 'hc-white-black';
  return theme;
}

export function applyVisualSettings(settings = loadSettings()) {
  const themeValue = settings.theme ?? settings.contrastTheme ?? 'off';
  const scaleValue = settings.scale ?? settings.textScale ?? 'normal';
  const body = document.body;
  body.classList.remove('text-scale-normal', 'text-scale-large', 'text-scale-xlarge');
  const theme = normalizeTheme(themeValue);
  if (theme && theme !== 'off') document.documentElement.setAttribute('data-theme', theme);
  else document.documentElement.removeAttribute('data-theme');
  body.classList.add(`text-scale-${scaleValue}`);
}

export function readRuleStats() {
  const stats = readJson(KEYS.ruleStats, {});
  return stats && typeof stats === 'object' && !Array.isArray(stats) ? stats : {};
}

export function recordResult({ game, rule, correct }) {
  if (!rule || typeof rule !== 'string') return readRuleStats();
  const stats = readRuleStats();
  if (!stats[rule] || typeof stats[rule] !== 'object') {
    stats[rule] = { errors: 0, trials: 0, games: {} };
  }
  stats[rule].trials = (stats[rule].trials || 0) + 1;
  if (!correct) {
    stats[rule].errors = (stats[rule].errors || 0) + 1;
    if (!stats[rule].games || typeof stats[rule].games !== 'object') stats[rule].games = {};
    if (game) stats[rule].games[game] = (stats[rule].games[game] || 0) + 1;
  }
  localStorage.setItem(KEYS.ruleStats, JSON.stringify(stats));
  return stats;
}

const PASS_PERCENT = 80;

export function readProgress() {
  const data = readJson(KEYS.progress, {});
  return data && typeof data === 'object' && !Array.isArray(data) ? data : {};
}

function writeProgress(data) {
  localStorage.setItem(KEYS.progress, JSON.stringify(data));
}

function langKey(lang) {
  return String(lang || loadSettings().lang || 'KO').toUpperCase();
}

function ensureLang(data, lang) {
  const key = langKey(lang);
  if (!data[key] || typeof data[key] !== 'object' || Array.isArray(data[key])) {
    data[key] = { current: '', units: {} };
  }
  if (!data[key].units || typeof data[key].units !== 'object' || Array.isArray(data[key].units)) {
    data[key].units = {};
  }
  return data[key];
}

function ensureUnit(langState, unitId) {
  if (!langState.units[unitId] || typeof langState.units[unitId] !== 'object') {
    langState.units[unitId] = { read: 0, write: 0, readDone: false, writeDone: false, passed: false, wrong: [] };
  }
  const unit = langState.units[unitId];
  if (typeof unit.read !== 'number') unit.read = 0;
  if (typeof unit.write !== 'number') unit.write = 0;
  if (!Array.isArray(unit.wrong)) unit.wrong = [];
  return unit;
}

function normalizeSkill(skill, game) {
  if (skill === 'read' || skill === 'write') return skill;
  if (game === 'blank') return 'write';
  if (game) return 'read';
  return '';
}

function sessionMet(correct, total) {
  return total > 0 && correct * 100 >= total * PASS_PERCENT;
}

export function recordItem({ lang, unitId, itemId, skill, correct } = {}) {
  const id = unitId ? String(unitId) : '';
  const item = itemId == null ? '' : String(itemId);
  const skillName = normalizeSkill(skill);
  if (!id || !item || !skillName) return readProgress();
  const data = readProgress();
  const langState = ensureLang(data, lang);
  langState.current = id;
  const unit = ensureUnit(langState, id);
  const wrong = unit.wrong.filter((key) => key !== item);
  if (!correct) wrong.push(item);
  unit.wrong = wrong;
  writeProgress(data);
  return data;
}

export function wrongItemKeys(lang, unitId) {
  const data = readProgress();
  const unit = data[langKey(lang)] && data[langKey(lang)].units
    ? data[langKey(lang)].units[unitId]
    : null;
  return unit && Array.isArray(unit.wrong) ? unit.wrong.slice() : [];
}

export function isUnitPassed(lang, unitId) {
  const data = readProgress();
  const unit = data[langKey(lang)] && data[langKey(lang)].units
    ? data[langKey(lang)].units[unitId]
    : null;
  return !!(unit && unit.passed);
}

export function isUnitOpen(lang, unitId) {
  const langState = readProgress()[langKey(lang)];
  if (!langState || typeof langState !== 'object') return false;
  return langState.current === unitId;
}

function saveSkillScore({ lang, unitId, skill, game, correct, total }) {
  const id = unitId ? String(unitId) : '';
  const skillName = normalizeSkill(skill, game);
  if (!id || !skillName) return false;
  const data = readProgress();
  const langState = ensureLang(data, lang);
  langState.current = id;
  const unit = ensureUnit(langState, id);
  const met = sessionMet(correct, total);
  if (met || !unit[`${skillName}Done`]) unit[skillName] = Number(correct) || 0;
  if (met) unit[`${skillName}Done`] = true;
  // 읽기·쓰기를 모두 넘긴 이 단원만 통과다. 다음 단원은 열지 않는다.
  if (met && unit.readDone && unit.writeDone) unit.passed = true;
  writeProgress(data);
  return !!(met && unit.passed);
}

export function errorCounts() {
  const out = {};
  Object.entries(readRuleStats()).forEach(([rule, stat]) => {
    const errors = stat && typeof stat.errors === 'number' ? stat.errors : 0;
    if (errors > 0) out[rule] = errors;
  });
  return out;
}

export function readHistory() {
  const history = readJson(KEYS.history, []);
  return Array.isArray(history) ? history : [];
}

export function recordSession(entry) {
  if (!entry || !entry.game) return readHistory();
  const settings = loadSettings();
  const history = readHistory();
  history.unshift({
    game: String(entry.game),
    lang: entry.lang || settings.lang,
    level: Number(entry.level) || settings.level,
    score: Number(entry.score) || 0,
    total: Number(entry.total) || 0,
    date: entry.date || new Date().toISOString()
  });
  const trimmed = history.slice(0, 50);
  localStorage.setItem(KEYS.history, JSON.stringify(trimmed));
  return trimmed;
}

export function clearLearningData() {
  localStorage.removeItem(KEYS.ruleStats);
  localStorage.removeItem(KEYS.history);
  localStorage.removeItem(KEYS.progress);
  LEGACY_KEYS.forEach((key) => localStorage.removeItem(key));
}

export function goHub() {
  window.location.href = 'front_end.html';
}

export const STAGE_SIZE = 10;

function speakStage(text) {
  const settings = loadSettings();
  if (!settings.tts || !window.speechSynthesis || !text) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = settings.lang === 'EN' ? 'en-US' : 'ko-KR';
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utter);
}

export function createStageSession({ game, trackCombo = true, getMeta, onContinue, onHome }) {
  const size = STAGE_SIZE;
  let stage = 1;
  let correct = 0;
  let wrong = 0;
  let answered = 0;
  let bestCombo = 0;
  let accepting = false;
  let showing = false;
  let passedThisResult = false;

  const overlay = document.createElement('div');
  overlay.id = 'stage-result-overlay';
  overlay.className = 'fixed inset-0 z-[90] hidden items-center justify-center bg-slate-950/75 backdrop-blur-sm p-4';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-labelledby', 'stage-result-title');
  overlay.innerHTML = `
    <div class="glass-panel rounded-3xl p-6 sm:p-7 max-w-md w-full shadow-2xl flex flex-col gap-5 max-h-[90vh] overflow-y-auto">
      <div>
        <p id="stage-result-kicker" class="text-xs font-black uppercase tracking-wider text-indigo-600">스테이지 1</p>
        <h3 id="stage-result-title" class="text-2xl font-black text-slate-900 mt-1">학습 결과</h3>
        <p id="stage-result-summary" class="text-sm text-slate-600 font-semibold mt-2"></p>
      </div>
      <div id="stage-result-stats" class="grid grid-cols-2 gap-2.5"></div>
      <div class="flex flex-col gap-2">
        <button type="button" id="stage-btn-continue" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-black py-3 rounded-xl text-sm shadow-md">계속하기</button>
        <button type="button" id="stage-btn-home" class="w-full bg-white hover:bg-slate-50 text-slate-800 font-bold py-3 rounded-xl text-sm border border-slate-200">홈으로 돌아가기</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector('#stage-btn-continue').addEventListener('click', () => {
    overlay.classList.add('hidden');
    overlay.classList.remove('flex');
    showing = false;
    if (passedThisResult) {
      passedThisResult = false;
      if (typeof onHome === 'function') onHome();
      else goHub();
      return;
    }
    stage += 1;
    correct = 0;
    wrong = 0;
    answered = 0;
    bestCombo = 0;
    accepting = false;
    paint();
    if (typeof onContinue === 'function') onContinue();
  });

  overlay.querySelector('#stage-btn-home').addEventListener('click', () => {
    if (typeof onHome === 'function') onHome();
    else goHub();
  });

  function paint() {
    const el = document.getElementById('stage-progress');
    if (!el) return;
    let current = answered;
    if (!showing && accepting) current += 1;
    if (current < 1) current = 1;
    if (current > size) current = size;
    el.textContent = `스테이지 ${stage} · ${current}/${size}`;
  }

  function canAnswer() {
    return accepting && !showing;
  }

  function onAnswer(isCorrect, combo) {
    if (!canAnswer()) return { consumed: false, stageDone: false };
    accepting = false;
    answered += 1;
    if (isCorrect) {
      correct += 1;
      if (trackCombo && typeof combo === 'number' && combo > bestCombo) bestCombo = combo;
    } else {
      wrong += 1;
    }
    const meta = currentMeta();
    if (meta.unitId && meta.itemId) {
      recordItem({
        lang: meta.lang,
        unitId: meta.unitId,
        itemId: meta.itemId,
        skill: normalizeSkill(meta.skill, game),
        correct: !!isCorrect
      });
    }
    paint();
    return { consumed: true, stageDone: answered >= size };
  }

  function currentMeta() {
    return (typeof getMeta === 'function' ? getMeta() : {}) || {};
  }

  function allowNext() {
    if (showing) return;
    accepting = true;
    paint();
  }

  function showResult() {
    if (showing) return;
    showing = true;
    accepting = false;
    const meta = currentMeta();
    const accuracy = answered > 0 ? Math.round((correct / answered) * 100) : 0;
    const unitId = meta.unitId || '';
    const unitPassed = unitId
      ? saveSkillScore({
        lang: meta.lang,
        unitId,
        skill: meta.skill,
        game,
        correct,
        total: size
      })
      : false;
    passedThisResult = unitPassed;
    recordSession({
      game,
      lang: meta.lang,
      level: meta.level,
      score: correct,
      total: size
    });

    const met = sessionMet(correct, size);
    overlay.querySelector('#stage-result-kicker').textContent = unitPassed ? '단원 통과' : `스테이지 ${stage} 완료`;
    overlay.querySelector('#stage-result-title').textContent = unitPassed ? '단원 통과' : '학습 결과';
    let summary = `${size}문제 중 ${correct}문제를 맞혔습니다.`;
    if (unitPassed) summary += ' 허브로 돌아갑니다.';
    else if (unitId && met) summary += ' 읽기와 쓰기를 모두 마치면 통과합니다. 계속하기는 같은 단원을 다시 엽니다.';
    else if (unitId) summary += ' 기준에 못 미쳐 같은 단원을 다시 엽니다.';
    overlay.querySelector('#stage-result-summary').textContent = summary;

    const stats = [
      ['정답', `${correct} / ${size}`],
      ['오답', `${wrong}문제`],
      ['정답률', `${accuracy}%`]
    ];
    if (trackCombo) stats.push(['최고 콤보', `${bestCombo}`]);
    if (unitId) stats.push(['단원', unitPassed ? '통과' : '다시']);

    overlay.querySelector('#stage-result-stats').innerHTML = stats.map(([label, value]) => `
      <div class="bg-white/80 rounded-2xl border border-slate-200 p-3 text-center">
        <p class="text-[11px] font-bold text-slate-500">${label}</p>
        <p class="text-xl font-black text-slate-900 mt-0.5">${value}</p>
      </div>
    `).join('');

    overlay.classList.remove('hidden');
    overlay.classList.add('flex');
    const cont = overlay.querySelector('#stage-btn-continue');
    if (cont) {
      cont.textContent = unitPassed ? '허브로 돌아가기' : '계속하기';
      cont.focus();
    }
    const spoken = unitPassed
      ? `이 단원을 통과했습니다. ${size}문제 중 ${correct}문제를 맞혔습니다.`
      : `스테이지 ${stage} 학습 결과. ${size}문제 중 ${correct}문제를 맞혔습니다. 정답률 ${accuracy}퍼센트.`;
    speakStage(spoken);
  }

  paint();
  return { onAnswer, allowNext, showResult, canAnswer, paint, size };
}

export async function loadQuizBank() {
  const res = await fetch(new URL('quiz_bank.json', import.meta.url));
  if (!res.ok) throw new Error('quiz_bank.json');
  return res.json();
}

export function bankItems(bank, lang) {
  if (!bank) return [];
  const key = String(lang || 'KO').toUpperCase();
  const list = bank[key] || bank.KO || [];
  return Array.isArray(list) ? list : [];
}
