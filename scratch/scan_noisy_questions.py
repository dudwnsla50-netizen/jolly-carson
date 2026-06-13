# -*- coding: utf-8 -*-
import os
import sys
import re
import json

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

db_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_db\se_db.js"

with open(db_path, "r", encoding="utf-8") as f:
    content = f.read()

match = re.search(r"const\s+examDatabase\s*=\s*(\{[\s\S]*\});", content)
if not match:
    print("Database not found")
    sys.exit(1)

db = json.loads(match.group(1))

print("=== [시작] 보기 ④번 뒤 노이즈 엘리먼트(이미지/페이지번호) 스캔 ===")

candidates = []

for key, val in db.items():
    if not isinstance(val, str) or "<p" not in val:
        continue
        
    sub_elements = re.findall(r'(<p[^>]*>[\s\S]*?</p>|<img[^>]*>)', val)
    
    # 보기 ④번의 인덱스 찾기
    q4_idx = -1
    for idx, el in enumerate(sub_elements):
        if "<p" in el:
            txt = re.sub(r'<[^>]*>', '', el).strip()
            if "④" in txt:
                q4_idx = idx
                
    if q4_idx != -1:
        # 보기 ④번 뒤에 존재하는 엘리먼트들 분석
        post_elements = sub_elements[q4_idx+1:]
        has_noise_img = any("<img" in el for el in post_elements)
        has_page_num = any(re.match(r'^\s*-\s*\d+\s*-\s*$', re.sub(r'<[^>]*>', '', el).strip()) for el in post_elements if "<p" in el)
        
        # 만약 전체 이미지 수가 4개 미만인데 ④번 뒤에 이미지가 있거나, 페이지 번호가 붙은 경우
        total_imgs = sum(1 for el in sub_elements if "<img" in el)
        
        if (has_noise_img and total_imgs < 4) or has_page_num:
            candidates.append({
                "key": key,
                "total_elements": len(sub_elements),
                "q4_index": q4_idx,
                "total_images": total_imgs,
                "has_noise_img": has_noise_img,
                "has_page_num": has_page_num,
                "post_elements_count": len(post_elements)
            })

print(f"검출된 노이즈 후보 문항 수: {len(candidates)}")
for c in candidates:
    print(f"  👉 Key: {c['key']} | 총 이미지: {c['total_images']}개 | ④번 뒤 이미지 여부: {c['has_noise_img']} | 페이지번호 여부: {c['has_page_num']} | ④번 뒤 엘리먼트 수: {c['post_elements_count']}개")
