# -*- coding: utf-8 -*-
import os
import sys

sys.path.append(r"d:\100.lyj\anti_workspace\jolly-carson")
from build_premium_se_official_viewer import run_extraction_and_mapping, CONCEPT_KEYWORDS

question_db, concept_map = run_extraction_and_mapping()
print(f"Loaded question_db size: {len(question_db)}")

years_in_db = set()
for key in question_db.keys():
    year = key.split("_")[0]
    years_in_db.add(year)
print(f"Years present in question_db: {sorted(list(years_in_db))}")

# 각 연도별 문항 수 집계
year_counts = {}
for key in question_db.keys():
    year = int(key.split("_")[0])
    year_counts[year] = year_counts.get(year, 0) + 1
print("Question counts by year in question_db:")
for y in sorted(year_counts.keys()):
    print(f"  {y}년: {year_counts[y]}개")

# concept_map 분석
print("\nConcept Map unique questions count:")
all_mapped = set()
for concept, items in concept_map.items():
    for it in items:
        all_mapped.add(f"{it['year']}_{it['num']}")
print(f"Total unique mapped questions in concept_map: {len(all_mapped)}")

mapped_years = set(key.split("_")[0] for key in all_mapped)
print(f"Years present in concept_map: {sorted(list(mapped_years))}")
