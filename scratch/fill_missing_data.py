# -*- coding: utf-8 -*-
"""
[기출 DB 누락 데이터 통합 보정 스크립트]
- 설계 목적: options(보기)와 answer(정답)가 누락된 레코드를 PDF/이미지에서 추출하여 DB에 채웁니다.
- Phase 1: options 누락/불완전 보정 (PDF 텍스트 재파싱)
- Phase 2: answer 누락 보정 (이미지 밀도 분석 + 폰트 분석)
- Phase 3: 결과 검증 리포트 출력
- 안전 원칙: 기존에 이미 등록된 데이터는 절대 덮어쓰지 않습니다.
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

# Windows 콘솔 인코딩 에러 방지
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")
PDF_DIR = os.path.join(BASE_DIR, "data", "past_exams")
IMG_DIR = os.path.join(BASE_DIR, "reports", "images")

# 보기 기호 → 정답 번호 매핑
SYM_MAP = {"①": 1, "②": 2, "③": 3, "④": 4, "❶": 1, "❷": 2, "❸": 3, "❹": 4}

# 2025년용 Bold 판정 폰트명 키워드
BOLD_FONT_KEYWORDS = ["bold", "t12", "t18", "t19", "t21", "t22", "t23", "t24", "gothic-bold", "myeongjo-bold"]


# ======================================================================
# 공통 유틸리티
# ======================================================================

def get_pdf_file_for_year(year, want_answer_sheet=False):
    """연도별 PDF 파일 경로를 탐색합니다."""
    if not os.path.exists(PDF_DIR):
        return None
    files = os.listdir(PDF_DIR)
    if want_answer_sheet:
        for f in files:
            if f.endswith(".pdf") and f.startswith(str(year)) and "답안표" in f:
                return os.path.join(PDF_DIR, f)
    for f in files:
        if f.endswith(".pdf") and f.startswith(str(year)) and "답안표" not in f:
            return os.path.join(PDF_DIR, f)
    return None


def find_question_in_pdf(doc, q_num):
    """
    PDF 문서에서 특정 문제 번호의 영역(페이지, 크롭 영역)을 탐색합니다.
    - 반환: (page, crop_rect) 또는 (None, None)
    """
    for page_idx, page in enumerate(doc):
        if page_idx == 0:
            continue  # 표지 스킵
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
                    target_rect = fitz.Rect(block[0], block[1], block[2], height)
                    # 다음 문항 기준으로 y1 경계 제한
                    for block_next in blocks:
                        if re.match(rf"^{q_num + 1}[\.)\s]", block_next[4].strip()):
                            target_rect.y1 = block_next[1] - 5
                            break
                    return page, target_rect
    return None, None


# ======================================================================
# Phase 1: options(보기) 누락 보정
# ======================================================================

def extract_options_from_pdf(doc, q_num):
    """
    PDF에서 특정 문항의 보기(①②③④) 텍스트를 추출합니다.
    - 반환: [보기1, 보기2, 보기3, 보기4] 또는 빈 리스트
    """
    page, crop_rect = find_question_in_pdf(doc, q_num)
    if not page or not crop_rect:
        return []

    # 크롭 영역의 텍스트 블록 수집
    blocks = page.get_text("blocks", clip=crop_rect)
    full_text = ""
    for block in sorted(blocks, key=lambda b: (b[1], b[0])):
        full_text += block[4] + "\n"

    # 보기 시작 기호 위치 탐색
    match = re.search(r'[\s]*(?:①|❶|➀)', full_text)
    if not match:
        return []

    options_text = full_text[match.start():]

    # 보기 기호(①~④, ❶~❹, ➀~➃)를 구분자로 분할
    parts = re.split(r'[\s]*(?:①|②|③|④|❶|❷|❸|❹|➀|➁|➂|➃)', options_text)
    options = [p.strip() for p in parts if p.strip()]

    # 최대 4개까지만 반환 (다음 문항이 같이 잡히는 경우 방지)
    return options[:4]


def phase1_fix_options():
    """options가 누락되거나 불완전한 레코드를 PDF에서 보기를 재파싱하여 보정합니다."""
    print("\n" + "=" * 70)
    print("[Phase 1] options(보기) 누락 보정 시작")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 누락된 options 레코드 조회
    c.execute("""SELECT id, year, question_num, options 
                 FROM exam_questions 
                 WHERE options IS NULL OR options = '' OR options = '[]'
                 ORDER BY year, question_num""")
    missing_rows = c.fetchall()

    # 불완전한 보기도 포함
    c.execute("SELECT id, year, question_num, options FROM exam_questions WHERE options IS NOT NULL AND options != '' AND options != '[]'")
    for row in c.fetchall():
        try:
            opts = json.loads(row[3])
            if len(opts) < 4:
                missing_rows.append(row)
        except:
            missing_rows.append(row)

    print(f"  대상 레코드: {len(missing_rows)}건")
    
    fixed_count = 0
    failed_ids = []

    # 연도별 PDF 캐시
    pdf_cache = {}

    for q_id, year, q_num, current_opts in missing_rows:
        if year not in pdf_cache:
            pdf_path = get_pdf_file_for_year(year)
            if pdf_path:
                try:
                    pdf_cache[year] = fitz.open(pdf_path)
                except:
                    pdf_cache[year] = None
            else:
                pdf_cache[year] = None

        doc = pdf_cache[year]
        if not doc:
            failed_ids.append(q_id)
            continue

        new_options = extract_options_from_pdf(doc, q_num)
        if new_options and len(new_options) >= 4:
            options_json = json.dumps(new_options[:4], ensure_ascii=False)
            c.execute("UPDATE exam_questions SET options = ? WHERE id = ?", (options_json, q_id))
            fixed_count += 1
            print(f"    [OK] {q_id}: {len(new_options)}개 보기 추출 완료")
        else:
            failed_ids.append(q_id)
            print(f"    [FAIL] {q_id}: 보기 추출 실패 ({len(new_options)}개)")

    conn.commit()

    # PDF 파일 닫기
    for doc in pdf_cache.values():
        if doc:
            doc.close()

    conn.close()
    print(f"\n  [Phase 1 결과] 보정 성공: {fixed_count}건 / 실패: {len(failed_ids)}건")
    if failed_ids:
        print(f"    실패 목록: {failed_ids}")
    return fixed_count, failed_ids


# ======================================================================
# Phase 2: answer(정답) 누락 보정
# ======================================================================

def parse_2024_answer_sheet():
    """2024년 답안표 PDF에서 정답 딕셔너리 추출"""
    pdf_path = get_pdf_file_for_year(2024, want_answer_sheet=True)
    if not pdf_path or not os.path.exists(pdf_path):
        return {}
    try:
        doc = fitz.open(pdf_path)
        page_text = doc[0].get_text()
        doc.close()
    except:
        return {}

    items = [x.strip() for x in page_text.split("\n") if x.strip()]
    ans_dict = {}
    for i in range(len(items) - 1):
        val = items[i]
        if val.isdecimal():
            num = int(val)
            match = re.search(r'([①②③④❶❷❸❹])', items[i + 1])
            if match:
                ans_dict[num] = SYM_MAP[match.group(1)]
    return ans_dict


def get_inferred_answer_by_font(font_counts, total_font_counter):
    """폰트 메타데이터 분석으로 정답 유추 (2025년 최적화)"""
    bold_candidates = []
    for sym, counts in font_counts.items():
        bold_score = sum(c for f, c in counts.items() if any(kw in f.lower() for kw in BOLD_FONT_KEYWORDS))
        if bold_score > 0:
            bold_candidates.append((sym, bold_score))

    if bold_candidates:
        bold_candidates.sort(key=lambda x: x[1], reverse=True)
        return bold_candidates[0][0]

    if len(total_font_counter) >= 2:
        most_common_font = total_font_counter.most_common(1)[0][0]
        minority = [(s, sum(c for f, c in cnt.items() if f != most_common_font))
                     for s, cnt in font_counts.items()]
        minority = [(s, c) for s, c in minority if c > 0]
        if len(minority) == 1:
            return minority[0][0]
    return None


def detect_answer_by_font_2025(page, crop_rect):
    """2025년 PDF 폰트 분석으로 정답 유추"""
    text_page = page.get_text("dict")
    spans = []
    for block in text_page["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                span_rect = fitz.Rect(span["bbox"])
                if (crop_rect.x0 - 5 <= span_rect.x0 <= crop_rect.x1 + 5 and
                    crop_rect.y0 - 5 <= span_rect.y0 <= crop_rect.y1 + 5):
                    spans.append(span)

    option_symbols = []
    for span in spans:
        text = span["text"].strip()
        match = re.search(r'([①②③④❶❷❸❹])', text)
        if match:
            option_symbols.append({"sym": match.group(1), "y": span["bbox"][1], "x": span["bbox"][0]})

    option_symbols.sort(key=lambda x: (x["y"], x["x"]))
    opt_ranges = {}
    for opt in option_symbols:
        sym = opt["sym"]
        x_limit = 9999.0
        for other in option_symbols:
            if other["sym"] != sym and abs(other["y"] - opt["y"]) < 5 and other["x"] > opt["x"]:
                x_limit = min(x_limit, other["x"] - 2)
        opt_ranges[sym] = {"y": opt["y"], "x_min": opt["x"] - 2, "x_max": x_limit}

    opt_spans = {opt["sym"]: [] for opt in option_symbols}
    for span in spans:
        if not span["text"].strip():
            continue
        matched_sym = None
        min_y_diff = 5.0
        for sym, r in opt_ranges.items():
            y_diff = abs(span["bbox"][1] - r["y"])
            if y_diff < min_y_diff and r["x_min"] <= span["bbox"][0] <= r["x_max"]:
                matched_sym = sym
                min_y_diff = y_diff
        if matched_sym:
            opt_spans[matched_sym].append(span)

    font_counts = {}
    all_fonts = []
    for sym in ["①", "②", "③", "④"]:
        s_list = opt_spans.get(sym, [])
        fonts = [s["font"] for s in s_list]
        font_counts[sym] = Counter(fonts)
        all_fonts.extend(fonts)

    return get_inferred_answer_by_font(font_counts, Counter(all_fonts))


def detect_answer_by_image(year, q_num, page, crop_rect):
    """
    크롭 이미지의 보기 기호 영역 픽셀 밀도 분석으로 정답 유추.
    - 안전 마진을 기존 15%에서 10%로 완화하여 더 많은 문항 판정 시도
    """
    img_path = os.path.join(IMG_DIR, f"{year}_{q_num}.png")
    if not os.path.exists(img_path):
        return None

    try:
        img = Image.open(img_path).convert("L")
        img_w, img_h = img.size
    except:
        return None

    # 이미지 좌표계 복원
    width = page.rect.width
    height = page.rect.height
    bands_count = 4 if width > height else 2
    band_width = width / bands_count
    q_x_center = (crop_rect.x0 + crop_rect.x1) / 2
    band_idx = int(q_x_center / band_width)
    band_x0 = band_width * band_idx

    # PDF 텍스트 스팬 수집
    text_page = page.get_text("dict")
    spans = []
    for block in text_page["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                span_rect = fitz.Rect(span["bbox"])
                if (crop_rect.x0 - 5 <= span_rect.x0 <= crop_rect.x1 + 5 and
                    crop_rect.y0 - 5 <= span_rect.y0 <= crop_rect.y1 + 5):
                    spans.append(span)

    # 보기 기호 스팬 선별
    option_symbols = []
    for span in spans:
        text = span["text"].strip()
        match = re.search(r'([①②③④❶❷❸❹])', text)
        if match:
            option_symbols.append({"sym": match.group(1), "bbox": span["bbox"]})

    if len(option_symbols) < 4:
        return None

    results = []
    scale = 2.2  # 이미지 렌더링 스케일

    for opt in option_symbols:
        sym = opt["sym"]
        bbox = fitz.Rect(opt["bbox"])

        # 이미지 픽셀 좌표 변환 (band_x0 기준)
        px_x0 = int((bbox.x0 - band_x0) * scale) - 12
        px_y0 = int((bbox.y0 - crop_rect.y0) * scale) - 12
        span_height = abs(bbox.y1 - bbox.y0)
        px_x1 = px_x0 + int(span_height * scale) + 24
        px_y1 = int((bbox.y1 - crop_rect.y0) * scale) + 12

        # 경계 제한
        px_x0 = max(0, min(img_w, px_x0))
        px_y0 = max(0, min(img_h, px_y0))
        px_x1 = max(0, min(img_w, px_x1))
        px_y1 = max(0, min(img_h, px_y1))
        px_x0, px_x1 = min(px_x0, px_x1), max(px_x0, px_x1)
        px_y0, px_y1 = min(px_y0, px_y1), max(px_y0, px_y1)

        if px_x1 <= px_x0:
            px_x1 = max(0, min(img_w, px_x0 + 10))
        if px_y1 <= px_y0:
            px_y1 = max(0, min(img_h, px_y0 + 10))

        patch = img.crop((px_x0, px_y0, px_x1, px_y1))
        pixels = list(patch.getdata())
        total_pixels = len(pixels)
        mean_darkness = 255 - (sum(pixels) / total_pixels) if total_pixels > 0 else 0
        results.append({"sym": sym, "mean_darkness": mean_darkness})

    if not results:
        return None

    results.sort(key=lambda x: x["mean_darkness"], reverse=True)
    best = results[0]
    second = results[1]

    # 안전 조건: 1위가 2위보다 확실히 굵어야 함 (비율차 10%로 완화)
    if best["mean_darkness"] > 1.5:
        if second["mean_darkness"] == 0:
            return best["sym"]
        ratio_diff = (best["mean_darkness"] - second["mean_darkness"]) / second["mean_darkness"]
        if ratio_diff > 0.10:  # 기존 0.15에서 0.10으로 완화
            return best["sym"]
    return None


def phase2_fix_answers():
    """answer가 누락된 레코드의 정답을 PDF/이미지에서 추출하여 보정합니다."""
    print("\n" + "=" * 70)
    print("[Phase 2] answer(정답) 누락 보정 시작")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # answer가 NULL인 레코드만 조회
    c.execute("""SELECT id, year, question_num 
                 FROM exam_questions 
                 WHERE answer IS NULL OR answer = '' OR answer = '[]'
                 ORDER BY year, question_num""")
    missing_rows = c.fetchall()
    print(f"  대상 레코드: {len(missing_rows)}건")

    # 2024년 답안표 일괄 처리
    ans_2024 = parse_2024_answer_sheet()
    updated_2024 = 0
    if ans_2024:
        for q_id, year, q_num in missing_rows:
            if year == 2024 and q_num in ans_2024:
                ans_json = json.dumps([ans_2024[q_num]])
                c.execute("UPDATE exam_questions SET answer = ? WHERE id = ?", (ans_json, q_id))
                updated_2024 += 1
        conn.commit()
        print(f"  [2024년] 답안표 기반 적재: {updated_2024}건")

    # 나머지 연도 처리
    non_2024 = [(q_id, year, q_num) for q_id, year, q_num in missing_rows if year != 2024]

    # 연도별 그룹핑
    by_year = {}
    for q_id, year, q_num in non_2024:
        if year not in by_year:
            by_year[year] = []
        by_year[year].append((q_id, q_num))

    total_success = updated_2024
    total_failed = 0

    for year in sorted(by_year.keys()):
        pdf_path = get_pdf_file_for_year(year)
        if not pdf_path:
            print(f"  [{year}년] PDF 없음, 스킵")
            total_failed += len(by_year[year])
            continue

        try:
            doc = fitz.open(pdf_path)
        except:
            print(f"  [{year}년] PDF 로드 실패")
            total_failed += len(by_year[year])
            continue

        year_success = 0
        year_failed = 0

        for q_id, q_num in sorted(by_year[year], key=lambda x: x[1]):
            page, crop_rect = find_question_in_pdf(doc, q_num)
            if not page or not crop_rect:
                year_failed += 1
                continue

            inferred_sym = None

            # 2025년: 폰트 분석 우선
            if year == 2025:
                inferred_sym = detect_answer_by_font_2025(page, crop_rect)

            # 이미지 밀도 분석 (모든 연도 공통 폴백)
            if not inferred_sym:
                inferred_sym = detect_answer_by_image(year, q_num, page, crop_rect)

            if inferred_sym:
                ans_num = SYM_MAP[inferred_sym]
                ans_json = json.dumps([ans_num])
                c.execute("UPDATE exam_questions SET answer = ? WHERE id = ?", (ans_json, q_id))
                year_success += 1
            else:
                year_failed += 1

        conn.commit()
        doc.close()
        total_success += year_success
        total_failed += year_failed
        print(f"  [{year}년] 성공: {year_success}건 / 실패: {year_failed}건")

    conn.close()
    print(f"\n  [Phase 2 결과] 보정 성공: {total_success}건 / 실패: {total_failed}건")
    return total_success, total_failed


# ======================================================================
# Phase 3: 결과 검증 리포트
# ======================================================================

def phase3_report():
    """보정 후 DB 상태를 검증하고 리포트를 출력합니다."""
    print("\n" + "=" * 70)
    print("[Phase 3] 보정 후 검증 리포트")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM exam_questions")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM exam_questions WHERE options IS NULL OR options = '' OR options = '[]'")
    missing_opts = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM exam_questions WHERE answer IS NULL OR answer = '' OR answer = '[]'")
    missing_ans = c.fetchone()[0]

    print(f"  전체 레코드: {total}")
    print(f"  options 누락: {missing_opts}")
    print(f"  answer 누락: {missing_ans}")
    print(f"  answer 채워진 비율: {((total - missing_ans) / total * 100):.1f}%")

    print("\n  연도별 현황:")
    c.execute("""
        SELECT year, COUNT(*),
               SUM(CASE WHEN options IS NULL OR options = '' OR options = '[]' THEN 1 ELSE 0 END),
               SUM(CASE WHEN answer IS NULL OR answer = '' OR answer = '[]' THEN 1 ELSE 0 END)
        FROM exam_questions GROUP BY year ORDER BY year
    """)
    for row in c.fetchall():
        filled = row[1] - row[3]
        pct = filled / row[1] * 100
        print(f"    {row[0]}년: 전체 {row[1]} | opts누락 {row[2]} | ans누락 {row[3]} | 정답률 {pct:.0f}%")

    # 여전히 누락된 레코드 목록
    c.execute("""SELECT id FROM exam_questions 
                 WHERE answer IS NULL OR answer = '' OR answer = '[]'
                 ORDER BY year, question_num""")
    still_missing = [r[0] for r in c.fetchall()]

    if still_missing:
        print(f"\n  [수동 보정 필요] 여전히 정답 누락: {len(still_missing)}건")
        # 20건까지만 출력
        for item in still_missing[:20]:
            print(f"    - {item}")
        if len(still_missing) > 20:
            print(f"    ... 외 {len(still_missing) - 20}건")

    conn.close()


# ======================================================================
# 메인 실행
# ======================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("[기출 DB 누락 데이터 통합 보정 프로세스]")
    print("=" * 70)

    # Phase 1: options 보정
    p1_ok, p1_fail = phase1_fix_options()

    # Phase 2: answer 보정
    p2_ok, p2_fail = phase2_fix_answers()

    # Phase 3: 결과 검증
    phase3_report()

    print("\n" + "=" * 70)
    print("[전체 완료]")
    print(f"  Phase 1 (보기 보정): 성공 {p1_ok}건")
    print(f"  Phase 2 (정답 보정): 성공 {p2_ok}건")
    print("=" * 70)
