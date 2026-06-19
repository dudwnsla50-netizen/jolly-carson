# -*- coding: utf-8 -*-
"""
[PDF 답안 텍스트 검색기]
- 작성자: Antigravity
- 설계 목적: data/past_exams/*.pdf 파일의 각 페이지 텍스트를 검색하여 정답표가 포함되어 있는지 확인합니다.
"""
import fitz
import os
import sys

# Windows 콘솔 인코딩 에러 방지
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "data", "past_exams")

def check_pdf_answers():
    if not os.path.exists(PDF_DIR):
        print(f"디렉토리가 없습니다: {PDF_DIR}")
        return
        
    files = sorted(os.listdir(PDF_DIR))
    for f in files:
        if not f.endswith(".pdf"):
            continue
            
        pdf_path = os.path.join(PDF_DIR, f)
        print(f"\n=========================================")
        print(f"파일 분석: {f}")
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"로드 실패: {e}")
            continue
            
        page_count = len(doc)
        print(f"총 페이지 수: {page_count}")
        
        # 전체 페이지 탐색
        start_page = 0
        found_sheet = False
        for idx in range(start_page, page_count):
            page_text = doc[idx].get_text()
            # 정답표 매칭 키워드
            if "정답" in page_text or "가답안" in page_text or "답안" in page_text:
                # 단어들이 많이 나열되어 있는지 (예: ①, ②, ③, ④ 또는 숫자들)
                # 정답표 느낌이 나는지 판단
                print(f"  -> Page {idx + 1}에서 '답안/정답' 관련 텍스트 감지!")
                print(f"--- Page {idx + 1} 텍스트 미리보기 ---")
                lines = page_text.split("\n")
                # 처음 20줄 출력
                for line in lines[:30]:
                    print(f"    {line}")
                print(f"------------------------------------")
                found_sheet = True
                
        if not found_sheet:
            print("  -> 마지막 3페이지에서 답안 관련 텍스트를 감지하지 못했습니다.")
            
        doc.close()

if __name__ == "__main__":
    check_pdf_answers()
