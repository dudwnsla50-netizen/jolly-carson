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
    artifact_img_dir = r"C:\Users\DCCIS040000\.gemini\antigravity-ide\brain\7e1fd111-1dc1-495d-82a1-c40573600184\images"
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
    
    html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>데이터베이스 공식 범위별 기출 뷰어</title>
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

        .viewer-image-wrapper {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            overflow: hidden;
            background: #0c101b;
            display: flex;
            justify-content: center;
            padding: 1rem;
        }

        .viewer-img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            filter: brightness(0.95) contrast(1.05);
        }

        /* Hide elements helper */
        .hidden { display: none !important; }
    
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

    </style>
    <script src="exam_db/db_db.js?v=20260613"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>데이터베이스 공식 범위별 기출분석</h1>
            <p class="subtitle">공식 시험 범위 표준 가이드를 기준으로 매핑된 21개 세부 중단원 정밀 대시보드</p>
            <div class="meta-badges" style="margin-top: 1rem; margin-bottom: 1.2rem;">
                <span class="badge">기출 범위: 2015년 ~ 2026년</span>
                <span class="badge accent">총 분석 데이터: <span id="total-question-badge">0</span> 문항</span>
                <span class="badge" onclick="openTopicListModal()" style="cursor: pointer; transition: all 0.2s;" title="클릭 시 중단원 목록 팝업 열기">
                    매핑된 공식 중단원: <span id="topic-count-badge">0</span>개
                </span>
            </div>
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
        </header>

        <div class="filter-section">
            <button class="filter-btn active" onclick="filterCategory('all')">전체 대단원</button>
            <button class="filter-btn" onclick="filterCategory('1. DB개념 및 설계')">1. DB개념 및 설계</button>
            <button class="filter-btn" onclick="filterCategory('2. DB언어')">2. DB언어</button>
            <button class="filter-btn" onclick="filterCategory('3. DBMS 기술')">3. DBMS 기술</button>
            <button class="filter-btn" onclick="filterCategory('4. DB응용')">4. DB응용</button>
            <button class="filter-btn" onclick="filterCategory('5. 빅데이터 및 AI데이터')">5. 빅데이터 및 AI데이터</button>
        </div>

        <div class="accordion-list" id="accordionContainer">
            <!-- Dynamic Accordion Items Rendered by JS -->
        </div>
    </div>

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
                badge.href = target + '?v=20260613';
            } else {
                badge.href = '/reports/' + target + '?v=20260613';
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
                window.location.href = targetRedirect + '?v=20260613';
            } else {
                window.location.href = '/reports/' + targetRedirect + '?v=20260613';
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
                badge.href = target + '?v=20260613';
            } else {
                badge.href = '/reports/' + target + '?v=20260613';
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

        // Inject mappings & DB from Python
        
        const conceptMappings = _MAPPING_PLACEHOLDER_;


        // 9종 대시보드 네비게이션
        function navigateDashboard(target) {
            const isLocal = window.location.protocol === 'file:';
            if (isLocal) {
                window.location.href = target;
            } else {
                window.location.href = '/reports/' + target;
            }
        }

        function filterCategory(category) {
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.innerText === category || (category === 'all' && btn.innerText === '전체 대단원')) {
                    btn.classList.add('active');
                }
            });
            renderAccordions(category);
        }

        function renderAccordions(filter = 'all') {
            const container = document.getElementById('accordionContainer');
            container.innerHTML = '';

            const filtered = conceptMappings.filter(item => {
                if (filter === 'all') return true;
                return item.category === filter;
            });

            filtered.forEach((item) => {
                const globalIdx = item.global_idx;
                const totalCount = item.count;
                const yearsStr = item.years.length > 0 ? item.years.join(', ') : '없음';

                const accordion = document.createElement('div');
                accordion.className = 'accordion-item';
                accordion.dataset.category = item.category;
                accordion.id = `item-${globalIdx}`;

                accordion.innerHTML = `
                    <button class="accordion-trigger" onclick="toggleAccordion('${globalIdx}')">
                        <div class="card-header-row">
                            <div class="card-title-group">
                                <span class="rank-badge">${item.concept.split('.')[0]}</span>
                                <span class="concept-title">${item.concept}</span>
                                <span class="category-tag">${item.category}</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 0.8rem;">
                                <span class="freq-count-badge">기출 ${totalCount}회</span>
                                <span class="arrow">▼</span>
                            </div>
                        </div>
                        <div class="card-meta-grid">
                            <div class="meta-label">핵심 요약</div>
                            <div class="meta-value">${item.core_concept}</div>
                            <div class="meta-label">기출 연도</div>
                            <div class="meta-value accent">${yearsStr}</div>
                        </div>
                    </button>
                    <div class="accordion-content">
                        <div class="accordion-inner">
                            <div>
                                <h4 class="section-title">출제 범위 및 핵심 특징</h4>
                                <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.4rem; line-height: 1.6;">
                                    <strong>세부 범위:</strong> ${item.scope}<br>
                                    <strong>핵심 특징:</strong> ${item.features}
                                </p>
                            </div>
                            <div>
                                <h4 class="section-title">출제 문항 일람 (선택 시 하단에 문제지와 원본 크롭 이미지가 즉시 표시됩니다)</h4>
                                <div class="year-grid" style="margin-top: 0.6rem;">
                                    ${item.questions.map(q => `
                                        <button class="year-btn" id="btn-${globalIdx}-${q.year}-${q.num}" onclick="showQuestion('${globalIdx}', ${q.year}, ${q.num})">
                                            ${q.year}년 <span class="num-label">${q.num}번</span>
                                        </button>
                                    `).join('')}
                                </div>
                            </div>
                            
                            <div class="inline-question-viewer hidden" id="viewer-${globalIdx}">
                                <div class="viewer-header">
                                    <span class="viewer-title" id="viewer-title-${globalIdx}"></span>
                                    <button class="viewer-close-btn" onclick="closeViewer('${globalIdx}')">닫기 ✕</button>
                                </div>
                                <div class="viewer-body" id="viewer-body-${globalIdx}"></div>
                                <div class="viewer-image-wrapper" id="viewer-img-wrap-${globalIdx}">
                                    <img class="viewer-img" id="viewer-img-${globalIdx}" src="" alt="크롭 문제지 영역">
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(accordion);
            });
        }

        function toggleAccordion(idx) {
            const item = document.getElementById(`item-${idx}`);
            const content = item.querySelector('.accordion-content');
            const isActive = item.classList.contains('active');

            document.querySelectorAll('.accordion-item').forEach(el => {
                el.classList.remove('active');
                el.querySelector('.accordion-content').style.maxHeight = null;
            });

            if (!isActive) {
                item.classList.add('active');
                content.style.maxHeight = content.scrollHeight + 1000 + 'px'; // 여유 마진 추가
            }
        }

        function showQuestion(idx, year, num) {
            // 버튼 활성화 스타일
            document.querySelectorAll(`#item-${idx} .year-btn`).forEach(btn => btn.classList.remove('active-btn'));
            const activeBtn = document.getElementById(`btn-${idx}-${year}-${num}`);
            if (activeBtn) activeBtn.classList.add('active-btn');

            const key = `${year}_${num}`;
            const questionBody = examDatabase[key] || "지문 정보를 읽어올 수 없습니다.";
            
            const viewer = document.getElementById(`viewer-${idx}`);
            viewer.classList.remove('hidden');

            const title = document.getElementById(`viewer-title-${idx}`);
            title.innerText = `[상세 기출] ${year}년도 데이터베이스 ${num}번 문항`;

            const body = document.getElementById(`viewer-body-${idx}`);
            body.innerText = questionBody;

            // 로컬 파일과 웹 서버 URL 경로 분기 처리
            const isLocal = window.location.protocol === 'file:';
            const imgPath = isLocal ? `images/${year}_${num}.png` : `/reports/images/${year}_${num}.png`;
            
            const img = document.getElementById(`viewer-img-${idx}`);
            img.src = imgPath;

            // 아코디언 높이 조정 (뷰어가 열리면서 늘어난 높이 반영)
            const content = document.getElementById(`item-${idx}`).querySelector('.accordion-content');
            content.style.maxHeight = content.scrollHeight + 500 + 'px';
        }

        function closeViewer(idx) {
            const viewer = document.getElementById(`viewer-${idx}`);
            viewer.classList.add('hidden');
            
            document.querySelectorAll(`#item-${idx} .year-btn`).forEach(btn => btn.classList.remove('active-btn'));

            // 아코디언 높이 재조정
            const content = document.getElementById(`item-${idx}`).querySelector('.accordion-content');
            content.style.maxHeight = content.scrollHeight + 'px';
        }

        // [설계 의도] 공식 중단원 목록 모달 팝업을 열고, 클릭 시 해당 아코디언으로 포커싱 및 스크롤을 시킵니다.
        // 대단원 필터 여부와 무관하게 전체 21개 중단원 목록을 언제나 일관되게 서비스하며,
        // 현재 숨겨진 항목을 클릭한 경우에는 필터를 자동으로 초기화하여 정상 노출시킨 후 포커싱을 유도합니다.
        window.openTopicListModal = function() {
            const modal = document.getElementById('topic-modal');
            const listEl = document.getElementById('modal-topic-list');
            listEl.innerHTML = '';
            
            conceptMappings.forEach((item) => {
                const li = document.createElement('li');
                li.className = 'modal-topic-item';
                li.style.cursor = 'pointer';
                li.onclick = () => {
                    closeTopicModal();
                    
                    // 선택한 중단원이 속한 대단원이 현재 필터와 맞지 않으면 필터를 해제하여 보이게 처리
                    const activeFilterBtn = document.querySelector('.filter-btn.active');
                    const activeFilter = activeFilterBtn ? activeFilterBtn.innerText : '전체 대단원';
                    if (activeFilter !== '전체 대단원' && item.category !== activeFilter) {
                        filterCategory('all');
                    }
                    
                    setTimeout(() => {
                        const itemEl = document.getElementById(`item-${item.global_idx}`);
                        if (itemEl) {
                            const trigger = itemEl.querySelector('.accordion-trigger');
                            const content = itemEl.querySelector('.accordion-content');
                            if (content.style.maxHeight === '0px' || !content.style.maxHeight) {
                                trigger.click();
                            }
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

        // Initial Render & Badge Setup
        if (document.getElementById('topic-count-badge')) {
            document.getElementById('topic-count-badge').textContent = conceptMappings.length;
        }
        if (document.getElementById('total-question-badge')) {
            if (document.getElementById('total-question-badge')) {
            const uniqueQuestions = new Set();
            conceptMappings.forEach(item => {
                item.questions.forEach(q => {
                    uniqueQuestions.add(q.year + "_" + q.num);
                });
            });
            document.getElementById('total-question-badge').textContent = uniqueQuestions.size;
        }
        }
        renderAccordions('all');
    </script>

    <!-- 세부 토픽 목록 팝업 모달 -->
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
    final_html = html_template.replace("_MAPPING_PLACEHOLDER_", mapping_json)
    
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
