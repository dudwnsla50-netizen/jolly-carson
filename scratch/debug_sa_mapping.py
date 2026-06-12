# -*- coding: utf-8 -*-
import os
import sys
import re

base_dir = r"d:\100.lyj\anti_workspace\jolly-carson"
sys.path.append(base_dir)

# build_premium_sa_viewer의 load_exam_database_dict, run_extraction_and_mapping 테스트
from build_premium_sa_viewer import load_exam_database_dict, run_extraction_and_mapping, CONCEPT_KEYWORDS

print("CONCEPT_KEYWORDS count:", len(CONCEPT_KEYWORDS))

subject_code = "SA"
exam_db_dict = load_exam_database_dict(subject_code)
print("load_exam_database_dict length:", len(exam_db_dict))
if exam_db_dict:
    print("Sample keys from loaded dict:", list(exam_db_dict.keys())[:10])

# run_extraction_and_mapping 결과물 테스트
q_db, c_map = run_extraction_and_mapping()
print("run_extraction_and_mapping q_db length:", len(q_db))
if q_db:
    print("Sample keys from mapping:", list(q_db.keys())[:10])
else:
    print("q_db is EMPTY!")
