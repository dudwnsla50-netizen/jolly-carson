# -*- coding: utf-8 -*-
import os

base_dir = r"d:\100.lyj\anti_workspace\jolly-carson"

builders = [
    "build_premium_se_viewer.py",
    "build_premium_se_official_viewer.py"
]

def fix_se_image_margin(filename):
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"[오류] 파일 없음: {filename}")
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    target = "margin: 0.8rem auto !important;"
    replacement = "margin: 0.8rem 0 !important;"
    
    if target in content:
        modified = content.replace(target, replacement)
        with open(path, "w", encoding="utf-8") as f:
            f.write(modified)
        print(f"[성공] 원본 이미지 마진 좌측 정렬로 패치 완료: {filename}")
        return True
    else:
        print(f"[정보] 타겟 패턴 없음: {filename}")
        return False

print("=== [시작] SE 빌더 원본 이미지 마진 일괄 패치 ===")
for builder in builders:
    fix_se_image_margin(builder)
