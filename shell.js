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
  history: 'braille_global_history'
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
  LEGACY_KEYS.forEach((key) => localStorage.removeItem(key));
}

export function goHub() {
  window.location.href = 'front_end.html';
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
