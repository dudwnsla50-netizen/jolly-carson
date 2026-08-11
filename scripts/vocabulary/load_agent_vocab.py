# -*- coding: utf-8 -*-
"""
[에이전트 고품질 단어장 일괄 적재 스크립트]
- 설계 목적: 에이전트가 직접 생성한 고품질 용어 사전 JSON 파일(agent_ai_vocab.json)을 읽어
  jolly_carson.db의 SE, DB, SA, SC 과목에 대해 기존 데이터를 비우고 새롭게 적재합니다.
- PM 과목 데이터는 수집 품질이 양호하므로 그대로 보존하여 데이터 정합성을 유지합니다.
"""

import os
import sys
import json
import sqlite3

# Windows 콘솔 한글 깨짐 방지
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VOCAB_DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")
JSON_PATH = os.path.join(BASE_DIR, "data", "agent_ai_vocab.json")

SUBJECT_NAMES = {
    "PM": "사업관리(PM)",
    "SE": "소프트웨어공학(SE)",
    "DB": "데이터베이스(DB)",
    "SA": "시스템구조(SA)",
    "SC": "보안(SC)"
}

def load_agent_vocab():
    print("=" * 60)
    print("  [Agent-AI] 전 과목 고품질 용어 사전 일괄 적재 시작")
    print("=" * 60)
    
    if not os.path.exists(VOCAB_DB_PATH):
        print(f"[오류] 데이터베이스가 존재하지 않습니다: {VOCAB_DB_PATH}")
        sys.exit(1)
        
    if not os.path.exists(JSON_PATH):
        print(f"[오류] 용어 사전 JSON 파일이 존재하지 않습니다: {JSON_PATH}")
        sys.exit(1)
        
    # JSON 로드
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        vocab_list = json.load(f)
    print(f"  → JSON 파일로부터 {len(vocab_list)}개의 정제된 용어 로드 완료")
    
    conn = sqlite3.connect(VOCAB_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. 전 과목의 기존 데이터 비우기 (PM 포함 리셋)
        target_subjects = ["PM", "SE", "DB", "SA", "SC"]
        print(f"\n[1/3] 대상 과목({', '.join(target_subjects)})의 기존 데이터 초기화 중...")
        
        # 외래키 연쇄 삭제 또는 삭제 수행
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # srs_state 삭제
        cursor.execute("DELETE FROM vocab_srs_state")
        # review_log 삭제
        cursor.execute("DELETE FROM vocab_review_log")
        # terms 삭제
        cursor.execute("DELETE FROM vocab_terms")
        # topics 삭제 (소분류 삭제)
        cursor.execute("DELETE FROM vocab_topics WHERE parent_id IS NOT NULL")
        
        print("  → 기존 데이터 초기화 완료!")
        
        # 2. 용어 적재
        print("\n[2/3] 에이전트 AI 정제 데이터 DB 적재 중...")
        inserted = 0
        
        for item in vocab_list:
            subject = item["subject"].upper()
            term_ko = item["term_ko"].strip()
            term_en = item.get("term_en", "").strip() or None
            abbreviation = item.get("abbreviation", "").strip() or None
            definition = item["definition"].strip()
            topic_major = item["topic_major"].strip()
            topic_minor = item.get("topic_minor", "").strip() or None
            related_kw = item.get("related_keywords", [])
            source_val = item.get("source", "").strip()
            
            # 대분류 ID 확인 및 생성
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
                
            # 소분류 ID 확인 및 생성
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
                    
            related_kw_json = json.dumps(related_kw, ensure_ascii=False) if related_kw else None
            source_json = json.dumps([source_val] if source_val else [], ensure_ascii=False)
            
            # 용어 삽입
            cursor.execute("""
                INSERT INTO vocab_terms (term_ko, term_en, abbreviation, definition, subject, topic_id, frequency, related_keywords, source)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (term_ko, term_en, abbreviation, definition, subject, topic_id, related_kw_json, source_json))
            
            term_id = cursor.lastrowid
            
            # SRS 초기화 상태 삽입
            cursor.execute("""
                INSERT INTO vocab_srs_state (term_id, ease_factor, interval_days, repetitions, next_review_at)
                VALUES (?, 2.5, 0, 0, datetime('now', 'localtime'))
            """, (term_id,))
            inserted += 1
            
        conn.commit()
        print(f"  → 신규 데이터 {inserted}건 적재 완료!")
        
    except Exception as e:
        conn.rollback()
        print(f"  [오류] 데이터베이스 적재 실패: {e}")
        sys.exit(1)
    finally:
        conn.close()
        
    # 3. 전체 통계 출력
    print("\n[3/3] 최종 단어장 구축 상태 요약")
    print("=" * 60)
    
    conn = sqlite3.connect(VOCAB_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT subject, COUNT(*) as count 
        FROM vocab_terms 
        GROUP BY subject 
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    
    total = 0
    for r in rows:
        subj = r["subject"]
        name = SUBJECT_NAMES.get(subj, subj)
        count = r["count"]
        total += count
        
        cursor.execute("SELECT COUNT(*) FROM vocab_terms WHERE subject = ? AND abbreviation IS NOT NULL AND abbreviation != ''", (subj,))
        abbr_cnt = cursor.fetchone()[0]
        
        bar = "■" * min(int(count / 15), 25)
        print(f"  {name:15s} | {count:3d}개 (약어 {abbr_cnt:2d}개) {bar}")
        
    print("-" * 60)
    print(f"  누적 전체 용어 수: {total}개")
    print("=" * 60)
    conn.close()

if __name__ == "__main__":
    load_agent_vocab()
