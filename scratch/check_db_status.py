# -*- coding: utf-8 -*-
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")

def check_status():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT year, 
               COUNT(id) as total, 
               SUM(CASE WHEN answer IS NOT NULL THEN 1 ELSE 0 END) as has_answer,
               SUM(CASE WHEN answer IS NULL THEN 1 ELSE 0 END) as no_answer
        FROM exam_questions 
        WHERE subject='DB' 
        GROUP BY year
        ORDER BY year
    """)
    rows = cursor.fetchall()
    
    print("=== [DB 과목] 연도별 정답 적재 현황 ===")
    print(f"{'연도':<6} | {'전체 문항':<10} | {'정답 존재':<10} | {'정답 미매핑 (NULL)':<15}")
    print("-" * 55)
    for row in rows:
        print(f"{row[0]:<6} | {row[1]:<10} | {row[2]:<10} | {row[3]:<15}")
        
    cursor.execute("SELECT COUNT(id) FROM exam_questions WHERE subject='DB' AND answer IS NULL")
    total_db_null = cursor.fetchone()[0]
    print("-" * 55)
    print(f"-> DB 과목 전체 정답 누락 건수: {total_db_null}건")
    conn.close()

if __name__ == "__main__":
    check_status()
