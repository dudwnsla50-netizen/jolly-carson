# -*- coding: utf-8 -*-
import os
import re
import json

base_dir = r"d:\100.lyj\anti_workspace\jolly-carson"
reports_dir = os.path.join(base_dir, "reports")

files = [
    "se_frequent_concepts.html",
    "se_official_scopes.html",
    "pm_frequent_concepts.html",
    "pm_official_scopes.html",
    "db_frequent_concepts.html",
    "db_official_scopes.html",
    "sa_frequent_concepts.html",
    "sa_official_scopes.html",
    "sc_frequent_concepts.html",
    "sc_official_scopes.html"
]

expected = {
    "se": 300,
    "pm": 300,
    "db": 300,
    "sa": 300,
    "sc": 240
}

print("=== [Analysis] Dashboard HTML mapping_json uniqueness check ===")

for filename in files:
    path = os.path.join(reports_dir, filename)
    if not os.path.exists(path):
        print(f"{filename}: 파일 없음")
        continue
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # HTML 내의 topicMapping 또는 conceptMappings 값 추출 (JS 객체 또는 변수)
    match = re.search(r"const\s+(?:topicMapping|conceptMappings)\s*=\s*(\[[\s\S]*?\]);", content)
    if not match:
        print(f"{filename}: mapping 변수 매칭 실패")
        continue
        
    js_arr_str = match.group(1)
    try:
        topic_mapping = json.loads(js_arr_str)
    except Exception as e:
        print(f"{filename}: JSON 파싱 에러 - {e}")
        # 폴백 파서
        continue
        
    # 고유 문항 수 집계
    unique_qs = set()
    for item in topic_mapping:
        if "questions" in item:
            for q in item["questions"]:
                unique_qs.add(f"{q['year']}_{q['num']}")
                
    prefix = filename.split("_")[0]
    exp_count = expected[prefix]
    actual_count = len(unique_qs)
    
    status = "OK" if actual_count == exp_count else "FAIL"
    print(f"File: {filename:30s} | Actual: {actual_count:3d} (Expected: {exp_count:3d}) | Status: {status}")
    if actual_count != exp_count:
        # 누락된 키를 찾아보기 위해 12개년 전수 문항과 비교
        # 12개년 기준에 맞춰 전체 리스트 생성
        all_possible = set()
        if prefix == "se":
            q_start, q_end = 26, 50
        elif prefix == "pm":
            q_start, q_end = 1, 25
        elif prefix == "db":
            q_start, q_end = 51, 75
        elif prefix == "sa":
            q_start, q_end = 76, 100 # 임시
        elif prefix == "sc":
            q_start, q_end = 101, 120 # 임시
            
        for y in range(2015, 2027):
            curr_start = q_start
            curr_end = q_end
            # 2015년 분기 제거함 (SA: 76~100, SC: 101~120 고정)
            for n in range(curr_start, curr_end + 1):
                all_possible.add(f"{y}_{n}")
                
        missing = all_possible - unique_qs
        print(f"   Missing count: {len(missing)}: {sorted(list(missing))[:15]} ...")
