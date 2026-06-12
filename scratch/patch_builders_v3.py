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

def patch_js_navigation(filename):
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"[ERROR] 파일 없음: {filename}")
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # toggleDashboardMode 내의 badge.href 변경 부분
    # badge.href = target; -> badge.href = target + '?v=20260613';
    # badge.href = '/reports/' + target; -> badge.href = '/reports/' + target + '?v=20260613';
    
    modified = content
    
    # regex로 badge.href 변경 부분 매칭 및 치환
    # Local 분기 및 Server 분기 둘 다 처리
    modified = re.sub(
        r"badge\.href\s*=\s*target\s*;",
        r"badge.href = target + '?v=20260613';",
        modified
    )
    
    modified = re.sub(
        r"badge\.href\s*=\s*'/reports/'\s*\+\s*target\s*;",
        r"badge.href = '/reports/' + target + '?v=20260613';",
        modified
    )
    
    # 3. 리다이렉션 경로에도 캐시 버스터 추가 (?v=20260613)
    # window.location.href = targetRedirect; -> window.location.href = targetRedirect + '?v=20260613';
    # window.location.href = '/reports/' + targetRedirect; -> window.location.href = '/reports/' + targetRedirect + '?v=20260613';
    modified = re.sub(
        r"window\.location\.href\s*=\s*targetRedirect\s*;",
        r"window.location.href = targetRedirect + '?v=20260613';",
        modified
    )
    
    modified = re.sub(
        r"window\.location\.href\s*=\s*'/reports/'\s*\+\s*targetRedirect\s*;",
        r"window.location.href = '/reports/' + targetRedirect + '?v=20260613';",
        modified
    )
    
    # 4. initDashboardNav 내의 badge.href 변경 부분
    # badge.href = target; -> badge.href = target + '?v=20260613';
    # badge.href = '/reports/' + target; -> badge.href = '/reports/' + target + '?v=20260613';
    # (이미 위에서 치환을 통해 완료되었을 수 있으나 명확하게 다시 정의)
    
    if modified != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[SUCCESS] JS 내비게이션 캐시 버스터 패치 완료: {filename}")
        return True
    else:
        print(f"[INFO] 변경 사항 없음: {filename}")
        return False

print("=== [시작] 10종 빌더 JS 내비게이션 캐시 버스터 일괄 주입 ===")
for builder in builders:
    patch_js_navigation(builder)
