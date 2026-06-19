# -*- coding: utf-8 -*-
import fitz
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "data", "past_exams")
OUT_FILE = os.path.join(BASE_DIR, "scratch", "answers_extracted.txt")

def main():
    if not os.path.exists(PDF_DIR):
        print("PDF Directory not found:", PDF_DIR)
        return
        
    files = sorted(os.listdir(PDF_DIR))
    with open(OUT_FILE, "w", encoding="utf-8") as out:
        for f in files:
            if not f.endswith(".pdf"):
                continue
                
            pdf_path = os.path.join(PDF_DIR, f)
            out.write(f"\n=========================================\n")
            out.write(f"FILE: {f}\n")
            
            try:
                doc = fitz.open(pdf_path)
            except Exception as e:
                out.write(f"Load failed: {e}\n")
                continue
                
            page_count = len(doc)
            out.write(f"Total pages: {page_count}\n")
            
            # 마지막 2페이지 확인
            start_check = max(0, page_count - 2)
            for idx in range(start_check, page_count):
                page_text = doc[idx].get_text()
                out.write(f"\n--- Page {idx + 1} ---\n")
                out.write(page_text)
                out.write("\n---------------------\n")
                
            doc.close()
            
    print("Successfully wrote extracted texts to scratch/answers_extracted.txt")

if __name__ == "__main__":
    main()
