import sqlite3
import os

db_path = os.path.join("reports", "exam_db", "jolly_carson.db")
print("DB Path:", db_path, "Exists:", os.path.exists(db_path))

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 테이블 확인
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables in SQLite:", tables)
    
    if "quiz_history" in tables:
        cur.execute("SELECT COUNT(*) FROM quiz_history")
        print("quiz_history count:", cur.fetchone()[0])
        
        cur.execute("SELECT DISTINCT subject FROM quiz_history")
        print("quiz_history subjects:", cur.fetchall())
        
        cur.execute("SELECT * FROM quiz_history LIMIT 5")
        for row in cur.fetchall():
            print(row)
    else:
        print("quiz_history table does not exist in SQLite.")
        
    cur.close()
    conn.close()
