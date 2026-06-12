# -*- coding: utf-8 -*-
"""
[초프리미엄 시스템구조(SA) 기출문제 뷰어 자동 빌더]
- 목적: 2015년~2026년 기출 PDF에서 SA 과목 전체 문항(76~100번)을 추출하고,
  12대 세부 토픽 사전을 기반으로 정형화된 빈출 분석 대시보드 웹앱(sa_frequent_concepts.html)을 생성합니다.
"""

import os
import sys
import re
import json
import pdfplumber
import fitz

# 공통 이미지 크롭 모듈 임포트
import image_cropper

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

def run_extraction_and_mapping():
    question_db = {}
    concept_map = {concept: [] for concept in CONCEPT_KEYWORDS}
    concept_map["[기타]"] = [] # [기타] 카테고리 초기화
    
    print("[1/3] SA 기출문제 PDF 파싱 및 전체 문항 DB 구축 중...")
    for exam in EXAM_FILES:
        year = exam["year"]
        filename = exam["filename"]
        pdf_path = os.path.join(EXAM_DIR, filename)
        
        if not os.path.exists(pdf_path):
            continue
            
        try:
            local_img_dir = r"e:\jolly-carson\reports\images"
            artifact_img_dir = r"C:\Users\DCCIS040000\.gemini\antigravity-ide\brain\7e1fd111-1dc1-495d-82a1-c40573600184\images"
            unique_positions = crop_question_images(pdf_path, year, local_img_dir)
            crop_question_images(pdf_path, year, artifact_img_dir)
            
            # pdfplumber를 활용한 각 문제 영역 텍스트 직접 추출로 정합성 100% 보장
            with pdfplumber.open(pdf_path) as pdf:
                for num in range(76, 101):
                    if num not in unique_positions:
                        continue
                    pos = unique_positions[num]
                    page_idx = pos["page_idx"]
                    page = pdf.pages[page_idx]
                    
                    bbox = pos.get("crop_rect")
                    if not bbox:
                        continue
                        
                    # coordinates boundary check
                    x0 = max(0, min(bbox[0], page.width))
                    y0 = max(0, min(bbox[1], page.height))
                    x1 = max(0, min(bbox[2], page.width))
                    y1 = max(0, min(bbox[3], page.height))
                    
                    if x1 <= x0: x1 = page.width
                    if y1 <= y0: y1 = page.height
                    
                    cropped = page.crop((x0, y0, x1, y1))
                    q_text = cropped.extract_text() or ""
                    q_text_clean = q_text.strip()
                    
                    # 텍스트가 번호로 시작하지 않으면 번호를 보정하여 붙여줍니다.
                    if not re.match(rf"^{num}\b", q_text_clean):
                        q_text_clean = f"{num}. {q_text_clean}"
                        
                    key = f"{year}_{num}"
                    question_db[key] = q_text_clean
                    
                    # 키워드 매칭 분석
                    body_lower = q_text_clean.lower()
                    matched_concepts = []
                    for concept, keywords in CONCEPT_KEYWORDS.items():
                        for kw in keywords:
                            if re.match(r"^[a-zA-Z0-9\-\_\/]+$", kw):
                                pattern = rf"\b{re.escape(kw.lower())}\b"
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
        except Exception as e:
            print(f"  [에러] {year}년도 처리 실패: {e}")
            
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
    <title>시스템구조 12개년 빈출 개념 정밀 뷰어</title>
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
</head>
<body>



<div class="container">
    <header>
        <h1>시스템구조 기출 정밀 분석 대시보드</h1>
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
            <span class="badge accent">총 분석 데이터: 300 문항</span>
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
            if (isLocal) {
                badge.href = target;
            } else {
                badge.href = '/reports/' + target;
            }
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
            if (isLocal) {
                window.location.href = targetRedirect;
            } else {
                window.location.href = '/reports/' + targetRedirect;
            }
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
            if (isLocal) {
                badge.href = target;
            } else {
                badge.href = '/reports/' + target;
            }

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

    const examDatabase = %DB_JSON%;
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
    html_content = html_template.replace("%DB_JSON%", db_json).replace("%MAPPING_JSON%", mapping_json)
    return html_content

def main():
    question_db, concept_map = run_extraction_and_mapping()
    html_content = build_html_content(question_db, concept_map)
    
    local_path = r"e:\jolly-carson\reports\sa_frequent_concepts.html"
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[2/3] 로컬 reports 폴더 저장 완료: {local_path}")
    
    artifact_path = r"C:\Users\DCCIS040000\.gemini\antigravity-ide\brain\7e1fd111-1dc1-495d-82a1-c40573600184\sa_frequent_concepts.html"
    os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[3/3] 아티팩트 디렉토리 저장 완료: {artifact_path}")
    
    print("\n[성공] SA 기출문제 뷰어 빌드가 완료되었습니다!")

if __name__ == "__main__":
    main()
