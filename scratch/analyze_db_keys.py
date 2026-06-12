import os
import json
import re

reports_dir = r"d:\100.lyj\anti_workspace\jolly-carson\reports"
db_dir = os.path.join(reports_dir, "exam_db")

def analyze_js_file(path, expected_count):
    if not os.path.exists(path):
        print(f"[경고] 파일이 존재하지 않음: {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # regex to match "2015_26" style keys
    keys = re.findall(r'"(\d{4}_\d+)":', content)
    print(f"File: {os.path.basename(path)}")
    print(f"  Total keys: {len(keys)} (Expected: {expected_count})")
    if len(keys) != expected_count:
        print(f"  [오류] 문항 수 불일치! 기대값: {expected_count}, 실제값: {len(keys)}")
    if keys:
        print(f"  Min key: {min(keys)}, Max key: {max(keys)}")

print("Analyzing separated subject database files:")
analyze_js_file(os.path.join(db_dir, "pm_db.js"), 300)
analyze_js_file(os.path.join(db_dir, "se_db.js"), 300)
analyze_js_file(os.path.join(db_dir, "db_db.js"), 300)
analyze_js_file(os.path.join(db_dir, "sa_db.js"), 300)
analyze_js_file(os.path.join(db_dir, "sc_db.js"), 240)

