# -*- coding: utf-8 -*-
import sqlite3

DB_PATH = r"e:\jolly-carson\reports\exam_db\jolly_carson.db"

def check():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT body FROM exam_questions WHERE id='2016_54'")
    row = cursor.fetchone()
    if row:
        print("--- 2016_54 BODY ---")
        print(row[0])
    conn.close()

if __name__ == "__main__":
    check()
