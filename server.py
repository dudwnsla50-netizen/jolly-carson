# -*- coding: utf-8 -*-
# [Jolly-Carson REST API 웹서버 - SQLite & PostgreSQL 하이브리드 개정판]
# - 작성자: Antigravity
# - 설계 의도:
#   1. 로컬 환경에서는 네트워크 포트 차단이 없고 설정이 가벼운 SQLite3 파일 데이터베이스를 기본 사용합니다.
#   2. Render.com 프로덕션 환경에서는 환경변수 DATABASE_URL을 감지하여 원격 Supabase PostgreSQL 데이터베이스로 자동 전환합니다.
#   3. SQLite와 PostgreSQL 간의 SQL 플레이스홀더 문법 차이(%s vs ?)를 런타임에 자동 번역하는 쿼리 실행 헬퍼를 도입하여 소스 코드 중복을 제거합니다.
#   4. psycopg2.extras.RealDictCursor 및 sqlite3.Row의 리턴 형식을 통일성 있게 제어하여 API 비즈니스 로직을 변경 없이 양방향 지원합니다.
import os
import sys
import json
import sqlite3
import urllib.parse
import traceback
import psycopg2
import psycopg2.extras
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# [설계 의도]
# Render.com 배포 환경에 등록될 Supabase 연결 문자열 기본값 설정
# (비밀번호 특수문자 처리를 위해 안전한 인코딩 필터링을 거치게 설계)
SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
DATABASE_URL_RAW = os.environ.get("DATABASE_URL")

# [설계 변경]
# 로컬에서도 기본적으로 PostgreSQL(Supabase) 데이터베이스에 연결하도록 기본 DB_TYPE을 POSTGRES로 고정합니다.
# 다만 오프라인 환경 등에서 SQLite를 강제로 사용해야 할 경우를 위해 USE_SQLITE 환경변수를 통한 폴백 옵션을 제공합니다.
if os.environ.get("USE_SQLITE") == "true":
    DB_TYPE = "SQLITE"
else:
    DB_TYPE = "POSTGRES"

SQLITE_DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")

def get_db_connection():
    """
    [설계 의도]
    DB_TYPE 설정에 따라 SQLite 커넥션 또는 PostgreSQL 커넥션을 유연하게 반환합니다.
    - PostgreSQL의 경우 URL을 개별 파라미터로 디코딩하여 특수문자나 인코딩으로 인한 오류를 방지하고, 
      dict 타입 매핑을 위해 RealDictCursor를 제공합니다.
    - SQLite의 경우 Row 객체를 바인딩하여 dict-like 조회를 지원합니다.
    """
    if DB_TYPE == "POSTGRES":
        raw_url = DATABASE_URL_RAW if DATABASE_URL_RAW else SUPABASE_URL_RAW
        parsed = urllib.parse.urlparse(raw_url)
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
                    
        conn = psycopg2.connect(**conn_kwargs, cursor_factory=psycopg2.extras.RealDictCursor)
        conn.set_client_encoding('UTF8')
        return conn
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

from contextlib import contextmanager

@contextmanager
def get_db_cursor(conn):
    """
    [설계 의도]
    sqlite3.Cursor는 일부 Python 버전에서 context manager(with)를 미지원할 수 있습니다.
    psycopg2 커서와 sqlite3 커서 모두 안전하게 with 문으로 사용할 수 있도록 래핑 컨텍스트를 제공합니다.
    """
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()

def execute_query(cursor, query, params=None):
    """
    [설계 의도]
    PostgreSQL 규격(%s)으로 작성된 SQL 문을 SQLite 실행 규격(?)에 맞춰 실시간으로 포맷팅을 중재합니다.
    이를 통해 데이터베이스 기종이 변경되어도 API 로직 쿼리문을 일관되게 유지할 수 있습니다.
    """
    if DB_TYPE == "SQLITE":
        # SQLite에서는 %s 대신 ? 플레이스홀더를 사용하므로 변환해 줍니다.
        query = query.replace("%s", "?")
    
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)


class JollyCarsonRequestHandler(SimpleHTTPRequestHandler):
    
    def log_message(self, format, *args):
        sys.stderr.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS, POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path.startswith("/api/"):
            self.handle_api(path, query)
        else:
            super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/"):
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
            except Exception as e:
                self.send_error_response(400, f"Invalid JSON data: {str(e)}")
                return
                
            self.handle_post_api(path, data)
        else:
            self.send_error_response(404, "Not Found")

    def handle_post_api(self, path, data):
        if path == "/api/question/update":
            self.update_question(data)
        elif path == "/api/quiz/submit":
            self.submit_quiz(data)
        else:
            self.send_error_response(404, "API Endpoint Not Found")

    def handle_api(self, path, query):
        if path == "/api/dashboard":
            self.get_dashboard(query)
        elif path == "/api/question":
            self.get_question(query)
        elif path == "/api/questions":
            self.get_questions(query)
        elif path == "/api/quiz/stats":
            self.get_quiz_stats(query)
        elif path == "/api/quiz/total-exp":
            self.get_total_exp(query)
        else:
            self.send_error_response(404, "API Endpoint Not Found")

    def get_dashboard(self, query):
        subject = query.get("subject", [None])[0]
        dtype = query.get("type", [None])[0]
        
        if not subject or not dtype:
            self.send_error_response(400, "Missing parameters (subject, type)")
            return
            
        subject = subject.upper()
        dtype = dtype.lower()

        try:
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    # SQLite와 PostgreSQL 모두 CAST 및 || 문자열 결합 문법을 안전하게 지원하므로 공통 쿼리를 적용합니다.
                    sql = """
                    SELECT dm.concept, dm.category, dm.count, dm.core_concept, dm.features, dm.scope, 
                           COALESCE(eq.question, dm.rep_question) AS rep_question, 
                           dm.rep_year, dm.rep_num, dm.global_idx, dm.years, dm.questions
                    FROM dashboard_mappings dm
                    LEFT JOIN exam_questions eq ON eq.id = (CAST(dm.rep_year AS VARCHAR) || '_' || CAST(dm.rep_num AS VARCHAR)) 
                                               AND eq.subject = dm.subject
                    WHERE dm.subject = %s AND dm.dashboard_type = %s
                    ORDER BY dm.global_idx ASC
                    """
                    execute_query(cursor, sql, (subject, dtype))
                    rows = cursor.fetchall()
                    
                    data_list = []
                    for row in rows:
                        item = dict(row)
                        item["years"] = json.loads(item["years"]) if item["years"] else []
                        item["questions"] = json.loads(item["questions"]) if item["questions"] else []
                        data_list.append(item)
                        
                    self.send_json_response(data_list)
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def get_question(self, query):
        q_id = query.get("id", [None])[0]
        if not q_id:
            self.send_error_response(400, "Missing parameter (id)")
            return
            
        try:
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    sql = """
                        SELECT question, options, answer, explanation, subject 
                        FROM exam_questions 
                        WHERE id = %s
                    """
                    execute_query(cursor, sql, (q_id,))
                    row = cursor.fetchone()
                    if row:
                        row_dict = dict(row)
                        raw_answer = row_dict["answer"]
                        
                        if isinstance(raw_answer, int):
                            answer_val = [raw_answer]
                        elif isinstance(raw_answer, str) and raw_answer.strip():
                            try:
                                answer_val = json.loads(raw_answer)
                                if isinstance(answer_val, int):
                                    answer_val = [answer_val]
                            except Exception:
                                if raw_answer.isdigit():
                                    answer_val = [int(raw_answer)]
                                else:
                                    answer_val = []
                        else:
                            answer_val = []

                        self.send_json_response({
                            "id": q_id, 
                            "question": row_dict["question"],
                            "options": json.loads(row_dict["options"]) if row_dict["options"] else [],
                            "answer": answer_val,
                            "explanation": row_dict["explanation"],
                            "subject": row_dict["subject"]
                        })
                    else:
                        self.send_error_response(404, f"Question {q_id} Not Found")
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def get_questions(self, query):
        subject = query.get("subject", [None])[0]
        if not subject:
            self.send_error_response(400, "Missing parameter (subject)")
            return
            
        subject = subject.upper()
        try:
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    sql = """
                        SELECT id, subject, question, options, answer, explanation 
                        FROM exam_questions 
                        WHERE subject = %s
                    """
                    execute_query(cursor, sql, (subject,))
                    rows = cursor.fetchall()
                    
                    data_dict = {}
                    for row in rows:
                        item = dict(row)
                        item["options"] = json.loads(item["options"]) if item["options"] else []
                        
                        raw_answer = item["answer"]
                        if isinstance(raw_answer, int):
                            item["answer"] = [raw_answer]
                        elif isinstance(raw_answer, str) and raw_answer.strip():
                            try:
                                parsed_ans = json.loads(raw_answer)
                                if isinstance(parsed_ans, int):
                                    item["answer"] = [parsed_ans]
                                else:
                                    item["answer"] = parsed_ans
                            except Exception:
                                if raw_answer.isdigit():
                                    item["answer"] = [int(raw_answer)]
                                else:
                                    item["answer"] = []
                        else:
                            item["answer"] = []
                        data_dict[item["id"]] = item
                        
                    self.send_json_response(data_dict)
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def update_question(self, data):
        q_id = data.get("id")
        question = data.get("question")
        options = data.get("options")
        answer = data.get("answer")
        explanation = data.get("explanation")
        
        if not q_id or question is None or options is None:
            self.send_error_response(400, "Missing parameters (id, question, options)")
            return
            
        try:
            options_json = json.dumps(options, ensure_ascii=False)
            answer_json = json.dumps(answer) if answer and len(answer) > 0 else None
            
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    sql = """
                        UPDATE exam_questions 
                        SET question = %s, options = %s, answer = %s, explanation = %s
                        WHERE id = %s
                    """
                    execute_query(cursor, sql, (question, options_json, answer_json, explanation, q_id))
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        self.send_json_response({"success": True, "message": "Question updated successfully"})
                    else:
                        self.send_error_response(404, f"Question {q_id} Not Found in database")
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def submit_quiz(self, data):
        subject = data.get("subject")
        concept = data.get("concept")
        total_questions = data.get("total_questions")
        correct_count = data.get("correct_count")
        wrong_count = data.get("wrong_count")
        details = data.get("details")
        
        if not subject or not concept or total_questions is None or correct_count is None or wrong_count is None:
            self.send_error_response(400, "Missing parameters for quiz submission")
            return
            
        try:
            details_json = json.dumps(details, ensure_ascii=False) if details else None
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    sql = """
                        INSERT INTO quiz_history (subject, concept, total_questions, correct_count, wrong_count, details)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    execute_query(cursor, sql, (subject, concept, total_questions, correct_count, wrong_count, details_json))
                    conn.commit()
                    self.send_json_response({"success": True, "message": "Quiz attempt history saved successfully"})
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def get_quiz_stats(self, query):
        subject = query.get("subject", [None])[0]
        if not subject:
            self.send_error_response(400, "Missing parameter (subject)")
            return
            
        subject = subject.upper()
        try:
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    sql_concept = """
                        SELECT concept, 
                               COUNT(*) as attempt_count,
                               SUM(correct_count) as total_correct,
                               SUM(total_questions) as total_solved,
                               MAX(created_at) as last_attempt_at
                        FROM quiz_history
                        WHERE subject = %s
                        GROUP BY concept
                    """
                    execute_query(cursor, sql_concept, (subject,))
                    rows = cursor.fetchall()
                    stats_list = []
                    for row in rows:
                        item = dict(row)
                        # SQLite3는 Datetime 컬럼을 문자열로, psycopg2는 datetime 객체로 반환하므로 유연한 호환 포맷팅 적용
                        if item["last_attempt_at"]:
                            if isinstance(item["last_attempt_at"], str):
                                # SQLite의 기존 문자열 날짜 유지
                                pass
                            else:
                                item["last_attempt_at"] = item["last_attempt_at"].isoformat()
                        total_solved = item["total_solved"]
                        item["avg_score"] = round((item["total_correct"] * 100.0 / total_solved), 1) if total_solved > 0 else 0.0
                        stats_list.append(item)
                        
                    sql_summary = """
                        SELECT COUNT(*) as total_attempts,
                               SUM(correct_count) as total_correct,
                               SUM(total_questions) as total_solved
                        FROM quiz_history
                        WHERE subject = %s
                    """
                    execute_query(cursor, sql_summary, (subject,))
                    summary_row = cursor.fetchone()
                    summary = dict(summary_row) if summary_row else {"total_attempts": 0, "total_correct": 0, "total_solved": 0}
                    
                    if summary["total_attempts"] is None: summary["total_attempts"] = 0
                    if summary["total_correct"] is None: summary["total_correct"] = 0
                    if summary["total_solved"] is None: summary["total_solved"] = 0
                    
                    summary["avg_score"] = round((summary["total_correct"] * 100.0 / summary["total_solved"]), 1) if summary["total_solved"] > 0 else 0.0
                    
                    sql_logs = """
                        SELECT created_at, concept, total_questions, correct_count, wrong_count, details
                        FROM quiz_history
                        WHERE subject = %s
                        ORDER BY created_at DESC
                    """
                    execute_query(cursor, sql_logs, (subject,))
                    log_rows = cursor.fetchall()
                    logs_list = []
                    for r in log_rows:
                        d = dict(r)
                        if d["created_at"]:
                            if not isinstance(d["created_at"], str):
                                d["created_at"] = d["created_at"].isoformat()
                        logs_list.append(d)
                    
                    self.send_json_response({
                        "summary": summary,
                        "concepts": stats_list,
                        "logs": logs_list
                    })
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def get_total_exp(self, query):
        try:
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    sql = """
                        SELECT COALESCE(SUM(correct_count), 0) as total_exp
                        FROM quiz_history
                    """
                    execute_query(cursor, sql)
                    row = cursor.fetchone()
                    total_exp = dict(row)["total_exp"] if row else 0
                    
                    level = (total_exp // 10) + 1
                    exp_in_level = total_exp % 10
                    exp_to_next = 10
                    
                    self.send_json_response({
                        "total_exp": total_exp,
                        "level": level,
                        "exp_in_level": exp_in_level,
                        "exp_to_next": exp_to_next
                    })
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def send_json_response(self, data):
        try:
            response_content = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_content)))
            self.end_headers()
            self.wfile.write(response_content)
        except Exception as e:
            self.send_error_response(500, f"JSON Serialization error: {str(e)}")

    def send_error_response(self, status_code, message):
        response_content = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_content)))
        self.end_headers()
        self.wfile.write(response_content)


def init_quiz_history_table():
    """[설계 의도] SQLite 또는 PostgreSQL 등 기종에 맞는 퀴즈 히스토리 테이블을 생성/검증합니다."""
    try:
        with get_db_connection() as conn:
            with get_db_cursor(conn) as cursor:
                if DB_TYPE == "POSTGRES":
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quiz_history (
                        id SERIAL PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        subject TEXT NOT NULL,
                        concept TEXT NOT NULL,
                        total_questions INTEGER NOT NULL,
                        correct_count INTEGER NOT NULL,
                        wrong_count INTEGER NOT NULL,
                        details TEXT
                    );
                    """)
                else:
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
                conn.commit()
        print(f"[{DB_TYPE}] 퀴즈 이력(quiz_history) 테이블 검증/초기화 완료.")
    except Exception as e:
        print(f"[{DB_TYPE}] 경고 - 퀴즈 이력 테이블 초기화 중 예외가 발생했으나 시작을 속행합니다: {e}")


def main():
    global DB_TYPE
    os.chdir(BASE_DIR)
    
    # [설계 의도]
    # 만약 설정된 DB_TYPE이 POSTGRES이지만, Supabase 등 원격 DB 연결이 제한되거나 실패하는 환경인 경우
    # 퀴즈 제출 및 조회 시 에러가 발생하는 것을 방지하기 위해 로컬 SQLite 모드로 자동 폴백(Fallback)시킵니다.
    if DB_TYPE == "POSTGRES":
        raw_url = DATABASE_URL_RAW if DATABASE_URL_RAW else SUPABASE_URL_RAW
        try:
            parsed = urllib.parse.urlparse(raw_url)
            dbname = urllib.parse.unquote(parsed.path.lstrip("/")) if parsed.path else ""
            masked_host = f"{parsed.hostname}:{parsed.port or 5432}/{dbname}"
        except Exception:
            masked_host = raw_url.split("@")[-1] if "@" in raw_url else raw_url
        
        print(f"\n[데이터베이스 설정] 모드: {DB_TYPE}")
        print(f"  -> PostgreSQL 연결 시도 중 (호스트: {masked_host})")
        
        try:
            # 실시간 가용성 체크를 위한 가벼운 연결 확인
            conn = get_db_connection()
            conn.close()
            print("  -> PostgreSQL 연결 성공!")
        except Exception as e:
            print(f"  -> [경고] PostgreSQL 연결 실패: {e}")
            print("  -> [폴백] 로컬 SQLite 모드로 자동 전환하여 서버를 실행합니다.")
            DB_TYPE = "SQLITE"
            
    if DB_TYPE == "SQLITE":
        print(f"\n[데이터베이스 설정] 모드: {DB_TYPE}")
        print(f"  -> 로컬 SQLite 파일 연결 중 (경로: {SQLITE_DB_PATH})")
        
    try:
        init_quiz_history_table()
    except Exception as e:
        print(f"[Server] 경고: DB 연결 제한 상황에서 구동을 대기합니다. -> {e}")
        
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, JollyCarsonRequestHandler)
    print(f"========================================================")
    print(f"[Server] Jolly-Carson Hybrid Server Started Successfully")
    print(f"[Dashboard URL] http://localhost:{PORT}/reports/db_official_scopes.html")
    print(f"========================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[서버] 웹 API 서버 종료 중...")
        httpd.server_close()
        print("[서버] 웹 API 서버가 정상 종료되었습니다.")

if __name__ == "__main__":
    main()
