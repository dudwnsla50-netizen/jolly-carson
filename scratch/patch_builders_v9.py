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

old_patch_indicator = "/* [일괄 레이아웃 패치: 스크롤바 제거 및 이미지 50% 축소] */"
new_patch_indicator = "/* [일괄 레이아웃 패치: 스크롤바 제거, 이미지 50% 축소 및 좌측 정렬] */"

new_patch_css = """
        /* [일괄 레이아웃 패치: 스크롤바 제거, 이미지 50% 축소 및 좌측 정렬] */
        .viewer-body {
            max-height: none !important;
            overflow-y: visible !important;
        }
        .viewer-body img, .viewer-img-container img, .question-img {
            max-width: 50% !important;
            height: auto !important;
            margin: 0.8rem 0 !important; /* 가운데 정렬(auto)에서 좌측 정렬(0)로 변경 */
            display: block !important;
        }
        @media (max-width: 768px) {
            .viewer-body {
                max-height: none !important;
                overflow-y: visible !important;
            }
            .viewer-body img, .viewer-img-container img, .question-img {
                max-width: 50% !important;
                height: auto !important;
                margin: 0.8rem 0 !important;
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
        
    # 이미 새 패치가 적용되어 있는 경우 스킵
    if new_patch_indicator in content:
        print(f"[정보] 이미 새 패치가 적용됨: {filename}")
        return False
        
    # 기존에 v8 패치가 들어있는 경우 정규식으로 감지하여 교체
    if old_patch_indicator in content:
        # 기존 v8 패치 영역을 정밀하게 추출해서 교체하기 위해 정규식 패턴 설계
        # v8 주석부터 시작해서 다음 </style> 또는 괄호 닫는 부분까지 매칭
        pattern = r"\s*/\* \[일괄 레이아웃 패치: 스크롤바 제거 및 이미지 50% 축소\] \*/[\s\S]*?(?=\n\s*</style>)"
        modified = re.sub(pattern, new_patch_css, content)
        
        # 만약 정규식 교체로 내용이 바뀌었다면 저장
        if modified != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(modified)
            print(f"[성공] v8 -> v9 교체 완료: {filename}")
            return True
            
    # 기존 패치를 못 찾았거나 다른 형태로 되어 있을 경우 </style> 직전에 신규 삽입
    match = re.search(r'(?i)</style>', content)
    if match:
        tag = match.group(0)
        modified = content.replace(tag, new_patch_css + "\n    " + tag)
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[성공] 신규 v9 패치 완료: {filename}")
        return True
    else:
        print(f"[경고] </style> 태그를 찾지 못함: {filename}")
        return False

print("=== [시작] 10종 빌더 CSS 일괄 v9 패치 (이미지 좌측 정렬 추가) ===")
for builder in builders:
    patch_builder(builder)
