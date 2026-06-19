# -*- coding: utf-8 -*-
import sqlite3
import re

DB_PATH = r"e:\jolly-carson\reports\exam_db\jolly_carson.db"

def check_html_tags():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, body FROM exam_questions")
    rows = cursor.fetchall()
    
    tag_patterns = [
        r"<u\b[^>]*>(.*?)</u>",
        r"<b\b[^>]*>(.*?)</b>",
        r"<strong\b[^>]*>(.*?)</strong>",
        r"<span\b[^>]*>(.*?)</span>"
    ]
    
    found_count = 0
    for row in rows:
        q_id, body = row
        found_tags = []
        for pat in tag_patterns:
            matches = re.findall(pat, body, re.IGNORECASE)
            if matches:
                found_tags.append((pat, matches))
        if found_tags:
            print(f"[Tags Found] {q_id}: {found_tags}")
            found_count += 1
            if found_count >= 15:
                break
                
    conn.close()

if __name__ == "__main__":
    check_html_tags()
