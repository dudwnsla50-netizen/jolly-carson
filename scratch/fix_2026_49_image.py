# -*- coding: utf-8 -*-
import os
import sys
import re
import json

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

def fix_2026_49(db_dict):
    key = "2026_49"
    if key in db_dict:
        val = db_dict[key]
        sub_elements = re.findall(r'(<p[^>]*>[\s\S]*?</p>|<img[^>]*>)', val)
        
        # Element 0부터 11까지만 취합니다. (보기 ④번 문항 텍스트 끝까지)
        if len(sub_elements) > 12:
            fixed_val = "".join(sub_elements[:12])
            db_dict[key] = fixed_val
            print(f"  -> {key} 문항 크기 축소 완료: {len(val)} -> {len(fixed_val)}")
            return True
        else:
            print(f"  -> {key} 문항의 하위 엘리먼트 수가 {len(sub_elements)}개로 이미 12개 이하입니다. 수정 패스.")
    return False

def main():
    print("=== [시작] 2026년 기출 49번 노이즈 이미지 제거 작업 ===")
    
    se_db = load_db_js(SE_DB_JS_PATH)
    shared_db = load_db_js(SHARED_DB_JS_PATH)
    
    changed1 = fix_2026_49(se_db)
    changed2 = fix_2026_49(shared_db)
    
    if changed1 or changed2:
        save_db_js(SE_DB_JS_PATH, se_db)
        save_db_js(SHARED_DB_JS_PATH, shared_db)
        print("✅ 데이터베이스 파일 저장 완료!")
        
        print("\n대시보드 10종 리빌드 작업을 실행합니다...")
        import subprocess
        rebuild_script = os.path.join(BASE_DIR, "rebuild_all_dashboards.py")
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = BASE_DIR
            result = subprocess.run(
                [sys.executable, rebuild_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                cwd=BASE_DIR,
                env=env
            )
            print(result.stdout)
            print("✅ 대시보드 리빌드 성공!")
        except Exception as e:
            print(f"❌ 대시보드 리빌드 에러: {e}")
    else:
        print("ℹ️ 변경할 데이터가 존재하지 않거나 이미 처리되었습니다.")

if __name__ == "__main__":
    main()
