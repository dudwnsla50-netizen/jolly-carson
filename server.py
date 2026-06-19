# -*- coding: utf-8 -*-
"""
[Jolly-Carson 초경량 REST API & 정적 파일 통합 웹서버]
- 작성자: Antigravity
- 목적: 외부 라이브러리 없이 SQLite DB 조회 및 대시보드 웹앱 서빙을 처리합니다.
"""
import os
import sys
import json
import sqlite3
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")

class JollyCarsonRequestHandler(SimpleHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # 콘솔 출력이 너무 지저분해지지 않도록 로그를 예쁘게 커스텀하거나 음소거합니다.
        sys.stderr.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))

    def end_headers(self):
        # CORS 및 캐시 방지 헤더 설정
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        # 브라우저의 CORS Preflight 요청 대응
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # URL 디코딩 및 쿼리 파라미터 분리
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 1. API 요청 라우팅 처리
        if path.startswith("/api/"):
            self.handle_api(path, query)
        else:
            # 2. 일반 정적 리소스 서빙
            # 로컬 경로를 강제로 base 디렉토리로 바인딩하여 서빙
            super().do_GET()

    def do_POST(self):
        # POST 요청 본문 파싱 및 API 라우팅
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
        # POST 전 전용 API 라우터
        if path == "/api/question/update":
            self.update_question(data)
        else:
            self.send_error_response(404, "API Endpoint Not Found")

    def handle_api(self, path, query):
        if path == "/api/dashboard":
            self.get_dashboard(query)
        elif path == "/api/question":
            self.get_question(query)
        elif path == "/api/questions":
            self.get_questions(query)
        else:
            self.send_error_response(404, "API Endpoint Not Found")

    def get_dashboard(self, query):
        subject = query.get("subject", [None])[0]
        dtype = query.get("type", [None])[0] # frequent / official
        
        if not subject or not dtype:
            self.send_error_response(400, "Missing parameters (subject, type)")
            return
            
        subject = subject.upper()
        dtype = dtype.lower()

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            SELECT concept, category, count, core_concept, features, scope, 
                   rep_question, rep_year, rep_num, global_idx, years, questions
            FROM dashboard_mappings
            WHERE subject = ? AND dashboard_type = ?
            ORDER BY global_idx ASC
            """, (subject, dtype))
            
            rows = cursor.fetchall()
            
            data_list = []
            for row in rows:
                item = dict(row)
                # JSON 문자열 필드를 리스트/객체로 역직렬화
                item["years"] = json.loads(item["years"]) if item["years"] else []
                item["questions"] = json.loads(item["questions"]) if item["questions"] else []
                data_list.append(item)
                
            self.send_json_response(data_list)
        except Exception as e:
            self.send_error_response(500, f"Database error: {str(e)}")
        finally:
            conn.close()

    def get_question(self, query):
        q_id = query.get("id", [None])[0] # 예: "2026_101"
        if not q_id:
            self.send_error_response(400, "Missing parameter (id)")
            return
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT question, options, answer, explanation FROM exam_questions WHERE id = ?", (q_id,))
            row = cursor.fetchone()
            if row:
                # answer는 JSON 배열 문자열(예: "[1,3]")로 저장됨 → 파싱하여 리스트로 반환
                answer_val = json.loads(row[2]) if row[2] else []
                self.send_json_response({
                    "id": q_id, 
                    "question": row[0],
                    "options": json.loads(row[1]) if row[1] else [],
                    "answer": answer_val,
                    "explanation": row[3]
                })
            else:
                self.send_error_response(404, f"Question {q_id} Not Found")
        except Exception as e:
            self.send_error_response(500, f"Database error: {str(e)}")
        finally:
            conn.close()

    def get_questions(self, query):
        subject = query.get("subject", [None])[0]
        if not subject:
            self.send_error_response(400, "Missing parameter (subject)")
            return
            
        subject = subject.upper()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id, question, options, answer, explanation FROM exam_questions WHERE subject = ?", (subject,))
            rows = cursor.fetchall()
            
            data_dict = {}
            for row in rows:
                item = dict(row)
                item["options"] = json.loads(item["options"]) if item["options"] else []
                # answer JSON 배열 파싱 (복수 정답 지원)
                item["answer"] = json.loads(item["answer"]) if item["answer"] else []
                data_dict[item["id"]] = item
                
            self.send_json_response(data_dict)
        except Exception as e:
            self.send_error_response(500, f"Database error: {str(e)}")
        finally:
            conn.close()

    def update_question(self, data):
        """[설계 의도] 대시보드 편집 화면으로부터 입력받은 질문, 보기, 정답, 해설을 SQLite DB에 업데이트합니다."""
        q_id = data.get("id")
        question = data.get("question")
        options = data.get("options")
        answer = data.get("answer")           # 배열 형태 (예: [1], [1,3]) 또는 빈 배열
        explanation = data.get("explanation")   # 해설 텍스트 또는 None
        
        if not q_id or question is None or options is None:
            self.send_error_response(400, "Missing parameters (id, question, options)")
            return
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            options_json = json.dumps(options, ensure_ascii=False)
            # 복수 정답: 배열이 비어있으면 NULL로 저장, 아니면 JSON 문자열로 저장
            answer_json = json.dumps(answer) if answer and len(answer) > 0 else None
            cursor.execute("""
                UPDATE exam_questions 
                SET question = ?, options = ?, answer = ?, explanation = ?
                WHERE id = ?
            """, (question, options_json, answer_json, explanation, q_id))
            conn.commit()
            
            if cursor.rowcount > 0:
                self.send_json_response({"success": True, "message": "Question updated successfully"})
            else:
                self.send_error_response(404, f"Question {q_id} Not Found in database")
        except Exception as e:
            self.send_error_response(500, f"Database error: {str(e)}")
        finally:
            conn.close()

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

def main():
    # 현재 디렉토리를 작업 디렉토리로 고정하여 SimpleHTTPRequestHandler가 프로젝트 리소스를 정상적으로 서빙하도록 보장
    os.chdir(BASE_DIR)
    
    if not os.path.exists(DB_PATH):
        print(f"[오류] 데이터베이스 파일이 존재하지 않습니다: {DB_PATH}")
        print("  -> 먼저 'python migrate_to_db.py'를 실행하여 DB를 구축해 주세요.")
        sys.exit(1)
        
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, JollyCarsonRequestHandler)
    print(f"\n========================================================")
    print(f"[Server] Jolly-Carson Web API Server Started Successfully")
    print(f"[Dashboard URL] http://localhost:{PORT}/reports/db_frequent_concepts.html")
    print(f"========================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[서버] 웹 API 서버 종료 중...")
        httpd.server_close()
        print("[서버] 웹 API 서버가 정상 종료되었습니다.")

if __name__ == "__main__":
    main()
