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

target_sa = """        elif subject_code == "SA":
            if year == 2015:
                q_start, q_end = 76, 90
            else:
                q_start, q_end = 76, 100"""

replacement_sa = """        elif subject_code == "SA":
            q_start, q_end = 76, 100"""

target_sc = """        elif subject_code == "SC":
            if year == 2015:
                q_start, q_end = 91, 105
            else:
                q_start, q_end = 101, 120"""

replacement_sc = """        elif subject_code == "SC":
            q_start, q_end = 101, 120"""

print("=== [시작] 10종 빌더 2015년 SA/SC 문항 범위 패치 ===")

for builder in builders:
    path = os.path.join(base_dir, builder)
    if not os.path.exists(path):
        print(f"[ERROR] 파일 없음: {builder}")
        continue
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    modified = content
    
    # SA 치환
    if target_sa in modified:
        modified = modified.replace(target_sa, replacement_sa)
        print(f"  - {builder}: SA 범위 분기 치환 완료")
    else:
        # 혹시 개행 문자 포맷이 다를 수 있으므로 정규화 처리 후 시도
        normalized_content = content.replace("\r\n", "\n")
        normalized_target_sa = target_sa.replace("\r\n", "\n")
        normalized_replacement_sa = replacement_sa.replace("\r\n", "\n")
        if normalized_target_sa in normalized_content:
            normalized_content = normalized_content.replace(normalized_target_sa, normalized_replacement_sa)
            modified = normalized_content
            print(f"  - {builder}: SA 범위 분기 치환 완료 (개행 정규화 적용)")
        else:
            print(f"  - {builder}: SA 범위 치환 대상 찾지 못함")
            
    # SC 치환
    if target_sc in modified:
        modified = modified.replace(target_sc, replacement_sc)
        print(f"  - {builder}: SC 범위 분기 치환 완료")
    else:
        # 개행 정규화 후 시도
        normalized_content = modified.replace("\r\n", "\n")
        normalized_target_sc = target_sc.replace("\r\n", "\n")
        normalized_replacement_sc = replacement_sc.replace("\r\n", "\n")
        if normalized_target_sc in normalized_content:
            normalized_content = normalized_content.replace(normalized_target_sc, normalized_replacement_sc)
            modified = normalized_content
            print(f"  - {builder}: SC 범위 분기 치환 완료 (개행 정규화 적용)")
        else:
            print(f"  - {builder}: SC 범위 치환 대상 찾지 못함")
            
    if modified != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[SUCCESS] {builder} 파일 쓰기 완료")
    else:
        print(f"[INFO] 변경 사항 없음: {builder}")

print("=== [완료] 패치 완료 ===")
