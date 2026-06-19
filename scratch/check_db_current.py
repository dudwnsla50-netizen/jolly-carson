# -*- coding: utf-8 -*-
import fitz
import sys
import io

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

pdf_path = r"e:\jolly-carson\data\past_exams\2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf"
doc = fitz.open(pdf_path)
print("전체 페이지 수:", len(doc))
# 마지막 페이지 (인덱스 24) 출력
print(doc[24].get_text())
doc.close()

conn.close()
