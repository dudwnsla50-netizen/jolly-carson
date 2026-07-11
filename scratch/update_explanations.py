# -*- coding: utf-8 -*-
import os
import sys
import json
import re
import urllib.request
import urllib.parse
import sqlite3
import psycopg2
import time
import argparse

# Windows 콘솔 인코딩 에러 방지
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

SQLITE_DB_PATH = "d:/100.lyj/anti_workspace/jolly-carson/reports/exam_db/jolly_carson.db"
SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
DATABASE_URL = os.environ.get("DATABASE_URL", SUPABASE_URL_RAW)
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"

def parse_args():
    parser = argparse.ArgumentParser(description="PostgreSQL 기출문제 해설 업데이트 스크립트")
    parser.add_argument("--dry-run", action="store_true", help="실제 DB에 업데이트하지 않고 대상 문항 분석만 수행")
    parser.add_argument("--api-key", type=str, default="", help="Gemini API Key (생략 시 GEMINI_API_KEY 환경변수 활용)")
    parser.add_argument("--limit", type=int, default=0, help="처리할 최대 문제 수 (테스트용, 0이면 무제한)")
    return parser.parse_args()

def get_gemini_api_key(args):
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        # 콘솔 입력을 통해 안전하게 API 키 획득 시도
        try:
            api_key = input("Gemini API Key가 필요합니다. 입력해주세요 (또는 Enter로 취소): ").strip()
        except Exception:
            pass
    return api_key

def normalize_ans(ans):
    if not ans:
        return []
    try:
        p = json.loads(ans)
        if isinstance(p, list):
            return sorted([str(x) for x in p])
        return [str(p)]
    except Exception:
        return [str(ans).strip()]

def get_discrepancies_and_diffs():
    # 1. SQLite의 answer 로드
    sl_data = {}
    if os.path.exists(SQLITE_DB_PATH):
        try:
            sl_conn = sqlite3.connect(SQLITE_DB_PATH)
            sl_cur = sl_conn.cursor()
            sl_cur.execute("SELECT id, answer FROM exam_questions")
            sl_data = {r[0]: r[1] for r in sl_cur.fetchall()}
            sl_conn.close()
        except Exception as e:
            print(f"[경고] SQLite 데이터 로드 중 에러: {e}")
            
    # 2. PostgreSQL 연결 정보 구성 및 연결
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
    
    # 3. PostgreSQL 데이터 로드
    cur = conn.cursor()
    cur.execute("SELECT id, year, subject, question_num, question, options, answer, explanation FROM exam_questions")
    pg_rows = cur.fetchall()
    
    targets = []
    
    print("\n--- [문항 비교 분석 시작] ---")
    for row in pg_rows:
        qid, year, subject, qnum, question, options, answer, explanation = row
        
        pg_norm = normalize_ans(answer)
        sl_ans = sl_data.get(qid)
        sl_norm = normalize_ans(sl_ans)
        
        is_target = False
        reason = ""
        
        # 조건 A: SQLite의 answer와 Postgres의 answer가 다르고, 동시에 Postgres 내 해설이 없음 (신규 생성 타겟)
        if sl_ans is not None and sl_norm != pg_norm and (not explanation or not explanation.strip()):
            is_target = True
            reason = f"정답 수정 및 해설 미등록 감지 (SQLite: {sl_norm} -> Postgres: {pg_norm})"
            
        # 조건 B: Postgres 내 해설은 존재하지만, 해설 내 정답 표기와 DB answer가 불일치함
        elif explanation and explanation.strip():
            ans_in_exp = []
            
            # 패턴 1: - **정답**: X번
            m1 = re.search(r'-\s*\*\*정답\*\*:\s*([0-9,\s번또는및]+)', explanation)
            if m1:
                nums = re.findall(r'\d+', m1.group(1))
                ans_in_exp.extend(nums)
            
            # 패턴 2: DB 채점 [X]
            m2 = re.search(r'DB\s*(?:채점|등록|등록\s*번호)\s*\[([0-9,\s]+)\]', explanation)
            if m2:
                nums = re.findall(r'\d+', m2.group(1))
                for n in nums:
                    if n not in ans_in_exp:
                        ans_in_exp.append(n)
                        
            ans_in_exp_sorted = sorted(list(set(ans_in_exp)))
            
            if ans_in_exp_sorted and pg_norm != ans_in_exp_sorted:
                is_target = True
                reason = f"해설 내 정답 불일치 (DB: {pg_norm} vs 해설 표기: {ans_in_exp_sorted})"
                
        if is_target:
            targets.append({
                "id": qid,
                "year": year,
                "subject": subject,
                "qnum": qnum,
                "question": question,
                "options": options,
                "answer": answer,
                "explanation": explanation,
                "reason": reason
            })
            
    cur.close()
    conn.close()
    return targets

def call_huggingface_raw_prompt(prompt, hf_key):
    model_id = "meta-llama/Meta-Llama-3-8B-Instruct"
    url = f"https://api-inference.huggingface.co/models/{model_id}/v1/chat/completions"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.2
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {hf_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        data = json.loads(res.read().decode("utf-8"))
        response_text = data["choices"][0]["message"]["content"].strip()
        return response_text

def call_groq_raw_prompt(prompt, groq_key):
    model_id = "llama-3.1-8b-instant"
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.2
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        data = json.loads(res.read().decode("utf-8"))
        response_text = data["choices"][0]["message"]["content"].strip()
        return response_text

def call_gemini_api(prompt, api_key):
    keys = [k for k in [api_key, os.environ.get("GEMINI_API_KEY2", "")] if k]
    if not keys:
        print("[API 에러] 제공된 API Key 또는 백업 API Key가 없습니다.", flush=True)
        return None, 401

    max_retries = 2
    for attempt in range(max_retries):
        for i, key in enumerate(keys):
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2
                }
            }
            url = f"{GEMINI_API_URL}?key={key}"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                # timeout=10초를 설정하여 무한 대기 현상 방지
                with urllib.request.urlopen(req, timeout=10) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return text, 200
            except urllib.error.HTTPError as e:
                if e.code == 429 or (500 <= e.code < 600):
                    status_type = "429 Too Many Requests" if e.code == 429 else f"HTTP {e.code} Server Error"
                    print(f"[Warning] Gemini API Key #{i+1} {status_type} 감지.", flush=True)
                    if i < len(keys) - 1:
                        print(f"-> 백업 API Key #{i+2}로 즉시 전환하여 재시도합니다.", flush=True)
                        continue
                    else:
                        wait_time = 2
                        print(f"-> 모든 API Key 제한되거나 서버 에러 발생. {wait_time}초 후 재시도합니다... (시도 {attempt + 1}/{max_retries})", flush=True)
                        time.sleep(wait_time)
                else:
                    if i < len(keys) - 1:
                        print(f"[Warning] Gemini API Key #{i+1} 호출 실패 (HTTP {e.code}). 백업 API Key #{i+2}로 즉시 재시도합니다.", flush=True)
                        continue
                    print(f"[API 에러] Gemini 호출 실패 (HTTP {e.code}): {e}", flush=True)
                    return None, e.code
            except Exception as e:
                if i < len(keys) - 1:
                    print(f"[Warning] Gemini API Key #{i+1} 호출 중 예외 발생: {e}. 백업 API Key #{i+2}로 즉시 재시도합니다.", flush=True)
                    continue
                if attempt == max_retries - 1:
                    print(f"[API 에러] Gemini 호출 실패: {e}", flush=True)
                    return None, 500
                wait_time = 1
                print(f"[Warning] 모든 Gemini API Key 호출 실패: {e}. {wait_time}초 후 재시도합니다... (시도 {attempt + 1}/{max_retries})", flush=True)
                time.sleep(wait_time)
            
    # 3차 폴백: Hugging Face (HF_API_KEY)
    hf_key = os.environ.get("HF_API_KEY", "")
    if hf_key:
        print("[Warning] 모든 Gemini API Key 제한 또는 지연 감지. Hugging Face Llama-3 3차 폴백 가동합니다...", flush=True)
        try:
            hf_response = call_huggingface_raw_prompt(prompt, hf_key)
            if hf_response:
                return hf_response, 200
        except Exception as hf_ex:
            print(f"[Warning] Hugging Face 3차 폴백 호출 중 예외 발생: {hf_ex}", flush=True)

    # 4차 폴백: Groq (GROQ_API_KEY)
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        print("[Warning] Gemini 및 Hugging Face API 제한 또는 차단 감지. Groq Llama-3.1 4차 폴백 가동합니다...", flush=True)
        try:
            groq_response = call_groq_raw_prompt(prompt, groq_key)
            if groq_response:
                return groq_response, 200
        except Exception as groq_ex:
            print(f"[Warning] Groq 4차 폴백 호출 중 예외 발생: {groq_ex}", flush=True)

    print("[API 에러] Gemini 호출 실패: 재시도 횟수를 초과했습니다. (429)", flush=True)
    return None, 429

def process_targets(targets, api_key, args):
    if not targets:
        print("업데이트할 대상 문항이 없습니다.", flush=True)
        return
        
    print(f"\n총 {len(targets)}개의 대상 문항이 발견되었습니다.", flush=True)
    if args.dry_run:
        print("[Dry-run 모드] 실제 DB 업데이트를 실행하지 않습니다.", flush=True)
        for idx, t in enumerate(targets[:15]):
            print(f"  [{idx+1}] ID: {t['id']} ({t['year']}년 {t['subject']} {t['qnum']}번) | 사유: {t['reason']} | 해설 유무: {bool(t['explanation'])}", flush=True)
        if len(targets) > 15:
            print(f"  ...외 {len(targets) - 15}개 문항", flush=True)
        return
        
    if not api_key:
        print("[오류] Gemini API Key가 제공되지 않아 업데이트를 중단합니다.", flush=True)
        return
        
    limit = args.limit
    if limit > 0:
        targets = targets[:limit]
        print(f"[테스트 모드] 최초 {limit}개 문항만 처리를 시작합니다.", flush=True)
        
    # PostgreSQL 연결
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
    
    success_count = 0
    fail_count = 0
    current_delay = 10.0  # 기본 딜레이 설정 (제한 극복을 위해 안전하게 10.0초 시작)
    
    print("\n--- [해설 업데이트 루프 가동] ---", flush=True)
    for idx, t in enumerate(targets):
        qid = t['id']
        year = t['year']
        subject = t['subject']
        qnum = t['qnum']
        question = t['question']
        options = t['options']
        answer = t['answer']
        existing_exp = t['explanation']
        
        print(f"[{idx+1}/{len(targets)}] ID: {qid} ({year}년 {subject} {qnum}번) 처리 중... (현재 대기 설정: {current_delay:.1f}초)", flush=True)
        print(f"  - 변경 이유: {t['reason']}", flush=True)
        
        # 프롬프트 설계
        if existing_exp and existing_exp.strip():
            prompt = f"""
이 기출문제의 정답이 새로운 정답({answer})으로 최종 수정 및 확정되었습니다.
기존의 해설 텍스트({existing_exp})를 분석하여, 새로운 정답 번호와 논리에 완벽히 부합하도록 정답 표기 및 상세 설명 구성을 올바르게 교정해 주세요.

[제약 사항]
1. 기존의 양질의 해설 논리와 지식을 최대한 계승하여 보존하십시오.
2. 기존 해설에서 정답 번호(예: **정답**: 4번) 부분을 반드시 수정된 정답({answer})에 맞는 번호로 정확하게 치환해 주십시오. (보기 1번은 인덱스 0번에 대응하므로 정답 값 [1]은 1번 보기, [2]는 2번 보기를 의미합니다.)
3. 기존 설명 중에 "DB 채점은 X번으로 설정되었지만..." 이나 "보기 매칭 기준에 따라 4번을 정답으로 한다"와 같은 임시방편의 구구절절한 모순적 설명을 모두 완전히 삭제하고, 해당 정답이 진정한 정답인 것처럼 자연스럽고 직관적으로 서술을 수정하십시오.
4. 마크다운 스타일(### [정답 및 해설], - **정답**: X번, - **답인 이유** 등)의 출력 포맷을 엄격히 고수하십시오.
5. 다른 잡담이나 설명 멘트 없이, 오직 마크다운 해설 본문만 반환해 주십시오.

[문제 정보]
- 질문: {question}
- 보기: {options}
- 수정된 올바른 정답: {answer}
"""
        else:
            prompt = f"""
이 정보시스템 감리사 기출문제에 대한 고품질의 상세한 정답 및 해설을 작성해 주세요.

[제약 사항]
1. 반드시 다음 마크다운 포맷을 엄격하게 준수하여 출력하십시오:
### [정답 및 해설]
- **정답**: X번
- **답인 이유**:
(상세 설명)
2. 정답 번호는 주어진 수정된 정답({answer}) 정보에 대응하는 정확한 보기를 가리켜야 합니다. (보기 1번은 인덱스 0번에 대응하므로 정답 값 [1]은 1번 보기, [2]는 2번 보기를 의미합니다. 예: answer가 [1]이면 정답은 1번입니다.)
3. 정보시스템 감리사 시험의 공식 도메인 지식(PMBOK, 소프트웨어공학 품질/테스팅 기법, 정규화/트랜잭션 SQL, IT 인프라/클라우드 아키텍처, 보안/암호학, 감리 및 법제도/전자정부 지침 등)에 기반하여 전문성 있고 정확한 해설을 적어주십시오.
4. 각 보기가 왜 정답인지 혹은 오답인지 분석을 상세히 포함시켜 주십시오.
5. 다른 잡담이나 설명 멘트 없이, 오직 마크다운 해설 본문만 반환해 주십시오.

[문제 정보]
- 질문: {question}
- 보기: {options}
- 정답: {answer}
"""
        
        # Gemini API 호출
        new_exp, status_code = call_gemini_api(prompt, api_key)
        
        # 429 에러(Rate Limit) 대응 백오프 및 자동 조절 로직
        if status_code == 429:
            current_delay = min(current_delay + 2.0, 20.0)  # 딜레이 2초 상향 조정
            print(f"  [경고] HTTP 429 Too Many Requests 감지! 70초 쿨다운을 실행하며 대기 설정을 {current_delay:.1f}초로 상향합니다.", flush=True)
            for remain in range(70, 0, -10):
                print(f"    -> 쿨다운 남은 시간: {remain}초...", flush=True)
                time.sleep(10)
            
            # 1차 재시도
            new_exp, status_code = call_gemini_api(prompt, api_key)
            if status_code == 429:
                print(f"  [경고] 재시도에서도 HTTP 429 감지! 70초 추가 쿨다운 후 2차 재시도합니다.", flush=True)
                for remain in range(70, 0, -10):
                    print(f"    -> 쿨다운 남은 시간: {remain}초...", flush=True)
                    time.sleep(10)
                # 2차 재시도
                new_exp, status_code = call_gemini_api(prompt, api_key)
            
        if status_code == 200 and new_exp:
            try:
                # DB 업데이트
                cur.execute(
                    "UPDATE exam_questions SET explanation = %s WHERE id = %s",
                    (new_exp, qid)
                )
                conn.commit()
                success_count += 1
                print(f"  -> [성공] 해설 업데이트 완료.", flush=True)
                # 성공 시 딜레이 서서히 하향 (최소 6.0초 유지)
                current_delay = max(current_delay - 0.2, 6.0)
            except Exception as update_err:
                conn.rollback()
                print(f"  -> [실패] DB 업데이트 중 오류: {update_err}", flush=True)
                fail_count += 1
        else:
            print(f"  -> [실패] Gemini API로부터 해설을 수신하지 못했습니다. (응답 코드: {status_code})", flush=True)
            fail_count += 1
            
        # 속도 제한 예방용 동적 딜레이
        time.sleep(current_delay)
        
    cur.close()
    conn.close()
    
    print("\n--- [업데이트 완료 보고] ---", flush=True)
    print(f"처리 대상 문항: {len(targets)}", flush=True)
    print(f"성공: {success_count}건", flush=True)
    print(f"실패: {fail_count}건", flush=True)

if __name__ == "__main__":
    args = parse_args()
    api_key = get_gemini_api_key(args)
    
    try:
        targets = get_discrepancies_and_diffs()
        process_targets(targets, api_key, args)
    except Exception as e:
        print(f"\n[오류] 프로그램 실행 도중 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()
