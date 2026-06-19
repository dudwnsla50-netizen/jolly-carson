# -*- coding: utf-8 -*-
"""
[PDF 답안 페이지 정밀 분석기]
- 설계 목적: 기출 PDF의 마지막 페이지들에서 답안표를 찾고, 형식을 정밀 분석합니다.
- 2015~2023년 PDF는 "문제 및 답안"이라는 제목 → 답안 페이지 존재 가능성 높음
"""
import fitz
import os
import re
import sys
import io

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "past_exams")

def analyze_pdf_answers(year):
    """PDF의 마지막 3페이지를 분석하여 답안표 패턴을 탐색합니다."""
    files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf') and f.startswith(str(year)) and '답안표' not in f]
    if not files:
        print(f"  [{year}] PDF 없음")
        return
    
    pdf_path = os.path.join(PDF_DIR, files[0])
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    
    print(f"\n{'='*70}")
    print(f"[{year}년] {files[0]} (총 {page_count}페이지)")
    print(f"{'='*70}")
    
    # 마지막 3페이지 분석
    for pg_idx in range(max(0, page_count - 3), page_count):
        page = doc[pg_idx]
        text = page.get_text()
        images = page.get_images()
        
        print(f"\n  --- 페이지 {pg_idx + 1} ---")
        print(f"  이미지 수: {len(images)}")
        print(f"  텍스트 길이: {len(text)}")
        
        # 답안 관련 키워드 검색
        keywords = ['정답', '답안', '답', '해설', '가답안', '확정답안']
        found_keywords = [kw for kw in keywords if kw in text]
        if found_keywords:
            print(f"  발견 키워드: {found_keywords}")
        
        # 보기 기호(①②③④) 패턴 탐색
        syms = re.findall(r'[①②③④❶❷❸❹]', text)
        if syms:
            print(f"  보기 기호 발견: {len(syms)}개 ({', '.join(set(syms))})")
        
        # 숫자 + 보기 기호 패턴 (예: "1 ③", "2 ①" → 답안표 형식)
        answer_patterns = re.findall(r'(\d{1,3})\s*[\.)]?\s*([①②③④❶❷❸❹])', text)
        if answer_patterns:
            print(f"  답안 패턴 발견: {len(answer_patterns)}건")
            for num, sym in answer_patterns[:10]:
                print(f"    {num}번 → {sym}")
            if len(answer_patterns) > 10:
                print(f"    ... 외 {len(answer_patterns) - 10}건")
        
        # 텍스트 미리보기 (처음 500자)
        preview = text.strip()[:500].replace('\n', ' | ')
        if preview:
            print(f"  텍스트 미리보기: {preview[:200]}...")

    doc.close()

# 모든 연도 분석
for year in range(2015, 2024):
    analyze_pdf_answers(year)
