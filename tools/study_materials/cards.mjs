// 앱과 똑같은 학습 카드를 뽑아 JSON으로 내보낸다. 사용: node cards.mjs <단원id>
import { readFileSync } from 'node:fs';
import { cardsFor, unitById } from '../../web/js/curriculum.js';
import { dataUrl } from '../../web/js/data_paths.js';

const names = ['ko.json', 'ko_marks.json', 'numbers.json', 'en_spell.json', 'en_shortform.json', 'en_contractions.json', 'ueb_number_rules.json'];
const data = Object.fromEntries(names.map((n) => [n, JSON.parse(readFileSync(dataUrl(n), 'utf8'))]));
const unit = unitById(process.argv[2]);
if (!unit) throw new Error(`단원 없음: ${process.argv[2]}`);
process.stdout.write(JSON.stringify(cardsFor(unit, data)));
