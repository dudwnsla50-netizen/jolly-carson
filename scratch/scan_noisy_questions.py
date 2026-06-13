# -*- coding: utf-8 -*-
import os
import sys
import re
import json

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r"d:\100.lyj\anti_workspace\jolly-carson"
DB_DIR = os.path.join(BASE_DIR, "reports", "exam_db")

db_files = [
    "db_db.js",
    "pm_db.js",
    "se_db.js",
    "sa_db.js",
    "sc_db.js",
    "../exam_database.js"
]

print("=== [시작] 보기 ④번 뒤 노이즈 단락(텍스트/이미지) 전과목 스캔 ===")

for db_file in db_files:
    db_path = os.path.normpath(os.path.join(DB_DIR, db_file))
    if not os.path.exists(db_path):
        continue
        
    with open(db_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r"const\s+examDatabase\s*=\s*(\{[\s\S]*\});", content)
    if not match:
        continue
        
    try:
        db = json.loads(match.group(1))
    except Exception:
        # 간단한 파서 폴백
        pairs = re.findall(r'"(\d{4}_\d+)":\s*"(.*?)"(?=,\s*"|\s*\})', match.group(1), re.DOTALL)
        db = {}
        for k, v in pairs:
            db[k] = v.replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')
            
    filename = os.path.basename(db_path)
    print(f"\n📂 [{filename}] 스캔 중...")
    
    candidates = []
    for key, val in db.items():
        if not isinstance(val, str) or "<p" not in val:
            continue
            
        sub_elements = re.findall(r'(<p[^>]*>[\s\S]*?</p>|<img[^>]*>)', val)
        
        # 보기 ④번의 인덱스 찾기 (가장 마지막 ④번)
        q4_idx = -1
        for idx, el in enumerate(sub_elements):
            if "<p" in el:
                txt = re.sub(r'<[^>]*>', '', el).strip()
                if "④" in txt:
                    q4_idx = idx
                    
        if q4_idx != -1 and q4_idx < len(sub_elements) - 1:
            post_elements = sub_elements[q4_idx+1:]
            # 텍스트 내용 복원
            post_text = " / ".join(re.sub(r'<[^>]*>', '', el).strip() for el in post_elements if "<p" in el)
            post_text = post_text.strip()
            
            # 사소한 공백이나 구분자만 남은 경우는 제외
            if post_text or any("<img" in el for el in post_elements):
                candidates.append({
                    "key": key,
                    "total": len(sub_elements),
                    "q4_idx": q4_idx,
                    "post_count": len(post_elements),
                    "post_snippet": post_text[:80] + ("..." if len(post_text) > 80 else "")
                })
                
    print(f"  -> 검출된 노이즈 후보 문항 수: {len(candidates)}")
    for c in candidates:
        print(f"    👉 Key: {c['key']} | ④번 뒤 엘리먼트 수: {c['post_count']}개 | 내용 스니펫: {c['post_snippet']}")

