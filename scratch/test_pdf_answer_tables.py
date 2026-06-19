# -*- coding: utf-8 -*-
import fitz
import os
import sys

if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "data", "past_exams")

def check_last_pages():
    files = os.listdir(PDF_DIR)
    for f_name in sorted(files):
        if not f_name.endswith(".pdf"):
            continue
        pdf_path = os.path.join(PDF_DIR, f_name)
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        print(f"\n==========================================")
        print(f"파일명: {f_name} (총 {page_count}페이지)")
        
        # 마지막 2페이지 텍스트 스캔
        start_p = max(0, page_count - 2)
        found_keywords = False
        for p_idx in range(start_p, page_count):
            page = doc[p_idx]
            text = page.get_text()
            # 정답표가 있을 만한 키워드 검사
            if "정답" in text or "가답안" in text or "정답표" in text or "과목" in text:
                found_keywords = True
                print(f"--- Page {p_idx + 1} 텍스트 일부 (길이 {len(text)}) ---")
                # 텍스트가 너무 길면 처음 500자만 출력
                print(text[:800])
                print("-" * 30)
        if not found_keywords:
            print("마지막 페이지에 정답표 관련 키워드가 검출되지 않았습니다.")

if __name__ == "__main__":
    check_last_pages()
