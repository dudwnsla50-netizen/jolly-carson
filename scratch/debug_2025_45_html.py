# -*- coding: utf-8 -*-
import os
import re

html_path = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html\2025년 감리사 자격검정 필기시험 문제-A형(답포함).html"

with open(html_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# "45." 또는 "Normal" 또는 "Conditional" 등 유스케이스 관련 키워드가 있는 라인 검색
found_lines = []
for idx, line in enumerate(lines):
    if "Normal" in line or "Conditional" in line or "유스케이스" in line:
        found_lines.append((idx, line))

print(f"검색된 라인 수: {len(found_lines)}")
for idx, line in found_lines[:15]:
    print(f"Line {idx}: {line.strip()[:150]}")
