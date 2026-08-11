# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

"""
[초프리미엄 시스템구조(SA) 기출문제 뷰어 자동 빌더]
- 목적: 2015년~2026년 기출 PDF에서 SA 과목 전체 문항(76~100번)을 추출하고,
  12대 세부 토픽 사전을 기반으로 정형화된 빈출 분석 대시보드 웹앱(sa_frequent_concepts.html)을 생성합니다.
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
    "CPU 정보 레지스터 및 명령어 사이클": ["cpu", "레지스터", "프로그램 카운터", "alu", "명령어 사이클", "간접 주소", "누산기"],
    "명령어 파이프라이닝 및 해저드 종류 (구조적/데이터/제어)": ["파이프라인", "pipelining", "해저드", "hazard", "데이터 해저드", "구조적 해저드", "제어 해저드", "분기 예측"],
    "캐시 메모리 매핑 및 쓰기 정책 (Write-through/Write-back)": ["캐시", "cache", "직접 매핑", "연관 매핑", "세트 연관", "캐시 쓰기", "쓰기 통과", "쓰기 되돌리기", "hit ratio", "캐시 일관성"],
    "가상 메모리 및 페이지 교체 알고리즘 (LRU/LFU/FIFO)": ["가상 메모리", "가상메모리", "lru", "lfu", "fifo", "opt", "페이지 교체", "스래싱", "페이지폴트", "워킹셋"],
    "RAID 레벨별 패리티 및 디스크 효율 (0/1/5/6/10)": ["raid", "스트라이핑", "미러링", "패리티", "raid 0", "raid 1", "raid 5", "raid 6", "raid 10"],
    "고가용성 아키텍처 및 재해 복구 시스템 (DRS)": ["고가용성", "ha", "액티브-액티브", "액티브-스탠바이", "drs", "rto", "rpo", "클러스터링", "이중화"],
    "OSI 7계층 및 TCP/IP 프로토콜 스택": ["osi 7", "osi 7계층", "물리 계층", "데이터 링크", "네트워크 계층", "전송 계층", "세션", "표현", "응용 계층", "캡슐화"],
    "IP 주소 체계 비교 (IPv4 vs IPv6 헤더 필드)": ["ipv4", "ipv6", "ip 주소", "서브넷", "서브넷 마스크", "애니캐스트", "멀티캐스트", "ipv6 헤더"],
    "TCP 혼잡 제어 (Slow Start / Congestion Avoidance)": ["tcp", "혼잡 제어", "흐름 제어", "slow start", "혼잡 회피", "슬라이딩 윈도우", "빠른 재전송", "임계치"],
    "클라우드 서비스 모델 (IaaS/PaaS/SaaS) 및 가상화": ["클라우드", "iaas", "paas", "saas", "가상화", "docker", "kubernetes", "컨테이너", "하이퍼바이저"],
    "네트워크 라우팅 프로토콜 (RIP/OSPF/BGP)": ["라우터", "스위치", "라우팅", "rip", "ospf", "bgp", "거리 벡터", "링크 상태"],
    "컴퓨터 조합/순서 논리 회로 (가산기/플립플롭 등)": ["논리 회로", "논리회로", "가산기", "디코더", "멀티플렉서", "플립플롭", "부울 대수", "카르노 맵"]
}

CONCEPT_METADATA = {
    "CPU 정보 레지스터 및 명령어 사이클": {
        "core_concept": "중앙처리장치의 구성 요소 및 주소 지정 방식과 실행 주기 제어",
        "features": "프로그램 카운터(PC), 누산기(AC), 메모리 주소 레지스터(MAR)의 흐름과 인출(Fetch)->간접(Indirect)->실행(Execute)->인터럽트(Interrupt) 사이클 상태 변화를 묻습니다.",
        "scope": "공통기술 -> 컴퓨터 구조 -> CPU"
    },
    "명령어 파이프라이닝 및 해저드 종류 (구조적/데이터/제어)": {
        "core_concept": "여러 명령어를 중첩 실행하여 처리량(Throughput)을 높이는 병렬 처리 기술",
        "features": "구조적 해저드(자원 충돌), 데이터 해저드(RAW, WAR, WAW 의존성), 제어 해저드(분기 명령 발생)의 발생 원인과 지연(Stall) 및 우회(Bypassing) 해결 기법을 출제합니다.",
        "scope": "공통기술 -> 컴퓨터 구조 -> 파이프라인"
    },
    "캐시 메모리 매핑 및 쓰기 정책 (Write-through/Write-back)": {
        "core_concept": "CPU와 메인 메모리 간 속도 차이를 해소하기 위한 고속 버퍼 메모리 운영 기법",
        "features": "직접(Direct), 연관(Associative), 세트 연관(Set-Associative) 매핑의 주소 구조 분석과 Write-through(즉시 기록) / Write-back(교체 시 기록)의 성능 특징을 비교합니다.",
        "scope": "공통기술 -> 컴퓨터 구조 -> 캐시"
    },
    "가상 메모리 및 페이지 교체 알고리즘 (LRU/LFU/FIFO)": {
        "core_concept": "물리 메모리 크기 한계를 극복하고 가상 주소를 물리 주소로 사상하여 관리하는 메모리 관리 모델",
        "features": "LRU(최근 최소 사용), LFU(최소 빈도 사용), FIFO 교체 알고리즘의 페이지 부재(Page Fault) 횟수 계산 문제 및 스래싱(Thrashing) 예방을 위한 워킹셋 모델을 다룹니다.",
        "scope": "공통기술 -> 운영체제 -> 메모리 관리"
    },
    "RAID 레벨별 패리티 및 디스크 효율 (0/1/5/6/10)": {
        "core_concept": "여러 물리 디스크를 논리적 하나의 저장장치로 묶어 성능과 신뢰성을 올리는 기술",
        "features": "RAID 0(스트라이핑), 1(미러링), 5(분산 단일 패리티), 6(분산 이중 패리티)의 필요 디스크 수 계산, 가용 용량 비율 및 결함 복구 한계를 물어봅니다.",
        "scope": "아키텍처 설계 및 구축 -> 스토리지 아키텍처"
    },
    "고가용성 아키텍처 및 재해 복구 시스템 (DRS)": {
        "core_concept": "시스템 다운 타임을 최소화하기 위한 이중화 및 재해 복구(DR) 아키텍처 표준",
        "features": "Active-Active, Active-Standby 구성의 세션 동기화 문제와 DRS 수준(Mirroring, Hot, Warm, Cold)에 따른 RTO(복구목표시간) 및 RPO(복구목표시점) 관계를 매년 질문합니다.",
        "scope": "아키텍처 설계 및 구축 -> 가용성 설계"
    },
    "OSI 7계층 및 TCP/IP 프로토콜 스택": {
        "core_concept": "네트워크 통신망 구축을 위한 ISO 표준 개방형 아키텍처와 실제 인터넷 프로토콜 표준",
        "features": "각 계층별 역할(데이터링크: 흐름/에러 제어, 전송: End-to-End 신뢰성 등)과 대표적인 프로토콜/장비 매핑 관계를 묻습니다.",
        "scope": "데이터 통신 및 네트워크 설계 -> 네트워크 모델"
    },
    "IP 주소 체계 비교 (IPv4 vs IPv6 헤더 필드)": {
        "core_concept": "인터넷망 상의 호스트 식별을 위한 주소 규격 및 차세대 인터넷 프로토콜 헤더 사양",
        "features": "IPv4(32비트, 가변 헤더)와 IPv6(128비트, 고정 헤더, 흐름 레이블 필드 도입, 체크섬 필드 제거)의 헤더 필드 대조 및 서브넷 마스크 연산 문제가 빈출됩니다.",
        "scope": "데이터 통신 및 네트워크 설계 -> IP 프로토콜"
    },
    "TCP 혼잡 제어 (Slow Start / Congestion Avoidance)": {
        "core_concept": "송신 호스트가 네트워크 내의 혼잡 상태를 감지하여 전송률을 스스로 조절하는 흐름 제어 기법",
        "features": "Slow Start(지수적 증가), Congestion Avoidance(선형적 증가), 빠른 재전송(3 Duplicate ACKs 시 임계값 조정 및 전송) 그래프 상의 윈도우 크기 변화를 계산합니다.",
        "scope": "데이터 통신 및 네트워크 설계 -> 전송 프로토콜"
    },
    "클라우드 서비스 모델 (IaaS/PaaS/SaaS) 및 가상화": {
        "core_concept": "가상화된 컴퓨팅 리소스를 온디맨드로 제공하는 서비스 모델 및 컨테이너화 기술",
        "features": "IaaS, PaaS, SaaS의 관리 책임 한계선 분기점 및 Type-1/Type-2 하이퍼바이저와 Docker 컨테이너(OS 커널 공유)의 성능 구조적 장단점을 비교 출제합니다.",
        "scope": "기타 신기술 -> 클라우드 컴퓨팅"
    },
    "네트워크 라우팅 프로토콜 (RIP/OSPF/BGP)": {
        "core_concept": "패킷을 목적지까지 가장 효율적인 경로로 전달하기 위한 네트워크 라우팅 프로토콜",
        "features": "RIP(거리 벡터, 벨만-포드, 최대 15홉 제한)와 OSPF(링크 상태, 다익스트라, 계층 구조) 및 BGP(경로 벡터, 자율 시스템 간 연동)의 세부 명세 비교가 출제됩니다.",
        "scope": "데이터 통신 및 네트워크 설계 -> 라우팅 프로토콜"
    },
    "컴퓨터 조합/순서 논리 회로 (가산기/플립플롭 등)": {
        "core_concept": "하드웨어 회로 설계를 위한 기초 수학 논리 및 소자 아키텍처",
        "features": "가산기, 디코더, 멀티플렉서(기억 소자 없음 -> 조합 회로)와 플립플롭, 카운터(기억 소자 있음 -> 순서 회로)의 출력 진리표 해석과 부울 대수 간소화를 질문합니다.",
        "scope": "공통기술 -> 디지털 논리 설계"
    }
}

TOPIC_CATEGORIES = {
    "CPU 정보 레지스터 및 명령어 사이클": "공통기술",
    "명령어 파이프라이닝 및 해저드 종류 (구조적/데이터/제어)": "공통기술",
    "캐시 메모리 매핑 및 쓰기 정책 (Write-through/Write-back)": "공통기술",
    "가상 메모리 및 페이지 교체 알고리즘 (LRU/LFU/FIFO)": "공통기술",
    "RAID 레벨별 패리티 및 디스크 효율 (0/1/5/6/10)": "아키텍처 설계 및 구축",
    "고가용성 아키텍처 및 재해 복구 시스템 (DRS)": "아키텍처 설계 및 구축",
    "OSI 7계층 및 TCP/IP 프로토콜 스택": "데이터 통신 및 네트워크 설계",
    "IP 주소 체계 비교 (IPv4 vs IPv6 헤더 필드)": "데이터 통신 및 네트워크 설계",
    "TCP 혼잡 제어 (Slow Start / Congestion Avoidance)": "데이터 통신 및 네트워크 설계",
    "클라우드 서비스 모델 (IaaS/PaaS/SaaS) 및 가상화": "기타 신기술",
    "네트워크 라우팅 프로토콜 (RIP/OSPF/BGP)": "데이터 통신 및 네트워크 설계",
    "컴퓨터 조합/순서 논리 회로 (가산기/플립플롭 등)": "공통기술"
}

def crop_question_images(pdf_path, year, output_dir):
    """[공통 모듈 위임] PDF로부터 SA 과목 문항 영역을 추출하여 이미지로 저장하고 위치 좌표를 반환"""
    local_img_dir = r"e:\jolly-carson\reports\images"
    artifact_img_dir = os.path.join(ARTIFACT_DIR, "images")
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
    start_pattern = r"\b76\s*[\.\)]"
    end_pattern = r"\b101\s*[\.\)]"
    
    start_match = re.search(start_pattern, full_text)
    end_match = re.search(end_pattern, full_text)
    
    if start_match:
        start_idx = start_match.start()
        end_idx = end_match.start() if end_match else len(full_text)
        return full_text[start_idx:end_idx].strip()
    return ""

def parse_questions(sa_text):
    questions = []
    for num in range(76, 101):
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
            
        # [방어 코드] 보기 ④번 이후에 다단 텍스트 등의 영향으로 타 문제(예: 77번)가 달라붙는 버그 방지
        if "④" in q_body:
            clean_match = re.search(r"④.*?(?=(?:\r?\n)\s*(?!(?:1|2|3|4)\b)\d+\s*[\.\)])", q_body, re.DOTALL)
            if clean_match:
                q_body = q_body[:clean_match.end()].strip()
            
            # 과목 경계를 알리는 한글 구분자나 페이지 지시문이 붙어 있으면 잘라냅니다.
            for separator in ["보안", "보안공학", "정보보호", "소프트웨어", "=== NEW PAGE ==="]:
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
    update_shared_db(question_db, "SA")
    html_content = build_html_content(question_db, concept_map)
    
    local_path, artifact_path = get_output_paths("sa_frequent_concepts.html")
    
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
