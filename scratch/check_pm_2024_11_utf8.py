# -*- coding: utf-8 -*-
import os
import re
import sys

# 출력 인코딩 강제 설정
sys.stdout.reconfigure(encoding='utf-8')

base_dir = r"d:\100.lyj\anti_workspace\jolly-carson"
js_path = os.path.join(base_dir, "reports", "exam_db", "pm_db.js")

with open(js_path, "r", encoding="utf-8") as f:
    content = f.read()

# JSON 파싱 시도
match = re.search(r"const\s+examDatabase\s*=\s*(\{[\s\S]*\});", content)
if match:
    js_obj_str = match.group(1)
    import json
    data = json.loads(js_obj_str)
    q_text = data.get("2024_11", "Not found")
    print("Found 2024_11:")
    print(q_text)
else:
    print("Could not find examDatabase pattern!")
