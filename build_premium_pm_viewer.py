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
from build_utils import get_output_paths, update_shared_db
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
    artifact_img_dir = r"C:\Users\DCCIS040000\.gemini\antigravity-ide\brain\7e1fd111-1dc1-495d-82a1-c40573600184\images"
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
    
    html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>프로젝트관리 및 감리 12개년 빈출 개념 정밀 뷰어</title>
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
            user-select: text !important;
            -webkit-user-select: text !important;
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
    <script src="exam_db/pm_db.js?v=20260613"></script>
</head>
<body>



<div class="container">
    <header>
        <h1>프로젝트관리 및 감리 기출 정밀 분석 대시보드</h1>
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
            <span class="badge accent">총 분석 데이터: <span id="total-question-badge">0</span> 문항</span>
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
            badge.href = target + '?v=20260613';
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
            window.location.href = targetRedirect + '?v=20260613';
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
            badge.href = target + '?v=20260613';

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

    // 파이썬 빌더에서 동적으로 인젝션하는 기출문제 데이터베이스
    

    // 파이썬 빌더에서 동적으로 인젝션하는 개념별 매핑 구조
    const topicMapping = %MAPPING_JSON%;

    let currentCategory = '전체';

    // 초기 로딩 렌더러
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

            // 연도별 뱃지 버튼 빌드
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
                if (document.getElementById('total-question-badge')) {
            const uniqueQuestions = new Set();
            const mappingsObj = (typeof conceptMappings !== 'undefined') ? conceptMappings : ((typeof topicMapping !== 'undefined') ? topicMapping : []);
            mappingsObj.forEach(item => {
                if (item.questions) {
                    item.questions.forEach(q => {
                        uniqueQuestions.add(q.year + "_" + q.num);
                    });
                }
            });
            document.getElementById('total-question-badge').textContent = uniqueQuestions.size;
        }
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

            if (document.getElementById('total-question-badge')) {
            const uniqueQuestions = new Set();
            const mappingsObj = (typeof conceptMappings !== 'undefined') ? conceptMappings : ((typeof topicMapping !== 'undefined') ? topicMapping : []);
            mappingsObj.forEach(item => {
                if (item.questions) {
                    item.questions.forEach(q => {
                        uniqueQuestions.add(q.year + "_" + q.num);
                    });
                }
            });
            document.getElementById('total-question-badge').textContent = uniqueQuestions.size;
        }
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
    html_content = html_template.replace("%MAPPING_JSON%", mapping_json)
    return html_content

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
