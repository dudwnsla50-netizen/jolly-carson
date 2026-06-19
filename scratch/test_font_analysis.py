# -*- coding: utf-8 -*-
import fitz
import os
import re
import sys
from collections import Counter

if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "data", "past_exams", "2025년 감리사 자격검정 필기시험 문제-A형(답포함).pdf")

def analyze_fonts():
    doc = fitz.open(PDF_PATH)
    
    # 51번부터 75번(DB 과목) 분석
    for q_num in range(51, 76):
        # 1. 문제 위치 찾기
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
                    if text.startswith(f"{q_num}."):
                        found_page = page
                        target_rect = fitz.Rect(block[0], block[1], block[2], height)
                        # 다음 문제 위치로 y1 제한
                        for block_next in blocks:
                            if block_next[4].strip().startswith(f"{q_num + 1}."):
                                target_rect.y1 = block_next[1] - 5
                                break
                        break
                if found_page:
                    break
            if found_page:
                break
                
        if not found_page:
            print(f"{q_num}번 문제를 찾을 수 없습니다.")
            continue
            
        # 2. 해당 영역 내 텍스트 스팬 수집
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
                        
        # 3. 보기 기호 매칭 및 줄별 폰트 분석
        # 보기 기호들의 y좌표 구하기
        opt_y_map = {}
        for span in spans:
            text = span["text"].strip()
            match = re.search(r'([①②③④❶❷❸❹])', text)
            if match:
                sym = match.group(1)
                opt_y_map[sym] = span["bbox"][1] # y좌표 저장
                
        # 보기별 텍스트 스팬 수집
        opt_spans = {sym: [] for sym in opt_y_map}
        for span in spans:
            span_y = span["bbox"][1]
            # y좌표가 어떤 보기의 y좌표와 가까운지 매칭 (오차 3px 내)
            for sym, opt_y in opt_y_map.items():
                if abs(span_y - opt_y) < 4:
                    opt_spans[sym].append(span)
                    
        # 보기별 폰트 명칭 분포 확인
        print(f"\n[{q_num}번 문항 보기별 폰트 분석]")
        font_counts = {}
        all_fonts = []
        for sym, s_list in opt_spans.items():
            fonts = [s["font"] for s in s_list if s["text"].strip()]
            font_counts[sym] = Counter(fonts)
            all_fonts.extend(fonts)
            print(f"  보기 {sym}: {dict(font_counts[sym])} | 텍스트: {' '.join([s['text'] for s in s_list])}")
            
        # 전체 폰트 빈도 계산
        total_font_counter = Counter(all_fonts)
        # 폰트명 중 가장 드물게 쓰인 폰트(소수 폰트, 즉 Bold 폰트)가 있는 보기를 정답으로 판별
        # 단, 다수 폰트가 다량 존재하는 상황에서 소수 폰트가 1개 보기에서만 주되게 사용되었는지 확인
        inferred_answer = None
        
        # 폰트 종류가 2개 이상일 때 작동
        if len(total_font_counter) >= 2:
            # 가장 많이 쓰인 폰트(일반 폰트)와 적게 쓰인 폰트(Bold 폰트) 구분
            most_common_font = total_font_counter.most_common(1)[0][0]
            # most_common_font가 아닌 다른 폰트(소수 폰트)가 포함된 보기를 찾음
            candidates = []
            for sym, counts in font_counts.items():
                # 일반 폰트 외에 다른 폰트가 있는지 검사
                has_minority_font = any(f != most_common_font for f in counts)
                if has_minority_font:
                    candidates.append(sym)
            if len(candidates) == 1:
                inferred_answer = candidates[0]
                print(f"  => 판정 정답: {inferred_answer} (이유: 일반 폰트 '{most_common_font}' 외의 특이 폰트 검출)")
            else:
                print(f"  => 판정 불가 (소수 폰트 후보들: {candidates})")
        else:
            print("  => 판정 불가 (폰트가 1종류만 사용됨)")

if __name__ == "__main__":
    analyze_fonts()
