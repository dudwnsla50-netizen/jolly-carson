# -*- coding: utf-8 -*-
"""
[Phase 2 최종 개선판(v3): 정밀 정답 추출 및 자동 보정]
- 작성자: Antigravity
- 설계 목적:
  1. image_cropper.py와 동일한 PDF 상의 crop_rect를 복원하여 오프셋 오차를 원천 차단합니다.
  2. 실제 저장된 이미지 크기와 PDF 상 크기를 대조하여 동적으로 scale을 계산하므로 스케일 변화에 유연하게 대응합니다.
  3. 한 행에 보기 기호가 뭉쳐서 하나의 스팬으로 나오는 경우(예: ① 가. 나  ② 가, 나, 라), 
     글자 인덱스 기반 비례 배분 방식으로 보기 기호 각각의 Bounding Box를 정밀 유추합니다.
  4. 이미지 분석 시 계산된 픽셀 오프셋 영역에 핀포인트로 접근하여 볼드체 여부를 확실하게 판별합니다.
"""
import fitz
import os
import re
import sys
import io
import json
import sqlite3
from PIL import Image

# Windows 콘솔 한글 깨짐 방지
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")
PDF_DIR = os.path.join(BASE_DIR, "data", "past_exams")
IMG_DIR = os.path.join(BASE_DIR, "reports", "images")

# 보기 기호 및 정답 매핑
SYM_MAP = {
    "①": 1, "②": 2, "③": 3, "④": 4,
    "❶": 1, "❷": 2, "❸": 3, "❹": 4,
    "➀": 1, "➁": 2, "➂": 3, "➃": 4,
}
SYM_REGEX = r'[①②③④❶❷❸❹➀➁➂➃]'

def get_pdf_file_for_year(year):
    """연도에 해당하는 PDF 파일 경로 반환"""
    try:
        files = os.listdir(PDF_DIR)
        for f in files:
            if f.endswith(".pdf") and f.startswith(str(year)) and "답안표" not in f:
                return os.path.join(PDF_DIR, f)
    except Exception as e:
        print(f"  [오류] PDF 디렉토리 탐색 실패: {e}")
    return None

def get_subject_for_qnum(year, q_num):
    """문제 번호별 과목 코드 매핑"""
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

def get_pdf_crop_rect(doc, year, subject_code, q_num):
    """
    image_cropper.py 의 좌표 산출 방식을 모사하여
    실제 크롭 시 사용한 PDF 상의 정확한 crop_rect 바운더리를 구합니다.
    """
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
                        
    # 2단계: 정합성 필터링
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
        return None, None

    pos = unique_positions[q_num]
    page_idx = pos["page_idx"]
    page = doc[page_idx]
    height = page.rect.height
    
    # 다음 문항 찾기
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
        
    # ④번 보기 하단 경계 보정
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
        
    return page, crop_rect

def parse_inline_option_symbols(span):
    """
    [핵심 논리]
    하나의 텍스트 스팬 내에 여러 보기 기호가 뭉쳐 있는 경우,
    텍스트 오프셋 비율을 기반으로 각 보기 기호의 Bounding Box를 나누어 반환합니다.
    """
    text = span["text"]
    bbox = fitz.Rect(span["bbox"])
    matches = list(re.finditer(SYM_REGEX, text))
    if not matches:
        return []
        
    results = []
    L = len(text)
    W = bbox.x1 - bbox.x0
    
    for match in matches:
        sym = match.group(0)
        idx = match.start()
        # 글자 인덱스를 기준으로 Bounding Box의 추정 x좌표 산출
        x0_est = bbox.x0 + W * (idx / L)
        x1_est = bbox.x0 + W * ((idx + 1) / L)
        
        # 실제 보기 기호 주변 1~2글자 수준의 좁은 영역만 지정
        results.append({
            "sym": sym,
            "bbox": fitz.Rect(x0_est, bbox.y0, x1_est, bbox.y1),
            "font": span.get("font", ""),
            "flags": span.get("flags", 0)
        })
    return results

def detect_answer_by_image_v3(year, q_num, page, pdf_crop_rect):
    """
    실제 크롭된 이미지와 PDF 상의 crop_rect를 기반으로 
    각 보기 기호 패치 영역을 정밀하게 추출하고 이미지 밀도를 통해 볼드체(정답)를 탐색합니다.
    """
    img_path = os.path.join(IMG_DIR, f"{year}_{q_num}.png")
    if not os.path.exists(img_path):
        return None

    try:
        img = Image.open(img_path).convert("L")
        img_w, img_h = img.size
    except Exception as e:
        print(f"    [오류] 이미지 로드 실패 ({year}_{q_num}): {e}")
        return None

    # 동적 스케일 비율 계산
    pdf_w = pdf_crop_rect.width
    pdf_h = pdf_crop_rect.height
    scale_x = img_w / pdf_w
    scale_y = img_h / pdf_h
    scale = (scale_x + scale_y) / 2

    # 스케일 검증: 비정상적인 종횡비 어긋남 방지
    if abs(scale_x - scale_y) > 0.5:
        # 세로만 잘린 이미지인 경우, 가로 스케일을 기준 삼음
        scale = scale_x

    text_page = page.get_text("dict")
    option_symbols = []
    
    # PDF 상 검색 영역 확장 (여유 마진)
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
                    # 인라인 보기 기호 파싱 및 수집
                    inlines = parse_inline_option_symbols(span)
                    option_symbols.extend(inlines)

    if len(option_symbols) < 4:
        # 감지된 보기 기호가 부족하면 정답 유추 불가
        return None

    results = []
    for opt in option_symbols:
        sym_key = SYM_MAP.get(opt["sym"])
        if not sym_key:
            continue
        bbox = fitz.Rect(opt["bbox"])
        
        # 동적 스케일 기반 픽셀 좌표 환산 (핀포인트 패치)
        px_x0 = int((bbox.x0 - pdf_crop_rect.x0) * scale) - 2
        px_y0 = int((bbox.y0 - pdf_crop_rect.y0) * scale) - 2
        px_x1 = int((bbox.x1 - pdf_crop_rect.x0) * scale) + 2
        px_y1 = int((bbox.y1 - pdf_crop_rect.y0) * scale) + 2
        
        # 이미지 경계 조절
        px_x0 = max(0, min(img_w - 1, px_x0))
        px_y0 = max(0, min(img_h - 1, px_y0))
        px_x1 = max(px_x0 + 1, min(img_w, px_x1))
        px_y1 = max(px_y0 + 1, min(img_h, px_y1))
        
        # 패치 크롭 및 어두운 영역(볼드 획) 비율 계산
        patch = img.crop((px_x0, px_y0, px_x1, px_y1))
        pixels = list(patch.getdata())
        total_pixels = len(pixels)
        if total_pixels == 0:
            continue
            
        mean_darkness = 255 - (sum(pixels) / total_pixels)
        # 150 이하의 픽셀을 글자 획(어두운 영역)으로 간주
        dark_pixels = sum(1 for p in pixels if p < 150)
        dark_ratio = dark_pixels / total_pixels
        
        results.append({
            "num": sym_key,
            "sym": opt["sym"],
            "mean_darkness": mean_darkness,
            "dark_ratio": dark_ratio,
        })

    # 중복 감지 제거 (동일 기호가 있을 시 최대값 기준 필터링)
    best_by_num = {}
    for r in results:
        n = r["num"]
        if n not in best_by_num or r["dark_ratio"] > best_by_num[n]["dark_ratio"]:
            best_by_num[n] = r
    
    results = list(best_by_num.values())
    if len(results) < 4:
        return None

    # 정렬 및 판정 (가장 어두운 픽셀 비율이 높은 순)
    results.sort(key=lambda x: x["dark_ratio"], reverse=True)
    best = results[0]
    second = results[1]

    # 판정 임계값: 가장 어두운 보기가 최소 1.5% 이상의 글자 획 비율을 가지며,
    # 2위 보기 대비 최소 8% 이상의 비율 차이(상대적 볼드도)를 가져야 함
    if best["dark_ratio"] > 0.015:
        if second["dark_ratio"] == 0:
            return best["num"]
        ratio_diff = (best["dark_ratio"] - second["dark_ratio"]) / second["dark_ratio"]
        if ratio_diff > 0.08:
            return best["num"]

    # 백업 판정: mean_darkness 기준 비교
    results.sort(key=lambda x: x["mean_darkness"], reverse=True)
    best = results[0]
    second = results[1]
    if best["mean_darkness"] > 2.0:
        if second["mean_darkness"] == 0:
            return best["num"]
        ratio_diff = (best["mean_darkness"] - second["mean_darkness"]) / second["mean_darkness"]
        if ratio_diff > 0.08:
            return best["num"]

    return None

def main():
    print("=" * 70)
    print("[Phase 2 v3] 동적 스케일 및 핀포인트 픽셀 분석 기반 정답 추가 복원")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 이미 정답이 들어있는 것은 건드리지 않고 누락된 문항만 수집
    c.execute("""SELECT id, year, question_num FROM exam_questions 
                 WHERE answer IS NULL OR answer = '' OR answer = '[]'
                 ORDER BY year, question_num""")
    missing = c.fetchall()
    print(f"  복원 대상 문항: {len(missing)}건")

    by_year = {}
    for q_id, year, q_num in missing:
        by_year.setdefault(year, []).append((q_id, q_num))

    total_success = 0
    total_failed = 0

    for year in sorted(by_year.keys()):
        pdf_path = get_pdf_file_for_year(year)
        if not pdf_path:
            total_failed += len(by_year[year])
            print(f"  [{year}년] 실패: PDF 파일을 찾을 수 없습니다.")
            continue

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            total_failed += len(by_year[year])
            print(f"  [{year}년] 실패: PDF 로드 예외 ({e})")
            continue

        year_success = 0
        year_failed = 0

        for q_id, q_num in sorted(by_year[year], key=lambda x: x[1]):
            subject = get_subject_for_qnum(year, q_num)
            page, pdf_crop_rect = get_pdf_crop_rect(doc, year, subject, q_num)
            if not page or not pdf_crop_rect:
                year_failed += 1
                continue

            inferred_answer = detect_answer_by_image_v3(year, q_num, page, pdf_crop_rect)
            
            if inferred_answer:
                # 단일 정답 JSON 포맷 저장
                ans_json = json.dumps([inferred_answer])
                c.execute("UPDATE exam_questions SET answer = ? WHERE id = ?", (ans_json, q_id))
                year_success += 1
            else:
                year_failed += 1

        conn.commit()
        doc.close()
        total_success += year_success
        total_failed += year_failed
        print(f"  [{year}년] 복원 성공: {year_success}건 / 실패: {year_failed}건")

    conn.close()
    print(f"\n  [최종 복원 결과] 신규 복원: {total_success}건 / 복원 불가: {total_failed}건")

    # DB의 현재 누락 상태 상세 요약 출력
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM exam_questions")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM exam_questions WHERE answer IS NULL OR answer = '' OR answer = '[]'")
    still_missing = c.fetchone()[0]
    filled = total - still_missing
    print(f"\n  [최종 현황] 전체 {total}건 중 정답 완료 {filled}건 ({filled/total*100:.1f}%)")
    print(f"  여전히 누락: {still_missing}건")
    conn.close()

if __name__ == "__main__":
    main()
