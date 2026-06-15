# -*- coding: utf-8 -*-
"""
[대시보드 빌더 스크립트 일괄 마이그레이션 패치 스크립트]
- 목적: 10개 빌더 파이썬 스크립트의 하드코딩된 HTML 템플릿을 제거하고,
  build_utils.get_dashboard_html_template 공통 함수를 호출하도록 일괄 마이그레이션합니다.
"""

import os
import re

# 대상 빌더 파일 리스트
BUILDERS = [
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

BASE_DIR = r"e:\jolly-carson"

# 주입할 새로운 리턴 블록 코드
PATCH_CODE = '''    # ------------------[ 공통 템플릿 리팩토링 적용 ]------------------
    filename_lower = os.path.basename(__file__).lower()
    dashboard_type = "official" if "official" in filename_lower else "frequent"
    
    if "db" in filename_lower:
        subject_code, subject_name = "DB", "데이터베이스"
    elif "pm" in filename_lower:
        subject_code, subject_name = "PM", "프로젝트관리"
    elif "se" in filename_lower:
        subject_code, subject_name = "SE", "소프트웨어공학"
    elif "sa" in filename_lower:
        subject_code, subject_name = "SA", "시스템 아키텍처"
    elif "sc" in filename_lower:
        subject_code, subject_name = "SC", "보안"
    else:
        subject_code, subject_name = "UNKNOWN", "알수없음"

    filter_section_html = ""
    if dashboard_type == "official":
        categories = sorted(list(set(TOPIC_CATEGORIES.values())))
        filter_buttons = [f'<button class="filter-btn active" onclick="filterCategory(\\'all\\')">전체 대단원</button>']
        for cat in categories:
            filter_buttons.append(f'<button class="filter-btn" onclick="filterCategory(\\'{cat}\\')">{cat}</button>')
        filter_section_html = f'<div class="filter-section">{"".join(filter_buttons)}</div>'

    from build_utils import get_dashboard_html_template
    final_html = get_dashboard_html_template(
        dashboard_type=dashboard_type,
        subject_code=subject_code,
        subject_name=subject_name,
        mapping_json=mapping_json,
        filter_section_html=filter_section_html
    )
    return final_html'''

def patch_file(filepath):
    print(f"[PATCH] Target file: {os.path.basename(filepath)}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # html_template = """<!DOCTYPE html> 찾기
    start_match = re.search(r'html_template\s*=\s*"""<!DOCTYPE html>', content, re.IGNORECASE)
    if not start_match:
        print(f"[WARN] Cannot find start of HTML template: {os.path.basename(filepath)}")
        return False

    start_idx = start_match.start()

    # start_idx 이후로 첫 번째로 등장하는 return final_html (혹은 return 문)의 끝지점 찾기
    # 함수 정의가 끝나는 마지막 줄을 매칭하기 위해 return 문과 그 뒤의 변수명 매칭
    end_match = re.search(r'return\s+final_html[^\n]*', content[start_idx:])
    if not end_match:
        # 폴백: return 문 전체 찾기
        end_match = re.search(r'return\s+[a-zA-Z_0-9]+[^\n]*', content[start_idx:])
        if not end_match:
            print(f"[WARN] Cannot find return statement: {os.path.basename(filepath)}")
            return False

    end_idx = start_idx + end_match.end()

    # 치환 수행
    new_content = content[:start_idx] + PATCH_CODE + content[end_idx:]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print(f"[OK] Patched successfully: {os.path.basename(filepath)}")
    return True

def main():
    print("=== [START] Patching 10 builders for common modules ===")
    success_count = 0
    for builder in BUILDERS:
        filepath = os.path.join(BASE_DIR, builder)
        if os.path.exists(filepath):
            if patch_file(filepath):
                success_count += 1
        else:
            print(f"[ERROR] File does not exist: {builder}")

    print(f"\n=== [COMPLETE] {success_count} / {len(BUILDERS)} successfully patched ===")

if __name__ == "__main__":
    main()
