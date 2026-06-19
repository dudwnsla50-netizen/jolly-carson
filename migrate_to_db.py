# -*- coding: utf-8 -*-
"""
[Jolly-Carson SQLite 데이터 이관 마이그레이터 - 개정판]
- 작성자: Antigravity
- 목적: reports/exam_db/*.js 기출문제를 질문과 보기로 파싱하여 분리하고, 
        정답 캐시 파일(past_exams_db.json)과 매핑하여 SQLite DB로 정교하게 이관합니다.
"""
import os
import re
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "reports", "exam_db")
DB_PATH = os.path.join(DB_DIR, "jolly_carson.db")
PAST_EXAMS_DB_PATH = os.path.join(BASE_DIR, "data", "past_exams_db.json")

def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 구조 변경을 위해 기존 테이블이 존재한다면 확실히 삭제 후 재생성
    cursor.execute("DROP TABLE IF EXISTS exam_questions")
    
    # 1. 기출문제 본문 테이블 (질문, 보기, 정답, 해설 분리 구조)
    cursor.execute("""
    CREATE TABLE exam_questions (
        id TEXT PRIMARY KEY,
        year INTEGER NOT NULL,
        subject TEXT NOT NULL,
        question_num INTEGER NOT NULL,
        question TEXT NOT NULL,
        options TEXT NOT NULL,     -- JSON array (예: '["보기1", "보기2", "보기3", "보기4"]')
        answer INTEGER,            -- 정수형 1~4 (정답이 매핑되지 않는 경우 NULL)
        explanation TEXT           -- 정답 해설 (없는 경우 NULL)
    )
    """)
    
    # 2. 대시보드 매핑 데이터 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dashboard_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        dashboard_type TEXT NOT NULL,
        concept TEXT NOT NULL,
        category TEXT NOT NULL,
        count INTEGER NOT NULL,
        core_concept TEXT NOT NULL,
        features TEXT NOT NULL,
        scope TEXT NOT NULL,
        rep_question TEXT NOT NULL,
        rep_year INTEGER,
        rep_num INTEGER,
        global_idx INTEGER,
        years TEXT,         -- JSON array (예: '[2026, 2025]')
        questions TEXT      -- JSON array (예: '[{"year": 2026, "num": 109}]')
    )
    """)
    
    conn.commit()
    conn.close()
    print(f"[SQLite] 테이블 구조 생성/초기화 완료: {DB_PATH}")

def split_question_and_options(body_text):
    """
    [설계 의도]
    기출문제의 전체 body 문자열에서 보기 시작점(① 또는 ❶)을 기점으로
    질문(question)과 4지선다 보기 배열(options)을 안전하게 추출합니다.
    """
    # 보기 시작 기호 위치 탐색
    match = re.search(r'[\s]*(?:①|❶)', body_text)
    if not match:
        # 보기 번호가 없는 비정형 문제일 경우 전체를 질문으로 간주
        return body_text.strip(), []
        
    split_idx = match.start()
    question = body_text[:split_idx].strip()
    options_text = body_text[split_idx:]
    
    # 보기 기호(①~④, ❶~❹)를 구분자로 분할하여 실제 보기 텍스트 수집
    parts = re.split(r'[\s]*(?:①|②|③|④|❶|❷|❸|❹)', options_text)
    options = [p.strip() for p in parts if p.strip()]
    
    return question, options

def load_past_exams_answers():
    """data/past_exams_db.json 파일에서 정답 캐시 데이터 로드"""
    if not os.path.exists(PAST_EXAMS_DB_PATH):
        return {}
    try:
        with open(PAST_EXAMS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[경고] past_exams_db.json 로드 실패: {e}")
        return {}

def migrate_exam_questions():
    """reports/exam_db/*_db.js 파싱 후 분리하여 이관"""
    print("[SQLite] 기출문제 데이터 분리 이관 시작...")
    
    # 정답 캐시 데이터 불러오기
    answers_cache = load_past_exams_answers()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    subjects = ["db", "pm", "sa", "sc", "se"]
    total_count = 0
    
    for sub in subjects:
        file_path = os.path.join(DB_DIR, f"{sub}_db.js")
        if not os.path.exists(file_path):
            print(f"  -> {file_path} 파일이 존재하지 않습니다. 스킵.")
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        match = re.search(r"const\s+examDatabase\s*=\s*(\{[\s\S]*\});", content)
        if not match:
            print(f"  -> {sub}_db.js 정규식 매칭 실패.")
            continue
            
        js_obj_str = match.group(1)
        try:
            data = json.loads(js_obj_str)
        except Exception as e:
            # JSON 파싱 실패 시 예외 방지 정규식 폴백 작동
            print(f"  -> {sub}_db.js JSON 파싱 실패 ({e}). 정규식 폴백 작동.")
            pairs = re.findall(r'"(\d{4}_\d+)":\s*"(.*?)"(?=,\s*"|\s*\})', js_obj_str, re.DOTALL)
            data = {}
            for k, v in pairs:
                data[k] = v.replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')
                
        for key, body in data.items():
            # key 예: "2016_101" -> year: 2016, q_num: 101
            year, q_num = map(int, key.split("_"))
            
            # 질문 본문과 보기 분리 실행
            question, options = split_question_and_options(body)
            
            # 캐시 데이터와 매칭하여 정답/해설 정보 확보
            cached_item = answers_cache.get(key, {})
            answer = cached_item.get("answer")
            explanation = cached_item.get("explanation")
            
            cursor.execute("""
            INSERT OR REPLACE INTO exam_questions (id, year, subject, question_num, question, options, answer, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key, 
                year, 
                sub.upper(), 
                q_num, 
                question, 
                json.dumps(options, ensure_ascii=False), 
                answer, 
                explanation
            ))
            total_count += 1
            
    conn.commit()
    conn.close()
    print(f"[SQLite] 기출문제 총 {total_count}건 분리 이관 완료.")

def migrate_dashboard_mappings():
    """reports/js/data/*.js 파싱 및 이관 (기존 로직 유지)"""
    print("[SQLite] 대시보드 아코디언 매핑 데이터 이관 시작...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 기존 아코디언 데이터 삭제 후 재생성 (중복 누적 방지)
    cursor.execute("DELETE FROM dashboard_mappings")
    
    data_dir = os.path.join(BASE_DIR, "reports", "js", "data")
    if not os.path.exists(data_dir):
        print(f"  -> {data_dir} 디렉토리가 존재하지 않습니다. 스킵.")
        conn.close()
        return
        
    files = os.listdir(data_dir)
    total_count = 0
    
    for filename in files:
        if not filename.endswith(".js"):
            continue
            
        parts = filename[:-3].split("_")
        if len(parts) != 2:
            continue
            
        sub, dtype = parts[0], parts[1]
        file_path = os.path.join(data_dir, filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        match = re.search(r"window\.dashboardData\s*=\s*(\[[\s\S]*\]);", content)
        if not match:
            print(f"  -> {filename} 정규식 매칭 실패.")
            continue
            
        js_arr_str = match.group(1)
        try:
            data = json.loads(js_arr_str)
        except Exception as e:
            print(f"  -> {filename} JSON 파싱 오류: {e}")
            continue
            
        for item in data:
            cursor.execute("""
            INSERT INTO dashboard_mappings (
                subject, dashboard_type, concept, category, count,
                core_concept, features, scope, rep_question,
                rep_year, rep_num, global_idx, years, questions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sub.upper(),
                dtype,
                item.get("concept", ""),
                item.get("category", ""),
                item.get("count", 0),
                item.get("core_concept", ""),
                item.get("features", ""),
                item.get("scope", ""),
                item.get("rep_question", ""),
                int(item.get("rep_year")) if item.get("rep_year") else None,
                int(item.get("rep_num")) if item.get("rep_num") else None,
                item.get("global_idx"),
                json.dumps(item.get("years", []), ensure_ascii=False),
                json.dumps(item.get("questions", []), ensure_ascii=False)
            ))
            total_count += 1
            
    conn.commit()
    conn.close()
    print(f"[SQLite] 대시보드 매핑 총 {total_count}건 이관 완료.")

def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    create_tables()
    migrate_exam_questions()
    migrate_dashboard_mappings()
    print("[완료] SQLite 데이터베이스 리팩토링 및 이관 완료.")

if __name__ == "__main__":
    main()
