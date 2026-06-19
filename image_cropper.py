# -*- coding: utf-8 -*-
"""
[공통 기출문제 이미지 크롭 및 캐싱 모듈]
- 목적: 5대 과목(PM, SE, DB, SA, SC)의 문항별 bounding box 탐색, 이미지 크롭 및 캐싱을 일괄 처리합니다.
- 작성자: Antigravity
"""

import os
import re
import fitz

# 과목별 문제 번호 수집 범위 정의 (다음 과목 첫 문제는 현재 과목 마지막 문제의 하단 경계선 감지용)
SUBJECT_RANGE_MAP = {
    "PM": {"start": 1, "end": 25, "next_limit": 26},
    "SE": {"start": 26, "end": 50, "next_limit": 51},
    "DB": {"start": 51, "end": 75, "next_limit": 76},
    "SA": {"start": 76, "end": 100, "next_limit": 101},
    "SC": {"start": 101, "end": 120, "next_limit": 121}
}

def get_subject_range(subject_code, year):
    """연도별/과목별 문제 번호 범위를 정밀 튜닝하여 반환합니다."""
    # 2015년 시스템 구조(SA)는 76번~90번까지 총 15문항 출제
    if subject_code == "SA" and year == 2015:
        return {"start": 76, "end": 90, "next_limit": 91}
    # 2015년 보안(SC)은 91번~105번까지 총 15문항 출제
    if subject_code == "SC" and year == 2015:
        return {"start": 91, "end": 105, "next_limit": 106}
        
    return SUBJECT_RANGE_MAP.get(subject_code, {"start": 1, "end": 25, "next_limit": 26})

def get_question_positions_and_crop(pdf_path, year, subject_code, local_img_dir, artifact_img_dir, force_crop=False):
    """
    기출 PDF를 분석하여 과목별 문제의 위치를 결정하고 이미지를 크롭합니다.
    - 캐싱 정책: 기존 크롭 파일이 이미 존재하면 렌더링 과정을 건너뛰고 기존 좌표만 반환합니다.
    """
    os.makedirs(local_img_dir, exist_ok=True)
    # 배포 환경을 위한 방어 코드: 아티팩트 디렉토리 생성 실패 시 에러 없이 넘어감
    try:
        if artifact_img_dir:
            os.makedirs(artifact_img_dir, exist_ok=True)
    except Exception:
        pass
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"  [경고] {year}년도 PDF 로드 실패: {e}")
        return {}
        
    # 과목 번호 범위 획득
    s_range = get_subject_range(subject_code, year)
    q_start = s_range["start"]
    q_end = s_range["end"]
    q_next_limit = s_range["next_limit"]
    
    found_positions = []
    
    # 1. 기출문제 번호의 위치(Bounding Box) 수집
    for page_idx, page in enumerate(doc):
        # 0페이지는 표지이므로 건너뜀 (2015~2026 공통)
        if page_idx == 0:
            continue
        width = page.rect.width
        height = page.rect.height
        bands_count = 4 if width > height else 2 # 가로형 4단, 세로형 2단 분할
        
        for b in range(bands_count):
            x0 = (width / bands_count) * b
            x1 = (width / bands_count) * (b + 1)
            clip_rect = fitz.Rect(x0, 0, x1, height)
            
            blocks = page.get_text("blocks", clip=clip_rect)
            blocks.sort(key=lambda x: x[1]) # y좌표 기준 정렬
            
            for block in blocks:
                text = block[4].strip()
                # 범위 내의 문제 번호 탑색
                match = re.match(r"^([1-9][0-9]*|1[0-9][0-9])[\.\)\s]", text)
                if match:
                    num = int(match.group(1))
                    if q_start <= num <= q_next_limit:
                        margin_threshold = 80.0 if b == 0 else (x0 + 30.0)
                        if block[0] > margin_threshold:
                            continue
                            
                        rect = fitz.Rect(block[0], block[1], block[2], block[3])
                        found_positions.append({
                            "num": num,
                            "rect": rect,
                            "page_idx": page_idx,
                            "band_idx": b,
                            "x0": x0,
                            "x1": x1
                        })
                        
    # 2. 물리적 위치(페이지, 단, y좌표) 기준으로 단조 증가 정합성 필터링
    found_positions.sort(key=lambda x: (x["page_idx"], x["band_idx"], x["rect"].y0))
    
    candidates = {n: [] for n in range(q_start, q_next_limit + 1)}
    for pos in found_positions:
        num = pos["num"]
        candidates[num].append(pos)
        
    for n in candidates:
        candidates[n].sort(key=lambda x: (x["page_idx"], x["band_idx"], x["rect"].y0))
        
    unique_positions = {}
    prev_pos = None
    for n in range(q_start, q_next_limit + 1):
        opts = candidates[n]
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
                
    # 3. 크롭 사각형 영역 결정 및 캐싱 이미지 저장
    for num in range(q_start, q_end + 1):
        if num not in unique_positions:
            continue
            
        pos = unique_positions[num]
        page_idx = pos["page_idx"]
        page = doc[page_idx]
        height = page.rect.height
        
        # 다음 문항이 있을 경우 아래쪽 끝 구하기
        next_pos = None
        sorted_nums = sorted(list(unique_positions.keys()))
        try:
            curr_idx = sorted_nums.index(num)
            if curr_idx + 1 < len(sorted_nums):
                next_num = sorted_nums[curr_idx + 1]
                next_pos = unique_positions[next_num]
        except ValueError:
            pass
            
        y_start = pos["rect"].y0 - 6
        y_end = height - 12
        
        if next_pos and next_pos["page_idx"] == page_idx and next_pos["band_idx"] == pos["band_idx"]:
            y_end = next_pos["rect"].y0 - 8
            
        # [추가] 보기 ④번의 위치를 찾아서 y_end를 보정 (마지막 문제 등의 노이즈 이미지 섞임 방지)
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
            # 보기 ④번 하단에 적절한 마진(+20)을 더한 값이 기존 y_end보다 작으면 경계로 채택
            q4_y_end = q4_y1 + 20
            if q4_y_end < y_end:
                y_end = q4_y_end
            
        crop_rect = fitz.Rect(pos["x0"], y_start, pos["x1"], y_end)
        
        # 비정상적인 극소 면적 방지
        if crop_rect.height < 40:
            crop_rect.y1 = crop_rect.y0 + 250
        if crop_rect.y1 > height:
            crop_rect.y1 = height
            
        # 텍스트 크롭에 사용할 영역 좌표 저장 (pdfplumber용)
        pos["crop_rect"] = (pos["x0"], y_start, pos["x1"], crop_rect.y1)
        
        # 캐싱 정책 검증: 이미지가 이미 존재하고 force_crop이 비활성화인 경우 렌더링 스킵
        local_path = os.path.join(local_img_dir, f"{year}_{num}.png")
        artifact_path = os.path.join(artifact_img_dir, f"{year}_{num}.png")
        
        is_cached = not force_crop and os.path.exists(local_path) and os.path.exists(artifact_path)
        
        if is_cached:
            continue
            
        # 렌더링 및 디스크 쓰기 수행
        try:
            # 사용자의 요청에 따라 이미지 사이즈 및 품질을 50% 줄이기 위해 Matrix 배율을 2.2에서 1.1로 조정
            pix = page.get_pixmap(clip=crop_rect, matrix=fitz.Matrix(1.1, 1.1))
            pix.save(local_path)
            # 배포 환경을 위한 방어 코드: 아티팩트 파일 저장 실패 시 에러 없이 넘어감
            if artifact_path:
                try:
                    pix.save(artifact_path)
                except Exception:
                    pass
        except Exception as e:
            print(f"  [경고] {year}년도 {num}번 크롭 이미지 저장 실패: {e}")
            
    return unique_positions

