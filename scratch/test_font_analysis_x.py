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
PDF_PATH = os.path.join(BASE_DIR, "data", "past_exams", "2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf")

# Bold로 간주하는 폰트명 패턴
BOLD_FONT_KEYWORDS = ["bold", "t12", "t18", "t19", "t21", "t22", "t23", "t24", "gothic-bold", "myeongjo-bold"]

def get_inferred_answer(font_counts, total_font_counter):
    """
    보기별 폰트 카운트를 분석하여 정답을 유추합니다.
    """
    # 1. 폰트명 자체에 'bold' 키워드가 들어있거나 미리 정의된 BOLD 폰트를 많이 가진 보기가 있는지 확인
    bold_candidates = []
    for sym, counts in font_counts.items():
        bold_score = 0
        for font_name, count in counts.items():
            fn_lower = font_name.lower()
            if any(kw in fn_lower for kw in BOLD_FONT_KEYWORDS):
                bold_score += count
        if bold_score > 0:
            bold_candidates.append((sym, bold_score))
            
    if bold_candidates:
        # 가장 bold 스코어가 높은 보기를 선택
        bold_candidates.sort(key=lambda x: x[1], reverse=True)
        return bold_candidates[0][0]
        
    # 2. 만약 폰트명에 직접적인 키워드가 없는 경우, 전체 폰트 분포를 비교하여 소수 폰트 검출
    if len(total_font_counter) >= 2:
        most_common_font = total_font_counter.most_common(1)[0][0]
        minority_candidates = []
        for sym, counts in font_counts.items():
            # 다수 폰트가 아닌 다른 폰트가 쓰인 비율이 높은가?
            non_common_count = sum(c for f, c in counts.items() if f != most_common_font)
            if non_common_count > 0:
                minority_candidates.append((sym, non_common_count))
        if len(minority_candidates) == 1:
            return minority_candidates[0][0]
            
    return None

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
                        
        # 3. 보기 기호 스팬 찾기 및 정렬
        option_symbols = []
        for span in spans:
            text = span["text"].strip()
            match = re.search(r'([①②③④❶❷❸❹])', text)
            if match:
                sym = match.group(1)
                option_symbols.append({
                    "sym": sym,
                    "bbox": span["bbox"],
                    "y": span["bbox"][1],
                    "x": span["bbox"][0]
                })
                
        # 보기 기호를 y좌표 기준 정렬 후 x좌표 정렬
        option_symbols.sort(key=lambda x: (x["y"], x["x"]))
        
        # 보기별 배정할 영역(y 범위 및 x 범위) 정의
        # 같은 y 라인에 여러 보기가 있을 때 가로 분리 경계 정의
        opt_ranges = {}
        for i, opt in enumerate(option_symbols):
            sym = opt["sym"]
            y_val = opt["y"]
            x_val = opt["x"]
            
            # 같은 행(y차가 5px 이내)에 다른 보기가 뒤에 오는지 검사
            x_limit = 9999.0
            for other_opt in option_symbols:
                if other_opt["sym"] != sym and abs(other_opt["y"] - y_val) < 5:
                    if other_opt["x"] > x_val:
                        # 다음 보기의 x 시작점의 조금 이전값을 경계로 삼음
                        x_limit = min(x_limit, other_opt["x"] - 2)
                        
            opt_ranges[sym] = {
                "y": y_val,
                "x_min": x_val - 2,
                "x_max": x_limit
            }
            
        # 4. 스팬들을 보기 매핑
        opt_spans = {opt["sym"]: [] for opt in option_symbols}
        for span in spans:
            span_text = span["text"].strip()
            if not span_text:
                continue
            span_y = span["bbox"][1]
            span_x = span["bbox"][0]
            
            # y좌표가 일치하는 행을 우선 매핑
            matched_sym = None
            min_y_diff = 5.0
            for sym, r in opt_ranges.items():
                y_diff = abs(span_y - r["y"])
                if y_diff < min_y_diff:
                    # x좌표 영역에 속하는지 검사
                    if r["x_min"] <= span_x <= r["x_max"]:
                        matched_sym = sym
                        min_y_diff = y_diff
            
            if matched_sym:
                opt_spans[matched_sym].append(span)
                
        # 5. 보기별 폰트 분포 확인
        print(f"\n[{q_num}번 문항 보기별 폰트 분석]")
        font_counts = {}
        all_fonts = []
        for sym in ["①", "②", "③", "④"]:
            s_list = opt_spans.get(sym, [])
            fonts = [s["font"] for s in s_list]
            font_counts[sym] = Counter(fonts)
            all_fonts.extend(fonts)
            print(f"  보기 {sym}: {dict(font_counts[sym])} | 텍스트: {' '.join([s['text'] for s in s_list])}")
            
        total_font_counter = Counter(all_fonts)
        inferred = get_inferred_answer(font_counts, total_font_counter)
        if inferred:
            sym_map = {"①": 1, "②": 2, "③": 3, "④": 4, "❶": 1, "❷": 2, "❸": 3, "❹": 4}
            print(f"  => 판정 정답: {inferred} ({sym_map[inferred]}번)")
        else:
            print("  => 판정 불가")

if __name__ == "__main__":
    analyze_fonts()
