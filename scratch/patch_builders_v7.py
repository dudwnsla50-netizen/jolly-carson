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

def patch_pm_testing_keywords(filename):
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"[ERROR] 파일 없음: {filename}")
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    modified = content
    
    # 2-c. 정보시스템 감리 관련 가이드의 키워드 리스트를 찾아서 확장
    target_str = '"발주관리가이드", "감리수행가이드", "유지보수 감리 점검가이드", "점검가이드", "윤리 가이드"'
    replacement = '"발주관리가이드", "감리수행가이드", "유지보수 감리 점검가이드", "점검가이드", "윤리 가이드", "지능정보기술 감리 실무 가이드", "감리 실무 가이드", "감리 실무가이드", "실무 가이드", "실무가이드", "감리 가이드", "감리가이드", "발주·관리 가이드", "수행 가이드", "수행가이드"'
    
    if target_str in modified:
        modified = modified.replace(target_str, replacement)
        
    if modified != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[SUCCESS] 감리 가이드 키워드 패치 완료: {filename}")
        return True
    else:
        print(f"[INFO] 변경 사항 없음: {filename}")
        return False

print("=== [시작] 10종 빌더 감리 가이드 키워드 일괄 패치 ===")
for builder in builders:
    patch_pm_testing_keywords(builder)
