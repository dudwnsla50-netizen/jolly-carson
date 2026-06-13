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
from build_utils import get_output_paths, update_shared_db
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
    
    html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>보안 공식 범위별 기출 뷰어</title>
    <!-- Google Fonts -->
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

        /* Category Filter Badges */
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

        /* Main Accordion List */
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

        /* 스크롤바 디자인 */
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
        .viewer-body::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }
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

        /* 반응형 모바일 최적화 */
        @media (max-width: 768px) {
            body { padding: 1.5rem 0.8rem; }
            header h1 { font-size: 1.8rem; line-height: 1.3; }
            header p.subtitle { font-size: 0.88rem; padding: 0 0.5rem; word-break: keep-all; }
            .meta-badges { gap: 0.5rem; }
            .badge { padding: 0.25rem 0.6rem; font-size: 0.72rem; }
            .filter-section { gap: 0.4rem; margin-bottom: 1.5rem; }
            .filter-btn { padding: 0.35rem 0.7rem; font-size: 0.78rem; }
            .accordion-trigger { padding: 1.2rem 1rem; gap: 0.6rem; }
            .concept-title {
            user-select: text !important;
            -webkit-user-select: text !important; font-size: 1.05rem; }
            .rank-badge { font-size: 1rem; }
            .category-tag, .freq-count-badge { font-size: 0.7rem; padding: 0.1rem 0.35rem; }
            .card-meta-grid { grid-template-columns: 80px 1fr; font-size: 0.82rem; row-gap: 0.4rem; }
            .accordion-inner { padding: 1.2rem 1rem; gap: 1rem; }
            .section-title { font-size: 0.75rem; }
            .year-btn { padding: 0.3rem 0.6rem; font-size: 0.75rem; }
            .inline-question-viewer { padding: 0.9rem; }
            .viewer-body { font-size: 0.85rem; max-height: 300px; }
            .modal-card { width: 95%; max-height: 90%; }
            .modal-card-header { padding: 1rem; }
            .modal-card-title { font-size: 1.05rem; }
            .modal-card-body { padding: 0.8rem 1rem 1.2rem 1rem; }
            .modal-topic-item { padding: 0.6rem 0.8rem; }
            .modal-topic-name { font-size: 0.85rem; }
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
        /* [일괄 레이아웃 패치: 스크롤바 제거, 이미지 50% 축소 및 좌측 정렬] */
        .viewer-body {
            max-height: none !important;
            overflow-y: visible !important;
        }
        .viewer-body img, .viewer-img-container img, .question-img {
            max-width: 50% !important;
            height: auto !important;
            margin: 0.8rem 0 !important; /* 가운데 정렬(auto)에서 좌측 정렬(0)로 변경 */
            display: block !important;
        }
        @media (max-width: 768px) {
            .viewer-body {
                max-height: none !important;
                overflow-y: visible !important;
            }
            .viewer-body img, .viewer-img-container img, .question-img {
                max-width: 50% !important;
                height: auto !important;
                margin: 0.8rem 0 !important;
            }
        }


    </style>
    <script src="exam_db/sc_db.js?v=20260613"></script>
</head>
<body>



<div class="container">
    <header>
        <h1>보안 공식 범위별 기출 대시보드</h1>
        <p class="subtitle">공식 시험 가이드라인(SC.txt) 5대 단원 및 15개 중단원 매핑 기출 뷰어</p>
        
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
            <span class="badge" onclick="openTopicListModal()" style="cursor: pointer; transition: all 0.2s;" title="클릭 시 중단원 목록 팝업 열기">
                매핑된 공식 중단원: <span id="topic-count-badge">0</span>개
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
                            <span class="rank-badge">${item.concept.split('.')[0]}</span>
                            <span class="concept-title">${item.concept}</span>
                            <span class="category-tag">${item.category.split(' ')[1] || item.category}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.8rem;">
                            <span class="freq-count-badge">매핑 문항 ${item.count}개</span>
                            <span class="arrow">▼</span>
                        </div>
                    </div>
                    <div class="card-meta-grid">
                        <div class="meta-label">공식 영역</div>
                        <div class="meta-value accent">${item.scope}</div>
                        <div class="meta-label">핵심 개념</div>
                        <div class="meta-value" style="font-weight: 500; color: #ffffff;">${item.core_concept}</div>
                        <div class="meta-label">출제 특징</div>
                        <div class="meta-value">${item.features}</div>
                        <div class="meta-label">출제 연도</div>
                        <div class="meta-value">${item.years.length > 0 ? item.years.join(', ') + '년' : '출제 이력 없음'}</div>
                    </div>
                </button>
                <div class="accordion-content" style="max-height: 0px;">
                    <div class="accordion-inner">
                        <div class="section-title">해당 범위 기출문제 선택 (클릭 시 하단에 문제 전환)</div>
                        <div class="year-grid">
                            ${yearButtonsHtml || '<span class="memo-placeholder">이 중단원에 직접 매핑된 기출문제가 캐시 DB에 존재하지 않습니다.</span>'}
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
            if (btn.textContent === category || (category === '전체' && btn.textContent === '전체') || (category.includes('요구') && btn.textContent.includes('요구')) || (category.includes('구현') && btn.textContent.includes('구현')) || (category.includes('유지') && btn.textContent.includes('유지')) || (category.includes('개발') && btn.textContent.includes('개발')) || (category.includes('품질') && btn.textContent.includes('품질'))) {
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
                <span class="modal-topic-name">${item.concept}</span>
                <span class="modal-topic-count">${item.count}개 문항 매핑</span>
            `;
            listEl.appendChild(li);
        });
        
        modal.style.display = 'flex';
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
    };

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

<div id="topic-modal" class="modal-overlay" onclick="closeTopicModal(event)">
    <div class="modal-card" onclick="event.stopPropagation()">
        <div class="modal-card-header">
            <h2 class="modal-card-title">🔍 검출된 공식 중단원 목록</h2>
            <button class="modal-close-x" onclick="closeTopicModal()">✕</button>
        </div>
        <div class="modal-card-body">
            <ul id="modal-topic-list" class="modal-topic-list">
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
