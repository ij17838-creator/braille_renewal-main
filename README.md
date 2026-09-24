# braille_renewal

한/영 점자 학습 프로그램입니다. HTML 게임과 파이썬 점역 엔진이 프로젝트 루트에 함께 있습니다.

## 실행

브라우저에서 `index.html` 또는 `front_end.html`을 엽니다. JSON을 `fetch`하므로, 파일을 더블클릭하기보다 같은 폴더에서 간단한 정적 서버를 켜는 편이 안전합니다.

```bash
python -m http.server 8000
```

브라우저에서 `http://localhost:8000` 으로 접속합니다.

점역 엔진 스모크 테스트:

```bash
python run_p2_tests.py
```
