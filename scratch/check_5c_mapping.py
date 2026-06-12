# -*- coding: utf-8 -*-
import os
import re
import json

base_dir = r"d:\100.lyj\anti_workspace\jolly-carson"
path = os.path.join(base_dir, "reports", "se_official_scopes.html")

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# topicMapping 추출
match = re.search(r"const\s+topicMapping\s*=\s*(\[[\s\S]*?\]);", content)
if match:
    mapping = json.loads(match.group(1))
    # 5-c 찾기
    found_5c = False
    for item in mapping:
        if "5-c." in item["concept"]:
            found_5c = True
            print("Found 5-c:", item["concept"])
            print("Mapped questions:")
            for q in item["questions"]:
                print(f"  {q['year']}년 {q['num']}번")
            # 2024년 39번이 있는지 검사
            has_2024_39 = any(q["year"] == 2024 and q["num"] == 39 for q in item["questions"])
            print("Has 2024_39 mapped to 5-c?", has_2024_39)
    if not found_5c:
        print("Could not find 5-c in mapping!")
else:
    print("Could not find topicMapping in file!")
