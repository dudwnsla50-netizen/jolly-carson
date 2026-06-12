# -*- coding: utf-8 -*-
import os
import sys

def check_pdf():
    # PDF 파일 경로 설정
    pdf_path = r"d:\100.lyj\anti_workspace\감리사_시험대비\1.기출문제\2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf"
    if not os.path.exists(pdf_path):
        # jolly-carson 폴더 안에도 있을 수 있으니 백업 경로 확인
        pdf_path = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf"

    if not os.path.exists(pdf_path):
        print(f"[에러] 파일을 찾을 수 없습니다: {pdf_path}")
        return

    print(f"대상 파일: {pdf_path}")
    
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"총 페이지 수: {total_pages}")
        
        output_path = r"d:\100.lyj\anti_workspace\jolly-carson\scratch\check_pdf_output.txt"
        with open(output_path, "w", encoding="utf-8") as out_f:
            # 마지막 3개 페이지 읽어보기
            for p_idx in range(max(0, total_pages - 3), total_pages):
                out_f.write(f"\n--- [페이지 {p_idx + 1}] ---\n")
                page = doc.load_page(p_idx)
                text = page.get_text()
                out_f.write(text)
        print(f"출력이 저장되었습니다: {output_path}")
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_pdf()
