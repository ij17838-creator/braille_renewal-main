/**
 * JSON 데이터 파일 위치표. 코드에서는 'ko.json'처럼 파일 이름만 쓰고,
 * 실제 위치(data/ko, data/en …)는 여기서만 정한다.
 */

const DATA_DIRS = {
  'ko.json': 'ko',
  'ko_marks.json': 'ko',
  'ko_number_rules.json': 'ko',
  'lexicon_ko.json': 'ko',
  'ko_rules.json': 'ko',
  'en_spell.json': 'en',
  'en_shortform.json': 'en',
  'en_contractions.json': 'en',
  'lexicon_en.json': 'en',
  'ueb_number_rules.json': 'en',
  'numbers.json': 'common',
  'curriculum.json': 'curriculum',
  'quiz_bank.json': 'curriculum'
};

export function dataUrl(name) {
  const dir = DATA_DIRS[name];
  if (!dir) throw new Error(`알 수 없는 데이터 파일: ${name}`);
  return new URL(`../../data/${dir}/${name}`, import.meta.url);
}
