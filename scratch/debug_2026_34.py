# -*- coding: utf-8 -*-
import fitz
import os
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf"
doc = fitz.open(pdf_path)

for page_idx in [6, 7]:
    page = doc[page_idx]
    print(f"=== Page {page_idx} ===")
    width = page.rect.width
    height = page.rect.height
    bands_count = 4 if width > height else 2
    for b in range(bands_count):
        x0 = (width / bands_count) * b
        x1 = (width / bands_count) * (b + 1)
        clip_rect = fitz.Rect(x0, 0, x1, height)
        blocks = page.get_text("blocks", clip=clip_rect)
        blocks.sort(key=lambda x: x[1])
        
        print(f"  --- Band {b} (x0={x0:.1f}, x1={x1:.1f}) ---")
        for block in blocks:
            block_text = block[4].replace("\n", " ").strip()
            print(f"    rect=({block[0]:.1f}, {block[1]:.1f}, {block[2]:.1f}, {block[3]:.1f}) Text: {block_text[:120]}")


