# -*- coding: utf-8 -*-
import fitz # PyMuPDF
import os

pdf_path = r"e:\jolly-carson\data\past_exams\2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf"

def parse_pdf():
    if not os.path.exists(pdf_path):
        print("PDF file not found.")
        return
        
    doc = fitz.open(pdf_path)
    print(f"Total pages: {len(doc)}")
    
    # 마지막 3페이지의 텍스트를 출력해서 정답표가 있는지 확인
    for page_num in range(len(doc) - 3, len(doc)):
        page = doc[page_num]
        print(f"--- PAGE {page_num + 1} ---")
        print(page.get_text()[:1000]) # 1000자만 출력
        print("---------------------\n")
        
    doc.close()

if __name__ == "__main__":
    parse_pdf()
