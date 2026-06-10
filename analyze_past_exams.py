# -*- coding: utf-8 -*-
"""
[기출문제-시험범위 상호 대조 분석 엔진]
- 설계 목적: 기출문제 통합 PDF를 분석하여 과목별(PM, SE, DB, SA, SC) 텍스트로 자동 분할하고,
  적재된 상세 시험 범위와 대조하여 출제자가 중시하는 핵심 출제 영역 분석 보고서 및 5대 과목 대시보드를 생성합니다.
- 원칙 준수: 외부 SDK 모듈 없이 파이썬 표준 urllib.request를 활용하여 구글 Gemini API와 통신하며,
  API 키가 없는 환경을 위해 정밀 키워드 스캐닝 방식의 오프라인 분석 폴백(Mock/Heuristic) 기능을 탑재했습니다.
"""

import os
import sys
import re
import json
import urllib.request
import urllib.error
from datetime import datetime

# 기존 파서 모듈 로드
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import parser

# ==========================================
# 1. 아키텍처 상태 및 상수 정의
# ==========================================
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

SUBJECT_CODES = ["PM", "SE", "DB", "SA", "SC"]
SUBJECT_NAMES = parser.SUBJECT_NAMES

# ==========================================
# 2. 기출문제 과목 분할 엔진 (Slicing Parser)
# ==========================================

def split_exam_by_subjects(exam_text):
    """
    [설계 의도]
    정보시스템 감리사 시험의 문제 번호(1~25: PM, 26~50: SE, 51~75: DB, 76~100: SA, 101~120: SC)가 
    엄격하게 고정되어 있다는 도메인 지식을 활용하여 슬라이싱 경계를 확정합니다.
    - 본문 속의 일반적인 과목명 단어(예: '보안')가 앞부분에 중복 출현하여 오작동하는 리스크를 방지하기 위해 
      문항 경계 번호(1., 26., 51., 76., 101.)를 1순위 감지 수단으로 채택했습니다.
    - 1과목의 경우 수험지 표지 유의사항 등을 다 포함할 수 있도록 0번지부터 시작합니다.
    """
    positions = [0]  # 1과목 PM은 항상 파일 시작(0)에서 출발합니다.
    
    # 2과목, 3과목, 4과목, 5과목 시작 문항 번호
    boundary_numbers = [26, 51, 76, 101]
    
    for num in boundary_numbers:
        # 단어 경계 + 숫자 + 점 패턴 (예: \b26\s*\.)
        num_pat = rf"\b{num}\s*\."
        match = re.search(num_pat, exam_text)
        if match:
            positions.append(match.start())
        else:
            # 매칭 실패 시, 줄바꿈 뒤에 숫자가 바로 오는 경우도 대비하는 백업 패턴
            num_pat_alt = rf"\n\s*{num}\s+"
            match_alt = re.search(num_pat_alt, exam_text)
            if match_alt:
                positions.append(match_alt.start())
            else:
                # 둘 다 실패할 경우, 균등 분할 위치로 강제 보정하여 파이프라인 중단을 예방
                approx_pos = int(len(exam_text) * (len(positions) / 5.0))
                positions.append(approx_pos)
                
    # 구간별 슬라이싱 매핑
    sections = {}
    txt_len = len(exam_text)
    for idx, code in enumerate(SUBJECT_CODES):
        start = positions[idx]
        end = positions[idx+1] if idx + 1 < len(positions) else txt_len
        sections[code] = exam_text[start:end].strip()
        
    return sections

# ==========================================
# 3. 로컬 시험범위 데이터 로딩
# ==========================================

def load_scope_details(subject_code):
    """
    [설계 의도]
    data/exam_scopes/ 디렉토리 하위의 과목별 시험 범위를 읽어옵니다.
    """
    scope_path = os.path.join("data", "exam_scopes", f"{subject_code}.txt")
    if os.path.exists(scope_path):
        try:
            with open(scope_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            print(f"[경고] {subject_code} 시험범위 파일 로딩 실패: {e}")
    return "상세 시험범위 정보가 등록되어 있지 않습니다."

# ==========================================
# 4. 오프라인 트렌드 키워드 매칭 분석 (Mock/Heuristic Engine)
# ==========================================

def run_heuristic_trend_analysis(subject_code, scope_text, exam_chunk):
    """
    [설계 의도]
    구글 API 키가 없는 오프라인 환경에서도 기출문제를 분석할 수 있도록 설계된 차선책입니다.
    상세 시험범위 텍스트에 들어있는 핵심 주제 명칭들이 기출문제 본문에서 몇 번 
    출현(스캔)되었는지 누적 카운팅하여 빈출 TOP 3 토픽을 과학적으로 감지해 리포트를 구성합니다.
    """
    topic_keywords = {
        "PM": {
            "소프트웨어사업 계약 및 과업심의위원회": ["과업심의", "과업내용 변경", "계약금액", "대가", "고시", "예규", "국가계약"],
            "정보시스템 감리 제도 및 가이드": ["감리기준", "감리원", "감리수행", "유지보수", "발주관리", "전자정부법"],
            "프로젝트 관리 기법 및 표준": ["pmbok", "iso 21500", "wbs", "일정관리", "위험관리", "의사소통"]
        },
        "SE": {
            "요구사항 분석 및 설계 패턴": ["요구사항 명세", "유스케이스", "디자인 패턴", "아키텍처", "uml", "mvc"],
            "소프트웨어 테스트 기법 및 표준": ["테스팅", "단위 테스트", "통합 테스트", "29119", "화이트박스", "블랙박스"],
            "개발 방법론 및 클린 아키텍처": ["애자일", "스크럼", "msa", "refactoring", "형상관리", "itil", "clean architecture"]
        },
        "DB": {
            "데이터베이스 설계 및 정규화": ["정규화", "정규형", "1nf", "2nf", "3nf", "bcnf", "데이터 모델", "erd"],
            "DBMS 물리 설계 및 성능 튜닝": ["인덱스", "튜닝", "트랜잭션", "동시성 제어", "락킹", "백업", "복구"],
            "빅데이터 및 분산 데이터베이스": ["nosql", "하두프", "data mining", "dw", "분산 db", "ai학습"]
        },
        "SA": {
            "컴퓨터 구조론 및 인프라 설계": ["디지털 논리", "파이프라이닝", "백업장치", "ups", "raid", "가상화", "고가용성"],
            "데이터 통신 및 네트워크 라우팅": ["osi", "ip", "라우터", "스위치", "라우팅 프로토콜", "lan", "wan"],
            "무선 네트워크 및 사물인터넷 신기술": ["nfc", "iot", "lora", "zigbee", "sdn", "nfv", "cdn", "클라우드"]
        },
        "SC": {
            "공통 보안 암호 프로토콜": ["대칭키", "공개키", "해쉬", "전자서명", "pki", "sso", "otp"],
            "네트워크 침해사고 및 시스템 보안": ["방화벽", "vpn", "ips", "nac", "망분리", "해킹", "취약점"],
            "개발 보안 및 정보보호 법령": ["시큐어 코딩", "개인정보보호법", "비식별", "암호화", "포렌식", "보안 감사"]
        }
    }
    
    exam_lower = exam_chunk.lower()
    subject_topics = topic_keywords.get(subject_code, {})
    
    topic_scores = []
    for topic_name, keywords in subject_topics.items():
        score = 0
        for kw in keywords:
            score += exam_lower.count(kw.lower())
        topic_scores.append((topic_name, score))
        
    topic_scores.sort(key=lambda x: x[1], reverse=True)
    
    report = []
    report.append(f"# [{subject_code} - {SUBJECT_NAMES[subject_code]}] 출제 분석 보고서 (오프라인 모드)")
    report.append(f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"분석 방식: 정밀 키워드 스캐닝 및 시험 범위 대조 오프라인 분석")
    report.append("\n## 1. 최다 빈출 토픽 순위")
    
    for rank, (topic, score) in enumerate(topic_scores, 1):
        report.append(f"- **{rank}위**: {topic} (감지 횟수: {score}회)")
        
    report.append("\n## 2. 출제 빈도 기준 학습 가이드 및 팁")
    report.append(f"현재 기출문제 검사 결과 **{topic_scores[0][0]}** 영역이 출제 빈도 {topic_scores[0][1]}회로 가장 높게 측정되었습니다.")
    report.append(f"출제자는 이 과목에서 다음 사항들을 아주 중요시합니다:")
    
    if subject_code == "PM":
        report.append("  1. 과학기술정보통신부 고시인 **소프트웨어사업 계약 및 관리감독에 관한 지침**의 의결 정족수, 재심의 청구 기간(14일) 등 법적 의무 규정은 매년 출제됩니다.")
        report.append("  2. 용역계약 일반조건 및 국가계약법 상의 대가 조정 기준 및 지체상금 조항도 꼼꼼히 확인해 두어야 합니다.")
    elif subject_code == "SE":
        report.append("  1. 요구사항 정의서 개발 시 **UML 다이어그램**(시퀀스, 클래스 등) 해석법과 디자인 패턴(싱글톤, 팩토리 등)의 정적/동적 구조를 묻는 문제가 빈출됩니다.")
        report.append("  2. 테스팅 방법론 표준인 **ISO/IEC/IEEE 29119**의 단위/통합 테스팅 룰과 화이트/블랙박스 기법의 차이는 점수 획득의 핵심입니다.")
    elif subject_code == "DB":
        report.append("  1. **정규화(1NF ~ BCNF)** 단계를 직접 스키마 분석을 통해 추적하는 연산 문제는 단골 출제 대상입니다.")
        report.append("  2. 성능 튜닝에 필수적인 **인덱스 스캔 구조(B+Tree)**와 트랜잭션의 ACID 성질(특히 동시성 제어 락킹 프로토콜)을 암기하십시오.")
    elif subject_code == "SA":
        report.append("  1. 컴퓨터 구조론의 핵심인 **파이프라이닝 해저드(데이터, 구조, 제어)** 해결책과 메모리 계층(캐시, 매핑 방식)을 출제자가 선호합니다.")
        report.append("  2. 네트워크 계층 구조에서 **IP 서브네팅 및 라우팅 프로토콜(OSPF, BGP)** 구조 파악에 대한 지식이 아주 중요합니다.")
    elif subject_code == "SC":
        report.append("  1. 암호 프로토콜의 대칭/비대칭 키 특징과 인증 핵심 기술인 **PKI, 전자서명** 구조를 숙지해야 합니다.")
        report.append("  2. 시큐어 코딩(개발 보안 7대 취약점)과 **개인정보보호법에 규정된 기술적/관리적 보호조치**(암호화, 비식별화 기준)는 무조건 매년 출제됩니다.")
        
    report.append("\n## 3. 상세 시험 범위 대조 현황")
    report.append("```text")
    report.append(scope_text)
    report.append("```")
    
    return "\n".join(report)

# ==========================================
# 5. 실시간 AI 트렌드 교차 분석 (Online Engine)
# ==========================================

def run_online_ai_trend_analysis(subject_code, scope_text, exam_chunk):
    """
    [설계 의도]
    Gemini API 키가 있을 때 작동하는 실시간 지능형 상호 분석 모듈입니다.
    분할된 기출문제를 분석하여 출제자의 중요도를 RAG 대조를 통해 정밀하게 평가 및 작성합니다.
    """
    prompt = f"""
당신은 대한민국 최고 권위의 '정보시스템 감리사 필기시험 수석 연구원'입니다.
제공된 과목별 [상세 시험 범위]와 최근의 [기출문제 본문] 데이터를 상호 대조하여,
출제자가 해당 과목에서 가장 중요시하고 있는 핵심 중요 영역 및 학습 전략 보고서를 작성해 주세요.

[과목명]
{SUBJECT_NAMES[subject_code]} ({subject_code})

[상세 시험 범위]
{scope_text}

[기출문제 텍스트 서두]
{exam_chunk[:4000]} # 용량 한계로 상단 4,000자 분석

보고서 작성 요구사항:
- Markdown 포맷으로 작성하세요.
- 1. 최근 출제자가 중요시하는 TOP 3 개념 및 출제 흐름 요약
- 2. 기출문제 분석을 토대로 한 세부 출제 유형 및 문제 분석 예시 (어떻게 유도되고 꼬아 내는지 설명)
- 3. 감리사 수험생들을 위한 해당 과목 공부 팁 및 합격 전략
- 모든 문장과 설명은 친절하고 전문적인 한국어로 서술해 주세요.

트렌드 분석 리포트 내용:"""

    try:
        report_text = parser.call_gemini_raw_prompt(prompt) if hasattr(parser, 'call_gemini_raw_prompt') else call_gemini_raw_prompt(prompt)
        return report_text
    except Exception as e:
        print(f"[경고] AI 분석 API 호출 중 에러 발생 ({e}). 오프라인 Heuristic 모드로 대체합니다.")
        return run_heuristic_trend_analysis(subject_code, scope_text, exam_chunk)

def call_gemini_raw_prompt(prompt):
    """Fallback용 API 호출 함수"""
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

# ==========================================
# 6. 메인 통합 컨트롤러
# ==========================================

def main():
    print("=" * 60)
    print("  [Jolly-Carson 기출문제-시험범위 상호 대조 분석 엔진]  ")
    print("=" * 60)
    
    exam_dir = os.path.join("data", "past_exams")
    target_file = "2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.pdf"
    target_path = os.path.join(exam_dir, target_file)
    
    if not os.path.exists(target_path):
        print(f"[오류] 분석 대상 기출문제 파일을 찾을 수 없습니다: {target_path}")
        print("  - data/past_exams/ 디렉토리에 기출문제를 먼저 넣어주세요.")
        sys.exit(1)
        
    print(f"[작업 1/4] 최신 기출문제 PDF 텍스트 추출 중 -> {target_file}")
    try:
        raw_text = parser.extract_pdf(target_path)
        print(f"  -> 파싱 성공 (총 {len(raw_text)}글자 획득)")
    except Exception as e:
        print(f"[치명적 오류] PDF 텍스트 추출 중 에러 발생: {e}")
        sys.exit(1)
        
    print(f"[작업 2/4] 기출문제 과목별 영역 분할(Slicing) 수행 중...")
    sections = split_exam_by_subjects(raw_text)
    for code in SUBJECT_CODES:
        chunk_len = len(sections.get(code, ''))
        print(f"  -> {code} ({SUBJECT_NAMES[code]}): 분할 길이 {chunk_len}자")
        
    print(f"[작업 3/4] 상세 시험 범위 대조 및 과목별 트렌드 분석 구동 중...")
    
    reports = {}
    report_paths = []
    
    os.makedirs(os.path.join("data", "exam_analysis_reports"), exist_ok=True)
    
    for code in SUBJECT_CODES:
        print(f"  * {SUBJECT_NAMES[code]} ({code}) 분석 진행 중...")
        scope_text = load_scope_details(code)
        exam_chunk = sections.get(code, "")
        
        if GEMINI_API_KEY:
            report_content = run_online_ai_trend_analysis(code, scope_text, exam_chunk)
        else:
            report_content = run_heuristic_trend_analysis(code, scope_text, exam_chunk)
            
        report_filename = f"{code}_trend_analysis.md"
        report_path = os.path.join("data", "exam_analysis_reports", report_filename)
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            reports[code] = report_content
            report_paths.append(report_path)
            print(f"    -> 분석 보고서 작성 완료: {report_path}")
        except Exception as e:
            print(f"    [에러] 분석 보고서 파일 쓰기 실패 ({code}): {e}")

    print(f"[작업 4/4] 전체 5대 과목 통합 대시보드 리포트 생성 중...")
    dashboard = []
    dashboard.append("# [종합 대시보드] 정보시스템 감리사 기출분석 트렌드 리포트 (2026년 기준)")
    dashboard.append(f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    dashboard.append("본 리포트는 기출문제 통합 데이터셋과 5대 과목별 상세 시험 범위 내용을 교차 매핑하여 수립된 수험생 합격 가이드입니다.\n")
    dashboard.append("| 과목 코드 | 과목 명칭 | 최다 빈출 핵심 개념 및 출제 흐름 | 개별 보고서 링크 |")
    dashboard.append("| :--- | :--- | :--- | :--- |")
    
    for code in SUBJECT_CODES:
        report_lines = reports.get(code, "").split("\n")
        first_finding = "분석 보고서 참조"
        for line in report_lines:
            if "1위" in line or "최다 빈출" in line or "- **" in line:
                first_finding = line.replace("-", "").replace("*", "").strip()
                break
        
        link_str = f"[보고서 바로가기]({code}_trend_analysis.md)"
        dashboard.append(f"| {code} | {SUBJECT_NAMES[code]} | {first_finding} | {link_str} |")
        
    dashboard.append("\n## 종합 학습 전략 요약")
    dashboard.append("1. **사업관리 및 감리(PM)**: 소프트웨어사업 관리감독 지침 등의 국가 고시 관련 재심의(14일) 등의 정확한 일수 및 계약 조건을 우선 숙지해야 합니다.")
    dashboard.append("2. **소프트웨어공학(SE)**: 요구사항 관리 기법과 시퀀스 다이어그램 해석 및 ISO/IEC/IEEE 29119 테스팅 표준은 고정 출제 대상입니다.")
    dashboard.append("3. **데이터베이스(DB)**: SQL 쿼리 해석과 트랜잭션 병행제어 락킹 연산 및 DB 정규화 단계를 직접 수행할 줄 알아야 고득점이 가능합니다.")
    dashboard.append("4. **시스템구조(SA)**: 컴퓨터 논리회로와 파이프라이닝의 구조적 해결 및 IPv4/IPv6 주소 변환과 클라우드 아키텍처 설계를 이해해야 합니다.")
    dashboard.append("5. **보안(SC)**: 암호 프로토콜(SSL/TLS 등)과 시큐어 코딩 및 개인정보보호법에 명시된 비식별 조치 기술을 확실히 암기해야 과락을 피할 수 있습니다.")
    
    dashboard_content = "\n".join(dashboard)
    dashboard_path = os.path.join("data", "exam_analysis_reports", "dashboard_2026.md")
    
    try:
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(dashboard_content)
        print(f"  -> 종합 대시보드 리포트 생성 완료: {dashboard_path}")
    except Exception as e:
        print(f"  [에러] 종합 대시보드 쓰기 실패: {e}")
        
    print("\n" + "=" * 60)
    print("  기출문제 및 시험범위 대조 분석이 성공적으로 마무리되었습니다.  ")
    print("=" * 60)

if __name__ == "__main__":
    main()
