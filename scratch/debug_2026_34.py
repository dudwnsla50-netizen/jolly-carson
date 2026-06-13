# -*- coding: utf-8 -*-
import re
import os
import sys

# 인코딩 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

db_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_db\se_db.js"
if os.path.exists(db_path):
    with open(db_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    match = re.search(r'"2026_49":\s*"(.*?)"(?=,\s*"|\s*\})', content, re.DOTALL)
    if match:
        print("--- 2026_49 Question Content ---")
        val = match.group(1).replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')
        print(val)
    else:
        print("2026_49 key not found in se_db.js")
else:
    print("se_db.js file not found")
