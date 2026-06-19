# -*- coding: utf-8 -*-
import sqlite3
import re

DB_PATH = r"e:\jolly-carson\reports\exam_db\jolly_carson.db"

def find_bracket_answers():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, body FROM exam_questions")
    rows = cursor.fetchall()
    
    bracket_pattern = re.compile(r'\[[1-4]\]\s*$|\([1-4]\)\s*$|답:\s*[1-4]\s*$|정답:\s*[1-4]\s*$')
    digit_at_end = re.compile(r'\s+[1-4]\s*$')
    
    count = 0
    for row in rows:
        q_id, body = row
        # 끝 부분에 정답이 적혀있는지
        match = bracket_pattern.search(body)
        if match:
            print(f"[Match Bracket] {q_id}: {match.group(0)}")
            count += 1
            if count >= 10:
                break
        
        # 끝 부분이 그냥 숫자 하나로 끝나는지
        match_digit = digit_at_end.search(body)
        if match_digit:
            print(f"[Match Digit] {q_id}: {match_digit.group(0)}")
            count += 1
            if count >= 10:
                break
                
    conn.close()

if __name__ == "__main__":
    find_bracket_answers()
