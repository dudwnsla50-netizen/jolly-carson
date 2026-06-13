# -*- coding: utf-8 -*-
import os
import sys
import re

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

html_path = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html\2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.html"

if not os.path.exists(html_path):
    print("HTML file not found")
    sys.exit(1)

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

elements = re.findall(r'(<p[^>]*>[\s\S]*?</p>|<img[^>]*>)', content)

found_34 = False
count = 0
for idx, el in enumerate(elements):
    txt = re.sub(r'<[^>]*>', '', el).strip()
    if txt.startswith("34."):
        found_34 = True
        print(f"--- Found 34. at element index {idx} ---")
    
    if found_34:
        print(f"Element {idx}: {el[:200]} ... (Length: {len(el)})")
        count += 1
        if txt.startswith("35."):
            print(f"--- Found 35. at element index {idx} ---")
        if count > 25:
            break
