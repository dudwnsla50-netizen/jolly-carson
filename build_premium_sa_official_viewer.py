# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

"""
[초프리미엄 시스템 아키텍처 공식 범위(SA.txt) 기출문제 뷰어 자동 빌더]
- 목적: 2015년~2026년 기출 PDF에서 시스템 아키텍처 전체 문항(76~100번, 2015년은 76~90번)을 읽어와서 
  공식 가이드라인(SA.txt) 대단원 및 세부 중단원에 부합하도록 구조화하고, 
  이를 수려한 다크모드 대시보드 HTML 파일 안에 임베딩하여 자동 생성합니다.
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

# SA.txt 공식 가이드라인 기반의 14개 중단원 분류 사전 및 키워드 매핑
CONCEPT_KEYWORDS = {
    # 1. 공통기술
    "1-a. IT 및 정보화 관련 표준, 국내외 표준화 동향": ["표준화", "동향", "it 표준", "iso/iec", "itu", "ieee 표준", "w3c"],
    "1-b. 정보기술 아키텍처(EA)": ["ea", "it 아키텍처", "정보기술아키텍처", "enterprise architecture", "자카만", "zachman", "togaf", "feaf", "참조모델", "drm", "prm", "trm", "srm", "sprm"],

    # 2. 아키텍처 설계 및 구축
    "2-a. 컴퓨터 구조론 : 디지털 논리회로, 명령어, 주소, CPU/GPU, 파이프라이닝, 기억장치, 입출력장치, 병렬처리 등": ["논리회로", "명령어", "주소", "cpu", "gpu", "파이프라이닝", "pipelining", "기억장치", "캐시", "cache", "입출력", "병렬처리", "해자드", "멀티코어", "인터럽트"],
    "2-b. 하드웨어 : 서버, 스토리지, NAS, 백업장치, UPS, 항온항습기 등": ["서버", "server", "스토리지", "storage", "nas", "san", "das", "백업장치", "ups", "무정전", "항온항습기"],
    "2-c. 아키텍처 설계 : N-Tier, RAID, 이중화, 부하분산, 가상화, 최적화, 고가용성, 용량산정, 백업/복구, 재해복구 등": ["n-tier", "raid", "이중화", "부하분산", "load balancing", "가상화", "virtualization", "최적화", "고가용성", "active-active", "active-standby", "용량산정", "용량 산정", "백업", "재해복구", "drp", "rto", "rpo", "clustering", "클러스터링"],
    "2-d. 클라우드 기반 아키텍처, 전자정부 공통 기반, 서버리스 등": ["클라우드 기반", "전자정부 공통", "서버리스", "serverless", "fiss", "g-cloud", "egovframe"],
    "2-e. 공개SW(오픈소스) : 솔루션, 라이선스 정책 등": ["공개sw", "공개 소프트웨어", "오픈소스", "open source", "라이선스", "gpl", "apache", "mit"],
    "2-f. 성능시험, 이중화 시험": ["성능시험", "성능 시험", "이중화 시험", "부하 시험", "스트레스 시험", "stress test", "load test", "tps", "응답시간", "response time"],

    # 3. 데이터 통신 및 네트워크 설계
    "3-a. 데이터 통신이론, 데이터 전송 방식 및 기술, OSI 참조 모델, 네트워크 프로토콜, IPv4/IPv6, LAN, WAN, 무선LAN, 인터네트워킹, 스토리지 전송 프로토콜, 네트워크 관리 등": ["데이터 통신", "데이터 전송", "osi", "네트워크 프로토콜", "ipv4", "ipv6", "lan", "wan", "무선lan", "인터네트워킹", "스토리지 전송", "네트워크 관리", "snmp", "tcp", "udp", "ip 주소", "서브넷", "arp", "icmp"],
    "3-b. 네트워크 장비 : 라우터, 스위치, 허브, 브리지, 백본 등": ["라우터", "router", "스위치", "switch", "허브", "hub", "브리지", "bridge", "백본", "backbone", "l2 스위치", "l3 스위치", "l4 스위치", "l7 스위치"],
    "3-c. 네트워크 설계 : 주소, 네트워크 분할, 가상화, 이중화, 스위칭, 라우팅 프로토콜 등": ["주소 설계", "네트워크 분할", "가상화", "네트워크 이중화", "스위칭", "라우팅 프로토콜", "ospf", "bgp", "rip", "vlan", "stp", "mstp", "vrrp", "hsrp"],
    "3-d. 근거리 통신 기술 : NFC, Zigbee, Beacon, Bluetooth 등": ["nfc", "zigbee", "직비", "beacon", "비콘", "bluetooth", "블루투스", "uwb", "rfid"],
    "3-e. 저전력 장거리 통신 기술 : Sigfox, LoRa, NB-IoT 등": ["저전력 장거리", "sigfox", "lora", "로라", "nb-iot", "lpwan"],
    "3-f. 기타 데이터 통신 기술 : WiFi, HSDPA, WPAN, BcN, ADN, CDN, NFV, SDN": ["wifi", "hsdpa", "wpan", "bcn", "adn", "cdn", "nfv", "sdn"],

    # 4. 기타 신기술
    "4-a. 클라우드 컴퓨팅, 빅데이터 플랫폼, 사물인터넷, AI, 머신러닝, 블록체인, 메타버스, 스마트카, VR/AR, 3D프린팅, 드론, 스마트시티 등": ["클라우드 컴퓨팅", "cloud computing", "iaas", "paas", "saas", "빅데이터 플랫폼", "hadoop", "spark", "사물인터넷", "iot", "ai", "머신러닝", "딥러닝", "블록체인", "blockchain", "메타버스", "스마트카", "vr", "ar", "3d프린팅", "드론", "스마트시티"]
}

# 공식 세부 설명 메타데이터 정의
CONCEPT_METADATA = {
    "1-a. IT 및 정보화 관련 표준, 국내외 표준화 동향": {"core_concept": "IT 표준 및 표준화 동향", "features": "국내외 IT 표준(ISO, IEEE 등) 및 최신 표준화 동향을 묻습니다.", "scope": "공통기술"},
    "1-b. 정보기술 아키텍처(EA)": {"core_concept": "EA 참조 모델 및 프레임워크", "features": "EA의 구성 요소(BA, DA, TA, SA), 참조모델(TRM, SPB 등) 및 Zachman/TOGAF 프레임워크를 질문합니다.", "scope": "공통기술"},

    "2-a. 컴퓨터 구조론 : 디지털 논리회로, 명령어, 주소, CPU/GPU, 파이프라이닝, 기억장치, 입출력장치, 병렬처리 등": {"core_concept": "컴퓨터 구조 및 하드웨어 제어", "features": "디지털 논리회로, CPU 연산, 캐시 매핑, 파이프라인 해자드, 병렬 처리 연산을 다룹니다.", "scope": "아키텍처 설계 및 구축"},
    "2-b. 하드웨어 : 서버, 스토리지, NAS, 백업장치, UPS, 항온항습기 등": {"core_concept": "서버 및 백업 인프라 하드웨어", "features": "서버 스펙 분석, NAS/SAN 스토리지 설계, UPS 전력 계산 및 항온항습 용량 평가를 질문합니다.", "scope": "아키텍처 설계 및 구축"},
    "2-c. 아키텍처 설계 : N-Tier, RAID, 이중화, 부하분산, 가상화, 최적화, 고가용성, 용량산정, 백업/복구, 재해복구 등": {"core_concept": "고가용성 이중화 및 재해복구 설계", "features": "RAID 레벨 구성, 로드밸런싱 알고리즘, 이중화 구조, DR 센터 유형 및 가상화(하이퍼바이저/컨테이너) 설계를 중점 질문합니다.", "scope": "아키텍처 설계 및 구축"},
    "2-d. 클라우드 기반 아키텍처, 전자정부 공통 기반, 서버리스 등": {"core_concept": "클라우드 인프라 및 서버리스 아키텍처", "features": "서버리스 가용성 보장, 전자정부 프레임워크 기반 연계 및 G-Cloud 구조를 다룹니다.", "scope": "아키텍처 설계 및 구축"},
    "2-e. 공개SW(오픈소스) : 솔루션, 라이선스 정책 등": {"core_concept": "오픈소스 생태계 라이선스 의무 사항", "features": "GPL, Apache, MIT 라이선스의 법적 의무 사항 및 소스코드 공개 범위를 질문합니다.", "scope": "아키텍처 설계 및 구축"},
    "2-f. 성능시험, 이중화 시험": {"core_concept": "시스템 성능 튜닝 및 시험 방안", "features": "성능 지표(TPS, 응답시간, 자원사용율) 분석 및 부하/이중화 장애 전환(Failover) 시험 요건을 검증합니다.", "scope": "아키텍처 설계 및 구축"},

    "3-a. 데이터 통신이론, 데이터 전송 방식 및 기술, OSI 참조 모델, 네트워크 프로토콜, IPv4/IPv6, LAN, WAN, 무선LAN, 인터네트워킹, 스토리지 전송 프로토콜, 네트워크 관리 등": {"core_concept": "네트워크 통신 이론 및 TCP/IP", "features": "OSI 7계층 기능, IPv4/IPv6 헤더 비교, 서브네팅 연산, TCP 흐름 제어, SNMP 관리 방식을 검증합니다.", "scope": "데이터 통신 및 네트워크 설계"},
    "3-b. 네트워크 장비 : 라우터, 스위치, 허브, 브리지, 백본 등": {"core_concept": "네트워크 중계 장비 아키텍처", "features": "라우터, L2/L3/L4/L7 스위치의 차이점 및 스위치 로드밸런싱 구성을 평가합니다.", "scope": "데이터 통신 및 네트워크 설계"},
    "3-c. 네트워크 설계 : 주소, 네트워크 분할, 가상화, 이중화, 스위칭, 라우팅 프로토콜 등": {"core_concept": "가상화 및 고신뢰 네트워크 설계", "features": "IP 주소 설계, VLAN 구성, 라우팅 프로토콜(OSPF/BGP) 연산, 루핑 방지(STP/MSTP) 방안을 질문합니다.", "scope": "데이터 통신 및 네트워크 설계"},
    "3-d. 근거리 통신 기술 : NFC, Zigbee, Beacon, Bluetooth 등": {"core_concept": "센서망 및 근거리 통신 프로토콜", "features": "NFC 규격, Zigbee 토폴로지, BLE 비콘 설계 및 RFID 주파수대 특징을 질문합니다.", "scope": "데이터 통신 및 네트워크 설계"},
    "3-e. 저전력 장거리 통신 기술 : Sigfox, LoRa, NB-IoT 등": {"core_concept": "LPWAN IoT 무선 기술", "features": "LoRaWAN 아키텍처, Sigfox 특징 및 NB-IoT의 주파수 대역 배치 기법을 검증합니다.", "scope": "데이터 통신 및 네트워크 설계"},
    "3-f. 기타 데이터 통신 기술 : WiFi, HSDPA, WPAN, BcN, ADN, CDN, NFV, SDN": {"core_concept": "최신 네트워크 인프라 기술", "features": "CDN 설계, SDN/NFV 가상화 원리 및 WPAN 규격을 다룹니다.", "scope": "데이터 통신 및 네트워크 설계"},

    "4-a. 클라우드 컴퓨팅, 빅데이터 플랫폼, 사물인터넷, AI, 머신러닝, 블록체인, 메타버스, 스마트카, VR/AR, 3D프린팅, 드론, 스마트시티 등": {"core_concept": "신기술 아키텍처 및 플랫폼", "features": "빅데이터 하둡 에코시스템, IoT 플랫폼 아키텍처, 인공지능 머신러닝 인프라 구성 및 블록체인 합의 알고리즘을 질문합니다.", "scope": "기타 신기술"}
}

# 4대 대단원 매핑
TOPIC_CATEGORIES = {
    "1-a. IT 및 정보화 관련 표준, 국내외 표준화 동향": "1. 공통기술",
    "1-b. 정보기술 아키텍처(EA)": "1. 공통기술",
    
    "2-a. 컴퓨터 구조론 : 디지털 논리회로, 명령어, 주소, CPU/GPU, 파이프라이닝, 기억장치, 입출력장치, 병렬처리 등": "2. 아키텍처 설계 및 구축",
    "2-b. 하드웨어 : 서버, 스토리지, NAS, 백업장치, UPS, 항온항습기 등": "2. 아키텍처 설계 및 구축",
    "2-c. 아키텍처 설계 : N-Tier, RAID, 이중화, 부하분산, 가상화, 최적화, 고가용성, 용량산정, 백업/복구, 재해복구 등": "2. 아키텍처 설계 및 구축",
    "2-d. 클라우드 기반 아키텍처, 전자정부 공통 기반, 서버리스 등": "2. 아키텍처 설계 및 구축",
    "2-e. 공개SW(오픈소스) : 솔루션, 라이선스 정책 등": "2. 아키텍처 설계 및 구축",
    "2-f. 성능시험, 이중화 시험": "2. 아키텍처 설계 및 구축",
    
    "3-a. 데이터 통신이론, 데이터 전송 방식 및 기술, OSI 참조 모델, 네트워크 프로토콜, IPv4/IPv6, LAN, WAN, 무선LAN, 인터네트워킹, 스토리지 전송 프로토콜, 네트워크 관리 등": "3. 데이터 통신 및 네트워크 설계",
    "3-b. 네트워크 장비 : 라우터, 스위치, 허브, 브리지, 백본 등": "3. 데이터 통신 및 네트워크 설계",
    "3-c. 네트워크 설계 : 주소, 네트워크 분할, 가상화, 이중화, 스위칭, 라우팅 프로토콜 등": "3. 데이터 통신 및 네트워크 설계",
    "3-d. 근거리 통신 기술 : NFC, Zigbee, Beacon, Bluetooth 등": "3. 데이터 통신 및 네트워크 설계",
    "3-e. 저전력 장거리 통신 기술 : Sigfox, LoRa, NB-IoT 등": "3. 데이터 통신 및 네트워크 설계",
    "3-f. 기타 데이터 통신 기술 : WiFi, HSDPA, WPAN, BcN, ADN, CDN, NFV, SDN": "3. 데이터 통신 및 네트워크 설계",
    
    "4-a. 클라우드 컴퓨팅, 빅데이터 플랫폼, 사물인터넷, AI, 머신러닝, 블록체인, 메타버스, 스마트카, VR/AR, 3D프린팅, 드론, 스마트시티 등": "4. 기타 신기술"
}

def crop_question_images(pdf_path, year, output_dir):
    """[공통 모듈 위임] PDF로부터 SA 과목 문항 영역을 추출하여 이미지로 저장하고 위치 좌표를 반환"""
    local_img_dir = r"e:\jolly-carson\reports\images"
    artifact_img_dir = r"C:\Users\DCCIS040000\.gemini\antigravity-ide\brain\7e1fd111-1dc1-495d-82a1-c40573600184\images"
    return image_cropper.get_question_positions_and_crop(
        pdf_path, year, "SA", local_img_dir, artifact_img_dir, force_crop=FORCE_CROP
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

def slice_sa_section(full_text):
    """시스템구조(51번~75번) 범위 슬라이싱"""
    start_pattern = r"\b51\s*[\.\)]"
    end_pattern = r"\b76\s*[\.\)]"
    
    start_match = re.search(start_pattern, full_text)
    end_match = re.search(end_pattern, full_text)
    
    if start_match:
        start_idx = start_match.start()
        end_idx = end_match.start() if end_match else len(full_text)
        return full_text[start_idx:end_idx].strip()
    return ""

def parse_questions(sa_text):
    """문항 분절화"""
    questions = []
    for num in range(51, 76):
        curr_pat = rf"(?<![\.\d]){num}\s*[\.\)]"
        next_pat = rf"(?<![\.\d]){num+1}\s*[\.\)]"
        
        curr_match = re.search(curr_pat, sa_text)
        if not curr_match:
            continue
            
        start_pos = curr_match.start()
        next_match = re.search(next_pat, sa_text)
        
        if next_match:
            end_pos = next_match.start()
            q_body = sa_text[start_pos:end_pos].strip()
        else:
            q_body = sa_text[start_pos:].strip()
            
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
    update_shared_db(question_db, "SA")
    html_content = build_html_content(question_db, concept_map)
    
    local_path, artifact_path = get_output_paths("sa_official_scopes.html")
    
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
