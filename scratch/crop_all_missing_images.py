# -*- coding: utf-8 -*-
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import image_cropper

# 인코딩 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 파일 저장 절대 경로 설정
BASE_DIR = r"d:\100.lyj\anti_workspace\jolly-carson"
EXAM_DIR = os.path.join(BASE_DIR, "data", "past_exam")
LOCAL_IMG_DIR = os.path.join(BASE_DIR, "reports", "images")
ARTIFACT_IMG_DIR = r"C:\Users\histo\.gemini\antigravity-ide\brain\ae510509-1b89-475f-9e8b-abe2d35a05b1\images"

EXAM_FILES = [
    {"year": 2015, "filename": "2015년(제16회) 정보시스템감리사 필기시험문제(답안).pdf"},
    {"year": 2016, "filename": "2016년(제17회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2017, "filename": "2017년(제18회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2018, "filename": "2018년(제19회)정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2019, "filename": "2019년(제20회)정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2020, "filename": "2020년(제21회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2021, "filename": "2021년(제22회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2022, "filename": "2022년(제23회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2023, "filename": "2023년 정보시스템 감리사 자격검정 필기시험 문제 A형(답안포함).pdf"},
    {"year": 2024, "filename": "2024년(제25회) 감리사 자격검정 필기시험 문제-A형.pdf"},
    {"year": 2025, "filename": "2025년 감리사 자격검정 필기시험 문제-A형(답포함).pdf"},
    {"year": 2026, "filename": "2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf"}
]

SUBJECTS = ["PM", "SE", "DB", "SA", "SC"]

def main():
    print("=== [시작] 기출문제 이미지 일괄 강제 크롭 (2015년~2026년) ===")
    
    total_cropped = 0
    for exam in EXAM_FILES:
        year = exam["year"]
        pdf_name = exam["filename"]
        pdf_path = os.path.join(EXAM_DIR, pdf_name)
        
        if not os.path.exists(pdf_path):
            print(f"❌ PDF 파일이 존재하지 않습니다: {pdf_path}")
            continue
            
        print(f"\n👉 {year}년도 기출 PDF 크롭 시작: {pdf_name}")
        for subject in SUBJECTS:
            try:
                # force_crop=True로 설정하여 누락 여부에 상관없이 최신 경로에 다시 덮어씁니다.
                positions = image_cropper.get_question_positions_and_crop(
                    pdf_path, year, subject, LOCAL_IMG_DIR, ARTIFACT_IMG_DIR, force_crop=True
                )
                print(f"  ✅ 과목 [{subject}] 크롭 성공 (문항수: {len(positions)})")
                total_cropped += len(positions)
            except Exception as e:
                print(f"  ❌ 과목 [{subject}] 크롭 중 에러 발생: {e}")
                
    print(f"\n=== [완료] 이미지 크롭 배치 작업 종료 (총 {total_cropped}개 작업 완료) ===")

if __name__ == "__main__":
    main()
