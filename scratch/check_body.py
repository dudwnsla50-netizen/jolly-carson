# -*- coding: utf-8 -*-
import sqlite3
import os

DB_PATH = r"e:\jolly-carson\reports\exam_db\jolly_carson.db"

def check():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, body FROM exam_questions LIMIT 10")
    rows = cursor.fetchall()
    for row in rows:
        q_id, body = row
        print(f"ID: {q_id}")
        print("BODY START ----")
        print(body)
        print("BODY END ------\n")
    conn.close()

if __name__ == "__main__":
    check()
