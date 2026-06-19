# -*- coding: utf-8 -*-
import fitz
import os
import re

import fitz
import os
import re
import sys

# Windows 콘솔 인코딩 에러 방지
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "data", "past_exams")
PDF_PATH = os.path.join(PDF_DIR, "2025년 감리사 자격검정 필기시험 문제-A형(답포함).pdf")

def test_bold_detection():
    if not os.path.exists(PDF_PATH):
        print(f"PDF를 찾을 수 없습니다: {PDF_PATH}")
        return
        
    doc = fitz.open(PDF_PATH)
    
    # 2026년 70번 문제 검사 (DB 과목, 51~75번 사이이므로 3과목)
    # 70번 문제를 찾아보자
    print("PDF 파일에서 70번 문제의 Bold 텍스트 분석 시작...")
    
    target_num = 70
    found_page = None
    target_rect = None
    
    # 1단계: 70번 문제 위치 찾기
    for page_idx, page in enumerate(doc):
        if page_idx == 0:
            continue
        width = page.rect.width
        height = page.rect.height
        bands_count = 4 if width > height else 2
        
        for b in range(bands_count):
            x0 = (width / bands_count) * b
            x1 = (width / bands_count) * (b + 1)
            clip_rect = fitz.Rect(x0, 0, x1, height)
            blocks = page.get_text("blocks", clip=clip_rect)
            for block in blocks:
                text = block[4].strip()
                if text.startswith(f"{target_num}."):
                    found_page = page
                    target_rect = fitz.Rect(block[0], block[1], block[2], height) # 우선 대략 하단까지 잡음
                    # 대략 다음 문제 71번의 시작 위치를 구해서 잘라보자
                    for block_next in blocks:
                        if block_next[4].strip().startswith(f"{target_num + 1}."):
                            target_rect.y1 = block_next[1] - 5
                            break
                    break
            if found_page:
                break
        if found_page:
            break
            
    if not found_page:
        print("70번 문제를 찾을 수 없습니다.")
        return
        
    print(f"70번 문제 감지: Page {found_page.number}, Rect {target_rect}")
    
    # 2단계: 해당 rect 영역 내의 text dict 조회
    text_page = found_page.get_text("dict")
    
    bold_spans = []
    option_spans = []
    
    for block in text_page["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                span_rect = fitz.Rect(span["bbox"])
                # 타겟 영역 내부인지 확인
                if (target_rect.x0 - 5 <= span_rect.x0 <= target_rect.x1 + 5 and
                    target_rect.y0 - 5 <= span_rect.y0 <= target_rect.y1 + 5):
                    text = span["text"].strip()
                    font = span["font"].lower()
                    flags = span["flags"]
                    
                    is_bold = "bold" in font or (flags & 2 != 0)
                    
                    if text:
                        print(f"Text: '{text}' | Font: '{span['font']}' | Flags: {flags} | Bold: {is_bold}")
                        if is_bold:
                            bold_spans.append(span)
                        if re.search(r'[①②③④]', text):
                            option_spans.append(span)
                            
    print("\n--- 분석 결과 ---")
    print(f"발견된 보기 기호 스팬: {[s['text'] for s in option_spans]}")
    print(f"발견된 Bold 스팬: {[s['text'] for s in bold_spans]}")
    
    # Bold 처리된 보기 기호 매칭
    answer_num = None
    for opt_span in option_spans:
        opt_text = opt_span["text"]
        # 이 opt_span의 폰트가 Bold인지 검사
        opt_font = opt_span["font"].lower()
        opt_flags = opt_span["flags"]
        if "bold" in opt_font or (opt_flags & 2 != 0):
            match = re.search(r'([①②③④])', opt_text)
            if match:
                sym = match.group(1)
                sym_map = {"①": 1, "②": 2, "③": 3, "④": 4}
                answer_num = sym_map[sym]
                print(f"-> 정답 기호 자체(Bold) 발견: {sym} ({answer_num}번)")
                break
                
    if not answer_num:
        # 보기 기호 자체가 Bold가 아니라면, 보기 기호 근처의 텍스트가 Bold인지 확인
        print("-> 보기 기호 자체가 Bold가 아니므로 보기 텍스트의 Bold 여부를 매칭합니다.")
        for span in bold_spans:
            span_text = span["text"]
            # 보기 기호 뒤에 나오는 텍스트가 Bold인 경우
            # span의 y좌표가 어떤 보기 기호 스팬과 일치하는지 비교
            for opt_span in option_spans:
                if abs(opt_span["bbox"][1] - span["bbox"][1]) < 3: # 동일 라인 수준
                    match = re.search(r'([①②③④])', opt_span["text"])
                    if match:
                        sym = match.group(1)
                        sym_map = {"①": 1, "②": 2, "③": 3, "④": 4}
                        answer_num = sym_map[sym]
                        print(f"-> 동일 라인의 Bold 텍스트 '{span_text}' 발견으로 정답 추정: {sym} ({answer_num}번)")
                        break
            if answer_num:
                break
                
    print(f"최종 판정 정답: {answer_num}번")

if __name__ == "__main__":
    test_bold_detection()
