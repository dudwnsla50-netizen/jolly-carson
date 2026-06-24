import os
import psycopg2
import urllib.parse

SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
DATABASE_URL = os.environ.get("DATABASE_URL", SUPABASE_URL_RAW)

try:
    print("PostgreSQL 연결 시도 중...")
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
    cur = conn.cursor()
    
    # 테이블 리스트 확인
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables in Postgres:", tables)
    
    if "quiz_history" in tables:
        cur.execute("SELECT COUNT(*) FROM quiz_history")
        print("quiz_history count:", cur.fetchone()[0])
        
        cur.execute("SELECT DISTINCT subject FROM quiz_history")
        print("quiz_history subjects:", cur.fetchall())
        
        cur.execute("SELECT id, created_at, subject, concept, total_questions FROM quiz_history ORDER BY id DESC LIMIT 5")
        for row in cur.fetchall():
            print(row)
    else:
        print("quiz_history table does not exist in Postgres.")
        
    cur.close()
    conn.close()
except Exception as e:
    print("Postgres Connection or Query Failed:", e)
