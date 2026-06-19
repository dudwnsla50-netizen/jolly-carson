# -*- coding: utf-8 -*-
"""
[Phase 2 실패 원인 정밀 진단]
- 설계 목적: answer 누락 424건의 실패 원인을 분류합니다.
  1. PDF에서 문항 영역을 찾지 못한 경우 (find_question_in_pdf 실패)
  2. 보기 기호를 감지하지 못한 경우 (option_symbols < 4)
  3. 크롭 이미지가 없는 경우
  4. 밀도 차이가 임계값 미만인 경우 (판정 불가)
"""
import fitz
import os
import re
import sys
import io
import json
import sqlite3
from PIL import Image

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")
PDF_DIR = os.path.join(BASE_DIR, "data", "past_exams")
IMG_DIR = os.path.join(BASE_DIR, "reports", "images")

SYM_MAP = {"①": 1, "②": 2, "③": 3, "④": 4, "❶": 1, "❷": 2, "❸": 3, "❹": 4}

def get_pdf_file_for_year(year):
    files = os.listdir(PDF_DIR)
    for f in files:
        if f.endswith(".pdf") and f.startswith(str(year)) and "답안표" not in f:
            return os.path.join(PDF_DIR, f)
    return None

def find_question_in_pdf(doc, q_num):
    for page_idx, page in enumerate(doc):
        if page_idx == 0:
            continue
        width = page.rect.width
        height = page.rect.height
        bands_count = 4 if width > height else 2
        for b in range(bands_count):
            x0 = (width / bands_count) * b
            x1 = (width / bands_count) * (b + 1)
            clip_rect = fitz.Rect(x0, 0, x1, height)
            blocks = page.get_text("blocks", clip=clip_rect)
            for block in blocks:
                text = block[4].strip()
                if re.match(rf"^{q_num}[\.)\s]", text):
                    target_rect = fitz.Rect(block[0], block[1], block[2], height)
                    for block_next in blocks:
                        if re.match(rf"^{q_num + 1}[\.)\s]", block_next[4].strip()):
                            target_rect.y1 = block_next[1] - 5
                            break
                    return page, target_rect
    return None, None

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("""SELECT id, year, question_num FROM exam_questions 
             WHERE answer IS NULL OR answer = '' OR answer = '[]'
             ORDER BY year, question_num""")
missing = c.fetchall()
conn.close()

# 실패 원인 분류
reasons = {
    "no_pdf": [],        # PDF 없음
    "not_found": [],     # PDF에서 문항 못 찾음
    "no_image": [],      # 크롭 이미지 없음
    "few_symbols": [],   # 보기 기호 4개 미만
    "low_density": [],   # 밀도 차이 미달
}

by_year = {}
for q_id, year, q_num in missing:
    if year not in by_year:
        by_year[year] = []
    by_year[year].append((q_id, q_num))

for year in sorted(by_year.keys()):
    pdf_path = get_pdf_file_for_year(year)
    if not pdf_path:
        for q_id, q_num in by_year[year]:
            reasons["no_pdf"].append(q_id)
        continue

    doc = fitz.open(pdf_path)
    
    for q_id, q_num in sorted(by_year[year], key=lambda x: x[1]):
        page, crop_rect = find_question_in_pdf(doc, q_num)
        
        if not page:
            reasons["not_found"].append(q_id)
            continue
        
        # 크롭 이미지 확인
        img_path = os.path.join(IMG_DIR, f"{year}_{q_num}.png")
        if not os.path.exists(img_path):
            reasons["no_image"].append(q_id)
            continue
        
        # 보기 기호 감지
        text_page = page.get_text("dict")
        option_count = 0
        for block in text_page["blocks"]:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    span_rect = fitz.Rect(span["bbox"])
                    if (crop_rect.x0 - 5 <= span_rect.x0 <= crop_rect.x1 + 5 and
                        crop_rect.y0 - 5 <= span_rect.y0 <= crop_rect.y1 + 5):
                        if re.search(r'[①②③④❶❷❸❹]', span["text"].strip()):
                            option_count += 1
        
        if option_count < 4:
            reasons["few_symbols"].append(q_id)
            continue
        
        reasons["low_density"].append(q_id)
    
    doc.close()

print("=" * 70)
print("[answer 누락 실패 원인 분류]")
print("=" * 70)
print(f"  전체 누락: {len(missing)}건")
print(f"  PDF 없음: {len(reasons['no_pdf'])}건")
print(f"  문항 못 찾음: {len(reasons['not_found'])}건")
print(f"  크롭 이미지 없음: {len(reasons['no_image'])}건")
print(f"  보기 기호 미달(<4): {len(reasons['few_symbols'])}건")
print(f"  밀도 차이 미달: {len(reasons['low_density'])}건")

print(f"\n--- 문항 못 찾음 상세 ({len(reasons['not_found'])}건) ---")
for q_id in reasons['not_found'][:30]:
    print(f"  {q_id}")
if len(reasons['not_found']) > 30:
    print(f"  ... 외 {len(reasons['not_found'])-30}건")

print(f"\n--- 보기 기호 미달 상세 ({len(reasons['few_symbols'])}건) ---")
for q_id in reasons['few_symbols'][:30]:
    print(f"  {q_id}")
if len(reasons['few_symbols']) > 30:
    print(f"  ... 외 {len(reasons['few_symbols'])-30}건")

print(f"\n--- 밀도 차이 미달 상세 ({len(reasons['low_density'])}건) ---")
for q_id in reasons['low_density'][:30]:
    print(f"  {q_id}")
if len(reasons['low_density']) > 30:
    print(f"  ... 외 {len(reasons['low_density'])-30}건")
