# jolly-carson 인수/준비 메모 (Copilot)

## 1) 현재 저장소 상태
- 브랜치: master (origin/master 추적)
- 최근 커밋(최신순):
  - 79e9c49: check-report API 추가
  - 2a0a92a: 상세 분석 모달 캐시 무효화
  - 5dd703a: 과목별 평균 시간/취약 과목 진단
- 작업트리 변경 파일(미커밋):
  - reports/Learning_History/history.js
  - reports/Learning_History/lhistory.html

## 2) 런타임/의존성 상태
- 로컬 가상환경 확인: .venv 존재 (Python 3.13.2)
- requirements 설치 상태: 모두 설치됨 (재설치 없이 충족)
- 핵심 import 점검: Flask, psycopg2, fitz(PyMuPDF), pdfplumber 정상

## 3) DB 동작 확인 결과 (중요)
- 기본 동작: POSTGRES
- 기본 DB 연결 테스트: 실패
  - 원인: 외부 Supabase 연결 중 네트워크 단절(OperationalError)
- 로컬 강제 SQLite 모드: 성공
  - USE_SQLITE=true 설정 시 SQLite 연결 정상

## 4) 바로 작업 시작 명령
PowerShell 기준:

```powershell
Set-Location "e:\VS_WORKSPACE\jolly-carson"
$env:USE_SQLITE = "true"
.\.venv\Scripts\python.exe server.py
```

브라우저 확인:
- http://localhost:8000
- DB 모드 확인 API: http://localhost:8000/api/db-mode

## 5) 인수 시 주의 포인트
- server.py에 Supabase 접속 문자열이 코드에 하드코딩되어 있음.
- 로컬 개발은 반드시 USE_SQLITE=true 권장.
- 향후 정리 권장:
  1. DB 접속 정보는 환경변수로만 주입
  2. .env(.env.example) 기반 설정 분리
  3. 로컬 기본 DB를 SQLite로 되돌려 개발 안정성 확보

## 6) 다음 작업 우선순위 제안
1. 미커밋 2개 파일 변경 의도 확인 및 분리 커밋
2. DB 설정 리팩터링(하드코딩 제거)
3. API 기본 스모크 테스트 스크립트 추가
4. 분석 리포트 생성/노출 플로우(check-report 포함) 회귀 점검
