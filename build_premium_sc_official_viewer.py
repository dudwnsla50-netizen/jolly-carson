# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

"""
[초프리미엄 보안 공식 범위(SC.txt) 기출문제 뷰어 자동 빌더]
- 목적: 2015년~2026년 기출 PDF에서 보안 전체 문항(101~120번, 2015년은 91~105번)을 읽어와서 
  공식 가이드라인(SC.txt) 대단원 및 세부 중단원에 부합하도록 구조화하고, 
  이를 수려한 다크모드 대시보드 HTML 파일 안에 임베딩하여 자동 생성합니다.
"""

import os
from build_utils import get_output_paths, update_shared_db, ARTIFACT_DIR
import sys
import re
import json
# import pdfplumber

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

# SC.txt 공식 가이드라인 기반의 15개 중단원 분류 사전 및 키워드 매핑
CONCEPT_KEYWORDS = {
    # 1. 공통 보안 기술
    "1-a. 암호 알고리즘, 해쉬함수, 키관리, 암호 프로토콜 등 암호시스템": ["암호", "해쉬", "해시", "대칭키", "공개키", "aes", "des", "rsa", "sha", "diffie", "디피", "암호시스템", "블록암호", "스트림암호", "암호 프로토콜", "salt", "솔트"],
    "1-b. 전자서명, PKI, 생체인식 등 인증기술": ["전자서명", "pki", "공인인증", "생체인식", "지문", "홍채", "인증기술", "인증 기술", "서명", "인증서", "인증 체계", "ca", "fido"],
    "1-c. 접근권한, SSO, OTP 등 접근제어 기술": ["접근권한", "접근 권한", "sso", "otp", "접근제어", "접근 제어", "mac", "dac", "rbac", "abac", "권한 부여", "인가"],

    # 2. 네트워크 및 시스템 보안
    "2-a. 파이어월, IPS, VPN, ESM, NAC, 망분리, 무선보안 등 유무선 네트워크 보안 기술": ["파이어월", "방화벽", "firewall", "ips", "vpn", "esm", "nac", "망분리", "무선보안", "무선 보안", "wep", "wpa", "침입 차단", "침입방지", "ids", "siem", "utm"],
    "2-b. OS보안, DB보안, 서버 보안, 클라이언트 보안, PC 보안, 휴대용 단말 보안 등 시스템 보안 기술": ["os보안", "db보안", "서버 보안", "클라이언트 보안", "pc 보안", "휴대용 단말", "모바일 보안", "시스템 보안", "secure os", "db 암호화", "접근제어"],
    "2-c. 네트워크/시스템 보안 공격, 해킹 및 침해사고 대응 기술": ["보안 공격", "해킹", "침해사고", "침해 사고", "ddos", "dos", "웜", "바이러스", "악성코드", "랜섬웨어", "ransomware", "spoofing", "스푸핑", "sniffing", "스니핑", "버퍼 오버플로우", "sql 인젝션", "xss"],

    # 3. 응용 및 신기술 보안
    "3-a. 웹 보안, 모바일 앱 보안, DRM, DLP, 전자거래 보안 등 응용 보안 기술": ["웹 보안", "웹보안", "모바일 앱 보안", "drm", "dlp", "전자거래 보안", "응용 보안", "owasp", "https", "ssl", "tls", "보안코딩", "코드 서명", "데이터 유출"],
    "3-b. 클라우드 보안, 빅데이터 보안, IoT 보안, 스마트워크 보안 등 최신 응용 보안": ["클라우드 보안", "빅데이터 보안", "iot 보안", "스마트워크", "최신 응용 보안", "casb", "edge 보안", "가상화 보안"],
    "3-c. 디지털 포렌식, 블록체인, AI 연계 등 보안 신기술": ["디지털 포렌식", "포렌식", "forensic", "블록체인", "blockchain", "ai 연계", "보안 신기술", "스마트 계약", "스마트 컨트랙트", "합의 알고리즘"],

    # 4. 개발 및 운영 보안
    "4-a. 시큐어 코딩, SW형상관리, 개발 환경 보안 등 개발 보안 기술": ["시큐어 코딩", "secure coding", "시큐어코딩", "sw형상관리", "형상관리 보안", "개발 환경 보안", "소프트웨어 개발 보안"],
    "4-b. SW취약점 진단, 도구, 최신 공격 및 대응 기술": ["sw취약점", "취약점 진단", "정적 분석", "동적 분석", "fuzzing", "퍼징", "모의해킹", "도구", "cve", "cwe", "cves"],
    "4-c. 운영 통제, 외주 용역 등 운영 보안 기술": ["운영 통제", "외주 용역", "위탁 보안", "운영 보안", "백업 보안", "접근 이력", "감사 로그"],

    # 5. 정보보호 법규 및 개인정보보호
    "5-a. 정보보호 및 개인정보보호 관련 법규, 표준, 지침, 평가/인증제도": ["정보보호 법규", "개인정보보호법", "정보통신망법", "isms", "isms-p", "iso 27001", "cc 인증", "평가/인증", "인증제도", "보안 인증", "고시"],
    "5-b. 거버넌스, 위험관리, 업무연속성 관리, 보안 감사 등 보안관리 기술": ["거버넌스", "위험관리", "위험 분석", "bcp", "drt", "drp", "업무연속성", "보안 감사", "보안감사", "위험 수용", "위험 회피", "위험 전가", "위험 완화", "cia", "기밀성", "무결성", "가용성"],
    "5-c. 암호화, 개인정보 비식별화 조치 등 기술적, 관리적 보호조치": ["비식별", "익명화", "가명화", "k-익명성", "l-다양성", "t-근접성", "보호조치", "기술적 보호", "관리적 보호"]
}

# 공식 세부 설명 메타데이터 정의
CONCEPT_METADATA = {
    "1-a. 암호 알고리즘, 해쉬함수, 키관리, 암호 프로토콜 등 암호시스템": {"core_concept": "암호 시스템", "features": "대칭/비대칭 암호 알고리즘, 블록/스트림 암호 모드, 해시 함수 및 키 분배 프로토콜을 다룹니다.", "scope": "공통 보안 기술"},
    "1-b. 전자서명, PKI, 생체인식 등 인증기술": {"core_concept": "인증 및 전자 서명", "features": "PKI 공개키 인프라 구조, 인증서 관리, 전자서명 메커니즘 및 다중 인증(MFA) 기술을 검증합니다.", "scope": "공통 보안 기술"},
    "1-c. 접근권한, SSO, OTP 등 접근제어 기술": {"core_concept": "접근 제어 모델", "features": "임의적/강제적/역할기반/속성기반 접근제어, 싱글사인온(SSO), 일회용 비밀번호(OTP) 검증 체계를 다룹니다.", "scope": "공통 보안 기술"},

    "2-a. 파이어월, IPS, VPN, ESM, NAC, 망분리, 무선보안 등 유무선 네트워크 보안 기술": {"core_concept": "유무선 네트워크 보안", "features": "방화벽, IPS/IDS 차이점, VPN 터널링 프로토콜, SIEM 분석, NAC 제어 및 무선 LAN 보안 규격을 질문합니다.", "scope": "네트워크 및 시스템 보안"},
    "2-b. OS보안, DB보안, 서버 보안, 클라이언트 보안, PC 보안, 휴대용 단말 보안 등 시스템 보안 기술": {"core_concept": "호스트 및 데이터베이스 보안", "features": "Secure OS 접근 통제, DB 암호화 방식(API/Filter/Plug-in), 단말 관리 보안 솔루션의 특징을 평가합니다.", "scope": "네트워크 및 시스템 보안"},
    "2-c. 네트워크/시스템 보안 공격, 해킹 및 침해사고 대응 기술": {"core_concept": "시스템 공격 및 악성코드 대응", "features": "DoS/DDoS 기법, 스푸핑/스니핑 공격, 메모리 버퍼 오버플로우, 악성코드 종류 분석 및 대응을 다룹니다.", "scope": "네트워크 및 시스템 보안"},

    "3-a. 웹 보안, 모바일 앱 보안, DRM, DLP, 전자거래 보안 등 응용 보안 기술": {"core_concept": "응용 서비스 보안", "features": "OWASP 탑 10 웹 취약점, 모바일 하이재킹 대응, DRM/DLP 유출 방지 및 전자서명 결제 보안 요건을 평가합니다.", "scope": "응용 및 신기술 보안"},
    "3-b. 클라우드 보안, 빅데이터 보안, IoT 보안, 스마트워크 보안 등 최신 응용 보안": {"core_concept": "최신 응용 인프라 보안", "features": "클라우드 서비스 모델(IaaS/PaaS/SaaS) 책임 한계, CASB 보안 솔루션, IoT 및 가상화 취약점 대응을 질문합니다.", "scope": "응용 및 신기술 보안"},
    "3-c. 디지털 포렌식, 블록체인, AI 연계 등 보안 신기술": {"core_concept": "보안 신기술 융합", "features": "포렌식 증거 수집 원칙, 안티포렌식 기술, 블록체인 합의 알고리즘 취약성 및 AI 기반 침입 탐지 기법을 검증합니다.", "scope": "응용 및 신기술 보안"},

    "4-a. 시큐어 코딩, SW형상관리, 개발 환경 보안 등 개발 보안 기술": {"core_concept": "소프트웨어 개발 보안", "features": "행정안전부 가이드 기반 시큐어 코딩 기법, 소스코드 저장소 보안 및 개발 형상 관리 수명 주기를 질문합니다.", "scope": "개발 및 운영 보안"},
    "4-b. SW취약점 진단, 도구, 최신 공격 및 대응 기술": {"core_concept": "정적/동적 취약점 진단", "features": "정적 분석 도구와 동적 퍼징(Fuzzing) 도구 차이점, CVE 취약점 분석 및 패치 배포 절차를 평가합니다.", "scope": "개발 및 운영 보안"},
    "4-c. 운영 통제, 외주 용역 등 운영 보안 기술": {"core_concept": "보안 운영 및 자산 관리", "features": "내부자 위협 통제, 외주 인력 보안 감사 규정, 접근 기록 감사 로그 보존 및 백업 복구 검증 체계를 질문합니다.", "scope": "개발 및 운영 보안"},

    "5-a. 정보보호 및 개인정보보호 관련 법규, 표준, 지침, 평가/인증제도": {"core_concept": "컴플라이언스 및 표준 규정", "features": "개인정보보호법 주요 조항, ISMS-P 인증 규정, 국제 보안 표준(ISO 27001), CC 평가 기준을 중점 질문합니다.", "scope": "정보보호 법규 및 개인정보보호"},
    "5-b. 거버넌스, 위험관리, 업무연속성 관리, 보안 감사 등 보안관리 기술": {"core_concept": "보안 거버넌스 및 위험 분석", "features": "정보보호 프레임워크 설계, 위험 분석 모델(정량/정성), BCP/DRP 수립 단계 및 보안 감사 기법을 평가합니다.", "scope": "정보보호 법규 및 개인정보보호"},
    "5-c. 암호화, 개인정보 비식별화 조치 등 기술적, 관리적 보호조치": {"core_concept": "개인정보 보호조치", "features": "개인정보 비식별화 5대 기법(가명화, 총계처리 등), 프라이버시 모델(k-익명성, l-다양성)의 수학적 검증을 다룹니다.", "scope": "정보보호 법규 및 개인정보보호"}
}

# 5대 대단원 매핑
TOPIC_CATEGORIES = {
    "1-a. 암호 알고리즘, 해쉬함수, 키관리, 암호 프로토콜 등 암호시스템": "1. 공통 보안 기술",
    "1-b. 전자서명, PKI, 생체인식 등 인증기술": "1. 공통 보안 기술",
    "1-c. 접근권한, SSO, OTP 등 접근제어 기술": "1. 공통 보안 기술",

    "2-a. 파이어월, IPS, VPN, ESM, NAC, 망분리, 무선보안 등 유무선 네트워크 보안 기술": "2. 네트워크 및 시스템 보안",
    "2-b. OS보안, DB보안, 서버 보안, 클라이언트 보안, PC 보안, 휴대용 단말 보안 등 시스템 보안 기술": "2. 네트워크 및 시스템 보안",
    "2-c. 네트워크/시스템 보안 공격, 해킹 및 침해사고 대응 기술": "2. 네트워크 및 시스템 보안",

    "3-a. 웹 보안, 모바일 앱 보안, DRM, DLP, 전자거래 보안 등 응용 보안 기술": "3. 응용 및 신기술 보안",
    "3-b. 클라우드 보안, 빅데이터 보안, IoT 보안, 스마트워크 보안 등 최신 응용 보안": "3. 응용 및 신기술 보안",
    "3-c. 디지털 포렌식, 블록체인, AI 연계 등 보안 신기술": "3. 응용 및 신기술 보안",

    "4-a. 시큐어 코딩, SW형상관리, 개발 환경 보안 등 개발 보안 기술": "4. 개발 및 운영 보안",
    "4-b. SW취약점 진단, 도구, 최신 공격 및 대응 기술": "4. 개발 및 운영 보안",
    "4-c. 운영 통제, 외주 용역 등 운영 보안 기술": "4. 개발 및 운영 보안",

    "5-a. 정보보호 및 개인정보보호 관련 법규, 표준, 지침, 평가/인증제도": "5. 정보보호 법규 및 개인정보보호",
    "5-b. 거버넌스, 위험관리, 업무연속성 관리, 보안 감사 등 보안관리 기술": "5. 정보보호 법규 및 개인정보보호",
    "5-c. 암호화, 개인정보 비식별화 조치 등 기술적, 관리적 보호조치": "5. 정보보호 법규 및 개인정보보호"
}

def crop_question_images(pdf_path, year, output_dir):
    """[공통 모듈 위임] PDF로부터 SC 과목 문항 영역을 추출하여 이미지로 저장하고 위치 좌표를 반환"""
    local_img_dir = r"e:\jolly-carson\reports\images"
    artifact_img_dir = os.path.join(ARTIFACT_DIR, "images")
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

def slice_sc_section(full_text, year=2016):
    """[설계 의도] 연도별 보안(SC) 실제 시험 범위를 반영하여 텍스트 영역을 적절히 슬라이싱합니다."""
    s_range = image_cropper.get_subject_range("SC", year)
    start_num = s_range["start"]
    limit_num = s_range["next_limit"]
    
    start_pattern = rf"\b{start_num}\s*[\.\)]"
    end_pattern = rf"\b{limit_num}\s*[\.\)]"
    
    start_match = re.search(start_pattern, full_text)
    end_match = re.search(end_pattern, full_text)
    
    if start_match:
        start_idx = start_match.start()
        end_idx = end_match.start() if end_match else len(full_text)
        return full_text[start_idx:end_idx].strip()
    return ""

def parse_questions(sc_text, year=2016):
    """[설계 의도] 보안 연도별 문항 수집 범위에 맞추어 개별 문제 지문을 파싱 및 분절합니다."""
    s_range = image_cropper.get_subject_range("SC", year)
    start_num = s_range["start"]
    end_num = s_range["end"]
    
    questions = []
    for num in range(start_num, end_num + 1):
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
            
        if "④" in q_body:
            clean_match = re.search(r"④.*?(?=(?:\r?\n)\s*(?!(?:1|2|3|4)\b)\d+\s*[\.\)])", q_body, re.DOTALL)
            if clean_match:
                q_body = q_body[:clean_match.end()].strip()
            
            for separator in ["데이터베이스", "시스템구조", "보안", "소프트웨어 공학", "=== NEW PAGE ==="]:
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
    update_shared_db(question_db, "SC")
    html_content = build_html_content(question_db, concept_map)
    
    local_path, artifact_path = get_output_paths("sc_official_scopes.html")
    
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
