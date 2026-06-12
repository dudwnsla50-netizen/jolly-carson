# -*- coding: utf-8 -*-
import json
import re

def main():
    js_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_database.js"
    
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Strip Javascript variable declaration to make it parseable as JSON
    # It starts with "const examDatabase = {" and ends with "};"
    # We find the first occurrence of '{' and the last occurrence of '}'
    start_idx = content.find('{')
    end_idx = content.rfind('}')
    
    if start_idx == -1 or end_idx == -1:
        print("Error: Could not find object boundaries in the file.")
        return
        
    json_str = content[start_idx:end_idx+1]
    
    # JSON doesn't allow trailing commas, so we strip them if present.
    # A robust way is to try loading it directly first.
    try:
        data = json.loads(json_str)
        print("Success: exam_database.js structure is 100% valid JSON!")
        
        # Count keys by year
        years = {}
        for k in data.keys():
            y, n = k.split('_')
            years.setdefault(y, []).append(int(n))
            
        for y, nums in sorted(years.items()):
            print(f"Year {y}: min_num={min(nums)}, max_num={max(nums)}, total_count={len(nums)}")
            if len(nums) != max(nums):
                missing = [i for i in range(1, max(nums)+1) if i not in nums]
                print(f"  Warning: missing numbers in {y}: {missing}")
    except json.JSONDecodeError as e:
        print(f"JSON Load failed initially (expected due to trailing commas/comments): {e}")
        print("Attempting to parse and clean up key-values dynamically...")
        
        # Let's parse it using regular expressions to check key-values
        # Each entry looks like: "year_num": "question_text", or "year_num": "question_text"
        pattern = r'"(\d{4}_\d+)":\s*(".*?")\s*(?:,|$)'
        # Using re.DOTALL and re.VERBOSE because question texts are multiline and contain escaped characters
        # But a safer approach is to parse line by line or use a custom JSON parser
        # Let's count how many keys match the expected pattern
        keys = re.findall(r'"(\d{4}_\d+)":', content)
        print(f"Total keys found in JS file: {len(keys)}")
        
        # Check specific key ranges
        years = {}
        for k in keys:
            y, n = k.split('_')
            n = int(n)
            years.setdefault(y, []).append(n)
            
        for y, nums in sorted(years.items()):
            print(f"Year {y}: min_num={min(nums)}, max_num={max(nums)}, total_count={len(nums)}")
            if len(nums) != max(nums):
                # check if there are missing numbers
                missing = [i for i in range(1, max(nums)+1) if i not in nums]
                if missing:
                    print(f"  Warning: missing numbers in {y}: {missing}")
                    
        # Check 2025 and 2026 specifically
        if '2025' in years:
            print(f"2025 verification: total={len(years['2025'])} (1-120)")
        if '2026' in years:
            print(f"2026 verification: total={len(years['2026'])} (1-120)")
            
if __name__ == "__main__":
    main()
