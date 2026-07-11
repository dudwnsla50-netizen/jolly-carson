# -*- coding: utf-8 -*-
"""
[AI 기반 IT 용어 자동 추출 스크립트]
- 설계 목적: PostgreSQL(Supabase) exam_questions 테이블에서 PM(사업관리) 과목 기출문제를 읽어,
  Gemini AI를 통해 약자, 영문 용어, 전문 용어를 자동으로 식별·정의하여 jolly_carson.db의 vocab_terms 테이블에 저장합니다.
- 원칙 준수: 외부 라이브러리 설치 없이 파이썬 내장 모듈(urllib, json, sqlite3)만 활용합니다.
- 배치 처리: API 호출 횟수를 줄이기 위해 문제 5개씩 묶어서 AI에 전달합니다.
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
import time
from datetime import datetime

# 프로젝트 루트 기반 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOCAB_DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")

# .env 파일 로드 (외부 라이브러리 없이 내장 파서)
env_file_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file_path):
    try:
        with open(env_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
    except Exception as e:
        print(f"[경고] .env 파일 로드 실패: {e}")

# API 설정
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_KEY2 = os.environ.get("GEMINI_API_KEY2", "")

# Supabase PostgreSQL 연결 정보
SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"


def get_pg_connection():
    """PostgreSQL(Supabase) 연결을 반환합니다."""
    import psycopg2
    import psycopg2.extras
    
    raw_url = os.environ.get("DATABASE_URL", SUPABASE_URL_RAW)
    parsed = urllib.parse.urlparse(raw_url)
    
    conn = psycopg2.connect(
        dbname=urllib.parse.unquote(parsed.path.lstrip("/")),
        user=urllib.parse.unquote(parsed.username) if parsed.username else None,
        password=urllib.parse.unquote(parsed.password) if parsed.password else None,
        host=parsed.hostname,
        port=parsed.port or 5432,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    conn.set_client_encoding('UTF8')
    return conn


def get_vocab_db():
    """단어장 SQLite DB 연결을 반환합니다."""
    conn = sqlite3.connect(VOCAB_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# 과목별 대분류 고정 목록 매핑
FIXED_MAJOR_TOPICS = {
    "PM": [
        "통합관리", "범위관리", "일정관리", "원가관리", "품질관리",
        "인적자원관리", "의사소통관리", "위험관리", "조달관리",
        "이해관계자관리", "감리업무", "대가산정", "법규/제도"
    ],
    "SE": [
        "요구사항분석 및 설계", "구현 및 테스트", "유지관리 및 운영",
        "개발방법론/SW구조/공개SW", "SW품질 및 비용산정"
    ],
    "DB": [
        "DB개념 및 설계", "DB언어", "DBMS 기술", "DB응용", "빅데이터 및 AI데이터"
    ],
    "SA": [
        "공통기술", "아키텍처 설계 및 구축", "데이터 통신 및 네트워크 설계", "기타 신기술"
    ],
    "SC": [
        "공통 보안 기술", "네트워크 및 시스템 보안", "응용 및 신기술 보안",
        "개발 및 운영 보안", "정보보호 법규 및 개인정보보호"
    ]
}

SUBJECT_NAMES = {
    "PM": "사업관리(PM)",
    "SE": "소프트웨어공학(SE)",
    "DB": "데이터베이스(DB)",
    "SA": "시스템구조(SA)",
    "SC": "보안(SC)"
}

def call_gemini(prompt, timeout=30):
    """
    Gemini API에 프롬프트를 전송하고 텍스트 응답을 반환합니다.
    429 요율 한도 초과 시 지연 대기 후 최대 3회 재시도하며, 실패 시 다음 백업 키로 폴백합니다.
    """
    keys = [k for k in [GEMINI_API_KEY, GEMINI_API_KEY2] if k]
    if not keys:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    
    for i, api_key in enumerate(keys):
        url = f"{GEMINI_API_URL}?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4096
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        max_retries = 3
        backoff = 2
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    sleep_time = backoff ** (attempt + 1)
                    print(f"\n  [경고] Gemini Key #{i+1} HTTP 429 (Rate Limit). {sleep_time}초 대기 후 재시도합니다... (시도 {attempt+1}/{max_retries})")
                    time.sleep(sleep_time)
                    continue
                
                print(f"\n  [경고] Gemini Key #{i+1} HTTP {e.code} 오류.")
                if i < len(keys) - 1:
                    print("  -> 백업 키로 전환하여 진행합니다.")
                    break
                else:
                    raise
            except Exception as e:
                print(f"\n  [경고] Gemini Key #{i+1} 예외 발생: {e}")
                if i < len(keys) - 1:
                    break
                raise
        else:
            # 1회 시도가 모두 429로 끝난 경우 다음 API 키로 전환
            continue
        
        # loop 정상 실행 시 break로 키 순회 종료
        break
    else:
        raise RuntimeError("모든 API 키의 사용 한도가 초과되었거나 에러가 해결되지 않았습니다.")


def fetch_questions(subject):
    """PostgreSQL에서 지정한 과목의 기출 문제를 모두 가져옵니다."""
    print(f"\n[1/4] PostgreSQL 접속 중 ({subject} 과목 기출 조회)...")
    
    try:
        conn = get_pg_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, year, question_num, question, options, answer, explanation 
            FROM exam_questions 
            WHERE subject = %s
            ORDER BY year DESC, question_num ASC
        """, (subject.upper(),))
        rows = cursor.fetchall()
        conn.close()
        
        print(f"  → {subject} 과목 문제 {len(rows)}건 로드 완료")
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"  [오류] PostgreSQL 접속 실패: {e}")
        print("  [안내] 네트워크 연결 또는 Supabase 설정을 확인하세요.")
        sys.exit(1)


def extract_terms_from_batch(questions_batch, batch_num, total_batches, subject="PM"):
    """
    문제 배치(5개)를 Gemini AI에 전달하여 용어를 추출합니다.
    반환값: 추출된 용어 리스트 (dict 배열)
    """
    # 문제 텍스트 조합
    question_texts = []
    for q in questions_batch:
        text_parts = [f"[{q['year']}년 {q['question_num']}번] {q['question']}"]
        
        if q.get('options'):
            try:
                opts = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
                for idx, opt in enumerate(opts, 1):
                    text_parts.append(f"  {idx}. {opt}")
            except Exception:
                pass
        
        if q.get('explanation'):
            text_parts.append(f"  [해설] {q['explanation']}")
        
        question_texts.append("\n".join(text_parts))
    
    combined_text = "\n\n---\n\n".join(question_texts)
    
    subject_name = SUBJECT_NAMES.get(subject.upper(), "IT 전문 과목")
    major_list_str = ", ".join(FIXED_MAJOR_TOPICS.get(subject.upper(), []))
    
    prompt = f"""다음은 정보시스템감리사 시험의 "{subject_name}" 과목 기출문제들입니다.
이 지문들에서 기출된 핵심 IT 전문 용어, 약자(Abbreviation), 영문 용어를 추출하고 표준적이고 정밀한 수험용 정의를 작성해 주세요.

[중요 지침] 용어 정의(definition) 작성 원칙:
1. 지문에 적힌 문제 형식의 문맥(예: "~에 대한 설명으로 가장 틀린 것은?", "~를 묻는 문제이다")이나 파편화된 지문 내용을 그대로 복사하지 마세요. 이는 절대 금지됩니다!
2. 해당 용어가 가리키는 기술/개념의 핵심 본질과 표준적인 정의를 감리사 수험 사전 수준으로 엄밀하게 새로 작성하세요.
3. 정의는 2~3문장으로 구성하며, 다음 요소를 포함해야 합니다:
   - "이 개념은 무엇인가?" (표준 정의)
   - "핵심 메커니즘 또는 주요 특징은 무엇인가?"
   - "정보시스템 감리 시 주로 무엇을 통제/점검하는가?" (예: 암호키 관리의 적절성, 정규화 준수 여부, 소스코드의 안전성 등)

[추출 및 분류 기준]
1. 약자 (예: EVM, PMBOK, WBS, CPM, PERT, COCOMO 등) — 반드시 영문 풀네임과 한글 뜻을 함께 제시
2. 영문 전문 용어 (예: Earned Value, Critical Path, Risk Matrix 등)
3. 한국어 IT 전문 용어 (예: 획득가치관리, 임계경로법, 기능점수 등)
4. 일반 상식 수준의 단어(프로젝트, 관리, 시스템 등)는 제외
5. 대분류(topic_major)는 반드시 다음 목록 중 하나를 선택해야 합니다:
   [{major_list_str}]
6. 소분류(topic_minor)는 대분류 내에서 용어가 속하는 구체적인 세부 주제를 자유롭게 작성하세요. (예: "EVM분석", "비용추정모형", "네트워크다이어그램" 등)

반드시 아래 JSON 배열 형식으로만 응답하세요. 다른 설명 텍스트 없이 순수 JSON만 출력하세요:
[
  {{
    "term_ko": "획득가치관리",
    "term_en": "Earned Value Management",
    "abbreviation": "EVM",
    "definition": "프로젝트의 범위, 일정, 원가를 통합적으로 측정하여 성과를 정량적으로 평가하는 표준 관리 기법입니다. 성과 계획인 계획가치(PV)와 실제 투입된 실제원가(AC)를 획득가치(EV)와 비교하여 비용 및 일정 편차를 측정합니다. 감리 시에는 성과측정 기준선인 기준선(Baseline)의 적정 수립 여부 및 누적 비용지수(CPI)의 추세를 중점 점검합니다.",
    "topic_major": "원가관리",
    "topic_minor": "EVM분석",
    "related_keywords": ["PV", "AC", "EV", "SPI", "CPI"],
    "source": "2024년 15번"
  }}
]

주의사항:
- 동일 용어가 여러 문제에 등장하더라도 한 번만 추출
- definition은 시험에 나올 수 있는 수준으로 정확하고 간결하게 작성
- related_keywords에는 함께 출제되는 관련 개념을 포함
- source에는 해당 용어가 등장한 문제의 연도와 번호를 기재 (형식: "YYYY년 NN번")

[기출문제 텍스트]
{combined_text}
"""

    print(f"  배치 {batch_num}/{total_batches} 처리 중... ({len(questions_batch)}문제)", end=" ")
    
    try:
        response = call_gemini(prompt)
        
        # JSON 파싱 (```json ... ``` 감싸기 제거)
        json_text = response
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0].strip()
        
        terms = json.loads(json_text)
        print(f"→ {len(terms)}개 용어 추출")
        return terms
    except json.JSONDecodeError as e:
        print(f"→ JSON 파싱 실패: {e}")
        # 부분 복구 시도
        try:
            # 배열 시작과 끝 찾기
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                terms = json.loads(response[start:end])
                print(f"  → 부분 복구 성공: {len(terms)}개 용어")
                return terms
        except Exception:
            pass
        return []
    except Exception as e:
        print(f"→ 오류 발생: {e}")
        return []



# 과목별 최핵심 빈출 IT 전문 용어 및 약어 시드 데이터 (과목당 15선)
SEED_TERMS = {
    "SE": [
        {"term_ko": "역량 성숙도 통합 모델", "term_en": "Capability Maturity Model Integration", "abbreviation": "CMMI", "definition": "조직의 소프트웨어 개발 및 비즈니스 프로세스 능력을 평가하고 개선하기 위한 통합 성숙도 모델", "topic_major": "SW품질 및 비용산정", "topic_minor": "CMMI인증", "related_keywords": ["성숙도5단계", "프로세스영역", "연속형", "단계형"], "source": "기출 다수 빈출"},
        {"term_ko": "도메인 주도 설계", "term_en": "Domain Driven Design", "abbreviation": "DDD", "definition": "비즈니스 도메인의 핵심 개념과 로직을 중심으로 소프트웨어를 모델링하고 설계하는 아법", "topic_major": "요구사항분석 및 설계", "topic_minor": "객체지향설계", "related_keywords": ["Ubiquitous Language", "Bounded Context", "Aggregate"], "source": "기출 핵심 이론"},
        {"term_ko": "테스트 주도 개발", "term_en": "Test Driven Development", "abbreviation": "TDD", "definition": "구현 코드를 작성하기 전에 테스트 케이스를 먼저 개발하고, 이를 통과하는 최소한의 코드를 점진적으로 작성해 나가는 개발 방법론", "topic_major": "구현 및 테스트", "topic_minor": "애자일방법론", "related_keywords": ["Red-Green-Refactor", "단위테스트", "회귀테스트"], "source": "기출 빈출"},
        {"term_ko": "마이크로서비스 아키텍처", "term_en": "Microservices Architecture", "abbreviation": "MSA", "definition": "하나의 거대한 애플리케이션을 독립적으로 배포 및 실행 가능한 핵심 서비스 단위로 나누어 통합하는 소프트웨어 아키텍처", "topic_major": "개발방법론/SW구조/공개SW", "topic_minor": "SW아키텍처", "related_keywords": ["API Gateway", "Loose Coupling", "Decentralized"], "source": "기출 핵심 트렌드"},
        {"term_ko": "코코모", "term_en": "Constructive Cost Model", "abbreviation": "COCOMO", "definition": "보헴(Boehm)이 주창한 라인 수(LOC) 기준의 정적 소프트웨어 원가/비용 산정 기법", "topic_major": "SW품질 및 비용산정", "topic_minor": "비용산정모형", "related_keywords": ["Organic", "Semidetached", "Embedded", "LOC"], "source": "기출 단골 문제"},
        {"term_ko": "기능점수", "term_en": "Function Point", "abbreviation": "FP", "definition": "사용자 관점의 논리적 요구 기능을 정량화하여 소프트웨어 규모 및 개발 비용을 산정하는 표준 기법", "topic_major": "SW품질 및 비용산정", "topic_minor": "비용산정모형", "related_keywords": ["간이법", "상세법", "데이터기능", "트랜잭션기능"], "source": "SW사업 대가산정 가이드"},
        {"term_ko": "리팩토링", "term_en": "Refactoring", "abbreviation": "Refactoring", "definition": "소프트웨어의 외부 동작적 기능은 변경하지 않은 채, 내부 구조를 개선하여 가독성과 유지보수성을 극대화하는 기법", "topic_major": "유지관리 및 운영", "topic_minor": "코드품질개선", "related_keywords": ["Bad Smell", "Technical Debt", "Clean Code"], "source": "기출 핵심 이론"},
        {"term_ko": "데브옵스", "term_en": "DevOps", "abbreviation": "DevOps", "definition": "소프트웨어 개발(Development)과 IT 운영(Operations)을 긴밀하게 연계하여 배포 주기 단축과 무장애 릴리즈를 지향하는 개발 문화 및 방법론", "topic_major": "개발방법론/SW구조/공개SW", "topic_minor": "최신개발론", "related_keywords": ["CI/CD", "Feedback Loop", "Automation"], "source": "기출 신기술 범위"},
        {"term_ko": "익스트림 프로그래밍", "term_en": "Extreme Programming", "abbreviation": "XP", "definition": "고객 소통과 피드백을 극대화하고 개발 주기를 단축하는, 5대 가치와 12대 실천 요소를 가지는 대표적인 애자일 개발론", "topic_major": "개발방법론/SW구조/공개SW", "topic_minor": "애자일방법론", "related_keywords": ["Pair Programming", "Refactoring", "TDD", "Small Releases"], "source": "기출 단골 출제"},
        {"term_ko": "스크럼", "term_en": "Scrum", "abbreviation": "Scrum", "definition": "매일 짧은 미팅을 가지고 정해진 스프린트 기간 동안 점진적이고 지속적으로 제품을 릴리즈하는 애자일 프로젝트 관리 프레임워크", "topic_major": "개발방법론/SW구조/공개SW", "topic_minor": "애자일방법론", "related_keywords": ["Sprint", "Product Backlog", "Daily Standup"], "source": "기출 핵심 이론"},
        {"term_ko": "디자인 패턴", "term_en": "Design Pattern", "abbreviation": "Design Pattern", "definition": "소프트웨어 설계 시 공통으로 발생하는 문제에 대해 검증되고 재사용 가능한 객체지향적 설계 해결책", "topic_major": "요구사항분석 및 설계", "topic_minor": "디자인패턴", "related_keywords": ["GoF 패턴", "생성패턴", "구조패턴", "행위패턴"], "source": "GoF 디자인 패턴"},
        {"term_ko": "ISO/IEC 25010", "term_en": "Software Quality Standard", "abbreviation": "ISO 25010", "definition": "소프트웨어 제품 품질 평가를 위해 기능성, 신뢰성, 사용성 등 8대 주 품질 특성을 정의한 국제 표준 규격", "topic_major": "SW품질 및 비용산정", "topic_minor": "품질인증표준", "related_keywords": ["SQUA", "기능적합성", "신뢰성", "사용성", "보안성"], "source": "기출 빈출 표준"},
        {"term_ko": "정적 분석", "term_en": "Static Analysis", "abbreviation": "Static Analysis", "definition": "소프트웨어를 실제로 컴파일하거나 실행하지 않고 소스 코드 자체를 도구로 검사하여 잠재적 논리 결함과 위반 사양을 조기에 검출하는 기법", "topic_major": "구현 및 테스트", "topic_minor": "소프트웨어테스트", "related_keywords": ["코드리뷰", "룰셋 검사", "잠재적결함", "MISRA-C"], "source": "전자정부 개발가이드"},
        {"term_ko": "지속적 통합 및 배포", "term_en": "Continuous Integration & Deployment", "abbreviation": "CI/CD", "definition": "형 형상관리 서버에 수시로 코드를 통합 및 자동 테스트하고, 검증된 빌드본을 실시간 상용 서버에 자동 배포하는 현대적 딜리버리 파이프라인", "topic_major": "개발방법론/SW구조/공개SW", "topic_minor": "형상/빌드관리", "related_keywords": ["Jenkins", "GitLab CI", "자동빌드", "배포자동화"], "source": "기출 핵심 개념"},
        {"term_ko": "비용산정 모델 COCOMO II", "term_en": "Constructive Cost Model II", "abbreviation": "COCOMO II", "definition": "기존 대규모 폭포수 기반 코코모를 현대 재사용성, 객체지향, 애자일 개발 및 단계별 비용산정이 가능하게 전면 개정한 비용 예측 모형", "topic_major": "SW품질 및 비용산정", "topic_minor": "비용산정모형", "related_keywords": ["Application Composition", "Early Design", "Post-Architecture"], "source": "기출 심화 문제"}
    ],
    "DB": [
        {"term_ko": "데이터베이스 관리 시스템", "term_en": "Database Management System", "abbreviation": "DBMS", "definition": "다수의 사용자가 데이터베이스에 동시 접근하여 데이터를 추가, 조회, 조작할 수 있도록 중재하고 통제하는 소프트웨어 엔진", "topic_major": "DBMS 기술", "topic_minor": "데이터베이스기초", "related_keywords": ["스키마", "데이터독립성", "정의/조작/제어"], "source": "기출 기초 개념"},
        {"term_ko": "트랜잭션 4대 특성", "term_en": "Atomicity Consistency Isolation Durability", "abbreviation": "ACID", "definition": "데이터베이스 트랜잭션이 안전하게 수행됨을 보장하는 4대 필수 성질 (원자성, 일관성, 고립성, 지속성)", "topic_major": "DBMS 기술", "topic_minor": "트랜잭션관리", "related_keywords": ["원자성", "일관성", "고립성", "지속성", "Rollback"], "source": "기출 단골 문제"},
        {"term_ko": "구조화 질의어", "term_en": "Structured Query Language", "abbreviation": "SQL", "definition": "관계형 데이터베이스에 데이터를 삽입, 조회, 갱신, 삭제하거나 스키마 및 권한을 정의하기 위한 업계 표준 질의 언어", "topic_major": "DB언어", "topic_minor": "SQL질의", "related_keywords": ["DDL", "DML", "DCL", "TCL", "Select"], "source": "기출 빈출"},
        {"term_ko": "관계형 DBMS", "term_en": "Relational DBMS", "abbreviation": "RDBMS", "definition": "데이터를 이차원 테이블 구조인 릴레이션(Relation)들로 구조화하고 기본키(PK)와 외래키(FK)를 사용해 상호 관계를 매핑하는 DBMS", "topic_major": "DBMS 기술", "topic_minor": "관계형모델", "related_keywords": ["릴레이션", "튜플", "도메인", "참조무결성"], "source": "기출 핵심 이론"},
        {"term_ko": "비관계형 데이터베이스", "term_en": "Not Only SQL", "abbreviation": "NoSQL", "definition": "관계형 모델 및 스키마의 제약을 탈피하여 대용량 분산 로그 및 비정형 데이터를 유연하게 저장, 처리하는 분산 스키마리스 데이터베이스 기술", "topic_major": "DBMS 기술", "topic_minor": "최신DB기술", "related_keywords": ["Key-Value store", "Document store", "Base 트랜잭션", "Sharding"], "source": "기출 신기술 범위"},
        {"term_ko": "데이터 정규화", "term_en": "Database Normalization", "abbreviation": "Normalization", "definition": "관계형 데이터베이스 설계 시 중복 데이터와 데이터 이상현상(삽입,삭제,갱신)을 배제하기 위해 일관된 릴레이션을 분해하는 정형 기법", "topic_major": "DB개념 및 설계", "topic_minor": "정규화이론", "related_keywords": ["제1정규형", "제2정규형", "제3정규형", "BCNF", "함수적종속성"], "source": "기출 필수 정복"},
        {"term_ko": "인덱싱 구조 B-Tree", "term_en": "Balanced Tree Indexing", "abbreviation": "B-Tree", "definition": "검색 경로를 단축하기 위해 노드의 삽입/삭제 시 스스로 균형을 유지하며 데이터를 탐색하는 관계형 DB의 핵심 물리적 인덱싱 자료구조", "topic_major": "DBMS 기술", "topic_minor": "물리설계/튜닝", "related_keywords": ["Balanced Tree", "B+Tree", "인덱스스캔", "풀테이블스캔"], "source": "기출 단골 출제"},
        {"term_ko": "데이터 웨어하우스", "term_en": "Data Warehouse", "abbreviation": "Data Warehouse", "definition": "기업이나 조직의 다수의 하위 의사결정권자를 지원하기 위해 여러 정보 소스의 이종 데이터를 수집, 요약하여 통합 보존하는 다차원 분석 데이터 저장소", "topic_major": "DB응용", "topic_minor": "OLAP/빅데이터", "related_keywords": ["OLAP", "주제지향성", "시계열성", "비휘발성"], "source": "기출 핵심 개념"},
        {"term_ko": "데이터 추출변환적재", "term_en": "Extract Transform Load", "abbreviation": "ETL", "definition": "운영 트랜잭션 원본 소스 시스템으로부터 대량 데이터를 추출(Extract)하고 정제 및 변환(Transform)하여 다차원 분석 데이터 저장소에 적재(Load)하는 일관 프로세스", "topic_major": "DB응용", "topic_minor": "데이터통합", "related_keywords": ["EAI", "CDC", "데이터정제", "스테이징영역"], "source": "공공데이터 관리지침"},
        {"term_ko": "데이터 거버넌스", "term_en": "Data Governance", "abbreviation": "Data Governance", "definition": "전사적 데이터 품질, 메타데이터 관리, 마스터데이터, 보안 및 표준 준수성을 보장하기 위해 수립하는 종합적인 통제 절차 및 거버넌스 체계", "topic_major": "DB응용", "topic_minor": "데이터거버넌스", "related_keywords": ["메타데이터", "데이터표준화", "데이터품질관리", "DAMA-DMBOK"], "source": "공공데이터 관리지침"},
        {"term_ko": "CAP 이론", "term_en": "Consistency Availability Partition-tolerance", "abbreviation": "CAP", "definition": "분산 데이터베이스 환경에서 일관성(C), 가용성(A), 분할 허용성(P) 세 성질을 모두 한 번에 만족시킬 수는 없다는 이론", "topic_major": "DBMS 기술", "topic_minor": "분산데이터베이스", "related_keywords": ["일관성", "가용성", "네트워크분할", "PACELC"], "source": "기출 빈출 이론"},
        {"term_ko": "동시성 제어 2단계 잠금 규약", "term_en": "Two-Phase Locking protocol", "abbreviation": "2PL", "definition": "트랜잭션 실행 시 자원의 잠금을 확장하는 단계(Growing Phase)와 잠금을 해제하는 단계(Shrinking Phase)로 분리해 직렬가능성을 보장하는 동시성 제어 기술", "topic_major": "DBMS 기술", "topic_minor": "트랜잭션관리", "related_keywords": ["확장단계", "축소단계", "직렬가능성", "데드락"], "source": "기출 핵심 이론"},
        {"term_ko": "다중 버전 동시성 제어", "term_en": "Multi-Version Concurrency Control", "abbreviation": "MVCC", "definition": "데이터 변경 기록을 버전별로 저장해 읽기 작업 시 쓰기 락(Lock)을 기다리지 않고 해당 시점 스냅샷을 읽을 수 있게 보장해주는 고성능 동시성 제어 기법", "topic_major": "DBMS 기술", "topic_minor": "트랜잭션관리", "related_keywords": ["스냅샷격리", "Undo 로그", "Read Committed", "락프리"], "source": "기출 고급 문제"},
        {"term_ko": "벡터 데이터베이스", "term_en": "Vector Database", "abbreviation": "Vector DB", "definition": "거대언어모델(LLM)에 의해 고차원 벡터로 변환된 이미지, 텍스트 등의 임베딩 값을 저장하고 유사도 검색(ANN)을 통해 신속하게 찾아내는 특화 DB 기술", "topic_major": "빅데이터 및 AI데이터", "topic_minor": "AI데이터기술", "related_keywords": ["임베딩벡터", "코사인유사도", "ANN검색", "RAG기반"], "source": "최초 도입 가이드라인"},
        {"term_ko": "데이터 이상현상", "term_en": "Database Anomaly", "abbreviation": "Anomaly", "definition": "릴레이션 스키마 설계 오류로 데이터 중복이 발생해 자원을 변경할 때 발생하는 부작용(삽입 이상, 삭제 이상, 갱신 이상)", "topic_major": "DB개념 및 설계", "topic_minor": "정규화이론", "related_keywords": ["삽입이상", "삭제이상", "갱신이상", "중복저장"], "source": "기출 필수 개념"}
    ],
    "SA": [
        {"term_ko": "클라우드 컴퓨팅", "term_en": "Cloud Computing", "abbreviation": "Cloud", "definition": "인터넷 망을 통하여 IT 인프라(서버, 스토리지, DB 등) 자원을 자체 소유하지 않고 온디맨드로 확장 가능하게 임대하여 활용하는 기술", "topic_major": "기타 신기술", "topic_minor": "클라우드기반", "related_keywords": ["가상화", "탄력성", "종량제요금", "멀티테넌시"], "source": "초거대 AI 도입 가이드라인"},
        {"term_ko": "인프라 가상화 서비스", "term_en": "Infrastructure as a Service", "abbreviation": "IaaS", "definition": "서버 컴퓨터, 스토리지 디스크, 가상 네트워크 자원 등의 가장 하위 레벨의 가상 인프라 자원을 사용자가 통제할 수 있게 임대/구축하는 서비스 모델", "topic_major": "아키텍처 설계 및 구축", "topic_minor": "클라우드구조", "related_keywords": ["가상머신", "하이퍼바이저", "VPC", "AWS EC2"], "source": "기출 빈출"},
        {"term_ko": "플랫폼 서비스", "term_en": "Platform as a Service", "abbreviation": "PaaS", "definition": "서버 OS, 런타임 플랫폼, 개발 프레임워크 등을 서비스 형태로 공급해 개발자가 인프라 관리 부담 없이 개발에만 몰두할 수 있게 지원하는 클라우드 모델", "topic_major": "아키텍처 설계 및 구축", "topic_minor": "클라우드구조", "related_keywords": ["미들웨어", "런타임환경", "서버리스", "Heroku"], "source": "기출 핵심 개념"},
        {"term_ko": "소프트웨어 서비스", "term_en": "Software as a Service", "abbreviation": "SaaS", "definition": "설치 과정 없이 웹 브라우저를 통해 인터넷 상에서 완제품 소프트웨어를 구동하여 실시간 접근하고 구독 요금을 지불하는 서비스 모델", "topic_major": "아키텍처 설계 및 구축", "topic_minor": "클라우드구조", "related_keywords": ["웹애플리케이션", "구독모델", "Office 365", "Salesforce"], "source": "기출 핵심 개념"},
        {"term_ko": "가상 격리 컨테이너", "term_en": "OS-level Containerization", "abbreviation": "Container", "definition": "호스트 OS 커널 공간을 가볍게 공유하며 독립적인 애플리케이션 실행 환경을 파일시스템 레벨에서 완전히 분할 격리 구동하는 기술", "topic_major": "아키텍처 설계 및 구축", "topic_minor": "가상화기술", "related_keywords": ["Docker", "네임스페이스", "컨테이너이미지", "Cgroups"], "source": "기출 최신 인프라"},
        {"term_ko": "컨테이너 오케스트레이션", "term_en": "Container Orchestration Engine", "abbreviation": "Kubernetes", "definition": "수백 수천 개의 가상 컨테이너들의 자동 배포, 자가 치유(Self-healing), 동적 로드밸런싱 및 자원 확장을 통합 관리해주는 표준 엔진 프레임워크 (예: K8s)", "topic_major": "아키텍처 설계 및 구축", "topic_minor": "가상화기술", "related_keywords": ["K8s", "Pod", "ReplicaSet", "Auto-scaling"], "source": "기출 최신 인프라"},
        {"term_ko": "로컬 부하 분산 장치", "term_en": "Load Balancing hardware/software", "abbreviation": "L4 Switch", "definition": "외부의 과도한 트래픽 요청을 세션 레벨(L4) 또는 HTTP 컨텐츠 레벨(L7)에서 여러 백엔드 서버로 고르게 전달해 병목을 해소하고 장애 복구력을 올리는 기술", "topic_major": "데이터 통신 및 네트워크 설계", "topic_minor": "네트워크장비", "related_keywords": ["로드밸런서", "라운드로빈", "세션유지", "L7 스위치"], "source": "기출 단골 출제"},
        {"term_ko": "소프트웨어 정의 네트워크", "term_en": "Software Defined Networking", "abbreviation": "SDN", "definition": "네트워크 하드웨어 장비에서 컨트롤 플레인(제어 영역)을 완전 분리하여 하나의 중앙 집중형 컨트롤러 소프트웨어로 전체 통신을 조율하는 기술", "topic_major": "데이터 통신 및 네트워크 설계", "topic_minor": "차세대네트워크", "related_keywords": ["OpenFlow", "Control Plane", "Data Plane", "오버레이 네트워크"], "source": "기출 빈출 기술"},
        {"term_ko": "콘텐츠 전송 네트워크", "term_en": "Content Delivery Network", "abbreviation": "CDN", "definition": "용량이 큰 웹 리소스 및 동영상 파일을 지리적으로 사용자와 가까운 엣지 서버들에 미리 캐싱해두어 전송 지연과 주 서버의 대역폭 소모를 배제하는 캐싱 서비스", "topic_major": "데이터 통신 및 네트워크 설계", "topic_minor": "네트워크응용", "related_keywords": ["Edge Server", "캐시히트율", "Origin Server", "DNS 리다이렉션"], "source": "기출 핵심 개념"},
        {"term_ko": "서비스 지향 아키텍처", "term_en": "Service Oriented Architecture", "abbreviation": "SOA", "definition": "비즈니스 기능들을 상호 연동 가능하고 느슨하게 결합된 하나의 '서비스' 단위로 부품화하고 연결하여 기업 아키텍처를 유연하게 구축하는 설계 사상", "topic_major": "아키텍처 설계 및 구축", "topic_minor": "SW아키텍처", "related_keywords": ["ESB", "느슨한결합", "WSDL/UDDI", "재사용성"], "source": "기출 아키텍처 범위"},
        {"term_ko": "경계 관문 프로토콜", "term_en": "Border Gateway Protocol", "abbreviation": "BGP", "definition": "인터넷 망 상에서 대규모 자율 시스템(AS - Autonomous System) 상호 간의 가용한 최적의 경로 정적 정보를 동적으로 유통, 갱신하는 프로토콜", "topic_major": "데이터 통신 및 네트워크 설계", "topic_minor": "라우팅프로토콜", "related_keywords": ["경로벡터", "Autonomous System", "AS-path", "피어링"], "source": "기출 통신 범위"},
        {"term_ko": "이중화 디스크 구성", "term_en": "Redundant Array of Independent Disks", "abbreviation": "RAID", "definition": "복수의 물리적 하드디스크를 단일의 논리적 디스크로 묶어 성능 향상(스트라이핑) 및 데이터 유실 복원력(패리티 이중화)을 제공하는 저장장치 다중화 기술", "topic_major": "아키텍처 설계 및 구축", "topic_minor": "서버/스토리지", "related_keywords": ["RAID 0 (스트라이핑)", "RAID 1 (미러링)", "RAID 5 (패리티분산)", "RAID 6"], "source": "기출 단골 문제"},
        {"term_ko": "초경량 메시지 프로토콜", "term_en": "Message Queuing Telemetry Transport", "abbreviation": "MQTT", "definition": "대역폭이 매우 좁고 신뢰도가 낮은 IoT 센서 장치 환경에서 경량 메시지를 발행/구독 방식으로 유연하고 신속하게 중계하는 오버레이 프로토콜", "topic_major": "데이터 통신 및 네트워크 설계", "topic_minor": "IoT통신", "related_keywords": ["발행/구독", "Broker", "QoS 레벨", "Keep Alive"], "source": "기출 신기술 범위"},
        {"term_ko": "애플리케이션 성능 모니터링", "term_en": "Application Performance Monitoring", "abbreviation": "APM", "definition": "운영계 시스템 내의 미들웨어, DB 쿼리, JVM 메모리 상태를 지속적으로 수집, 분석하여 병목을 시각화하고 응답 지연을 추적하는 성능 모니터링 솔루션", "topic_major": "공통기술", "topic_minor": "시스템모니터링", "related_keywords": ["JVM 모니터링", "응답시간분포", "Thread Dump", "Jennifer/Scouter"], "source": "전자정부 성과관리 지침"},
        {"term_ko": "하이퍼바이저 기반 가상화", "term_en": "Hypervisor Virtualization", "abbreviation": "Hypervisor", "definition": "단일 물리 서버 하드웨어 위에 가상화 관리 계층을 두어 독립된 복수의 게스트 OS들을 하부 시스템 간 겹침 없이 안전하게 동작시키는 원격 가상화 기술", "topic_major": "아키텍처 설계 및 구축", "topic_minor": "가상화기술", "related_keywords": ["Bare-Metal (Type 1)", "Hosted (Type 2)", "가상머신", "게스트 OS"], "source": "기출 빈출"}
    ],
    "SC": [
        {"term_ko": "정보보호 관리체계 인증", "term_en": "Information Security Management System - Personal", "abbreviation": "ISMS-P", "definition": "조직의 핵심 정보자산 및 개인정보 유출 방지를 위한 수립, 운영, 통제 관리 활동이 정부 표준 고시 규격을 충족하는지 종합 심사하는 국가 공인 인증제도", "topic_major": "정보보호 법규 및 개인정보보호", "topic_minor": "정보보호인증", "related_keywords": ["인증기준102개", "관리과정", "개인정보처리단계", "인증기관"], "source": "기출 초빈출 제도"},
        {"term_ko": "공개키 기반 구조", "term_en": "Public Key Infrastructure", "abbreviation": "PKI", "definition": "공개키 암호화 알고리즘에 기초하여 사용자의 인증서 발급, 검증, 폐기 및 키 배포가 공신력 있게 이루어지도록 수립한 국가·글로벌 보안 인증 인증 체계", "topic_major": "공통 보안 기술", "topic_minor": "인증기술", "related_keywords": ["CA (인증기관)", "RA (등록기관)", "인증서 (X.509)", "CRL (폐기목록)", "OCSP"], "source": "기출 핵심 이론"},
        {"term_ko": "분산 서비스 거부 공격", "term_en": "Distributed Denial of Service", "abbreviation": "DDoS", "definition": "감염된 다수의 좀비 PC들로 구성된 봇넷(Botnet)을 원격 조종하여 특정 표적 시스템에 대량의 트래픽을 동시 주입해 대역폭이나 자원을 고갈시켜 마비시키는 공격", "topic_major": "네트워크 및 시스템 보안", "topic_minor": "보안침해공격", "related_keywords": ["Syn Flooding", "Get Flooding", "Botnet", "C&C Server", "DRDoS"], "source": "기출 단골 문제"},
        {"term_ko": "제로 트러스트", "term_en": "Zero Trust Security Model", "abbreviation": "Zero Trust", "definition": "네트워크의 경계 보안을 신뢰하지 않고, 사설망 내외부를 불문하여 모든 시스템 접근 행위와 기기 정체성을 지속적으로 강제 검증하고 최소 권한만 부여하는 현대 보안 프레임워크", "topic_major": "응용 및 신기술 보안", "topic_minor": "최신보안동향", "related_keywords": ["Never Trust", "Always Verify", "상태기반 세션인증", "최소권한"], "source": "기출 최신 트렌드"},
        {"term_ko": "고급 블록 암호 표준", "term_en": "Advanced Encryption Standard", "abbreviation": "AES", "definition": "대칭키 암호화 방식 중 128비트 데이터 블록을 128, 192, 256비트 비밀키로 고속 라운드 변환하는 미국의 국가 공인 표준 비밀키 블록 암호 알고리즘", "topic_major": "공통 보안 기술", "topic_minor": "암호학", "related_keywords": ["대칭키암호", "블록암호", "SPN 구조", "Rijndael"], "source": "기출 핵심 이론"},
        {"term_ko": "공개키 암호화 RSA", "term_en": "Rivest Shamir Adleman algorithm", "abbreviation": "RSA", "definition": "매우 큰 두 소수의 곱을 구하기는 쉬우나, 이를 다시 소인수분해하는 것은 수학적으로 매우 난해하다는 난제성에 착안하여 고안된 공개키 비대칭 암호화 기술 표준", "topic_major": "공통 보안 기술", "topic_minor": "암호학", "related_keywords": ["비대칭키암호", "소인수분해", "디지털서명", "오일러파이함수"], "source": "기출 핵심 이론"},
        {"term_ko": "데이터베이스 인젝션", "term_en": "SQL Injection", "abbreviation": "SQL Injection", "definition": "웹 애플리케이션 입력창 및 파라미터에 악의적인 SQL 질의 구문을 오버레이 주입하여 개발자가 차단하지 않은 백엔드 DB의 원본 데이터를 무단 조회, 탈취하는 웹 애플리케이션 해킹 기법", "topic_major": "개발 및 운영 보안", "topic_minor": "웹애플리케이션보안", "related_keywords": ["입력값검증", "PreparedStatement", "Union-based SQLi", "Blind SQLi"], "source": "소프트웨어 개발보안 가이드"},
        {"term_ko": "크로스 사이트 스크립팅", "term_en": "Cross Site Scripting", "abbreviation": "XSS", "definition": "게시판이나 입력 양식에 악의적 사용자 스크립트 코드를 삽입하여 다른 일반 방문자가 이를 열람할 때 브라우저에서 스크립트가 실행되어 피해자의 세션 쿠키를 가로채는 공격", "topic_major": "개발 및 운영 보안", "topic_minor": "웹애플리케이션보안", "related_keywords": ["HTML Entity Encoding", "DOM-based XSS", "Stored XSS", "Reflected XSS"], "source": "소프트웨어 개발보안 가이드"},
        {"term_ko": "웹 애플리케이션 방화벽", "term_en": "Web Application Firewall", "abbreviation": "WAF", "definition": "일반 네트워크 방화벽이 보지 못하는 L7 웹 프로토콜(HTTP) 내부 요청 패킷과 파라미터의 변조를 상세 분석하여 웹 애플리케이션 침해(XSS, SQLi 등)를 차단하는 웹 전용 보안 장비", "topic_major": "네트워크 및 시스템 보안", "topic_minor": "보안네트워크장비", "related_keywords": ["HTTP패킷정밀검사", "L7방화벽", "OWASP Top 10 차단", "웹보안"], "source": "기출 빈출 장비"},
        {"term_ko": "오픈 인증 연동 규격", "term_en": "Open Authorization 2.0", "abbreviation": "OAuth 2.0", "definition": "사용자의 패스워드를 노출하지 않고 다른 서드파티 애플리케이션에게 특정 리소스 소유자의 접근 권한을 안전하게 위임하고 토큰을 발급해주는 표준 연동 인증 프로토콜", "topic_major": "응용 및 신기술 보안", "topic_minor": "인증기술", "related_keywords": ["Access Token", "Authorization Code", "API 연동", "SSO"], "source": "기출 핵심 응용"},
        {"term_ko": "보안 커널 운영체제", "term_en": "Secure Operating System", "abbreviation": "Secure OS", "definition": "운영체제 커널 내부의 파일 및 프로세스에 참조 모니터를 구현하고 다중 참조 기준 보안 정책(MAC)을 철저히 집행하여 루트 권한 무단 변조를 배제하는 보안 강화 OS", "topic_major": "네트워크 및 시스템 보안", "topic_minor": "서버시스템보안", "related_keywords": ["MAC (강제적접근통제)", "보안커널", "참조모니터", "통제대상"], "source": "기출 보안 범위"},
        {"term_ko": "개인정보 보호법 고시 규정", "term_en": "Personal Information Protection Act", "abbreviation": "PIPA", "definition": "개인정보의 수집, 유출, 남용으로부터 국민 개개인의 권리와 이익을 안전하게 보호하고 처리 권한과 의무를 성문화한 대한민국 개인정보 기본 법률", "topic_major": "정보보호 법규 및 개인정보보호", "topic_minor": "보안법규", "related_keywords": ["고유식별정보", "동의의무", "안전조치의무", "개인정보처리방침"], "source": "개인정보 보호법 고시"},
        {"term_ko": "데이터 암호화 표준 DES", "term_en": "Data Encryption Standard", "abbreviation": "DES", "definition": "과거 널리 활용된 블록 암호 규격으로, 64비트 평문 블록을 페이스텔(Feistel) 구조 하에 56비트 비밀키를 이용하여 라운드 가공 및 전치하는 고전적 대칭 암호 표준", "topic_major": "공통 보안 기술", "topic_minor": "암호학", "related_keywords": ["대칭키암호", "Feistel구조", "키길이56비트", "Triple-DES (대체)"], "source": "기출 기초 개념"},
        {"term_ko": "강제적 접근 통제 MAC", "term_en": "Mandatory Access Control", "abbreviation": "MAC", "definition": "사용자의 신분이 아니라 시스템에서 주체에 부여한 보안 등급과 객체에 부여된 인가 수준을 비교하여 보안 커널에서 접근 권한을 결정하는 강제성 접근 제어 기술", "topic_major": "네트워크 및 시스템 보안", "topic_minor": "액세스통제", "related_keywords": ["보안등급", "인증기준", "DAC (대조)", "RBAC (대조)", "Bell-LaPadula 모델"], "source": "기출 핵심 이론"},
        {"term_ko": "역할 기반 접근 통제 RBAC", "term_en": "Role-Based Access Control", "abbreviation": "RBAC", "definition": "개별 주체가 아니라 조직 내에서 갖는 권한 직책과 역할(Role)에 모든 권한을 매핑하고 주체를 그 역할 그룹에 바인딩하여 안전하게 권한을 할당하는 접근 통제 기법", "topic_major": "네트워크 및 시스템 보안", "topic_minor": "액세스통제", "related_keywords": ["역할그룹", "직무분리", "최소권한원칙", "그룹접근통제"], "source": "기출 핵심 이론"}
    ]
}


def insert_seed_terms_if_empty(subject="PM"):
    """
    [설계 의도]
    각 과목의 단어장 데이터가 전혀 없을 때, 정보시스템감리사 시험의 최핵심 15대 빈출 용어/약자를
    seed 데이터로 미리 insert하여 즉각 학습 및 조회가 가동될 수 있도록 안전판을 구축합니다.
    """
    subject = subject.upper()
    if subject not in SEED_TERMS:
        return
        
    conn = get_vocab_db()
    cursor = conn.cursor()
    
    # 해당 과목에 등록된 term 건수 확인
    cursor.execute("SELECT COUNT(*) FROM vocab_terms WHERE subject = ?", (subject,))
    cnt = cursor.fetchone()[0]
    
    if cnt > 0:
        conn.close()
        return  # 이미 용어가 있으면 시드 추가 건너뜀
        
    print(f"  → {subject} 과목의 초기 시드(Seed) 용어 {len(SEED_TERMS[subject])}개를 적재합니다...")
    
    for term in SEED_TERMS[subject]:
        term_ko = term["term_ko"]
        term_en = term["term_en"]
        abbreviation = term["abbreviation"]
        definition = term["definition"]
        topic_major = term["topic_major"]
        topic_minor = term["topic_minor"]
        related_kw = term["related_keywords"]
        source_val = term["source"]
        
        # 1. 대분류 ID 확인/생성
        cursor.execute(
            "SELECT id FROM vocab_topics WHERE subject = ? AND parent_id IS NULL AND name = ?",
            (subject, topic_major)
        )
        row_major = cursor.fetchone()
        if row_major:
            major_id = row_major["id"]
        else:
            cursor.execute(
                "INSERT INTO vocab_topics (subject, name, parent_id) VALUES (?, ?, NULL)",
                (subject, topic_major)
            )
            major_id = cursor.lastrowid

        # 2. 소분류 ID 확인/생성
        topic_id = major_id
        if topic_minor:
            cursor.execute(
                "SELECT id FROM vocab_topics WHERE subject = ? AND parent_id = ? AND name = ?",
                (subject, major_id, topic_minor)
            )
            row_minor = cursor.fetchone()
            if row_minor:
                topic_id = row_minor["id"]
            else:
                cursor.execute(
                    "INSERT INTO vocab_topics (subject, name, parent_id) VALUES (?, ?, ?)",
                    (subject, topic_minor, major_id)
                )
                topic_id = cursor.lastrowid

        # 3. 용어 테이블 입력
        related_kw_json = json.dumps(related_kw, ensure_ascii=False)
        source_json = json.dumps([source_val], ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO vocab_terms (term_ko, term_en, abbreviation, definition, subject, topic_id, frequency, related_keywords, source)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (term_ko, term_en, abbreviation, definition, subject, topic_id, related_kw_json, source_json))
        
        term_id = cursor.lastrowid
        
        # 4. SRS 상태 생성
        cursor.execute("""
            INSERT INTO vocab_srs_state (term_id, ease_factor, interval_days, repetitions, next_review_at)
            VALUES (?, 2.5, 0, 0, datetime('now', 'localtime'))
        """, (term_id,))
        
    conn.commit()
    conn.close()
    print(f"  → {subject} 과목의 초기 시드 적재 완료!")


def save_terms_to_db(terms_list, subject="PM"):
    """
    추출된 용어들을 jolly_carson.db의 단어장 관련 테이블들에 저장합니다.
    중복 체크: 동일 약자 또는 동일 한글 용어명이 존재할 경우 frequency를 올리고 source를 통합합니다.
    """
    print(f"\n[3/4] jolly_carson.db에 저장 중...")
    
    conn = get_vocab_db()
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    skipped = 0
    
    for term in terms_list:
        term_ko = term.get("term_ko", "").strip()
        term_en = term.get("term_en", "").strip() or None
        abbreviation = term.get("abbreviation", "").strip() or None
        definition = term.get("definition", "").strip()
        topic_major = term.get("topic_major", "").strip() or "통합관리"
        topic_minor = term.get("topic_minor", "").strip() or None
        related_kw = term.get("related_keywords", [])
        source_val = term.get("source", "").strip()
        
        if not term_ko or not definition:
            skipped += 1
            continue

        # 1. 대분류 ID 확인 및 생성
        cursor.execute(
            "SELECT id FROM vocab_topics WHERE subject = ? AND parent_id IS NULL AND name = ?",
            (subject, topic_major)
        )
        row_major = cursor.fetchone()
        if row_major:
            major_id = row_major["id"]
        else:
            # 기본 대분류 세트에 없으면 새로 생성
            cursor.execute(
                "INSERT INTO vocab_topics (subject, name, parent_id) VALUES (?, ?, NULL)",
                (subject, topic_major)
            )
            major_id = cursor.lastrowid

        # 2. 소분류 ID 확인 및 생성
        topic_id = major_id
        if topic_minor:
            cursor.execute(
                "SELECT id FROM vocab_topics WHERE subject = ? AND parent_id = ? AND name = ?",
                (subject, major_id, topic_minor)
            )
            row_minor = cursor.fetchone()
            if row_minor:
                topic_id = row_minor["id"]
            else:
                cursor.execute(
                    "INSERT INTO vocab_topics (subject, name, parent_id) VALUES (?, ?, ?)",
                    (subject, topic_minor, major_id)
                )
                topic_id = cursor.lastrowid

        # 3. 중복 체크: 약자 또는 한글 용어명 기준
        existing_id = None
        existing_freq = 1
        existing_source = []

        if abbreviation:
            cursor.execute(
                "SELECT id, frequency, source FROM vocab_terms WHERE abbreviation = ? AND subject = ?",
                (abbreviation, subject)
            )
            row = cursor.fetchone()
            if row:
                existing_id = row["id"]
                existing_freq = row["frequency"]
                try:
                    existing_source = json.loads(row["source"]) if row["source"] else []
                except:
                    existing_source = [row["source"]] if row["source"] else []

        if not existing_id:
            cursor.execute(
                "SELECT id, frequency, source FROM vocab_terms WHERE term_ko = ? AND subject = ?",
                (term_ko, subject)
            )
            row = cursor.fetchone()
            if row:
                existing_id = row["id"]
                existing_freq = row["frequency"]
                try:
                    existing_source = json.loads(row["source"]) if row["source"] else []
                except:
                    existing_source = [row["source"]] if row["source"] else []

        # 관련 키워드 파싱
        related_kw_json = json.dumps(related_kw, ensure_ascii=False) if related_kw else None

        if existing_id:
            # 업데이트 로직 (중복 발견 시 빈도수 + 출처 병합)
            new_freq = existing_freq + 1
            if source_val and source_val not in existing_source:
                existing_source.append(source_val)
            
            source_json = json.dumps(existing_source, ensure_ascii=False)
            
            cursor.execute("""
                UPDATE vocab_terms 
                SET frequency = ?, source = ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?
            """, (new_freq, source_json, existing_id))
            updated += 1
        else:
            # 신규 삽입
            source_json = json.dumps([source_val] if source_val else [], ensure_ascii=False)
            cursor.execute("""
                INSERT INTO vocab_terms (term_ko, term_en, abbreviation, definition, subject, topic_id, frequency, related_keywords, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (term_ko, term_en, abbreviation, definition, subject, topic_id, 1, related_kw_json, source_json))

            term_id = cursor.lastrowid

            # SRS 초기 상태 생성
            cursor.execute("""
                INSERT INTO vocab_srs_state (term_id, ease_factor, interval_days, repetitions, next_review_at)
                VALUES (?, 2.5, 0, 0, datetime('now', 'localtime'))
            """, (term_id,))
            inserted += 1

    conn.commit()
    conn.close()
    
    print(f"  → 신규 저장: {inserted}건")
    print(f"  → 기존 갱신: {updated}건")
    print(f"  → 스킵/오류: {skipped}건")
    return inserted, updated


def print_summary(subject="PM"):
    """저장된 용어 통계를 출력합니다."""
    print(f"\n[4/4] {subject} 과목 추출 결과 요약")
    print("=" * 60)
    
    conn = get_vocab_db()
    cursor = conn.cursor()
    
    # 총 용어 수
    cursor.execute("SELECT COUNT(*) as cnt FROM vocab_terms WHERE subject = ?", (subject.upper(),))
    total = cursor.fetchone()["cnt"]

    # 대분류별 분포
    cursor.execute("""
        SELECT p.name AS major, COUNT(t.id) as cnt
        FROM vocab_terms t
        JOIN vocab_topics c ON t.topic_id = c.id
        LEFT JOIN vocab_topics p ON c.parent_id = p.id
        WHERE t.subject = ?
        GROUP BY COALESCE(p.name, c.name)
        ORDER BY cnt DESC
    """, (subject.upper(),))
    groups = cursor.fetchall()

    # 약자가 있는 용어 수
    cursor.execute("SELECT COUNT(*) as cnt FROM vocab_terms WHERE subject = ? AND abbreviation IS NOT NULL AND abbreviation != ''", (subject.upper(),))
    abbr_count = cursor.fetchone()["cnt"]
    
    print(f"  총 {subject} 용어 수: {total}개")
    print(f"  약자 포함 용어: {abbr_count}개")
    print(f"\n  [대분류별 용어 분포]")
    for g in groups:
        bar = "#" * min(g["cnt"], 30)
        print(f"    {g['major']:15s} | {bar} {g['cnt']}개")
    
    # 샘플 출력
    cursor.execute("""
        SELECT t.term_ko, t.term_en, t.abbreviation, c.name AS topic_name
        FROM vocab_terms t
        JOIN vocab_topics c ON t.topic_id = c.id
        WHERE t.subject = ? AND t.abbreviation IS NOT NULL AND t.abbreviation != ''
        ORDER BY RANDOM()
        LIMIT 5
    """, (subject.upper(),))
    samples = cursor.fetchall()
    
    if samples:
        print(f"\n  [약자 용어 샘플 10개]")
        for s in samples:
            abbr = s["abbreviation"] or ""
            en = s["term_en"] or ""
            print(f"    {abbr:10s} → {en:35s} → {s['term_ko']} [{s['topic_name']}]")
    
    conn.close()
    print("=" * 60)


def main():
    print("=" * 60)
    print("  [Jolly-Carson] 전 과목 IT 용어 자동 추출기")
    print("=" * 60)
    
    if not os.path.exists(VOCAB_DB_PATH):
        print("[오류] jolly_carson.db가 존재하지 않습니다. 먼저 init_vocabulary_db.py를 실행하세요.")
        sys.exit(1)

    conn_check = get_vocab_db()
    table_exists = conn_check.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='vocab_terms'"
    ).fetchone()
    conn_check.close()
    if not table_exists:
        print("[오류] vocab_terms 테이블이 존재하지 않습니다. 먼저 init_vocabulary_db.py를 실행하세요.")
        sys.exit(1)
        
    # [초기화] 이전의 로컬 기계적 스캐닝으로 적재된 파편화 데이터를 비우고,
    # 순수 고품질 AI 데이터로만 전 과목 단어장을 정화 리빌딩합니다.
    print("\n[초기화] 고품질 AI 단어장 구축을 위해 기존 vocab 관련 데이터를 리셋합니다...")
    conn_reset = sqlite3.connect(VOCAB_DB_PATH)
    cursor_reset = conn_reset.cursor()
    try:
        cursor_reset.execute("DELETE FROM vocab_review_log")
        cursor_reset.execute("DELETE FROM vocab_srs_state")
        cursor_reset.execute("DELETE FROM vocab_terms")
        cursor_reset.execute("DELETE FROM vocab_topics")
        conn_reset.commit()
        print("  → 초기화 완료!")
    except Exception as e:
        print(f"  [경고] 초기화 중 오류: {e}")
    finally:
        conn_reset.close()

    subjects = ["PM", "SE", "DB", "SA", "SC"]
    
    for sub in subjects:
        print(f"\n>>> {sub} 과목 검사 중...")
        
        # 1. 초기 핵심 용어 시드 데이터 무조건 선제 적재 (비어있는 경우에만 실행됨)
        insert_seed_terms_if_empty(sub)
        
        # 2단계: PostgreSQL에서 문제 가져오기 (추가 수집용)
        questions = fetch_questions(sub)
        
        if not questions:
            print(f"  [안내] {sub} 과목 기출문제가 없어 스킵합니다.")
            continue
            
        # 3단계: 배치 단위로 AI 용어 추가 추출 (요율 429 방지를 위해 최신 50문제 = 10배치만 수행)
        print(f"\n[2/4] Gemini AI 용어 추가 추출 시작 (배치 크기: 5문제 / 대상: 최신 50문제)")
        
        BATCH_SIZE = 5
        all_terms = []
        
        max_questions = questions[:50]  # 최신 50문제로 범위 확장
        total_batches = (len(max_questions) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, len(max_questions), BATCH_SIZE):
            batch = max_questions[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            
            terms = extract_terms_from_batch(batch, batch_num, total_batches, subject=sub)
            all_terms.extend(terms)
            
            # API 과부하 방지: 배치 간 3.5초 대기
            if batch_num < total_batches:
                time.sleep(3.5)
        
        print(f"\n  → 추가 추출 완료: {len(all_terms)}개 용어 (중복 포함)")
        
        # 4단계: DB에 저장 및 결과 요약
        inserted, updated = save_terms_to_db(all_terms, subject=sub)
        print_summary(subject=sub)
        
        print(f"\n[완료] {sub} 과목 용어 추가 추출 및 적재가 끝났습니다.")
        
    print(f"\n[전체 완료] 모든 과목에 대한 단어장 구축이 종료되었습니다.")
    print(f"  → jolly_carson.db 경로: {VOCAB_DB_PATH}")


if __name__ == "__main__":
    main()
