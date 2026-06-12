# -*- coding: utf-8 -*-
import os
import re
import json

base_dir = r"d:\100.lyj\anti_workspace\jolly-carson"
path = os.path.join(base_dir, "reports", "pm_official_scopes.html")

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# topicMapping 추출
match = re.search(r"const\s+topicMapping\s*=\s*(\[[\s\S]*?\]);", content)
if match:
    mapping = json.loads(match.group(1))
    found_2c = False
    for item in mapping:
        if "2-c." in item["concept"]:
            found_2c = True
            print("Found 2-c:", item["concept"])
            print("Mapped questions count:", len(item["questions"]))
            # 2024년 11번이 있는지 검사
            has_2024_11 = any(q["year"] == 2024 and q["num"] == 11 for q in item["questions"])
            print("Has 2024_11 mapped to 2-c?", has_2024_11)
            for q in item["questions"]:
                print(f"  {q['year']}년 {q['num']}번")
    if not found_2c:
        print("Could not find 2-c in mapping!")
else:
    print("Could not find topicMapping in file!")
