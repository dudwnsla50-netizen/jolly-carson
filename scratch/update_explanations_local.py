# -*- coding: utf-8 -*-
import os
import sys
import json
import re
import psycopg2
import urllib.parse

# Windows 콘솔 인코딩 에러 방지
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
DATABASE_URL = os.environ.get("DATABASE_URL", SUPABASE_URL_RAW)

def clean_and_update_all():
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
    
    # 전체 기출 문항 중 해설이 존재하는 것 로드
    cur.execute("""
        SELECT id, question_num, subject, answer, explanation 
        FROM exam_questions 
        WHERE explanation IS NOT NULL AND explanation != ''
    """)
    rows = cur.fetchall()
    
    print(f"전체 대상 해설 문항 수: {len(rows)}개")
    
    updated_count = 0
    
    for row in rows:
        qid, qnum, subject, answer, explanation = row
        
        # answer 파싱
        try:
            ans_parsed = json.loads(answer)
            if isinstance(ans_parsed, list):
                ans_str = ", ".join(str(x) for x in ans_parsed)
            else:
                ans_str = str(ans_parsed)
        except:
            ans_str = str(answer).strip().replace("[", "").replace("]", "")
            
        original_exp = explanation
        
        # 1. 정답 부분 교정 (- **정답**: X번 형식)
        # 예: "- **정답**: 4번 (라, 마, 바 등 또는 나, 다, 마)" -> "- **정답**: 2번" 처럼 바꿈
        # 먼저 기존 정답 줄을 탐색
        match_line = re.search(r'-\s*\*\*정답\*\*:\s*(.*)', explanation)
        if match_line:
            orig_ans_line = match_line.group(0)
            # 새로운 정답 라인 정의
            new_ans_line = f"- **정답**: {ans_str}번"
            explanation = explanation.replace(orig_ans_line, new_ans_line)
            
        # 2. 사족 설명 삭제 (DB 채점, DB 기록, DB 등록 등으로 시작하는 설명 문장 제거)
        # 예: "DB 채점상 [4]번으로 기재된 경우..." / "DB 기록 데이터 정답 번호..."
        # 마침표(.) 또는 줄바꿈 단위로 해당 사족이 들어간 문장을 찾아서 제거
        
        # 정규표현식으로 "DB 채점", "DB 기록", "DB 등록"이 포함된 문장을 삭제
        # 문장 끝 마침표(.) 및 줄바꿈을 포함하여 삭제
        pattern = r'(?:DB\s*(?:채점|기록|등록|등록\s*번호)[^\.\n]*?[\.\n])'
        explanation = re.sub(pattern, '', explanation)
        
        # 3. 연속된 공백 라인 정리
        explanation = re.sub(r'\n{3,}', '\n\n', explanation).strip()
        
        # 변경 사항이 있을 경우에만 업데이트
        if explanation != original_exp:
            try:
                cur.execute(
                    "UPDATE exam_questions SET explanation = %s WHERE id = %s",
                    (explanation, qid)
                )
                conn.commit()
                updated_count += 1
                print(f"[성공] {subject} {qnum}번 | 기존 정답라인: {match_line.group(1) if match_line else '없음'} -> 새 정답: {ans_str}번")
            except Exception as e:
                conn.rollback()
                print(f"[실패] {qid} 업데이트 에러: {e}")
                
    cur.close()
    conn.close()
    
    print(f"\n전체 년도 해설 로컬 보정 및 업데이트 완료: 총 {updated_count}건 반영됨.")

if __name__ == "__main__":
    clean_and_update_all()
