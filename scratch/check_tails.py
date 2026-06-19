# -*- coding: utf-8 -*-
import sqlite3

DB_PATH = r"e:\jolly-carson\reports\exam_db\jolly_carson.db"

def check_subjects_and_years():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 각 과목 및 연도별 샘플 2개씩 출력
    cursor.execute("SELECT DISTINCT subject, year FROM exam_questions ORDER BY subject, year")
    pairs = cursor.fetchall()
    
    for sub, yr in pairs:
        cursor.execute("SELECT id, body FROM exam_questions WHERE subject=? AND year=? LIMIT 1", (sub, yr))
        row = cursor.fetchone()
        if row:
            q_id, body = row
            # 끝부분 50자 출력
            tail = body[-80:].replace("\n", "\\n")
            print(f"[{sub} - {yr}] {q_id} tail: ... {tail}")
            
    conn.close()

if __name__ == "__main__":
    check_subjects_and_years()
