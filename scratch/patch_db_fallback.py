# -*- coding: utf-8 -*-
import os

base_dir = r"d:\100.lyj\anti_workspace\jolly-carson"

builders = [
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

target_code = """def load_exam_database_dict(subject_code):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    js_path = os.path.join(base_dir, "reports", "exam_db", f"{subject_code.lower()}_db.js")
        
    if not os.path.exists(js_path):
        return {}"""

replacement_code = """def load_exam_database_dict(subject_code):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    js_path = os.path.join(base_dir, "reports", "exam_db", f"{subject_code.lower()}_db.js")
    
    # 폴백: 개별 DB가 아직 없는 경우 공통 DB 참조
    if not os.path.exists(js_path):
        js_path = os.path.join(base_dir, "reports", "exam_database.js")
        
    if not os.path.exists(js_path):
        return {}"""

print("=== [시작] 10종 빌더 DB 로딩 폴백 패치 ===")

for builder in builders:
    path = os.path.join(base_dir, builder)
    if not os.path.exists(path):
        print(f"[ERROR] 파일 없음: {builder}")
        continue
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    modified = content
    
    if target_code in modified:
        modified = modified.replace(target_code, replacement_code)
        print(f"  - {builder}: 폴백 로직 치환 완료")
    else:
        # 개행 정규화 후 시도
        normalized_content = content.replace("\r\n", "\n")
        normalized_target = target_code.replace("\r\n", "\n")
        normalized_replacement = replacement_code.replace("\r\n", "\n")
        if normalized_target in normalized_content:
            normalized_content = normalized_content.replace(normalized_target, normalized_replacement)
            modified = normalized_content
            print(f"  - {builder}: 폴백 로직 치환 완료 (개행 정규화 적용)")
        else:
            print(f"  - {builder}: 폴백 로직 치환 대상 찾지 못함")
            
    if modified != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[SUCCESS] {builder} 파일 쓰기 완료")
    else:
        print(f"[INFO] 변경 사항 없음: {builder}")

print("=== [완료] 패치 완료 ===")
