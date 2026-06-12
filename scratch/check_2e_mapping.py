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
    found_2e = False
    for item in mapping:
        if "2-e." in item["concept"]:
            found_2e = True
            print("Found 2-e:", item["concept"])
            print("Mapped questions count:", len(item["questions"]))
            # 2019년 50번이 있는지 검사
            has_2019_50 = any(q["year"] == 2019 and q["num"] == 50 for q in item["questions"])
            print("Has 2019_50 mapped to 2-e?", has_2019_50)
    if not found_2e:
        print("Could not find 2-e in mapping!")
else:
    print("Could not find topicMapping in file!")
