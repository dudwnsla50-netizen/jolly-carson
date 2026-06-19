# -*- coding: utf-8 -*-
"""
[HTML 대시보드 내 정적 데이터 로더 태그 제거 패치]
- 작성자: Antigravity
- 목적: 10종 HTML 대시보드 파일들에서 이제 불필요해진 정적 데이터 스크립트 태그(exam_db 및 js/data)를 주석처리 혹은 제거합니다.
"""
import os
import re

BASE_DIR = r"e:\jolly-carson"
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

def clean_tags():
    html_files = [
        "db_frequent_concepts.html",
        "db_official_scopes.html",
        "pm_frequent_concepts.html",
        "pm_official_scopes.html",
        "sa_frequent_concepts.html",
        "sa_official_scopes.html",
        "sc_frequent_concepts.html",
        "sc_official_scopes.html",
        "se_frequent_concepts.html",
        "se_official_scopes.html"
    ]
    
    for filename in html_files:
        path = os.path.join(REPORTS_DIR, filename)
        if not os.path.exists(path):
            print(f"  -> {filename} 파일이 존재하지 않습니다. 스킵.")
            continue
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 1. <script src="exam_db/..._db.js..."></script> 제거 또는 주석
        # 2. <script src="js/data/....js..."></script> 제거 또는 주석
        
        modified_content = content
        
        # 정밀 정규식으로 스크립트 태그 탐색 및 제거
        pattern_db = r'^\s*<script src="exam_db/[a-z_]+\.js\?v=\d+"></script>\s*$'
        pattern_data = r'^\s*<!-- 외부 데이터 스크립트 동적 로드 -->\s*\n\s*<script src="js/data/[a-z_]+\.js\?v=\d+"></script>\s*$'
        
        # multiline 모드로 라인 매칭 처리
        modified_content = re.sub(pattern_db, '', modified_content, flags=re.MULTILINE)
        modified_content = re.sub(pattern_data, '', modified_content, flags=re.MULTILINE)
        
        # 주석되지 않고 태그가 남아있을 수 있는 일반 매칭 처리 (백업 방어)
        modified_content = re.sub(r'<script src="exam_db/.*_db\.js.*"></script>', '<!-- <script src="exam_db/..._db.js"></script> (DB 연동 대체됨) -->', modified_content)
        modified_content = re.sub(r'<script src="js/data/.*\.js.*"></script>', '<!-- <script src="js/data/...js"></script> (DB 연동 대체됨) -->', modified_content)
        
        # 중복된 주석라인 제거 정돈
        modified_content = re.sub(r'<!-- 외부 데이터 스크립트 동적 로드 -->\s*\n\s*<!-- <script src="js/data/\.\.\.js"></script>', '<!-- <script src="js/data/...js"></script>', modified_content)

        if modified_content != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(modified_content)
            print(f"[HTML 패치] {filename} 불필요 정적 태그 제거 성공")
        else:
            print(f"[HTML 패치] {filename} 수정 불필요 (이미 패치 완료)")

def main():
    print("[시작] 10종 HTML 대시보드 정적 태그 클리닝 작업...")
    clean_tags()
    print("[완료] 정적 태그 클리닝이 성공적으로 완료되었습니다.")

if __name__ == "__main__":
    main()
