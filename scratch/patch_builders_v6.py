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

def patch_testing_keywords(filename):
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"[ERROR] 파일 없음: {filename}")
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    modified = content
    
    # 2-e. 테스팅 방법 및 도구의 키워드 리스트를 찾아서 확장
    target_str = '"구문 검증", "분기 검증", "조건 검증", "결정 검증", "경로 검증"'
    replacement = '"구문 검증", "분기 검증", "조건 검증", "결정 검증", "경로 검증", "문장 커버리지", "분기 커버리지", "조건 커버리지", "결정 커버리지", "경로 커버리지", "커버리지", "coverage", "test case", "테스트 케이스", "테스트케이스"'
    
    if target_str in modified:
        modified = modified.replace(target_str, replacement)
        
    if modified != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[SUCCESS] 테스팅 키워드 패치 완료: {filename}")
        return True
    else:
        print(f"[INFO] 변경 사항 없음: {filename}")
        return False

print("=== [시작] 10종 빌더 테스팅 키워드 일괄 패치 ===")
for builder in builders:
    patch_testing_keywords(builder)
