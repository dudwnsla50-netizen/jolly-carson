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

def patch_file(filename):
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"[ERROR] 파일 없음: {filename}")
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 1. load_exam_database_dict 함수 내 폴백 부분 제거
    # 변경 전 대상 탐색
    fallback_pattern = re.compile(
        r"js_path\s*=\s*os\.path\.join\(base_dir,\s*\"reports\",\s*\"exam_db\",\s*f\"\{subject_code\.lower\(\)\}_db\.js\"\)\s*\n\s*#\s*폴백:\s*개별\s*DB가\s*아직\s*없는\s*경우\s*공통\s*DB\s*참조\s*\n\s*if\s*not\s*os\.path\.exists\(js_path\):\s*\n\s*js_path\s*=\s*os\.path\.join\(base_dir,\s*\"reports\",\s*\"exam_database\.js\"\)"
    )
    
    # 더 단순한 형태의 폴백 매칭 시도
    simple_fallback_pattern = re.compile(
        r"if\s*not\s*os\.path\.exists\(js_path\):\s*\n\s*js_path\s*=\s*os\.path\.join\(base_dir,\s*\"reports\",\s*\"exam_database\.js\"\)"
    )
    
    modified = content
    
    if fallback_pattern.search(modified):
        modified = fallback_pattern.sub(
            'js_path = os.path.join(base_dir, "reports", "exam_db", f"{subject_code.lower()}_db.js")',
            modified
        )
    elif simple_fallback_pattern.search(modified):
        modified = simple_fallback_pattern.sub(
            '# 폴백 제거됨',
            modified
        )
        
    # 2. HTML 템플릿의 스크립트 참조를 캐시 버스터 적용 버전으로 변경
    # <script src="exam_db/db_db.js"></script> -> <script src="exam_db/db_db.js?v=20260613"></script>
    script_pattern = re.compile(r'<script\s+src="exam_db/([a-z]+)_db\.js"></script>')
    modified = script_pattern.sub(r'<script src="exam_db/\1_db.js?v=20260613"></script>', modified)
    
    if modified != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[SUCCESS] 패치 완료: {filename}")
        return True
    else:
        print(f"[INFO] 변경 사항 없음 또는 이미 패치됨: {filename}")
        return False

print("=== [시작] 10종 빌더 스크립트 일괄 정밀 패치 ===")
for builder in builders:
    patch_file(builder)
