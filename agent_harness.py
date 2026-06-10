# -*- coding: utf-8 -*-
"""
[에이전트 하네스(Agent Harness) 프레임워크]
- 설계 목적: AI 에이전트(LLM)가 사용자의 자연어 지시를 받아 스스로 문서를 스캔, 과목 분류, 파싱 및 최종 품질 검수(Audit)를 
  자율 조율(Tool Execution Loop)하여 처리하는 제어 인프라입니다.
- 원칙 준수: 외부 라이브러리(SDK) 설치 없이 파이썬 내장 urllib 및 json 모듈만을 활용해 구글 Gemini API와 REST 통신을 수행합니다.
- 거버넌스(보안): 주요 파일 쓰기/실행 툴 구동 전에 사용자 승인(Y/N) 훅을 배치하여 폭주 위험을 방지합니다.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

# 기존 파서의 핵심 모듈을 호출하기 위해 jolly-carson 경로를 sys.path에 추가하고 임포트합니다.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import parser

# ==========================================
# 1. 환경 설정 및 글로벌 상태 정의
# ==========================================
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 5대 과목 매핑 정보 (parser.py의 정보를 활용하되, 에이전트 가이드용으로 명시)
SUBJECTS = parser.SUBJECT_NAMES

# ==========================================
# 2. 에이전트 하네스 툴킷 (Harness Toolkit)
# 에이전트가 호출 가능한 로컬 액션(도구)들을 정의합니다.
# ==========================================

def list_uploaded_files():
    """
    [설계 의도]
    test_files 디렉토리와 data 폴더 하위에 보관된 원본 문서 목록을 스캔하여 반환합니다.
    에이전트가 어떤 문서가 존재하며 처리 가능한지 상태 파악을 돕는 필수 도구입니다.
    """
    targets = []
    # 1. test_files 스캔
    test_dir = "test_files"
    if os.path.exists(test_dir):
        for f in os.listdir(test_dir):
            if os.path.isfile(os.path.join(test_dir, f)) and f.lower().endswith(('.txt', '.docx', '.pdf')):
                targets.append({"source": "test_files", "filename": f, "path": os.path.join(test_dir, f)})
                
    # 2. data/uploaded_inputs/{subject_code} 스캔
    uploaded_dir = os.path.join("data", "uploaded_inputs")
    if os.path.exists(uploaded_dir):
        for sub in os.listdir(uploaded_dir):
            sub_path = os.path.join(uploaded_dir, sub)
            if os.path.isdir(sub_path):
                for f in os.listdir(sub_path):
                    if os.path.isfile(os.path.join(sub_path, f)):
                        targets.append({"source": f"uploaded_{sub}", "filename": f, "path": os.path.join(sub_path, f)})
                        
    return {"status": "success", "files": targets}

def load_exam_scope_details(subject_code):
    """
    [설계 의도]
    data/exam_scopes/ 디렉토리 하위에 과목별 상세 시험 범위 파일(예: PM.txt)이 
    존재하는지 탐색하여, 존재하는 경우 AI 분류기의 학습용 컨텍스트 보강을 위해 내용을 읽어옵니다.
    """
    scope_path = os.path.join("data", "exam_scopes", f"{subject_code}.txt")
    if os.path.exists(scope_path):
        try:
            with open(scope_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            print(f"[경고] 시험 범위 파일 {subject_code}.txt 로드 실패: {e}")
    return ""

def classify_subject_by_llm(filename):
    """
    [설계 의도]
    문서의 첫 부분 1,500자를 읽은 뒤 AI 에이전트 서브 루프를 호출하여
    해당 문서가 5대 과목(PM, SE, DB, SA, SC) 중 어느 과목에 해당하는지 판별합니다.
    - data/exam_scopes/ 내에 저장된 상세 시험 범위 텍스트가 있을 경우 이를 AI 컨텍스트에 
      RAG 형태로 동적 융합하여 분류 성능을 고도화했습니다.
    - 사용자가 직접 수동으로 분류 번호를 정해야 하던 번거로움을 자동화합니다.
    """
    # 1. 파일 찾기
    file_path = None
    # test_files 확인
    if os.path.exists(os.path.join("test_files", filename)):
        file_path = os.path.join("test_files", filename)
    else:
        # uploaded_inputs에서 탐색
        uploaded_dir = os.path.join("data", "uploaded_inputs")
        if os.path.exists(uploaded_dir):
            for sub in os.listdir(uploaded_dir):
                candidate = os.path.join(uploaded_dir, sub, filename)
                if os.path.exists(candidate):
                    file_path = candidate
                    break
                    
    if not file_path:
        return {"status": "error", "message": f"파일을 찾을 수 없습니다: {filename}"}

    # 2. 파일 서두 텍스트 추출 (인코딩 우회 적용)
    snippet = ""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".txt":
            snippet = parser.extract_txt(file_path)[:1500]
        elif ext == ".docx":
            snippet = parser.extract_docx(file_path)[:1500]
        elif ext == ".pdf":
            # PDF는 설치 상황에 따라 텍스트 추출
            snippet = parser.extract_pdf(file_path)[:1500]
        else:
            return {"status": "error", "message": "지원하지 않는 확장자입니다."}
    except Exception as e:
        return {"status": "error", "message": f"파일 프리뷰 읽기 실패: {str(e)}"}

    # 3. 만약 API 키가 설정되어 있다면 LLM을 통한 정확한 분류 수행
    if GEMINI_API_KEY:
        # 각 과목별 상세 범위 로딩 및 프롬프트 결합
        scopes_content = []
        for code in SUBJECTS.keys():
            detail = load_exam_scope_details(code)
            if detail:
                scopes_content.append(f"[{code} - {SUBJECTS[code]} 상세 시험 범위]\n{detail}")
            else:
                # 상세 파일이 없을 경우 기본 키워드 정의 제공
                basic_defs = {
                    "PM": "프로젝트 관리, 감리 및 사업관리, 일정/품질/원가 관리",
                    "SE": "소프트웨어 공학, 요구사항 분석, 디자인 패턴, 소스코드 관리, 애자일",
                    "DB": "데이터베이스, SQL, 모델링, 튜닝, 정규화",
                    "SA": "시스템 구조, 서버 아키텍처, 네트워크, 하드웨어, 클라우드",
                    "SC": "보안, 정보보호, 암호학, 취약점 점검, 개인정보보호"
                }
                scopes_content.append(f"[{code} - {SUBJECTS[code]}]\n{basic_defs.get(code, '')}")
                
        scopes_str = "\n\n".join(scopes_content)

        prompt = f"""
다음은 수집된 문서의 첫 부분 텍스트입니다. 이 내용을 분석하여 아래의 5대 IT 시험 과목 중 가장 관련이 깊은 하나를 선택하세요.
반드시 과목 코드 두 글자(PM, SE, DB, SA, SC)로만 답변하세요. 애매하더라도 가장 가능성 높은 하나를 골라야 합니다.

[시험 과목 상세 정의 및 범위]
{scopes_str}

[문서 내용 서두]
{snippet}

답변 과목 코드:"""
        try:
            res_text = call_gemini_raw_prompt(prompt)
            subject_code = res_text.strip().upper()
            # 안전장치: 응답값 필터링
            for code in SUBJECTS.keys():
                if code in subject_code:
                    return {"status": "success", "subject_code": code, "subject_name": SUBJECTS[code], "method": "llm_agent"}
        except Exception as e:
            print(f"[경고] LLM 분류기 호출 실패 ({e}). 키워드 규칙 기반 매칭으로 대체합니다.")

    # 4. API가 없거나 에러 시 규칙 기반 폴백 매칭 (키워드 스캔)
    text_lower = snippet.lower()
    keywords = {
        "PM": ["감리", "사업관리", "프로젝트", "품질", "일정", "공정", "pm", "wbs", "계약", "법령", "예규", "대가산정", "고시", "지침", "가이드", "전자정부법", "소프트웨어 진흥법", "지능정보화", "의결", "조직관리"],
        "SE": ["소프트웨어", "디자인 패턴", "요구사항", "테스트", "설계", "객체지향", "se", "구현", "모듈", "클래스", "메소드", "애자일", "형상관리"],
        "DB": ["데이터베이스", "db", "sql", "테이블", "정규화", "모델링", "인덱스", "트랜잭션", "쿼리", "schema", "속성", "릴레이션"],
        "SA": ["시스템", "네트워크", "아키텍처", "서버", "클라우드", "하드웨어", "sa", "인프라", "프로토콜", "라우터", "운영체제", "os"],
        "SC": ["보안", "보호", "암호", "취약점", "해킹", "인증", "sc", "security", "방화벽", "백신", "개인정보", "접근 통제"]
    }
    
    match_scores = {k: 0 for k in keywords.keys()}
    for code, kw_list in keywords.items():
        for kw in kw_list:
            match_scores[code] += text_lower.count(kw)
            
    best_code = max(match_scores, key=match_scores.get)
    if match_scores[best_code] > 0:
        return {"status": "success", "subject_code": best_code, "subject_name": SUBJECTS[best_code], "method": "heuristic_fallback"}
    
    # 기본값은 소프트웨어공학(SE)으로 처리
    return {"status": "success", "subject_code": "SE", "subject_name": SUBJECTS["SE"], "method": "default_fallback"}

def parse_file_to_markdown_tool(filename, subject_code):
    """
    [설계 의도]
    에이전트가 특정 파일의 파싱 실행을 결정하면, 기존 parser.py의 파이프라인을 구동시킵니다.
    백업 폴더(data/uploaded_inputs)로 안전하게 복사한 뒤 마크다운 변환을 시도합니다.
    """
    if subject_code not in SUBJECTS:
        return {"status": "error", "message": f"올바르지 않은 과목 코드입니다: {subject_code}"}

    # 1. 파일 원본 찾기
    src_path = None
    if os.path.exists(os.path.join("test_files", filename)):
        src_path = os.path.join("test_files", filename)
    else:
        # 이미 uploaded_inputs 폴더에 존재하는지 검사
        uploaded_dir = os.path.join("data", "uploaded_inputs", subject_code)
        if os.path.exists(os.path.join(uploaded_dir, filename)):
            src_path = os.path.join(uploaded_dir, filename)

    if not src_path:
        return {"status": "error", "message": f"파싱할 원본 파일을 찾을 수 없습니다: {filename}"}

    # 2. 백업 목적지 생성 및 복사
    dest_dir = os.path.join("data", "uploaded_inputs", subject_code)
    os.makedirs(dest_dir, exist_ok=True)
    dest_file_path = os.path.join(dest_dir, filename)
    
    try:
        if os.path.abspath(src_path) != os.path.abspath(dest_file_path):
            import shutil
            shutil.copy2(src_path, dest_file_path)
    except Exception as e:
        return {"status": "error", "message": f"파일 복사 보관 실패: {str(e)}"}

    # 3. 파싱 구동
    filename_without_ext = os.path.splitext(filename)[0]
    dest_md_path = os.path.join("extracted", subject_code, f"{filename_without_ext}.md")
    
    try:
        parser.parse_file_to_markdown(dest_file_path, dest_md_path)
        # 상태 업데이트 (캐시 동기화)
        status_cache = parser.load_status_json()
        if subject_code not in status_cache:
            status_cache[subject_code] = {}
            
        status_cache[subject_code][filename] = {
            "mtime": os.path.getmtime(dest_file_path),
            "size": os.path.getsize(dest_file_path),
            "status": "success",
            "extracted_path": dest_md_path,
            "parsed_at": datetime.now().isoformat()
        }
        parser.save_status_json(status_cache)
        
        return {
            "status": "success", 
            "message": "마크다운 정제 저장 완료", 
            "output_path": dest_md_path
        }
    except Exception as e:
        return {"status": "error", "message": f"마크다운 파싱 변환 실패: {str(e)}"}

def audit_markdown(filename, subject_code):
    """
    [설계 의도]
    변환된 마크다운을 에이전트가 직접 최종 검수(Audit)하여 표 구조 누락이나 
    텍스트 한글 인코딩 불량이 있는지 평가하고, 오류 검수 보고서를 작성하는 고급 품질 보증 기능입니다.
    """
    filename_without_ext = os.path.splitext(filename)[0]
    md_path = os.path.join("extracted", subject_code, f"{filename_without_ext}.md")
    
    if not os.path.exists(md_path):
        return {"status": "error", "message": f"감사 대상 마크다운 파일이 존재하지 않습니다: {md_path}"}
        
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"status": "error", "message": f"마크다운 파일 읽기 실패: {str(e)}"}

    # 검수 기준 분석
    checks = {
        "is_empty": len(content.strip()) == 0,
        "contains_table_syntax": "|" in content and "---" in content,
        "contains_encoding_error": "" in content or "" in content,
        "char_count": len(content)
    }
    
    report = []
    report.append(f"=== [AI 에이전트 파싱 감사 보고서] {filename} ===")
    report.append(f"검수 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"과목 분류: {SUBJECTS.get(subject_code)} ({subject_code})")
    report.append(f"총 글자수: {checks['char_count']}자")
    report.append("-" * 45)
    
    error_found = False
    if checks["is_empty"]:
        report.append("[심각] 파싱된 텍스트가 전혀 없습니다. 파일이 손상되었거나 추출에 실패한 것으로 보입니다.")
        error_found = True
    if checks["contains_encoding_error"]:
        report.append("[경고] 한글 디코딩 깨짐( 문자)이 감지되었습니다. 원본 텍스트의 인코딩 재점검이 필요합니다.")
        error_found = True
    if not checks["contains_table_syntax"] and (".docx" in filename.lower() or ".pdf" in filename.lower()):
        report.append("[안내] 본문에 마크다운 표가 확인되지 않았습니다. 원본에 표가 없는 문서인지 더블체크를 권장합니다.")
        
    if not error_found:
        report.append("[성공] 파싱 상태가 양호합니다. 한글 인코딩 및 마크다운 정제 상태에 이상이 없습니다.")
        
    report_content = "\n".join(report)
    
    # 보고서 파일 저장
    report_dir = os.path.join("data", "audit_reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"audit_{filename_without_ext}.txt")
    
    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write(report_content)
        
    return {
        "status": "success", 
        "checks": checks, 
        "report_summary": report_content, 
        "report_path": report_path
    }

# ==========================================
# 3. 에이전트 거버넌스 (Governance) 훅
# 툴 사용 전 보안 및 무단 실행 방지를 위한 안전벨트 장치
# ==========================================
def approve_tool_execution(tool_name, arguments):
    """
    [설계 의도]
    에이전트가 로컬 파일 변경이나 파싱 실행 등 쓰기(Write) 작업을 자율 실행하기 직전에 
    사용자에게 동적으로 승인(Governance)을 요청하는 훅입니다.
    """
    # 안전한 읽기 전용 도구는 승인 확인 생략 (자동 승인)
    if tool_name in ["list_uploaded_files"]:
        return True
        
    print(f"\n[보안 - 에이전트 거버넌스 승인 요청]")
    print(f"  * 실행하려는 도구: {tool_name}")
    print(f"  * 전달인자(Arguments): {json.dumps(arguments, ensure_ascii=False)}")
    
    try:
        choice = input(">> AI의 도구 실행을 승인하시겠습니까? (Y/n): ").strip().lower()
        if choice in ["", "y", "yes", "예"]:
            print("  -> 실행 승인됨.")
            return True
        else:
            print("  -> 실행 거부됨. 에이전트 루프가 차단됩니다.")
            return False
    except (KeyboardInterrupt, EOFError):
        print("\n  -> 실행 차단됨.")
        return False

# ==========================================
# 4. 외부 LLM API 통신부 (Gemini Connection)
# 내장 urllib.request 모듈을 최우선으로 사용하여 Gemini API 호출을 처리합니다.
# ==========================================
def call_gemini_raw_prompt(prompt):
    """간단한 텍스트 프롬프트를 전송해 문자열 답변을 받아옵니다."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]

def call_gemini_agent_loop(messages):
    """
    툴 명세서와 대화 이력을 포함하여 Gemini API에 요청을 보내고 
    모델의 응답(텍스트 답변 또는 툴 호출 요청)을 받아옵니다.
    """
    tools_declaration = {
        "functionDeclarations": [
            {
                "name": "list_uploaded_files",
                "description": "서버에 적재되어 있는 분석 대상 원본 파일들의 목록을 스캔하여 가져옵니다. 인자가 필요 없습니다."
            },
            {
                "name": "classify_subject_by_llm",
                "description": "파일명에 해당하는 문서 파일의 상단 내용을 분석해 5대 과목 코드(PM, SE, DB, SA, SC) 중 하나로 자동 분류합니다.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "filename": {"type": "STRING", "description": "분류할 대상 파일 명칭 (예: exam.docx)"}
                    },
                    "required": ["filename"]
                }
            },
            {
                "name": "parse_file_to_markdown_tool",
                "description": "대상 원본 문서를 파싱하여 정제된 마크다운 문서로 변환하고 캐시를 업데이트합니다.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "filename": {"type": "STRING", "description": "마크다운으로 변환할 대상 원본 파일명"},
                        "subject_code": {"type": "STRING", "description": "과목 코드 (PM, SE, DB, SA, SC)"}
                    },
                    "required": ["filename", "subject_code"]
                }
            },
            {
                "name": "audit_markdown",
                "description": "추출 변환이 끝난 마크다운 텍스트 품질을 진단하고 오타나 표 깨짐 등의 리포트를 작성합니다.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "filename": {"type": "STRING", "description": "감증할 대상 원본 파일명"},
                        "subject_code": {"type": "STRING", "description": "해당 과목 코드 (PM, SE, DB, SA, SC)"}
                    },
                    "required": ["filename", "subject_code"]
                }
            }
        ]
    }

    payload = {
        "contents": messages,
        "systemInstruction": {
            "parts": [{
                "text": (
                    "당신은 jolly-carson 문서 파이프라인 프로젝트를 제어하는 'AI 에이전트 하네스 코어'입니다.\n"
                    "사용자가 자연어로 요청하는 다양한 문서 파싱, 스캔, 분류, 품질 검사 작업을 대행합니다.\n"
                    "당신은 직접 문서를 수정할 수 없으며, 제공된 로컬 도구(Tools)들을 순서대로 조합 호출(Tool Call)하여 최종 목적을 완수해야 합니다.\n"
                    "반드시 제공된 도구 명세에 일치하는 도구만을 호출하십시오.\n"
                    "모든 대화 및 보고서는 친절한 한국어로 작성하십시오."
                )
            }]
        },
        "tools": [tools_declaration]
    }

    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))

# ==========================================
# 5. 오프라인 Mock 에이전트 루프 (Mock Engine)
# API 키가 없어도 사용자가 흐름을 충분히 테스트해 볼 수 있도록 설계한 대체 폴백 엔진입니다.
# ==========================================
def run_mock_agent(user_input):
    """
    [설계 의도]
    오프라인 상태이거나 API 키가 유실된 사용자 환경에서도 에이전트의 '도구 지스크/실행/보안 거버넌스' 
    흐름을 경험할 수 있도록 정규식 기반으로 툴 구동 루프를 시뮬레이션하는 복원력 도구입니다.
    영문 키워드(parse, list, audit 등)도 지원하여 윈도우 등 한글 인코딩이 깨지는 환경에서도 
    안정적으로 제어 테스트가 가능하도록 설계했습니다.
    """
    user_input_clean = user_input.lower()
    
    print("\n[안내] API 키가 탐지되지 않아 오프라인 Mock 에이전트 모드로 전환하여 시뮬레이션을 돌립니다.")
    
    # 1. 파일 목록 보기 명령 감지
    if any(k in user_input_clean for k in ["목록", "파일", "list", "ls"]):
        if approve_tool_execution("list_uploaded_files", {}):
            res = list_uploaded_files()
            print(f"\n[AI 에이전트 답변]\n대상 디렉토리를 스캔한 결과 아래 파일들을 찾았습니다:\n{json.dumps(res['files'], indent=2, ensure_ascii=False)}")
            
    # 2. 파싱 및 분류 명령 감지
    elif any(k in user_input_clean for k in ["파싱", "변환", "분류", "parse", "convert", "classify"]):
        # 가상의 파일명 추출 및 과목 추출 (더미)
        filename = "test_subj_SE.docx"
        if "pm" in user_input_clean or "txt" in user_input_clean:
            filename = "test_subj_PM.txt"
            
        print(f"\n* 에이전트 자율 판단: '{filename}' 분석을 위해 먼저 [과목 분류] 및 [파싱]을 계획합니다.")
        
        # 과목 분류 실행
        if approve_tool_execution("classify_subject_by_llm", {"filename": filename}):
            class_res = classify_subject_by_llm(filename)
            code = class_res["subject_code"]
            print(f"-> 자동 분류 결과: {class_res['subject_name']} ({code}) [방식: {class_res['method']}]")
            
            # 파싱 및 마크다운 변환 실행
            if approve_tool_execution("parse_file_to_markdown_tool", {"filename": filename, "subject_code": code}):
                parse_res = parse_file_to_markdown_tool(filename, code)
                print(f"-> 파싱 결과: {parse_res['message']} -> {parse_res.get('output_path', '')}")
                
                # 감사(Audit) 실행
                if approve_tool_execution("audit_markdown", {"filename": filename, "subject_code": code}):
                    audit_res = audit_markdown(filename, code)
                    print(f"\n[AI 감사 리포트 내용]\n{audit_res['report_summary']}\n보고서 저장 경로: {audit_res['report_path']}")
    else:
        print("\n[AI 에이전트 답변] 무엇을 도와드릴까요? (예: '목록 보여줘', 'test_subj_SE.docx 파싱하고 검수해줘')")

# ==========================================
# 6. 메인 통합 컨트롤러
# ==========================================
def main():
    print("=" * 60)
    print("  [Jolly-Carson AI 에이전트 하네스(Agent Harness) 콘솔]  ")
    print("=" * 60)
    if not GEMINI_API_KEY:
        print("[주의] GEMINI_API_KEY 환경변수가 보이지 않습니다. (오프라인 시뮬레이션으로 가동)")
    else:
        print("[확인] AI 에이전트 실시간 API 연결 모드가 활성화되었습니다.")
    print("  - 도움말: '목록 보여줘', '특정 파일명 파싱해줘', '종료' 등")
    print("=" * 60)

    # 실시간 API 연동 모드용 대화 히스토리 메모리
    chat_history = []

    while True:
        try:
            user_input = input("\n[사용자 명령] >> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n프로그램을 종료합니다.")
            break
            
        if not user_input:
            continue
        if user_input.lower() in ["종료", "exit", "q", "quit"]:
            print("에이전트 하네스를 종료합니다. 감사합니다.")
            break

        # API KEY가 없으면 Mock 시뮬레이터로 가동
        if not GEMINI_API_KEY:
            run_mock_agent(user_input)
            continue

        # 실시간 API 모드 루프 가동
        chat_history.append({
            "role": "user",
            "parts": [{"text": user_input}]
        })
        
        # 툴 체인 자율 구동 루프
        loop_count = 0
        max_loops = 5
        
        while loop_count < max_loops:
            loop_count += 1
            print("  AI 에이전트가 생각 중입니다...", end="\r")
            try:
                response = call_gemini_agent_loop(chat_history)
            except urllib.error.HTTPError as he:
                print(f"\n[API 오류] HTTP {he.code}: {he.reason}")
                print("  - API 호출 요율 초과 또는 만료된 키일 수 있습니다. 오프라인 모드로 폴백 실행합니다.")
                run_mock_agent(user_input)
                break
            except Exception as e:
                print(f"\n[네트워크 오류] API 호출 중 예기치 않은 예외 발생: {e}")
                print("  - 오프라인 모드로 폴백하여 시뮬레이션을 수행합니다.")
                run_mock_agent(user_input)
                break

            # 모델의 응답 분석
            candidate = response.get("candidates", [{}])[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [{}])
            
            # 1. 툴 호출이 들어온 경우 (Function Call)
            has_tool_call = False
            for part in parts:
                if "functionCall" in part:
                    has_tool_call = True
                    func_call = part["functionCall"]
                    tool_name = func_call["name"]
                    args = func_call.get("args", {})
                    
                    # 보안 거버넌스 훅 구동 (승인 확인)
                    approved = approve_tool_execution(tool_name, args)
                    
                    # 로컬 툴 맵핑 실행 및 결과 취합
                    tool_result = {"status": "denied", "message": "사용자가 도구 실행을 취소했습니다."}
                    if approved:
                        try:
                            if tool_name == "list_uploaded_files":
                                tool_result = list_uploaded_files()
                            elif tool_name == "classify_subject_by_llm":
                                tool_result = classify_subject_by_llm(args.get("filename"))
                            elif tool_name == "parse_file_to_markdown_tool":
                                tool_result = parse_file_to_markdown_tool(args.get("filename"), args.get("subject_code"))
                            elif tool_name == "audit_markdown":
                                tool_result = audit_markdown(args.get("filename"), args.get("subject_code"))
                            else:
                                tool_result = {"status": "error", "message": f"알 수 없는 도구: {tool_name}"}
                        except Exception as te:
                            tool_result = {"status": "error", "message": f"도구 실행 중 예외 발생: {str(te)}"}
                            
                    print(f"  -> 도구 [{tool_name}] 결과 상태: {tool_result.get('status')}")
                    
                    # AI에게 이 결과를 보고하기 위해 히스토리에 누적
                    # API 규격상 model의 functionCall 응답과 이에 매칭되는 functionResponse(역할 user 혹은 function)를 차례로 넣어줘야 함
                    chat_history.append(content) # model의 functionCall 파트 추가
                    
                    chat_history.append({
                        "role": "function",
                        "parts": [{
                            "functionResponse": {
                                "name": tool_name,
                                "response": tool_result
                            }
                        }]
                    })
                    break # 한 루프에 하나의 툴 순차 처리
            
            # 2. 툴 호출 없이 일반 대화 답변만 온 경우 (에이전트 루프 완료)
            if not has_tool_call:
                text_response = parts[0].get("text", "")
                print(f"\n[AI 에이전트 답변]\n{text_response}")
                # 대화 기억을 위해 히스토리에 추가
                chat_history.append(content)
                break
        else:
            print("\n[경고] 최대 에이전트 루프 횟수(5회)를 초과하여 자동 제어를 종료합니다.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n에이전트 하네스 실행이 중단되었습니다.")
        sys.exit(0)
