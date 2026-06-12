# -*- coding: utf-8 -*-
"""
[10종 대시보드 빌더 스크립트 일괄 패치 스크립트]
- 목적: 빌더 파일들을 읽어서 
  1. Python Isolated Mode 대응을 위해 sys.path.append 설정 주입 및 불필요한 PDF 라이브러리 임포트 주석 처리
  2. PDF 파싱 로직을 exam_database.js 다이렉트 로드로 변경
  3. HTML 템플릿의 문항 개수 뱃지를 dynamic하게 갱신하는 JS 코드를 주입합니다.
"""
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

NEW_EXTRACT_FUNCS = r"""
def load_exam_database_dict():
    js_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_database.js"
    if not os.path.exists(js_path):
        return {}
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
    start = content.find('{')
    end = content.rfind('}')
    if start == -1 or end == -1:
        return {}
    import json
    try:
        return json.loads(content[start:end+1])
    except Exception as e:
        print(f"[경고] exam_database.js JSON 파싱 실패: {e}")
        return {}

def run_extraction_and_mapping():
    question_db = {}
    concept_map = {concept: [] for concept in CONCEPT_KEYWORDS}
    concept_map["[기타]"] = []
    
    exam_db_dict = load_exam_database_dict()
    
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
        
    print(f"[1/3] {subject_code} 과목 기출문제 로딩 및 공식범위 매핑 중...")
    
    for year in range(2015, 2027):
        if subject_code == "DB":
            q_start, q_end = 51, 75
        elif subject_code == "PM":
            q_start, q_end = 1, 25
        elif subject_code == "SE":
            q_start, q_end = 26, 50
        elif subject_code == "SA":
            if year == 2015:
                q_start, q_end = 76, 90
            else:
                q_start, q_end = 76, 100
        elif subject_code == "SC":
            if year == 2015:
                q_start, q_end = 91, 105
            else:
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
                    if re.match(r"^[a-zA-Z0-9\-\_\/]+$", kw):
                        pattern = rf"\b{re.escape(kw.lower())}\b"
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
                
    return question_db, concept_map
"""

JS_UPDATE_BLOCK = r"""        if (document.getElementById('total-question-badge')) {
            const uniqueQuestions = new Set();
            const mappingsObj = (typeof conceptMappings !== 'undefined') ? conceptMappings : ((typeof topicMapping !== 'undefined') ? topicMapping : []);
            mappingsObj.forEach(item => {
                if (item.questions) {
                    item.questions.forEach(q => {
                        uniqueQuestions.add(q.year + "_" + q.num);
                    });
                }
            });
            document.getElementById('total-question-badge').textContent = uniqueQuestions.size;
        }"""

SYS_PATH_INJECT = """# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
"""

def main():
    base_dir = r"d:\100.lyj\anti_workspace\jolly-carson"
    print("=== [시작] 대시보드 빌더 스크립트 일괄 패치 (Isolated & 라이브러리 예외 대응) ===")
    
    for builder in BUILDERS:
        file_path = os.path.join(base_dir, builder)
        if not os.path.exists(file_path):
            print(f"[오류] 파일을 찾을 수 없음: {builder}")
            continue
            
        print(f"[*] {builder} 패치 적용 중...")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 0. sys.path.append 코드 주입
        if "sys.path.append" not in content:
            if content.startswith("# -*- coding: utf-8 -*-"):
                content = content.replace("# -*- coding: utf-8 -*-", SYS_PATH_INJECT, 1)
            else:
                content = SYS_PATH_INJECT + content
            print("  - sys.path.append 헤더 주입 완료")
        else:
            print("  - [안내] sys.path.append가 이미 포함되어 있음")
            
        # 0-1. pdfplumber, fitz, image_cropper 등 불필요한 라이브러리 임포트 주석 처리
        content = content.replace("import pdfplumber", "# import pdfplumber")
        content = content.replace("import fitz", "# import fitz")
        content = content.replace("import image_cropper", "# import image_cropper")
        print("  - pdfplumber, fitz, image_cropper 임포트 주석 처리 완료")
            
        # 1. run_extraction_and_mapping 함수를 NEW_EXTRACT_FUNCS로 교체
        pattern_func = r"def run_extraction_and_mapping\(\):[\s\S]+?return question_db, concept_map"
        if re.search(pattern_func, content):
            content = re.sub(pattern_func, lambda m: NEW_EXTRACT_FUNCS.strip(), content)
            print("  - run_extraction_and_mapping 함수 대체 완료")
        else:
            print("  - [경고] run_extraction_and_mapping 함수 패턴을 찾을 수 없음")
            
        # 2. HTML 뱃지 마크업 동적화 (총 분석 데이터: 300 문항 -> 총 분석 데이터: <span id="total-question-badge">0</span> 문항)
        content = re.sub(r"총 분석 데이터:\s*\d+\s*문항", '총 분석 데이터: <span id="total-question-badge">0</span> 문항', content)
        print("  - HTML 총 분석 데이터 뱃지 마크업 동적화 완료")
        
        # 3. 자바스크립트 갱신 블록 삽입 (기존에 이미 uniqueQuestions 가 포함되어 있으면 건너뜀)
        if "uniqueQuestions" not in content:
            # renderTopics(); 또는 renderAccordions('all'); 호출 직전에 JS_UPDATE_BLOCK 삽입
            if "renderTopics();" in content:
                content = content.replace("renderTopics();", JS_UPDATE_BLOCK + "\n    renderTopics();")
                print("  - JS 카운터 주입 완료 (renderTopics)")
            elif "renderAccordions('all');" in content:
                content = content.replace("renderAccordions('all');", JS_UPDATE_BLOCK + "\n    renderAccordions('all');")
                print("  - JS 카운터 주입 완료 (renderAccordions)")
            else:
                print("  - [경고] JS 초기화 함수를 찾을 수 없음")
        else:
            print("  - [안내] 자바스크립트 카운터가 이미 삽입되어 있음")
            
        # 변경 사항 파일에 쓰기
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
    print("\n=== [완료] 전체 10개 빌더 스크립트 패치 완료 ===")

if __name__ == "__main__":
    main()
