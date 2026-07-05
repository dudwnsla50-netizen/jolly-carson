import os
import sqlite3
import psycopg2
import urllib.parse

SQLITE_DB_PATH = "d:/100.lyj/anti_workspace/jolly-carson/reports/exam_db/jolly_carson.db"
SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

def analyze_sqlite():
    if not os.path.exists(SQLITE_DB_PATH):
        print("SQLite DB not found at", SQLITE_DB_PATH)
        return
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print("SQLite Tables:", tables)
        if "exam_questions" in tables:
            cur.execute("PRAGMA table_info(exam_questions)")
            cols = cur.fetchall()
            print("exam_questions columns in SQLite:")
            for col in cols:
                print(col)
            
            cur.execute("SELECT COUNT(*), COUNT(explanation), COUNT(answer) FROM exam_questions")
            count, exp_count, ans_count = cur.fetchone()
            print(f"exam_questions in SQLite: total={count}, non-null explanation={exp_count}, non-null answer={ans_count}")
            
            cur.execute("SELECT id, year, subject, question_num, answer, explanation FROM exam_questions WHERE explanation IS NOT NULL AND explanation != '' LIMIT 3")
            rows = cur.fetchall()
            print("SQLite Sample Explanations:")
            for r in rows:
                print(r)
        else:
            print("exam_questions table NOT found in SQLite")
    except Exception as e:
        print("SQLite query failed:", e)
    finally:
        conn.close()

def analyze_pg():
    try:
        parsed = urllib.parse.urlparse(SUPABASE_URL_RAW)
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
        cur = conn.cursor()
        
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = [r[0] for r in cur.fetchall()]
        print("PG Tables:", tables)
        
        if "exam_questions" in tables:
            cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='exam_questions'")
            cols = cur.fetchall()
            print("exam_questions columns in PG:")
            for col in cols:
                print(col)
                
            cur.execute("SELECT COUNT(*), COUNT(explanation), COUNT(answer) FROM exam_questions")
            count, exp_count, ans_count = cur.fetchone()
            print(f"exam_questions in PG: total={count}, non-null explanation={exp_count}, non-null answer={ans_count}")
            
            cur.execute("SELECT id, year, subject, question_num, answer, explanation FROM exam_questions WHERE explanation IS NOT NULL AND explanation != '' LIMIT 3")
            rows = cur.fetchall()
            print("PG Sample Explanations:")
            for r in rows:
                print(r)
        else:
            print("exam_questions table NOT found in PG")
            
        cur.close()
        conn.close()
    except Exception as e:
        print("PG query failed:", e)

if __name__ == "__main__":
    print("=== SQLite ===")
    analyze_sqlite()
    print("\n=== PG ===")
    analyze_pg()
