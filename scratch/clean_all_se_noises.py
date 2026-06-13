# -*- coding: utf-8 -*-
import os
import sys
import re
import json
import base64
import io
from PIL import Image

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r"d:\100.lyj\anti_workspace\jolly-carson"
SE_DB_JS_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "se_db.js")
SHARED_DB_JS_PATH = os.path.join(BASE_DIR, "reports", "exam_database.js")

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
    content = f"const examDatabase = {db_json};\n\nif (typeof module !== 'undefined' && module.exports) {{\n    module.exports = examDatabase;\n}}\n"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(content)

def compress_base64_image(img_tag):
     # img 태그 내의 src="data:image/...;base64,..." 에서 base64 데이터를 파싱합니다.
    src_match = re.search(r'src="data:image/([^;]+);base64,([^"]+)"', img_tag)
    if not src_match:
        return img_tag
    
    img_type = src_match.group(1)
    b64_data = src_match.group(2).strip().replace('\n', '').replace('\r', '')
    
    try:
        img_bytes = base64.b64decode(b64_data)
        img = Image.open(io.BytesIO(img_bytes))
        
        # 해상도 50% 축소
        w, h = img.size
        new_size = (max(1, w // 2), max(1, h // 2))
        img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # 50% 품질로 JPEG 포맷 압축
        out_buf = io.BytesIO()
        img_resized.convert("RGB").save(out_buf, format="JPEG", quality=50)
        compressed_b64 = base64.b64encode(out_buf.getvalue()).decode('utf-8')
        
        # 새로운 img 태그 구성
        new_src = f'src="data:image/jpeg;base64,{compressed_b64}"'
        new_tag = re.sub(r'src="[^"]+"', new_src, img_tag)
        return new_tag
    except Exception as e:
        print(f"      [경고] 이미지 압축 에러: {e}")
        return img_tag

def sanitize_and_compress_question(key, val):
    if not isinstance(val, str) or "<p" not in val:
        return val, False
        
    sub_elements = re.findall(r'(<p[^>]*>[\s\S]*?</p>|<img[^>]*>)', val)
    
    # 1. 보기 ④번의 인덱스 찾기 (가장 마지막 ④번)
    q4_idx = -1
    for idx, el in enumerate(sub_elements):
        if "<p" in el:
            txt = re.sub(r'<[^>]*>', '', el).strip()
            if "④" in txt:
                q4_idx = idx
                
    changed = False
    cleaned_elements = []
    
    if q4_idx != -1:
        # 보기 ④번이 발견되면 보기 ④번 인덱스까지만 취하고 그 뒤의 모든 노이즈를 일괄 소거합니다.
        cleaned_elements.extend(sub_elements[:q4_idx+1])
        if len(sub_elements) > (q4_idx + 1):
            # 사소한 공백이나 구분선만 있는 경우는 제외하고 실질적 텍스트/이미지가 있을 때만 변경된 것으로 판단
            post_elements = sub_elements[q4_idx+1:]
            post_text = " ".join(re.sub(r'<[^>]*>', '', el).strip() for el in post_elements if "<p" in el).strip()
            has_img = any("<img" in el for el in post_elements)
            if post_text or has_img:
                print(f"    -> [{key}] 보기 ④번 뒤 노이즈 일괄 제거됨. (엘리먼트 수: {len(sub_elements)} -> {q4_idx+1})")
                changed = True
    else:
        cleaned_elements.extend(sub_elements)
        
    # 2. 남아 있는 모든 <img> 태그들의 base64 크기 압축 수행
    final_elements = []
    for el in cleaned_elements:
        if "<img" in el:
            new_el = compress_base64_image(el)
            if len(new_el) != len(el):
                print(f"    -> [{key}] 이미지 압축 완료: 크기 {len(el)} -> {len(new_el)}")
                changed = True
            final_elements.append(new_el)
        else:
            final_elements.append(el)
            
    if changed:
        return "".join(final_elements), True
    return val, False

def main():
    print("=== [시작] 전과목 노이즈 소거 및 이미지 50% 최적화 작업 ===")
    
    db_files = [
        "se_db.js",
        "db_db.js",
        "pm_db.js",
        "sa_db.js",
        "sc_db.js"
    ]
    
    # 1. 5대 개별 과목 DB 가공 및 저장
    for db_file in db_files:
        db_path = os.path.join(BASE_DIR, "reports", "exam_db", db_file)
        if not os.path.exists(db_path):
            continue
            
        print(f"\n📂 [{db_file}] 정화 및 압축 시작...")
        db_dict = load_db_js(db_path)
        
        file_changed = False
        for key, val in db_dict.items():
            new_val, changed = sanitize_and_compress_question(key, val)
            if changed:
                db_dict[key] = new_val
                file_changed = True
                
        if file_changed:
            save_db_js(db_path, db_dict)
            print(f"✅ [{db_file}] 정화 완료 및 저장!")
            
    # 2. 공통 DB (exam_database.js) 가공 및 저장
    shared_path = SHARED_DB_JS_PATH
    if os.path.exists(shared_path):
        print(f"\n📂 [exam_database.js] 정화 및 압축 시작...")
        shared_db = load_db_js(shared_path)
        
        shared_changed = False
        for key, val in shared_db.items():
            new_val, changed = sanitize_and_compress_question(key, val)
            if changed:
                shared_db[key] = new_val
                shared_changed = True
                
        if shared_changed:
            save_db_js(shared_path, shared_db)
            print(f"✅ [exam_database.js] 정화 완료 및 저장!")

if __name__ == "__main__":
    main()
