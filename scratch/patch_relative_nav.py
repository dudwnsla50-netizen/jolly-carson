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

# 치환 대상 1: switchDashboardMode 내 badge.href 설정
target1 = """        badges.forEach(badge => {
            const target = isOfficial ? badge.getAttribute('data-official') : badge.getAttribute('data-freq');
            if (isLocal) {
                badge.href = target + '?v=20260613';
            } else {
                badge.href = '/reports/' + target + '?v=20260613';
            }
        });"""

replacement1 = """        badges.forEach(badge => {
            const target = isOfficial ? badge.getAttribute('data-official') : badge.getAttribute('data-freq');
            badge.href = target + '?v=20260613';
        });"""

# 치환 대상 2: switchDashboardMode 내 redirect 설정
target2 = """        if (targetRedirect) {
            if (isLocal) {
                window.location.href = targetRedirect + '?v=20260613';
            } else {
                window.location.href = '/reports/' + targetRedirect + '?v=20260613';
            }
        }"""

replacement2 = """        if (targetRedirect) {
            window.location.href = targetRedirect + '?v=20260613';
        }"""

# 치환 대상 3: initDashboardNav 내 badge.href 설정
target3 = """        badges.forEach(badge => {
            const target = isOfficialPage ? badge.getAttribute('data-official') : badge.getAttribute('data-freq');
            if (isLocal) {
                badge.href = target + '?v=20260613';
            } else {
                badge.href = '/reports/' + target + '?v=20260613';
            }"""

replacement3 = """        badges.forEach(badge => {
            const target = isOfficialPage ? badge.getAttribute('data-official') : badge.getAttribute('data-freq');
            badge.href = target + '?v=20260613';"""


print("=== [시작] 10종 빌더 상대경로 네비게이션 패치 ===")

for builder in builders:
    path = os.path.join(base_dir, builder)
    if not os.path.exists(path):
        print(f"[ERROR] 파일 없음: {builder}")
        continue
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    modified = content
    
    # Target 1 치환
    if target1 in modified:
        modified = modified.replace(target1, replacement1)
    else:
        normalized_content = content.replace("\r\n", "\n")
        n_target1 = target1.replace("\r\n", "\n")
        n_replacement1 = replacement1.replace("\r\n", "\n")
        if n_target1 in normalized_content:
            normalized_content = normalized_content.replace(n_target1, n_replacement1)
            modified = normalized_content
            
    # Target 2 치환
    if target2 in modified:
        modified = modified.replace(target2, replacement2)
    else:
        normalized_content = modified.replace("\r\n", "\n")
        n_target2 = target2.replace("\r\n", "\n")
        n_replacement2 = replacement2.replace("\r\n", "\n")
        if n_target2 in normalized_content:
            normalized_content = normalized_content.replace(n_target2, n_replacement2)
            modified = normalized_content
            
    # Target 3 치환
    if target3 in modified:
        modified = modified.replace(target3, replacement3)
    else:
        normalized_content = modified.replace("\r\n", "\n")
        n_target3 = target3.replace("\r\n", "\n")
        n_replacement3 = replacement3.replace("\r\n", "\n")
        if n_target3 in normalized_content:
            normalized_content = normalized_content.replace(n_target3, n_replacement3)
            modified = normalized_content
            
    if modified != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[SUCCESS] {builder}: 상대경로 패치 완료")
    else:
        print(f"[INFO] {builder}: 변경사항 없음")

print("=== [완료] 패치 완료 ===")
