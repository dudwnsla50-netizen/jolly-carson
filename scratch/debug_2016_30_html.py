# -*- coding: utf-8 -*-
import os
import sys
import re

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

html_path = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html\2016년(제17회) 정보시스템 감리사 필기시험 문제 및 답안.html"

if not os.path.exists(html_path):
    print("HTML file not found")
    sys.exit(1)

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

elements = re.findall(r'(<p[^>]*>[\s\S]*?</p>|<img[^>]*>)', content)

print("--- 2016년 기출 HTML에서 X: 40~60pt, Y: 400~550pt 부근의 p 태그 검색 ---")
for idx, el in enumerate(elements):
    if "<p" in el:
        style_match = re.search(r'style="([^"]*)"', el)
        if style_match:
            style = style_match.group(1)
            top_match = re.search(r'top:\s*(\d+(\.\d+)?)pt', style)
            left_match = re.search(r'left:\s*(\d+(\.\d+)?)pt', style)
            if top_match and left_match:
                top = float(top_match.group(1))
                left = float(left_match.group(1))
                # 좌측 단 40~70pt, 높이 400~550pt
                if 40 <= left <= 70 and 400 <= top <= 580:
                    txt = re.sub(r'<[^>]*>', '', el).strip()
                    print(f"Element {idx} [L:{left}, T:{top}]: {txt}")

