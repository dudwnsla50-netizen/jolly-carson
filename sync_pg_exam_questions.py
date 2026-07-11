# -*- coding: utf-8 -*-
"""
[PostgreSQL(Supabase) → 로컬 SQLite exam_questions 동기화 스크립트]
- 설계 목적: 운영 DB(Postgres)의 exam_questions 최신 데이터를 로컬 jolly_carson.db로 미러링합니다.
  단어 추출 등 로컬 작업이 항상 최신 기출문제 데이터를 기준으로 이뤄지도록 보장합니다.
- 방식: id 기준 INSERT OR REPLACE — 기존 로컬 행은 최신 내용으로 덮어쓰고, 신규 행은 추가됩니다.
"""

import os
import json
import sqlite3
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")

env_file_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file_path):
    with open(env_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"


def get_pg_connection():
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


def sync_exam_questions():
    print("[1/3] PostgreSQL 접속 중...")
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("""
        SELECT id, year, subject, question_num, question, options, answer, explanation,
               is_new_trend, similar_past_questions, ai_explanation, ai_explanation_model
        FROM exam_questions
    """)
    rows = pg_cursor.fetchall()
    pg_conn.close()
    print(f"  -> Postgres exam_questions {len(rows)}건 로드 완료")

    print("\n[2/3] 로컬 SQLite(jolly_carson.db)에 반영 중...")
    sq_conn = sqlite3.connect(SQLITE_DB_PATH)
    sq_cursor = sq_conn.cursor()

    for r in rows:
        sq_cursor.execute("""
            INSERT INTO exam_questions
                (id, year, subject, question_num, question, options, answer, explanation,
                 is_new_trend, similar_past_questions, ai_explanation, ai_explanation_model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                year=excluded.year, subject=excluded.subject, question_num=excluded.question_num,
                question=excluded.question, options=excluded.options, answer=excluded.answer,
                explanation=excluded.explanation, is_new_trend=excluded.is_new_trend,
                similar_past_questions=excluded.similar_past_questions,
                ai_explanation=excluded.ai_explanation, ai_explanation_model=excluded.ai_explanation_model
        """, (
            r["id"], r["year"], r["subject"], r["question_num"], r["question"], r["options"],
            r["answer"], r["explanation"], r["is_new_trend"], r["similar_past_questions"],
            r["ai_explanation"], r["ai_explanation_model"]
        ))

    sq_conn.commit()

    print("\n[3/3] 동기화 결과 확인")
    sq_cursor.execute("SELECT subject, COUNT(*) as cnt FROM exam_questions GROUP BY subject ORDER BY subject")
    for row in sq_cursor.fetchall():
        print(f"  {row[0]}: {row[1]}건")
    sq_conn.close()

    print(f"\n[완료] 총 {len(rows)}건 동기화 완료 -> {SQLITE_DB_PATH}")


if __name__ == "__main__":
    sync_exam_questions()
