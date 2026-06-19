# -*- coding: utf-8 -*-
import sqlite3

DB_PATH = r"e:\jolly-carson\reports\exam_db\jolly_carson.db"

def analyze_symbols():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, body FROM exam_questions")
    rows = cursor.fetchall()
    
    filled_circles = ["❶", "❷", "❸", "❹"]
    star_marks = ["★", "☆"]
    check_marks = ["v", "V", "O", "X", "정답"]
    
    for row in rows:
        q_id, body = row
        # 1. 채워진 원 숫자가 들어있는지 검사
        has_filled = [sym for sym in filled_circles if sym in body]
        if has_filled:
            print(f"[Filled Circle] {q_id} has {has_filled}")
            
        # 2. 기타 정답 표시용으로 의심되는 기호가 본문 끝부분에 있는지
        for sym in ["정답", "답 :", "정답:", "답은", "Answer"]:
            if sym in body:
                print(f"[Keyword] {q_id}: found {sym}")
                
    conn.close()

if __name__ == "__main__":
    analyze_symbols()
