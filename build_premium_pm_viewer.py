# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

"""
[초프리미엄 감리 및 사업관리(PM) 기출문제 뷰어 자동 빌더]
- 목적: 2015년~2026년 기출 PDF에서 PM 과목 전체 문항(1~25번)을 추출하고,
  24대 세부 토픽 사전을 기반으로 정형화된 빈출 분석 대시보드 웹앱(pm_frequent_concepts.html)을 생성합니다.
- 동작 원리:
  1. PDF 텍스트를 페이지별 4단 또는 2단 레이아웃을 보정하여 깔끔하게 병합합니다.
  2. 기출문제 1번~25번 문항 영역을 감지하고 PyMuPDF(fitz)를 이용해 고해상도로 자동 크롭하여 이미지로 저장합니다.
  3. 키워드 매칭 분석을 통해 3회 이상 출제된 핵심 개념을 추출하고, 각 개념별 메타데이터(출제 범위, 핵심 개념, 특징)와 매핑합니다.
  4. 웹앱 템플릿 내에 데이터를 인젝션하고 Flask 백엔드 API(/api/pm/memos) 연동 로직을 심어 HTML을 최종 빌드합니다.
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

# Windows 콘솔 환경 한글 깨짐 방지
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 기출문제 PDF 경로 정의
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

# PM 24대 세부 개념 키워드 정의
CONCEPT_KEYWORDS = {
    "소프트웨어 진흥법": ["소프트웨어 진흥법", "소프트웨어진흥법", "sw진흥법", "소프트웨어 진흥"],
    "전자정부법 및 의무감리 제도": ["전자정부법", "의무감리", "의무 감리", "감리 대상", "감리대상"],
    "지능정보화 기본법": ["지능정보화 기본법", "지능정보화기본법", "지능정보화"],
    "정보시스템 감리기준 & 감리 수행 규격": ["정보시스템 감리기준", "정보시스템감리기준", "감리기준", "감리원", "감리법인", "윤리 가이드", "감리 보고서", "의견 진술서", "감리보고서"],
    "행정기관 및 공공기관 정보시스템 구축운영 지침": ["구축운영 지침", "구축운영지침", "행정기관 및 공공기관 정보시스템", "구축 운영 지침"],
    "소프트웨어사업 계약 및 관리감독 지침": ["관리감독에 관한 지침", "관리감독 지침", "과업심의", "과업 변경", "적정성 심의", "과업조정", "과업내용 변경", "과업심의위원회"],
    "공공데이터 및 데이터베이스 표준화 지침": ["공공데이터", "데이터베이스 표준화", "품질관리 지침", "공공기관의 데이터베이스", "데이터 표준화"],
    "국가계약법 및 예규 규칙": ["국가계약법", "국가를 당사자로 하는", "국가계약", "조달청", "입찰"],
    "협상에 의한 계약체결기준": ["협상에 의한 계약", "협상에 의한", "기술성 평가", "차등점수"],
    "용역계약 일반조건 및 지체상금": ["용역계약일반조건", "용역계약 일반조건", "지체상금", "계약금액 조정", "대가 조정", "물가변동"],
    "소프트웨어사업 대가산정 가이드": ["대가산정", "sw사업 대가", "엔지니어링사업대가", "대가산정 가이드", "기능점수 단가", "엔지니어링 대가"],
    "IT거버넌스 및 COBIT 프레임워크": ["it거버넌스", "cobit", "it 거버넌스", "it거버넌스", "코빗"],
    "조직 구조론 (매트릭스/기능/프로젝트 조직)": ["조직구조", "조직이론", "조직설계", "매트릭스 조직", "기능식 조직", "프로젝트 조직", "매트릭스형", "기능형 조직"],
    "동기부여 이론 (매슬로우/허즈버그/맥그리거 등)": ["인적 자원", "동기부여", "매슬로우", "허즈버그", "맥그리거", "위생 이론", "x-y이론", "동기 이론", "동기-위생", "욕구단계", "인적자원"],
    "의사소통 관리 및 소통 채널 계산": ["의사소통", "소통 관리", "의사소통 채널", "의사소통수", "채널 수"],
    "PMBOK 프로젝트 관리 10대 지식 영역": ["pmbok", "통합 관리", "범위 관리", "품질 관리", "자원 관리", "조달 관리", "이해관계자", "지식 영역", "도메인", "프로젝트 헌장"],
    "CPM 일정 관리 및 주공정(Critical Path) 분석": ["cpm", "pert", "주공정", "임계경로", "임계 경로", "여유시간", "float", "주공정법", "es", "ef", "ls", "lf", "총여유", "자유여유"],
    "EVM 획득가치 및 기성고 관리 (CPI/SPI/EAC)": ["evm", "획득가치", "기성고", "cpi", "spi", "cvr", "sv", "bac", "eac", "tcpi", "획득 가치", "일정분산", "비용분산"],
    "위험 관리 전략 및 리스크 대응 (회피/전이/완화/수용)": ["위험 관리", "리스크 식별", "정량적 위험", "정성적 위험", "위험 대응", "위험 회피", "위험 완화", "위험 전이", "위험 수용"],
    "품질 관리 도구 및 통계적 기법": ["품질 통제", "관리도", "파레토", "인과관계", "fishbone", "통계적 품질", "특성요인도", "산점도", "체크시트", "히스토그램"],
    "변경 통제 절차 및 CCB 변경통제위원회": ["변경 관리", "변경 통제", "ccb", "변경통제"],
    "소프트웨어 표준 산출물 가이드": ["cbd", "sw개발 표준 산출물", "산출물 가이드", "산출물 표준"],
    "공동계약 및 하도급 관리 규정": ["공동계약", "하도급", "공동이행", "분담이행", "하도급 계약"],
    "정보기술 아키텍처(EA) 수립 및 관리": ["정보기술 아키텍처", "ea", "enterprise architecture", "ita"]
}

# PM 24대 세부 개념 설명 메타데이터 정의
CONCEPT_METADATA = {
    "소프트웨어 진흥법": {
        "core_concept": "공공 SW사업의 대기업 참여 제한, 중소기업 참여 확대 및 상생협력 규정",
        "features": "대기업 참여 제한 예외 사업 요건(국가안보, 신기술 등)과 대기업 참여 시 상생협력 평가 비중, 하자담보책임기간 조항 등이 단골 출제 대상입니다.",
        "scope": "법/제도/지침 -> 소프트웨어 진흥법령"
    },
    "전자정부법 및 의무감리 제도": {
        "core_concept": "행정기관 등의 정보화 추진 및 국가 의무감리 대상 사업 기준 규격",
        "features": "전자정부사업 중 감리를 의무적으로 받아야 하는 대상 기준(사업비 5억 원 이상인 소프트웨어 개발 사업, 2억 원 이상 데이터베이스 구축 등)의 상세 조건을 묻습니다.",
        "scope": "감리 법제도/기술 -> 전자정부법 및 감리제도"
    },
    "지능정보화 기본법": {
        "core_concept": "지능정보기술 활성화 및 지능정보사회 규격과 기본 계획 수립",
        "features": "국가 지능정보화 기본계획(3년 주기) 수립 주체 및 지능정보기술 전문인력 양성, 역기능 방지 대책 규정의 주체(과기정통부 장관 등)를 구별하는 문제가 출제됩니다.",
        "scope": "법/제도/지침 -> 지능정보화 기본법령"
    },
    "정보시스템 감리기준 & 감리 수행 규격": {
        "core_concept": "감리수행 계획, 영역(대비/유형별), 감리원의 자격 조건 및 윤리 기준",
        "features": "감리 수행 시 적용되는 상시/정기 감리 절차, 감리 계획서 제출 기한(계약 후 15일 이내 등), 의견 진술서 처리 절차 및 감리원 배치 기준이 핵심 출제 범위입니다.",
        "scope": "감리 법제도/기술 -> 정보시스템 감리기준"
    },
    "행정기관 및 공공기관 정보시스템 구축운영 지침": {
        "core_concept": "공공 부문 정보시스템 구축 시 준수해야 하는 기술적/관리적 아키텍처 및 보안 표준",
        "features": "하드웨어/소프트웨어 기술성 평가 비중 기본값(90:10 등), 기술적용계획표 작성 의무화 및 소프트웨어 분리발주 대상(사업비 3억 이상 등) 예외 사유를 질문합니다.",
        "scope": "법/제도/지침 -> 구축운영 지침"
    },
    "소프트웨어사업 계약 및 관리감독 지침": {
        "core_concept": "과업내용의 확정 및 적정성 심의를 담당하는 과업심의위원회 규정 및 과업 변경 관리",
        "features": "과업 변경 및 조정을 위한 적정성 심의 신청 기한(14일 이내 등), 과업심의위원회 구성 요건 및 의결 정족수 등 수치 위주의 세부 규정이 매년 출제됩니다.",
        "scope": "법/제도/지침 -> 계약 및 관리감독 지침"
    },
    "공공데이터 및 데이터베이스 표준화 지침": {
        "core_concept": "공공기관이 수집/보유하는 데이터의 개방, 연동 표준화 및 품질 관리 준칙",
        "features": "공공데이터 개방 제외 사유(개인정보 등), 데이터베이스 표준화 적용 영역(메타데이터, 데이터 도메인, 표준 코드 등)의 기술 가이드 준수 여부를 다룹니다.",
        "scope": "법/제도/지침 -> 공공데이터 법령/지침"
    },
    "국가계약법 및 예규 규칙": {
        "core_concept": "국가를 당사자로 하는 계약 체결 시의 경쟁 입찰, 수의 계약 기준 및 계약 보증금 조항",
        "features": "입찰 참가 자격 제한 요건, 부정당업자 제재 효력 범위, 입찰보증금 납부 및 국고 귀속 절차에 대한 법적 규칙을 꼼꼼히 물어봅니다.",
        "scope": "법/제도/지침 -> 국가계약법령"
    },
    "협상에 의한 계약체결기준": {
        "core_concept": "기술 능력과 입찰 가격을 종합 평가하여 협상 대상자를 선정하는 낙찰 절차 규격",
        "features": "기술 평가점수 비중 배정(일반적으로 90% 이상), 협상 적격자 판정 기준(기술평가 배점의 85% 이상 획득자) 및 입찰 보증 규정을 정확히 암기해야 합니다.",
        "scope": "법/제도/지침 -> 계약 예규"
    },
    "용역계약 일반조건 및 지체상금": {
        "core_concept": "용역 수행 중의 대가 조정 기준 및 납기 지연에 따른 지체상금 부과 규칙",
        "features": "지체상금율 계산 공식 및 지연 일수 산정 기준(검수 기간 제외 등), 물가변동이나 설계변경에 따른 계약금액 조정 요건과 절차를 평가합니다.",
        "scope": "법/제도/지침 -> 계약 예규"
    },
    "소프트웨어사업 대가산정 가이드": {
        "core_concept": "SW 개발비, 유지관리비, 재개발비 산정을 위한 정밀 표준 모델",
        "features": "기능점수(FP) 기반 대가 산정 방식의 절차, 보정계수(규모, 애플리케이션 복잡도 등)의 반영법 및 투입공수(Man-Month) 방식 적용 시의 노임단가 적용 기준이 기출됩니다.",
        "scope": "법/제도/지침 -> SW 대가산정"
    },
    "IT거버넌스 및 COBIT 프레임워크": {
        "core_concept": "IT 자산과 비즈니스 목표를 정렬하는 기업 거버넌스 및 통제 모델",
        "features": "COBIT의 핵심 5대 영역 및 성숙도 수준 평가 모델의 성격, 거버넌스와 매니지먼트의 차이점 및 ITIL과의 상호 보완적 매핑 관계를 묻습니다.",
        "scope": "법/제도/지침 -> IT 거버넌스"
    },
    "조직 구조론 (매트릭스/기능/프로젝트 조직)": {
        "core_concept": "프로젝트 수행을 위한 임시/영구 조직 구조 설계 및 장단점 비교",
        "features": "기능형, 매트릭스형(강한/약한/균형), 프로젝트 전담형 조직의 자원 배정 효율성, 프로젝트 관리자의 권한 크기 및 의사소통 경로 복잡도를 주로 비교합니다.",
        "scope": "조직 관리론 -> 조직 구조"
    },
    "동기부여 이론 (매슬로우/허즈버그/맥그리거 등)": {
        "core_concept": "조직원의 생산성을 극대화하기 위한 인적자원 관리 및 동기 요인 분석",
        "features": "매슬로우의 5대 욕구 계층설, 허즈버그의 2요인 이론(동기요인과 위생요인의 격리), 맥그리거의 X-Y이론, 아담스의 공정성 이론 등의 개념 비교가 주를 이룹니다.",
        "scope": "조직 관리론 -> 인적 자원 관리"
    },
    "의사소통 관리 및 소통 채널 계산": {
        "core_concept": "프로젝트 이해관계자 간 효과적인 정보 공유 및 의사소통 통로 설계",
        "features": "이해관계자가 N명일 때 의사소통 채널 수의 계산 공식 [N * (N - 1) / 2]을 활용한 응용 계산 문제와 보고 관계 정의가 자주 출제됩니다.",
        "scope": "조직 관리론 -> 의사소통 관리"
    },
    "PMBOK 프로젝트 관리 10대 지식 영역": {
        "core_concept": "프로젝트 시작부터 종료까지 5대 프로세스 그룹(기획/실행/통제 등)과 10대 지식 체계 구성",
        "features": "프로젝트 헌장(Charter) 작성 승인 주체, 프로젝트 관리 계획서 구성 요소, 그리고 이해관계자 식별 및 기성고 분석과의 통합 관점 연계가 출제됩니다.",
        "scope": "프로젝트 관리 -> PMBOK 가이드"
    },
    "CPM 일정 관리 및 주공정(Critical Path) 분석": {
        "core_concept": "일정 지연을 방지하기 위한 최장 경로 분석 및 여유시간 연산 기법",
        "features": "네트워크 다이어그램 상에서 가장 긴 경로(주공정)를 식별하고, 각 액티비티의 총 여유(Total Float) 및 자유 여유(Free Float)를 역방향/순방향 계산법으로 도출하는 문제가 매년 출제됩니다.",
        "scope": "프로젝트 관리 -> 일정 관리"
    },
    "EVM 획득가치 및 기성고 관리 (CPI/SPI/EAC)": {
        "core_concept": "현재 시점까지의 비용 및 일정 성과를 계량화하여 미래 프로젝트 최종 비용을 예측하는 정량적 통제 기법",
        "features": "PV(계획가치), EV(획득가치), AC(실제원가)를 기준으로 일정차이(SV), 비용차이(CV), 비용수행지수(CPI), 일정수행지수(SPI) 및 완공시점예측(EAC)을 산출하는 연산이 단골 출제됩니다.",
        "scope": "프로젝트 관리 -> 원가/일정 관리"
    },
    "위험 관리 전략 및 리스크 대응 (회피/전이/완화/수용)": {
        "core_concept": "부정적 리스크의 발생 가능성과 영향을 식별하고 적절한 대응 방안을 선정하는 과정",
        "features": "회피(경로 변경), 전이(보험 가입, 외주 계약), 완화(사전 교육, 테스트 강화), 수용(예비비 편성) 등 개별 상황에 맞는 최적의 리스크 관리 수단을 연결하는 문제입니다.",
        "scope": "프로젝트 관리 -> 위험 관리"
    },
    "품질 관리 도구 및 통계적 기법": {
        "core_concept": "프로젝트 결과물의 품질 보증 및 통제를 위해 활용하는 전통적인 통계 도구",
        "features": "파레토 차트(80:20 법칙 및 빈도 분석), 원인결과도(Fishbone), 관리도(Control Chart - 공정 이상 유무 판별), 산점도(두 변수 간 상관관계)의 특징과 쓰임새를 물어봅니다.",
        "scope": "프로젝트 관리 -> 품질 관리"
    },
    "변경 통제 절차 및 CCB 변경통제위원회": {
        "core_concept": "공식 승인된 베이스라인의 모든 변경 요구를 통합 검토하고 승인 여부를 결정하는 절차",
        "features": "변경 요청서 접수 -> 영향성 평가 -> CCB 검토 및 의결 -> 변경 사항 반영 및 통지 순서의 공식 변경 통제 수명 주기가 핵심 주제입니다.",
        "scope": "프로젝트 관리 -> 통합 변경 통제"
    },
    "소프트웨어 표준 산출물 가이드": {
        "core_concept": "SW 개발 공학 방법론(CBD, 애자일 등)에 따른 공식 설계 산출물 구성 기준",
        "features": "컴포넌트 설계서, 유스케이스 정의서 등 단계별 필수 산출물과 이를 검토/검수하는 기준 규격서 구별 능력을 평가합니다.",
        "scope": "프로젝트 관리 -> 산출물 가이드"
    },
    "공동계약 및 하도급 관리 규정": {
        "core_concept": "복수의 계약자가 연대하여 이행하는 공동계약 유형 및 공공 SW사업의 하도급 승인 체계",
        "features": "공동이행방식(출자 비율대로 비용/수익 배분)과 분담이행방식(구역 분할 분담)의 리스크 차이, 그리고 하도급 적정성 심의 기준과 비율 규정을 질문합니다.",
        "scope": "법/제도/지침 -> 하도급 및 공동계약"
    },
    "정보기술 아키텍처(EA) 수립 및 관리": {
        "core_concept": "기관의 업무, 데이터, 애플리케이션, 기술의 상호 유기적 구조를 기획 및 운영하는 틀",
        "features": "EA 5대 참조모델(PRM, BRM, SRM, DRM, TRM)의 고유 정의와 각 참조모델 간의 계층적 연계 구조를 매핑하는 유형이 주를 이룹니다.",
        "scope": "법/제도/지침 -> EA 수립 가이드"
    }
}

# 4대 대단원 분류 맵핑 (UI 필터 처리)
TOPIC_CATEGORIES = {
    "소프트웨어 진흥법": "법/제도/지침",
    "지능정보화 기본법": "법/제도/지침",
    "행정기관 및 공공기관 정보시스템 구축운영 지침": "법/제도/지침",
    "소프트웨어사업 계약 및 관리감독 지침": "법/제도/지침",
    "공공데이터 및 데이터베이스 표준화 지침": "법/제도/지침",
    "국가계약법 및 예규 규칙": "법/제도/지침",
    "협상에 의한 계약체결기준": "법/제도/지침",
    "용역계약 일반조건 및 지체상금": "법/제도/지침",
    "소프트웨어사업 대가산정 가이드": "법/제도/지침",
    "IT거버넌스 및 COBIT 프레임워크": "법/제도/지침",
    "공동계약 및 하도급 관리 규정": "법/제도/지침",
    "정보기술 아키텍처(EA) 수립 및 관리": "법/제도/지침",
    
    "전자정부법 및 의무감리 제도": "감리 법제도/기술",
    "정보시스템 감리기준 & 감리 수행 규격": "감리 법제도/기술",
    
    "조직 구조론 (매트릭스/기능/프로젝트 조직)": "조직 관리론",
    "동기부여 이론 (매슬로우/허즈버그/맥그리거 등)": "조직 관리론",
    "의사소통 관리 및 소통 채널 계산": "조직 관리론",
    
    "PMBOK 프로젝트 관리 10대 지식 영역": "프로젝트 관리",
    "CPM 일정 관리 및 주공정(Critical Path) 분석": "프로젝트 관리",
    "EVM 획득가치 및 기성고 관리 (CPI/SPI/EAC)": "프로젝트 관리",
    "위험 관리 전략 및 리스크 대응 (회피/전이/완화/수용)": "프로젝트 관리",
    "품질 관리 도구 및 통계적 기법": "프로젝트 관리",
    "변경 통제 절차 및 CCB 변경통제위원회": "프로젝트 관리",
    "소프트웨어 표준 산출물 가이드": "프로젝트 관리"
}

def crop_question_images(pdf_path, year, output_dir):
    """[공통 모듈 위임] PDF로부터 PM 과목 문항 영역을 추출하여 이미지로 저장하고 위치 좌표를 반환"""
    local_img_dir = r"e:\jolly-carson\reports\images"
    artifact_img_dir = os.path.join(ARTIFACT_DIR, "images")
    return image_cropper.get_question_positions_and_crop(
        pdf_path, year, "PM", local_img_dir, artifact_img_dir, force_crop=FORCE_CROP
    )

def extract_pdf_clean(file_path):
    """PDF 종횡비(가로 4단, 세로 2단) 보정 추출"""
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

def slice_pm_section(full_text):
    """PM 과목(1번~25번) 범위 슬라이싱"""
    start_pattern = r"\b1\s*[\.\)]"
    end_pattern = r"\b26\s*[\.\)]"
    
    start_match = re.search(start_pattern, full_text)
    end_match = re.search(end_pattern, full_text)
    
    if start_match:
        start_idx = start_match.start()
        end_idx = end_match.start() if end_match else len(full_text)
        return full_text[start_idx:end_idx].strip()
    return ""

def parse_questions(pm_text):
    """문항 분절화 (직전 문제 발견 위치 이후부터 탐색하여 가짜 문제 번호 역행 오파싱 방지)"""
    questions = []
    last_idx = 0
    positions = {}
    
    # 1번부터 25번까지의 시작 위치를 순차적으로 탐색
    for num in range(1, 26):
        curr_pat = rf"(?<![\.\d]){num}\s*[\.\)]"
        curr_match = re.search(curr_pat, pm_text[last_idx:])
        if not curr_match:
            # 안전 폴백: 만약 검색 범위 좁히기로 못 찾을 경우 전체 영역 재탐색
            curr_match = re.search(curr_pat, pm_text)
            if not curr_match:
                continue
            start_pos = curr_match.start()
        else:
            start_pos = last_idx + curr_match.start()
            
        positions[num] = start_pos
        last_idx = start_pos + len(curr_match.group(0))
        
    sorted_nums = sorted(list(positions.keys()))
    for i, num in enumerate(sorted_nums):
        start_pos = positions[num]
        if i + 1 < len(sorted_nums):
            next_num = sorted_nums[i + 1]
            end_pos = positions[next_num]
            q_body = pm_text[start_pos:end_pos].strip()
        else:
            q_body = pm_text[start_pos:].strip()
            
        # [방어 코드] 보기 ④번 이후에 다단 텍스트 등의 영향으로 타 문제(예: 18번)가 달라붙는 버그 방지
        if "④" in q_body:
            clean_match = re.search(r"④.*?(?=(?:\r?\n)\s*(?!(?:1|2|3|4)\b)\d+\s*[\.\)])", q_body, re.DOTALL)
            if clean_match:
                q_body = q_body[:clean_match.end()].strip()
            
            # 과목 경계를 알리는 한글 구분자나 페이지 지시문이 붙어 있으면 잘라냅니다.
            for separator in ["소프트웨어공학", "데이터베이스", "시스템구조", "보안", "=== NEW PAGE ===", "소프트웨어 공학"]:
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
    
    # 3회 이상 기출 핵심 토픽 필터링하되, [기타]는 항상 표시
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
    update_shared_db(question_db, "PM")
    html_content = build_html_content(question_db, concept_map)
    
    local_path, artifact_path = get_output_paths("pm_frequent_concepts.html")
    
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
