# -*- coding: utf-8 -*-
"""
[Flask 기반 다중 과목 통합 예상문제 웹 서버]
- 작성 목적: 수험생이 웹 브라우저를 통해 PM, SE, DB, SA, SC 5대 과목의 예상문제를 풀고, 
  누적 정답률 분석을 통해 즉각적인 처방(출제 범위 및 학습 팁)을 받을 수 있게 돕는 통합 웹 서비스 백엔드입니다.
- 설계 원칙:
  1. 외부 SDK 의존 없이 urllib 표준 라이브러리를 사용하여 Gemini 2.5-flash 모델과 연동합니다.
  2. 오프라인이나 API 장애 발생 시 미리 구축한 mock_quizzes.json에서 즉각 로드하는 하이브리드 안정성을 확보합니다.
  3. 모든 파일 I/O는 UTF-8 인코딩을 지정하여 Windows 시스템 환경에서의 인코딩 크래시를 원천 차단합니다.
"""

import os
import sys
import json
import re
import hashlib
import urllib.request
import urllib.error
from datetime import datetime
from flask import Flask, jsonify, request, render_template, send_from_directory

app = Flask(__name__, template_folder="templates", static_folder="static")

# ==========================================
# 1. 파일 경로 및 환경 설정
# ==========================================
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HISTORY_PATH = os.path.join(DATA_DIR, "quiz_history.json")
MOCK_QUIZ_PATH = os.path.join(DATA_DIR, "mock_quizzes.json")
AUTH_PROPERTIES_PATH = os.path.join(DATA_DIR, "auth.properties")

# 과목 코드와 한글 과목명 매핑
SUBJECT_MAP = {
    "PM": "프로젝트관리 및 감리",
    "SE": "소프트웨어공학",
    "DB": "데이터베이스",
    "SA": "시스템구조",
    "SC": "보안"
}

# 각 단원별 핵심 보강 팁 매핑
REMEDY_TIPS = {
    # PM (사업관리)
    "1. 정보화 및 소프트웨어 관련 법/제도 및 국내외 지침, 가이드": "소프트웨어 진흥법 상의 중소기업 참여제한 예외 요건, 지능정보화 기본법의 국가정보화 기본 계획 수립 주체 및 공공데이터 표준화 지침을 대조 학습하세요.",
    "2. 감리 관련 법제도 및 관련 기술": "전자정부법상 의무감리 대상 기준(5억 이상 SW개발 등) 및 정보시스템 감리기준의 감리인 수행 규격, 의견 진술서 처리 기한을 숙지하십시오.",
    "3. 조직 관리론": "허즈버그의 동기-위생 이론, 맥그리거 X-Y이론, 매슬로우 욕구단계설 등 인적자원 관리이론의 동기 요인들을 구분하여 학습해 두어야 합니다.",
    "4. 프로젝트 관리": "임계경로(Critical Path) 계산에서 여유시간(Float) 분석 기법과 PMBOK 7판의 12대 프로젝트 관리 원칙 및 8대 성과 도메인의 정의를 철저히 매핑해 두세요.",
    
    # SE (소프트웨어공학)
    "1. 요구사항분석 및 설계": "요구사항 추적성 매트릭스 구성 요소와 SOLID 설계 원칙(특히 LSP, ISP) 및 GoF 디자인 패턴(생성/구조/행위)의 구체적 활용 매칭을 복습하세요.",
    "2. 구현 및 테스트": "화이트박스 테스트 기법 중 분기/조건/결정 조건 커버리지를 계산하는 연산식과 ISO/IEC/IEEE 29119 표준에 따른 테스트 레벨 산출물을 암기하십시오.",
    "3. 유지관리 및 운영": "형상 통제 위원회(CCB)의 승인 프로세스, ITSM/ITIL 4의 서비스 가치 체계(SVS) 및 리팩토링과 재공학의 개념적 차이를 명확히 하세요.",
    "4. 개발방법론, sw 구조 및 공개sw": "스크럼의 3가지 산출물(제품 백로그, 스프린트 백로그, 증가분)과 MSA(마이크로서비스 아키텍처)의 패턴(API 게이트웨이, 서킷 브레이커)을 재정리하십시오.",
    "5. SW 품질 및 비용산정": "기능점수(FP) 산정 시 데이터 기능점수(ILF, EIF)와 트랜잭션 기능점수(EI, EO, EQ)의 산정 기준 가이드를 암기하고 직접 계산하는 기출을 풀어보세요.",

    # DB (데이터베이스)
    "1. DB개념 및 설계": "제3정규형(3NF)에서 BCNF, 제4정규형(4NF), 제5정규형(5NF)으로 가기 위한 종속성 특징(이행적 함수 종속 제거, 모든 결정자가 후보키, 다치종속 제거)을 완벽히 정리하세요.",
    "2. DB언어": "관계대수의 순수 관계 연산자(Select, Project, Join, Division)와 일반 집합 연산자를 SQL 쿼리와 매핑하여 상호 변환하는 연습을 반복해야 합니다.",
    "3. DBMS 기술": "트랜잭션 ACID 특성, 회복 기법(REDO/UNDO, 즉시/지연 갱신), 동시성 제어(2단계 잠금 규약의 교착상태 리스크) 동작 원리를 파헤쳐야 합니다.",
    "4. DB응용": "공공데이터 연동 표준 포맷(XML, JSON)과 REST API 아키텍처 규칙(Stateless, Uniform Interface) 및 분산 DBMS의 투명성 4가지 요건을 정리하십시오.",
    "5. 빅데이터 및 AI데티어": "NoSQL의 CAP 이론 분류(CP, AP, CA)와 데이터웨어하우스(DW) 스키마(스타, 스노우플레이크) 및 AI 학습 데이터 수집 가이드라인을 암기하세요.",

    # SA (시스템구조)
    "1. 공통기술": "정보기술 아키텍처(EA)의 5대 참조 모델(업무, 서비스, 데이터, 기술, 성과)의 목적 및 상호운용성 기술 표준(TRM/SP) 관계를 복습해 두어야 합니다.",
    "2. 아키텍처 설계 및 구축": "RAID 레벨별(0, 1, 5, 6, 10) 디스크 효율 및 패리티 저장 기법과 고가용성 액티브-액티브 이중화 및 재해복구(DRS)의 복구목표시간(RTO/RPO)을 비교 정리하세요.",
    "3. 데이터 통신 및 네트워크 설계": "OSI 7계층 프로토콜 매핑, IPv4와 IPv6 헤더 구조의 주요 필드 차이점 및 TCP 혼잡 제어(Slow Start, 혼잡 회피) 동작 메커니즘을 상세히 공부하세요.",
    "4. 기타 신기술": "클라우드 서비스 모델(IaaS, PaaS, SaaS)의 책임 한계선 분기점 및 컨테이너 가상화(Docker)와 하이퍼바이저 방식의 성능 구조 차이를 암기하십시오.",

    # SC (보안)
    "1. 공통 보안 기술": "대칭키(블록/스트림)와 비대칭키(RSA, ECC)의 연산 속도 및 키 관리 특징, 암호학적 해시 함수의 충돌 저항성 개념을 비교 숙지해야 합니다.",
    "2. 네트워크 및 시스템 보안": "침입방지시스템(IPS)과 방화벽의 패킷 필터링 범위 차이, 망분리 기술(물리적/논리적-SBC, CBC) 및 SQL 인젝션/XSS 해킹 메커니즘을 파악하세요.",
    "3. 응용 및 신기술 보안": "OAuth 2.0 권한 획득 프레임워크 동작 절차, DRM 유통 패키징 구조 및 공공 클라우드 보안인증제도(CSAP) 등급별 기준을 상세 대조하십시오.",
    "4. 개발 및 운영 보안": "SW 개발보안(시큐어 코딩) 7대 취약점 영역(입력데이터 검증 및 표현, 보안기능, 시간 및 상태 등) 가이드라인 준수 기법을 코드 관점에서 정리하세요.",
    "5. 정보보호 법규 및 개인정보보호": "개인정보 보호법상 고유식별정보의 종류 및 동의 획득 절차, 가명정보와 익명정보의 활용 제한 범위 및 ISMS-P 인증 기준을 비교 숙지하십시오."
}

# ==========================================
# 2. 유틸리티 함수 및 비즈니스 로직
# ==========================================

def get_scope_details(subject, category):
    """
    [설계 의도]
    지정된 과목의 txt 파일(예: SE.txt)을 열고, 
    해당 취약 카테고리가 시작되는 라인부터 다음 대단원이 시작되는 라인 전까지를 슬라이싱하여 반환합니다.
    """
    scope_file = os.path.join(DATA_DIR, "exam_scopes", f"{subject}.txt")
    if not os.path.exists(scope_file):
        return "상세 시험 범위 규격서가 로드되지 않았습니다."

    scope_details = ""
    try:
        with open(scope_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            in_target = False
            for line in lines:
                # 타겟 단어 검색 (카테고리 번호와 매칭, 예: "3. 유지관리 및 운영")
                if line.strip().startswith(category):
                    in_target = True
                    scope_details += line
                    continue
                # 다음 번호 대단원("4. ...", "5. ...")을 발견하면 파싱 중단
                if in_target and re.match(r"^\d+\.", line.strip()):
                    break
                if in_target:
                    scope_details += line
        return scope_details.strip()
    except Exception as e:
        return f"시험 범위를 추출하는 중 오류가 발생했습니다: {e}"


def load_quiz_history():
    """
    [설계 의도]
    기존에 누적된 풀이 데이터를 data/quiz_history.json 파일에서 안전하게 로드합니다.
    파일이 없거나 손상되었을 시 빈 리스트 구조를 리턴하여 예외를 방지합니다.
    """
    if not os.path.exists(HISTORY_PATH):
        return {"attempts": []}
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"attempts": []}


def save_quiz_history(history):
    """
    [설계 의도]
    사용자의 풀이 데이터를 누적한 뒤 파일로 디스크에 영속 저장합니다.
    """
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def call_gemini_api(prompt):
    """
    [설계 의도]
    외부 SDK에 의존하지 않고 Python 내장 urllib 모듈만을 사용하여 
    Gemini 2.5-flash 모델의 API 포인트를 호출하고 원시 텍스트 결과를 가공합니다.
    """
    if not GEMINI_API_KEY:
        raise ValueError("API Key가 누락되었습니다.")

    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=15) as res:
        response_data = json.loads(res.read().decode("utf-8"))
        raw_text = response_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Markdown Fences가 씌워져서 응답이 올 경우 정제 처리
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()
            
        return json.loads(raw_text)


# ==========================================
# 3. HTTP 라우트 및 API 정의
# ==========================================

@app.route("/")
def index():
    """메인 Single Page Application(SPA)의 HTML 템플릿을 서빙합니다."""
    return render_template("index.html")


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """
    [설계 의도]
    각 과목별 누적 진행도, 정답률을 계산하고, 가장 성적이 나쁜 취약 대단원을 판별하여
    RAG 범위와 학습 보강 처방을 포함한 종합 대시보드 데이터를 리턴합니다.
    """
    history = load_quiz_history()
    attempts = history.get("attempts", [])

    # 과목별 데이터 구조 초기화
    subject_stats = {}
    for code, name in SUBJECT_MAP.items():
        subject_stats[code] = {
            "name": name,
            "total_solved": 0,
            "correct_solved": 0,
            "rate": 100.0,  # 초기 정답률 기본값
            "chapter_stats": {}  # 세부 단원별 집계
        }

    # 누적 이력 분석 루프
    for att in attempts:
        quiz_id = att.get("quiz_id", "")
        # quiz_id 포맷: "PM_MOCK_01" 또는 "SE_AUTO_01" 등에서 과목 코드 파싱
        sub_code = quiz_id.split("_")[0] if "_" in quiz_id else "SE"
        if sub_code not in SUBJECT_MAP:
            continue
            
        category = att.get("category", "")
        is_correct = att.get("is_correct", False)

        sub_data = subject_stats[sub_code]
        sub_data["total_solved"] += 1
        if is_correct:
            sub_data["correct_solved"] += 1

        # 세부 단원별 통계
        if category:
            if category not in sub_data["chapter_stats"]:
                sub_data["chapter_stats"][category] = {"total": 0, "correct": 0}
            sub_data["chapter_stats"][category]["total"] += 1
            if is_correct:
                sub_data["chapter_stats"][category]["correct"] += 1

    # 과목별 최종 정답률 산정
    for code, info in subject_stats.items():
        if info["total_solved"] > 0:
            info["rate"] = round((info["correct_solved"] / info["total_solved"]) * 100, 1)

    # 전체를 통틀어 '정답률이 100% 미만'이고 가장 심각하게 낮은 '취약 대단원'을 진단
    weakest_subject = None
    weakest_category = None
    min_rate = 1.0  # 100% 기준 비교를 위해 소수점으로 변환

    for code, info in subject_stats.items():
        for cat, data in info["chapter_stats"].items():
            rate = data["correct"] / data["total"]
            # 100%보다 낮으면서 기존 최솟값보다 더 낮을 때 갱신
            if rate < min_rate:
                min_rate = rate
                weakest_subject = code
                weakest_category = cat

    # 처방 데이터 빌드
    remedy_data = None
    if weakest_category:
        scope_text = get_scope_details(weakest_subject, weakest_category)
        tip_text = REMEDY_TIPS.get(weakest_category, "이 단원의 개념을 심도 있게 짚고 기출문제를 반복 풀이하세요.")
        remedy_data = {
            "subject_code": weakest_subject,
            "subject_name": SUBJECT_MAP[weakest_subject],
            "category": weakest_category,
            "rate": round(min_rate * 100, 1),
            "scope_details": scope_text,
            "tip": tip_text
        }

    return jsonify({
        "overall_solved": len(attempts),
        "overall_correct": sum(1 for a in attempts if a.get("is_correct", False)),
        "subjects": subject_stats,
        "remedy": remedy_data
    })


@app.route("/api/stats/reset", methods=["POST"])
def reset_stats():
    """
    [설계 의도]
    기존의 모든 풀이 히스토리를 깔끔하게 제거하여 수험생이 다시 공부를 시작할 수 있게 리셋을 지원합니다.
    """
    empty_history = {"attempts": []}
    if save_quiz_history(empty_history):
        return jsonify({"success": True, "message": "학습 이력이 성공적으로 초기화되었습니다."})
    return jsonify({"success": False, "message": "이력 초기화 중 오류가 발생했습니다."}), 500


@app.route("/reports/<path:filename>")
def serve_reports(filename):
    """
    [설계 의도]
    E 드라이브의 reports/ 폴더 내에 빌드된 5대 과목 프리미엄 대시보드 HTML 파일을 
    웹 서버 환경(http://localhost:5000/reports/...)에서도 정상적으로 조회할 수 있도록 서빙합니다.
    """
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    return send_from_directory(reports_dir, filename)


def get_exam_category_heuristic(subject, question_text):
    """
    [설계 의도]
    기출문제 질문 속의 핵심 키워드를 스캔하여 과목별 공식 대단원(1~5장) 중 
    가장 관련도(매칭 스코어)가 높은 대단원 명칭을 반환하여 통계 및 처방 연동의 무결성을 지킵니다.
    """
    subject_chapters = {
        "PM": [
            "1. 정보화 및 소프트웨어 관련 법/제도 및 국내외 지침, 가이드",
            "2. 감리 관련 법제도 및 관련 기술",
            "3. 조직 관리론",
            "4. 프로젝트 관리"
        ],
        "SE": [
            "1. 요구사항분석 및 설계",
            "2. 구현 및 테스트",
            "3. 유지관리 및 운영",
            "4. 개발방법론, sw 구조 및 공개sw",
            "5. SW 품질 및 비용산정"
        ],
        "DB": [
            "1. DB개념 및 설계",
            "2. DB언어",
            "3. DBMS 기술",
            "4. DB응용",
            "5. 빅데이터 및 AI데티어"
        ],
        "SA": [
            "1. 공통기술",
            "2. 아키텍처 설계 및 구축",
            "3. 데이터 통신 및 네트워크 설계",
            "4. 기타 신기술"
        ],
        "SC": [
            "1. 공통 보안 기술",
            "2. 네트워크 및 시스템 보안",
            "3. 응용 및 신기술 보안",
            "4. 개발 및 운영 보안",
            "5. 정보보호 법규 및 개인정보보호"
        ]
    }
    
    chapters = subject_chapters.get(subject, [])
    if not chapters:
        return "기타 공통영역"
        
    chapter_keywords = {
        "PM": {
            0: ["법", "제도", "지침", "가이드", "고시", "진흥법", "계약", "대기업", "조달"],
            1: ["감리", "전자정부법", "감리기준", "감리원", "수행"],
            2: ["허즈버그", "동기", "위생", "맥그리거", "매슬로우", "인적", "조직", "리더십"],
            3: ["일정", "임계", "경로", "wbs", "pmbok", "여유시간", "float", "원칙", "위험", "원가"]
        },
        "SE": {
            0: ["요구", "분석", "명세", "추적", "객체지향", "설계", "uml", "sysml", "다이어그램", "패턴", "solid", "리스코프"],
            1: ["테스트", "검증", "커버리지", "구문", "분기", "조건", "결정", "29119", "웹접근성", "화이트박스", "블랙박스", "코딩"],
            2: ["유지보수", "유지관리", "형상", "itsm", "itil", "sla", "slm", "재사용", "재공학", "역공학", "리팩토링", "refactoring"],
            3: ["방법론", "애자일", "agile", "스크럼", "scrum", "스프린트", "데브옵스", "devops", "클린 아키텍처", "msa", "마이크로서비스", "프레임워크", "스프링", "soap", "rest", "오픈소스"],
            4: ["품질", "비용", "산정", "cmmi", "spice", "25010", "12207", "기능점수", "fp", "cocomo", "loc"]
        },
        "DB": {
            0: ["정규화", "정규형", "릴레이션", "erd", "모델", "키", "종속", "bcnf", "후보키"],
            1: ["sql", "쿼리", "관계대수", "조인", "join", "select", "project", "division"],
            2: ["트랜잭션", "acid", "회복", "동시성", "제어", "락킹", "locking", "교착", "2단계", "격리"],
            3: ["xml", "json", "rest", "공공데이터", "분산", "투명성"],
            4: ["nosql", "cap", "하두프", "dw", "마이닝", "빅데이터", "ai", "학습"]
        },
        "SA": {
            0: ["ea", "참조", "trm", "srm", "brm", "drm", "정보기술", "아키텍처"],
            1: ["raid", "디스크", "가용성", "재해복구", "drs", "rto", "rpo", "백업", "이중화", "패리티"],
            2: ["네트워크", "프로토콜", "라우팅", "routing", "ip", "ipv6", "tcp", "혼잡", "osi", "arp", "icmp"],
            3: ["클라우드", "iaas", "paas", "saas", "컨테이너", "가상화", "docker", "도커"]
        },
        "SC": {
            0: ["대칭키", "비대칭키", "rsa", "seed", "aes", "암호", "해시", "sha-256", "서명", "인증", "pki"],
            1: ["방화벽", "firewall", "ips", "침입", "vpn", "망분리", "인젝션", "xss", "취약점", "보안"],
            2: ["oauth", "drm", "ssl", "tls", "클리어링", "라이선스", "csap"],
            3: ["시큐어", "코딩", "개발보안", "취약점", "7대", "행안부"],
            4: ["개인정보", "보호법", "가명", "익명", "비식별", "isms-p", "고유식별"]
        }
    }
    
    txt = question_text.lower()
    subject_map = chapter_keywords.get(subject, {})
    
    best_chapter_idx = 0
    max_matches = 0
    
    for idx, keywords in subject_map.items():
        matches = sum(1 for kw in keywords if kw.lower() in txt)
        if matches > max_matches:
            max_matches = matches
            best_chapter_idx = idx
            
    return chapters[best_chapter_idx]


def extract_single_past_exam(year, num):
    """
    [설계 의도]
    기출 PDF 텍스트에서 특정 연도/문제번호의 지문을 찾아내고 Gemini API로 구조화한 뒤 캐시하고 반환합니다.
    """
    db_key = f"{year}_{num}"
    
    # 1. 캐시 DB 먼저 로드
    db_data = {}
    if os.path.exists(PAST_EXAMS_DB_PATH):
        try:
            with open(PAST_EXAMS_DB_PATH, "r", encoding="utf-8") as f:
                db_data = json.load(f)
                if db_key in db_data:
                    return db_data[db_key]
        except Exception:
            pass
            
    # 2. 실시간 파싱 시도
    exam_dir = os.path.join(DATA_DIR, "past_exams")
    target_pdf = None
    if os.path.exists(exam_dir):
        for file in os.listdir(exam_dir):
            if file.endswith(".pdf") and (str(year) in file):
                target_pdf = file
                break
                
    if not target_pdf or not GEMINI_API_KEY:
        raise ValueError(f"기출 PDF를 찾을 수 없거나 Gemini API Key가 없습니다. (연도: {year})")
        
    pdf_path = os.path.join(exam_dir, target_pdf)
    import parser
    
    full_text = parser.extract_pdf(pdf_path)
    
    num_int = int(num)
    pattern = rf"\b{num_int}\s*\.(.*?)(?=\b{num_int + 1}\s*\.|$)"
    match = re.search(pattern, full_text, re.DOTALL)
    
    chunk = ""
    if match:
        chunk = match.group(0).strip()
    else:
        pattern_alt = rf"\n\s*{num_int}\s+(.*?)(?=\n\s*{num_int + 1}\s+|$)"
        match_alt = re.search(pattern_alt, full_text, re.DOTALL)
        if match_alt:
            chunk = match_alt.group(0).strip()
            
    if not chunk or len(chunk) < 10:
        raise ValueError(f"PDF에서 {year}년 {num}번 문항의 텍스트 슬라이싱에 실패했습니다.")
        
    prompt = f"""
다음 텍스트는 {year}년 정보시스템 감리사 기출문제 중 일부({num_int}번 문항)입니다.
텍스트에서 문제 질문 본문, 4개의 보기 지문, 정답(1~4번 중 하나)을 추적 및 추출하여 
반드시 아래 JSON 규격으로만 응답해 주세요. 마크다운 기호(```json)는 절대 덧붙이지 마십시오.

[기출문제 원문 텍스트]
{chunk}

[응답 JSON 스키마]
{{
  "year": {year},
  "num": {num_int},
  "question": "추출한 문제 질문 지문...",
  "options": [
    "1. 보기 1...",
    "2. 보기 2...",
    "3. 보기 3...",
    "4. 보기 4..."
  ],
  "answer": 정답번호(정수형 1~4),
  "explanation": "해당 기출문제 정답의 간략한 근거 해설"
}}
"""
    parsed_quiz = call_gemini_api(prompt)
    
    db_data[db_key] = parsed_quiz
    save_past_exams_db(db_data)
    
    return parsed_quiz


@app.route("/api/quiz/<subject>", methods=["GET"])
def get_quiz(subject):
    """
    [설계 의도]
    요청된 과목(PM, SE, DB, SA, SC)의 12개년 기출문제(총 300문항 범위) 중 무작위 5문항을 추출하여 제공합니다.
    1단계: 기출 캐시 DB(past_exams_db.json)에서 해당 과목 범위 문항들을 무작위 추출하되,
    2단계: 캐시가 부족하거나 새로운 문항 출제를 위해 실시간 PDF 파싱(extract_single_past_exam)을 병행 시도합니다.
    3단계: Gemini API 장애나 오프라인 상태일 경우, data/mock_quizzes.json에서 즉각 로드하는 Fallback(이중 방어막)을 작동시킵니다.
    """
    subject = subject.upper()
    if subject not in SUBJECT_MAP:
        return jsonify({"error": "존재하지 않는 과목 코드입니다."}), 400

    # 과목별 기출문제 번호 범위 정의
    subject_ranges = {
        "PM": (1, 25),
        "SE": (26, 50),
        "DB": (51, 75),
        "SA": (76, 100),
        "SC": (101, 120)  # 감리사 보안 과목은 일반적으로 120번까지임
    }
    
    start_num, end_num = subject_ranges.get(subject, (26, 50))
    years = list(range(2015, 2027)) # 2015년 ~ 2026년 (12개년)
    
    # 전체 300문항(또는 보안의 경우 240문항)의 후보 목록 생성
    candidate_keys = []
    for y in years:
        for n in range(start_num, end_num + 1):
            candidate_keys.append((y, n))
            
    import random
    # 중복되지 않게 5개 조합을 무작위 셔플하여 선택 후보 생성
    random.shuffle(candidate_keys)
    
    quizzes = []
    
    # 로컬 기출 캐시 DB 먼저 로드
    db_data = {}
    if os.path.exists(PAST_EXAMS_DB_PATH):
        try:
            with open(PAST_EXAMS_DB_PATH, "r", encoding="utf-8") as f:
                db_data = json.load(f)
        except Exception:
            pass

    # 후보들 중 5문항을 확보할 때까지 루프
    for year, num in candidate_keys:
        if len(quizzes) >= 5:
            break
            
        db_key = f"{year}_{num}"
        quiz_item = None
        
        # 1. 로컬 캐시 DB에 존재하면 바로 가져옴
        if db_key in db_data:
            # 원본 데이터가 변경되지 않도록 깊은 복사 혹은 딕셔너리 재할당
            quiz_item = dict(db_data[db_key])
            # 캐시 데이터에 id가 없을 수 있으므로 보정
            if "id" not in quiz_item:
                quiz_item["id"] = db_key
            # category가 없거나 올바르지 않으면 헤리스틱으로 매핑
            if "category" not in quiz_item or not quiz_item["category"]:
                quiz_item["category"] = get_exam_category_heuristic(subject, quiz_item.get("question", ""))
            quizzes.append(quiz_item)
            continue
            
        # 2. 캐시에 없으면 Gemini API 실시간 RAG 추출 시도 (API 키가 있는 경우만)
        if GEMINI_API_KEY:
            try:
                # 단일 문항 RAG 추출
                parsed = extract_single_past_exam(year, num)
                if parsed:
                    parsed_copy = dict(parsed)
                    parsed_copy["id"] = db_key
                    parsed_copy["category"] = get_exam_category_heuristic(subject, parsed_copy.get("question", ""))
                    quizzes.append(parsed_copy)
                    continue
            except Exception as e:
                # 실시간 파싱 에러 시 로그 출력 후 다음 후보로 넘어가거나 Mock 폴백 처리
                print(f"[경고] {year}년 {num}번 기출 실시간 파싱 실패: {e}")
                
    # 만약 RAG 추출 실패나 캐시 부족으로 5문항을 못 채웠다면, 캐시된 전체 문항 중에서 중복되지 않게 무작위 수급
    if len(quizzes) < 5:
        cached_subject_quizzes = []
        for key, val in db_data.items():
            try:
                k_year, k_num = map(int, key.split("_"))
                if start_num <= k_num <= end_num:
                    val_copy = dict(val)
                    val_copy["id"] = key
                    if "category" not in val_copy or not val_copy["category"]:
                        val_copy["category"] = get_exam_category_heuristic(subject, val_copy.get("question", ""))
                    cached_subject_quizzes.append(val_copy)
            except Exception:
                continue
                
        # 캐시된 것들 중에서 채움
        for item in cached_subject_quizzes:
            if len(quizzes) >= 5:
                break
            if item["id"] not in [q["id"] for q in quizzes]:
                quizzes.append(item)
                
    # 그럼에도 5문항을 못 채웠다면 최종 보루로 mock_quizzes.json에서 무작위 추출하여 Fallback
    if len(quizzes) < 5:
        print(f"[알림] 기출문제 데이터가 부족하여 {subject} 과목의 로컬 Mock 문제로 Fallback합니다.")
        if os.path.exists(MOCK_QUIZ_PATH):
            try:
                with open(MOCK_QUIZ_PATH, "r", encoding="utf-8") as f:
                    mock_data = json.load(f)
                    mock_list = mock_data.get(subject, [])
                    # 부족한 개수만큼 mock에서 채움
                    random.shuffle(mock_list)
                    for item in mock_list:
                        if len(quizzes) >= 5:
                            break
                        item_copy = dict(item)
                        if item_copy.get("id") not in [q.get("id") for q in quizzes]:
                            quizzes.append(item_copy)
            except Exception as e:
                print(f"[오류] Mock 파일 읽기 에러: {e}")
                
    # 최종 퀴즈 구성 완료
    if len(quizzes) >= 5:
        # 반환 포맷을 맞추어 준다
        return jsonify({"quizzes": quizzes[:5], "source": "PAST_EXAM_RAG"})
        
    return jsonify({"error": "기출문제 및 예상문제를 로드하지 못했습니다."}), 500


@app.route("/api/quiz/submit", methods=["POST"])
def submit_quiz():
    """
    [설계 의도]
    사용자가 웹 화면에서 제출한 각 문항의 답안 리스트를 접수받아 채점 결과를 집계하고,
    풀이 이력 DB(quiz_history.json)에 기록하여 대시보드 상태를 동적 업데이트하도록 연동합니다.
    """
    data = request.get_json() or {}
    answers = data.get("answers", [])  # 구조: [{"quiz_id": "SE_MOCK_01", "category": "...", "user_answer": 3, "correct_answer": 3}]

    if not answers:
        return jsonify({"success": False, "message": "채점할 답안 내역이 전달되지 않았습니다."}), 400

    new_attempts = []
    correct_count = 0
    
    for ans in answers:
        user_ans = ans.get("user_answer")
        correct_ans = ans.get("correct_answer")
        is_correct = (user_ans == correct_ans)
        
        if is_correct:
            correct_count += 1

        new_attempts.append({
            "quiz_id": ans.get("quiz_id"),
            "category": ans.get("category"),
            "user_answer": user_ans,
            "is_correct": is_correct,
            "timestamp": datetime.now().isoformat()
        })

    # 누적 기록 로드 및 병합 저장
    history = load_quiz_history()
    history["attempts"].extend(new_attempts)
    save_quiz_history(history)

    return jsonify({
        "success": True,
        "total_items": len(answers),
        "correct_items": correct_count,
        "message": f"총 {len(answers)}문항 중 {correct_count}문항 정답 처리 완료."
    })


# ==========================================
# 3-1. 기출문제 원본 및 유사기출 연동 API
# ==========================================
PAST_EXAMS_DB_PATH = os.path.join(DATA_DIR, "past_exams_db.json")

@app.route("/api/exam/pdf/<filename>", methods=["GET"])
def get_exam_pdf(filename):
    """
    [설계 의도]
    기출 원본 PDF 파일을 브라우저에서 직접 열람하거나 다운로드할 수 있도록 정적 서빙합니다.
    """
    exam_dir = os.path.join(DATA_DIR, "past_exams")
    return send_from_directory(exam_dir, filename)


@app.route("/api/exam/query", methods=["GET"])
def query_past_exam():
    """
    [설계 의도]
    사용자가 '2025년 기출 55번 유사' 텍스트를 클릭하면, 연도와 문항 번호를 파싱해 기출문제를 조회합니다.
    1단계: past_exams_db.json 에 이미 로드되어 있는 문제이면 즉시 리턴 (Mock 맵핑 100% 처리).
    2단계: 온라인 상태인 경우, data/past_exams 내의 연도 매칭 PDF 텍스트에서 해당 문항 부근을 
           정규식으로 슬라이싱하여 Gemini API에 연동해 정형 JSON을 획득하고 캐시 보관.
    3단계: 모두 실패 시 PDF 다운로드/보기 링크를 폴백으로 전달하여 수험 흐름 유지.
    """
    year = request.args.get("year", "").strip()
    num = request.args.get("num", "").strip()

    if not year or not num:
        return jsonify({"success": False, "message": "연도(year)와 문항 번호(num) 정보가 부족합니다."}), 400

    db_key = f"{year}_{num}"

    # 1단계: 로컬 기출 캐시 DB 조회
    if os.path.exists(PAST_EXAMS_DB_PATH):
        try:
            with open(PAST_EXAMS_DB_PATH, "r", encoding="utf-8") as f:
                db_data = json.load(f)
                if db_key in db_data:
                    return jsonify({
                        "success": True,
                        "data": db_data[db_key],
                        "source": "LOCAL_CACHE"
                    })
        except Exception as e:
            print(f"[경고] 기출 DB 캐시 로드 오류: {e}")

    # 2단계: AI 실시간 기출 원문 RAG 파싱 및 복원
    exam_dir = os.path.join(DATA_DIR, "past_exams")
    target_pdf = None
    if os.path.exists(exam_dir):
        for file in os.listdir(exam_dir):
            if file.endswith(".pdf") and (year in file):
                target_pdf = file
                break

    if target_pdf and GEMINI_API_KEY:
        try:
            pdf_path = os.path.join(exam_dir, target_pdf)
            import parser  # 기존 파일 파서 연동
            
            # PDF 전체 텍스트 수집
            full_text = parser.extract_pdf(pdf_path)
            
            # 정규식을 이용해 해당 문항 슬라이싱 (예: 55. 부터 56. 전까지)
            num_int = int(num)
            pattern = rf"\b{num_int}\s*\.(.*?)(?=\b{num_int + 1}\s*\.|$)"
            match = re.search(pattern, full_text, re.DOTALL)
            
            chunk = ""
            if match:
                chunk = match.group(0).strip()
            else:
                pattern_alt = rf"\n\s*{num_int}\s+(.*?)(?=\n\s*{num_int + 1}\s+|$)"
                match_alt = re.search(pattern_alt, full_text, re.DOTALL)
                if match_alt:
                    chunk = match_alt.group(0).strip()

            if chunk and len(chunk) > 10:
                prompt = f"""
다음 텍스트는 {year}년 정보시스템 감리사 기출문제 중 일부({num_int}번 문항)입니다.
텍스트에서 문제 질문 본문, 4개의 보기 지문, 정답(1~4번 중 하나)을 추적 및 추출하여 
반드시 아래 JSON 규격으로만 응답해 주세요. 마크다운 기호(```json)는 절대 덧붙이지 마십시오.

[기출문제 원문 텍스트]
{chunk}

[응답 JSON 스키마]
{{
  "year": {year},
  "num": {num_int},
  "question": "추출한 문제 질문 지문...",
  "options": [
    "1. 보기 1...",
    "2. 보기 2...",
    "3. 보기 3...",
    "4. 보기 4..."
  ],
  "answer": 정답번호(정수형 1~4),
  "explanation": "해당 기출문제 정답의 간략한 근거 해설"
}}
"""
                parsed_quiz = call_gemini_api(prompt)
                
                # 로컬 캐시에 영속 저장하여 다음 번엔 즉각 반환 처리
                db_data = {}
                if os.path.exists(PAST_EXAMS_DB_PATH):
                    try:
                        with open(PAST_EXAMS_DB_PATH, "r", encoding="utf-8") as f:
                            db_data = json.load(f)
                    except Exception:
                        pass
                
                db_data[db_key] = parsed_quiz
                save_past_exams_db(db_data)
                
                return jsonify({
                    "success": True,
                    "data": parsed_quiz,
                    "source": "AI_RAG_EXTRACT"
                })
        except Exception as e:
            print(f"[경고] 기출문제 AI 실시간 RAG 추출 에러: {e}")

    # 3단계: 복원 실패 시 PDF 다운로드 및 보기 폴백 정보 전달
    fallback_url = f"/api/exam/pdf/{target_pdf}" if target_pdf else None
    return jsonify({
        "success": False,
        "message": f"{year}년 기출 {num}번 문항의 상세 텍스트 데이터를 파싱할 수 없습니다.",
        "pdf_url": fallback_url,
        "pdf_name": target_pdf
    })


def save_past_exams_db(db_data):
    """RAG로 추출한 기출문제를 JSON에 영속적으로 캐싱합니다."""
    try:
        with open(PAST_EXAMS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass





# ==========================================
# 인증(로그인) API
# ==========================================

def _load_auth_properties():
    """
    auth.properties 파일을 파싱하여 key=value 딕셔너리로 반환합니다.
    # 주석과 빈 줄은 무시하며, '=' 구분자 기준으로 key/value를 분리합니다.
    """
    props = {}
    if not os.path.exists(AUTH_PROPERTIES_PATH):
        return props
    try:
        with open(AUTH_PROPERTIES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 주석 또는 빈 줄은 건너뜀
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    props[key.strip()] = value.strip()
    except Exception as e:
        print(f"[AUTH] properties 파일 읽기 실패: {e}", file=sys.stderr)
    return props


@app.route("/api/auth/login", methods=["POST", "OPTIONS"])
def api_auth_login():
    """
    로그인 인증 엔드포인트.
    - 클라이언트에서 보낸 평문 비밀번호를 서버에서 SHA-256 해시 후,
      properties 파일에 저장된 해시값과 비교합니다.
    - 평문 비밀번호는 메모리에 잠깐만 존재하고 즉시 해시 처리됩니다.
    """
    # CORS preflight 요청 처리
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json(silent=True) or {}
    input_username = data.get("username", "").strip()
    input_password = data.get("password", "").strip()

    # 입력값 유효성 검증
    if not input_username or not input_password:
        return jsonify({"success": False, "message": "아이디와 비밀번호를 모두 입력해주세요."}), 400

    # properties 파일에서 저장된 인증 정보 로드
    auth_props = _load_auth_properties()
    stored_username = auth_props.get("auth.username", "")
    stored_password_hash = auth_props.get("auth.password_hash", "")

    if not stored_username or not stored_password_hash:
        return jsonify({"success": False, "message": "서버 인증 설정이 올바르지 않습니다."}), 500

    # 입력된 비밀번호를 SHA-256 해시 후 비교
    input_password_hash = hashlib.sha256(input_password.encode("utf-8")).hexdigest()

    if input_username == stored_username and input_password_hash == stored_password_hash:
        return jsonify({"success": True, "message": "로그인 성공"})
    else:
        return jsonify({"success": False, "message": "아이디 또는 비밀번호가 올바르지 않습니다."}), 401


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


# ==========================================
# 4. 서버 구동 진입점
# ==========================================
if __name__ == "__main__":
    # 데이터 폴더가 없으면 미리 구조화하여 생성
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 디버그 모드로 구동하여 개발 편리성 확보
    app.run(host="127.0.0.1", port=5000, debug=True)
