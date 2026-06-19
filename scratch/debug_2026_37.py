# -*- coding: utf-8 -*-
import sys
import json
import re

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

db_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_db\se_db.js"
with open(db_path, "r", encoding="utf-8") as f:
    content = f.read()

match = re.search(r"const\s+examDatabase\s*=\s*(\{[\s\S]*\});", content)
if match:
    raw_dict = match.group(1)
    key_match = re.search(r'"2026_37":\s*"([\s\S]*?)"(?=,\s*"|\s*\})', raw_dict)
    if key_match:
        val = key_match.group(1)
        print("=== 2026_37 Content ===")
        print(val[:2000])
        print("=======================")
    else:
        print("Key '2026_37' not found.")
else:
    print("examDatabase not found.")
