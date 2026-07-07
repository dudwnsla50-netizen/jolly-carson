# -*- coding: utf-8 -*-
import sys
import os
import psycopg2
import urllib.parse

# e:\jolly-carson 폴더를 path에 추가하여 server.py의 설정을 참조할 수 있게 합니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

def clear_ai_cache():
    print("원격 Supabase 데이터베이스에 연결 중...")
    try:
        parsed = urllib.parse.urlparse(SUPABASE_URL_RAW)
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
        
        conn = psycopg2.connect(**conn_kwargs)
        cursor = conn.cursor()
        
        # ai_desc, ai_rec를 모두 NULL로 날려서 캐시를 무효화합니다.
        sql = "UPDATE yearly_exam_history SET ai_desc = NULL, ai_rec = NULL"
        cursor.execute(sql)
        row_count = cursor.rowcount
        conn.commit()
        
        print(f"성공: {row_count}개의 모의고사 연습 이력에 대한 AI 진단 캐시가 초기화되었습니다.")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

if __name__ == "__main__":
    clear_ai_cache()
