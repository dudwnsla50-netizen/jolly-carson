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
    
    html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>보안 12개년 빈출 개념 정밀 뷰어</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #080b13;
            --card-bg: rgba(17, 24, 39, 0.75);
            --border-color: rgba(255, 255, 255, 0.06);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
            --accent-violet: #8b5cf6;
            --accent-blue: #3b82f6;
            --accent-gradient: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
            --accent-glow: rgba(139, 92, 246, 0.12);
            --success: #10b981;
            --card-hover-border: rgba(139, 92, 246, 0.3);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Inter', 'Noto Sans KR', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2.5rem 1.5rem;
            min-height: 100vh;
            background-image: 
                radial-gradient(at 0% 0%, rgba(139, 92, 246, 0.06) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(59, 130, 246, 0.06) 0px, transparent 50%);
            background-attachment: fixed;
        }

        .container {
            max-width: 1050px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            margin-bottom: 2.5rem;
        }

        header h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 2.6rem;
            font-weight: 800;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.6rem;
            letter-spacing: -0.03em;
        }

        header p.subtitle {
            font-size: 1rem;
            color: var(--text-secondary);
        }

        .meta-badges {
            display: flex;
            justify-content: center;
            gap: 0.8rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }

        .badge {
            background: var(--border-color);
            border: 1px solid rgba(255, 255, 255, 0.04);
            color: var(--text-secondary);
            padding: 0.35rem 0.9rem;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 500;
            backdrop-filter: blur(8px);
        }

        .badge.accent {
            background: rgba(139, 92, 246, 0.12);
            border-color: rgba(139, 92, 246, 0.25);
            color: #c084fc;
        }

        .filter-section {
            display: flex;
            justify-content: center;
            gap: 0.6rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }

        .filter-btn {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.45rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .filter-btn:hover, .filter-btn.active {
            border-color: var(--accent-violet);
            color: #ffffff;
            background: rgba(139, 92, 246, 0.08);
            box-shadow: 0 0 10px var(--accent-glow);
        }

        .accordion-list {
            display: flex;
            flex-direction: column;
            gap: 1.2rem;
            margin-bottom: 4rem;
        }

        .accordion-item {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            backdrop-filter: blur(10px);
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
        }

        .accordion-item:hover {
            border-color: var(--card-hover-border);
            box-shadow: 0 6px 20px var(--accent-glow);
        }

        .accordion-trigger {
            width: 100%;
            background: none;
            border: none;
            color: inherit;
            padding: 1.6rem 1.8rem;
            text-align: left;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
        }

        .card-header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
        }

        .card-title-group {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            flex-wrap: wrap;
        }

        .rank-badge {
            font-family: 'Outfit', sans-serif;
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--accent-blue);
        }

        .concept-title {
            user-select: text !important;
            -webkit-user-select: text !important;
            font-size: 1.2rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.02em;
        }

        .category-tag {
            background: rgba(59, 130, 246, 0.08);
            border: 1px solid rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            padding: 0.15rem 0.45rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .freq-count-badge {
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.15);
            color: var(--success);
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 700;
        }

        .card-meta-grid {
            display: grid;
            grid-template-columns: 90px 1fr;
            row-gap: 0.5rem;
            column-gap: 0.8rem;
            width: 100%;
            font-size: 0.88rem;
            border-top: 1px solid rgba(255, 255, 255, 0.04);
            padding-top: 0.8rem;
            margin-top: 0.2rem;
        }

        .meta-label {
            color: var(--text-muted);
            font-weight: 600;
        }

        .meta-value {
            color: var(--text-secondary);
            word-break: keep-all;
        }

        .meta-value.accent {
            color: #c8a2c8;
        }

        .accordion-trigger .arrow {
            transition: transform 0.3s ease;
            color: var(--text-muted);
            font-size: 0.9rem;
        }

        .accordion-item.active .accordion-trigger .arrow {
            transform: rotate(180deg);
            color: var(--accent-violet);
        }

        .accordion-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            background: rgba(0, 0, 0, 0.18);
        }

        .accordion-inner {
            padding: 1.6rem 1.8rem;
            border-top: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            gap: 1.2rem;
        }

        .section-title {
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 700;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            padding-bottom: 0.3rem;
            margin-top: 0.2rem;
        }

        .year-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .year-btn {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.35rem 0.8rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
        }

        .year-btn:hover {
            background: var(--accent-gradient);
            border-color: transparent;
            box-shadow: 0 4px 10px rgba(59, 130, 246, 0.25);
            transform: translateY(-1px);
        }

        .year-btn.active-btn {
            background: var(--accent-gradient);
            border-color: transparent;
            box-shadow: 0 4px 10px rgba(139, 92, 246, 0.3);
            color: #ffffff;
        }

        .year-btn .num-label {
            opacity: 0.7;
            font-size: 0.7rem;
        }

        .inline-question-viewer {
            background: #090d16;
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 8px;
            padding: 1.2rem;
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
            transition: all 0.3s ease;
        }

        .viewer-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            padding-bottom: 0.5rem;
        }

        .viewer-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: #60a5fa;
            font-family: 'Outfit', sans-serif;
        }

        .viewer-close-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 600;
            transition: color 0.2s;
        }

        .viewer-close-btn:hover {
            color: #ef4444;
        }

        .viewer-body {
            font-size: 0.92rem;
            line-height: 1.7;
            color: #d1d5db;
            white-space: pre-wrap;
            overflow-y: auto;
            max-height: 400px;
            padding-right: 0.5rem;
        }

        .viewer-body::-webkit-scrollbar {
            width: 6px;
        }
        .viewer-body::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.01);
        }
        .viewer-body::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
        }
        /* 뱃지 호버 효과 */
        a.badge {
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.2s ease;
        }
        a.badge:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.15);
            color: var(--text-primary) !important;
        }

        /* [검출 토픽 팝업 모달 스타일] */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(8, 11, 19, 0.85);
            backdrop-filter: blur(8px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.25s ease;
        }
        .modal-overlay.show {
            opacity: 1;
            pointer-events: auto;
        }
        .modal-card {
            background: rgba(17, 24, 39, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            width: 90%;
            max-width: 500px;
            max-height: 80%;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), 0 0 20px rgba(139, 92, 246, 0.15);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transform: scale(0.9);
            transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        .modal-overlay.show .modal-card {
            transform: scale(1);
        }
        .modal-card-header {
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-card-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.2rem;
            font-weight: 700;
            color: #ffffff;
            margin: 0;
        }
        .modal-close-x {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 1.4rem;
            cursor: pointer;
            transition: color 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .modal-close-x:hover {
            color: #ffffff;
        }
        .modal-card-body {
            padding: 1rem 1.5rem 1.5rem 1.5rem;
            overflow-y: auto;
        }
        .modal-topic-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .modal-topic-item {
            padding: 0.8rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            transition: all 0.2s ease;
            border-radius: 8px;
        }
        .modal-topic-item:hover {
            background: rgba(139, 92, 246, 0.08);
            transform: translateX(4px);
        }
        .modal-topic-name {
            font-size: 0.92rem;
            font-weight: 500;
            color: var(--text-primary);
        }
        .modal-topic-count {
            background: rgba(139, 92, 246, 0.15);
            color: #c084fc;
            border: 1px solid rgba(139, 92, 246, 0.2);
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.6rem;
            border-radius: 50px;
            white-space: nowrap;
        }
        span.badge[onclick]:hover {
            background: rgba(255, 255, 255, 0.08) !important;
            border-color: rgba(255, 255, 255, 0.15) !important;
            color: var(--text-primary) !important;
        }

        /* ==================================
           반응형 미디어 쿼리 (모바일 최적화)
        ================================== */
        @media (max-width: 768px) {
            body {
                padding: 1.5rem 0.8rem;
            }

            header h1 {
                font-size: 1.8rem;
                line-height: 1.3;
            }

            header p.subtitle {
                font-size: 0.88rem;
                padding: 0 0.5rem;
                word-break: keep-all;
            }

            .meta-badges {
                gap: 0.5rem;
            }

            .badge {
                padding: 0.25rem 0.6rem;
                font-size: 0.72rem;
            }

            .filter-section {
                gap: 0.4rem;
                margin-bottom: 1.5rem;
            }

            .filter-btn {
                padding: 0.35rem 0.7rem;
                font-size: 0.78rem;
            }

            .accordion-trigger {
                padding: 1.2rem 1rem;
                gap: 0.6rem;
            }

            .concept-title {
            user-select: text !important;
            -webkit-user-select: text !important;
                font-size: 1.05rem;
            }

            .rank-badge {
                font-size: 1rem;
            }

            .category-tag, .freq-count-badge {
                font-size: 0.7rem;
                padding: 0.1rem 0.35rem;
            }

            .card-meta-grid {
                grid-template-columns: 80px 1fr;
                font-size: 0.82rem;
                row-gap: 0.4rem;
            }

            .accordion-inner {
                padding: 1.2rem 1rem;
                gap: 1rem;
            }

            .section-title {
                font-size: 0.75rem;
            }

            .year-btn {
                padding: 0.3rem 0.6rem;
                font-size: 0.75rem;
            }

            .inline-question-viewer {
                padding: 0.9rem;
            }

            .viewer-body {
                font-size: 0.85rem;
                max-height: 300px;
            }
            .modal-card {
                width: 95%;
                max-height: 90%;
            }

            .modal-card-header {
                padding: 1rem;
            }

            .modal-card-title {
                font-size: 1.05rem;
            }

            .modal-card-body {
                padding: 0.8rem 1rem 1.2rem 1rem;
            }

            .modal-topic-item {
                padding: 0.6rem 0.8rem;
            }

            .modal-topic-name {
                font-size: 0.85rem;
            }
        }
    
        /* [설계 의도] 시안A: 모드 토글 스위치 및 최적화된 내비게이션 스타일 */
        .navigation-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1.2rem;
            margin-bottom: 2rem;
            width: 100%;
        }
        .mode-switch-wrapper {
            display: flex;
            align-items: center;
            gap: 1rem;
            background: rgba(255, 255, 255, 0.02);
            padding: 0.5rem 1.2rem;
            border-radius: 50px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(8px);
        }
        .mode-label {
            font-size: 0.88rem;
            font-weight: 600;
            transition: color 0.25s ease;
        }
        .switch {
            position: relative;
            display: inline-block;
            width: 46px;
            height: 24px;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: rgba(255, 255, 255, 0.08);
            transition: .3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 18px; width: 18px;
            left: 3px; bottom: 3px;
            background-color: #ffffff;
            transition: .3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        input:checked + .slider {
            background: var(--accent-gradient);
            box-shadow: 0 0 10px rgba(139, 92, 246, 0.2);
        }
        input:checked + .slider:before {
            transform: translateX(22px);
        }
        .slider.round { border-radius: 34px; }
        .slider.round:before { border-radius: 50%; }
        
        .badge.accent {
            background: rgba(139, 92, 246, 0.12) !important;
            border-color: rgba(139, 92, 246, 0.25) !important;
            color: #ffffff !important;
        }

    </style>
    <script src="exam_db/sc_db.js?v=20260613"></script>
</head>
<body>



<div class="container">
    <header>
        <h1>보안 기출 정밀 분석 대시보드</h1>
        <p class="subtitle">12개년 기출 전수 조사 기반 3회 이상 빈출 세부 토픽 분석 엔진</p>
        
                <div class="navigation-container">
            <div class="mode-switch-wrapper">
                <span class="mode-label" id="label-freq">🔥 빈출 개념순</span>
                <label class="switch">
                    <input type="checkbox" id="dashboard-mode-toggle" onchange="toggleDashboardMode(this)">
                    <span class="slider round"></span>
                </label>
                <span class="mode-label" id="label-official">📋 공식 범위순</span>
            </div>
            
            <div class="meta-badges" id="dynamic-nav-badges">
                <a href="#" class="badge home-badge" onclick="goToHome(event)" style="text-decoration: none; background: var(--accent-gradient); color: #ffffff; border: none; font-weight: 700;">🏠 퀴즈 홈으로</a>
                <a href="se_frequent_concepts.html" class="badge subject-badge" data-freq="se_frequent_concepts.html" data-official="se_official_scopes.html" style="text-decoration: none;">소프트웨어공학</a>
                <a href="pm_frequent_concepts.html" class="badge subject-badge" data-freq="pm_frequent_concepts.html" data-official="pm_official_scopes.html" style="text-decoration: none;">프로젝트 관리</a>
                <a href="db_frequent_concepts.html" class="badge subject-badge" data-freq="db_frequent_concepts.html" data-official="db_official_scopes.html" style="text-decoration: none;">데이터베이스</a>
                <a href="sa_frequent_concepts.html" class="badge subject-badge" data-freq="sa_frequent_concepts.html" data-official="sa_official_scopes.html" style="text-decoration: none;">시스템 아키텍처</a>
                <a href="sc_frequent_concepts.html" class="badge subject-badge" data-freq="sc_frequent_concepts.html" data-official="sc_official_scopes.html" style="text-decoration: none;">보안</a>
            </div>
        </div>
        
        <div class="meta-badges">
            <span class="badge">기출 범위: 2015년 ~ 2026년</span>
            <span class="badge accent">총 분석 데이터: <span id="total-question-badge">0</span> 문항</span>
            <span class="badge" onclick="openTopicListModal()" style="cursor: pointer; transition: all 0.2s;" title="클릭 시 검출된 세부 토픽 목록 팝업 열기">
                검출된 빈출 세부 토픽: <span id="topic-count-badge">0</span>개
            </span>
            </div>
    </header>

    <div id="accordion-container" class="accordion-list"></div>


    
<script>

    // [설계 의도] 로컬 오프라인 실행(file:///)과 웹 서버 호스팅(http://) 환경 양쪽 모두에서 퀴즈 대시보드 홈으로 매끄럽게 이동하도록 분기 처리합니다.
    function goToHome(event) {
        event.preventDefault();
        if (window.location.protocol === 'file:') {
            window.location.href = '../index.html';
        } else {
            window.location.href = '/';
        }
    }

    // [설계 의도] 학습 모드 변경에 따라 과목 뱃지의 링크 목적지를 실시간 동적 갱신하고 즉시 이동 처리합니다.
    function toggleDashboardMode(toggleEl) {
        const isOfficial = toggleEl.checked;
        
        // 라벨 색상 하이라이트 전환
        document.getElementById('label-freq').style.color = isOfficial ? 'var(--text-secondary)' : '#ffffff';
        document.getElementById('label-official').style.color = isOfficial ? '#ffffff' : 'var(--text-secondary)';
        
        // 과목별 이동 경로 실시간 매핑
        const badges = document.querySelectorAll('.subject-badge');
        const isLocal = window.location.protocol === 'file:';
        
        badges.forEach(badge => {
            const target = isOfficial ? badge.getAttribute('data-official') : badge.getAttribute('data-freq');
            badge.href = target + '?v=20260613';
        });

        // 사용자의 현재 보고 있는 과목에 매칭되는 대시보드로 즉각 리다이렉트
        const currentPath = window.location.pathname;
        let targetRedirect = "";
        badges.forEach(badge => {
            const freqPath = badge.getAttribute('data-freq');
            const officialPath = badge.getAttribute('data-official');
            if (currentPath.includes(freqPath) && isOfficial) {
                targetRedirect = officialPath;
            } else if (currentPath.includes(officialPath) && !isOfficial) {
                targetRedirect = freqPath;
            }
        });

        if (targetRedirect) {
            window.location.href = targetRedirect + '?v=20260613';
        }
    }

    // [설계 의도] 페이지 로드 시 현재 페이지 파일명에 매핑되는 모드 스위치 상태 및 배지 컬러를 활성화합니다.
    function initDashboardNav() {
        const toggle = document.getElementById('dashboard-mode-toggle');
        const currentPath = window.location.pathname;
        const isOfficialPage = currentPath.includes('official_scopes');
        
        if (toggle) {
            toggle.checked = isOfficialPage;
            // 라벨 색상 하이라이트 초기화
            document.getElementById('label-freq').style.color = isOfficialPage ? 'var(--text-secondary)' : '#ffffff';
            document.getElementById('label-official').style.color = isOfficialPage ? '#ffffff' : 'var(--text-secondary)';
        }

        const badges = document.querySelectorAll('.subject-badge');
        const isLocal = window.location.protocol === 'file:';
        
        badges.forEach(badge => {
            const target = isOfficialPage ? badge.getAttribute('data-official') : badge.getAttribute('data-freq');
            badge.href = target + '?v=20260613';

            // 활성화 배지 하이라이트 (현재 페이지 파일명이 target을 포함하는 경우)
            if (currentPath.includes(target)) {
                badge.classList.add('accent');
                badge.style.color = '#ffffff';
                badge.style.background = 'rgba(139, 92, 246, 0.12)';
                badge.style.borderColor = 'rgba(139, 92, 246, 0.25)';
            } else {
                badge.classList.remove('accent');
            }
        });
    }

    // DOMContentLoaded 시점에 즉시 내비게이션 초기화 적용
    document.addEventListener('DOMContentLoaded', initDashboardNav);

    
    const topicMapping = %MAPPING_JSON%;
    let currentCategory = '전체';

    function renderTopics() {
        const container = document.getElementById('accordion-container');
        container.innerHTML = '';
        
        let filtered = topicMapping;
        if (currentCategory !== '전체') {
            filtered = topicMapping.filter(item => item.category === currentCategory);
        }

        document.getElementById('topic-count-badge').textContent = filtered.length;

        filtered.forEach((item, idx) => {
            const accItem = document.createElement('div');
            accItem.className = 'accordion-item';
            accItem.id = `accordion-${idx}`;

            let yearButtonsHtml = '';
            item.questions.forEach(q => {
                yearButtonsHtml += `<button class="year-btn q-btn-${q.year}-${q.num}" onclick="openQuestion('${q.year}', '${q.num}', ${idx}, this)">
                    ${q.year}년 <span class="num-label">${q.num}번</span>
                </button>`;
            });

            accItem.innerHTML = `
                <button class="accordion-trigger" onclick="toggleAccordion(${idx})">
                    <div class="card-header-row">
                        <div class="card-title-group">
                            <span class="rank-badge">RANK ${String(idx + 1).padStart(2, '0')}</span>
                            <span class="concept-title">${item.concept}</span>
                            <span class="category-tag">${item.category}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.8rem;">
                            <span class="freq-count-badge">총 ${item.count}회 기출</span>
                            <span class="arrow">▼</span>
                        </div>
                    </div>
                    <div class="card-meta-grid">
                        <div class="meta-label">출제 범위</div>
                        <div class="meta-value accent">${item.scope}</div>
                        <div class="meta-label">핵심 개념</div>
                        <div class="meta-value" style="font-weight: 500; color: #ffffff;">${item.core_concept}</div>
                        <div class="meta-label">출제 특징</div>
                        <div class="meta-value">${item.features}</div>
                        <div class="meta-label">기출 연도</div>
                        <div class="meta-value">${item.years.join(', ')}년</div>
                    </div>
                </button>
                <div class="accordion-content" style="max-height: 0px;">
                    <div class="accordion-inner">
                        <div class="section-title">출제 기출문제 선택 (클릭 시 하단에 문제 전환)</div>
                        <div class="year-grid">
                            ${yearButtonsHtml}
                        </div>
                        
                        <div class="inline-question-viewer" id="viewer-${idx}" style="display: none;">
                            <div class="viewer-header">
                                <span class="viewer-title" id="viewer-title-${idx}"></span>
                                <button class="viewer-close-btn" onclick="closeInlineViewer(${idx}, event)">문제 숨기기</button>
                            </div>
                            <div class="viewer-body" id="viewer-body-${idx}"></div>
                            
                            <div class="viewer-img-container" id="viewer-img-container-${idx}" style="margin-top: 1rem; border-top: 1px dashed rgba(255,255,255,0.06); padding-top: 1rem;">
                                <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.6rem; font-weight: 700;">
                                    ▼ 시험지 원본 이미지 (다이어그램 및 수식 확인용)
                                </div>
                                <img src="" id="viewer-img-${idx}" class="question-img" style="max-width: 100%; height: auto; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); display: block;" onerror="hideImageContainer(${idx})">
                            </div>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(accItem);
            });
    }

    function hideImageContainer(idx) {
        const container = document.getElementById(`viewer-img-container-${idx}`);
        if (container) {
            container.style.display = 'none';
        }
    }

    function filterCategory(category) {
        currentCategory = category;
        document.querySelectorAll('.filter-btn').forEach(btn => {
            if (btn.textContent === category) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
                if (document.getElementById('total-question-badge')) {
            const uniqueQuestions = new Set();
            const mappingsObj = (typeof conceptMappings !== 'undefined') ? conceptMappings : ((typeof topicMapping !== 'undefined') ? topicMapping : []);
            mappingsObj.forEach(item => {
                if (item.questions) {
                    item.questions.forEach(q => {
                        uniqueQuestions.add(q.year + "_" + q.num);
                    });
                }
            });
            document.getElementById('total-question-badge').textContent = uniqueQuestions.size;
        }
    renderTopics();
    }

    function toggleAccordion(index) {
        const item = document.getElementById(`accordion-${index}`);
        const content = item.querySelector('.accordion-content');
        const isActive = item.classList.contains('active');

        document.querySelectorAll('.accordion-item').forEach((el, i) => {
            if (i !== index) {
                el.classList.remove('active');
                el.querySelector('.accordion-content').style.maxHeight = '0px';
            }
        });

        if (!isActive) {
            item.classList.add('active');
            
            let filtered = topicMapping;
            if (currentCategory !== '전체') {
                filtered = topicMapping.filter(item => item.category === currentCategory);
            }
            const dataObj = filtered[index];
            
            if (dataObj && dataObj.rep_question) {
                const viewer = document.getElementById(`viewer-${index}`);
                const titleEl = document.getElementById(`viewer-title-${index}`);
                const bodyEl = document.getElementById(`viewer-body-${index}`);
                const imgEl = document.getElementById(`viewer-img-${index}`);
                const imgContainer = document.getElementById(`viewer-img-container-${index}`);
                
                titleEl.textContent = `[대표 문제 예시] ${dataObj.rep_year}년 기출 ${dataObj.rep_num}번`;
                bodyEl.textContent = dataObj.rep_question;
                
                if (imgEl && imgContainer) {
                    imgContainer.style.display = 'block';
                    imgEl.src = `images/${dataObj.rep_year}_${dataObj.rep_num}.png`;
                }
                
                viewer.style.display = 'flex';
                
                item.querySelectorAll('.year-btn').forEach(btn => btn.classList.remove('active-btn'));
                setTimeout(() => {
                    const activeBtn = item.querySelector(`.q-btn-${dataObj.rep_year}-${dataObj.rep_num}`);
                    if (activeBtn) {
                        activeBtn.classList.add('active-btn');
                    }
                }, 50);
            }
            
            setTimeout(() => {
                content.style.maxHeight = content.scrollHeight + 'px';
            }, 150);
        } else {
            item.classList.remove('active');
            content.style.maxHeight = '0px';
        }
    }

    function openQuestion(year, num, idx, btnElement) {
        const key = `${year}_${num}`;
        const questionText = examDatabase[key] || "해당 기출문제를 데이터베이스에서 찾을 수 없습니다.";
        
        const item = document.getElementById(`accordion-${idx}`);
        const content = item.querySelector('.accordion-content');
        
        item.querySelectorAll('.year-btn').forEach(btn => btn.classList.remove('active-btn'));
        
        if (btnElement) {
            btnElement.classList.add('active-btn');
        }
        
        const viewer = document.getElementById(`viewer-${idx}`);
        const titleEl = document.getElementById(`viewer-title-${idx}`);
        const bodyEl = document.getElementById(`viewer-body-${idx}`);
        const imgEl = document.getElementById(`viewer-img-${idx}`);
        const imgContainer = document.getElementById(`viewer-img-container-${idx}`);
        
        titleEl.textContent = `${year}년도 감리사 기출 ${num}번`;
        bodyEl.textContent = questionText;
        
        if (imgEl && imgContainer) {
            imgContainer.style.display = 'block';
            imgEl.src = `images/${year}_${num}.png`;
        }
        
        viewer.style.display = 'flex';
        
        content.style.maxHeight = 'none';
        setTimeout(() => {
            const newHeight = content.scrollHeight;
            content.style.maxHeight = newHeight + 'px';
        }, 50);
    }

    function closeInlineViewer(idx, event) {
        if (event) event.stopPropagation();
        
        const item = document.getElementById(`accordion-${idx}`);
        const content = item.querySelector('.accordion-content');
        
        item.querySelectorAll('.year-btn').forEach(btn => btn.classList.remove('active-btn'));
        
        const viewer = document.getElementById(`viewer-${idx}`);
        viewer.style.display = 'none';
        
        content.style.maxHeight = 'none';
        setTimeout(() => {
            const newHeight = content.scrollHeight;
            content.style.maxHeight = newHeight + 'px';
        }, 50);
    }

    // [세부 토픽 목록 모달 열기]
    window.openTopicListModal = function() {
        const modal = document.getElementById('topic-modal');
        const listEl = document.getElementById('modal-topic-list');
        listEl.innerHTML = '';
        
        let filtered = topicMapping;
        if (currentCategory !== '전체') {
            filtered = topicMapping.filter(item => item.category === currentCategory);
        }
        
        filtered.forEach((item, idx) => {
            const li = document.createElement('li');
            li.className = 'modal-topic-item';
            li.style.cursor = 'pointer';
            li.onclick = () => {
                closeTopicModal();
                setTimeout(() => {
                    const itemEl = document.getElementById(`accordion-${idx}`);
                    if (itemEl && !itemEl.classList.contains('active')) {
                        toggleAccordion(idx);
                    }
                    if (itemEl) {
                        itemEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }, 200);
            };
            
            li.innerHTML = `
                <span class="modal-topic-name">${idx + 1}. ${item.concept}</span>
                <span class="modal-topic-count">${item.count}회 출제</span>
            `;
            listEl.appendChild(li);
        });
        
        modal.style.display = 'flex';
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
    };

    // [세부 토픽 목록 모달 닫기]
    window.closeTopicModal = function(event) {
        const modal = document.getElementById('topic-modal');
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 250);
    };

            if (document.getElementById('total-question-badge')) {
            const uniqueQuestions = new Set();
            const mappingsObj = (typeof conceptMappings !== 'undefined') ? conceptMappings : ((typeof topicMapping !== 'undefined') ? topicMapping : []);
            mappingsObj.forEach(item => {
                if (item.questions) {
                    item.questions.forEach(q => {
                        uniqueQuestions.add(q.year + "_" + q.num);
                    });
                }
            });
            document.getElementById('total-question-badge').textContent = uniqueQuestions.size;
        }
    renderTopics();
    </script>

<!-- 세부 토픽 목록 팝업 모달 -->
<div id="topic-modal" class="modal-overlay" onclick="closeTopicModal(event)">
    <div class="modal-card" onclick="event.stopPropagation()">
        <div class="modal-card-header">
            <h2 class="modal-card-title">🔍 검출된 빈출 세부 토픽 목록</h2>
            <button class="modal-close-x" onclick="closeTopicModal()">✕</button>
        </div>
        <div class="modal-card-body">
            <ul id="modal-topic-list" class="modal-topic-list">
                <!-- 자바스크립트로 동적 로딩 -->
            </ul>
        </div>
    </div>
</div>
</body>
</html>
"""
    html_content = html_template.replace("%MAPPING_JSON%", mapping_json)
    return html_content

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
