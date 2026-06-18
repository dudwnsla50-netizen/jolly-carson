# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

"""
[초프리미엄 데이터베이스 공식 범위(DB.txt) 기출문제 뷰어 자동 빌더]
- 목적: 2015년~2026년 기출 PDF에서 데이터베이스 전체 문항(51~75번)을 읽어와서 
  공식 가이드라인(DB.txt) 대단원 및 세부 중단원에 부합하도록 구조화하고, 
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

# DB.txt 공식 가이드라인 기반의 20개 중단원 분류 사전 및 키워드 매핑
CONCEPT_KEYWORDS = {
    # 1. DB개념 및 설계
    "1-a. 데이터베이스 시스템 개념 및 이론": [
        "3단계 스키마", "3계층", "외부 스키마", "개념 스키마", "내부 스키마", "데이터 사전", "시스템 카탈로그", "카탈로그", "데이터 독립성"
    ],
    "1-b. 데이터 모델의 개념, 관계형/객체지향 DB": [
        "e-r", "개체-관계", "식별 관계", "비식별 관계", "관계형 데이터 모델", "객체지향", "오브젝트", "superkey", "candidate key", "후보키", "기본키", "외래키", "참조 무결성", "도메인 무결성", "엔티티 무결성", "무결성 규약", "대체키", "슈퍼키", "기본 키"
    ],
    "1-c. 데이터베이스 설계, 정규화": [
        "정규화", "bcnf", "1nf", "2nf", "3nf", "4nf", "5nf", "무손실 분해", "역정규화", "함수적 종속", "함수 종속", "다치 종속", "조인 종속", "이행적 종속", "이상 현상", "삽입 이상", "삭제 이상", "갱신 이상"
    ],
    "1-d. 데이터 아키텍처, 데이터베이스 구축 방법론v.4.0(NIA, 2014)": [
        "구축 방법론", "데이터 아키텍처", "da", "dama", "데이터 표준화", "전사 아키텍처", "구축방법론"
    ],
    "1-e. 데이터베이스 품질관리, 공공기관 데이터베이스 표준화 지침": [
        "품질관리", "품질 관리 지침", "데이터 값 검증", "메타데이터", "공공기관의 데이터베이스 표준화"
    ],
    
    # 2. DB언어
    "2-a. 관계대수": [
        "관계대수", "관계 해석", "프로젝트", "셀렉트", "디비전", "관계 연산자", "카티션", "세타 조인", "자연 조인", "관계 대수", "시그마", "파이"
    ],
    "2-b. SQL, 내장SQL, 절차형 SQL, ODBC/JDBC 등": [
        "sql", "select", "insert", "update", "delete", "create table", "alter table", "drop table", "grant", "revoke", "having", "group by", "내장 sql", "pl/sql", "odbc", "jdbc", "트리거", "사용자 정의 함수", "뷰", "view", "윈도우 함수", "서브쿼리", "subquery", "조인"
    ],
    
    # 3. DBMS 기술
    "3-a. DB성능(인덱스, 튜닝), 트랜잭션, 동시성 제어": [
        "트랜잭션", "acid", "원자성", "일관성", "격리성", "영속성", "동시성 제어", "병행 제어", "2단계 잠금", "2pl", "교착 상태", "데드락", "로킹", "locking", "인덱스", "b-tree", "b+tree", "클러스터드 인덱스", "넌클러스터드", "튜닝", "실행 계획", "옵티마이저", "해시 조인", "중첩 루프", "정렬 병합", "직렬화 가능성", "mcvc", "격리 수준"
    ],
    "3-b. 데이터 백업 및 복구, 데이터 마이그레이션": [
        "회복 기법", "redo", "undo", "체크포인트", "지연 갱신", "즉시 갱신", "마이그레이션", "백업", "recovery", "장애 복구"
    ],
    "3-c. 저장장치, 메모리 DB": [
        "저장장치", "디스크", "메모리 db", "in-memory", "인메모리", "메모리디비"
    ],
    "3-d. 데이터베이스 보안": [
        "보안", "다중 버전", "암호화", "접근 제어", "dac", "mac", "rbac", "접근제어", "뷰 보안"
    ],
    
    # 4. DB응용
    "4-a. 웹기반 정보시스템": [
        "웹기반", "웹 데이터베이스", "3-tier", "was", "ap 서버"
    ],
    "4-b. 정보검색, 검색엔진": [
        "정보검색", "검색엔진", "질의 처리", "역인덱스", "색인어", "tfidf", "tf-idf", "정밀도", "재현율"
    ],
    "4-c. 멀티미디어, GIS 등": [
        "gis", "지리 정보", "공간 데이터", "멀티미디어", "r-tree", "쿼드 트리"
    ],
    "4-d. 분산 DBMS, 모바일 DBMS": [
        "분산 db", "분산 데이터베이스", "분산 dbms", "위치 투명성", "중복 투명성", "단편화 투명성", "장애 투명성", "2단계 커밋", "2pc", "모바일 dbms"
    ],
    "4-e. OPEN API, 공공데이터": [
        "open api", "공공데이터", "오픈 api", "공공데이터 개방"
    ],
    
    # 5. 빅데이터 및 AI데티어
    "5-a. 빅데이터 관련 기술(저장, 처리, 분석, 시각화)": [
        "빅데이터", "big data", "하둡", "hdfs", "mapreduce", "맵리듀스", "스파크", "spark", "샤딩", "분산 컴퓨팅"
    ],
    "5-b. NoSQL": [
        "nosql", "cap 이론", "cap 정리", "key-value", "cassandra", "mongodb", "hbase", "document store", "비관계형 db"
    ],
    "5-c. 데이터마이닝, DW": [
        "데이터웨어하우스", "스타 스키마", "스노우플레이크", "dw", "olap", "roll-up", "drill-down", "slicing", "dicing", "데이터 마이닝", "연관 규칙", "의사결정 트리", "클러스터링"
    ],
    "5-d. AI학습데이터 구축": [
        "ai 학습", "인공지능 학습", "학습데이터", "어노테이션", "라벨링", "학습 데이터"
    ]
}

# DB 20대 중단원 설명 메타데이터 정의
CONCEPT_METADATA = {
    "1-a. 데이터베이스 시스템 개념 및 이론": {
        "core_concept": "데이터베이스 3단계 스키마 구조와 물리/논리적 독립성",
        "features": "외부/개념/내부 스키마 정의 및 독립성과 메타데이터 시스템 카탈로그의 성격을 묻는 기본 이론이 출제됩니다.",
        "scope": "DB개념 및 설계 -> DB 기본 개념"
    },
    "1-b. 데이터 모델의 개념, 관계형/객체지향 DB": {
        "core_concept": "개념적 ER 모델 및 관계형 모델의 기본키/외래키/키 종류 및 무결성 규약",
        "features": "개체 무결성, 참조 무결성, 후보키/슈퍼키/대체키 개념 식별 및 ERD 기호 해석이 빈출됩니다.",
        "scope": "DB개념 및 설계 -> 개념적/논리적 설계"
    },
    "1-c. 데이터베이스 설계, 정규화": {
        "core_concept": "중복 제거 및 이상 현상 해소를 위한 단계별 정규화 기법 (1NF~5NF, BCNF)",
        "features": "1NF부터 5NF 및 BCNF에 도달하는 조건식 판단 및 무손실 분해 성질 증명이 매년 2문항 이상 단골 출제됩니다.",
        "scope": "DB개념 및 설계 -> 정규화 이론"
    },
    "1-d. 데이터 아키텍처, 데이터베이스 구축 방법론v.4.0(NIA, 2014)": {
        "core_concept": "데이터 아키텍처(DA) 및 국가 정보화 데이터베이스 구축 절차 가이드",
        "features": "데이터 표준화 요소와 공공부문 DB 구축 방법론의 산출물 및 단계별 감리 점검 포인트가 기출됩니다.",
        "scope": "DB개념 및 설계 -> DA 및 구축방법론"
    },
    "1-e. 데이터베이스 품질관리, 공공기관 데이터베이스 표준화 지침": {
        "core_concept": "공공기관 메타데이터 등록 규칙 및 데이터 품질 지표 준칙",
        "features": "메타데이터, 데이터 도메인 관리 요건 및 행안부 DB 표준화 지침의 세부 점검 업무를 다룹니다.",
        "scope": "DB개념 및 설계 -> 품질관리 지침"
    },
    "2-a. 관계대수": {
        "core_concept": "릴레이션을 조작하는 절차적인 연산자 세트 (Select, Project, Join, Division 등)",
        "features": "순수 관계 대수의 시그마, 파이, 디비전 연산의 질의 표현식과 결과 릴레이션 차수 계산이 기출됩니다.",
        "scope": "DB언어 -> 관계 대수"
    },
    "2-b. SQL, 내장SQL, 절차형 SQL, ODBC/JDBC 등": {
        "core_concept": "DDL/DML/DCL 활용과 트리거, 사용자정의함수, 서브쿼리 및 DB 연동 인터페이스",
        "features": "Outer Join의 null 처리, Having절 조건 및 Having vs Where 차이점, 뷰의 갱신 조건 규정을 해석하는 쿼리 분석이 출제됩니다.",
        "scope": "DB언어 -> SQL 질의어"
    },
    "3-a. DB성능(인덱스, 튜닝), 트랜잭션, 동시성 제어": {
        "core_concept": "인덱스(B-Tree) 구조, 조인 방식, 트랜잭션 ACID 특성 및 2PL/MVCC 동시성 제어",
        "features": "B+Tree 특징, 중첩루프/해시/소트머지 조인 비교, 격리수행 수준(Isolation Level) 및 동시성 2PL 규약이 핵심입니다.",
        "scope": "DBMS 기술 -> 성능 및 트랜잭션 통제"
    },
    "3-b. 데이터 백업 및 복구, 데이터 마이그레이션": {
        "core_concept": "REDO/UNDO 복구 로직 및 데이터 이관 기법",
        "features": "로그 기반 지연/즉시 갱신 회복 메커니즘과 검사점(Checkpoint) 기반 복구 범위 판단 문제가 출제됩니다.",
        "scope": "DBMS 기술 -> 백업 및 회복"
    },
    "3-c. 저장장치, 메모리 DB": {
        "core_concept": "물리적 저장구조 및 메인메모리 DBMS 구조",
        "features": "물리 디스크 I/O 최적화 기법과 메모리 디바이스 활용 DB의 백업 덤프 주기 특성을 물어봅니다.",
        "scope": "DBMS 기술 -> 물리 저장장치"
    },
    "3-d. 데이터베이스 보안": {
        "core_concept": "접근제어 기법(DAC, MAC, RBAC) 및 뷰를 이용한 보안 설정",
        "features": "강제(MAC)와 임의(DAC) 접근제어 모델 차이 및 암호화 수준의 점검 조건을 묻습니다.",
        "scope": "DBMS 기술 -> 데이터베이스 보안"
    },
    "4-a. 웹기반 정보시스템": {
        "core_concept": "3계층 아키텍처 상의 애플리케이션 서버와 DBMS 결합 및 연동 규격",
        "features": "웹 환경 정보시스템 감리 시의 DB 연동 기술 아키텍처 관련 항목을 다룹니다.",
        "scope": "DB응용 -> 웹 연동 아키텍처"
    },
    "4-b. 정보검색, 검색엔진": {
        "core_concept": "역색인 구조 검색 메커니즘 및 성능 평가(Precision, Recall)",
        "features": "정밀도(Precision)와 재현율(Recall) 상반관계 계산 및 색인 구조 특성을 다룹니다.",
        "scope": "DB응용 -> 정보 검색 기술"
    },
    "4-c. 멀티미디어, GIS 등": {
        "core_concept": "공간 정보 검색용 색인 및 대용량 멀티미디어 컬럼 저장 기술",
        "features": "R-Tree 색인의 구조적 분할 및 공간 쿼리 점검 포인트가 종종 출제됩니다.",
        "scope": "DB응용 -> 공간/멀티미디어 기술"
    },
    "4-d. 분산 DBMS, 모바일 DBMS": {
        "core_concept": "4대 투명성 준수 및 2단계 커밋(2PC) 분산 트랜잭션 동기화",
        "features": "위치/중복/장애/단편화 투명성 구분과 2PC 프로토콜의 코디네이터 동작 단계를 다룹니다.",
        "scope": "DB응용 -> 분산 아키텍처"
    },
    "4-e. OPEN API, 공공데이터": {
        "core_concept": "개방 데이터 플랫폼 구성 및 연동 표준 규격",
        "features": "REST API 기반 연동 지침과 공공 데이터 수집 기준을 점검합니다.",
        "scope": "DB응용 -> 공공데이터 API"
    },
    "5-a. 빅데이터 관련 기술(저장, 처리, 분석, 시각화)": {
        "core_concept": "하둡 분산 파일시스템(HDFS) 구조 및 MapReduce 병렬 처리 프레임워크",
        "features": "마스터-네임노드, 데이터노드 장애 극복 메커니즘과 스파크 인메모리 처리 장점을 대조합니다.",
        "scope": "빅데이터 및 AI데이터 -> 빅데이터 저장/처리"
    },
    "5-b. NoSQL": {
        "core_concept": "비정형 데이터 분산을 위한 CAP 이론 및 스키마리스 Key-Value/Document/Graph 저장소",
        "features": "CAP 정리에 의한 고가용성과 일관성 트레이드오프 분석 및 Cassandra, MongoDB 등의 특징 매핑을 질문합니다.",
        "scope": "빅데이터 및 AI데이터 -> NoSQL 아키텍처"
    },
    "5-c. 데이터마이닝, DW": {
        "core_concept": "OLAP 다차원 분석 큐브 연산 및 대용량 데이터 유용 관계 추출 마이닝 기법",
        "features": "스타/스노우플레이크 구조 차이, OLAP의 Drill-down/Roll-up 기법 정의 및 연관 규칙 지지도/신뢰도 계산이 출제됩니다.",
        "scope": "빅데이터 및 AI데이터 -> DW 및 마이닝"
    },
    "5-d. AI학습데이터 구축": {
        "core_concept": "AI 모델 학습용 대용량 원시 데이터 가공 및 품질 점검 준칙",
        "features": "NIA 인공지능 학습데이터 가이드 상의 품질 요건 및 어노테이션 유형 구별이 신규 빈출 주제입니다.",
        "scope": "빅데이터 및 AI데이터 -> AI 학습데이터"
    }
}

# 5대 대단원 매핑
TOPIC_CATEGORIES = {
    "1-a. 데이터베이스 시스템 개념 및 이론": "1. DB개념 및 설계",
    "1-b. 데이터 모델의 개념, 관계형/객체지향 DB": "1. DB개념 및 설계",
    "1-c. 데이터베이스 설계, 정규화": "1. DB개념 및 설계",
    "1-d. 데이터 아키텍처, 데이터베이스 구축 방법론v.4.0(NIA, 2014)": "1. DB개념 및 설계",
    "1-e. 데이터베이스 품질관리, 공공기관 데이터베이스 표준화 지침": "1. DB개념 및 설계",
    
    "2-a. 관계대수": "2. DB언어",
    "2-b. SQL, 내장SQL, 절차형 SQL, ODBC/JDBC 등": "2. DB언어",
    
    "3-a. DB성능(인덱스, 튜닝), 트랜잭션, 동시성 제어": "3. DBMS 기술",
    "3-b. 데이터 백업 및 복구, 데이터 마이그레이션": "3. DBMS 기술",
    "3-c. 저장장치, 메모리 DB": "3. DBMS 기술",
    "3-d. 데이터베이스 보안": "3. DBMS 기술",
    
    "4-a. 웹기반 정보시스템": "4. DB응용",
    "4-b. 정보검색, 검색엔진": "4. DB응용",
    "4-c. 멀티미디어, GIS 등": "4. DB응용",
    "4-d. 분산 DBMS, 모바일 DBMS": "4. DB응용",
    "4-e. OPEN API, 공공데이터": "4. DB응용",
    
    "5-a. 빅데이터 관련 기술(저장, 처리, 분석, 시각화)": "5. 빅데이터 및 AI데티어",
    "5-b. NoSQL": "5. 빅데이터 및 AI데티어",
    "5-c. 데이터마이닝, DW": "5. 빅데이터 및 AI데티어",
    "5-d. AI학습데이터 구축": "5. 빅데이터 및 AI데티어"
}

def crop_question_images(pdf_path, year, output_dir):
    """[공통 모듈 위임] PDF로부터 DB 과목 문항 영역을 추출하여 이미지로 저장하고 위치 좌표를 반환"""
    local_img_dir = r"e:\jolly-carson\reports\images"
    artifact_img_dir = os.path.join(ARTIFACT_DIR, "images")
    return image_cropper.get_question_positions_and_crop(
        pdf_path, year, "DB", local_img_dir, artifact_img_dir, force_crop=FORCE_CROP
    )

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
    
    # 각 개념 항목에 고유 global_idx 부여하여 필터링 시에도 일관된 DOM ID 매핑 보장
    for g_idx, item in enumerate(sorted_concepts):
        item["global_idx"] = g_idx
        
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
    
    print("\n[성공] 초프리미엄 DB 공식범위 기출문제 뷰어 빌드가 완료되었습니다!")

def build_html():
    question_db, concept_map = run_extraction_and_mapping()
    update_shared_db(question_db, "DB")
    html_content = build_html_content(question_db, concept_map)
    
    local_path, artifact_path = get_output_paths("db_official_scopes.html")
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[로컬] 저장 완료: {local_path}")
    
    os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[아티팩트] 저장 완료: {artifact_path}")

if __name__ == "__main__":
    build_html()
