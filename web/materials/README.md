# 단원 학습자료

게임 전에 받는 단원별 학습자료(한글 파일 .hwpx, PDF)를 둔다.

- 파일 이름은 단원 id를 쓴다. 예) `ko/ko-dots.hwpx`, `ko/ko-dots.pdf`. 만드는 방법은 `tools/study_materials/README.md`.
- 로비의 「학습자료 받기」 버튼은 모든 단원에서 같은 자리에 있다. `data/curriculum/curriculum.json`의 해당 단원에 `materials`를 적으면 버튼이 켜지고, 없으면 「준비 중」으로 보인다.

```json
"materials": {
  "hwpx": "materials/ko/ko-dots.hwpx",
  "pdf": "materials/ko/ko-dots.pdf"
}
```

경로는 `web/` 폴더 기준이다. 받을 때 파일 이름은 로비가 `한글점자_1단원_점의자리.hwpx`처럼 정해 준다.
