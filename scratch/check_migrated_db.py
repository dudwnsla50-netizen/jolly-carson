# -*- coding: utf-8 -*-
import sqlite3
import json

DB_PATH = r"e:\jolly-carson\reports\exam_db\jolly_carson.db"

def check():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, options, answer, explanation FROM exam_questions WHERE id='2025_25'")
    row = cursor.fetchone()
    if row:
        q_id, q, opts, ans, exp = row
        options_list = json.loads(opts)
        print(f"ID: {q_id}")
        print(f"Question: {q}")
        print(f"Options: {options_list}")
        print(f"Answer: {ans}")
        print(f"Explanation: {exp}")
    conn.close()

if __name__ == "__main__":
    check()
