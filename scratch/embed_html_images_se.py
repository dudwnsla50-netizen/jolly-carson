# -*- coding: utf-8 -*-
import os
import sys
import re
import json

# 인코딩 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r"d:\100.lyj\anti_workspace\jolly-carson"
HTML_DIR = os.path.join(BASE_DIR, "data", "past_exam", "html")
SE_DB_JS_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "se_db.js")
SHARED_DB_JS_PATH = os.path.join(BASE_DIR, "reports", "exam_database.js")

EXAM_FILES = [
    {"year": 2015, "filename": "2015년(제16회) 정보시스템감리사 필기시험문제(답안).html"},
    {"year": 2016, "filename": "2016년(제17회) 정보시스템 감리사 필기시험 문제 및 답안.html"},
    {"year": 2017, "filename": "2017년(제18회) 정보시스템 감리사 필기시험 문제 및 답안.html"},
    {"year": 2018, "filename": "2018년(제19회)정보시스템 감리사 필기시험 문제 및 답안.html"},
    {"year": 2019, "filename": "2019년(제20회)정보시스템 감리사 필기시험 문제 및 답안.html"},
    {"year": 2020, "filename": "2020년(제21회) 정보시스템 감리사 필기시험 문제 및 답안.html"},
    {"year": 2021, "filename": "2021년(제22회) 정보시스템 감리사 필기시험 문제 및 답안.html"},
    {"year": 2022, "filename": "2022년(제23회) 정보시스템 감리사 필기시험 문제 및 답안.html"},
    {"year": 2023, "filename": "2023년 정보시스템 감리사 자격검정 필기시험 문제 A형(답안포함).html"},
    {"year": 2024, "filename": "2024년(제25회) 감리사 자격검정 필기시험 문제-A형.html"},
    {"year": 2025, "filename": "2025년 감리사 자격검정 필기시험 문제-A형(답포함).html"},
    {"year": 2026, "filename": "2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.html"}
]

def load_db_js(js_path):
    if not os.path.exists(js_path):
        return {}
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"const\s+examDatabase\s*=\s*(\{[\s\S]*\});", content)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except Exception:
        # 간단한 파서 폴백
        pairs = re.findall(r'"(\d{4}_\d+)":\s*"(.*?)"(?=,\s*"|\s*\})', match.group(1), re.DOTALL)
        parsed = {}
        for k, v in pairs:
            parsed[k] = v.replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')
        return parsed

def save_db_js(js_path, db_dict):
    db_json = json.dumps(db_dict, ensure_ascii=False, indent=2)
    # C++ 클래스 마감 기호 중복 검출 방지를 위한 greedy 매칭 호환용 선언 작성
    content = f"const examDatabase = {db_json};\n\nif (typeof module !== 'undefined' && module.exports) {{\n    module.exports = examDatabase;\n}}\n"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(content)

def clean_html_tags(text):
    # 단순 텍스트 내 태그 정리용
    return re.sub(r'<[^>]*>', '', text).strip()

def extract_images_for_questions(html_path, year):
    if not os.path.exists(html_path):
        print(f"  [경고] HTML 파일이 없습니다: {html_path}")
        return {}

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # w:body 자식 엘리먼트 단위로 분석하거나 단순 정규식 라인별 수집
    # 각 line을 분석하기 쉽게 <p> 또는 <img> 태그 단위로 파싱
    elements = re.findall(r'(<p[^>]*>[\s\S]*?</p>|<img[^>]*>)', content)
    
    question_elements = {n: [] for n in range(26, 52)} # 51번(다음 과목 첫문제)까지 수집
    current_q = None
    
    for el in elements:
        # 문제 번호 탐색 (예: 26., 45., 51.)
        if "<p" in el:
            txt = clean_html_tags(el)
            # 단어 경계 + 숫자 + 점 패턴 감지
            match = re.search(r'^(2[6-9]|[3-4][0-9]|5[0-1])\.', txt)
            if match:
                current_q = int(match.group(1))
                
        if current_q is not None:
            question_elements[current_q].append(el)
            
    # 과목별 HTML 데이터 빌드
    enriched_questions = {}
    for num in range(26, 51):
        q_elements = question_elements[num]
        if not q_elements:
            continue
            
        # 이 문항 내에서 <img> 태그들이 존재하는지 확인
        imgs = [el for el in q_elements if "<img" in el]
        if not imgs:
            continue
            
        print(f"  -> {year}년 {num}번 문항 이미지 {len(imgs)}개 감지")
        
        # 보기 번호별 이미지 분배 및 지문 매핑
        # HTML 텍스트의 흐름을 분석하여 지문과 보기에 적절히 이미지를 결합합니다.
        body_parts = []
        current_state = "body" # body, q1, q2, q3, q4
        
        for el in q_elements:
            if "<p" in el:
                txt = clean_html_tags(el)
                if "①" in txt:
                    current_state = "q1"
                elif "②" in txt:
                    current_state = "q2"
                elif "③" in txt:
                    current_state = "q3"
                elif "④" in txt:
                    current_state = "q4"
                
                body_parts.append(el)
            elif "<img" in el:
                # 이미지 크기를 반응형에 최적화하도록 style 강제 조정
                img_style = 'max-width: 100%; height: auto; display: block; margin: 0.5rem 0; border-radius: 4px; border: 1px solid rgba(255,255,255,0.06);'
                modified_img = re.sub(r'style="[^"]*"', f'style="{img_style}"', el)
                
                # absolute position이 혹시 남아있으면 인라인으로 강제 변경
                if 'position:absolute' in modified_img:
                    modified_img = re.sub(r'position:\s*absolute;?', '', modified_img)
                
                body_parts.append(modified_img)
                
        # 수집된 HTML 조각들을 문항 본문으로 결합
        html_body = "".join(body_parts)
        enriched_questions[f"{year}_{num}"] = html_body
        
    return enriched_questions

def main():
    print("=== [시작] SE 기출 HTML 지문 이미지 임베딩 작업 ===")
    
    # 1. 기존 SE DB 및 공통 DB 로드
    se_db = load_db_js(SE_DB_JS_PATH)
    shared_db = load_db_js(SHARED_DB_JS_PATH)
    
    print(f"현재 로드된 SE DB 문항 수: {len(se_db)}")
    
    total_embedded = 0
    
    # 2. 각 연도별로 이미지 추출
    for exam in EXAM_FILES:
        year = exam["year"]
        html_name = exam["filename"]
        html_path = os.path.join(HTML_DIR, html_name)
        
        print(f"\n👉 {year}년도 기출 HTML 분석 중...")
        enriched = extract_images_for_questions(html_path, year)
        
        for key, html_content in enriched.items():
            # 기존 텍스트 지문을 HTML 지문으로 대체 보강
            se_db[key] = html_content
            shared_db[key] = html_content
            total_embedded += 1
            
    # 3. 변경 내용 저장
    if total_embedded > 0:
        save_db_js(SE_DB_JS_PATH, se_db)
        save_db_js(SHARED_DB_JS_PATH, shared_db)
        print(f"\n✅ 지문 데이터베이스 업데이트 완료! (총 {total_embedded}개 문항 보강됨)")
    else:
        print("\nℹ️ 새로 업데이트된 지문이 없습니다.")

if __name__ == "__main__":
    main()
