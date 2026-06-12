# -*- coding: utf-8 -*-
import os
import re

base_dir = r"d:\100.lyj\anti_workspace\jolly-carson"
js_path = os.path.join(base_dir, "reports", "exam_db", "se_db.js")

with open(js_path, "r", encoding="utf-8") as f:
    content = f.read()

# regex to find the key and its value
match = re.search(r'"2019_50"\s*:\s*"(.*?)"(?=,\s*"|\s*\})', content, re.DOTALL)
if match:
    print("Found 2019_50!")
    print(match.group(1))
else:
    print("Could not find 2019_50!")
