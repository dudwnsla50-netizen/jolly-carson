# -*- coding: utf-8 -*-
"""
[이미지 기반 볼드체 감지 테스트]
- 작성자: Antigravity
- 설계 목적: 2015년 51번 문제의 보기 기호 영역을 이미지상에서 크롭하여 어두운 픽셀 밀도를 비교하고 정답을 판별합니다.
"""
import fitz
import os
import re
import sys
from PIL import Image

# Windows 콘솔 인코딩 에러 방지
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "data", "past_exams", "2024년(제25회) 감리사 자격검정 필기시험 문제-A형.pdf")
IMG_PATH = os.path.join(BASE_DIR, "reports", "images", "2024_51.png")

def test_detection():
    # 1. 2015년 51번 문제의 위치 찾기 (image_cropper 로직 재현)
    doc = fitz.open(PDF_PATH)
    # 51번 문제 찾기
    q_num = 51
    found_page = None
    found_block = None
    width = 0
    height = 0
    bands_count = 2 # 세로형 2단 분할
    
    for page_idx, page in enumerate(doc):
        if page_idx == 0:
            continue
        width = page.rect.width
        height = page.rect.height
        
        # 51번은 1단(왼쪽) 혹은 2단(오른쪽)에 있을 것임
        for b in range(bands_count):
            x0 = (width / bands_count) * b
            x1 = (width / bands_count) * (b + 1)
            clip_rect = fitz.Rect(x0, 0, x1, height)
            blocks = page.get_text("blocks", clip=clip_rect)
            for block in blocks:
                text = block[4].strip()
                if re.match(rf"^{q_num}[\.\)\s]", text):
                    found_block = block
                    found_page = page
                    band_idx = b
                    bx0, bx1 = x0, x1
                    break
            if found_block:
                break
        if found_block:
            break
            
    if not found_block:
        print("51번 문항을 찾을 수 없습니다.")
        doc.close()
        return
        
    page = found_page
    print(f"51번 문항 발견: Page {page.number + 1}")
            
    if not found_block:
        print("51번 문항을 찾을 수 없습니다.")
        doc.close()
        return
        
    y_start = found_block[1] - 6
    
    # 다음 문항 찾기 (52번)
    y_end = height - 12
    for block in blocks:
        text = block[4].strip()
        if text.startswith("52.") and block[1] > y_start:
            y_end = block[1] - 8
            break
            
    crop_rect = fitz.Rect(bx0, y_start, bx1, y_end)
    print(f"PDF 상의 crop_rect: {crop_rect}")
    
    # 2. 이미지 로드 및 그레이스케일 변환
    if not os.path.exists(IMG_PATH):
        print(f"이미지가 없습니다: {IMG_PATH}")
        doc.close()
        return
        
    img = Image.open(IMG_PATH).convert("L")
    img_w, img_h = img.size
    print(f"크롭 이미지 크기: {img_w}x{img_h}")
    
    # 3. 해당 문제 안의 보기 기호 ①~④ 스팬 찾기
    text_page = page.get_text("dict")
    spans = []
    for block in text_page["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                span_rect = fitz.Rect(span["bbox"])
                # 51번 문항 영역 내에 포함되는지 확인
                if (crop_rect.x0 - 5 <= span_rect.x0 <= crop_rect.x1 + 5 and
                    crop_rect.y0 - 5 <= span_rect.y0 <= crop_rect.y1 + 5):
                    spans.append(span)
                    
    # 보기 기호 스팬만 선별
    option_symbols = []
    for span in spans:
        text = span["text"].strip()
        match = re.search(r'([①②③④❶❷❸❹])', text)
        if match:
            sym = match.group(1)
            option_symbols.append({
                "sym": sym,
                "bbox": span["bbox"]
            })
            
    # 매핑 기호 정규화
    map_sym = {"❶": "①", "❷": "②", "❸": "③", "❹": "④"}
    
    # 4. 보기별 이미지 영역 계산 및 어두운 픽셀 강도 분석
    print("\n--- 보기 기호 영역 이미지 픽셀 분석 ---")
    results = []
    scale = 2.2 # 기존 캐시 이미지들은 2.2 배율로 렌더링됨
    
    for opt in option_symbols:
        sym = opt["sym"]
        normalized_sym = map_sym.get(sym, sym)
        bbox = fitz.Rect(opt["bbox"])
        
        # 이미지 상의 픽셀 좌표로 변환 (마진을 넉넉히 주어 글자가 완전히 들어가도록 함)
        px_x0 = int((bbox.x0 - crop_rect.x0) * scale) - 12
        px_y0 = int((bbox.y0 - crop_rect.y0) * scale) - 12
        
        # 보기 기호 1글자의 너비는 대략 높이(bbox.y1 - bbox.y0)와 유사함
        span_height = bbox.y1 - bbox.y0
        px_x1 = px_x0 + int(span_height * scale) + 24
        px_y1 = int((bbox.y1 - crop_rect.y0) * scale) + 12
        
        # 바운더리 체크
        px_x0 = max(0, px_x0)
        px_y0 = max(0, px_y0)
        px_x1 = min(img_w, px_x1)
        px_y1 = min(img_h, px_y1)
        
        # 패치 이미지 자르기
        patch = img.crop((px_x0, px_y0, px_x1, px_y1))
        
        # 어두운 픽셀 밀도 계산
        threshold = 220 # 글자 영역을 잡기 위해 threshold 상향 조정 (배경은 255에 가까운 흰색이므로 안전)
        pixels = list(patch.getdata())
        dark_pixels = sum(1 for p in pixels if p < threshold)
        total_pixels = len(pixels)
        dark_ratio = dark_pixels / total_pixels if total_pixels > 0 else 0
        mean_darkness = 255 - (sum(pixels) / total_pixels) if total_pixels > 0 else 0
        
        results.append({
            "sym": normalized_sym,
            "dark_pixels": dark_pixels,
            "dark_ratio": dark_ratio,
            "mean_darkness": mean_darkness,
            "px_box": (px_x0, px_y0, px_x1, px_y1)
        })
        
        print(f"보기 {normalized_sym}:")
        print(f"  픽셀 범위: {px_x0},{px_y0} -> {px_x1},{px_y1} (크기: {px_x1-px_x0}x{px_y1-px_y0})")
        print(f"  어두운 픽셀 개수: {dark_pixels} / 전체 {total_pixels} (비율: {dark_ratio:.3f})")
        print(f"  평균 어두움 강도: {mean_darkness:.2f}")
        
    doc.close()
    
    # 5. 정답 판별
    if results:
        # 평균 어두움 강도가 가장 높은 것을 선택
        results.sort(key=lambda x: x["mean_darkness"], reverse=True)
        best = results[0]
        print(f"\n===> 판정 정답: {best['sym']} (이유: 가장 높은 어두움 강도 {best['mean_darkness']:.2f})")

if __name__ == "__main__":
    test_detection()
