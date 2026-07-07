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
import urllib.request
import traceback
import psycopg2
import psycopg2.extras
import re
from http.server import SimpleHTTPRequestHandler
try:
    from http.server import ThreadingHTTPServer
except ImportError:
    from socketserver import ThreadingTCPServer
    from http.server import HTTPServer
    class ThreadingHTTPServer(ThreadingTCPServer, HTTPServer):
        allow_reuse_address = True

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

# [설계 의도] 로컬 개발용 .env 파일 자동 파서 내장 (외부 라이브러리 의존성 배제)
env_file_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file_path):
    try:
        with open(env_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
    except Exception as env_ex:
        print(f"[Warning] .env 파일 로드 중 실패: {env_ex}")

# [설계 의도] 로컬 개발용 .env 파일 자동 파서 내장 (외부 라이브러리 의존성 배제)
env_file_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file_path):
    try:
        with open(env_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
    except Exception as env_ex:
        print(f"[Warning] .env 파일 로드 중 실패: {env_ex}")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def call_gemini_raw_prompt(prompt):
    if not GEMINI_API_KEY:
        return ""
    try:
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as res:
            data = json.loads(res.read().decode("utf-8"))
            raw_response = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return raw_response
    except Exception as e:
        print(f"[Gemini API] 호출 오류: {e}")
        return ""

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
        elif path == "/api/yearly-exam/submit":
            self.submit_yearly_exam(data)
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
        elif path == "/api/db-mode":
            self.get_db_mode(query)
        elif path == "/api/analytics/concept-diagnostics":
            self.get_concept_diagnostics(query)
        elif path == "/api/analytics/check-report":
            self.check_analytics_report(query)
        elif path == "/api/yearly-exams":
            self.get_yearly_exams(query)
        elif path == "/api/yearly-exam/questions":
            self.get_yearly_exam_questions(query)
        elif path == "/api/yearly-exam/history":
            self.get_yearly_exam_history(query)
        elif path == "/api/yearly-exam/ai-diagnose":
            self.get_yearly_exam_ai_diagnose(query)
        elif path == "/api/law-guide":
            self.get_law_guide_content(query)
        else:
            self.send_error_response(404, "API Endpoint Not Found")

    def get_law_guide_content(self, query):
        """[설계 의도] 지정된 법규/가이드 요약 파일의 한글 텍스트 내용을 안전하게 읽어 반환합니다."""
        try:
            file_name = query.get("file", [None])[0]
            if not file_name:
                self.send_error_response(400, "Missing parameter (file)")
                return
            
            # 디렉토리 순회(Directory Traversal) 공격 차단 유효성 검증
            if ".." in file_name or "/" in file_name or "\\" in file_name:
                self.send_error_response(400, "Invalid file path")
                return

            base_path = "d:/100.lyj/anti_workspace/감리사_시험대비/가이드및법규"
            filepath = os.path.join(base_path, file_name)
            
            if not os.path.exists(filepath):
                self.send_error_response(404, "Law/Guide file not found")
                return

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            self.send_json_response({
                "success": True,
                "file": file_name,
                "content": content
            })
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Error reading law file: {str(e)}")

    def get_concept_diagnostics(self, query):
        try:
            with get_db_connection() as conn:
                # [설계 의도] 
                # 순환 참조 문제를 완벽하게 회피하고, 초기 구동 성능을 위해 
                # 분석 모듈을 호출 함수 시점에 지연 임포트(Lazy Import)합니다.
                from analytics import analyze_student_history
                result = analyze_student_history(conn, DB_TYPE)
                self.send_json_response(result)
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database analytics error: {str(e)}")

    def check_analytics_report(self, query):
        """[설계 의도] 오답 분석 리포트 HTML 파일의 존재 여부를 확인합니다 (404 콘솔 로그 노출 차단 방지 목적)."""
        try:
            date_str = query.get("date", [None])[0]
            if not date_str:
                self.send_json_response({"exists": False})
                return
            
            # 파일 규칙: diagnostics_report_YYMMDD.html
            filename = f"diagnostics_report_{date_str}.html"
            filepath = os.path.join(BASE_DIR, "analytics", "output", filename)
            
            exists = os.path.exists(filepath)
            self.send_json_response({"exists": exists})
        except Exception as e:
            traceback.print_exc()
            self.send_json_response({"exists": False})

    def get_db_mode(self, query):
        self.send_json_response({"db_type": DB_TYPE})

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
                        SELECT question, options, answer, explanation, subject, is_new_trend, similar_past_questions 
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

                        # similar_past_questions JSON 파싱 처리
                        sim_past = row_dict.get("similar_past_questions")
                        if sim_past:
                            try:
                                sim_past_val = json.loads(sim_past)
                            except:
                                sim_past_val = []
                        else:
                            sim_past_val = []

                        self.send_json_response({
                            "id": q_id, 
                            "question": row_dict["question"],
                            "options": json.loads(row_dict["options"]) if row_dict["options"] else [],
                            "answer": answer_val,
                            "explanation": row_dict["explanation"],
                            "subject": row_dict["subject"],
                            "is_new_trend": row_dict.get("is_new_trend", 0),
                            "similar_past_questions": sim_past_val
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
                        SELECT id, subject, question, options, answer, explanation, is_new_trend, similar_past_questions 
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
                            
                        # similar_past_questions JSON 파싱
                        sim_past = item.get("similar_past_questions")
                        if sim_past:
                            try:
                                item["similar_past_questions"] = json.loads(sim_past)
                            except:
                                item["similar_past_questions"] = []
                        else:
                            item["similar_past_questions"] = []
                            
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

    def _fetch_stats_for_subject(self, cursor, subject):
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
            if item["last_attempt_at"]:
                if isinstance(item["last_attempt_at"], str):
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
            
        return {
            "summary": summary,
            "concepts": stats_list,
            "logs": logs_list
        }

    def get_quiz_stats(self, query):
        subject = query.get("subject", [None])[0]
        if not subject:
            subject = "ALL"
            
        subject = subject.upper()
        try:
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    if subject == "ALL":
                        subjects = ['DB', 'SE', 'PM', 'SA', 'SC']
                        all_results = []
                        for sub in subjects:
                            all_results.append(self._fetch_stats_for_subject(cursor, sub))
                        self.send_json_response(all_results)
                    else:
                        result = self._fetch_stats_for_subject(cursor, subject)
                        self.send_json_response(result)
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def get_total_exp(self, query):
        # [설계 의도]
        # 사용자가 과목별로 경험치(EXP)를 획득하고 관리할 수 있도록, 
        # 쿼리 파라미터로 subject가 제공될 경우 해당 과목의 경험치 정보만 반환합니다.
        # subject가 누락된 경우에는 전체 누적 경험치 정보와 함께 
        # 5대 과목별 개별 경험치 맵(subjects_exp)을 일괄적으로 계산하여 반환합니다.
        # 이 때, 수험생의 동기부여를 위해 오늘 푼 총 문제 수(today_solved)를
        # 로컬 오늘 자정(KST 00:00:00) 기준 쿼리로 산출하여 항상 함께 반환해 줍니다.
        import datetime
        try:
            subject = query.get("subject", [None])[0]
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    # 1. 오늘 푼 총 문항 수(today_solved) 산출 - KST 오늘 자정 기준
                    # DB(created_at)는 UTC 시간으로 기록되므로, KST 기준 오늘 자정을 UTC 시간으로 변환하여 비교합니다.
                    # 이를 통해 서버의 기본 타임존 환경(KST 또는 UTC)에 구애받지 않고 일관된 집계가 가능합니다.
                    utc_now = datetime.datetime.utcnow()
                    kst_now = utc_now + datetime.timedelta(hours=9)
                    kst_today_start = kst_now.replace(hour=0, minute=0, second=0, microsecond=0)
                    utc_today_start = kst_today_start - datetime.timedelta(hours=9)
                    today_start_str = utc_today_start.strftime("%Y-%m-%d %H:%M:%S")

                    sql_today = """
                        SELECT COALESCE(SUM(total_questions), 0) as today_solved
                        FROM quiz_history
                        WHERE created_at >= %s
                    """
                    execute_query(cursor, sql_today, (today_start_str,))
                    row_today = cursor.fetchone()
                    today_solved_quiz = dict(row_today)["today_solved"] if row_today else 0

                    # 년도별 모의고사 오늘 푼 문제 수 조회 (테이블 부재 시 에러 방지용 예외 처리)
                    today_solved_yearly = 0
                    try:
                        sql_today_yearly = """
                            SELECT COALESCE(SUM(total_questions), 0) as today_solved
                            FROM yearly_exam_history
                            WHERE created_at >= %s
                        """
                        execute_query(cursor, sql_today_yearly, (today_start_str,))
                        row_yearly = cursor.fetchone()
                        today_solved_yearly = dict(row_yearly)["today_solved"] if row_yearly else 0
                    except Exception:
                        pass

                    today_solved = today_solved_quiz + today_solved_yearly

                    # 모의고사 이력에서 과목별 맞춘 정답 개수를 집계
                    yearly_correct_by_sub = { 'PM': 0, 'SE': 0, 'DB': 0, 'SA': 0, 'SC': 0 }
                    try:
                        sql_yearly_sums = """
                            SELECT COALESCE(SUM(pm_correct), 0) as pm_sum,
                                   COALESCE(SUM(se_correct), 0) as se_sum,
                                   COALESCE(SUM(db_correct), 0) as db_sum,
                                   COALESCE(SUM(sa_correct), 0) as sa_sum,
                                   COALESCE(SUM(sc_correct), 0) as sc_sum
                            FROM yearly_exam_history
                        """
                        execute_query(cursor, sql_yearly_sums)
                        sum_row = cursor.fetchone()
                        if sum_row:
                            sum_dict = dict(sum_row)
                            yearly_correct_by_sub['PM'] = sum_dict['pm_sum']
                            yearly_correct_by_sub['SE'] = sum_dict['se_sum']
                            yearly_correct_by_sub['DB'] = sum_dict['db_sum']
                            yearly_correct_by_sub['SA'] = sum_dict['sa_sum']
                            yearly_correct_by_sub['SC'] = sum_dict['sc_sum']
                    except Exception as ex_yearly:
                        print("[경고] yearly_exam_history EXP 수집 오류 방어:", ex_yearly)

                    # 특정 과목의 경험치만 조회할 경우
                    if subject:
                        subject = subject.upper()
                        sql = """
                            SELECT COALESCE(SUM(correct_count), 0) as total_exp
                            FROM quiz_history
                            WHERE subject = %s
                        """
                        execute_query(cursor, sql, (subject,))
                        row = cursor.fetchone()
                        total_exp_quiz = dict(row)["total_exp"] if row else 0
                        
                        # 모의고사 맞춘 개수 합산
                        total_exp = total_exp_quiz + yearly_correct_by_sub.get(subject, 0)
                        
                        # 레벨링 계산 공식: 누적 정답 10개당 1 레벨업 (기본 레벨 1)
                        level = (total_exp // 10) + 1
                        exp_in_level = total_exp % 10
                        exp_to_next = 10
                        
                        self.send_json_response({
                            "total_exp": total_exp,
                            "level": level,
                            "exp_in_level": exp_in_level,
                            "exp_to_next": exp_to_next,
                            "subject": subject,
                            "today_solved": today_solved
                        })
                    
                    # 과목 파라미터가 없어서 전체 및 과목별 경험치 맵을 모두 일괄 반환하는 경우 (학습 분석용)
                    else:
                        # 1. 전체 통합 누적 경험치 조회
                        sql_all = """
                            SELECT COALESCE(SUM(correct_count), 0) as total_exp
                            FROM quiz_history
                        """
                        execute_query(cursor, sql_all)
                        row_all = cursor.fetchone()
                        total_exp_quiz = dict(row_all)["total_exp"] if row_all else 0
                        
                        # 모의고사 전체 맞춘 문항 합산
                        total_exp = total_exp_quiz + sum(yearly_correct_by_sub.values())
                        
                        level = (total_exp // 10) + 1
                        exp_in_level = total_exp % 10
                        exp_to_next = 10
                        
                        # 2. 과목별 누적 경험치 조회 및 5대 과목 기본값(0) 매핑
                        sql_subjects = """
                            SELECT subject, COALESCE(SUM(correct_count), 0) as sub_exp
                            FROM quiz_history
                            GROUP BY subject
                        """
                        execute_query(cursor, sql_subjects)
                        rows_sub = cursor.fetchall()
                        
                        # 데이터가 없는 과목도 1레벨(0 EXP)로 안전하게 초기화하며 모의고사 데이터 기본 반영
                        subjects_exp = {}
                        for sub_code in ['DB', 'SE', 'PM', 'SA', 'SC']:
                            sub_exp_init = yearly_correct_by_sub[sub_code]
                            sub_lvl_init = (sub_exp_init // 10) + 1
                            sub_exp_in_lvl_init = sub_exp_init % 10
                            
                            subjects_exp[sub_code] = {
                                "total_exp": sub_exp_init,
                                "level": sub_lvl_init,
                                "exp_in_level": sub_exp_in_lvl_init,
                                "exp_to_next": 10
                            }
                            
                        # 조회된 과목별 실 데이터를 바인딩하여 합산
                        for r in rows_sub:
                            d = dict(r)
                            sub_name = d["subject"].upper()
                            sub_exp_quiz = d["sub_exp"]
                            
                            # 정의된 5대 과목 매핑 내에 있을 경우에만 합산 갱신
                            if sub_name in subjects_exp:
                                sub_exp = sub_exp_quiz + yearly_correct_by_sub.get(sub_name, 0)
                                sub_level = (sub_exp // 10) + 1
                                sub_exp_in_level = sub_exp % 10
                                
                                subjects_exp[sub_name] = {
                                    "total_exp": sub_exp,
                                    "level": sub_level,
                                    "exp_in_level": sub_exp_in_level,
                                    "exp_to_next": 10
                                }
                                
                        self.send_json_response({
                            "total_exp": total_exp,
                            "level": level,
                            "exp_in_level": exp_in_level,
                            "exp_to_next": exp_to_next,
                            "subjects_exp": subjects_exp,
                            "today_solved": today_solved
                        })
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def get_yearly_exams(self, query):
        """[설계 의도] 기출문제 연도 목록과 유저의 과목별 최고 점수 및 풀이 연습 통계를 요약하여 반환합니다."""
        try:
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    # 1. 기출 연도 및 문항 수 목록 조회
                    sql_years = """
                        SELECT year, COUNT(DISTINCT id) as question_count
                        FROM exam_questions
                        GROUP BY year
                        ORDER BY year DESC
                    """
                    execute_query(cursor, sql_years)
                    year_rows = cursor.fetchall()
                    
                    # 1.5. 신규 기출문제 통계 조회 (연도별/과목별)
                    sql_trends = """
                        SELECT year, subject, COALESCE(SUM(is_new_trend), 0) as new_trend_count, COUNT(*) as total_count
                        FROM exam_questions
                        GROUP BY year, subject
                    """
                    execute_query(cursor, sql_trends)
                    trend_rows = cursor.fetchall()
                    
                    # 2. 모든 모의고사 연습 이력 조회
                    sql_history = """
                        SELECT id, exam_year, score, created_at, pm_correct, se_correct, db_correct, sa_correct, sc_correct
                        FROM yearly_exam_history
                    """
                    execute_query(cursor, sql_history)
                    history_rows = cursor.fetchall()
                    
                    # 3. 파이썬 단에서 연도별/과목별 최고 점수 및 통계 집계
                    SUBJECT_RANGES = {
                        'PM': (1, 25, 25.0),
                        'SE': (26, 50, 25.0),
                        'DB': (51, 75, 25.0),
                        'SA': (76, 100, 25.0),
                        'SC': (101, 120, 20.0)
                    }
                    
                    # 연도별 통계 버퍼 초기화
                    stats_by_year = {}
                    for row in year_rows:
                        yr = row["year"]
                        stats_by_year[yr] = {
                            "year": yr,
                            "question_count": row["question_count"],
                            "max_score": 0.0,
                            "practice_count": 0,
                            "last_attempt_at": None,
                            "subject_max_scores": {
                                "PM": 0.0,
                                "SE": 0.0,
                                "DB": 0.0,
                                "SA": 0.0,
                                "SC": 0.0
                            },
                            "new_trends": {
                                "total_ratio": 0.0,
                                "total_count": 0,
                                "subjects": {
                                    "PM": {"count": 0, "ratio": 0.0},
                                    "SE": {"count": 0, "ratio": 0.0},
                                    "DB": {"count": 0, "ratio": 0.0},
                                    "SA": {"count": 0, "ratio": 0.0},
                                    "SC": {"count": 0, "ratio": 0.0}
                                }
                            }
                        }
                        
                    # 신규 기출 통계 집계 매핑
                    trends_by_year = {}
                    for row in trend_rows:
                        yr = row["year"]
                        sub = row["subject"]
                        count = row["new_trend_count"]
                        total = row["total_count"]
                        
                        if yr not in trends_by_year:
                            trends_by_year[yr] = {
                                "total_new": 0,
                                "total_questions": 0,
                                "subjects": {}
                            }
                        trends_by_year[yr]["total_new"] += count
                        trends_by_year[yr]["total_questions"] += total
                        trends_by_year[yr]["subjects"][sub] = {
                            "count": count,
                            "total": total,
                            "ratio": round((count / total) * 100.0, 1) if total > 0 else 0.0
                        }
                        
                    for yr in stats_by_year.keys():
                        if yr in trends_by_year:
                            trend_data = trends_by_year[yr]
                            t_new = trend_data["total_new"]
                            t_q = trend_data["total_questions"]
                            
                            stats_by_year[yr]["new_trends"]["total_ratio"] = round((t_new / t_q) * 100.0, 1) if t_q > 0 else 0.0
                            stats_by_year[yr]["new_trends"]["total_count"] = t_new
                            
                            for sub in ["PM", "SE", "DB", "SA", "SC"]:
                                sub_data = trend_data["subjects"].get(sub, {"count": 0, "total": 0, "ratio": 0.0})
                                stats_by_year[yr]["new_trends"]["subjects"][sub] = {
                                    "count": sub_data["count"],
                                    "ratio": sub_data["ratio"]
                                }
                    
                    for hist in history_rows:
                        yr = hist["exam_year"]
                        score = float(hist["score"]) if hist["score"] is not None else 0.0
                        created_at = hist["created_at"]
                        
                        if yr not in stats_by_year:
                            continue
                            
                        # 통계 기본값 누적
                        stats_by_year[yr]["practice_count"] += 1
                        if score > stats_by_year[yr]["max_score"]:
                            stats_by_year[yr]["max_score"] = score
                            
                        if not stats_by_year[yr]["last_attempt_at"] or created_at > stats_by_year[yr]["last_attempt_at"]:
                            stats_by_year[yr]["last_attempt_at"] = created_at
                            
                        # 과목별 점수 산출
                        correct_counts = {
                            'PM': hist.get("pm_correct") or 0,
                            'SE': hist.get("se_correct") or 0,
                            'DB': hist.get("db_correct") or 0,
                            'SA': hist.get("sa_correct") or 0,
                            'SC': hist.get("sc_correct") or 0
                        }
                                        
                        for sub, (start, end, total_num) in SUBJECT_RANGES.items():
                            # 이 풀이 시도의 과목별 100점 환산 점수
                            sub_score = round((correct_counts[sub] / total_num) * 100.0, 1)
                            if sub_score > stats_by_year[yr]["subject_max_scores"][sub]:
                                stats_by_year[yr]["subject_max_scores"][sub] = sub_score
                                    
                    # 4. JSON 직렬화에 적합한 데이터 포맷팅
                    data_list = []
                    for yr in sorted(stats_by_year.keys(), reverse=True):
                        item = stats_by_year[yr]
                        if item["last_attempt_at"]:
                            if not isinstance(item["last_attempt_at"], str):
                                item["last_attempt_at"] = item["last_attempt_at"].isoformat()
                        data_list.append(item)
                        
                    self.send_json_response(data_list)
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def get_yearly_exam_questions(self, query):
        """[설계 의도] 특정 연도의 모든 기출문제(120문항)를 번호 순서대로 조회합니다."""
        year_str = query.get("year", [None])[0]
        if not year_str or not year_str.isdigit():
            self.send_error_response(400, "Missing or invalid parameter (year)")
            return
            
        year = int(year_str)
        try:
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    sql = """
                        SELECT id, year, subject, question_num, question, options, answer, explanation, is_new_trend, similar_past_questions 
                        FROM exam_questions 
                        WHERE year = %s 
                        ORDER BY question_num ASC
                    """
                    execute_query(cursor, sql, (year,))
                    rows = cursor.fetchall()
                    
                    data_list = []
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
                            
                        # similar_past_questions JSON 파싱
                        sim_past = item.get("similar_past_questions")
                        if sim_past:
                            try:
                                item["similar_past_questions"] = json.loads(sim_past)
                            except:
                                item["similar_past_questions"] = []
                        else:
                            item["similar_past_questions"] = []
                            
                        data_list.append(item)
                        
                    self.send_json_response(data_list)
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def _get_yearly_subject_key(self, details):
        if not details:
            return 'ALL'
        code_set = set()
        for item in details:
            q_num = item.get("question_num")
            if q_num is not None:
                if 1 <= q_num <= 25: code_set.add('PM')
                elif 26 <= q_num <= 50: code_set.add('SE')
                elif 51 <= q_num <= 75: code_set.add('DB')
                elif 76 <= q_num <= 100: code_set.add('SA')
                elif 101 <= q_num <= 120: code_set.add('SC')
        
        ordered = [c for c in ['PM', 'SE', 'DB', 'SA', 'SC'] if c in code_set]
        if not ordered or len(ordered) == 5:
            return 'ALL'
        return ','.join(ordered)

    def submit_yearly_exam(self, data):
        """[설계 의도] 사용자가 제출한 모의고사 풀이 기록을 저장하고, 몇 회차인지 계산하여 DB에 기록합니다."""
        exam_year = data.get("exam_year")
        score = data.get("score")
        correct_count = data.get("correct_count")
        total_questions = data.get("total_questions")
        total_time = data.get("total_time")
        question_times = data.get("question_times")
        details = data.get("details")
        
        if exam_year is None or score is None or correct_count is None or total_questions is None or total_time is None:
            self.send_error_response(400, "Missing parameters for yearly exam submission")
            return
            
        # 과목별 정답수 산출
        pm_c = se_c = db_c = sa_c = sc_c = 0
        if details:
            for item in details:
                q_num = item.get("question_num")
                is_corr = item.get("is_correct", False)
                if is_corr and q_num is not None:
                    if 1 <= q_num <= 25: pm_c += 1
                    elif 26 <= q_num <= 50: se_c += 1
                    elif 51 <= q_num <= 75: db_c += 1
                    elif 76 <= q_num <= 100: sa_c += 1
                    elif 101 <= q_num <= 120: sc_c += 1

        try:
            question_times_json = json.dumps(question_times) if question_times is not None else None
            details_json = json.dumps(details, ensure_ascii=False) if details else None
            
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    # 1. 기존 연습 횟수(practice_count) 구하기 - 같은 년도 및 같은 과목 필터링
                    current_sub_key = self._get_yearly_subject_key(details)
                    sql_hist = "SELECT details FROM yearly_exam_history WHERE exam_year = %s"
                    execute_query(cursor, sql_hist, (exam_year,))
                    hist_rows = cursor.fetchall()
                    
                    matching_count = 0
                    for row in hist_rows:
                        row_details_raw = dict(row)["details"]
                        if row_details_raw:
                            if isinstance(row_details_raw, str):
                                try:
                                    row_details = json.loads(row_details_raw)
                                except Exception:
                                    row_details = []
                            else:
                                row_details = row_details_raw
                            
                            if self._get_yearly_subject_key(row_details) == current_sub_key:
                                matching_count += 1
                                
                    practice_count = matching_count + 1
                    
                    # 2. 결과 삽입
                    sql_insert = """
                        INSERT INTO yearly_exam_history (exam_year, practice_count, score, correct_count, total_questions, total_time, question_times, details, pm_correct, se_correct, db_correct, sa_correct, sc_correct)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    execute_query(cursor, sql_insert, (exam_year, practice_count, score, correct_count, total_questions, total_time, question_times_json, details_json, pm_c, se_c, db_c, sa_c, sc_c))
                    conn.commit()
                    
                    self.send_json_response({
                        "success": True, 
                        "message": "Yearly exam attempt saved successfully",
                        "practice_count": practice_count
                    })
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def get_yearly_exam_history(self, query):
        """[설계 의도] 전체 모의고사 연습 이력 목록을 반환합니다."""
        try:
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    sql = """
                        SELECT id, created_at, exam_year, practice_count, score, correct_count, total_questions, total_time, details 
                        FROM yearly_exam_history 
                        ORDER BY created_at DESC
                    """
                    execute_query(cursor, sql)
                    rows = cursor.fetchall()
                    
                    data_list = []
                    for row in rows:
                        item = dict(row)
                        if item["created_at"]:
                            if not isinstance(item["created_at"], str):
                                item["created_at"] = item["created_at"].isoformat()
                        data_list.append(item)
                        
                    self.send_json_response(data_list)
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database error: {str(e)}")

    def get_yearly_exam_ai_diagnose(self, query):
        """[설계 의도] 지정된 모의고사 풀이 이력에 대해 AI 취약 진단 및 처방 가이드를 반환합니다. 
        캐싱되어 있다면 즉시 반환하고, 없으면 Gemini API를 호출해 생성 후 저장합니다."""
        history_id_str = query.get("id", [None])[0]
        if not history_id_str or not history_id_str.isdigit():
            self.send_error_response(400, "Missing or invalid parameter (id)")
            return

        history_id = int(history_id_str)
        try:
            with get_db_connection() as conn:
                with get_db_cursor(conn) as cursor:
                    # 1. 기존 캐시 여부 확인
                    sql_select = "SELECT score, correct_count, total_questions, details, exam_year, ai_desc, ai_rec FROM yearly_exam_history WHERE id = %s"
                    execute_query(cursor, sql_select, (history_id,))
                    row = cursor.fetchone()
                    
                    if not row:
                        self.send_error_response(404, "Exam history not found")
                        return
                        
                    row_dict = dict(row)
                    ai_desc = row_dict.get("ai_desc")
                    ai_rec = row_dict.get("ai_rec")
                    
                    nocache = query.get("nocache", ["false"])[0].lower() == "true"
                    if ai_desc and ai_rec and not nocache:
                        # 캐시 반환
                        self.send_json_response({
                            "success": True,
                            "ai_analysis": {
                                "desc": ai_desc,
                                "recommendation": ai_rec
                            }
                        })
                        return
                        
                    # 2. 캐시가 없으면 Gemini API를 호출하여 생성
                    # API Key가 없으면 로컬 룰에 따른 폴백 값을 생성하여 반환 및 저장합니다.
                    score = row_dict.get("score", 0)
                    correct_count = row_dict.get("correct_count", 0)
                    total_questions = row_dict.get("total_questions", 120)
                    exam_year = row_dict.get("exam_year", 2025)
                    details_raw = row_dict.get("details", "")
                    
                    details = []
                    if details_raw:
                        try:
                            details = json.loads(details_raw) if isinstance(details_raw, str) else details_raw
                        except Exception:
                            details = []
                            
                    # 과목별 정답 분석 수행
                    pm_t = pm_c = se_t = se_c = db_t = db_c = sa_t = sa_c = sc_t = sc_c = 0
                    for item in details:
                        q_num = item.get("question_num")
                        is_corr = item.get("is_correct", False)
                        if q_num is not None:
                            if 1 <= q_num <= 25:
                                pm_t += 1
                                if is_corr: pm_c += 1
                            elif 26 <= q_num <= 50:
                                se_t += 1
                                if is_corr: se_c += 1
                            elif 51 <= q_num <= 75:
                                db_t += 1
                                if is_corr: db_c += 1
                            elif 76 <= q_num <= 100:
                                sa_t += 1
                                if is_corr: sa_c += 1
                            elif 101 <= q_num <= 120:
                                sc_t += 1
                                if is_corr: sc_c += 1
                                
                    normal_correct = normal_total = new_trend_correct = new_trend_total = 0
                    # new_trend_mapping 불러오기 (없는 경우 대비)
                    new_trend_mapping = {}
                    try:
                        mapping_path = os.path.join(BASE_DIR, "reports", "js", "data", "new_trend_mapping.js")
                        if os.path.exists(mapping_path):
                            with open(mapping_path, "r", encoding="utf-8") as f:
                                mapping_content = f.read()
                                matches = re.findall(r'"(\d{4}_\d+)":\s*(\d)', mapping_content)
                                for k, v in matches:
                                    new_trend_mapping[k] = int(v)
                    except Exception as ex:
                        print(f"new_trend_mapping 로드 오류: {ex}")
                        
                    for item in details:
                        q_num = item.get("question_num")
                        is_corr = item.get("is_correct", False)
                        if q_num is not None:
                            qid = f"{exam_year}_{q_num}"
                            is_new = new_trend_mapping.get(qid, 0) == 1
                            if is_new:
                                new_trend_total += 1
                                if is_corr: new_trend_correct += 1
                            else:
                                normal_total += 1
                                if is_corr: normal_correct += 1
                                
                    normal_pct = round((normal_correct / normal_total) * 100.0) if normal_total > 0 else 0
                    new_trend_pct = round((new_trend_correct / new_trend_total) * 100.0) if new_trend_total > 0 else 0
                    
                    ai_desc_generated = ""
                    ai_rec_generated = ""
                    
                    if GEMINI_API_KEY:
                        # Gemini Prompt 작성
                        prompt = f"""
당신은 대한민국 최고 수준의 '정보시스템 감리사 자격검정 수험 진단 시스템'입니다.
수험생이 치른 {exam_year}년도 모의고사 성적표 데이터를 바탕으로, 냉철하고 실질적인 학습 취약점 진단서와 추천 가이드를 작성해 주세요.

[시험 결과 요약]
- 총 문항 수: {total_questions}문항 중 {correct_count}문항 정답 (맞춤 환산 점수: {score}점)
- 일반 기출 영역 정답률: {normal_pct}% ({normal_correct}/{normal_total})
- 신규 트렌드/법규 영역 정답률: {new_trend_pct}% ({new_trend_correct}/{new_trend_total})

[과목별 정답률 세부 내역]
- 감리 및 사업관리(PM): {round((pm_c/pm_t)*100.0) if pm_t > 0 else 0}% ({pm_c}/{pm_t})
- 소프트웨어공학(SE): {round((se_c/se_t)*100.0) if se_t > 0 else 0}% ({se_c}/{se_t})
- 데이터베이스(DB): {round((db_c/db_t)*100.0) if db_t > 0 else 0}% ({db_c}/{db_t})
- 시스템 아키텍처(SA): {round((sa_c/sa_t)*100.0) if sa_t > 0 else 0}% ({sa_c}/{sa_t})
- 보안(SC): {round((sc_c/sc_t)*100.0) if sc_t > 0 else 0}% ({sc_c}/{sc_t})

[출력 요구사항]
1. 반드시 아래의 JSON 포맷 형식을 정확히 준수하여 응답하세요.
2. 백틱 기호(```json)나 여타 텍스트(설명글 등)를 절대 덧붙이지 마십시오. 순수 JSON 텍스트만 출력해야 합니다.
3. 'desc'는 수험생의 학습 패턴, 약점 단원, 일반 기출 대비 신규 기술 영역에서의 취약성 등을 냉철하고 예리하게 짚어내는 3~4줄 분량의 상세 분석 글이어야 합니다. (한국어로 격식 있는 조언 투)
4. 'recommendation'은 향후 어떤 가이드나 과목을 어떻게 회독해야 하는지에 대한 1~2줄 분량의 구체적인 행동 조언 및 학습 팁이어야 합니다.

[응답 JSON 스키마 포맷]
{{
  "desc": "이 수험생은 감리 및 사업관리의 공공 가이드라인 적용력은 우수하나, 소프트웨어공학의 복잡한 계산식 영역에서 잦은 오답이 보입니다. 특히 일반 기출 대비 신규 트렌드 문항의 정답률이 현저히 떨어지므로 최신 개정 고시에 대한 정리가 시급합니다.",
  "recommendation": "소프트웨어공학 PMBOK 임계경로 계산 공식을 오답노트에 정리하시고, 최신 공공데이터 지침 및 전자정부 표준 프레임워크 4.x 개정본 가이드를 집중 회독하세요."
}}

최종 JSON 응답:"""
                        raw_ai_res = call_gemini_raw_prompt(prompt)
                        if raw_ai_res:
                            # 백틱 블록 제거
                            raw_ai_res = raw_ai_res.strip()
                            if raw_ai_res.startswith("```"):
                                lines = raw_ai_res.split("\n")
                                if lines[0].startswith("```"):
                                    lines = lines[1:]
                                if lines[-1].startswith("```"):
                                    lines = lines[:-1]
                                raw_ai_res = "\n".join(lines).strip()
                            try:
                                ai_data = json.loads(raw_ai_res)
                                ai_desc_generated = ai_data.get("desc", "").strip()
                                ai_rec_generated = ai_data.get("recommendation", "").strip()
                            except Exception as parse_ex:
                                print(f"Gemini AI 응답 JSON 파싱 실패: {parse_ex}. 원본 응답: {raw_ai_res}")
                                
                    # 폴백 로직
                    if not ai_desc_generated or not ai_rec_generated:
                        if normal_pct >= 80 and new_trend_pct < 50:
                            ai_desc_generated = "기존 기출 회독 상태는 양호하나 최신 법제도 개정이나 생소한 신규 기술 트렌드에 약점을 보입니다."
                            ai_rec_generated = "💡 <b>처방 가이드:</b> <code>감리사_시험대비/가이드및법규</code> 폴더의 최신 고시 준수 가이드 및 공공데이터 지침서 등을 중심으로 신기술 트렌드를 집중 보완하십시오."
                        elif normal_pct >= 80 and new_trend_pct >= 80:
                            ai_desc_generated = "기출의 완성도와 최신 트렌드 대응력이 균형 있게 최상위권에 도달했습니다."
                            ai_rec_generated = "💡 <b>처방 가이드:</b> 실전 모드 하에서 실수를 방지하고 소요 시간을 80분 이내로 타이트하게 단축하는 훈련에 힘쓰십시오."
                        else:
                            ai_desc_generated = "디테일한 암기(수식 계산, 표준 표기 규칙 등)의 정확성이 부족하여 전형적인 기출 패턴에서 오답이 잦습니다."
                            ai_rec_generated = "💡 <b>처방 가이드:</b> 확실한 득점원 확보를 위해 데이터베이스 정규화 공식, PMBOK 임계경로(Critical Path) 계산식 및 오답 노트를 중심으로 회독 수를 높이십시오."
                        
                    # 3. 데이터베이스에 캐시 업데이트
                    sql_update = "UPDATE yearly_exam_history SET ai_desc = %s, ai_rec = %s WHERE id = %s"
                    execute_query(cursor, sql_update, (ai_desc_generated, ai_rec_generated, history_id))
                    conn.commit()
                    
                    self.send_json_response({
                        "success": True,
                        "ai_analysis": {
                            "desc": ai_desc_generated,
                            "recommendation": ai_rec_generated
                        }
                    })
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(500, f"Database diagnosis error: {str(e)}")

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


def init_yearly_exam_history_table():
    """[설계 의도] SQLite 또는 PostgreSQL 등 기종에 맞는 년도별 모의고사 연습 이력 테이블을 생성/검증합니다."""
    try:
        with get_db_connection() as conn:
            with get_db_cursor(conn) as cursor:
                if DB_TYPE == "POSTGRES":
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS yearly_exam_history (
                        id SERIAL PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        exam_year INTEGER NOT NULL,
                        practice_count INTEGER NOT NULL,
                        score REAL NOT NULL,
                        correct_count INTEGER NOT NULL,
                        total_questions INTEGER NOT NULL,
                        total_time INTEGER NOT NULL,
                        question_times TEXT,
                        details TEXT,
                        pm_correct INTEGER DEFAULT 0,
                        se_correct INTEGER DEFAULT 0,
                        db_correct INTEGER DEFAULT 0,
                        sa_correct INTEGER DEFAULT 0,
                        sc_correct INTEGER DEFAULT 0
                    );
                    """)
                else:
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS yearly_exam_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        exam_year INTEGER NOT NULL,
                        practice_count INTEGER NOT NULL,
                        score REAL NOT NULL,
                        correct_count INTEGER NOT NULL,
                        total_questions INTEGER NOT NULL,
                        total_time INTEGER NOT NULL,
                        question_times TEXT,
                        details TEXT,
                        pm_correct INTEGER DEFAULT 0,
                        se_correct INTEGER DEFAULT 0,
                        db_correct INTEGER DEFAULT 0,
                        sa_correct INTEGER DEFAULT 0,
                        sc_correct INTEGER DEFAULT 0
                    );
                    """)
                conn.commit()
                
                # 기존 테이블 호환성을 위한 캐시 컬럼 유무 확인 및 자동 추가
                columns_to_add = ["pm_correct", "se_correct", "db_correct", "sa_correct", "sc_correct"]
                for col in columns_to_add:
                    try:
                        cursor.execute(f"SELECT {col} FROM yearly_exam_history LIMIT 1")
                    except Exception:
                        conn.rollback()
                        alter_sql = f"ALTER TABLE yearly_exam_history ADD COLUMN {col} INTEGER DEFAULT 0"
                        cursor.execute(alter_sql)
                        conn.commit()
                        print(f"[{DB_TYPE}] yearly_exam_history 테이블에 컬럼 추가 완료: {col}")
                
                # AI 진단 캐시 컬럼 유무 확인 및 자동 추가
                ai_columns = ["ai_desc", "ai_rec"]
                for col in ai_columns:
                    try:
                        cursor.execute(f"SELECT {col} FROM yearly_exam_history LIMIT 1")
                    except Exception:
                        conn.rollback()
                        alter_sql = f"ALTER TABLE yearly_exam_history ADD COLUMN {col} TEXT"
                        cursor.execute(alter_sql)
                        conn.commit()
                        print(f"[{DB_TYPE}] yearly_exam_history 테이블에 AI 캐시 컬럼 추가 완료: {col}")
                
                # 기존 데이터에 대해 과목별 점수 데이터 복원 및 업데이트 수행
                # pm_correct, se_correct, db_correct, sa_correct, sc_correct가 모두 0이고, 맞춘 정답 수가 0보다 큰 대상들을 필터링
                select_sql = """
                    SELECT id, details FROM yearly_exam_history 
                    WHERE correct_count > 0 AND (pm_correct + se_correct + db_correct + sa_correct + sc_correct) = 0
                """
                cursor.execute(select_sql)
                rows = cursor.fetchall()
                migration_count = 0
                for r in rows:
                    row_dict = dict(r)
                    row_id = row_dict["id"]
                    details_raw = row_dict["details"]
                    if details_raw:
                        if isinstance(details_raw, str):
                            try:
                                exam_details = json.loads(details_raw)
                            except Exception:
                                exam_details = []
                        else:
                            exam_details = details_raw
                        
                        counts = { 'PM': 0, 'SE': 0, 'DB': 0, 'SA': 0, 'SC': 0 }
                        for item in exam_details:
                            q_num = item.get("question_num")
                            is_corr = item.get("is_correct", False)
                            if is_corr and q_num is not None:
                                sub_code = None
                                if 1 <= q_num <= 25: sub_code = 'PM'
                                elif 26 <= q_num <= 50: sub_code = 'SE'
                                elif 51 <= q_num <= 75: sub_code = 'DB'
                                elif 76 <= q_num <= 100: sub_code = 'SA'
                                elif 101 <= q_num <= 120: sub_code = 'SC'
                                if sub_code:
                                    counts[sub_code] += 1
                        
                        update_sql = """
                            UPDATE yearly_exam_history 
                            SET pm_correct = %s, se_correct = %s, db_correct = %s, sa_correct = %s, sc_correct = %s
                            WHERE id = %s
                        """
                        execute_query(cursor, update_sql, (counts['PM'], counts['SE'], counts['DB'], counts['SA'], counts['SC'], row_id))
                        migration_count += 1
                
                if migration_count > 0:
                    conn.commit()
                    print(f"[{DB_TYPE}] 기존 모의고사 이력 데이터 {migration_count}건에 대한 과목별 정답수 마이그레이션 완료.")
                    
        print(f"[{DB_TYPE}] 년도별 모의고사 이력(yearly_exam_history) 테이블 검증/초기화 완료.")
    except Exception as e:
        print(f"[{DB_TYPE}] 경고 - 년도별 모의고사 이력 테이블 초기화 중 예외가 발생했으나 시작을 속행합니다: {e}")


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
        init_yearly_exam_history_table()
    except Exception as e:
        print(f"[Server] 경고: DB 연결 제한 상황에서 구동을 대기합니다. -> {e}")
        
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, JollyCarsonRequestHandler)
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
