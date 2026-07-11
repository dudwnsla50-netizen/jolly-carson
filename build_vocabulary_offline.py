# -*- coding: utf-8 -*-
"""
[오프라인 용어 자동 추출 및 단어장 구축 엔진]
- 설계 목적: Gemini API 키 없이 로컬 리소스(서브노트, 암기노트)와 기출문제 DB(Supabase & Local JSON)를 분석하여
  SE, DB, SA, SC 과목의 고품질 단어장을 자동으로 구축하고 jolly_carson.db에 저장합니다.
- 원칙 준수: 외부 라이브러리 설치 없이 파이썬 내장 모듈(sqlite3, json, xml, zipfile, re, urllib)만 활용합니다.
"""

import os
import sys
import json
import sqlite3
import zipfile
import re
import xml.etree.ElementTree as ET
from datetime import datetime

# Windows 콘솔 한글 깨짐 방지
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOCAB_DB_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "jolly_carson.db")
EXCEL_SUBNOTE_PATH = r"d:\100.lyj\anti_workspace\감리사_시험대비\서브노트(감리)_160223.xlsx"
EXCEL_MEMONOTE_PATH = r"d:\100.lyj\anti_workspace\감리사_시험대비\암기노트.xlsx"
PAST_EXAMS_JSON_PATH = os.path.join(BASE_DIR, "data", "past_exams_db.json")

# Supabase PostgreSQL 연결 정보
SUPABASE_URL_RAW = "postgresql://postgres.sqrnhkhgctfxnxwbiwxp:yj1024word%5E%5E@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

SUBJECT_NAMES = {
    "PM": "사업관리(PM)",
    "SE": "소프트웨어공학(SE)",
    "DB": "데이터베이스(DB)",
    "SA": "시스템구조(SA)",
    "SC": "보안(SC)"
}

# ==========================================
# 1. 엑셀 파일 XML 기반 파서 유틸리티
# ==========================================

def read_xlsx_sheet(file_path, sheet_index=1):
    """
    [설계 의도]
    외부 라이브러리(openpyxl, pandas) 의존성 없이 .xlsx zip 구조를 직접 풀어
    sharedStrings와 sheet XML 데이터를 매핑해 2차원 행 배열을 추출합니다.
    """
    if not os.path.exists(file_path):
        print(f"  [경고] 파일이 존재하지 않습니다: {file_path}")
        return []

    try:
        with zipfile.ZipFile(file_path) as z:
            ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            # shared strings 로드
            shared_strings = []
            try:
                ss_data = z.read('xl/sharedStrings.xml')
                ss_xml = ET.fromstring(ss_data)
                for si in ss_xml.findall('.//ns:si', ns):
                    t_elem = si.find('ns:t', ns)
                    if t_elem is not None:
                        shared_strings.append(t_elem.text or '')
                    else:
                        r_texts = []
                        for t in si.findall('.//ns:t', ns):
                            r_texts.append(t.text or '')
                        shared_strings.append(''.join(r_texts))
            except KeyError:
                pass # sharedStrings가 없는 단순 수식/숫자 시트 대응

            # 대상 시트 로드 (sheet1.xml, sheet2.xml 등)
            sheet_data = z.read(f'xl/worksheets/sheet{sheet_index}.xml')
            sheet_xml = ET.fromstring(sheet_data)
            
            rows_data = []
            for row in sheet_xml.findall('.//ns:row', ns):
                row_idx = int(row.get('r'))
                cols = {}
                for cell in row.findall('ns:c', ns):
                    r = cell.get('r') # 예: A1, B25
                    t = cell.get('t') # 타입
                    val_elem = cell.find('ns:v', ns)
                    val = val_elem.text if val_elem is not None else ''
                    
                    if t == 's' and val:
                        try:
                            val = shared_strings[int(val)]
                        except IndexError:
                            pass
                    
                    # 컬럼 알파벳 문자만 추출 (A, B, C 등)
                    col_letter = re.match(r'[A-Z]+', r).group()
                    cols[col_letter] = val
                rows_data.append((row_idx, cols))
            
            return rows_data
    except Exception as e:
        print(f"  [오류] 엑셀 파싱 중 예외 발생 ({os.path.basename(file_path)}): {e}")
        return []


# ==========================================
# 2. 로컬 엑셀 데이터 용어/정의 추출 엔진
# ==========================================

def extract_from_subnote():
    """
    서브노트(감리)_160223.xlsx 파일에서 과목별 단어를 정교하게 추출합니다.
    행 번호 범위와 대분류 헤더를 기준으로 과목을 자동 매핑합니다.
    """
    print(f"\n[1/4] '{os.path.basename(EXCEL_SUBNOTE_PATH)}' 분석 시작...")
    rows = read_xlsx_sheet(EXCEL_SUBNOTE_PATH, sheet_index=1)
    if not rows:
        return []

    terms = []
    
    # 엑셀 행 번호 기준 과목 맵 정의
    # (앞서 스캔한 헤더 섹션들의 row 번호를 분석하여 범위 확정)
    def detect_subject_by_row(r_idx):
        if 1 <= r_idx <= 76:
            return "PM"          # 감리 법/제도 및 EA/ISP
        elif 77 <= r_idx <= 113:
            return "SE"          # SD구축 I, II
        elif 114 <= r_idx <= 118:
            return "DB"          # 데이터구축
        elif 119 <= r_idx <= 123:
            return "SE"          # 운영/유지보수
        elif 124 <= r_idx <= 198:
            return "PM"          # 사업관리, SW진흥법, 대가산정, 분리발주
        elif 199 <= r_idx <= 224:
            return "SE"          # 호환성, 웹접근성, 모바일서비스지침
        elif 225 <= r_idx <= 227:
            return "SC"          # 개발보안의무제
        elif 228 <= r_idx <= 247:
            return "DB"          # DB품질관리, DB표준화지침
        elif 248 <= r_idx <= 264:
            return "SA"          # 구축운영지침 기본/기술/하도급
        elif 265 <= r_idx <= 265:
            return "SC"          # 개발보안 원칙
        elif 266 <= r_idx <= 287:
            return "SA"          # 서비스전달, 요소기술, 플랫폼
        elif 288 <= r_idx <= 314:
            return "PM"          # 성과관리, 하도급판단기준
        elif 315 <= r_idx <= 322:
            return "SE"          # CBD 표준산출물
        elif 323 <= r_idx <= 376:
            return "PM"          # IT Governance, COBIT, COSO, EA성숙도
        elif 377 <= r_idx <= 388:
            return "SE"          # TRM, 공유서비스
        elif 389 <= r_idx <= 433:
            return "PM"          # SW사업 감독, 위탁
        return "PM"

    # 시트 내 임시 대분류 상태 보존용
    current_major = "통합관리"
    
    for r_idx, cols in rows:
        if r_idx <= 2: # 타이틀 행 스킵
            continue
            
        subj = detect_subject_by_row(r_idx)
        
        # A열에 텍스트가 존재하고 다른 열이 비어있는 경우 대분류 주제 업데이트
        val_a = cols.get('A', '').strip()
        val_b = cols.get('B', '').strip()
        val_c = cols.get('C', '').strip()
        val_d = cols.get('D', '').strip()
        val_e = cols.get('E', '').strip() # 설명열
        
        if val_a and not val_b and not val_e:
            current_major = val_a
            continue
        elif not val_a and val_b and not val_e:
            # B열 제목도 대분류로 참고
            current_major = val_b
            continue

        # 설명(E열)이 있어야 용어로 성립
        if not val_e or len(val_e.strip()) < 5:
            continue
            
        # 용어 이름 결정: A, B, C, D열 중 가장 상세 레벨(가장 오른쪽에 위치한 값) 선택
        term_name = ""
        for col_name in ['D', 'C', 'B', 'A']:
            txt = cols.get(col_name, '').strip()
            if txt:
                term_name = txt
                break
                
        if not term_name or term_name == current_major or len(term_name) < 2:
            continue
            
        # 특수문자나 숫자만 있는 용어 걸러내기
        if re.match(r'^[0-9\-\.\s]+$', term_name):
            continue

        # 대분류 매핑 정제 (jolly_carson.db의 FIXED_MAJOR_TOPICS 범주 중 하나에 적절히 매핑)
        # 기본값으로 current_major를 정제해서 매핑
        topic_major = "통합관리"
        if subj == "SE":
            topic_major = "요구사항분석 및 설계"
            if "테스트" in current_major or "검증" in current_major:
                topic_major = "구현 및 테스트"
            elif "유지" in current_major or "운영" in current_major:
                topic_major = "유지관리 및 운영"
            elif "비용" in current_major or "품질" in current_major or "FP" in current_major:
                topic_major = "SW품질 및 비용산정"
            elif "방법론" in current_major or "구조" in current_major or "CBD" in current_major or "호환성" in current_major or "접근성" in current_major:
                topic_major = "개발방법론/SW구조/공개SW"
        elif subj == "DB":
            topic_major = "DB개념 및 설계"
            if "품질" in current_major or "표준화" in current_major:
                topic_major = "DB응용"
            elif "SQL" in current_major:
                topic_major = "DB언어"
            elif "빅데이터" in current_major or "AI" in current_major:
                topic_major = "빅데이터 및 AI데이터"
        elif subj == "SA":
            topic_major = "아키텍처 설계 및 구축"
            if "네트워크" in current_major or "통신" in current_major or "인터페이스" in current_major:
                topic_major = "데이터 통신 및 네트워크 설계"
            elif "신기술" in current_major or "클라우드" in current_major:
                topic_major = "기타 신기술"
        elif subj == "SC":
            topic_major = "정보보호 법규 및 개인정보보호"
            if "개발" in current_major or "보안의무" in current_major:
                topic_major = "개발 및 운영 보안"
        elif subj == "PM":
            topic_major = "감리업무"
            if "법" in current_major or "고시" in current_major or "진흥법" in current_major or "제도" in current_major:
                topic_major = "법규/제도"
            elif "대가" in current_major or "산정" in current_major:
                topic_major = "대가산정"
            elif "일정" in current_major:
                topic_major = "일정관리"
            elif "원가" in current_major:
                topic_major = "원가관리"
            elif "위험" in current_major or "리스크" in current_major:
                topic_major = "위험관리"
            elif "품질" in current_major:
                topic_major = "품질관리"
            elif "조달" in current_major:
                topic_major = "조달관리"
            elif "이해관계" in current_major or "의사소통" in current_major:
                topic_major = "이해관계자관리"

        # 약어(Abbreviation) 추출 시도
        # 예: "정보기술아키텍처(ITA)" 또는 "ITA( 정합성 )" 등
        abbr = None
        term_ko = term_name
        
        # 괄호 안의 영문 대문자 약어 검색
        m_abbr = re.search(r'([가-힣a-zA-Z0-9\s]+)\(([A-Z0-9\-]+)\)', term_name)
        if m_abbr:
            term_ko = m_abbr.group(1).strip()
            abbr = m_abbr.group(2).strip()
        else:
            # 괄호 밖이 약어, 안이 한글인 경우
            m_abbr_alt = re.search(r'^([A-Z0-9\-]+)\s*\(([가-힣\s]+)\)', term_name)
            if m_abbr_alt:
                abbr = m_abbr_alt.group(1).strip()
                term_ko = m_abbr_alt.group(2).strip()

        terms.append({
            "term_ko": term_ko,
            "term_en": None,
            "abbreviation": abbr,
            "definition": val_e.strip(),
            "subject": subj,
            "topic_major": topic_major,
            "topic_minor": current_major[:20],
            "source": f"감리 서브노트 Row {r_idx}"
        })
        
    print(f"  → 서브노트에서 {len(terms)}개 단어 추출 완료")
    return terms


def extract_from_memonote():
    """
    암기노트.xlsx 파일에서 단어를 추출합니다.
    주로 보안(SC) 및 일부 네트워크 인프라(SA) 과목에 해당하는 내용입니다.
    """
    print(f"\n[2/4] '{os.path.basename(EXCEL_MEMONOTE_PATH)}' 분석 시작...")
    rows = read_xlsx_sheet(EXCEL_MEMONOTE_PATH, sheet_index=1)
    if not rows:
        return []

    terms = []
    
    for r_idx, cols in rows:
        # A열 데이터 분석
        val_a = cols.get('A', '').strip()
        val_f = cols.get('F', '').strip() # 가끔 F열에도 데이터가 있음
        
        for raw_txt in [val_a, val_f]:
            if not raw_txt or len(raw_txt) < 5 or ":" not in raw_txt:
                continue
                
            parts = raw_txt.split(":", 1)
            term_part = parts[0].strip()
            def_part = parts[1].strip()
            
            if not term_part or not def_part or len(def_part) < 4:
                continue
                
            # 용어명 정제
            term_ko = term_part
            abbr = None
            
            # 한글(영문약어) 구조 파싱
            m_abbr = re.search(r'([가-힣\s]+)\(([A-Za-z0-9\-]+)\)', term_part)
            if m_abbr:
                term_ko = m_abbr.group(1).strip()
                abbr = m_abbr.group(2).strip()
            else:
                # 영문(한글) 구조 파싱
                m_abbr_alt = re.search(r'^([A-Za-z0-9\-]+)\(([가-힣\s]+)\)', term_part)
                if m_abbr_alt:
                    abbr = m_abbr_alt.group(1).strip()
                    term_ko = m_abbr_alt.group(2).strip()
                elif term_part.isupper() and len(term_part) <= 10:
                    abbr = term_part
            
            # 과목 판별 (네트워크 성격은 SA, 보안 성격은 SC)
            subj = "SC" # 기본 보안
            topic_major = "공통 보안 기술"
            
            sa_keywords = ["arp", "dns", "vpn", "ipsec", "ssl", "tls", "l2", "l3", "l4", "l7", "스위치", "프로토콜", "무선", "wep", "wpa", "ap"]
            for kw in sa_keywords:
                if kw in term_part.lower() or kw in def_part.lower():
                    subj = "SA"
                    topic_major = "데이터 통신 및 네트워크 설계"
                    break
                    
            if subj == "SC":
                if "법" in term_part or "개인정보" in term_part or "isms" in term_part or "iso" in term_part:
                    topic_major = "정보보호 법규 및 개인정보보호"
                elif "시큐어" in term_part or "코딩" in term_part or "웹" in term_part or "inject" in term_part or "xss" in term_part:
                    topic_major = "개발 및 운영 보안"
                elif "침해" in term_part or "ddos" in term_part or "spoof" in term_part or "공격" in term_part:
                    topic_major = "네트워크 및 시스템 보안"
            
            terms.append({
                "term_ko": term_ko,
                "term_en": None,
                "abbreviation": abbr,
                "definition": def_part,
                "subject": subj,
                "topic_major": topic_major,
                "topic_minor": "암기노트 핵심",
                "source": f"암기노트 Row {r_idx}"
            })

    print(f"  → 암기노트에서 {len(terms)}개 단어 추출 완료")
    return terms


# ==========================================
# 3. 기출문제 텍스트 스캐닝 엔진
# ==========================================

def get_questions_from_db():
    """
    Supabase PostgreSQL 또는 로컬 JSON 캐시에서 기출문제 리스트를 읽어옵니다.
    """
    # 1. Supabase PostgreSQL 시도
    try:
        import psycopg2
        import psycopg2.extras
        
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres.sqrnhkhgctfxnxwbiwxp",
            password="yj1024word^^",
            host="aws-1-ap-northeast-1.pooler.supabase.com",
            port=6543
        )
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT year, question_num, question, options, answer, explanation, subject FROM exam_questions")
        rows = cursor.fetchall()
        conn.close()
        print(f"\n  → Supabase PostgreSQL에서 기출문제 {len(rows)}건 로드 성공")
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"\n  [경고] Supabase PostgreSQL 접속 실패: {e}")
        print("  -> 로컬 'past_exams_db.json' 캐시 파일로 대체하여 복구 진행합니다.")
        
    # 2. 로컬 JSON 폴백
    if os.path.exists(PAST_EXAMS_JSON_PATH):
        try:
            with open(PAST_EXAMS_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # JSON 데이터를 통일된 리스트 포맷으로 가공
            questions = []
            for k, val in data.items():
                # 과목 구분: 문항 번호 기준
                # 1~25: PM, 26~50: SE, 51~75: DB, 76~100: SA, 101~120: SC
                num = int(val.get('num', 0))
                subj = "PM"
                if 26 <= num <= 50:
                    subj = "SE"
                elif 51 <= num <= 75:
                    subj = "DB"
                elif 76 <= num <= 100:
                    subj = "SA"
                elif 101 <= num <= 120:
                    subj = "SC"
                
                questions.append({
                    "year": val.get("year"),
                    "question_num": num,
                    "question": val.get("question", ""),
                    "options": val.get("options", []),
                    "answer": val.get("answer"),
                    "explanation": val.get("explanation", "") or "",
                    "subject": subj
                })
            print(f"  → 로컬 JSON 캐시에서 기출문제 {len(questions)}건 로드 성공")
            return questions
        except Exception as ex:
            print(f"  [오류] 로컬 캐시 파일 로드 실패: {ex}")
            
    return []


def extract_from_exam_questions(questions):
    """
    기출문제 질문과 보기, 해설을 분석하여 괄호로 표기된 약어 후보를 찾고,
    해당 약어가 나타난 해설 문장을 정의로 사용하여 단어로 추출합니다.
    """
    print(f"\n[3/4] 기출문제 지문 및 해설 정밀 스캐닝 시작...")
    if not questions:
        return []

    terms = []
    
    # 5대 과목 대분류 목록
    default_majors = {
        "PM": "통합관리",
        "SE": "요구사항분석 및 설계",
        "DB": "DB개념 및 설계",
        "SA": "아키텍처 설계 및 구축",
        "SC": "공통 보안 기술"
    }

    for q in questions:
        subj = q["subject"].upper()
        year = q["year"]
        num = q["question_num"]
        src_label = f"{year}년 {num}번 기출"
        
        # 질문, 보기, 해설 통합 텍스트
        opts_str = " ".join(q["options"]) if isinstance(q["options"], list) else str(q["options"] or "")
        full_text = f"{q['question']} {opts_str} {q['explanation'] or ''}"
        
        # 1. 한글(영문약어) 패턴 매칭: 예) 기능점수(FP), 획득가치관리(EVM)
        candidates = []
        for m in re.finditer(r'([가-힣]{2,20})\s*\(\s*([A-Za-z0-9\-]{2,15})\s*\)', full_text):
            ko = m.group(1).strip()
            abbr = m.group(2).strip()
            if abbr.isupper() and len(abbr) <= 10:
                candidates.append((ko, abbr, None))
                
        # 2. 영문약어(한글) 패턴 매칭: 예) EVM(획득가치관리), WBS(작업분할구조)
        for m in re.finditer(r'\b([A-Z0-9\-]{2,10})\s*\(\s*([가-힣]{2,20})\s*\)', full_text):
            abbr = m.group(1).strip()
            ko = m.group(2).strip()
            candidates.append((ko, abbr, None))
            
        # 3. 영문약어(영문풀네임) 패턴 매칭: 예) BCNF(Boyce-Codd Normal Form)
        for m in re.finditer(r'\b([A-Z0-9\-]{2,10})\s*\(\s*([A-Za-z0-9\-\s]{5,40})\s*\)', full_text):
            abbr = m.group(1).strip()
            en = m.group(2).strip()
            # 한글 매칭이 없으므로 지문 내에서 한글 용어 매칭을 찾아보거나, 약어 자체를 한글명으로 임시 대체
            candidates.append((abbr, abbr, en))

        # 후보 용어의 정의(definition)를 지문/해설에서 문장 단위로 발췌
        for ko, abbr, en in candidates:
            # 특수 케이스 제외
            if len(ko) < 2 or (abbr and len(abbr) < 2):
                continue
                
            # 해당 약어/단어가 포함된 문장 발췌
            target_word = abbr if abbr else ko
            definition = None
            
            # 해설(explanation)을 1순위로, 질문(question)을 2순위로 탐색
            search_pool = [q.get("explanation"), q.get("question")]
            for text in search_pool:
                if not text:
                    continue
                # 문장 경계 기준 분리
                sentences = re.split(r'[\.\?\n]', text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if target_word in sentence and len(sentence) >= 15:
                        definition = sentence
                        break
                if definition:
                    break
                    
            if not definition:
                # 마땅한 설명 문장이 없으면 질문 지문의 앞부분 60글자를 가져와 정의로 사용
                definition = q["question"][:70].strip() + "..."
                
            topic_major = default_majors.get(subj, "통합관리")
            
            terms.append({
                "term_ko": ko,
                "term_en": en,
                "abbreviation": abbr,
                "definition": definition,
                "subject": subj,
                "topic_major": topic_major,
                "topic_minor": "기출 용어",
                "source": src_label
            })
            
    print(f"  → 기출문제 스캐닝에서 {len(terms)}개 단어 후보 발굴 완료")
    return terms


# ==========================================
# 4. SQLite DB 저장 엔진
# ==========================================

def save_terms_to_db(terms_list):
    """
    [설계 의도]
    추출된 용어를 jolly_carson.db에 기계적/규칙적 중복 처리를 거쳐 안전하게 저장합니다.
    - 동일 약자 또는 한글명 존재 시 빈도수 가산 및 출처(source) 병합
    - vocab_topics에 신규 소분류 자동 매핑 및 생성
    - vocab_srs_state 복습 상태 레코드 자동 생성
    """
    print(f"\n[4/4] SQLite 데이터베이스('jolly_carson.db') 적재 시작...")
    if not os.path.exists(VOCAB_DB_PATH):
        print(f"  [오류] jolly_carson.db가 없습니다. init_vocabulary_db.py를 먼저 실행하세요.")
        return
        
    conn = sqlite3.connect(VOCAB_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    skipped = 0
    
    for term in terms_list:
        term_ko = term.get("term_ko")
        term_ko = term_ko.strip() if term_ko else ""
        
        term_en = term.get("term_en")
        term_en = term_en.strip() if term_en else None
        
        abbreviation = term.get("abbreviation")
        abbreviation = abbreviation.strip() if abbreviation else None
        
        definition = term.get("definition")
        definition = definition.strip() if definition else ""
        
        subject = term.get("subject")
        subject = subject.strip().upper() if subject else ""
        
        topic_major = term.get("topic_major")
        topic_major = topic_major.strip() if topic_major else "통합관리"
        
        topic_minor = term.get("topic_minor")
        topic_minor = topic_minor.strip() if topic_minor else "기타"
        
        source_val = term.get("source")
        source_val = source_val.strip() if source_val else ""
        
        if not term_ko or not definition or len(definition) < 5:
            skipped += 1
            continue
            
        # 1. 대분류 ID 확인 및 생성
        cursor.execute(
            "SELECT id FROM vocab_topics WHERE subject = ? AND parent_id IS NULL AND name = ?",
            (subject, topic_major)
        )
        row_major = cursor.fetchone()
        if row_major:
            major_id = row_major["id"]
        else:
            cursor.execute(
                "INSERT INTO vocab_topics (subject, name, parent_id) VALUES (?, ?, NULL)",
                (subject, topic_major)
            )
            major_id = cursor.lastrowid
            
        # 2. 소분류 ID 확인 및 생성
        topic_id = major_id
        if topic_minor:
            cursor.execute(
                "SELECT id FROM vocab_topics WHERE subject = ? AND parent_id = ? AND name = ?",
                (subject, major_id, topic_minor)
            )
            row_minor = cursor.fetchone()
            if row_minor:
                topic_id = row_minor["id"]
            else:
                cursor.execute(
                    "INSERT INTO vocab_topics (subject, name, parent_id) VALUES (?, ?, ?)",
                    (subject, topic_minor, major_id)
                )
                topic_id = cursor.lastrowid

        # 3. 중복 체크 (약자 또는 한글명 매칭)
        existing_id = None
        existing_freq = 1
        existing_source = []
        
        if abbreviation:
            cursor.execute(
                "SELECT id, frequency, source FROM vocab_terms WHERE abbreviation = ? AND subject = ?",
                (abbreviation, subject)
            )
            row = cursor.fetchone()
            if row:
                existing_id = row["id"]
                existing_freq = row["frequency"]
                try:
                    existing_source = json.loads(row["source"]) if row["source"] else []
                except:
                    existing_source = [row["source"]] if row["source"] else []
                    
        if not existing_id:
            cursor.execute(
                "SELECT id, frequency, source FROM vocab_terms WHERE term_ko = ? AND subject = ?",
                (term_ko, subject)
            )
            row = cursor.fetchone()
            if row:
                existing_id = row["id"]
                existing_freq = row["frequency"]
                try:
                    existing_source = json.loads(row["source"]) if row["source"] else []
                except:
                    existing_source = [row["source"]] if row["source"] else []

        related_kw_json = None
        
        # 4. 저장 또는 업데이트 처리
        if existing_id:
            # 기존 정보 업데이트
            new_freq = existing_freq + 1
            if source_val and source_val not in existing_source:
                existing_source.append(source_val)
            source_json = json.dumps(existing_source, ensure_ascii=False)
            
            cursor.execute("""
                UPDATE vocab_terms
                SET frequency = ?, source = ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?
            """, (new_freq, source_json, existing_id))
            updated += 1
        else:
            # 신규 삽입
            source_json = json.dumps([source_val] if source_val else [], ensure_ascii=False)
            cursor.execute("""
                INSERT INTO vocab_terms (term_ko, term_en, abbreviation, definition, subject, topic_id, frequency, related_keywords, source)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (term_ko, term_en, abbreviation, definition, subject, topic_id, related_kw_json, source_json))
            
            term_id = cursor.lastrowid
            
            # SRS 복습 카드 생성
            cursor.execute("""
                INSERT OR IGNORE INTO vocab_srs_state (term_id, ease_factor, interval_days, repetitions, next_review_at)
                VALUES (?, 2.5, 0, 0, datetime('now', 'localtime'))
            """, (term_id,))
            inserted += 1

    conn.commit()
    conn.close()
    
    print(f"  → DB 적재 완료: 신규 추가 {inserted}건, 기존 업데이트 {updated}건 (무효 스킵 {skipped}건)")
    return inserted, updated


# ==========================================
# 5. 실행 결과 통계 분석 출력
# ==========================================

def print_overall_summary():
    """SQLite 단어장 DB의 현재 구축 현황 요약을 출력합니다."""
    print("\n" + "=" * 60)
    print("  [Jolly-Carson] 전 과목 IT 단어장 구축 결과 요약")
    print("=" * 60)
    
    conn = sqlite3.connect(VOCAB_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 과목별 총 용어 수 조회
    cursor.execute("""
        SELECT subject, COUNT(*) as count 
        FROM vocab_terms 
        GROUP BY subject 
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    
    total = 0
    for r in rows:
        subj = r["subject"]
        name = SUBJECT_NAMES.get(subj, subj)
        count = r["count"]
        total += count
        
        # 과목별 약자 포함 단어 수
        cursor.execute("SELECT COUNT(*) FROM vocab_terms WHERE subject = ? AND abbreviation IS NOT NULL AND abbreviation != ''", (subj,))
        abbr_cnt = cursor.fetchone()[0]
        
        # 대분류 TOP 2
        cursor.execute("""
            SELECT p.name as major, COUNT(t.id) as cnt
            FROM vocab_terms t
            JOIN vocab_topics c ON t.topic_id = c.id
            LEFT JOIN vocab_topics p ON c.parent_id = p.id
            WHERE t.subject = ?
            GROUP BY COALESCE(p.name, c.name)
            ORDER BY cnt DESC
            LIMIT 2
        """, (subj,))
        majors = cursor.fetchall()
        major_str = ", ".join([f"{m['major']}({m['cnt']})" for m in majors])
        
        bar = "■" * min(int(count / 15), 25)
        print(f"  {name:15s} | {count:3d}개 (약어 {abbr_cnt:2d}개) {bar}")
        print(f"    - 주요 도메인: {major_str}")
        
    print("-" * 60)
    print(f"  누적 전체 용어 수: {total}개")
    print("=" * 60)
    conn.close()


def main():
    # 1. 엑셀에서 단어 추출
    subnote_terms = extract_from_subnote()
    memonote_terms = extract_from_memonote()
    
    # 2. 기출문제 텍스트 스캔
    questions = get_questions_from_db()
    exam_terms = extract_from_exam_questions(questions)
    
    # 3. 데이터 병합
    all_extracted_terms = subnote_terms + memonote_terms + exam_terms
    print(f"\n총 {len(all_extracted_terms)}개의 용어 후보군이 발굴되었습니다.")
    
    # 4. DB 저장
    save_terms_to_db(all_extracted_terms)
    
    # 5. 결과 통계
    print_overall_summary()


if __name__ == "__main__":
    main()
