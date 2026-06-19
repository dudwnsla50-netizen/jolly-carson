# -*- coding: utf-8 -*-
import fitz
import os
import sys

if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "data", "past_exams", "2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf")

def print_last_pages():
    doc = fitz.open(PDF_PATH)
    page_count = len(doc)
    print(f"2026년 PDF 총 페이지 수: {page_count}")
    
    # 마지막 3페이지 출력
    for idx in range(page_count - 3, page_count):
        print(f"\n--- Page {idx + 1} 텍스트 ---")
        print(doc[idx].get_text()[:1000])

if __name__ == "__main__":
    print_last_pages()
