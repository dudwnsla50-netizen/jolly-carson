import os
import json
import re

html_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\se_frequent_concepts.html"
if not os.path.exists(html_path):
    print("se_frequent_concepts.html not found")
    exit()

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

match = re.search(r"const\s+topicMapping\s*=\s*(\[[\s\S]*?\]);", content)
if not match:
    print("topicMapping not found in HTML")
    exit()

mapping_str = match.group(1)
lines = mapping_str.split('\n')
print(f"Total lines in mapping string: {len(lines)}")
# Print lines around 277
start_line = max(0, 260)
end_line = min(len(lines), 300)
for idx in range(start_line, end_line):
    print(f"{idx+1}: {lines[idx]}")


# se_db.js 의 키 목록과 대조
db_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_db\se_db.js"
with open(db_path, "r", encoding="utf-8") as f:
    db_content = f.read()

db_keys = re.findall(r'"(\d{4}_\d+)":', db_content)
print(f"Total keys in se_db.js: {len(db_keys)}")

missing_in_mapping = set(db_keys) - unique_qs
print(f"Missing keys in mapping (db_keys but not in unique_qs): {len(missing_in_mapping)}")
if missing_in_mapping:
    print(f"First 20 missing: {sorted(list(missing_in_mapping))[:20]}")
