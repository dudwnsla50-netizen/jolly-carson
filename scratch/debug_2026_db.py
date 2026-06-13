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
if match:
    db = json.loads(match.group(1))
    val_49 = db.get("2026_49", "NOT_FOUND")
    print("--- 2026_49 Detailed Content ---")
    
    # p 태그와 img 태그 순서대로 분리해서 출력
    sub_elements = re.findall(r'(<p[^>]*>[\s\S]*?</p>|<img[^>]*>)', val_49)
    for idx, el in enumerate(sub_elements):
        if "<p" in el:
            txt = re.sub(r'<[^>]*>', '', el).strip()
            print(f"Element {idx} [TEXT]: {txt}")
        elif "<img" in el:
            print(f"Element {idx} [IMG]: Length={len(el)}, tag={el[:150]}...")
else:
    print("examDatabase not found")
