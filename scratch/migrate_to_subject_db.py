# -*- coding: utf-8 -*-
import os
import re

BUILDERS = [
    "build_premium_db_viewer.py",
    "build_premium_db_official_viewer.py",
    "build_premium_pm_viewer.py",
    "build_premium_pm_official_viewer.py",
    "build_premium_se_viewer.py",
    "build_premium_se_official_viewer.py",
    "build_premium_sa_viewer.py",
    "build_premium_sa_official_viewer.py",
    "build_premium_sc_viewer.py",
    "build_premium_sc_official_viewer.py"
]

base_dir = r"d:\100.lyj\anti_workspace\jolly-carson"

NEW_DB_LOADER_AND_MAPPER = """def load_exam_database_dict(subject_code):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    js_path = os.path.join(base_dir, "reports", "exam_db", f"{subject_code.lower()}_db.js")
    
    # 폴백: 개별 DB가 아직 없는 경우 공통 DB 참조
    if not os.path.exists(js_path):
        js_path = os.path.join(base_dir, "reports", "exam_database.js")
        
    if not os.path.exists(js_path):
        return {}
        
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Greedy 매칭 패턴 ((\{[\s\S]*\}))을 적용하여 지문 내 C++ 클래스 마감 기호(};) 오인식 방지
    match = re.search(r"const\\s+examDatabase\\s*=\\s*(\\{[\\s\\S]*\\});", content)
    if not match:
        return {}
        
    js_obj_str = match.group(1)
    try:
        import json
        return json.loads(js_obj_str)
    except Exception as e:
        # 정규식 파서 폴백 (JSON Decode 실패 시 대응)
        pairs = re.findall(r'"(\\d{4}_\\d+)":\\s*"(.*?)"(?=,\\s*"|\\s*\\})', js_obj_str, re.DOTALL)
        parsed = {}
        for k, v in pairs:
            parsed[k] = v.replace('\\\\\\\\', '\\\\').replace('\\\\"', '"').replace('\\\\n', '\\n')
        return parsed

def run_extraction_and_mapping():
    question_db = {}
    concept_map = {concept: [] for concept in CONCEPT_KEYWORDS}
    concept_map["[기타]"] = []
    
    filename_lower = os.path.basename(__file__).lower()
    if "_db_" in filename_lower:
        subject_code = "DB"
    elif "_pm_" in filename_lower:
        subject_code = "PM"
    elif "_se_" in filename_lower:
        subject_code = "SE"
    elif "_sa_" in filename_lower:
        subject_code = "SA"
    elif "_sc_" in filename_lower:
        subject_code = "SC"
    else:
        subject_code = "UNKNOWN"
        
    exam_db_dict = load_exam_database_dict(subject_code)
    
    print(f"[1/3] {subject_code} 과목 기출문제 로딩 및 공식범위 매핑 중...")
    
    for year in range(2015, 2027):
        if subject_code == "DB":
            q_start, q_end = 51, 75
        elif subject_code == "PM":
            q_start, q_end = 1, 25
        elif subject_code == "SE":
            q_start, q_end = 26, 50
        elif subject_code == "SA":
            q_start, q_end = 76, 100
        elif subject_code == "SC":
            q_start, q_end = 101, 120
        else:
            continue
            
        for num in range(q_start, q_end + 1):
            key = f"{year}_{num}"
            q_text_clean = exam_db_dict.get(key)
            if not q_text_clean:
                continue
                
            question_db[key] = q_text_clean
            
            body_lower = q_text_clean.lower()
            matched_concepts = []
            for concept, keywords in CONCEPT_KEYWORDS.items():
                for kw in keywords:
                    if re.match(r"^[a-zA-Z0-9\\-\\_\\/]+$", kw):
                        pattern = rf"\\\\b{re.escape(kw.lower())}\\\\b"
                        if re.search(pattern, body_lower):
                            matched_concepts.append(concept)
                            break
                    else:
                        if kw.lower() in body_lower:
                            matched_concepts.append(concept)
                            break
                            
            if not matched_concepts:
                matched_concepts.append("[기타]")
                            
            for concept in matched_concepts:
                concept_map[concept].append({
                    "year": year,
                    "num": num
                })
                
    return question_db, concept_map"""

def main():
    print("=== [시작] 과목별 DB 로딩 및 매퍼 최신화 패치 적용 ===")
    
    for builder in BUILDERS:
        file_path = os.path.join(base_dir, builder)
        if not os.path.exists(file_path):
            print(f"[경고] 파일 존재하지 않음: {builder}")
            continue
            
        print(f"[*] {builder} 처리 중...")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 기존 load_exam_database_dict 와 run_extraction_and_mapping 함수 영역을 일괄 치환
        # 두 함수가 연속해서 정의되어 있는 부분을 찾아서 교체 (람다 리플레이서 사용)
        pattern = r"def load_exam_database_dict\([\s\S]*?return question_db, concept_map"
        if re.search(pattern, content):
            content = re.sub(pattern, lambda m: NEW_DB_LOADER_AND_MAPPER, content)
            print("  - [성공] load_exam_database_dict 및 run_extraction_and_mapping 함수 전면 개편 적용")
        else:
            print("  - [경고] 교체 대상 함수 패턴을 찾을 수 없음")
            
        # 파일 저장
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
    print("=== [완료] 패치 적용 완료 ===")

if __name__ == "__main__":
    main()
