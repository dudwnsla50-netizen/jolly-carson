# -*- coding: utf-8 -*-
# [Jolly-Carson 로컬 SQLite3 데이터 마이그레이션 스크립트]
# - 작성자: Antigravity
# - 설계 의도:
#   1. e:\jolly-carson\analytics\input 디렉토리에 위치한 Supabase 추출 CSV 파일 3개
#      (dashboard_mappings_rows.csv, exam_questions_rows.csv, quiz_history_rows.csv)를 읽어옵니다.
#   2. 로컬 SQLite 데이터베이스(reports/exam_db/jolly_carson.db)에 접속하여 각 테이블이 존재하는지 검증하고,
#      없을 경우 각 컬럼과 호환되는 최적의 Schema로 테이블을 신설합니다.
#   3. 중복 저장 및 데이터 꼬임을 방지하기 위해 기존 로컬 데이터를 완전히 클리어한 후,
#      DictReader를 사용해 개행 및 쉼표 처리가 들어간 텍스트 데이터를 에러 없이 일괄 임포트(Bulk Insert)합니다.

import os
import csv
import sqlite3
import traceback

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")
INPUT_DIR = os.path.join(BASE_DIR, "analytics", "input")

CSV_FILES = {
    "dashboard_mappings": "dashboard_mappings_rows.csv",
    "exam_questions": "exam_questions_rows.csv",
    "quiz_history": "quiz_history_rows.csv"
}

def create_tables_if_not_exists(conn):
    """테이블이 존재할 경우 기존 스키마 강제 재구성을 위해 DROP한 후 DDL로 신설합니다."""
    cursor = conn.cursor()
    
    # [설계 의도]
    # 기존 데이터베이스 내에 이미 테이블이 존재하고 컬럼 제약 조건(예: NOT NULL)이 다르게 
    # 지정되어 있을 경우 발생하는 무결성 제약 오류를 방지하기 위해, 테이블을 DROP 한 후 재생성합니다.
    cursor.execute("DROP TABLE IF EXISTS quiz_history;")
    cursor.execute("DROP TABLE IF EXISTS exam_questions;")
    cursor.execute("DROP TABLE IF EXISTS dashboard_mappings;")
    
    # 1. quiz_history 테이블 생성
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        subject TEXT NOT NULL,
        concept TEXT NOT NULL,
        total_questions INTEGER NOT NULL,
        correct_count INTEGER NOT NULL,
        wrong_count INTEGER NOT NULL,
        details TEXT
    );
    """)
    
    # 2. exam_questions 테이블 생성
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_questions (
        id TEXT PRIMARY KEY,
        year INTEGER NOT NULL,
        subject TEXT NOT NULL,
        question_num INTEGER NOT NULL,
        question TEXT NOT NULL,
        options TEXT NOT NULL,
        answer TEXT,
        explanation TEXT
    );
    """)
    
    # 3. dashboard_mappings 테이블 생성
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dashboard_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        dashboard_type TEXT NOT NULL,
        concept TEXT NOT NULL,
        category TEXT,
        count INTEGER,
        core_concept TEXT,
        features TEXT,
        scope TEXT,
        rep_question TEXT,
        rep_year INTEGER,
        rep_num INTEGER,
        global_idx INTEGER,
        years TEXT,
        questions TEXT
    );
    """)
    
    conn.commit()
    print("[SQLite DB] 기존 테이블 삭제 후 재생성 및 구조 매핑 완료.")

def import_csv_to_table(conn, table_name, csv_filename):
    """CSV 파일을 읽어서 SQLite 테이블에 데이터를 임포트합니다."""
    csv_filepath = os.path.join(INPUT_DIR, csv_filename)
    if not os.path.exists(csv_filepath):
        print(f"[경고] CSV 파일이 존재하지 않습니다: {csv_filepath}")
        return
        
    print(f"[{table_name}] 마이그레이션 시작 -> 소스: {csv_filename}")
    
    cursor = conn.cursor()
    
    # 기존 데이터 청소 (Import 오버라이트 대응)
    cursor.execute(f"DELETE FROM {table_name}")
    
    # CSV 데이터 파싱 및 삽입
    # UTF-8 인코딩 명시 및 DictReader 사용
    with open(csv_filepath, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        # 쿼리 플레이스홀더 생성
        placeholders = ", ".join(["?"] * len(headers))
        columns = ", ".join(headers)
        insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        inserted_count = 0
        batch_data = []
        
        for row in reader:
            # CSV 데이터의 필드 순서에 맞춰 튜플 리스트화
            val_tuple = tuple(row[col] if row[col] != "" else None for col in headers)
            batch_data.append(val_tuple)
            inserted_count += 1
            
            # 500개씩 벌크 인서트 수행
            if len(batch_data) >= 500:
                cursor.executemany(insert_sql, batch_data)
                batch_data = []
                
        # 남은 배치 잔여분 처리
        if batch_data:
            cursor.executemany(insert_sql, batch_data)
            
    conn.commit()
    print(f"[{table_name}] 성공적으로 완료되었습니다. (총 {inserted_count}개 행 적재 완료)")

def main():
    print("==================================================")
    print("[Jolly-Carson] Supabase CSV 데이터 -> SQLite 임포터 기동")
    print(f"  -> SQLite 경로: {DB_PATH}")
    print(f"  -> CSV 입력 경로: {INPUT_DIR}")
    print("==================================================")
    
    # SQLite 상위 폴더 생성 (혹시 없을 경우 대비)
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"[알림] DB 디렉토리가 생성되었습니다: {db_dir}")
        
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(DB_PATH)
        
        # 1. 테이블 확인 및 스키마 선설
        create_tables_if_not_exists(conn)
        
        # 2. 과목 데이터 임포트
        for table_name, csv_filename in CSV_FILES.items():
            import_csv_to_table(conn, table_name, csv_filename)
            
        conn.close()
        print("\n[성공] 모든 데이터 마이그레이션이 성공적으로 완료되었습니다!")
        
    except Exception as e:
        print("\n[실패] 마이그레이션 중 예외 오류 발생:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
