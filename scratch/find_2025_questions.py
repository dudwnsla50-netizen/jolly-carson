# -*- coding: utf-8 -*-
import os
import sys
import psycopg2
import urllib.parse

# Windows 콘솔 인코딩 에러 방지
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
DATABASE_URL = os.environ.get("DATABASE_URL", SUPABASE_URL_RAW)

def find_2025():
    parsed = urllib.parse.urlparse(DATABASE_URL)
    username = urllib.parse.unquote(parsed.username) if parsed.username else None
    password = urllib.parse.unquote(parsed.password) if parsed.password else None
    dbname = urllib.parse.unquote(parsed.path.lstrip("/")) if parsed.path else None
    
    conn = psycopg2.connect(
        dbname=dbname,
        user=username,
        password=password,
        host=parsed.hostname,
        port=parsed.port or 5432
    )
    conn.set_client_encoding('UTF8')
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, subject, question_num, question, options, answer 
        FROM exam_questions 
        WHERE year = 2025 AND (explanation IS NULL OR explanation = '')
    """)
    rows = cur.fetchall()
    print(f"2025년도 해설 미등록 문항 수: {len(rows)}개")
    for idx, r in enumerate(rows):
        print(f"\n[{idx+1}] ID: {r[0]} ({r[1]} {r[2]}번) | 정답: {r[5]}")
        print(f"질문:\n{r[3]}")
        print(f"보기:\n{r[4]}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    find_2025()
