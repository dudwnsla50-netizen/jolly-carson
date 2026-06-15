import os
import json
import re

# 현재 대화의 아티팩트 디렉토리 경로
ARTIFACT_DIR = r"C:\Users\DCCIS040000\.gemini\antigravity-ide\brain\7e1fd111-1dc1-495d-82a1-c40573600184"

def get_output_paths(filename):
    """
    주어진 파일명에 대해 로컬 워크스페이스 reports 경로와 아티팩트 경로를 반환합니다.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(base_dir, "reports", filename)
    artifact_path = os.path.join(ARTIFACT_DIR, filename)
    return local_path, artifact_path

def update_shared_db(new_db, subject_code):
    """
    로컬 및 아티팩트 경로의 과목별 JS 파일에 새로운 기출문제 데이터를 머지하고 저장합니다.
    """
    filename = f"exam_db/{subject_code.lower()}_db.js"
    local_js_path, artifact_js_path = get_output_paths(filename)
    
    merged_db = {}
    
    # 정규식 기반 JS 객체 강인 파서 정의
    def parse_js_db(path):
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            match = re.search(r"const\s+examDatabase\s*=\s*(\{[\s\S]*\});", content)
            if not match:
                return {}
            js_obj_str = match.group(1)
            pairs = re.findall(r'"(\d{4}_\d+)":\s*"(.*?)"(?=,\s*"|\s*\})', js_obj_str, re.DOTALL)
            parsed = {}
            for k, v in pairs:
                parsed[k] = v.replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')
            return parsed
        except Exception as e:
            print(f"[경고] {os.path.basename(path)} 파싱 중 오류 발생: {e}")
            return {}
            
    # 1. 기존 로컬 js 파일이 존재하면 읽어서 파싱 시도
    merged_db = parse_js_db(local_js_path)
            
    # 2. 기존 아티팩트 js 파일이 존재하고 로컬에서 데이터를 못 읽었을 경우 대용으로 사용
    if not merged_db:
        merged_db = parse_js_db(artifact_js_path)

    # 3. 새로운 데이터 병합
    if new_db:
        merged_db.update(new_db)
        
    # 4. JSON 문자열로 포맷팅 및 JS 코드 작성
    db_json = json.dumps(merged_db, indent=2, ensure_ascii=False)
    js_content = f"const examDatabase = {db_json};\n"
    
    # 5. 로컬 경로에 저장
    os.makedirs(os.path.dirname(local_js_path), exist_ok=True)
    with open(local_js_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"[{subject_code} DB] 로컬 업데이트 완료: {local_js_path}")
    
    # 6. 아티팩트 경로에 저장
    os.makedirs(os.path.dirname(artifact_js_path), exist_ok=True)
    with open(artifact_js_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"[{subject_code} DB] 아티팩트 업데이트 완료: {artifact_js_path}")
