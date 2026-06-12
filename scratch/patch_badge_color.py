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

# 치환 대상 1: .badge 스타일 정의 부분에 color: var(--text-secondary); 추가
target_badge = """        .badge {
            background: var(--border-color);
            border: 1px solid rgba(255, 255, 255, 0.04);
            padding: 0.35rem 0.9rem;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 500;
            backdrop-filter: blur(8px);
        }"""

replacement_badge = """        .badge {
            background: var(--border-color);
            border: 1px solid rgba(255, 255, 255, 0.04);
            color: var(--text-secondary);
            padding: 0.35rem 0.9rem;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 500;
            backdrop-filter: blur(8px);
        }"""

# 치환 대상 2: a.badge 스타일 정의 부분에 color 지정 추가
target_a_badge = """        a.badge {
            transition: all 0.2s ease;
        }"""

replacement_a_badge = """        a.badge {
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.2s ease;
        }"""

print("=== [시작] 10종 빌더 비활성화 뱃지 가독성 색상 패치 ===")

for builder in builders:
    path = os.path.join(base_dir, builder)
    if not os.path.exists(path):
        print(f"[ERROR] 파일 없음: {builder}")
        continue
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    modified = content
    
    # .badge 치환
    if target_badge in modified:
        modified = modified.replace(target_badge, replacement_badge)
    else:
        normalized_content = content.replace("\r\n", "\n")
        n_target = target_badge.replace("\r\n", "\n")
        n_replacement = replacement_badge.replace("\r\n", "\n")
        if n_target in normalized_content:
            normalized_content = normalized_content.replace(n_target, n_replacement)
            modified = normalized_content
            
    # a.badge 치환
    if target_a_badge in modified:
        modified = modified.replace(target_a_badge, replacement_a_badge)
    else:
        normalized_content = modified.replace("\r\n", "\n")
        n_target = target_a_badge.replace("\r\n", "\n")
        n_replacement = replacement_a_badge.replace("\r\n", "\n")
        if n_target in normalized_content:
            normalized_content = normalized_content.replace(n_target, n_replacement)
            modified = normalized_content
            
    if modified != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[SUCCESS] {builder}: 뱃지 색상 패치 완료")
    else:
        print(f"[INFO] {builder}: 변경사항 없음")

print("=== [완료] 패치 완료 ===")
