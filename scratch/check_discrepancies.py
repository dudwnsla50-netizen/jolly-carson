import os
import psycopg2
import urllib.parse
import json
import re

SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

def check_discrepancies():
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
        conn.set_client_encoding('UTF8')
        cur = conn.cursor()
        
        cur.execute("SELECT id, year, subject, question_num, answer, explanation FROM exam_questions WHERE explanation IS NOT NULL AND explanation != ''")
        rows = cur.fetchall()
        
        print(f"Total rows with explanation: {len(rows)}")
        
        discrepancies = []
        for row in rows:
            qid, year, subject, qnum, answer, explanation = row
            
            # answer 파싱
            ans_list = []
            if answer:
                try:
                    # JSON array 형태인 경우 (예: [2] or [1, 2])
                    parsed_ans = json.loads(answer)
                    if isinstance(parsed_ans, list):
                        ans_list = [str(x) for x in parsed_ans]
                    else:
                        ans_list = [str(parsed_ans)]
                except json.JSONDecodeError:
                    # 단일 값인 경우
                    ans_list = [answer.strip()]
            
            # explanation에서 정답 추출 시도
            # 보통 형식: **정답**: 4번 / 정답: 2번 / DB 채점 [4] / DB 등록 번호 [2]
            # 혹은 - **정답**: 4번 (가, 나...)
            ans_in_exp = []
            
            # 정답 패턴 매칭
            # 1. - **정답**: X번
            m1 = re.search(r'-\s*\*\*정답\*\*:\s*([0-9,\s번또는및]+)', explanation)
            if m1:
                nums = re.findall(r'\d+', m1.group(1))
                ans_in_exp.extend(nums)
            
            # 2. DB 채점 [X] 또는 DB 등록 번호 [X] 또는 DB 등록 [X]
            m2 = re.search(r'DB\s*(?:채점|등록|등록\s*번호)\s*\[([0-9,\s]+)\]', explanation)
            if m2:
                nums = re.findall(r'\d+', m2.group(1))
                # 중복 방지하며 추가
                for n in nums:
                    if n not in ans_in_exp:
                        ans_in_exp.append(n)
                        
            # 정답 번호 리스트 정렬비교
            ans_list_sorted = sorted(list(set(ans_list)))
            ans_in_exp_sorted = sorted(list(set(ans_in_exp)))
            
            if ans_list_sorted != ans_in_exp_sorted and ans_in_exp_sorted:
                discrepancies.append({
                    "id": qid,
                    "year": year,
                    "subject": subject,
                    "qnum": qnum,
                    "answer_in_db": ans_list_sorted,
                    "answer_in_exp": ans_in_exp_sorted,
                    "explanation": explanation
                })
                
        print(f"Found {len(discrepancies)} discrepancies:")
        for idx, d in enumerate(discrepancies[:10]):
            print(f"\n[{idx+1}] ID: {d['id']} ({d['year']}년 {d['subject']} {d['qnum']}번)")
            print(f"  DB Answer: {d['answer_in_db']}")
            print(f"  Exp Answer: {d['answer_in_exp']}")
            print(f"  Explanation Snippet:")
            # 첫 3줄만 출력
            lines = d['explanation'].split('\n')
            for line in lines[:4]:
                print(f"    {line}")
                
        cur.close()
        conn.close()
    except Exception as e:
        print("PG query failed:", e)

if __name__ == "__main__":
    check_discrepancies()
