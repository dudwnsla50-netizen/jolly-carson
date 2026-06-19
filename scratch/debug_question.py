# -*- coding: utf-8 -*-
"""
[개선된 정답 추출 디버그 스크립트 - v3]
- 목적: 실제 크롭된 이미지 크기와 PDF 상의 크롭 영역 크기를 대조하여 동적으로 스케일을 계산합니다.
- 동작 방식:
  1. image_cropper.py 의 좌표 산출 알고리즘을 사용해 실제 이미지 저장 시 쓰인 PDF 상의 crop_rect를 구합니다.
  2. 실제 이미지 크기를 읽어 scale = img_w / pdf_w 를 구합니다.
  3. 이 scale을 적용하여 보기 기호의 정확한 픽셀 위치를 크롭하고 밀도를 분석합니다.
"""
import fitz
import os
import re
import sys
import io
import sqlite3
from PIL import Image

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")
PDF_DIR = os.path.join(BASE_DIR, "data", "past_exams")
IMG_DIR = os.path.join(BASE_DIR, "reports", "images")

# 과목 코드 매핑 유틸리티
def get_subject_for_qnum(year, q_num):
    if year == 2015:
        if 1 <= q_num <= 25: return "PM"
        if 26 <= q_num <= 50: return "SE"
        if 51 <= q_num <= 75: return "DB"
        if 76 <= q_num <= 90: return "SA"
        if 91 <= q_num <= 105: return "SC"
    else:
        if 1 <= q_num <= 25: return "PM"
        if 26 <= q_num <= 50: return "SE"
        if 51 <= q_num <= 75: return "DB"
        if 76 <= q_num <= 100: return "SA"
        if 101 <= q_num <= 120: return "SC"
    return "PM"

# image_cropper.py 의 로직에 기반한 정확한 crop_rect 계산 함수
def get_pdf_crop_rect(doc, year, subject_code, q_num):
    import image_cropper
    s_range = image_cropper.get_subject_range(subject_code, year)
    q_start = s_range["start"]
    q_next_limit = s_range["next_limit"]
    
    found_positions = []
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
            blocks.sort(key=lambda x: x[1])
            
            for block in blocks:
                text = block[4].strip()
                match = re.match(r"^([1-9][0-9]*|1[0-9][0-9])[\.\)\s]", text)
                if match:
                    num = int(match.group(1))
                    if q_start <= num <= q_next_limit:
                        margin_threshold = 80.0 if b == 0 else (x0 + 30.0)
                        if block[0] > margin_threshold:
                            continue
                        found_positions.append({
                            "num": num,
                            "rect": fitz.Rect(block[0], block[1], block[2], block[3]),
                            "page_idx": page_idx,
                            "band_idx": b,
                            "x0": x0,
                            "x1": x1
                        })
                        
    # 정렬 및 고유 위치 추출
    found_positions.sort(key=lambda x: (x["page_idx"], x["band_idx"], x["rect"].y0))
    candidates = {n: [] for n in range(q_start, q_next_limit + 1)}
    for pos in found_positions:
        candidates[pos["num"]].append(pos)
        
    unique_positions = {}
    prev_pos = None
    for n in range(q_start, q_next_limit + 1):
        opts = candidates.get(n, [])
        if not opts:
            continue
        if prev_pos is None:
            unique_positions[n] = opts[0]
            prev_pos = opts[0]
        else:
            best_opt = None
            for opt in opts:
                is_after = (
                    opt["page_idx"] > prev_pos["page_idx"] or
                    (opt["page_idx"] == prev_pos["page_idx"] and opt["band_idx"] > prev_pos["band_idx"]) or
                    (opt["page_idx"] == prev_pos["page_idx"] and opt["band_idx"] == prev_pos["band_idx"] and opt["rect"].y0 > prev_pos["rect"].y0)
                )
                if is_after:
                    best_opt = opt
                    break
            if best_opt:
                unique_positions[n] = best_opt
                prev_pos = best_opt
            else:
                unique_positions[n] = opts[0]
                prev_pos = opts[0]

    if q_num not in unique_positions:
        return None, None, None

    pos = unique_positions[q_num]
    page_idx = pos["page_idx"]
    page = doc[page_idx]
    height = page.rect.height
    
    next_pos = None
    sorted_keys = sorted(list(unique_positions.keys()))
    try:
        idx = sorted_keys.index(q_num)
        if idx + 1 < len(sorted_keys):
            next_pos = unique_positions[sorted_keys[idx + 1]]
    except:
        pass
        
    y_start = pos["rect"].y0 - 6
    y_end = height - 12
    if next_pos and next_pos["page_idx"] == page_idx and next_pos["band_idx"] == pos["band_idx"]:
        y_end = next_pos["rect"].y0 - 8
        
    q4_y1 = None
    clip_rect = fitz.Rect(pos["x0"], 0, pos["x1"], height)
    blocks = page.get_text("blocks", clip=clip_rect)
    blocks.sort(key=lambda x: x[1])
    for block in blocks:
        if block[1] >= y_start:
            if next_pos and next_pos["page_idx"] == page_idx and next_pos["band_idx"] == pos["band_idx"]:
                if block[1] >= next_pos["rect"].y0:
                    break
            block_text = block[4].strip()
            if "④" in block_text:
                q4_y1 = block[3]
                
    if q4_y1 is not None:
        q4_y_end = q4_y1 + 20
        if q4_y_end < y_end:
            y_end = q4_y_end
            
    crop_rect = fitz.Rect(pos["x0"], y_start, pos["x1"], y_end)
    if crop_rect.height < 40:
        crop_rect.y1 = crop_rect.y0 + 250
    if crop_rect.y1 > height:
        crop_rect.y1 = height
        
    return page, crop_rect, pos

def get_pdf_file_for_year(year):
    files = os.listdir(PDF_DIR)
    for f in files:
        if f.endswith(".pdf") and f.startswith(str(year)) and "답안표" not in f:
            return os.path.join(PDF_DIR, f)
    return None

SYM_MAP = {
    "①": 1, "②": 2, "③": 3, "④": 4,
    "❶": 1, "❷": 2, "❸": 3, "❹": 4,
    "➀": 1, "➁": 2, "➂": 3, "➃": 4,
}
SYM_REGEX = r'[①②③④❶❷❸❹➀➁➂➃]'

def debug_question_v3(year, q_num):
    print(f"\n=== Debugging v3 {year}년 {q_num}번 ===")
    pdf_path = get_pdf_file_for_year(year)
    if not pdf_path:
        print("PDF 없음")
        return
        
    doc = fitz.open(pdf_path)
    subject = get_subject_for_qnum(year, q_num)
    page, pdf_crop_rect, pos = get_pdf_crop_rect(doc, year, subject, q_num)
    if not page or not pdf_crop_rect:
        print("PDF에서 문항을 찾을 수 없음")
        doc.close()
        return
        
    print(f"PDF Page: {page.number}, Crop Rect: {pdf_crop_rect}")
    
    img_path = os.path.join(IMG_DIR, f"{year}_{q_num}.png")
    if not os.path.exists(img_path):
        print(f"이미지 없음: {img_path}")
        doc.close()
        return
        
    try:
        img = Image.open(img_path).convert("L")
        img_w, img_h = img.size
        print(f"실제 이미지 크기: {img_w}x{img_h}")
    except Exception as e:
        print(f"이미지 로딩 실패: {e}")
        doc.close()
        return
        
    # 동적 스케일 계산
    pdf_w = pdf_crop_rect.width
    pdf_h = pdf_crop_rect.height
    scale_x = img_w / pdf_w
    scale_y = img_h / pdf_h
    scale = (scale_x + scale_y) / 2
    print(f"동적 스케일 계산값: scale_x={scale_x:.3f}, scale_y={scale_y:.3f} -> scale={scale:.3f}")
    
    # 보기 기호 스팬 수집
    text_page = page.get_text("dict")
    option_symbols = []
    
    search_x0 = pdf_crop_rect.x0 - 10
    search_x1 = pdf_crop_rect.x1 + 10
    search_y0 = pdf_crop_rect.y0 - 10
    search_y1 = pdf_crop_rect.y1 + 10
    
    for block in text_page["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                sx0, sy0, sx1, sy1 = span["bbox"]
                if search_x0 <= sx0 <= search_x1 and search_y0 <= sy0 <= search_y1:
                    text = span["text"].strip()
                    match = re.search(SYM_REGEX, text)
                    if match:
                        option_symbols.append({
                            "sym": match.group(0),
                            "bbox": span["bbox"],
                            "text": text,
                        })
                        
    print(f"감지된 보기 기호 개수: {len(option_symbols)}")
    
    results = []
    for opt in option_symbols:
        sym_key = SYM_MAP.get(opt["sym"])
        bbox = fitz.Rect(opt["bbox"])
        
        # 동적 스케일을 반영하여 픽셀 좌표 계산
        px_x0 = int((bbox.x0 - pdf_crop_rect.x0) * scale) - 2
        px_y0 = int((bbox.y0 - pdf_crop_rect.y0) * scale) - 2
        px_x1 = int((bbox.x1 - pdf_crop_rect.x0) * scale) + 2
        px_y1 = int((bbox.y1 - pdf_crop_rect.y0) * scale) + 2
        
        # 이미지 경계 조절
        px_x0 = max(0, min(img_w - 1, px_x0))
        px_y0 = max(0, min(img_h - 1, px_y0))
        px_x1 = max(px_x0 + 1, min(img_w, px_x1))
        px_y1 = max(px_y0 + 1, min(img_h, px_y1))
        
        patch = img.crop((px_x0, px_y0, px_x1, px_y1))
        pixels = list(patch.getdata())
        total_pixels = len(pixels)
        if total_pixels == 0:
            continue
            
        mean_darkness = 255 - (sum(pixels) / total_pixels)
        dark_pixels = sum(1 for p in pixels if p < 150)
        dark_ratio = dark_pixels / total_pixels
        
        results.append({
            "num": sym_key,
            "sym": opt["sym"],
            "text": opt["text"],
            "mean_darkness": mean_darkness,
            "dark_ratio": dark_ratio,
            "bbox_px": (px_x0, px_y0, px_x1, px_y1)
        })
        
    print("스케일 보정 후 밀도 분석 결과:")
    for r in results:
        print(f"  보기 {r['num']}({r['sym']}): {repr(r['text'])} | mean_darkness={r['mean_darkness']:.3f}, dark_ratio={r['dark_ratio']:.3f}, bbox_px={r['bbox_px']}")

    doc.close()

if __name__ == "__main__":
    debug_question_v3(2025, 1)
    debug_question_v3(2015, 115)
