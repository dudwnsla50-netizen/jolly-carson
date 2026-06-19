# -*- coding: utf-8 -*-
"""
[연도별 폰트 정밀 진단기]
- 작성자: Antigravity
- 설계 목적: 각 기출 PDF의 51번 문항 보기(①~④) 영역을 탐색하여 사용된 폰트와 텍스트를 출력합니다.
"""
import fitz
import os
import re
import sys
from collections import Counter

# Windows 콘솔 인코딩 에러 방지
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "data", "past_exams")

def debug_fonts_for_all_years():
    if not os.path.exists(PDF_DIR):
        print("PDF 디렉토리가 없습니다.")
        return
        
    # 연도 추출
    files = sorted(os.listdir(PDF_DIR))
    years = []
    pdf_files = {}
    for f in files:
        if f.endswith(".pdf"):
            match = re.match(r"^(\d{4})", f)
            if match:
                y = int(match.group(1))
                # 문제지 파일만 선택 (답안표 등 제외)
                if "답안표" in f:
                    continue
                # 가급적 문제지만 선택
                pdf_files[y] = os.path.join(PDF_DIR, f)
                
    print(f"발견된 연도별 문제지 PDF: {list(pdf_files.keys())}")
    
    for year in sorted(pdf_files.keys()):
        pdf_path = pdf_files[year]
        print(f"\n=========================================")
        print(f"[{year}년도 분석] -> {os.path.basename(pdf_path)}")
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"로드 실패: {e}")
            continue
            
        # 51번 문제 찾기
        q_num = 51
        found_page = None
        target_rect = None
        
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
                    if re.match(rf"^{q_num}[\.\)\s]", text):
                        found_page = page
                        target_rect = fitz.Rect(block[0], block[1], block[2], height)
                        for block_next in blocks:
                            if re.match(rf"^{q_num + 1}[\.\)\s]", block_next[4].strip()):
                                target_rect.y1 = block_next[1] - 5
                                break
                        break
                if found_page:
                    break
            if found_page:
                break
                
        if not found_page:
            print(f"  -> 51번 문제를 찾지 못했습니다.")
            doc.close()
            continue
            
        print(f"  -> 51번 문제 발견 (Page {found_page.number + 1})")
        
        text_page = found_page.get_text("dict")
        spans = []
        for block in text_page["blocks"]:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    span_rect = fitz.Rect(span["bbox"])
                    if (target_rect.x0 - 5 <= span_rect.x0 <= target_rect.x1 + 5 and
                        target_rect.y0 - 5 <= span_rect.y0 <= target_rect.y1 + 5):
                        spans.append(span)
                        
        # 보기 스팬 분류
        opt_spans = {"①": [], "②": [], "③": [], "④": []}
        current_opt = None
        
        # y좌표 순으로 먼저 정렬해서 읽기 흐름에 따라 분류 시도
        spans.sort(key=lambda s: (s["bbox"][1], s["bbox"][0]))
        
        for span in spans:
            text = span["text"].strip()
            if not text:
                continue
            match = re.search(r'([①②③④❶❷❸❹])', text)
            if match:
                current_opt = match.group(1)
                # ❶❷❸❹ 를 ①②③④ 로 매핑
                map_sym = {"❶": "①", "❷": "②", "❸": "③", "❹": "④"}
                if current_opt in map_sym:
                    current_opt = map_sym[current_opt]
            if current_opt:
                opt_spans[current_opt].append(span)
                
        for sym in ["①", "②", "③", "④"]:
            s_list = opt_spans[sym]
            fonts = [s["font"] for s in s_list]
            texts = [s["text"] for s in s_list]
            font_counter = Counter(fonts)
            print(f"  보기 {sym}:")
            print(f"    폰트: {dict(font_counter)}")
            print(f"    텍스트: {' '.join(texts)}")
            # 상세한 font 정보 (flags 등)
            for s in s_list[:3]: # 상위 3개만
                print(f"      - [text='{s['text']}', font='{s['font']}', size={s['size']:.1f}, color={s['color']}, flags={s['flags']}]")
                
        doc.close()

if __name__ == "__main__":
    debug_fonts_for_all_years()
