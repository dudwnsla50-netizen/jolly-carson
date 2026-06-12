# -*- coding: utf-8 -*-
import sys
import os
import json
import re
import shutil

sys.path.append(r"d:\100.lyj\anti_workspace\jolly-carson\scratch")
from extract_questions_v2 import reconstruct_exam_text, parse_sequential_questions, HTML_NAMES

def main():
    html_dir = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html"
    js_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_database.js"
    backup_path = js_path + ".bak"
    
    # 1. Backup existing file
    if os.path.exists(js_path):
        shutil.copyfile(js_path, backup_path)
        print(f"Backup created at: {backup_path}")
        
    # 2. Extract questions for all years (2015-2026)
    extracted_data = {}
    for y in sorted(HTML_NAMES.keys()):
        html_path = os.path.join(html_dir, HTML_NAMES[y])
        if os.path.exists(html_path):
            print(f"Extracting {y} questions...")
            text = reconstruct_exam_text(html_path, year=y)
            qs = parse_sequential_questions(text)
            print(f"  {y} extracted count: {len(qs)}")
            if len(qs) != 120:
                print(f"Error: Extraction failed for year {y}. Expected 120, got {len(qs)}.")
                return
            extracted_data[y] = qs
        else:
            print(f"Error: HTML file not found for year {y}: {HTML_NAMES[y]}")
            return
            
    # 3. Read original JS file and parse as JSON
    with open(js_path, "r", encoding="utf-8") as f:
        js_content = f.read()
        
    start_idx = js_content.find('{')
    end_idx = js_content.rfind('}')
    if start_idx == -1 or end_idx == -1:
        print("Error: Could not parse JS database file boundaries.")
        return
        
    json_str = js_content[start_idx:end_idx+1]
    
    try:
        db = json.loads(json_str)
        print("Successfully parsed existing database JSON.")
    except json.JSONDecodeError as e:
        print(f"Error parsing existing JS database as JSON: {e}")
        return
        
    # 4. Overwrite all entries from 2015 to 2026
    for y, qs in extracted_data.items():
        for i in range(1, 121):
            db[f"{y}_{i}"] = qs[i]
            
    # 5. Sort all keys chronologically (by year and then by question number)
    def key_sorter(key):
        year, num = key.split('_')
        return int(year), int(num)
        
    sorted_keys = sorted(db.keys(), key=key_sorter)
    
    # 6. Format back to JS file structure
    new_entries = []
    for idx, k in enumerate(sorted_keys):
        val_escaped = json.dumps(db[k], ensure_ascii=False)
        comma = "," if idx < len(sorted_keys) - 1 else ""
        new_entries.append(f'  "{k}": {val_escaped}{comma}')
        
    final_content = "const examDatabase = {\n" + "\n".join(new_entries) + "\n};\n"
    
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(final_content)
        
    print("Successfully updated exam_database.js for all years from 2015 to 2026!")

if __name__ == "__main__":
    main()
