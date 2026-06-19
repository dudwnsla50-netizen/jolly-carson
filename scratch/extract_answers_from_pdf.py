# -*- coding: utf-8 -*-
"""
[최신 기출 PDF 분석 스크립트]
- 목적: 2024, 2025, 2026년 PDF 파일에서 아직 누락된 특정 문항들의 텍스트 지문과 정답을 직접 추출합니다.
  (예: 2025년 1,2,4,5,6,30,44번 및 2026년 3,28번, 2024년 35번)
"""
import fitz
import sys
import io
import re

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PDF_DIR = r"e:\jolly-carson\data\past_exams"

def scan_pdf_for_question(pdf_name, q_num):
    pdf_path = os.path.join(PDF_DIR, pdf_name)
    if not os.path.exists(pdf_path):
        print(f"파일 없음: {pdf_path}")
        return
        
    doc = fitz.open(pdf_path)
    print(f"\n==================== {pdf_name} - {q_num}번 문항 탐색 ====================")
    
    for page_idx, page in enumerate(doc):
        text = page.get_text()
        # 해당 문항 번호(예: '1.', '30.')가 시작되는 부분을 단순 검색
        if re.search(rf"\b{q_num}\s*[\.\)]", text):
            print(f"[Page {page_idx}]에서 감지됨:")
            lines = text.split("\n")
            # 문항 번호 근처 25줄을 가져와서 지문 확인
            start_print = False
            lines_printed = 0
            for line in lines:
                if re.search(rf"^\s*{q_num}\s*[\.\)]", line) or (not start_print and re.search(rf"\b{q_num}\s*[\.\)]", line)):
                    start_print = True
                if start_print:
                    print("  ", line)
                    lines_printed += 1
                    if lines_printed > 25:
                        break
    doc.close()

if __name__ == "__main__":
    import os
    # 2025년 누락 대상
    scan_pdf_for_question("2025년 감리사 자격검정 필기시험 문제-A형(답포함).pdf", 1)
    scan_pdf_for_question("2025년 감리사 자격검정 필기시험 문제-A형(답포함).pdf", 2)
    scan_pdf_for_question("2025년 감리사 자격검정 필기시험 문제-A형(답포함).pdf", 30)
    scan_pdf_for_question("2025년 감리사 자격검정 필기시험 문제-A형(답포함).pdf", 44)
    
    # 2026년 누락 대상
    scan_pdf_for_question("2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf", 3)
    scan_pdf_for_question("2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf", 28)
    
    # 2024년 누락 대상 (35번)
    scan_pdf_for_question("2024년(제25회) 감리사 자격검정 필기시험 문제-A형.pdf", 35)
    # 2024년 정답표 PDF 탐색
    scan_pdf_for_question("2024년 감리사 자격검정 필기시험 답안표.pdf", 35)
