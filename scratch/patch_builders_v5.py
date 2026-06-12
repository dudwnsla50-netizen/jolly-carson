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

def patch_user_select_styles(filename):
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"[ERROR] 파일 없음: {filename}")
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    modified = content
    
    # 1. concept-title 스타일 치환
    if ".concept-title {" in modified and "user-select: text" not in modified:
        modified = modified.replace(
            ".concept-title {",
            ".concept-title {\n            user-select: text !important;\n            -webkit-user-select: text !important;"
        )
        
    # 2. rank-badge 스타일 치환
    if ".rank-badge {" in modified and "user-select: text" not in modified:
        modified = modified.replace(
            ".rank-badge {",
            ".rank-badge {\n            user-select: text !important;\n            -webkit-user-select: text !important;"
        )
        
    # 3. meta-value 스타일 치환
    if ".meta-value {" in modified and "user-select: text" not in modified:
        modified = modified.replace(
            ".meta-value {",
            ".meta-value {\n            user-select: text !important;\n            -webkit-user-select: text !important;"
        )
        
    # 4. accordion-trigger 자체도 선택 가능하게 추가 (단추 내부 텍스트 선택 지원)
    if ".accordion-trigger {" in modified and "user-select: text" not in modified:
        modified = modified.replace(
            ".accordion-trigger {",
            ".accordion-trigger {\n            user-select: text !important;\n            -webkit-user-select: text !important;"
        )

    if modified != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[SUCCESS] user-select 스타일 패치 완료: {filename}")
        return True
    else:
        print(f"[INFO] 변경 사항 없음 (이미 적용되었거나 클래스명이 없음): {filename}")
        return False

print("=== [시작] 10종 빌더 텍스트 선택(user-select) 스타일 일괄 패치 ===")
for builder in builders:
    patch_user_select_styles(builder)
