import os
import sys
import re

sys.path.append(r"d:\100.lyj\anti_workspace\jolly-carson")
from build_premium_se_viewer import run_extraction_and_mapping, build_html_content, CONCEPT_KEYWORDS, TOPIC_CATEGORIES

# run
question_db, concept_map = run_extraction_and_mapping()
print(f"question_db size: {len(question_db)}")

# 구형 exam_database.js 체크 부분 제거
json_loads_success = True






# Check concept map sizes
print("Concept map counts:")
for c, qs in concept_map.items():
    if len(qs) > 0:
        print(f"  {c}: {len(qs)}")

# Check what happens inside build_html_content
# We will inspect sorted_concepts
sorted_concepts = []
for concept, items in concept_map.items():
    years = sorted(list(set([it["year"] for it in items])))
    sorted_questions = sorted(items, key=lambda x: (x["year"], x["num"]), reverse=True)
    sorted_concepts.append({
        "concept": concept,
        "category": TOPIC_CATEGORIES.get(concept, "기타"),
        "count": len(items),
        "years": years,
        "questions": sorted_questions
    })

print(f"Total concepts: {len(sorted_concepts)}")

discarded_questions = []
for c in sorted_concepts:
    if c["count"] < 3 and c["concept"] != "[기타]":
        discarded_questions.extend(c["questions"])
        
print(f"Discarded questions count: {len(discarded_questions)}")

etc_concept = None
for c in sorted_concepts:
    if c["concept"] == "[기타]":
        etc_concept = c
        break

if etc_concept:
    print(f"Initial etc_concept count: {etc_concept['count']}")
    existing = set((q["year"], q["num"]) for q in etc_concept["questions"])
    for q in discarded_questions:
        if (q["year"], q["num"]) not in existing:
            etc_concept["questions"].append(q)
            existing.add((q["year"], q["num"]))
    etc_concept["count"] = len(etc_concept["questions"])
    print(f"Final etc_concept count: {etc_concept['count']}")

# Count total unique questions in filtered concepts
filtered_concepts = [c for c in sorted_concepts if c["count"] >= 3 or c["concept"] == "[기타]"]
unique_qs = set()
for c in filtered_concepts:
    for q in c["questions"]:
        unique_qs.add(f"{q['year']}_{q['num']}")
        
print(f"Unique questions in filtered: {len(unique_qs)}")
