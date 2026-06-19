# -*- coding: utf-8 -*-
"""누락 레코드 상세 확인"""
import sqlite3
import json
import sys, io
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = 'reports/exam_db/jolly_carson.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print("=== options 누락/불완전 레코드 ===")
c.execute("""SELECT id, year, subject, question_num, options, 
             SUBSTR(question, 1, 50) 
             FROM exam_questions 
             WHERE options IS NULL OR options = '' OR options = '[]'
             ORDER BY year, question_num""")
for r in c.fetchall():
    print(f"  {r[0]:>10} | {r[1]} | {r[2]:>2} | {r[3]:>3}번 | opts={r[4]} | Q: {r[5]}")

print("\n=== 불완전 보기 (4개 미만) ===")
c.execute("SELECT id, options FROM exam_questions WHERE options IS NOT NULL AND options != '' AND options != '[]'")
for r in c.fetchall():
    try:
        opts = json.loads(r[1])
        if len(opts) < 4:
            print(f"  {r[0]:>10} | {len(opts)}개 보기 | {[o[:30] for o in opts]}")
    except:
        print(f"  {r[0]:>10} | 파싱실패 | {r[1][:50]}")

print("\n=== answer 누락 레코드 (연도별 문항 번호 목록) ===")
c.execute("""SELECT year, GROUP_CONCAT(question_num, ',') as nums, COUNT(*) as cnt
             FROM exam_questions 
             WHERE answer IS NULL OR answer = '' OR answer = '[]'
             GROUP BY year ORDER BY year""")
for r in c.fetchall():
    nums = r[1].split(',')
    preview = ', '.join(nums[:20])
    suffix = f" ... +{len(nums)-20}건" if len(nums) > 20 else ""
    print(f"  {r[0]}년 ({r[2]:>3}건): {preview}{suffix}")

conn.close()
