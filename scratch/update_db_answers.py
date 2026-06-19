# -*- coding: utf-8 -*-
"""
[기출문제 PDF 폰트 및 이미지 분석 기반 정답 자동 적재기]
- 작성자: Antigravity
- 설계 목적: 
  1. 2024년도는 별도의 텍스트 답안표 PDF에서 정답을 직접 파싱하여 100% 신뢰도로 적재합니다.
  2. 2025년도는 PDF 메타데이터 상의 폰트 분리 특성이 존재하므로 기존 폰트 기반 분석을 우선 적용합니다.
  3. 2015~2023년 및 2026년도는 PDF 상에 폰트 스타일 구분이 없으나, 기출문제 크롭 이미지에 정답 보기가 굵게(Bold) 표시되어 있습니다.
     따라서 PDF 상의 보기 기호 영역을 2.2배 스케일로 이미지 픽셀 좌표계로 매핑한 후, 
     기호 영역의 어두운 픽셀 밀도(Darkness Density)를 분석하여 정답을 판별 및 적재합니다.
"""
import fitz
import os
import re
import sys
import json
import sqlite3
from collections import Counter
from PIL import Image

# Windows 콘솔 인코딩 에러 방지
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")
PDF_DIR = os.path.join(BASE_DIR, "data", "past_exams")
IMG_DIR = os.path.join(BASE_DIR, "reports", "images")

# 2025년용 Bold로 판정하는 폰트명 키워드
BOLD_FONT_KEYWORDS = ["bold", "t12", "t18", "t19", "t21", "t22", "t23", "t24", "gothic-bold", "myeongjo-bold"]
SYM_MAP = {"①": 1, "②": 2, "③": 3, "④": 4, "❶": 1, "❷": 2, "❸": 3, "❹": 4}

def get_pdf_file_for_year(year, want_answer_sheet=False):
    """
    지정 연도에 해당하는 PDF 파일명을 탐색합니다.
    - want_answer_sheet가 True인 경우: '답안표' 텍스트가 들어간 PDF 우선 탐색 (2024년 대응)
    - want_answer_sheet가 False인 경우: 문제지 PDF 우선 탐색 ('답안표' 제외)
    """
    if not os.path.exists(PDF_DIR):
        return None
    files = os.listdir(PDF_DIR)
    
    # 2024년도 답안표 우선 처리
    if want_answer_sheet:
        for f in files:
            if f.endswith(".pdf") and f.startswith(str(year)) and "답안표" in f:
                return os.path.join(PDF_DIR, f)
                
    # 일반 문제지 탐색
    for f in files:
        if f.endswith(".pdf") and f.startswith(str(year)) and "답안표" not in f:
            return os.path.join(PDF_DIR, f)
            
    return None

def parse_2024_answer_sheet():
    """
    2024년 답안표 PDF에서 텍스트를 파싱하여 {문제번호: 정답번호} 딕셔너리를 구합니다.
    """
    pdf_path = get_pdf_file_for_year(2024, want_answer_sheet=True)
    if not pdf_path or not os.path.exists(pdf_path):
        print("[오류] 2024년 답안표 PDF 파일을 찾을 수 없습니다.")
        return {}
        
    try:
        doc = fitz.open(pdf_path)
        # 1페이지(A형 답안) 파싱
        page_text = doc[0].get_text()
        doc.close()
    except Exception as e:
        print(f"[오류] 2024년 답안표 로드 실패: {e}")
        return {}
        
    items = [x.strip() for x in page_text.split("\n") if x.strip()]
    ans_dict = {}
    
    for i in range(len(items) - 1):
        val = items[i]
        if val.isdecimal():
            num = int(val)
            next_val = items[i+1]
            match = re.search(r'([①②③④❶❷❸❹])', next_val)
            if match:
                ans_dict[num] = SYM_MAP[match.group(1)]
                
    return ans_dict

def get_inferred_answer_by_font(font_counts, total_font_counter):
    """
    보기별 폰트 메타데이터 빈도 정보를 분석하여 정답을 유추합니다 (2025년용).
    """
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
        bold_candidates.sort(key=lambda x: x[1], reverse=True)
        return bold_candidates[0][0]
        
    if len(total_font_counter) >= 2:
        most_common_font = total_font_counter.most_common(1)[0][0]
        minority_candidates = []
        for sym, counts in font_counts.items():
            non_common_count = sum(c for f, c in counts.items() if f != most_common_font)
            if non_common_count > 0:
                minority_candidates.append((sym, non_common_count))
        if len(minority_candidates) == 1:
            return minority_candidates[0][0]
            
    return None

def detect_answer_by_image(year, q_num, page, crop_rect):
    """
    문제 크롭 이미지의 보기 기호 영역 픽셀 밀도를 분석하여 정답을 유추합니다.
    - PDF 내 보기 기호의 Bounding Box를 이미지 픽셀 좌표(스케일 2.2)로 변환
    - 보기별 45x45 픽셀 패치를 추출하여 어두운 강도(검은색 픽셀 농도) 비교
    """
    img_filename = f"{year}_{q_num}.png"
    img_path = os.path.join(IMG_DIR, img_filename)
    if not os.path.exists(img_path):
        return None
        
    try:
        img = Image.open(img_path).convert("L")
        img_w, img_h = img.size
    except Exception as e:
        print(f"    -> [오류] {img_filename} 이미지 로드 실패: {e}")
        return None
        
    # [정밀 보정] 이미지 크롭 시 단의 왼쪽 경계(band_x0) 기준 좌표계를 복원합니다.
    width = page.rect.width
    height = page.rect.height
    bands_count = 4 if width > height else 2
    band_width = width / bands_count
    q_x_center = (crop_rect.x0 + crop_rect.x1) / 2
    band_idx = int(q_x_center / band_width)
    band_x0 = band_width * band_idx
        
    # PDF 상에서 해당 문항의 텍스트 스팬 수집
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
            sym = match.group(1)
            option_symbols.append({
                "sym": sym,
                "bbox": span["bbox"]
            })
            
    if len(option_symbols) < 4:
        # 보기 기호를 전부 감지하지 못한 경우 판정 불가 (디버그 정보 출력)
        print(f"    -> [실패] {year}_{q_num} 보기 기호 감지 개수 미달 ({len(option_symbols)}/4)")
        return None
        
    results = []
    scale = 2.2 # 캐시된 렌더링 이미지 해상도 배율
    
    for opt in option_symbols:
        sym = opt["sym"]
        bbox = fitz.Rect(opt["bbox"])
        
        # 이미지 픽셀 좌표계로 변환 (글자가 짤리지 않게 사방 12픽셀 마진 추가, band_x0 적용)
        px_x0 = int((bbox.x0 - band_x0) * scale) - 12
        px_y0 = int((bbox.y0 - crop_rect.y0) * scale) - 12
        
        span_height = abs(bbox.y1 - bbox.y0)
        px_x1 = px_x0 + int(span_height * scale) + 24
        px_y1 = int((bbox.y1 - crop_rect.y0) * scale) + 12
        
        # 이미지 경계 제한 우선 수행
        px_x0 = max(0, min(img_w, px_x0))
        px_y0 = max(0, min(img_h, px_y0))
        px_x1 = max(0, min(img_w, px_x1))
        px_y1 = max(0, min(img_h, px_y1))
        
        # 좌표 대소관계 정렬 (PIL ValueError 방지)
        px_x0, px_x1 = min(px_x0, px_x1), max(px_x0, px_x1)
        px_y0, px_y1 = min(px_y0, px_y1), max(px_y0, px_y1)
        
        # 면적이 0이 되는 것을 보정
        if px_x1 <= px_x0:
            px_x1 = max(0, min(img_w, px_x0 + 10))
        if px_y1 <= px_y0:
            px_y1 = max(0, min(img_h, px_y0 + 10))
            
        patch = img.crop((px_x0, px_y0, px_x1, px_y1))
        pixels = list(patch.getdata())
        total_pixels = len(pixels)
        
        # 어두움 평균 강도 (낮을수록 검은색 픽셀이 많음 -> 255 - mean)
        mean_darkness = 255 - (sum(pixels) / total_pixels) if total_pixels > 0 else 0
        results.append({
            "sym": sym,
            "mean_darkness": mean_darkness
        })
        
    if not results:
        return None
        
    # 어두움 강도 기준 정렬
    results.sort(key=lambda x: x["mean_darkness"], reverse=True)
    best = results[0]
    second = results[1]
    
    # [안전 조건] 1위 보기가 2위 보기보다 확실히 굵어야 함 (비율차 20% 이상)
    # 또한 원본에 볼드 처리가 아예 없어서 수치가 0에 수렴하는 경우 방지 (최소 1.5 이상)
    if best["mean_darkness"] > 1.5:
        if second["mean_darkness"] == 0:
            return best["sym"]
        ratio_diff = (best["mean_darkness"] - second["mean_darkness"]) / second["mean_darkness"]
        if ratio_diff > 0.15: # 안전 마진을 15%로 소폭 완화
            return best["sym"]
            
    # 판정 실패 시 로그 출력 (디버깅용)
    print(f"    -> [실패] {year}_{q_num} best={best['sym']}({best['mean_darkness']:.2f}), second={second['sym']}({second['mean_darkness']:.2f})")
    return None

def analyze_and_update_all():
    print("[정답 적재 자동화 프로세스] 구동 시작...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 2024년 정답표 PDF 일괄 추출 및 업데이트
    print("\n--- 2024년도 답안표 기반 정답 적재 ---")
    ans_2024_map = parse_2024_answer_sheet()
    if ans_2024_map:
        updated_2024_count = 0
        for q_num, ans in ans_2024_map.items():
            # DB의 id 형식은 '2024_문제번호' 형태
            q_id = f"2024_{q_num}"
            cursor.execute("UPDATE exam_questions SET answer = ? WHERE id = ?", (ans, q_id))
            if cursor.rowcount > 0:
                updated_2024_count += 1
        conn.commit()
        print(f"-> 2024년도 답안 일괄 매핑 완료 ({updated_2024_count}건 갱신)")
    else:
        print("-> 2024년도 답안표 매핑 스킵 (파일 없음 또는 오류)")
        
    # 2. DB 기출문제 조회
    cursor.execute("SELECT id, year, question_num FROM exam_questions WHERE year != 2024")
    db_questions = cursor.fetchall()
    
    questions_by_year = {}
    for q_id, year, q_num in db_questions:
        if year not in questions_by_year:
            questions_by_year[year] = []
        questions_by_year[year].append((q_id, q_num))
        
    total_inferred = 0
    total_failed = 0
    
    # 3. 연도별 PDF 분석 및 정답 유추 구동
    for year in sorted(questions_by_year.keys()):
        pdf_path = get_pdf_file_for_year(year, want_answer_sheet=False)
        if not pdf_path:
            print(f"[경고] {year}년도 PDF 문제지 파일이 존재하지 않아 스킵합니다.")
            continue
            
        print(f"\n[{year}년도 기출문제 분석 구동] -> {os.path.basename(pdf_path)}")
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"  -> PDF 로드 실패: {e}")
            continue
            
        q_list = sorted(questions_by_year[year], key=lambda x: x[1])
        year_success = 0
        year_failed = 0
        
        for q_id, q_num in q_list:
            found_page = None
            target_rect = None
            
            # (1) 문제 경계 영역 탐색 (image_cropper 알고리즘 동기화)
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
                            # 다음 문항 기준으로 y1 경계 제한
                            for block_next in blocks:
                                if re.match(rf"^{q_num + 1}[\.\)\s]", block_next[4].strip()):
                                    target_rect.y1 = block_next[1] - 5
                                    break
                            break
                    if found_page:
                        break
                if found_page:
                    break
                    
            if not found_page or not target_rect:
                year_failed += 1
                total_failed += 1
                continue
                
            inferred_sym = None
            
            # (2) 1차 시도: 폰트 메타데이터 분석 (2025년 최적화)
            if year == 2025:
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
                                
                option_symbols = []
                for span in spans:
                    text = span["text"].strip()
                    match = re.search(r'([①②③④❶❷❸❹])', text)
                    if match:
                        option_symbols.append({
                            "sym": match.group(1),
                            "y": span["bbox"][1],
                            "x": span["bbox"][0]
                        })
                
                option_symbols.sort(key=lambda x: (x["y"], x["x"]))
                opt_ranges = {}
                for opt in option_symbols:
                    sym = opt["sym"]
                    x_limit = 9999.0
                    for other_opt in option_symbols:
                        if other_opt["sym"] != sym and abs(other_opt["y"] - opt["y"]) < 5:
                            if other_opt["x"] > opt["x"]:
                                x_limit = min(x_limit, other_opt["x"] - 2)
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
                    
                inferred_sym = get_inferred_answer_by_font(font_counts, Counter(all_fonts))
                
            # (3) 2차 시도: 이미지 픽셀 어두움 강도 분석 (2015~2023, 2026 및 2025 폴백)
            if not inferred_sym:
                inferred_sym = detect_answer_by_image(year, q_num, found_page, target_rect)
                
            # (4) 정답 DB 업데이트 적용
            if inferred_sym:
                ans_num = SYM_MAP[inferred_sym]
                cursor.execute("UPDATE exam_questions SET answer = ? WHERE id = ?", (ans_num, q_id))
                year_success += 1
                total_inferred += 1
            else:
                year_failed += 1
                total_failed += 1
                
        conn.commit()
        print(f"  -> 완료. 성공: {year_success}건 / 실패: {year_failed}건")
        doc.close()
        
    conn.close()
    print(f"\n[정답 적재 자동화 완료]")
    print(f"- 성공적으로 정답이 입력된 문항: {total_inferred + (updated_2024_count if ans_2024_map else 0)}건")
    print(f"- 판정 실패 또는 크롭 누락 문항: {total_failed}건")

if __name__ == "__main__":
    analyze_and_update_all()
