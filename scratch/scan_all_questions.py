# -*- coding: utf-8 -*-
import sqlite3
import re

DB_PATH = r"e:\jolly-carson\reports\exam_db\jolly_carson.db"

def scan():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, body FROM exam_questions")
    rows = cursor.fetchall()
    
    # 정답이나 답이 적혀있는 다양한 포맷 검색
    patterns = [
        r'\[답\]\s*[1-4]',
        r'\[정답\]\s*[1-4]',
        r'정답\s*:\s*[1-4]',
        r'답\s*:\s*[1-4]',
        r'정답\s*[1-4]',
        r'답\s*[1-4]',
        r'Ans\s*:\s*[1-4]',
        r'Answer\s*:\s*[1-4]',
        r'\(정답\)\s*[1-4]',
        r'\(답\)\s*[1-4]'
    ]
    
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    found_count = 0
    for row in rows:
        q_id, body = row
        for cp in compiled_patterns:
            matches = cp.findall(body)
            if matches:
                print(f"[FOUND] {q_id}: {matches} inside body")
                # 해당 매칭이 일어난 라인 출력
                for line in body.split('\n'):
                    if cp.search(line):
                        print(f"  Line: {line}")
                found_count += 1
                break
                
    print(f"Total matching questions: {found_count}")
    conn.close()

if __name__ == "__main__":
    scan()
