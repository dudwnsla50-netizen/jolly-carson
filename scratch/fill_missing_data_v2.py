# -*- coding: utf-8 -*-
"""
[Phase 2 강화판: 정답 추출 개선]
- 보기 기호 검색 범위를 페이지 전체 → 근접 필터링 방식으로 변경
- 밀도 분석 임계값을 10% → 5%로 완화
- 보기 기호 패턴에 ➀➁➂➃ 추가
- 패치 크기를 키워 볼드 판정 정확도 향상
- 기존에 등록된 정답은 절대 건드리지 않음
"""
import fitz
import os
import re
import sys
import io
import json
import sqlite3
from collections import Counter
from PIL import Image

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")
PDF_DIR = os.path.join(BASE_DIR, "data", "past_exams")
IMG_DIR = os.path.join(BASE_DIR, "reports", "images")

# 확장된 보기 기호 매핑 (➀➁➂➃ 추가)
SYM_MAP = {
    "①": 1, "②": 2, "③": 3, "④": 4,
    "❶": 1, "❷": 2, "❸": 3, "❹": 4,
    "➀": 1, "➁": 2, "➂": 3, "➃": 4,
}
SYM_REGEX = r'[①②③④❶❷❸❹➀➁➂➃]'

BOLD_FONT_KEYWORDS = ["bold", "t12", "t18", "t19", "t21", "t22", "t23", "t24", "gothic-bold", "myeongjo-bold"]


def get_pdf_file_for_year(year):
    files = os.listdir(PDF_DIR)
    for f in files:
        if f.endswith(".pdf") and f.startswith(str(year)) and "답안표" not in f:
            return os.path.join(PDF_DIR, f)
    return None


def find_question_in_pdf_enhanced(doc, q_num):
    """
    [개선] 문항 영역 탐색 - crop_rect의 y1을 더 넓게 잡아 보기 영역을 포함시킵니다.
    """
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
                if re.match(rf"^{q_num}[\.)\s]", text):
                    # y1을 다음 문항까지 또는 페이지 끝까지 확장
                    target_rect = fitz.Rect(block[0], block[1], block[2], height)
                    
                    # 다음 문항 번호로 y1 제한 (넉넉하게 +10 마진)
                    for block_next in blocks:
                        next_text = block_next[4].strip()
                        if re.match(rf"^{q_num + 1}[\.)\s]", next_text):
                            target_rect.y1 = block_next[1] + 10  # 기존 -5 → +10으로 완화
                            break
                    
                    return page, target_rect
    return None, None


def collect_option_spans_enhanced(page, crop_rect):
    """
    [개선] 보기 기호 스팬을 수집합니다.
    - crop_rect 범위를 좌우로 ±15, 상하로 ±20 확장하여 검색
    - ➀➁➂➃ 패턴도 인식
    """
    text_page = page.get_text("dict")
    option_symbols = []
    all_spans_in_rect = []
    
    # 확장된 검색 범위
    search_x0 = crop_rect.x0 - 15
    search_x1 = crop_rect.x1 + 15
    search_y0 = crop_rect.y0 - 20
    search_y1 = crop_rect.y1 + 20
    
    for block in text_page["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                sx0, sy0, sx1, sy1 = span["bbox"]
                # 확장된 범위 내 스팬만 수집
                if search_x0 <= sx0 <= search_x1 and search_y0 <= sy0 <= search_y1:
                    all_spans_in_rect.append(span)
                    text = span["text"].strip()
                    match = re.search(SYM_REGEX, text)
                    if match:
                        option_symbols.append({
                            "sym": match.group(0),
                            "bbox": span["bbox"],
                            "font": span.get("font", ""),
                        })
    
    return option_symbols, all_spans_in_rect


def detect_answer_by_image_enhanced(year, q_num, page, crop_rect, option_symbols):
    """
    [개선된 이미지 밀도 분석]
    - 패치 크기를 기호 높이의 1.5배로 확대하여 글자 획 포함
    - 임계값을 5%로 완화
    - 밀도 분석 시 중앙값(median) 기반 추가 비교
    """
    img_path = os.path.join(IMG_DIR, f"{year}_{q_num}.png")
    if not os.path.exists(img_path):
        return None

    try:
        img = Image.open(img_path).convert("L")
        img_w, img_h = img.size
    except:
        return None

    width = page.rect.width
    height = page.rect.height
    bands_count = 4 if width > height else 2
    band_width = width / bands_count
    q_x_center = (crop_rect.x0 + crop_rect.x1) / 2
    band_idx = int(q_x_center / band_width)
    band_x0 = band_width * band_idx

    results = []
    scale = 2.2

    for opt in option_symbols:
        sym_key = SYM_MAP.get(opt["sym"])
        if not sym_key:
            continue
            
        bbox = fitz.Rect(opt["bbox"])

        # [개선] 패치를 더 넓게 잡아 글자 획까지 포함
        span_height = abs(bbox.y1 - bbox.y0)
        patch_size = int(span_height * scale * 1.5)  # 기존 1.0 → 1.5배

        px_x0 = int((bbox.x0 - band_x0) * scale) - 8
        px_y0 = int((bbox.y0 - crop_rect.y0) * scale) - 8
        px_x1 = px_x0 + patch_size + 16
        px_y1 = int((bbox.y1 - crop_rect.y0) * scale) + 8

        # 경계 제한
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
        
        # 어두운 픽셀 비율 (140 이하를 어두운 픽셀로 판정)
        dark_pixels = sum(1 for p in pixels if p < 140)
        dark_ratio = dark_pixels / total_pixels
        
        results.append({
            "sym": opt["sym"],
            "num": sym_key,
            "mean_darkness": mean_darkness,
            "dark_ratio": dark_ratio,
        })

    if len(results) < 4:
        return None

    # 중복 기호 제거 (같은 번호가 여러 번 검출된 경우 최대값 사용)
    best_by_num = {}
    for r in results:
        n = r["num"]
        if n not in best_by_num or r["dark_ratio"] > best_by_num[n]["dark_ratio"]:
            best_by_num[n] = r
    
    results = list(best_by_num.values())
    if len(results) < 4:
        return None

    # dark_ratio 기준 정렬 (어두운 픽셀 비율이 높을수록 볼드)
    results.sort(key=lambda x: x["dark_ratio"], reverse=True)
    best = results[0]
    second = results[1]

    # [완화] 임계값 5%
    if best["dark_ratio"] > 0.01:
        if second["dark_ratio"] == 0:
            return best["num"]
        ratio_diff = (best["dark_ratio"] - second["dark_ratio"]) / second["dark_ratio"]
        if ratio_diff > 0.05:  # 5%로 완화
            return best["num"]

    # mean_darkness 기준 추가 시도
    results.sort(key=lambda x: x["mean_darkness"], reverse=True)
    best = results[0]
    second = results[1]

    if best["mean_darkness"] > 1.0:
        if second["mean_darkness"] == 0:
            return best["num"]
        ratio_diff = (best["mean_darkness"] - second["mean_darkness"]) / second["mean_darkness"]
        if ratio_diff > 0.05:
            return best["num"]

    return None


def detect_answer_by_font(option_symbols, all_spans, crop_rect):
    """
    [폰트 메타데이터 기반 정답 유추 - 모든 연도 대상]
    동일 문항의 보기별 폰트 사용 패턴이 다른 경우 소수 폰트 사용 보기를 정답으로 유추합니다.
    """
    if len(option_symbols) < 4:
        return None
    
    # 보기 기호별 y좌표 범위 매핑
    opt_ranges = {}
    for opt in option_symbols:
        sym = opt["sym"]
        num = SYM_MAP.get(sym)
        if not num or num in opt_ranges:
            continue
        x_limit = 9999.0
        for other in option_symbols:
            other_num = SYM_MAP.get(other["sym"])
            if other_num != num and abs(other["bbox"][1] - opt["bbox"][1]) < 5 and other["bbox"][0] > opt["bbox"][0]:
                x_limit = min(x_limit, other["bbox"][0] - 2)
        opt_ranges[num] = {"y": opt["bbox"][1], "x_min": opt["bbox"][0] - 2, "x_max": x_limit}

    # 보기별 스팬 할당
    opt_spans = {n: [] for n in opt_ranges}
    for span in all_spans:
        if not span["text"].strip():
            continue
        matched_num = None
        min_y_diff = 8.0  # 완화: 5 → 8
        for num, r in opt_ranges.items():
            y_diff = abs(span["bbox"][1] - r["y"])
            if y_diff < min_y_diff and r["x_min"] <= span["bbox"][0] <= r["x_max"]:
                matched_num = num
                min_y_diff = y_diff
        if matched_num:
            opt_spans[matched_num].append(span)

    # 폰트 분석
    font_counts = {}
    all_fonts = []
    for num in [1, 2, 3, 4]:
        s_list = opt_spans.get(num, [])
        fonts = [s["font"] for s in s_list]
        font_counts[num] = Counter(fonts)
        all_fonts.extend(fonts)

    total_counter = Counter(all_fonts)

    # Bold 폰트 키워드 매칭
    bold_candidates = []
    for num, counts in font_counts.items():
        bold_score = sum(c for f, c in counts.items() if any(kw in f.lower() for kw in BOLD_FONT_KEYWORDS))
        if bold_score > 0:
            bold_candidates.append((num, bold_score))

    if bold_candidates:
        bold_candidates.sort(key=lambda x: x[1], reverse=True)
        return bold_candidates[0][0]

    # 소수 폰트 사용 보기 판별
    if len(total_counter) >= 2:
        most_common_font = total_counter.most_common(1)[0][0]
        minority = []
        for num, counts in font_counts.items():
            non_common = sum(c for f, c in counts.items() if f != most_common_font)
            if non_common > 0:
                minority.append((num, non_common))
        if len(minority) == 1:
            return minority[0][0]

    return None


def main():
    print("=" * 70)
    print("[Phase 2 강화판] 정답 누락 추가 보정")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # answer가 아직 NULL인 레코드만
    c.execute("""SELECT id, year, question_num FROM exam_questions 
                 WHERE answer IS NULL OR answer = '' OR answer = '[]'
                 ORDER BY year, question_num""")
    missing = c.fetchall()
    print(f"  대상: {len(missing)}건")

    by_year = {}
    for q_id, year, q_num in missing:
        by_year.setdefault(year, []).append((q_id, q_num))

    total_success = 0
    total_failed = 0

    for year in sorted(by_year.keys()):
        pdf_path = get_pdf_file_for_year(year)
        if not pdf_path:
            total_failed += len(by_year[year])
            continue

        try:
            doc = fitz.open(pdf_path)
        except:
            total_failed += len(by_year[year])
            continue

        year_success = 0
        year_failed = 0

        for q_id, q_num in sorted(by_year[year], key=lambda x: x[1]):
            page, crop_rect = find_question_in_pdf_enhanced(doc, q_num)
            if not page or not crop_rect:
                year_failed += 1
                continue

            # 보기 기호 수집 (확장 범위)
            option_symbols, all_spans = collect_option_spans_enhanced(page, crop_rect)

            inferred_answer = None

            # 1차: 폰트 분석 (모든 연도 대상)
            if len(option_symbols) >= 4:
                inferred_answer = detect_answer_by_font(option_symbols, all_spans, crop_rect)

            # 2차: 이미지 밀도 분석 (확장 기호 사용)
            if not inferred_answer and len(option_symbols) >= 4:
                inferred_answer = detect_answer_by_image_enhanced(
                    year, q_num, page, crop_rect, option_symbols
                )

            if inferred_answer:
                ans_json = json.dumps([inferred_answer])
                c.execute("UPDATE exam_questions SET answer = ? WHERE id = ?", (ans_json, q_id))
                year_success += 1
            else:
                year_failed += 1

        conn.commit()
        doc.close()
        total_success += year_success
        total_failed += year_failed
        print(f"  [{year}년] 성공: {year_success} / 실패: {year_failed}")

    conn.close()
    print(f"\n  [결과] 추가 보정: {total_success}건 / 실패: {total_failed}건")

    # 최종 통계
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM exam_questions")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM exam_questions WHERE answer IS NULL OR answer = '' OR answer = '[]'")
    still_missing = c.fetchone()[0]
    filled = total - still_missing
    print(f"\n  [최종 현황] 전체 {total}건 중 정답 {filled}건 ({filled/total*100:.1f}%)")
    print(f"  여전히 누락: {still_missing}건")
    
    # 연도별 현황
    c.execute("""SELECT year, COUNT(*),
                 SUM(CASE WHEN answer IS NULL OR answer = '' OR answer = '[]' THEN 1 ELSE 0 END)
                 FROM exam_questions GROUP BY year ORDER BY year""")
    for row in c.fetchall():
        filled_y = row[1] - row[2]
        pct = filled_y / row[1] * 100
        print(f"    {row[0]}년: {filled_y}/{row[1]} ({pct:.0f}%)")
    
    conn.close()


if __name__ == "__main__":
    main()
