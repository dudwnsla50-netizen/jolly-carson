# -*- coding: utf-8 -*-
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")

def test_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*), COUNT(answer) FROM exam_questions")
    total, has_answer = cursor.fetchone()
    print(f"전체 문항 수: {total}, 정답 등록 문항 수: {has_answer}, 미등록 문항 수: {total - has_answer}")
    
    cursor.execute("SELECT id, question, answer FROM exam_questions WHERE answer IS NULL LIMIT 5")
    rows = cursor.fetchall()
    print("\n--- 정답 미등록 문항 예시 (최대 5건) ---")
    for r in rows:
        print(f"ID: {r[0]}")
        print(f"지문 일부: {r[1][:100]}...")
        print("-" * 40)
        
    conn.close()

if __name__ == "__main__":
    test_db()
