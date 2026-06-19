# -*- coding: utf-8 -*-
"""
[DB 마이그레이션: answer 컬럼 INTEGER → TEXT(JSON 배열)]
- 설계 목적: 복수 정답을 지원하기 위해 answer 컬럼을 JSON 배열 문자열로 변환합니다.
- 예시: 기존 answer=1 → "[1]", answer=NULL → NULL
- 복수 정답 예시: "[1,3]" (①번과 ③번이 모두 정답)
"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reports', 'exam_db', 'jolly_carson.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 현재 answer 컬럼 타입 확인
    c.execute('PRAGMA table_info(exam_questions)')
    columns = c.fetchall()
    answer_col = [col for col in columns if col[1] == 'answer'][0]
    print(f"현재 answer 컬럼 타입: {answer_col[2]}")

    # 이미 TEXT 타입이면 중복 마이그레이션 방지
    if answer_col[2] == 'TEXT':
        # 이미 JSON 배열 형태인지 확인
        c.execute("SELECT answer FROM exam_questions WHERE answer IS NOT NULL LIMIT 1")
        sample = c.fetchone()
        if sample and sample[0] and str(sample[0]).startswith('['):
            print("이미 마이그레이션 완료된 상태입니다. 스킵합니다.")
            conn.close()
            return
    
    print("마이그레이션 시작: answer INTEGER → TEXT (JSON 배열)...")

    # 1. 새 테이블 생성 (answer 컬럼을 TEXT로 변경)
    c.execute('''CREATE TABLE IF NOT EXISTS exam_questions_new (
        id TEXT PRIMARY KEY,
        year INTEGER NOT NULL,
        subject TEXT NOT NULL,
        question_num INTEGER NOT NULL,
        question TEXT NOT NULL,
        options TEXT NOT NULL,
        answer TEXT,
        explanation TEXT
    )''')

    # 2. 기존 데이터 마이그레이션 (정수 → JSON 배열)
    c.execute('SELECT id, year, subject, question_num, question, options, answer, explanation FROM exam_questions')
    rows = c.fetchall()
    
    migrated_count = 0
    null_count = 0
    
    for row in rows:
        answer_val = row[6]
        if answer_val is not None:
            # 정수 정답을 단일 요소 배열로 변환
            answer_json = json.dumps([int(answer_val)])
            migrated_count += 1
        else:
            answer_json = None
            null_count += 1
        
        c.execute('''INSERT INTO exam_questions_new 
                     (id, year, subject, question_num, question, options, answer, explanation) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (row[0], row[1], row[2], row[3], row[4], row[5], answer_json, row[7]))

    # 3. 기존 테이블 삭제 후 신규 테이블로 교체
    c.execute('DROP TABLE exam_questions')
    c.execute('ALTER TABLE exam_questions_new RENAME TO exam_questions')
    
    conn.commit()
    
    # 4. 검증
    c.execute("SELECT COUNT(*) FROM exam_questions")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM exam_questions WHERE answer IS NOT NULL")
    with_answer = c.fetchone()[0]
    c.execute("SELECT id, answer FROM exam_questions WHERE answer IS NOT NULL LIMIT 3")
    samples = c.fetchall()
    
    print(f"\n[완료] 마이그레이션 완료!")
    print(f"  - 전체 레코드: {total}건")
    print(f"  - 정답 변환됨: {migrated_count}건 (INTEGER → JSON 배열)")
    print(f"  - 정답 미등록: {null_count}건")
    print(f"  - 샘플 데이터:")
    for s in samples:
        print(f"    {s[0]}: {s[1]}")
    
    conn.close()

if __name__ == "__main__":
    migrate()
