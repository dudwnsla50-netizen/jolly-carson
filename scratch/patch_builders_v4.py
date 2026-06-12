# -*- coding: utf-8 -*-
import os
import re

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

def patch_word_boundary_matching(filename):
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"[ERROR] 파일 없음: {filename}")
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 단순 문자열 치환으로 변경하여 특수문자 및 백슬래시 매칭 오류 방지
    target_str1 = 'pattern = rf"\\\\b{re.escape(kw.lower())}\\\\b"'
    target_str2 = "pattern = rf'\\\\b{re.escape(kw.lower())}\\\\b'"
    replacement = 'pattern = rf"(?<![a-zA-Z0-9]){re.escape(kw.lower())}(?![a-zA-Z0-9])"'
    
    modified = content
    if target_str1 in modified:
        modified = modified.replace(target_str1, replacement)
    if target_str2 in modified:
        modified = modified.replace(target_str2, replacement)
        
    if modified != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[SUCCESS] 정규식 매칭 패치 완료: {filename}")
        return True
    else:
        print(f"[INFO] 변경 사항 없음: {filename}")
        return False

print("=== [시작] 10종 빌더 단어 경계 정규식 일괄 패치 ===")
for builder in builders:
    patch_word_boundary_matching(builder)
