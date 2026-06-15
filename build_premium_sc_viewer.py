# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

"""
[초프리미엄 보안(SC) 기출문제 뷰어 자동 빌더]
- 목적: 2015년~2026년 기출 PDF에서 SC 과목 전체 문항(101~120번)을 추출하고,
  12대 세부 토픽 사전을 기반으로 정형화된 빈출 분석 대시보드 웹앱(sc_frequent_concepts.html)을 생성합니다.
"""

import os
from build_utils import get_output_paths, update_shared_db
import sys
import re
import json
# import pdfplumber
# import fitz

# 공통 이미지 크롭 모듈 임포트
# import image_cropper

FORCE_CROP = "--force" in sys.argv or "--force-crop" in sys.argv

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

CONCEPT_KEYWORDS = {
    "대칭키 및 비대칭키 암호화 알고리즘 비교 (AES/RSA/ECC)": ["대칭키", "비대칭키", "rsa", "des", "aes", "seed", "aria", "ecc", "공개키", "블록 암호", "스트림 암호"],
    "암호학적 해시 함수 및 충돌 저항성 (SHA/MD5)": ["해시 함수", "sha-256", "md5", "충돌 저항성", "일방향성", "해시함수", "충돌 회피"],
    "네트워크 차단 및 보안 장비 (방화벽/IDS/IPS)": ["방화벽", "ids", "ips", "침입탐지", "침입방지", "dmz", "패킷 필터링", "상태기반 방화벽"],
    "대표적 웹 보안 취약점 공격 기법 (SQLi/XSS/CSRF)": ["sql 인젝션", "sql injection", "xss", "크로스 사이트", "취약점", "버퍼 오버플로우", "csrf", "사이트 간 요청 위조"],
    "클라우드 보안인증제도 (CSAP) 운영 기준": ["csap", "클라우드 보안인증", "보안인증제도", "인증기준"],
    "인증 프레임워크 OAuth 2.0 프로토콜": ["oauth", "토큰", "인증 프레임워크", "인증서", "권한 부여"],
    "콘텐츠 저작권 통제 기술 (DRM / 워터마크)": ["drm", "저작권 관리", "워터마킹", "핑거프린팅", "디지털 저작권"],
    "SW 개발보안 시큐어 코딩 및 7대 취약 영역": ["시큐어 코딩", "시큐어코딩", "개발보안", "입력데이터 검증", "보안 취약점", "행정안전부 가이드"],
    "개인정보보호법 고유식별정보 및 가명조치 기술": ["개인정보", "가명정보", "익명정보", "비식별", "개인정보보호법", "고유식별정보", "가명 조치"],
    "정보보호 관리체계 ISMS-P 인증 기준": ["isms", "isms-p", "관리체계 인증", "인증 기준"],
    "전송 계층 보안 암호 프로토콜 (SSL/TLS / IPsec)": ["ssl", "tls", "https", "ipsec", "vpn", "보안 소켓"],
    "보안 공격 유형 및 대응 (DDoS/APT/Ransomware)": ["ddos", "디도스", "랜섬웨어", "악성코드", "피싱", "스미싱", "apt", "사회공학"]
}

CONCEPT_METADATA = {
    "대칭키 및 비대칭키 암호화 알고리즘 비교 (AES/RSA/ECC)": {
        "core_concept": "키의 형태에 따른 데이터 기밀성 보장 알고리즘 특징 및 연산 효율 대조",
        "features": "대칭키(블록 암호: AES/SEED, 스트림 암호: RC4)와 비대칭키(RSA, ECC - 짧은 키 길이로 고효율)의 연산 속도 및 키 관리 측면 장단점을 주로 출제합니다.",
        "scope": "공통 보안 기술 -> 암호학 -> 암호 알고리즘"
    },
    "암호학적 해시 함수 및 충돌 저항성 (SHA/MD5)": {
        "core_concept": "일방향성을 가진 고정 길이 메시지 다이제스트 산출 기술",
        "features": "역상 저항성(다이제스트에서 평문 유추 불가능), 제2역상 저항성(동일 다이제스트를 내는 평문 찾기 불가능), 충돌 저항성(동일 다이제스트를 내는 평문 쌍 찾기 불가능)을 질문합니다.",
        "scope": "공통 보안 기술 -> 암호학 -> 해시 함수"
    },
    "네트워크 차단 및 보안 장비 (방화벽/IDS/IPS)": {
        "core_concept": "비인가 패킷 흐름을 탐지/차단하여 사설망을 보호하는 게이트웨이 보안 시스템",
        "features": "방화벽(IP/Port 제어), IDS(오용/이상 탐지 및 모니터링), IPS(인라인 실시간 위협 차단)의 장비 배치 및 탐지 수준 차이를 구분하는 문제가 빈출됩니다.",
        "scope": "네트워크 및 시스템 보안 -> 네트워크 보안"
    },
    "대표적 웹 보안 취약점 공격 기법 (SQLi/XSS/CSRF)": {
        "core_concept": "입력값 검증 미흡에 따른 웹 서비스 상의 악성 스크립트 및 쿼리 실행 해킹",
        "features": "SQL Injection(악성 SQL 구문 삽입), XSS(사용자 브라우저에서 스크립트 실행 -> 세션 탈취), CSRF(사용자의 권한을 도용하여 서버에 불법 요청 전송)의 원리와 방어책을 묻습니다.",
        "scope": "네트워크 및 시스템 보안 -> 웹 보안 취약점"
    },
    "클라우드 보안인증제도 (CSAP) 운영 기준": {
        "core_concept": "공공기관에 클라우드 서비스를 제공하는 민간 사업자의 보안성 평가 인증 표준",
        "features": "CSAP 등급제(상/중/하)에 따른 데이터 물리적 분리(망분리) 의무 요건 및 시나리오별 적합 등급 선정 조항을 확인하는 문제가 기출됩니다.",
        "scope": "응용 및 신기술 보안 -> 클라우드 보안인증"
    },
    "인증 프레임워크 OAuth 2.0 프로토콜": {
        "core_concept": "제3자 애플리케이션에 사용자 리소스 접근 권한을 안전하게 위임하는 표준 프레임워크",
        "features": "4가지 권한 부여 승인 코드 방식(Authorization Code, Implicit, Resource Owner Password, Client Credentials)의 흐름과 Access Token 발급 절차를 주로 다룹니다.",
        "scope": "응용 및 신기술 보안 -> 접근 통제 및 인증"
    },
    "콘텐츠 저작권 통제 기술 (DRM / 워터마크)": {
        "core_concept": "디지털 콘텐츠 유통 전 과정의 저작권 보호 및 무단 배포 방지 기술",
        "features": "DRM 패키징 구성 요소(클리어링 하우스, 패키저, 라이선스 서버 등)의 역할과 워터마킹(비가시적 저작권 정보 삽입) 및 핑거프린팅(구매자 정보 삽입 -> 추적)의 특징 차이를 묻습니다.",
        "scope": "응용 및 신기술 보안 -> 디지털 콘텐츠 보안"
    },
    "SW 개발보안 시큐어 코딩 및 7대 취약 영역": {
        "core_concept": "SW 설계/구현 단계부터 보안 취약점을 예방하기 위해 준수하는 개발 가이드",
        "features": "행정안전부 시큐어코딩 7대 취약 영역(입력데이터 검증 및 표현, 보안기능, 시간 및 상태, 에러 처리, 코드오류, 캡슐화, API 오용)의 세부 명세와 소스코드 분석이 단골 출제됩니다.",
        "scope": "개발 및 운영 보안 -> 소프트웨어 개발 보안"
    },
    "개인정보보호법 고유식별정보 및 가명조치 기술": {
        "core_concept": "개인정보 오남용 방지를 위한 법적 준수사항 및 데이터 비식별 처리 기법",
        "features": "고유식별정보(주민등록번호, 여권번호 등)의 처리 요건, 가명정보(추가 정보 없이는 식별 불가 -> 통계/연구용 활용)와 익명정보의 차이, 그리고 비식별 기술(K-익명성, L-다양성)을 묻습니다.",
        "scope": "정보보호 법규 및 개인정보보호 -> 개인정보 비식별 조치"
    },
    "정보보호 관리체계 ISMS-P 인증 기준": {
        "core_concept": "종합 정보보호 및 개인정보보호 관리체계의 적합성을 평가하는 국가 공인 인증제도",
        "features": "3대 영역인 관리체계 수립/운영(16개), 보호대책 요구사항(64개), 개인정보 처리 단계별 요구사항(22개)의 하위 통제 항목 구별과 인증 의무 대상자 요건이 기출됩니다.",
        "scope": "정보보호 법규 및 개인정보보호 -> 정보보호 인증"
    },
    "전송 계층 보안 암호 프로토콜 (SSL/TLS / IPsec)": {
        "core_concept": "네트워크 통신망을 지나는 패킷의 위변조 방지 및 암호화 전송 표준 프로토콜",
        "features": "TLS 레코드 및 핸드셰이크 프로토콜의 단계별 동작 원리, 그리고 IPsec의 두 가지 모드(전송 모드: 페이로드만 암호화, 터널 모드: 헤더 포함 전체 암호화) 차이를 대조 질문합니다.",
        "scope": "공통 보안 기술 -> 암호학 -> 전송 프로토콜"
    },
    "보안 공격 유형 및 대응 (DDoS/APT/Ransomware)": {
        "core_concept": "시스템 자원을 고갈시키거나 표적 공격을 감행하는 악의적인 네트워크 해킹 및 악성코드 형태",
        "features": "DDoS 공격 유형(HTTP Get Flooding, DRDoS - 반사 서버 이용), APT(지속적 표적 공격 수명주기), 랜섬웨어의 암호화 피해 특징을 사례 기반으로 출제합니다.",
        "scope": "네트워크 및 시스템 보안 -> 시스템 해킹"
    }
}

TOPIC_CATEGORIES = {
    "대칭키 및 비대칭키 암호화 알고리즘 비교 (AES/RSA/ECC)": "공통 보안 기술",
    "암호학적 해시 함수 및 충돌 저항성 (SHA/MD5)": "공통 보안 기술",
    "네트워크 차단 및 보안 장비 (방화벽/IDS/IPS)": "네트워크 및 시스템 보안",
    "대표적 웹 보안 취약점 공격 기법 (SQLi/XSS/CSRF)": "네트워크 및 시스템 보안",
    "클라우드 보안인증제도 (CSAP) 운영 기준": "응용 및 신기술 보안",
    "인증 프레임워크 OAuth 2.0 프로토콜": "응용 및 신기술 보안",
    "콘텐츠 저작권 통제 기술 (DRM / 워터마크)": "응용 및 신기술 보안",
    "SW 개발보안 시큐어 코딩 및 7대 취약 영역": "개발 및 운영 보안",
    "개인정보보호법 고유식별정보 및 가명조치 기술": "정보보호 법규 및 개인정보보호",
    "정보보호 관리체계 ISMS-P 인증 기준": "정보보호 법규 및 개인정보보호",
    "전송 계층 보안 암호 프로토콜 (SSL/TLS / IPsec)": "공통 보안 기술",
    "보안 공격 유형 및 대응 (DDoS/APT/Ransomware)": "네트워크 및 시스템 보안"
}

def crop_question_images(pdf_path, year, output_dir):
    """[공통 모듈 위임] PDF로부터 SC 과목 문항 영역을 추출하여 이미지로 저장하고 위치 좌표를 반환"""
    local_img_dir = r"e:\jolly-carson\reports\images"
    artifact_img_dir = r"C:\Users\DCCIS040000\.gemini\antigravity-ide\brain\7e1fd111-1dc1-495d-82a1-c40573600184\images"
    return image_cropper.get_question_positions_and_crop(
        pdf_path, year, "SC", local_img_dir, artifact_img_dir, force_crop=FORCE_CROP
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

def slice_sc_section(full_text):
    start_pattern = r"\b101\s*[\.\)]"
    end_pattern = r"\b121\s*[\.\)]"
    
    start_match = re.search(start_pattern, full_text)
    end_match = re.search(end_pattern, full_text)
    
    if start_match:
        start_idx = start_match.start()
        end_idx = end_match.start() if end_match else len(full_text)
        return full_text[start_idx:end_idx].strip()
    return ""

def parse_questions(sc_text):
    questions = []
    for num in range(101, 121):
        curr_pat = rf"(?<![\.\d]){num}\s*[\.\)]"
        next_pat = rf"(?<![\.\d]){num+1}\s*[\.\)]"
        
        curr_match = re.search(curr_pat, sc_text)
        if not curr_match:
            continue
            
        start_pos = curr_match.start()
        next_match = re.search(next_pat, sc_text)
        
        if next_match:
            end_pos = next_match.start()
            q_body = sc_text[start_pos:end_pos].strip()
        else:
            q_body = sc_text[start_pos:].strip()
            
        # [방어 코드] 보기 ④번 이후에 다단 텍스트 등의 영향으로 타 문제(예: 42번)가 달라붙는 버그 방지
        if "④" in q_body:
            clean_match = re.search(r"④.*?(?=(?:\r?\n)\s*(?!(?:1|2|3|4)\b)\d+\s*[\.\)])", q_body, re.DOTALL)
            if clean_match:
                q_body = q_body[:clean_match.end()].strip()
            
            # 과목 경계를 알리는 한글 구분자나 페이지 지시문이 붙어 있으면 잘라냅니다.
            for separator in ["프로젝트관리", "소프트웨어", "=== NEW PAGE ==="]:
                sep_match = re.search(rf"\n\s*{separator}", q_body)
                if sep_match:
                    q_body = q_body[:sep_match.start()].strip()
            
        questions.append({"num": num, "body": q_body})
    return questions

def load_exam_database_dict(subject_code):
    base_dir = os.path.dirname(os.path.abspath(__file__))
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
                "core_concept": "기출문제 중 기존 세부 개념으로 정의되지 않은 기타 문항들입니다.",
                "features": "기타 분류된 문제 리스트를 검토하여 누락된 개념이나 특이 문제 유형을 점검합니다.",
                "scope": "기타"
            }
        else:
            meta = CONCEPT_METADATA.get(concept, {
                "core_concept": "세부 요건 정의 준비 중",
                "features": "분석 준비 중",
                "scope": "기타"
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
        
    # [기타]는 항상 정렬의 맨 마지막에 위치하도록 키 조정 (-1로 부여하여 reverse=True일 때 맨 뒤로 가도록 설정)
        # 3회 미만 출제된 개념들의 기출문제를 [기타] 카테고리로 수집
    discarded_questions = []
    for c in sorted_concepts:
        if c["count"] < 3 and c["concept"] != "[기타]":
            discarded_questions.extend(c["questions"])
            
    # [기타] 카테고리 확보
    etc_concept = None
    for c in sorted_concepts:
        if c["concept"] == "[기타]":
            etc_concept = c
            break
            
    if etc_concept is not None and discarded_questions:
        existing = set((q["year"], q["num"]) for q in etc_concept["questions"])
        for q in discarded_questions:
            if (q["year"], q["num"]) not in existing:
                etc_concept["questions"].append(q)
                existing.add((q["year"], q["num"]))
        # [기타] 카테고리 갱신
        etc_concept["count"] = len(etc_concept["questions"])
        etc_concept["years"] = sorted(list(set([q["year"] for q in etc_concept["questions"]])))

    sorted_concepts.sort(key=lambda x: (-1 if x["concept"] == "[기타]" else x["count"]), reverse=True)
    
    # 3회 이상 출제된 세부 토픽만 필터링하되, [기타]는 항상 표시
    filtered_concepts = [c for c in sorted_concepts if c["count"] >= 3 or c["concept"] == "[기타]"]
    
    db_json = json.dumps(question_db, ensure_ascii=False, indent=2)
    mapping_json = json.dumps(filtered_concepts, ensure_ascii=False, indent=2)
    
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
    update_shared_db(question_db, "SC")
    html_content = build_html_content(question_db, concept_map)
    
    local_path, artifact_path = get_output_paths("sc_frequent_concepts.html")
    
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
