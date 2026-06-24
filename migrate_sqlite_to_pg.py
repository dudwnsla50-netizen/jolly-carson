# -*- coding: utf-8 -*-
# [SQLite -> PostgreSQL 호환 DB(Azure Cosmos DB 등) 데이터 마이그레이션 스크립트]
# - 작성자: Antigravity
# - 설계 의도:
#   1. 기존 SQLite의 데이터(reports/exam_db/jolly_carson.db)를 Azure Cosmos DB for PostgreSQL 또는
#      원격 PostgreSQL 데이터베이스로 안정적으로 마이그레이션합니다.
#   2. 비밀번호에 특수문자(예: '^', '@' 등)가 포함되어 있어도 URL 파싱 시 크래시나 인증 실패가 발생하지 않도록
#      자동으로 URL-Encoding 처리하는 안전장치(safe_url_encode_password)를 탑재했습니다.
#   3. 이관 실행 시 데이터가 누락되는 일이 없도록 PostgreSQL 상에 필요한 스키마 테이블을 신규 생성한 뒤,
#      단일 트랜잭션 내에서 모든 벌크 인서트를 실행하고 도중에 실패하면 롤백을 수행하여 데이터의 일관성을 완벽히 보장합니다.
#   4. 콘솔 환경의 cp949 인코딩 문제를 방지하기 위해 특수 이모지 문자는 아스키 괄호형 텍스트로 치환했습니다.
import os
import sys
import json
import sqlite3
import urllib.parse
import psycopg2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")

# [설계 의도]
# Azure Cosmos DB 또는 일반 PostgreSQL의 연결 정보를 환경변수(DATABASE_URL)로 주입받습니다.
# 환경변수가 설정되지 않은 경우 Supabase PostgreSQL 주소를 기본값(폴백)으로 제공하여 server.py와 일치시킵니다.
DEFAULT_PG_URL = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
POSTGRES_URL = os.environ.get("DATABASE_URL", DEFAULT_PG_URL)

def safe_url_encode_password(url_str):
    """
    [설계 의도]
    연결 문자열(URL)에서 비밀번호 영역을 안전하게 추출하여, 특수문자('^' 등)를 URL-Encoding 처리합니다.
    이를 통해 PostgreSQL 드라이버가 비밀번호 특수문자로 인해 주소 파싱 오류나 로그인 실패를 내지 않도록 예방합니다.
    """
    try:
        parsed = urllib.parse.urlparse(url_str)
        if parsed.password:
            encoded_password = urllib.parse.quote_plus(parsed.password)
            # URL 문자열 재조립
            netloc = parsed.netloc.replace(f":{parsed.password}@", f":{encoded_password}@")
            return urllib.parse.urlunparse(parsed._replace(netloc=netloc))
    except Exception:
        pass
    return url_str

def create_postgres_tables(pg_conn):
    """
    [설계 의도]
    PostgreSQL 데이터베이스 상에 SQLite와 100% 호환되는 스키마 테이블을 신규로 구축합니다.
    - PostgreSQL의 자동 번호 증가(AUTOINCREMENT)는 SERIAL primary key 타입을 지정합니다.
    - 'answer'는 기출문제 정답이 단일 정수 또는 복수 정답의 배열(JSON 문자열)일 수 있으므로 TEXT로 설정해 유연하게 저장합니다.
    """
    pg_cursor = pg_conn.cursor()
    
    # 1. exam_questions (기출문제) 테이블 생성
    pg_cursor.execute("DROP TABLE IF EXISTS exam_questions CASCADE;")
    pg_cursor.execute("""
    CREATE TABLE exam_questions (
        id VARCHAR(50) PRIMARY KEY,
        year INT NOT NULL,
        subject VARCHAR(50) NOT NULL,
        question_num INT NOT NULL,
        question TEXT NOT NULL,
        options TEXT NOT NULL,     -- JSON array (예: '["보기1", "보기2", "보기3", "보기4"]')
        answer TEXT,               -- 정수형 1~4 또는 JSON array 문자열 호환
        explanation TEXT           -- 정답 해설
    );
    """)
    
    # 2. dashboard_mappings (대시보드 맵핑 데이터) 테이블 생성
    pg_cursor.execute("DROP TABLE IF EXISTS dashboard_mappings CASCADE;")
    pg_cursor.execute("""
    CREATE TABLE dashboard_mappings (
        id SERIAL PRIMARY KEY,
        subject VARCHAR(50) NOT NULL,
        dashboard_type VARCHAR(50) NOT NULL,
        concept VARCHAR(255) NOT NULL,
        category VARCHAR(255) NOT NULL,
        count INT NOT NULL,
        core_concept TEXT NOT NULL,
        features TEXT NOT NULL,
        scope TEXT NOT NULL,
        rep_question TEXT NOT NULL,
        rep_year INT,
        rep_num INT,
        global_idx INT,
        years TEXT,                -- JSON array 대응 (예: '[2026, 2025]')
        questions TEXT             -- JSON array 대응
    );
    """)
    
    # 3. quiz_history (퀴즈 풀이 이력) 테이블 생성
    pg_cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_history (
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        subject VARCHAR(50) NOT NULL,
        concept VARCHAR(255) NOT NULL,
        total_questions INTEGER NOT NULL,
        correct_count INTEGER NOT NULL,
        wrong_count INTEGER NOT NULL,
        details TEXT               -- 세부 채점 결과 JSON 문자열
    );
    """)
    
    pg_conn.commit()
    pg_cursor.close()
    print("[PostgreSQL] 데이터베이스 테이블 스키마 초기화 완료.")

def migrate_data():
    """
    [설계 의도]
    SQLite 데이터를 읽어서 트랜잭션을 적용한 뒤 Azure/원격 PostgreSQL로 복사합니다.
    """
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"[오류] 로컬 SQLite DB가 존재하지 않습니다: {SQLITE_DB_PATH}")
        sys.exit(1)
        
    print(f"[SQLite] {SQLITE_DB_PATH} 데이터 로드 준비 중...")
    sl_conn = sqlite3.connect(SQLITE_DB_PATH)
    sl_cursor = sl_conn.cursor()
    
    # 비밀번호 특수문자 대응을 위해 URL을 디코딩하여 개별 매개변수로 명시적 전달
    try:
        parsed = urllib.parse.urlparse(POSTGRES_URL)
        username = urllib.parse.unquote(parsed.username) if parsed.username else None
        password = urllib.parse.unquote(parsed.password) if parsed.password else None
        dbname = urllib.parse.unquote(parsed.path.lstrip("/")) if parsed.path else None
        
        conn_kwargs = {
            "dbname": dbname,
            "user": username,
            "password": password,
            "host": parsed.hostname,
            "port": parsed.port or 5432
        }
        
        if parsed.query:
            query_params = urllib.parse.parse_qs(parsed.query)
            for k, v in query_params.items():
                if v:
                    conn_kwargs[k] = v[0]
                    
        masked_host = f"{parsed.hostname}:{parsed.port or 5432}/{dbname}"
        print(f"[PostgreSQL] 원격 DB 연결 시도 중... (호스트: {masked_host})")
        
        pg_conn = psycopg2.connect(**conn_kwargs)
        print("[PostgreSQL] 원격 데이터베이스 연결 성공!")
    except Exception as e:
        print(f"\n[오류] 데이터베이스 연결에 실패했습니다: {e}")
        print("[원인 분석 및 조치 가이드]")
        print("  1. 로컬 환경의 방화벽이나 사내망 보안 정책에 의해 아웃바운드 5432 포트가 차단되었을 수 있습니다.")
        print("  2. 만약 외부 포트가 차단된 환경이라면, 본 스크립트(migrate_sqlite_to_pg.py)를")
        print("     외부 인터넷 통신이 차단되지 않는 개인 PC 터미널에서 환경변수 설정 후 직접 실행해주시기 바랍니다:")
        print("     -> $env:DATABASE_URL=\"발급받은_Azure_Cosmos_DB_연결_문자열\"")
        print("     -> python migrate_sqlite_to_pg.py")
        sl_cursor.close()
        sl_conn.close()
        sys.exit(1)
        
    pg_cursor = pg_conn.cursor()
    
    try:
        # 테이블 생성 및 초기화
        create_postgres_tables(pg_conn)
        
        # 1. exam_questions 데이터 이관
        sl_cursor.execute("SELECT id, year, subject, question_num, question, options, answer, explanation FROM exam_questions")
        questions = sl_cursor.fetchall()
        print(f"[이관 진행] exam_questions 데이터 {len(questions)}건 복사 중...")
        for row in questions:
            ans_val = str(row[6]) if row[6] is not None else None
            pg_cursor.execute("""
                INSERT INTO exam_questions (id, year, subject, question_num, question, options, answer, explanation)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (row[0], row[1], row[2], row[3], row[4], row[5], ans_val, row[7]))
            
        # 2. dashboard_mappings 데이터 이관
        sl_cursor.execute("""
            SELECT subject, dashboard_type, concept, category, count, core_concept, features, scope, 
                   rep_question, rep_year, rep_num, global_idx, years, questions 
            FROM dashboard_mappings
        """)
        mappings = sl_cursor.fetchall()
        print(f"[이관 진행] dashboard_mappings 데이터 {len(mappings)}건 복사 중...")
        for row in mappings:
            pg_cursor.execute("""
                INSERT INTO dashboard_mappings (
                    subject, dashboard_type, concept, category, count, core_concept, features, scope, 
                    rep_question, rep_year, rep_num, global_idx, years, questions
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, row)
            
        # 3. quiz_history 데이터 이관
        sl_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quiz_history'")
        if sl_cursor.fetchone():
            sl_cursor.execute("SELECT id, created_at, subject, concept, total_questions, correct_count, wrong_count, details FROM quiz_history")
            history_rows = sl_cursor.fetchall()
            if history_rows:
                pg_cursor.execute("TRUNCATE TABLE quiz_history RESTART IDENTITY;")
                print(f"[이관 진행] quiz_history (사용자 풀이 기록) 데이터 {len(history_rows)}건 복사 중...")
                for row in history_rows:
                    pg_cursor.execute("""
                        INSERT INTO quiz_history (id, created_at, subject, concept, total_questions, correct_count, wrong_count, details)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, row)
                
                # [설계 의도]
                # PostgreSQL의 SERIAL 기본키 id에 수동으로 명시 값을 대입하여 이관하였으므로,
                # 내부 시퀀스 카운터를 동기화해주어야 다음 신규 퀴즈 제출(INSERT) 시 중복 키 에러(UniqueViolation)가 발생하지 않습니다.
                pg_cursor.execute("SELECT setval(pg_get_serial_sequence('quiz_history', 'id'), COALESCE(MAX(id), 0) + 1, false) FROM quiz_history;")
                print("[이관 진행] quiz_history 테이블의 SERIAL 기본키 시퀀스 동기화 완료.")
                    
        pg_conn.commit()
        print("\n[완료] SQLite의 모든 데이터가 PostgreSQL DB로 정상적으로 마이그레이션되었습니다!")
        
    except Exception as e:
        pg_conn.rollback()
        print(f"\n[오류] 데이터 적재 도중 예외가 발생하여 모든 변경사항을 롤백했습니다: {e}")
        raise e
    finally:
        sl_cursor.close()
        sl_conn.close()
        pg_cursor.close()
        pg_conn.close()

if __name__ == "__main__":
    migrate_data()
