# braille_renewal

한/영 점자 학습 프로그램입니다. HTML 게임(`web/`)과 파이썬 점역 엔진(`engine/`)이 같은 점자 규칙 데이터(`data/`)를 함께 씁니다.

## 폴더 구조

```
index.html               첫 화면 → web/front_end.html 로 이동
web/                     브라우저 게임
  front_end.html           허브(학습 언어·단원 선택)
  morpheme.html            형태소 & 낱말 퀴즈
  select.html              점자 카드 셀렉트
  builders.html            점자 빌더즈
  blank.html               점자 빈칸 수사대
  js/                      공용 스크립트 (shell, curriculum, quiz_combo, data_paths)
  css/                     공용 스타일 (mobile.css)
data/                    점자 규칙·학습 데이터 (JSON)
  ko/                      한글: ko, ko_marks, ko_number_rules, lexicon_ko
  en/                      영어(UEB): en_spell, en_shortform, en_contractions, lexicon_en, ueb_number_rules
  common/                  한/영 공통: numbers
  curriculum/              단원표·문제은행: curriculum, quiz_bank
engine/                  파이썬 점역 엔진
  data_paths.py            JSON 위치 찾기
  ko/                      한글 엔진: ko_parser, ko_syntax_analyzer, ko_generator
  en/                      영어 엔진: en_parser, en_syntax_analyzer
tests/                   엔진 테스트
tools/                   개발용 점검 스크립트
```

JSON 파일을 옮기거나 새로 추가할 때는 위치표 두 곳을 함께 고칩니다.

- 웹: `web/js/data_paths.js` 의 `DATA_DIRS`
- 파이썬: `engine/data_paths.py` 의 `DATA_SUBDIRS` (새 하위 폴더를 만들 때만)

## 실행

JSON을 `fetch`하므로 파일을 더블클릭하지 말고, **저장소 루트**에서 정적 서버를 켭니다. (`web/` 안에서 켜면 `data/`를 읽지 못합니다.)

```bash
python -m http.server 8000
```

브라우저에서 `http://localhost:8000` 으로 접속합니다.

점역 엔진 테스트 (저장소 루트에서):

```bash
python tests/run_p2_tests.py
python -m unittest tests.test_ko_rule_changes
```

엔진 모듈을 직접 실행할 때는 `-m` 으로 실행합니다.

```bash
python -m engine.ko.ko_generator
```
