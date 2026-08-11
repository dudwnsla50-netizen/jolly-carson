"""
analytics/input 폴더에 있는 Postgres CSV 덤프를 로컬 SQLite(jolly_carson.db)에 반영합니다.

- UPSERT 테이블: dashboard_mappings, exam_questions, quiz_history, srs_review_state, yearly_exam_history
  (sqlite와 CSV의 기본키 체계가 동일하게 유지되고 있어, 같은 키는 갱신하고 없는 키는 새로 추가합니다.)
- 전체 교체 테이블: vocab_topics, vocab_terms, vocab_srs_state
  (Postgres 쪽에서 시퀀스가 재적재되어 sqlite와 id 체계가 완전히 달라졌기 때문에,
   기존 행을 모두 지우고 CSV 내용으로 다시 채웁니다.)
"""
import csv
import sqlite3
import sys

csv.field_size_limit(sys.maxsize)

DB_PATH = "reports/exam_db/jolly_carson.db"
INPUT_DIR = "analytics/input"

UPSERT_TABLES = [
    ("dashboard_mappings", "dashboard_mappings_rows.csv", "id"),
    ("exam_questions", "exam_questions_rows.csv", "id"),
    ("quiz_history", "quiz_history_rows.csv", "id"),
    ("srs_review_state", "srs_review_state_rows.csv", "q_id"),
    ("yearly_exam_history", "yearly_exam_history_rows.csv", "id"),
]

# 부모(참조되는) 테이블부터 순서대로 재적재합니다.
REPLACE_TABLES = [
    ("vocab_topics", "vocab_topics_rows.csv"),
    ("vocab_terms", "vocab_terms_rows.csv"),
    ("vocab_srs_state", "vocab_srs_state_rows.csv"),
]


def coerce(value):
    if value is None:
        return None
    if value == "":
        return None
    low = value.lower()
    if low == "true":
        return 1
    if low == "false":
        return 0
    return value


def read_csv_rows(filename):
    path = f"{INPUT_DIR}/{filename}"
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def sqlite_columns(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def upsert_table(cur, table, filename, pk):
    csv_cols, rows = read_csv_rows(filename)
    db_cols = sqlite_columns(cur, table)
    cols = [c for c in csv_cols if c in db_cols]

    placeholders = ", ".join("?" for _ in cols)
    col_list = ", ".join(cols)
    update_cols = [c for c in cols if c != pk]
    update_clause = ", ".join(f"{c}=excluded.{c}" for c in update_cols)

    sql = f"""
        INSERT INTO {table} ({col_list}) VALUES ({placeholders})
        ON CONFLICT({pk}) DO UPDATE SET {update_clause}
    """

    values = [[coerce(row.get(c)) for c in cols] for row in rows]
    cur.executemany(sql, values)
    return len(values)


def replace_table(cur, table, filename):
    csv_cols, rows = read_csv_rows(filename)
    db_cols = sqlite_columns(cur, table)
    cols = [c for c in csv_cols if c in db_cols]

    placeholders = ", ".join("?" for _ in cols)
    col_list = ", ".join(cols)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    cur.execute(f"DELETE FROM {table}")
    values = [[coerce(row.get(c)) for c in cols] for row in rows]
    cur.executemany(sql, values)
    return len(values)


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=== UPSERT ===")
    for table, filename, pk in UPSERT_TABLES:
        before = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        n = upsert_table(cur, table, filename, pk)
        after = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: CSV {n}건 처리 | {before} -> {after}건")

    print("=== FULL REPLACE ===")
    for table, filename in REPLACE_TABLES:
        before = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        n = replace_table(cur, table, filename)
        after = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: CSV {n}건 처리 | {before} -> {after}건")

    conn.commit()
    conn.close()
    print("완료")


if __name__ == "__main__":
    main()
