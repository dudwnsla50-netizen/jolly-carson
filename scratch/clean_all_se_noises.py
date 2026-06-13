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
    
    # 1. 보기 ④번의 인덱스 찾기
    q4_idx = -1
    for idx, el in enumerate(sub_elements):
        if "<p" in el:
            txt = re.sub(r'<[^>]*>', '', el).strip()
            if "④" in txt:
                q4_idx = idx
                
    changed = False
    cleaned_elements = []
    
    if q4_idx != -1:
        # 보기 ④번 인덱스 전까지는 그대로 누적
        cleaned_elements.extend(sub_elements[:q4_idx+1])
        
        # 보기 ④번 이후 노이즈 필터링
        post_elements = sub_elements[q4_idx+1:]
        total_imgs = sum(1 for el in sub_elements if "<img" in el)
        
        for el in post_elements:
            if "<img" in el:
                # 전체 이미지 수가 4개 미만인 경우(선택지 이미지형 문제가 아닌 경우) ④번 뒤 이미지는 타 문항 노이즈
                if total_imgs < 4:
                    print(f"    -> [{key}] ④번 뒤 노이즈 이미지 제거됨.")
                    changed = True
                    continue
                else:
                    cleaned_elements.append(el)
            elif "<p" in el:
                # 페이지 지시선 번호(- 11 - 등) 제거
                txt = re.sub(r'<[^>]*>', '', el).strip()
                if re.match(r'^\s*-\s*\d+\s*-\s*$', txt):
                    print(f"    -> [{key}] 페이지 번호 단락 제거됨: '{txt}'")
                    changed = True
                    continue
                else:
                    cleaned_elements.append(el)
            else:
                cleaned_elements.append(el)
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
    print("=== [시작] 노이즈 소거 및 이미지 50% 최적화 작업 ===")
    
    se_db = load_db_js(SE_DB_JS_PATH)
    shared_db = load_db_js(SHARED_DB_JS_PATH)
    
    total_changed = 0
    
    # SE DB 가공
    print("\n[1/2] se_db.js 정화 및 압축 시작...")
    for key, val in se_db.items():
        new_val, changed = sanitize_and_compress_question(key, val)
        if changed:
            se_db[key] = new_val
            total_changed += 1
            
    # Shared DB 가공 (SE 과목 범위인 26~50번만)
    print("\n[2/2] exam_database.js 정화 및 압축 시작...")
    for key, val in shared_db.items():
        # SE 과목 범위인지 확인 (예: 2015_26 ~ 2026_50)
        match = re.match(r'^(\d{4})_(\d+)$', key)
        if match:
            num = int(match.group(2))
            if 26 <= num <= 50:
                new_val, changed = sanitize_and_compress_question(key, val)
                if changed:
                    shared_db[key] = new_val
                    
    if total_changed > 0:
        save_db_js(SE_DB_JS_PATH, se_db)
        save_db_js(SHARED_DB_JS_PATH, shared_db)
        print(f"\n✅ 데이터베이스 정화 및 압축 저장 완료! (총 {total_changed}개 문항 변경)")
    else:
        print("\nℹ️ 변경할 데이터가 없거나 이미 정화 및 압축이 적용되어 있습니다.")

if __name__ == "__main__":
    main()
