# -*- coding: utf-8 -*-
"""
[누락 23개 문항 본문 및 보기 조회 스크립트]
- 목적: 여전히 DB 내에 정답이 누락된 23개 문항에 대해 질문 지문과 보기 문항 전체를 예쁘게 출력하여 사람이 직접 정답을 판독할 수 있도록 돕습니다.
"""
import sqlite3
import sys
import io
import json

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = 'reports/exam_db/jolly_carson.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    target_ids = (
        "2015_44", "2015_66", "2015_115", "2015_117",
        "2016_33", "2016_35", "2016_49", "2016_60", "2016_63", "2016_72", "2016_109",
        "2017_58", "2017_69",
        "2018_2", "2018_17", "2018_98",
        "2022_57",
        "2025_1", "2025_2", "2025_4", "2025_5", "2025_6",
        "2026_3"
    )
    c.execute(f"""SELECT id, year, subject, question_num, question, options 
                 FROM exam_questions 
                 WHERE id IN {target_ids}
                 ORDER BY year, question_num""")
                 
    rows = c.fetchall()
    out_path = 'scratch/missing_details.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"=== 정답 누락 23건 본문 조회 (총 {len(rows)}건) ===\n")
        for row in rows:
            q_id, year, subject, q_num, question, options_json = row
            options = json.loads(options_json) if options_json else []
            f.write(f"\n--------------------------------------------------\n")
            f.write(f"▶ ID: {q_id} ({year}년 {subject}과목 {q_num}번)\n")
            f.write(f"질문:\n{question}\n")
            f.write("보기:\n")
            for idx, opt in enumerate(options):
                f.write(f"  {idx+1}. {opt}\n")
    print("Done writing to scratch/missing_details.txt")
    conn.close()

if __name__ == "__main__":
    main()
