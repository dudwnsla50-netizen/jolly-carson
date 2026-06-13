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

patch_css = """
        /* [일괄 레이아웃 패치: 스크롤바 제거 및 이미지 50% 축소] */
        .viewer-body {
            max-height: none !important;
            overflow-y: visible !important;
        }
        .viewer-img-container img, .question-img {
            max-width: 50% !important;
            height: auto !important;
            display: block !important;
        }
        @media (max-width: 768px) {
            .viewer-body {
                max-height: none !important;
                overflow-y: visible !important;
            }
            .viewer-img-container img, .question-img {
                max-width: 50% !important;
                height: auto !important;
            }
        }
"""

def patch_builder(filename):
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"[오류] 파일 없음: {filename}")
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 중복 삽입 방지
    if "/* [일괄 레이아웃 패치: 스크롤바 제거 및 이미지 50% 축소] */" in content:
        print(f"[정보] 이미 패치됨: {filename}")
        return False
        
    # 대소문자 무관하게 </style> 태그 매칭
    import re
    match = re.search(r'(?i)</style>', content)
    if match:
        tag = match.group(0)
        modified = content.replace(tag, patch_css + "\n    " + tag)
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[성공] 패치 완료: {filename}")
        return True
    else:
        print(f"[경고] </style> 태그를 찾지 못함: {filename}")
        return False

print("=== [시작] 10종 빌더 CSS 일괄 패치 (스크롤바 제거 및 이미지 50% 축소) ===")
for builder in builders:
    patch_builder(builder)
