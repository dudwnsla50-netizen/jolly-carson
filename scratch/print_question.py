import os
import psycopg2
import urllib.parse
import json

SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

def print_question(qid):
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
    conn.set_client_encoding('UTF8')
    cur = conn.cursor()
    
    cur.execute("SELECT id, year, subject, question_num, question, options, answer, explanation FROM exam_questions WHERE id=%s", (qid,))
    row = cur.fetchone()
    if row:
        qid, year, subject, qnum, question, options, answer, explanation = row
        print(f"=== ID: {qid} ({year}년 {subject} {qnum}번) ===")
        print(f"Question:\n{question}\n")
        print(f"Options:\n{options}\n")
        print(f"Answer:\n{answer}\n")
        print(f"Explanation:\n{explanation}\n")
    else:
        print(f"Question with ID {qid} not found.")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    import sys
    qid = sys.argv[1] if len(sys.argv) > 1 else "2026_41"
    print_question(qid)
