# -*- coding: utf-8 -*-
"""
[DB 누락 데이터 정밀 진단]
- 설계 목적: options(보기)와 answer(정답)가 비어있는 레코드를 연도/과목별로 분석합니다.
"""
import sqlite3
import json

DB_PATH = 'reports/exam_db/jolly_carson.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("=" * 70)
print("[1] 전체 현황")
print("=" * 70)

c.execute("SELECT COUNT(*) FROM exam_questions")
total = c.fetchone()[0]

# options가 비어있는 레코드 (빈 배열 "[]" 이거나 NULL)
c.execute("""SELECT COUNT(*) FROM exam_questions 
             WHERE options IS NULL OR options = '' OR options = '[]'""")
empty_options = c.fetchone()[0]

# answer가 비어있는 레코드
c.execute("""SELECT COUNT(*) FROM exam_questions 
             WHERE answer IS NULL OR answer = '' OR answer = '[]'""")
empty_answer = c.fetchone()[0]

# 둘 다 비어있는 레코드
c.execute("""SELECT COUNT(*) FROM exam_questions 
             WHERE (options IS NULL OR options = '' OR options = '[]')
             AND (answer IS NULL OR answer = '' OR answer = '[]')""")
both_empty = c.fetchone()[0]

print(f"  전체 레코드: {total}")
print(f"  options 누락: {empty_options}")
print(f"  answer 누락: {empty_answer}")
print(f"  둘 다 누락: {both_empty}")

print("\n" + "=" * 70)
print("[2] 연도별 누락 현황")
print("=" * 70)

c.execute("""
    SELECT year, COUNT(*) as total,
           SUM(CASE WHEN options IS NULL OR options = '' OR options = '[]' THEN 1 ELSE 0 END) as missing_opts,
           SUM(CASE WHEN answer IS NULL OR answer = '' OR answer = '[]' THEN 1 ELSE 0 END) as missing_ans
    FROM exam_questions 
    GROUP BY year ORDER BY year
""")
for row in c.fetchall():
    print(f"  {row[0]}년: 전체 {row[1]}문항 | options 누락 {row[2]}개 | answer 누락 {row[3]}개")

print("\n" + "=" * 70)
print("[3] 과목별 누락 현황")
print("=" * 70)

c.execute("""
    SELECT subject, COUNT(*) as total,
           SUM(CASE WHEN options IS NULL OR options = '' OR options = '[]' THEN 1 ELSE 0 END) as missing_opts,
           SUM(CASE WHEN answer IS NULL OR answer = '' OR answer = '[]' THEN 1 ELSE 0 END) as missing_ans
    FROM exam_questions 
    GROUP BY subject ORDER BY subject
""")
for row in c.fetchall():
    print(f"  {row[0]}: 전체 {row[1]}문항 | options 누락 {row[2]}개 | answer 누락 {row[3]}개")

print("\n" + "=" * 70)
print("[4] 누락 샘플 (처음 10건)")
print("=" * 70)

c.execute("""
    SELECT id, year, subject, question_num, 
           CASE WHEN options IS NULL OR options = '' OR options = '[]' THEN 'X' ELSE 'O' END as has_opts,
           CASE WHEN answer IS NULL OR answer = '' OR answer = '[]' THEN 'X' ELSE 'O' END as has_ans,
           SUBSTR(question, 1, 40) as q_preview
    FROM exam_questions 
    WHERE (options IS NULL OR options = '' OR options = '[]')
       OR (answer IS NULL OR answer = '' OR answer = '[]')
    ORDER BY year, question_num
    LIMIT 10
""")
print(f"  {'ID':<12} {'년도':<6} {'과목':<4} {'번호':<4} {'보기':<4} {'정답':<4} 질문 미리보기")
print(f"  {'-'*12} {'-'*6} {'-'*4} {'-'*4} {'-'*4} {'-'*4} {'-'*30}")
for row in c.fetchall():
    print(f"  {row[0]:<12} {row[1]:<6} {row[2]:<4} {row[3]:<4} {row[4]:<4} {row[5]:<4} {row[6]}")

# [5] options가 있지만 빈 배열이거나 요소 수가 4 미만인 레코드
print("\n" + "=" * 70)
print("[5] options가 불완전한 레코드 (4개 미만)")
print("=" * 70)

c.execute("SELECT id, options FROM exam_questions WHERE options IS NOT NULL AND options != '' AND options != '[]'")
incomplete = []
for row in c.fetchall():
    try:
        opts = json.loads(row[1])
        if len(opts) < 4:
            incomplete.append((row[0], len(opts)))
    except:
        incomplete.append((row[0], -1))

print(f"  불완전한 보기 레코드: {len(incomplete)}건")
for item in incomplete[:5]:
    print(f"    {item[0]}: {item[1]}개 보기")

conn.close()
