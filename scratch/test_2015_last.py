# -*- coding: utf-8 -*-
import fitz
import os
import sys

if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "data", "past_exams", "2015년(제16회) 정보시스템 감리사 필기시험 문제 및 답안.pdf")

def print_last():
    doc = fitz.open(PDF_PATH)
    page_count = len(doc)
    print(f"2015년 PDF 총 페이지 수: {page_count}")
    
    # 마지막 2페이지
    for idx in range(page_count - 2, page_count):
        print(f"\n--- Page {idx + 1} 텍스트 ---")
        print(doc[idx].get_text())
    doc.close()

if __name__ == "__main__":
    print_last()
