# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

"""
[초프리미엄 프로젝트 관리 공식 범위(PM.txt) 기출문제 뷰어 자동 빌더]
- 목적: 2015년~2026년 기출 PDF에서 프로젝트 관리 전체 문항(1~25번)을 읽어와서 
  공식 가이드라인(PM.txt) 대단원 및 세부 중단원에 부합하도록 구조화하고, 
  이를 수려한 다크모드 대시보드 HTML 파일 안에 임베딩하여 자동 생성합니다.
"""

import os
from build_utils import get_output_paths, update_shared_db, ARTIFACT_DIR
import sys
import re
import json
# import pdfplumber
# import fitz

# 공통 이미지 크롭 모듈 임포트
# import image_cropper

FORCE_CROP = "--force" in sys.argv or "--force-crop" in sys.argv

# 한글 윈도우 환경에서 콘솔 출력 깨짐 방지
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

EXAM_DIR = r"e:\jolly-carson\data\past_exams"
EXAM_FILES = [
    {"year": 2015, "filename": "2015년(제16회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2016, "filename": "2016년(제17회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2017, "filename": "2017년(제18회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2018, "filename": "2018년(제19회)정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2019, "filename": "2019년(제20회)정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2020, "filename": "2020년(제21회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2021, "filename": "2021년(제22회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2022, "filename": "2022년(제23회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2023, "filename": "2023년(제24회) 정보시스템 감리사 필기시험 문제 및 답안.pdf"},
    {"year": 2024, "filename": "2024년(제25회) 감리사 자격검정 필기시험 문제-A형.pdf"},
    {"year": 2025, "filename": "2025년 감리사 자격검정 필기시험 문제-A형(답포함).pdf"},
    {"year": 2026, "filename": "2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf"}
]

# PM.txt 공식 가이드라인 기반의 11개 중단원 분류 사전 및 키워드 매핑
CONCEPT_KEYWORDS = {
    # 1. 정보화 및 소프트웨어 관련 법/제도 및 국내외 지침, 가이드
    "1-a. 정보화 및 소프트웨어 관련 법령 및 고시, 가이드": [
        "소프트웨어 진흥법", "소프트웨어진흥법", "sw진흥법", "소프트웨어 진흥",
        "지능정보화 기본법", "지능정보화기본법", "지능정보화",
        "구축운영 지침", "구축운영지침", "행정기관 및 공공기관 정보시스템", "구축 운영 지침",
        "관리감독에 관한 지침", "관리감독 지침", "과업심의", "과업 변경", "적정성 심의", "과업조정", "과업내용 변경", "과업심의위원회",
        "공공데이터", "데이터베이스 표준화", "품질관리 지침", "공공기관의 데이터베이스", "데이터 표준화",
        "cbd", "sw개발 표준 산출물", "산출물 가이드", "산출물 표준",
        "정보기술 아키텍처", "ea", "enterprise architecture", "ita", "웹사이트 품질관리", "성과관리 지침"
    ],
    "1-b. 계약 관련 법령 및 예규": [
        "국가계약법", "국가를 당사자로 하는", "국가계약", "조달청", "입찰",
        "협상에 의한 계약", "협상에 의한", "기술성 평가", "차등점수", "경쟁적대화",
        "용역계약일반조건", "용역계약 일반조건", "지체상금", "계약금액 조정", "대가 조정", "물가변동",
        "공동계약", "하도급", "공동이행", "분담이행", "하도급 계약", "공동계약운용요령"
    ],
    "1-c. 대가산정 관련 고시 및 가이드": [
        "대가산정", "sw사업 대가", "엔지니어링사업대가", "대가산정 가이드", "기능점수 단가", "엔지니어링 대가", "엔지니어링사업대가의 기준"
    ],
    "1-d. IT거버넌스, CoBIT 등 국외 관련 지침": [
        "it거버넌스", "cobit", "it 거버넌스", "코빗"
    ],

    # 2. 감리 관련 법제도 및 관련 기술
    "2-a. 전자정부법, 정보시스템 감리기준 등 감리 법제도": [
        "전자정부법", "의무감리", "의무 감리", "감리 대상", "감리대상",
        "정보시스템 감리기준", "정보시스템감리기준", "감리기준", "감리원", "감리법인", "윤리 가이드", "감리 보고서", "의견 진술서", "감리보고서"
    ],
    "2-b. 정보시스템 인프라 관련 법제도": [
        "인프라 관련 법제도", "인프라 법제도"
    ],
    "2-c. 정보시스템 감리 관련 가이드": [
        "발주관리가이드", "감리수행가이드", "유지보수 감리 점검가이드", "점검가이드", "윤리 가이드", "지능정보기술 감리 실무 가이드", "감리 실무 가이드", "감리 실무가이드", "실무 가이드", "실무가이드", "감리 가이드", "감리가이드", "발주·관리 가이드", "수행 가이드", "수행가이드"
    ],

    # 3. 조직 관리론
    "3-a. 조직구조, 조직이론, 조직설계": [
        "조직구조", "조직이론", "조직설계", "매트릭스 조직", "기능식 조직", "프로젝트 조직", "매트릭스형", "기능형 조직"
    ],
    "3-b. 인적 자원관리, 의사소통관리": [
        "인적 자원", "동기부여", "매슬로우", "허즈버그", "맥그리거", "위생 이론", "x-y이론", "동기 이론", "동기-위생", "욕구단계", "인적자원",
        "의사소통", "소통 관리", "의사소통 채널", "의사소통수", "채널 수"
    ],

    # 4. 프로젝트 관리
    "4-a. 프로젝트관리 관련 표준 및 가이드": [
        "ks a iso 21500", "iso 21500", "pmbok guide", "pmbok 가이드"
    ],
    "4-b. 통합/범위/자원/일정/위험/품질/성과/조달/변화 관리 등": [
        "pmbok", "통합 관리", "범위 관리", "품질 관리", "자원 관리", "조달 관리", "이해관계자", "지식 영역", "도메인", "프로젝트 헌장",
        "cpm", "pert", "주공정", "임계경로", "임계 경로", "여유시간", "float", "주공정법", "es", "ef", "ls", "lf", "총여유", "자유여유",
        "evm", "획득가치", "기성고", "cpi", "spi", "cvr", "sv", "bac", "eac", "tcpi", "획득 가치", "일정분산", "비용분산",
        "위험 관리", "리스크 식별", "정량적 위험", "정성적 위험", "위험 대응", "위험 회피", "위험 완화", "위험 전이", "위험 수용",
        "품질 통제", "관리도", "파레토", "인과관계", "fishbone", "통계적 품질", "특성요인도", "산점도", "체크시트", "히스토그램",
        "변경 관리", "변경 통제", "ccb", "변경통제", "변화 관리", "성과 관리"
    ]
}

# PM 11개 중단원 설명 메타데이터 정의
CONCEPT_METADATA = {
    # 1. 정보화 및 소프트웨어 관련 법/제도 및 국내외 지침, 가이드
    "1-a. 정보화 및 소프트웨어 관련 법령 및 고시, 가이드": {
        "core_concept": "공공 SW사업 관리 법령 및 지능정보화 정책 체계",
        "features": "소프트웨어 진흥법령 상의 중소기업 참여제한 예외 요건, 지능정보화 기본계획, 공공데이터 개방 및 데이터베이스 표준화 지침을 검증합니다.",
        "scope": "법/제도/지침 -> 정보화/SW 법령 및 고시"
    },
    "1-b. 계약 관련 법령 및 예규": {
        "core_concept": "국가 조달 계약 법적 규격 및 예규 수칙",
        "features": "국가계약법의 입찰보증금 규정, 협상에 의한 계약체결기준(평가비중 90:10, 85% 적격요건), 용역계약일반조건 상의 대가조정 요건 및 하도급 비율 지침이 빈출됩니다.",
        "scope": "법/제도/지침 -> 계약 법령 및 예규"
    },
    "1-c. 대가산정 관련 고시 및 가이드": {
        "core_concept": "소프트웨어 사업 대가 산정 표준 모델",
        "features": "기능점수(FP) 간이법 및 상세법의 보정계수 산정법, 엔지니어링사업대가 기준에 기초한 실비정산 가산방식 적용을 다룹니다.",
        "scope": "법/제도/지침 -> SW 대가산정 기준"
    },
    "1-d. IT거버넌스, CoBIT 등 국외 관련 지침": {
        "core_concept": "기업 IT 자산 통제 및 글로벌 거버넌스 프레임워크",
        "features": "COBIT의 거버넌스 및 매니지먼트 5대 영역 구분과 성숙도 평가 모델을 중점 질문합니다.",
        "scope": "법/제도/지침 -> IT 거버넌스 및 COBIT"
    },

    # 2. 감리 관련 법제도 및 관련 기술
    "2-a. 전자정부법, 정보시스템 감리기준 등 감리 법제도": {
        "core_concept": "국가 의무감리 대상 기준 및 감리원 윤리/배치 기준",
        "features": "전자정부법상 의무감리 조건(5억 이상 개발 등), 감리인 수행 규격, 의견 진술서 처리 절차 및 감리 계획서 제출 기한(15일)을 정확히 묻습니다.",
        "scope": "감리 법제도/기술 -> 감리 법제도"
    },
    "2-b. 정보시스템 인프라 관련 법제도": {
        "core_concept": "정보시스템 물리/기술 인프라 구축 관련 규정",
        "features": "정보시스템의 안정성 확보를 위한 인프라 법제도적 준수 사항을 검증합니다.",
        "scope": "감리 법제도/기술 -> 인프라 법제도"
    },
    "2-c. 정보시스템 감리 관련 가이드": {
        "core_concept": "감리 발주 및 분야별 수행 세부 가이드",
        "features": "감리원 윤리 가이드, 감리수행가이드 및 유지보수 감리 점검 가이드 상의 점검 단계와 항목을 다룹니다.",
        "scope": "감리 법제도/기술 -> 감리 수행 가이드"
    },

    # 3. 조직 관리론
    "3-a. 조직구조, 조직이론, 조직설계": {
        "core_concept": "프로젝트 수행 최적 조직 구조 설계 및 역량 분석",
        "features": "기능형, 매트릭스형(강한/약한/균형), 프로젝트 전담형 조직 간의 자원 활용성 및 의사결정 권한 범위를 주로 비교합니다.",
        "scope": "조직 관리론 -> 조직 설계 및 구조"
    },
    "3-b. 인적 자원관리, 의사소통관리": {
        "core_concept": "인적 동기부여 이론 및 의사소통 채널 산식",
        "features": "허즈버그 2요인설(동기/위생), 맥그리거 X-Y이론, 매슬로우 욕구계층 및 N명 이해관계자 간 소통 채널 수 계산 공식 [N*(N-1)/2] 등이 매년 출제됩니다.",
        "scope": "조직 관리론 -> 인적/의사소통 관리"
    },

    # 4. 프로젝트 관리
    "4-a. 프로젝트관리 관련 표준 및 가이드": {
        "core_concept": "글로벌 프로젝트 관리 국제 표준 및 체계",
        "features": "KS A ISO 21500 표준의 프로세스 맵 및 PMBOK 가이드의 프로젝트 관리 12대 원칙 및 8대 성과 도메인의 정의를 다룹니다.",
        "scope": "프로젝트 관리 -> PM 표준 및 가이드"
    },
    "4-b. 통합/범위/자원/일정/위험/품질/성과/조달/변화 관리 등": {
        "core_concept": "PMBOK 10대 지식 영역별 정량 통제 기법",
        "features": "주공정법(CPM)의 임계경로 및 여유시간(Float) 연산, 기성고 분석(EVM)의 CPI/SPI/EAC 공식, 위험 대응 전략(회피/완화/전이/수용) 및 통계적 품질 도구(파레토, 관리도)의 쓰임새를 핵심적으로 평가합니다.",
        "scope": "프로젝트 관리 -> 지식 영역별 통제"
    }
}

# 4대 대단원 매핑
TOPIC_CATEGORIES = {
    "1-a. 정보화 및 소프트웨어 관련 법령 및 고시, 가이드": "1. 정보화 및 소프트웨어 관련 법/제도 및 국내외 지침, 가이드",
    "1-b. 계약 관련 법령 및 예규": "1. 정보화 및 소프트웨어 관련 법/제도 및 국내외 지침, 가이드",
    "1-c. 대가산정 관련 고시 및 가이드": "1. 정보화 및 소프트웨어 관련 법/제도 및 국내외 지침, 가이드",
    "1-d. IT거버넌스, CoBIT 등 국외 관련 지침": "1. 정보화 및 소프트웨어 관련 법/제도 및 국내외 지침, 가이드",
    
    "2-a. 전자정부법, 정보시스템 감리기준 등 감리 법제도": "2. 감리 관련 법제도 및 관련 기술",
    "2-b. 정보시스템 인프라 관련 법제도": "2. 감리 관련 법제도 및 관련 기술",
    "2-c. 정보시스템 감리 관련 가이드": "2. 감리 관련 법제도 및 관련 기술",
    
    "3-a. 조직구조, 조직이론, 조직설계": "3. 조직 관리론",
    "3-b. 인적 자원관리, 의사소통관리": "3. 조직 관리론",
    
    "4-a. 프로젝트관리 관련 표준 및 가이드": "4. 프로젝트 관리",
    "4-b. 통합/범위/자원/일정/위험/품질/성과/조달/변화 관리 등": "4. 프로젝트 관리"
}

def crop_question_images(pdf_path, year, output_dir):
    """[공통 모듈 위임] PDF로부터 PM 과목 문항 영역을 추출하여 이미지로 저장하고 위치 좌표를 반환"""
    local_img_dir = r"e:\jolly-carson\reports\images"
    artifact_img_dir = os.path.join(ARTIFACT_DIR, "images")
    return image_cropper.get_question_positions_and_crop(
        pdf_path, year, "PM", local_img_dir, artifact_img_dir, force_crop=FORCE_CROP
    )

def extract_pdf_clean(file_path):
    cleaned_text = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            if i == 0:
                continue
            width = page.width
            height = page.height
            bands_count = 4 if width > height else 2
            page_text_parts = []
            
            for b in range(bands_count):
                x0 = (width / bands_count) * b
                x1 = (width / bands_count) * (b + 1)
                bbox = (x0, 0, x1, height)
                
                cropped_page = page.crop(bbox)
                text = cropped_page.extract_text()
                if text:
                    page_text_parts.append(text)
                    
            cleaned_text.append("\n".join(page_text_parts))
    return "\n\n=== NEW PAGE ===\n\n".join(cleaned_text)

def slice_pm_section(full_text):
    start_pattern = r"\b1\s*[\.\)]"
    end_pattern = r"\b26\s*[\.\)]"
    
    start_match = re.search(start_pattern, full_text)
    end_match = re.search(end_pattern, full_text)
    
    if start_match:
        start_idx = start_match.start()
        end_idx = end_match.start() if end_match else len(full_text)
        return full_text[start_idx:end_idx].strip()
    return ""

def parse_questions(pm_text):
    """문항 분절화 (직전 문제 발견 위치 이후부터 탐색하여 가짜 문제 번호 역행 오파싱 방지)"""
    questions = []
    last_idx = 0
    positions = {}
    
    # 1번부터 25번까지의 시작 위치를 순차적으로 탐색
    for num in range(1, 26):
        curr_pat = rf"(?<![\.\d]){num}\s*[\.\)]"
        curr_match = re.search(curr_pat, pm_text[last_idx:])
        if not curr_match:
            # 안전 폴백: 만약 검색 범위 좁히기로 못 찾을 경우 전체 영역 재탐색
            curr_match = re.search(curr_pat, pm_text)
            if not curr_match:
                continue
            start_pos = curr_match.start()
        else:
            start_pos = last_idx + curr_match.start()
            
        positions[num] = start_pos
        last_idx = start_pos + len(curr_match.group(0))
        
    sorted_nums = sorted(list(positions.keys()))
    for i, num in enumerate(sorted_nums):
        start_pos = positions[num]
        if i + 1 < len(sorted_nums):
            next_num = sorted_nums[i + 1]
            end_pos = positions[next_num]
            q_body = pm_text[start_pos:end_pos].strip()
        else:
            q_body = pm_text[start_pos:].strip()
            
        if "④" in q_body:
            clean_match = re.search(r"④.*?(?=(?:\r?\n)\s*(?!(?:1|2|3|4)\b)\d+\s*[\.\)])", q_body, re.DOTALL)
            if clean_match:
                q_body = q_body[:clean_match.end()].strip()
            
            for separator in ["소프트웨어공학", "소프트웨어 공학", "=== NEW PAGE ===", "데이터베이스", "시스템구조", "보안"]:
                sep_match = re.search(rf"\n\s*{separator}", q_body)
                if sep_match:
                    q_body = q_body[:sep_match.start()].strip()
            
        questions.append({"num": num, "body": q_body})
    return questions

def load_exam_database_dict(subject_code):
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    js_path = os.path.join(base_dir, "reports", "exam_db", f"{subject_code.lower()}_db.js")
    
    # 폴백: 개별 DB가 아직 없는 경우 공통 DB 참조
    if not os.path.exists(js_path):
        js_path = os.path.join(base_dir, "reports", "exam_database.js")
        
    if not os.path.exists(js_path):
        return {}
        
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Greedy 매칭 패턴 ((\{[\s\S]*\}))을 적용하여 지문 내 C++ 클래스 마감 기호(};) 오인식 방지
    match = re.search(r"const\s+examDatabase\s*=\s*(\{[\s\S]*\});", content)
    if not match:
        return {}
        
    js_obj_str = match.group(1)
    try:
        import json
        return json.loads(js_obj_str)
    except Exception as e:
        # 정규식 파서 폴백 (JSON Decode 실패 시 대응)
        pairs = re.findall(r'"(\d{4}_\d+)":\s*"(.*?)"(?=,\s*"|\s*\})', js_obj_str, re.DOTALL)
        parsed = {}
        for k, v in pairs:
            parsed[k] = v.replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')
        return parsed

def run_extraction_and_mapping():
    question_db = {}
    concept_map = {concept: [] for concept in CONCEPT_KEYWORDS}
    concept_map["[기타]"] = []
    
    filename_lower = os.path.basename(__file__).lower()
    if "_db_" in filename_lower:
        subject_code = "DB"
    elif "_pm_" in filename_lower:
        subject_code = "PM"
    elif "_se_" in filename_lower:
        subject_code = "SE"
    elif "_sa_" in filename_lower:
        subject_code = "SA"
    elif "_sc_" in filename_lower:
        subject_code = "SC"
    else:
        subject_code = "UNKNOWN"
        
    exam_db_dict = load_exam_database_dict(subject_code)
    
    print(f"[1/3] {subject_code} 과목 기출문제 로딩 및 공식범위 매핑 중...")
    
    for year in range(2015, 2027):
        if subject_code == "DB":
            q_start, q_end = 51, 75
        elif subject_code == "PM":
            q_start, q_end = 1, 25
        elif subject_code == "SE":
            q_start, q_end = 26, 50
        elif subject_code == "SA":
            q_start, q_end = 76, 100
        elif subject_code == "SC":
            q_start, q_end = 101, 120
        else:
            continue
            
        for num in range(q_start, q_end + 1):
            key = f"{year}_{num}"
            q_text_clean = exam_db_dict.get(key)
            if not q_text_clean:
                continue
                
            question_db[key] = q_text_clean
            
            body_lower = q_text_clean.lower()
            matched_concepts = []
            for concept, keywords in CONCEPT_KEYWORDS.items():
                for kw in keywords:
                    if re.match(r"^[a-zA-Z0-9\-\_\/]+$", kw):
                        pattern = rf"(?<![a-zA-Z0-9]){re.escape(kw.lower())}(?![a-zA-Z0-9])"
                        if re.search(pattern, body_lower):
                            matched_concepts.append(concept)
                            break
                    else:
                        if kw.lower() in body_lower:
                            matched_concepts.append(concept)
                            break
                            
            if not matched_concepts:
                matched_concepts.append("[기타]")
                            
            for concept in matched_concepts:
                concept_map[concept].append({
                    "year": year,
                    "num": num
                })
                
    return question_db, concept_map

def build_html_content(question_db, concept_map):
    sorted_concepts = []
    for concept, items in concept_map.items():
        years = sorted(list(set([it["year"] for it in items])))
        sorted_questions = sorted(items, key=lambda x: (x["year"], x["num"]), reverse=True)
        rep_question_text = ""
        rep_year = ""
        rep_num = ""
        if sorted_questions:
            rep_q = sorted_questions[0]
            rep_year = rep_q["year"]
            rep_num = rep_q["num"]
            rep_key = f"{rep_year}_{rep_num}"
            rep_question_text = question_db.get(rep_key, "대표 문제를 가져올 수 없습니다.")
            
        if concept == "[기타]":
            meta = {
                "core_concept": "기출문제 중 가이드라인 세부 중단원에 포함되지 않는 복합/기타 문항들입니다.",
                "features": "기타 분류 문제를 검토하여 변형 기출을 대비하세요.",
                "scope": "기타 영역"
            }
        else:
            meta = CONCEPT_METADATA.get(concept, {
                "core_concept": "세부 범위 매핑 준비 중",
                "features": "분석 준비 중",
                "scope": "기타 영역"
            })
        
        sorted_concepts.append({
            "concept": concept,
            "category": TOPIC_CATEGORIES.get(concept, "기타"),
            "count": len(items),
            "years": years,
            "questions": sorted_questions,
            "core_concept": meta["core_concept"],
            "features": meta["features"],
            "scope": meta["scope"],
            "rep_question": rep_question_text,
            "rep_year": rep_year,
            "rep_num": rep_num
        })
        
    # [기타]는 항상 마지막으로 정렬, 그 외에는 가이드라인 중단원 알파벳 순서(1-a, 1-b, 2-a 등)로 정렬
    sorted_concepts.sort(key=lambda x: (1 if x["concept"] == "[기타]" else 0, x["concept"]))
    
    db_json = json.dumps(question_db, ensure_ascii=False, indent=2)
    mapping_json = json.dumps(sorted_concepts, ensure_ascii=False, indent=2)
    
        # ------------------[ 공통 템플릿 리팩토링 적용 ]------------------
    filename_lower = os.path.basename(__file__).lower()
    dashboard_type = "official" if "official" in filename_lower else "frequent"
    
    if "db" in filename_lower:
        subject_code, subject_name = "DB", "데이터베이스"
    elif "pm" in filename_lower:
        subject_code, subject_name = "PM", "프로젝트관리"
    elif "se" in filename_lower:
        subject_code, subject_name = "SE", "소프트웨어공학"
    elif "sa" in filename_lower:
        subject_code, subject_name = "SA", "시스템 아키텍처"
    elif "sc" in filename_lower:
        subject_code, subject_name = "SC", "보안"
    else:
        subject_code, subject_name = "UNKNOWN", "알수없음"

    filter_section_html = ""
    if dashboard_type == "official":
        categories = sorted(list(set(TOPIC_CATEGORIES.values())))
        filter_buttons = [f'<button class="filter-btn active" onclick="filterCategory(\'all\')">전체 대단원</button>']
        for cat in categories:
            filter_buttons.append(f'<button class="filter-btn" onclick="filterCategory(\'{cat}\')">{cat}</button>')
        filter_section_html = f'<div class="filter-section">{"".join(filter_buttons)}</div>'

    from build_utils import get_dashboard_html_template
    final_html = get_dashboard_html_template(
        dashboard_type=dashboard_type,
        subject_code=subject_code,
        subject_name=subject_name,
        mapping_json=mapping_json,
        filter_section_html=filter_section_html
    )
    return final_html

def main():
    question_db, concept_map = run_extraction_and_mapping()
    update_shared_db(question_db, "PM")
    html_content = build_html_content(question_db, concept_map)
    
    local_path, artifact_path = get_output_paths("pm_official_scopes.html")
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[로컬] 저장 완료: {local_path}")
    
    os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[아티팩트] 저장 완료: {artifact_path}")

if __name__ == "__main__":
    main()
