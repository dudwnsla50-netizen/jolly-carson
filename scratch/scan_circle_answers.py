# -*- coding: utf-8 -*-
import sqlite3
import re

DB_PATH = r"e:\jolly-carson\reports\exam_db\jolly_carson.db"

def scan():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, body FROM exam_questions")
    rows = cursor.fetchall()
    
    # 원숫자 정답 기호(①, ②, ③, ④ / ❶, ❷, ❸, ❹)가 정답 단어 뒤에 오는 패턴 검색
    patterns = [
        r'정답\s*:\s*[①②③④❶❷❸❹]',
        r'답\s*:\s*[①②③④❶❷❸❹]',
        r'정답\s*[①②③④❶❷❸❹]',
        r'답\s*[①②③④❶❷❸❹]',
        r'\[정답\]\s*[①②③④❶❷❸❹]',
        r'\[답\]\s*[①②③④❶❷❸❹]',
        r'\(정답\)\s*[①②③④❶❷❸❹]',
        r'\(답\)\s*[①②③④❶❷❸❹]'
    ]
    
    compiled_patterns = [re.compile(p) for p in patterns]
    
    found_count = 0
    for row in rows:
        q_id, body = row
        for cp in compiled_patterns:
            matches = cp.findall(body)
            if matches:
                print(f"[FOUND] {q_id}: {matches} inside body")
                for line in body.split('\n'):
                    if cp.search(line):
                        print(f"  Line: {line}")
                found_count += 1
                break
                
    print(f"Total matching questions: {found_count}")
    conn.close()

if __name__ == "__main__":
    scan()
