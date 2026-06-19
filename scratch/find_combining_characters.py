# -*- coding: utf-8 -*-
import sqlite3
import unicodedata

DB_PATH = r"e:\jolly-carson\reports\exam_db\jolly_carson.db"

def find_combining():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, body FROM exam_questions")
    rows = cursor.fetchall()
    
    print(f"Scanning {len(rows)} records for combining characters or underlines...")
    
    found_count = 0
    for row in rows:
        q_id, body = row
        
        # 1. Combining underline (\u0332 등) 확인
        has_combining = False
        for char in body:
            if unicodedata.combining(char):
                has_combining = True
                break
                
        # 2. 일반적인 밑줄 문자나 취소선 문자 확인
        has_underline = '_' in body or '̲' in body or '̶' in body
        
        if has_combining or has_underline:
            print(f"[FOUND] {q_id}: combining={has_combining}, underline={has_underline}")
            found_count += 1
            if found_count >= 15:
                break
                
    conn.close()

if __name__ == "__main__":
    find_combining()
