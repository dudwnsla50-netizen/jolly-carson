# -*- coding: utf-8 -*-
import os
import re

base_dir = r"d:\100.lyj\anti_workspace\jolly-carson"
js_path = os.path.join(base_dir, "reports", "exam_db", "se_db.js")

with open(js_path, "r", encoding="utf-8") as f:
    content = f.read()

# regex to find the key and its value
# 예: "2024_39": "..."
match = re.search(r'"2024_39"\s*:\s*"(.*?)"(?=,\s*"|\s*\})', content, re.DOTALL)
if match:
    print("Found 2024_39!")
    print(match.group(1))
else:
    print("Could not find 2024_39 with regex!")
    # 파일 내에 "2024_39" 문자열이 존재하는지 단순 검색
    if "2024_39" in content:
        print("Simple search: '2024_39' string IS in the file!")
        # 주변 텍스트 출력
        pos = content.find("2024_39")
        print("Surrounding text:")
        print(content[pos-50:pos+300])
    else:
        print("Simple search: '2024_39' string is NOT in the file!")
        # 키 목록들 몇 개 출력
        keys = re.findall(r'"(\d{4}_\d+)":', content)
        print(f"Total keys found: {len(keys)}")
        print(f"Sample keys: {keys[:20]}")
        print("Is 2024_39 in keys?", "2024_39" in keys)
