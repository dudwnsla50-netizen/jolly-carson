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

LAYOUT_THRESHOLDS = {
    2015: [130.0, 300.0, 480.0],
    2016: [180.0, 400.0],
    2017: [180.0],
    2018: [180.0],
    2019: [180.0],
    2020: [200.0, 450.0, 560.0],
    2021: [200.0],
    2022: [140.0, 300.0, 430.0],
    2023: [200.0],
    2024: [180.0],
    2025: [180.0, 380.0, 580.0],
    2026: [180.0]
}

def clean_html_tags(html_str):
    text = re.sub(r'<[^>]+>', '', html_str)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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
        # 폴백 파서
        pairs = re.findall(r'"(\d{4}_\d+)":\s*"(.*?)"(?=,\s*"|\s*\})', match.group(1), re.DOTALL)
        parsed = {}
        for k, v in pairs:
            parsed[k] = v.replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')
        return parsed

def save_db_js(js_path, db_dict):
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("const examDatabase = ")
        f.write(json.dumps(db_dict, ensure_ascii=False, indent=2))
        f.write(";\n")

def extract_images_for_questions(html_path, year):
    if not os.path.exists(html_path):
        print(f"  [경고] HTML 파일이 없습니다: {html_path}")
        return {}

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 페이지 단위로 나누어 각 페이지별로 band/top 정렬을 수행 (페이지 간 이미지 섞임 방지)
    page_chunks = content.split('<div class="page-wrapper"')
    all_sorted_elements = []
    
    thresholds = LAYOUT_THRESHOLDS.get(year, [250.0])
    
    for page_idx, chunk in enumerate(page_chunks):
        if page_idx == 0:
            # 첫 번째 조각은 첫 페이지 이전의 헤더 영역이므로 제외
            continue
            
        elements = re.findall(r'(<p[^>]*>[\s\S]*?</p>|<img[^>]*>)', chunk)
        positioned_elements = []
        
        last_p_left = 0.0
        last_p_top = 0.0
        last_p_band = 0
        
        for idx, el in enumerate(elements):
            top = 0.0
            left = 0.0
            
            top_match = re.search(r'top:([\d\.-]+)(?:pt|px)?', el)
            left_match = re.search(r'left:([\d\.-]+)(?:pt|px)?', el)
            
            if top_match:
                top = float(top_match.group(1))
            if left_match:
                left = float(left_match.group(1))
                
            final_left = left
            final_top = top
            
            if "<img" in el:
                matrix_match = re.search(r'transform:matrix\([^,]+,[^,]+,[^,]+,[^,]+,([\d\.-]+),([\d\.-]+)\)', el)
                if matrix_match:
                    final_left = left + float(matrix_match.group(1))
                    final_top = top + float(matrix_match.group(2))
                    
                # 이미지 좌표 누락 혹은 음수 렌더링 시 직전 P 태그의 좌표를 상속받아 정렬
                if not left_match or final_left < 0.0:
                    final_left = last_p_left
                    final_top = last_p_top + 0.1
                    band = last_p_band
                else:
                    band = sum(1 for t in thresholds if final_left >= t)
            else:
                band = sum(1 for t in thresholds if final_left >= t)
                last_p_left = final_left
                last_p_top = final_top
                last_p_band = band
                
            positioned_elements.append({
                "element": el,
                "band": band,
                "top": final_top,
                "left": final_left
            })
            
        # 해당 페이지 내에서 (band, top) 기준으로 정렬
        positioned_elements.sort(key=lambda x: (x["band"], x["top"]))
        for item in positioned_elements:
            all_sorted_elements.append((item["element"], item["band"]))
            
    # 소프트웨어공학의 범위는 26번부터 50번까지임
    question_elements = {n: [] for n in range(26, 52)}
    current_q = None
    q_start_band = None
    
    for el, band in all_sorted_elements:
        if "<p" in el:
            txt = clean_html_tags(el)
            # 모든 번호 패턴 감지하여 소프트웨어공학 범위를 벗어나면 수집 중단(None) 처리
            match_any = re.search(r'^(\d+)\.', txt)
            if match_any:
                q_num = int(match_any.group(1))
                if 26 <= q_num <= 50:
                    current_q = q_num
                    q_start_band = band
                else:
                    current_q = None
                    q_start_band = None
                    
        if current_q is not None:
            # 문항이 시작된 단(Band)과 일치하는 요소만 수집하여 다른 단에 있는 타 과목 내용이 섞이는 것을 원천 방지
            if band == q_start_band:
                question_elements[current_q].append(el)
            
    # 과목별 HTML 데이터 빌드
    enriched_questions = {}
    for num in range(26, 51):
        q_elements = question_elements[num]
        if not q_elements:
            continue
            
        # 일관성을 위해 이미지가 없는 텍스트 문제도 모두 HTML로 변환하여 덮어쓰고, 기존 오염 데이터를 확실하게 정화함
        body_parts = []
        for el in q_elements:
            if "<p" in el:
                body_parts.append(el)
            elif "<img" in el:
                # 이미지 크기 max-width: 50% 및 display: block, margin: 0.8rem 0 설정
                img_style = 'max-width: 50%; height: auto; display: block; margin: 0.8rem 0; border-radius: 4px; border: 1px solid rgba(255,255,255,0.06);'
                modified_img = re.sub(r'style="[^"]*"', f'style="{img_style}"', el)
                
                if 'position:absolute' in modified_img:
                    modified_img = re.sub(r'position:\s*absolute;?', '', modified_img)
                
                body_parts.append(modified_img)
                
        html_body = "".join(body_parts)
        enriched_questions[f"{year}_{num}"] = html_body
        
    return enriched_questions

def main():
    print("=== [시작] SE 기출 HTML 지문 이미지 임베딩 및 지문 완전 정화 작업 ===")
    
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
            se_db[key] = html_content
            shared_db[key] = html_content
            total_embedded += 1
            
    # 3. 변경 내용 저장
    if total_embedded > 0:
        save_db_js(SE_DB_JS_PATH, se_db)
        save_db_js(SHARED_DB_JS_PATH, shared_db)
        print(f"\n✅ 지문 데이터베이스 업데이트 완료! (총 {total_embedded}개 문항 정화 및 보강됨)")
    else:
        print("\nℹ️ 새로 업데이트된 지문이 없습니다.")

if __name__ == "__main__":
    main()
