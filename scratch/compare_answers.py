import os
import sqlite3
import psycopg2
import urllib.parse
import json

SQLITE_DB_PATH = "d:/100.lyj/anti_workspace/jolly-carson/reports/exam_db/jolly_carson.db"
SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

def compare_answers():
    # SQLite
    sl_conn = sqlite3.connect(SQLITE_DB_PATH)
    sl_cur = sl_conn.cursor()
    sl_cur.execute("SELECT id, answer FROM exam_questions")
    sl_data = {r[0]: r[1] for r in sl_cur.fetchall()}
    sl_conn.close()
    
    # PostgreSQL
    parsed = urllib.parse.urlparse(SUPABASE_URL_RAW)
    username = urllib.parse.unquote(parsed.username) if parsed.username else None
    password = urllib.parse.unquote(parsed.password) if parsed.password else None
    dbname = urllib.parse.unquote(parsed.path.lstrip("/")) if parsed.path else None
    
    pg_conn = psycopg2.connect(
        dbname=dbname,
        user=username,
        password=password,
        host=parsed.hostname,
        port=parsed.port or 5432
    )
    pg_cur = pg_conn.cursor()
    pg_cur.execute("SELECT id, answer, explanation FROM exam_questions")
    pg_data = {r[0]: (r[1], r[2]) for r in pg_cur.fetchall()}
    pg_conn.close()
    
    diff_count = 0
    print("Comparing answers between SQLite and Postgres:")
    for qid, sl_ans in sl_data.items():
        if qid in pg_data:
            pg_ans, pg_exp = pg_data[qid]
            
            # normalize answer to compare
            def norm_ans(ans):
                if not ans:
                    return []
                try:
                    p = json.loads(ans)
                    if isinstance(p, list):
                        return sorted([str(x) for x in p])
                    return [str(p)]
                except:
                    return [str(ans).strip()]
                    
            sl_norm = norm_ans(sl_ans)
            pg_norm = norm_ans(pg_ans)
            
            if sl_norm != pg_norm:
                diff_count += 1
                print(f"ID: {qid} | SQLite: {sl_ans} -> Postgres: {pg_ans} | Has Postgres Exp: {pg_exp is not None and pg_exp != ''}")
                
    print(f"Total diffs: {diff_count}")

if __name__ == "__main__":
    compare_answers()
