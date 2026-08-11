# -*- coding: utf-8 -*-
"""
[단어장(Vocabulary) DB 초기화 스크립트]
- 설계 목적: 정보시스템감리사 시험 대비 IT 용어 사전 겸 단어장 테이블을 생성합니다.
- 저장 위치: reports/exam_db/jolly_carson.db (기존 exam DB와 동일 파일, 별도 테이블로 관리)
- 테이블 구조:
  1. vocab_topics      — 토픽 트리 (대분류/소분류, parent_id로 자기 참조)
  2. vocab_terms       — 용어 카드 본체 (한글명, 영문명, 약자, 정의, 과목, 토픽, 빈도수 등)
  3. vocab_srs_state   — SM-2 스페이스드 리피티션 학습 상태 (ease_factor, interval, next_review 등)
  4. vocab_review_log  — 복습 이력 기록 (언제, 어떤 난이도로 응답했는지)
"""

import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VOCAB_DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")

# [설계 의도] 과목별 고정 대분류(1레벨). 소분류(2레벨)는 추출 시 문제 내용을 보고 자유롭게 생성됩니다.
# PM 외 과목은 기존 dashboard_mappings 테이블에 이미 구축되어 있는 "공식범위" 5대 분류 체계를 그대로 재사용하여
# 단어장 대분류와 기존 대시보드(예: se_official_scopes.html)의 분류 체계가 서로 어긋나지 않도록 합니다.
FIXED_MAJOR_TOPICS = {
    "PM": [
        "통합관리", "범위관리", "일정관리", "원가관리", "품질관리",
        "인적자원관리", "의사소통관리", "위험관리", "조달관리",
        "이해관계자관리", "감리업무", "대가산정", "법규/제도",
    ],
    "SE": [
        "요구사항분석 및 설계", "구현 및 테스트", "유지관리 및 운영",
        "개발방법론/SW구조/공개SW", "SW품질 및 비용산정",
    ],
    "DB": [
        "DB개념 및 설계", "DB언어", "DBMS 기술", "DB응용", "빅데이터 및 AI데이터",
    ],
    "SA": [
        "공통기술", "아키텍처 설계 및 구축", "데이터 통신 및 네트워크 설계", "기타 신기술",
    ],
    "SC": [
        "공통 보안 기술", "네트워크 및 시스템 보안", "응용 및 신기술 보안",
        "개발 및 운영 보안", "정보보호 법규 및 개인정보보호",
    ],
}


def init_vocabulary_db():
    """
    [설계 의도]
    jolly_carson.db에 이미 다른 테이블(exam_questions 등)이 있어도 IF NOT EXISTS 조건으로
    안전하게 실행되며, 기존 데이터를 파괴하지 않습니다. 최초 실행 시에만 단어장 테이블이 추가됩니다.
    """
    # DB 저장 디렉토리 보장
    os.makedirs(os.path.dirname(VOCAB_DB_PATH), exist_ok=True)

    conn = sqlite3.connect(VOCAB_DB_PATH)
    cursor = conn.cursor()

    # ==========================================
    # 1. vocab_topics 테이블 — 토픽 트리 (대분류/소분류)
    # ==========================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocab_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,              -- 과목 코드 (PM, SE, DB, SA, SC)
        name TEXT NOT NULL,                 -- 토픽 이름 (예: 원가관리, EVM분석)
        parent_id INTEGER,                  -- NULL이면 대분류(1레벨), 값이 있으면 그 부모의 소분류
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (parent_id) REFERENCES vocab_topics(id) ON DELETE CASCADE,
        UNIQUE (subject, parent_id, name)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_topics_subject ON vocab_topics(subject)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_topics_parent ON vocab_topics(parent_id)")

    # 과목별 고정 대분류 시드 삽입 (이미 있으면 건너뜀)
    # [주의] parent_id가 NULL인 대분류 행은 UNIQUE(subject, parent_id, name) 제약이
    # SQL의 NULL 비교 규칙(NULL은 서로 같다고 간주되지 않음) 때문에 중복을 막아주지 못하므로,
    # INSERT OR IGNORE 대신 반드시 존재 여부를 먼저 SELECT로 확인한 뒤 삽입합니다.
    for subject, majors in FIXED_MAJOR_TOPICS.items():
        for name in majors:
            cursor.execute(
                "SELECT id FROM vocab_topics WHERE subject = ? AND parent_id IS NULL AND name = ?",
                (subject, name)
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO vocab_topics (subject, name, parent_id) VALUES (?, ?, NULL)",
                    (subject, name)
                )

    # ==========================================
    # 2. vocab_terms 테이블 — 용어 카드 본체
    # ==========================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocab_terms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term_ko TEXT NOT NULL,              -- 한글 용어명 (예: 획득가치관리)
        term_en TEXT,                        -- 영문 원어 (예: Earned Value Management)
        abbreviation TEXT,                  -- 약자/축약어 (예: EVM)
        definition TEXT NOT NULL,           -- 정의/뜻 설명
        subject TEXT NOT NULL,              -- 과목 코드 (PM, SE, DB, SA, SC)
        topic_id INTEGER NOT NULL,          -- vocab_topics 외래키 (소분류 노드, 없으면 대분류 노드)
        frequency INTEGER NOT NULL DEFAULT 1, -- 기출문제 등장 횟수 (중요도 판단 지표)
        related_keywords TEXT,              -- 관련 키워드 (JSON array 문자열, 예: '["PV","AC","SPI"]')
        source TEXT,                        -- 출처/비고 (JSON array 문자열, 예: '["2024년 15번"]')
        is_starred INTEGER DEFAULT 0,      -- 즐겨찾기 여부 (0: 일반, 1: 즐겨찾기)
        is_hidden INTEGER DEFAULT 0,       -- 숨김(휴지통) 여부 (0: 일반, 1: 숨김 — 암기 완료 등으로 목록에서 감춤)
        mastery_level INTEGER DEFAULT 0,   -- 암기 상태 (0: 미학습, 1: 학습중, 2: 완료)
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (topic_id) REFERENCES vocab_topics(id) ON DELETE RESTRICT
    )
    """)

    # 검색 성능 향상을 위한 인덱스 생성
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_terms_subject ON vocab_terms(subject)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_terms_topic ON vocab_terms(topic_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_terms_abbreviation ON vocab_terms(abbreviation)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_terms_starred ON vocab_terms(is_starred)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_terms_hidden ON vocab_terms(is_hidden)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_terms_frequency ON vocab_terms(frequency)")

    # ==========================================
    # 3. vocab_srs_state 테이블 — SM-2 스페이스드 리피티션 학습 상태
    # ==========================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocab_srs_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term_id INTEGER NOT NULL UNIQUE,    -- vocab_terms 테이블 외래키 (1:1 관계)
        ease_factor REAL DEFAULT 2.5,       -- SM-2 난이도 계수 (초기값 2.5)
        interval_days REAL DEFAULT 0,        -- 현재 복습 간격 (일 단위)
        repetitions INTEGER DEFAULT 0,       -- 연속 정답 횟수
        next_review_at TEXT,                 -- 다음 복습 예정 일시
        last_reviewed_at TEXT,               -- 마지막 복습 일시
        FOREIGN KEY (term_id) REFERENCES vocab_terms(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_srs_next_review ON vocab_srs_state(next_review_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_srs_term_id ON vocab_srs_state(term_id)")

    # ==========================================
    # 4. vocab_review_log 테이블 — 복습 이력 기록
    # ==========================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocab_review_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term_id INTEGER NOT NULL,            -- vocab_terms 테이블 외래키
        quality INTEGER NOT NULL,            -- 응답 품질 (0: Again/모름, 1: Hard/어려움, 2: Good/보통, 3: Easy/쉬움)
        reviewed_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (term_id) REFERENCES vocab_terms(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_review_term ON vocab_review_log(term_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_review_date ON vocab_review_log(reviewed_at)")

    conn.commit()
    conn.close()

    print(f"[완료] 단어장 테이블 초기화 성공!")
    print(f"  → 경로: {VOCAB_DB_PATH}")
    print(f"  → 테이블: vocab_topics, vocab_terms, vocab_srs_state, vocab_review_log")
    print(f"  → 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    init_vocabulary_db()
