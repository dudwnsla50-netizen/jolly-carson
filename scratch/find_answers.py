# -*- coding: utf-8 -*-
import sqlite3
import re

DB_PATH = r"e:\jolly-carson\reports\exam_db\jolly_carson.db"

def find_patterns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, body FROM exam_questions")
    rows = cursor.fetchall()
    
    print(f"Total rows: {len(rows)}")
    
    # 정답 패턴을 찾기 위한 시도
    # 예: body의 맨 끝 부분이 숫자인지, 혹은 "정답", "답" 등이 들어있는지
    sample_count = 0
    for row in rows:
        q_id, body = row
        # 1. body의 마지막 20글자 정도 확인
        tail = body[-30:].replace("\n", "\\n")
        # 2. 정답이나 답이라는 텍스트가 들어있는지
        if any(x in body for x in ["정답", "답:"]):
            print(f"[FOUND KEYWORD] {q_id}: ... {tail}")
            sample_count += 1
            if sample_count >= 10:
                break
                
    print("\n--- Show some tails ---")
    for row in rows[:15]:
        q_id, body = row
        tail = body[-40:].replace("\n", "\\n")
        print(f"{q_id}: ... {tail}")
        
    conn.close()

if __name__ == "__main__":
    find_patterns()
