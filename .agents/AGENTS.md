# Jolly-Carson AI 코딩 규칙 (Rules)

## 1. 오답 분석 리포트 생성 파일명 규칙
- 사용자의 퀴즈 풀이 이력을 바탕으로 AI 오답 분석 리포트 HTML 파일을 생성할 때, 파일명은 반드시 생성 시점의 날짜를 결합한 **`diagnostics_report_YYMMDD.html`** 패턴을 준수해야 합니다.
  - 예시: 2026년 6월 29일에 생성 시 -> `diagnostics_report_260629.html`
- 파일 생성 경로는 `analytics/output/` 폴더 아래여야 합니다.
- 이 규칙은 학습 이력 대시보드(`history.js` 등)에서 비동기 fetch 통신으로 파일의 실제 존재 여부를 실시간으로 판별하여 버튼을 노출하는 논리와 유기적으로 결합되어 있습니다.
