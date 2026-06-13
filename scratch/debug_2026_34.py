# -*- coding: utf-8 -*-
import re
import os

db_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_db\se_db.js"
if os.path.exists(db_path):
    with open(db_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 2026_34 부분을 찾기 위한 정규식
    match = re.search(r'"2026_34":\s*"(.*?)"(?=,\s*"|\s*\})', content, re.DOTALL)
    if match:
        print("--- 2026_34 Question Content (First 1500 chars) ---")
        val = match.group(1).replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')
        print(val[:1500])
    else:
        print("2026_34 key not found in se_db.js")
else:
    print("se_db.js file not found")
