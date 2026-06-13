# -*- coding: utf-8 -*-
import os
import sys
import re
import json

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

db_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_db\se_db.js"

if not os.path.exists(db_path):
    print("se_db.js not found")
    sys.exit(1)

with open(db_path, "r", encoding="utf-8") as f:
    content = f.read()

# const examDatabase = {...} 부분을 정규식으로 안전하게 추출하고 JSON 파싱
match = re.search(r"const\s+examDatabase\s*=\s*(\{[\s\S]*\});", content)
if match:
    try:
        db = json.loads(match.group(1))
        val = db.get("2016_30", "NOT_FOUND")
        print("--- Exact 2016_30 Content ---")
        # base64가 너무 길 수 있으므로 처음 1000글자만 출력
        print(val[:1000])
        print("Length of 2016_30 content:", len(val))
    except Exception as e:
        print("JSON parse error:", e)
else:
    print("const examDatabase pattern not found")
