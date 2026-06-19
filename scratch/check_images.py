# -*- coding: utf-8 -*-
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")
IMAGE_DIR = os.path.join(BASE_DIR, "reports", "images")

def check_images():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM exam_questions")
    rows = cursor.fetchall()
    
    total = len(rows)
    existing_images = 0
    missing_ids = []
    
    for r in rows:
        q_id = r[0]
        img_path = os.path.join(IMAGE_DIR, f"{q_id}.png")
        if os.path.exists(img_path):
            existing_images += 1
        else:
            missing_ids.append(q_id)
            
    print(f"전체 문항 수: {total}")
    print(f"이미지 파일 존재 문항 수: {existing_images}")
    print(f"이미지 누락 문항 수: {total - existing_images}")
    if missing_ids:
        print(f"누락된 문항 ID 예시: {missing_ids[:10]}")
        
    conn.close()

if __name__ == "__main__":
    check_images()
