# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

"""
[초프리미엄 데이터베이스(DB) 기출문제 뷰어 자동 빌더]
- 목적: 2015년~2026년 기출 PDF에서 DB 과목 전체 문항(51~75번)을 추출하고,
  12대 세부 토픽 사전을 기반으로 정형화된 빈출 분석 대시보드 웹앱(db_frequent_concepts.html)을 생성합니다.
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
    "DB 정규화 단계 및 정규형 특징 (1NF~5NF, BCNF)": ["정규화", "BCNF", "3NF", "4NF", "5NF", "함수 종속", "다치 종속", "조인 종속", "이행적", "결정자"],
    "관계대수 및 순수 관계 연산자": ["관계대수", "관계 대수", "셀렉트", "프로젝트", "조인", "디비전", "순수 관계 연산자", "관계해석", "division", "projection"],
    "트랜잭션 ACID 특성 및 상태 전이": ["acid", "원자성", "일관성", "격리성", "영속성", "트랜잭션", "durability", "isolation"],
    "DBMS 회복 기법 (REDO / UNDO)": ["회복 기법", "redo", "undo", "즉시 갱신", "지연 갱신", "체크포인트", "검사점 회복", "회복기법"],
    "동시성 제어 및 2단계 잠금 규약 (2PL)": ["동시성 제어", "병행 제어", "락킹", "locking", "2단계 잠금", "2pl", "교착상태", "데드락", "로킹", "병행제어"],
    "분산 데이터베이스 투명성 요건": ["분산 db", "분산 데이터베이스", "위치 투명성", "중복 투명성", "단편화 투명성", "장애 투명성", "분산 dbms"],
    "NoSQL 데이터베이스 분류 및 CAP 이론": ["nosql", "cap 이론", "cap 정리", "key-value", "document store", "hbase", "cassandra", "mongodb"],
    "데이터웨어하우스 스키마 설계 (스타/스노우플레이크)": ["데이터 웨어하우스", "data warehouse", "스타 스키마", "스노우플레이크", "dw", "스타스키마"],
    "SQL 쿼리 구문 (DDL/DML/DCL)": ["sql", "select", "update", "insert", "delete", "create", "grant", "revoke", "having", "group by"],
    "인덱스 및 B-Tree 구조 특징": ["인덱스", "index", "b-tree", "b+tree", "해싱", "데이터 물리", "클러스터드 인덱스"],
    "빅데이터 분산 플랫폼 (Hadoop/MapReduce)": ["하둡", "hadoop", "맵리듀스", "mapreduce", "스파크", "spark", "hdfs"],
    "ER 데이터 모델링 및 식별/비식별 관계": ["e-r", "er 다이어그램", "식별 관계", "비식별 관계", "다대다", "개체-관계"]
}

CONCEPT_METADATA = {
    "DB 정규화 단계 및 정규형 특징 (1NF~5NF, BCNF)": {
        "core_concept": "릴레이션 스키마 분해를 통해 중복을 제거하고 이상 현상을 방지하는 정밀 설계 기법",
        "features": "제3정규형(이행적 함수 종속 제거)에서 BCNF(모든 결정자가 후보키), 제4정규형(다치종속), 제5정규형(조인종속)으로 가는 단계적 결정 조건을 구별하는 문제가 매년 고정 출제됩니다.",
        "scope": "DB개념 및 설계 -> 논리적 설계 -> 정규화"
    },
    "관계대수 및 순수 관계 연산자": {
        "core_concept": "릴레이션을 처리하는 절차적 정형 대수 언어 및 집합 연산",
        "features": "순수 관계 연산자(Select: 시그마, Project: 파이, Join: 리본, Division: 나누기)의 수학적 기호 표현 및 SQL 질의문과의 상호 변환 동작을 깊이 있게 다룹니다.",
        "scope": "DB언어 -> 관계 대수 및 관계 해석"
    },
    "트랜잭션 ACID 특성 및 상태 전이": {
        "core_concept": "데이터베이스 논리적 연산 단위인 트랜잭션의 4대 필수 성질 보장",
        "features": "원자성(Atomicity), 일관성(Consistency), 격리성(Isolation - 특히 격리 레벨별 Read phenomena), 영속성(Durability)의 정의와 위배 예시를 평가합니다.",
        "scope": "DBMS 기술 -> 트랜잭션 정의"
    },
    "DBMS 회복 기법 (REDO / UNDO)": {
        "core_concept": "트랜잭션 장애 발생 시 데이터베이스를 일관된 이전 상태로 복구하는 기술",
        "features": "로그 기반 즉시 갱신(REDO/UNDO 모두 수행)과 지연 갱신(REDO만 수행)의 차이, 그리고 검사점(Checkpoint) 기법 적용 시점 기준 복구 로그 분석 연산이 출제됩니다.",
        "scope": "DBMS 기술 -> 트랜잭션 회복"
    },
    "동시성 제어 및 2단계 잠금 규약 (2PL)": {
        "core_concept": "다중 사용자 환경에서 트랜잭션들이 동시에 실행될 때 직렬 가능성을 보장하는 잠금 메커니즘",
        "features": "2단계 잠금 규약(2PL)의 직렬화 가능성 보장 여부 및 교착상태(Deadlock) 발생 한계점, 낙관적 검증 기법, 다중 버전 동시성 제어(MVCC)의 특징을 비교합니다.",
        "scope": "DBMS 기술 -> 동시성 제어"
    },
    "분산 데이터베이스 투명성 요건": {
        "core_concept": "물리적으로 분산된 여러 DB 노드를 단일 시스템처럼 투명하게 다루는 아키텍처",
        "features": "4대 투명성인 위치(Location), 중복(Replication), 단편화(Fragmentation), 장애(Failure) 투명성의 정의를 명확히 구분하는 문제가 빈출됩니다.",
        "scope": "DB응용 -> 분산 데이터베이스"
    },
    "NoSQL 데이터베이스 분류 및 CAP 이론": {
        "core_concept": "비관계형 대용량 데이터를 처리하기 위한 스키마리스 DBMS 아키텍처 표준",
        "features": "일관성(C), 가용성(A), 분할 용인성(P) 중 2가지만 충족 가능한 CAP 이론의 한계와 CA, CP, AP 계열 NoSQL 제품군(MongoDB, Cassandra 등) 맵핑을 다룹니다.",
        "scope": "빅데이터 및 AI데이터 -> NoSQL"
    },
    "데이터웨어하우스 스키마 설계 (스타/스노우플레이크)": {
        "core_concept": "다차원 데이터 분석(OLAP)을 위한 의사결정 지원용 전사 통합 데이터 아키텍처",
        "features": "스타 스키마(팩트 테이블과 역정규화된 디멘션 테이블 구성)와 이를 완전 정규화하여 조인 성능 조정을 시도하는 스노우플레이크 스키마의 구조적 장단점을 대조합니다.",
        "scope": "DB응용 -> 데이터웨어하우스 및 OLAP"
    },
    "SQL 쿼리 구문 (DDL/DML/DCL)": {
        "core_concept": "표준 SQL 선언문 활용 및 하위 질의, 집계, 뷰, 권한 제어 연산",
        "features": "Having 조건절 및 Group By 그룹 연산의 우선순위, EXISTS와 IN 연산자의 동작 효율, 그리고 Outer Join 수행 시 널(NULL) 값 분포 문제를 해석하는 쿼리 분석이 출제됩니다.",
        "scope": "DB언어 -> 표준 SQL"
    },
    "인덱스 및 B-Tree 구조 특징": {
        "core_concept": "검색 성과를 극대화하기 위해 물리 디스크 블록 검색 빈도를 최적화하는 색인 설계",
        "features": "B-Tree와 B+Tree(리프 노드 간 연결 리스트 제공)의 구조적 탐색 효율 차이, 클러스터드/넌클러스터드 인덱스 생성 시 테이블 물리 정렬 상태 차이를 질문합니다.",
        "scope": "DB개념 및 설계 -> 물리적 설계 -> 색인"
    },
    "빅데이터 분산 플랫폼 (Hadoop/MapReduce)": {
        "core_concept": "저가형 범용 서버를 이용해 대용량 빅데이터를 분산 저장하고 병렬 처리하는 에코시스템",
        "features": "HDFS(하둡 분산 파일시스템)의 마스터-슬레이브 복제 아키텍처와 맵(Map) 단계 및 리듀스(Reduce) 단계 간 셔플링 연산의 파이프라인 특징을 다룹니다.",
        "scope": "빅데이터 및 AI데이터 -> 분산 플랫폼"
    },
    "ER 데이터 모델링 및 식별/비식별 관계": {
        "core_concept": "개념적 설계 단계의 엔티티, 속성, 관계 표현법 및 물리 스키마 맵핑 규칙",
        "features": "식별 관계(부모 키를 자식의 주식별자로 상속)와 비식별 관계(일반 속성으로 상속)의 점선/실선 기호 해석 및 다대다 관계 해소를 위한 교차 테이블 설계를 묻습니다.",
        "scope": "DB개념 및 설계 -> 개념적 설계 -> ERD"
    }
}

TOPIC_CATEGORIES = {
    "DB 정규화 단계 및 정규형 특징 (1NF~5NF, BCNF)": "DB개념 및 설계",
    "관계대수 및 순수 관계 연산자": "DB언어",
    "트랜잭션 ACID 특성 및 상태 전이": "DBMS 기술",
    "DBMS 회복 기법 (REDO / UNDO)": "DBMS 기술",
    "동시성 제어 및 2단계 잠금 규약 (2PL)": "DBMS 기술",
    "분산 데이터베이스 투명성 요건": "DB응용",
    "NoSQL 데이터베이스 분류 및 CAP 이론": "빅데이터 및 AI데이터",
    "데이터웨어하우스 스키마 설계 (스타/스노우플레이크)": "DB응용",
    "SQL 쿼리 구문 (DDL/DML/DCL)": "DB언어",
    "인덱스 및 B-Tree 구조 특징": "DB개념 및 설계",
    "빅데이터 분산 플랫폼 (Hadoop/MapReduce)": "빅데이터 및 AI데이터",
    "ER 데이터 모델링 및 식별/비식별 관계": "DB개념 및 설계"
}

def crop_question_images(pdf_path, year, output_dir):
    """[공통 모듈 위임] PDF로부터 DB 과목 문항 영역을 추출하여 이미지로 저장하고 위치 좌표를 반환"""
    local_img_dir = r"e:\jolly-carson\reports\images"
    artifact_img_dir = os.path.join(ARTIFACT_DIR, "images")
    return image_cropper.get_question_positions_and_crop(
        pdf_path, year, "DB", local_img_dir, artifact_img_dir, force_crop=FORCE_CROP
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

def slice_db_section(full_text):
    start_pattern = r"\b51\s*[\.\)]"
    end_pattern = r"\b76\s*[\.\)]"
    
    start_match = re.search(start_pattern, full_text)
    end_match = re.search(end_pattern, full_text)
    
    if start_match:
        start_idx = start_match.start()
        end_idx = end_match.start() if end_match else len(full_text)
        return full_text[start_idx:end_idx].strip()
    return ""

def parse_questions(db_text):
    questions = []
    for num in range(51, 76):
        curr_pat = rf"(?<![\.\d]){num}\s*[\.\)]"
        next_pat = rf"(?<![\.\d]){num+1}\s*[\.\)]"
        
        curr_match = re.search(curr_pat, db_text)
        if not curr_match:
            continue
            
        start_pos = curr_match.start()
        next_match = re.search(next_pat, db_text)
        
        if next_match:
            end_pos = next_match.start()
            q_body = db_text[start_pos:end_pos].strip()
        else:
            q_body = db_text[start_pos:].strip()
            
        # [방어 코드] 보기 ④번 이후에 다단 텍스트 등의 영향으로 타 문제(예: 59번)가 달라붙는 버그 방지
        if "④" in q_body:
            clean_match = re.search(r"④.*?(?=(?:\r?\n)\s*(?!(?:1|2|3|4)\b)\d+\s*[\.\)])", q_body, re.DOTALL)
            if clean_match:
                q_body = q_body[:clean_match.end()].strip()
            
            # 과목 경계를 알리는 한글 구분자나 페이지 지시문이 붙어 있으면 잘라냅니다.
            for separator in ["시스템구조", "보안", "프로젝트관리", "소프트웨어", "=== NEW PAGE ==="]:
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
    update_shared_db(question_db, "DB")
    html_content = build_html_content(question_db, concept_map)
    
    local_path, artifact_path = get_output_paths("db_frequent_concepts.html")
    
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
