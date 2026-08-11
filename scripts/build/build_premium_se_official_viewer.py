# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

"""
[초프리미엄 소프트웨어공학 공식 범위(SE.txt) 기출문제 뷰어 자동 빌더]
- 목적: 2015년~2026년 기출 PDF에서 소프트웨어공학 전체 문항(26~50번)을 읽어와서 
  공식 가이드라인(SE.txt) 대단원 및 세부 중단원에 부합하도록 구조화하고, 
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

# SE.txt 공식 가이드라인 기반의 33개 중단원 분류 사전 및 키워드 매핑
CONCEPT_KEYWORDS = {
    # 1. 요구사항분석 및 설계
    "1-a. 요구사항 도출, 요구사항 분석, 요구사항 명세, 요구사항 추적": ["요구사항", "요구 명세", "요구 도출", "요구 분석", "요구 추적", "유스케이스", "use case", "사용사례"],
    "1-b. 객체지향 개념": ["객체지향", "상속", "캡슐화", "다형성", "추상화", "일반화", "실현", "연관", "합성", "집합", "의존", "overriding", "overloading", "오버라이딩", "오버로딩"],
    "1-c. 설계원리": ["설계 원칙", "설계원칙", "solid", "srp", "ocp", "lsp", "isp", "dip", "리스코프", "의존 역전", "단일 책임", "개방 폐쇄", "인터페이스 분리", "모듈 독립성", "결합도", "응집도", "coupling", "cohesion"],
    "1-d. UML/SysML 모델링": ["uml", "sysml", "다이어그램", "diagram", "클래스 다이어그램", "시퀀스 다이어그램", "상태 다이어그램", "활동 다이어그램", "state machine", "activity diagram", "use case diagram"],
    "1-e. 아키텍처 스타일(계층구조, 클라이언트 서버, 트랜잭션 처리, mvc, 이벤트 중심 등)": ["아키텍처 스타일", "architecture style", "계층 구조", "layered architecture", "클라이언트 서버", "client-server", "트랜잭션 처리", "mvc", "이벤트 중심", "event-driven", "repository architecture", "monolithic"],
    "1-f. 설계패턴": ["디자인 패턴", "gof", "싱글톤", "singleton", "팩토리", "factory", "빌더", "builder", "어댑터", "adapter", "데코레이터", "decorator", "옵저버", "observer", "상태 패턴", "state pattern", "전략 패턴", "strategy pattern", "템플릿 메서드", "template method", "프록시", "proxy"],
    "1-g. 사용자 인터페이스 설계": ["ui", "사용자 인터페이스", "사용성", "인터랙션", "웹접근성", "ux"],

    # 2. 구현 및 테스트
    "2-a. 프로그래밍언어 및 환경(코딩원리, 코딩오류, 코딩 스타일, uml과 코딩)": ["코딩원리", "코딩오류", "코딩 스타일", "uml과 코딩", "java", "c++", "c언어", "파이썬", "컴파일", "코딩 규칙", "misra-c"],
    "2-b. 코드 자동생성, 로우코드/노코드": ["자동생성", "로우코드", "노코드", "low-code", "no-code"],
    "2-c. 웹접근성, 웹호환성 점검": ["웹접근성", "웹호환성", "점검", "지침", "접근성 표준"],
    "2-d. 단위, 모듈, 연계, 통합, 시스템, 인수 등": ["단위 테스트", "모듈 테스트", "연계 테스트", "통합 테스트", "시스템 테스트", "인수 테스트", "테스트 레벨", "인수조건"],
    "2-e. 테스팅 방법 및 도구": ["테스팅 방법", "테스트 기법", "화이트박스", "블랙박스", "구문 검증", "분기 검증", "조건 검증", "결정 검증", "경로 검증", "문장 커버리지", "분기 커버리지", "조건 커버리지", "결정 커버리지", "경로 커버리지", "커버리지", "coverage", "test case", "테스트 케이스", "테스트케이스", "경계값", "동등 분할", "순환 복잡도", "mccabe", "tdd", "테스트 드라이버", "테스트 스텁", "뮤테이션", "concolic", "기호실행"],
    "2-f. KS X ISO/IEC/IEEE 29119, KS X ISO/IEC 33063 SW테스트 관련 표준": ["29119", "33063", "테스트 표준"],

    # 3. 유지관리 및 운영
    "3-a. 유지관리 개념 및 방법": ["유지보수", "유지관리", "개념 및 방법", "3r"],
    "3-b. 형상관리": ["형상 관리", "형상관리", "scm", "베이스라인", "baseline", "ccb", "git", "버전관리"],
    "3-c. ITSM, ITIL(SLA, SLM 등)": ["itsm", "itil", "sla", "slm", "서비스 수준", "서비스 관리"],
    "3-d. 재사용, 재공학, 역공학, Refactoring": ["재사용", "재공학", "역공학", "refactoring", "리팩토링", "리팩터링", "코드 스멜", "bad smell", "코드 냄새"],
    "3-e. 아웃소싱": ["아웃소싱", "outsourcing", "위탁"],

    # 4. 개발방법론, sw 구조 및 공개sw
    "4-a. 구조적, 정보공학, 객체지향": ["구조적 방법론", "정보공학 방법론", "객체지향 방법론"],
    "4-b. CBD, Agile, 데브 옵스, aop 등": ["cbd", "agile", "애자일", "스크럼", "scrum", "스프린트", "플래닝 포커", "데브옵스", "devops", "aop", "관점 지향", "횡단 관심"],
    "4-c. 프로세스 모델 : 폭포수, 프로타이핑, 점진적, 진화적, 나선형, v 모델, 스크럼 등": ["폭포수", "프로토타이핑", "점진적", "진화적", "나선형", "spiral", "v 모델", "v-모델", "프로세스 모델", "생명주기 모델"],
    "4-d. 클린 아키텍처": ["클린 아키텍처", "clean architecture"],
    "4-e. 웹기반 기술주고, j2ee, 닷넷, 컨테이너 등 개발 플랫폼": ["j2ee", "닷넷", ".net", "컨테이너", "docker", "도커", "쿠버네티스", "개발 플랫폼"],
    "4-f. 분산커포넌트 기술, xml 등": ["분산 컴포넌트", "corba", "dcom", "xml", "json"],
    "4-g. 전자정부표준프레임워크, 스프링 프레임워크": ["전자정부표준프레임워크", "전자정부 표준 프레임워크", "스프링 프레임워크", "spring framework", "스프링 부트"],
    "4-h. SOA, MSA": ["soa", "msa", "서비스 지향", "마이크로서비스", "api 게이트웨이", "서킷 브레이커"],
    "4-i. 웹서비스(SOAP, REST)": ["soap", "rest", "웹서비스", "web service", "wsdl", "uddi"],
    "4-j. 오픈소스 개념 및 활용방법": ["오픈소스", "open source", "라이선스", "gpl", "apache", "mit 라이선스"],

    # 5. SW 품질 및 비용산정
    "5-a. SW Product 품질": ["품질 속성", "품질 시나리오", "iso/iec 25010", "iso 25010", "신뢰성", "효율성", "유지보수성", "이식성", "기능성"],
    "5-b. SW Process 품질(CMMi, SPICE, SP인증 등)": ["cmmi", "spice", "sp인증", "sp 인증", "프로세스 품질", "성숙도"],
    "5-c. ISO/IEC 12207, ISO/IEC 25000, ISO/IEC 5055 등 SW품질 관련 표준": ["12207", "25000", "5055", "품질 관련 표준", "품질 표준"],
    "5-d. 품질보증": ["품질보증", "품질 보증", "qa", "품질 감사", "품질 통제"],
    "5-e. 기능점수산정": ["기능 점수", "기능점수", "fp", "ilf", "eif", "ei", "eo", "eq"],
    "5-f. 비용산정 모델": ["비용산정", "비용 산정", "대가산정", "대가 산정", "cocomo", "loc", "만먼스", "effort"]
}

# 공식 세부 설명 메타데이터 정의
CONCEPT_METADATA = {
    # 1. 요구사항분석 및 설계
    "1-a. 요구사항 도출, 요구사항 분석, 요구사항 명세, 요구사항 추적": {"core_concept": "요구사항 생명주기 관리", "features": "요구사항 도출 기법, 분석 원리, 명세서 가라인, 추적 매트릭스 구성 요소를 검증합니다.", "scope": "요구분석 및 설계"},
    "1-b. 객체지향 개념": {"core_concept": "객체지향 설계 핵심 원칙", "features": "상속, 다형성, 캡슐화, 추상화 및 5대 의존 관계의 소스 코드 매핑 구조를 검증합니다.", "scope": "요구분석 및 설계"},
    "1-c. 설계원리": {"core_concept": "결합도와 응집도 및 설계 원리", "features": "SOLID 설계 원칙과 강한 응집도/약한 결합도를 달성하기 위한 상세 설계 요소를 질문합니다.", "scope": "요구분석 및 설계"},
    "1-d. UML/SysML 모델링": {"core_concept": "UML 및 SysML 표기법 분석", "features": "다양한 UML 다이어그램(클래스, 시퀀스, 상태, 활동)과 SysML 제약 조건 명세 특징을 검증합니다.", "scope": "요구분석 및 설계"},
    "1-e. 아키텍처 스타일(계층구조, 클라이언트 서버, 트랜잭션 처리, mvc, 이벤트 중심 등)": {"core_concept": "소프트웨어 아키텍처 패턴", "features": "MVC, Layered, Event-Driven, Repository 등 전통적인 아키텍처 스타일의 구성과 특징을 비교 평가합니다.", "scope": "요구분석 및 설계"},
    "1-f. 설계패턴": {"core_concept": "GoF 디자인 패턴 실전 연계", "features": "23대 생성, 구조, 행위 패턴의 자바 소스코드 수준 활용 방안을 질문합니다.", "scope": "요구분석 및 설계"},
    "1-g. 사용자 인터페이스 설계": {"core_concept": "UI/UX 설계 및 사용성 지침", "features": "UI 설계 3대 규칙, 웹 접근성 설계 기준과 사용자 인터랙션 평가 기법을 질문합니다.", "scope": "요구분석 및 설계"},

    # 2. 구현 및 테스트
    "2-a. 프로그래밍언어 및 환경(코딩원리, 코딩오류, 코딩 스타일, uml과 코딩)": {"core_concept": "코딩 규칙 및 언어별 컴파일 메커니즘", "features": "MISRA-C 등 코딩 표준 규칙 위배 사례 및 디버깅 지침을 검증합니다.", "scope": "구현 및 테스트"},
    "2-b. 코드 자동생성, 로우코드/노코드": {"core_concept": "현대적 개발 패러다임 플랫폼", "features": "모델 기반 개발(MDD)의 코드 자동 생성 기법 및 로우코드 플랫폼의 아키텍처 특징을 질문합니다.", "scope": "구현 및 테스트"},
    "2-c. 웹접근성, 웹호환성 점검": {"core_concept": "국가 웹 접근성 표준 지침 준수", "features": "대체 텍스트, 키보드 조작 보장 등 24대 웹 접근성 점검 기준을 중점 검증합니다.", "scope": "구현 및 테스트"},
    "2-d. 단위, 모듈, 연계, 통합, 시스템, 인수 등": {"core_concept": "테스트 단계별 수행 범위", "features": "하향식/상향식 통합 테스트(드라이버/스텁), 시스템 성능 테스트 및 알파/베타 인수 조건 분석이 출제됩니다.", "scope": "구현 및 테스트"},
    "2-e. 테스팅 방법 및 도구": {"core_concept": "동적/정적 테스트 설계 기법", "features": "화이트박스(제어 흐름 커버리지, 순환 복잡도)와 블랙박스(경계값, 동등 분할)의 세부 연산을 질문합니다.", "scope": "구현 및 테스트"},
    "2-f. KS X ISO/IEC/IEEE 29119, KS X ISO/IEC 33063 SW테스트 관련 표준": {"core_concept": "국제 SW 테스팅 표준", "features": "29119 표준이 규정하는 테스트 프로세스 산출물과 테스트 계획 설계 표준을 검증합니다.", "scope": "구현 및 테스트"},

    # 3. 유지관리 및 운영
    "3-a. 유지관리 개념 및 방법": {"core_concept": "유지보수 유형 분류 및 개선 방법", "features": "수정, 예방, 적응, 완전 유지보수의 특징과 3R 진화 활동을 질문합니다.", "scope": "유지관리 및 운영"},
    "3-b. 형상관리": {"core_concept": "형상 식별, 통제, 감사 및 버전 관리", "features": "베이스라인 설정 요건, CCB 변경 제어 위원회의 변경 통제 절차 및 Git 명령어 분석이 출제됩니다.", "scope": "유지관리 및 운영"},
    "3-c. ITSM, ITIL(SLA, SLM 등)": {"core_concept": "IT 서비스 수준 및 프로세스 관리", "features": "ITIL v4 서비스 생명주기 관리 프로세스 및 SLA 정량 평가 메트릭 설정을 평가합니다.", "scope": "유지관리 및 운영"},
    "3-d. 재사용, 재공학, 역공학, Refactoring": {"core_concept": "코드 현대화 및 소스코드 품질 개선", "features": "코드 스멜 유형 식별 및 메서드 추출 등 안전한 리팩토링 실천 전략을 중점적으로 묻습니다.", "scope": "유지관리 및 운영"},
    "3-e. 아웃소싱": {"core_concept": "IT 서비스 위탁 관리 모델", "features": "SLA 기반의 아웃소싱 관리 절차와 위탁 리스크 식별 기준을 평가합니다.", "scope": "유지관리 및 운영"},

    # 4. 개발방법론, sw 구조 및 공개sw
    "4-a. 구조적, 정보공학, 객체지향": {"core_concept": "정통적 소프트웨어 방법론 특징", "features": "각 방법론의 분석 대상(프로세스, 데이터, 객체)과 고유 산출물 특징을 비교 질문합니다.", "scope": "개발방법론 및 플랫폼"},
    "4-b. CBD, Agile, 데브 옵스, aop 등": {"core_concept": "현대적 기민한 개발 아키텍처", "features": "스크럼 프레임워크 5대 회의와 산출물, AOP의 횡단 관심사 삽입 기법(Joinpoint/Advice)을 질문합니다.", "scope": "개발방법론 및 플랫폼"},
    "4-c. 프로세스 모델 : 폭포수, 프로타이핑, 점진적, 진화적, 나선형, v 모델, 스크럼 등": {"core_concept": "SDLC 생명주기 생태계 프로세스", "features": "폭포수, V-모델, 나선형(위험 분석), 점진적 모델의 생명주기 통제 절차를 검증합니다.", "scope": "개발방법론 및 플랫폼"},
    "4-d. 클린 아키텍처": {"core_concept": "관심사 분리 및 비즈니스 룰 보호", "features": "고수준 도메인 룰(엔티티/유스케이스) 중심의 내부 의존성 통제 규칙을 묻습니다.", "scope": "개발방법론 및 플랫폼"},
    "4-e. 웹기반 기술주고, j2ee, 닷넷, 컨테이너 등 개발 플랫폼": {"core_concept": "웹 개발 기술 플랫폼 인프라", "features": "Docker 컨테이너 가상화 기술의 경량성 아키텍처 장점 및 Kubernetes 관리 기법을 평가합니다.", "scope": "개발방법론 및 플랫폼"},
    "4-f. 분산커포넌트 기술, xml 등": {"core_concept": "분산 환경 메시지 통신 표준", "features": "XML/JSON 구조적 메시지 파싱 및 분산 컴포넌트 간 트랜잭션 보장 방안을 검증합니다.", "scope": "개발방법론 및 플랫폼"},
    "4-g. 전자정부표준프레임워크, 스프링 프레임워크": {"core_concept": "국내 공공 프레임워크 표준 기술", "features": "Spring Framework의 IoC(제어역전)와 DI(의존성 주입) 원리 및 eGovFrame 구성 요소를 검증합니다.", "scope": "개발방법론 및 플랫폼"},
    "4-h. SOA, MSA": {"core_concept": "마이크로서비스 아키텍처 설계 패턴", "features": "Saga 패턴의 트랜잭션 관리, API Gateway, Circuit Breaker의 가용성 제어 전략을 질문합니다.", "scope": "개발방법론 및 플랫폼"},
    "4-i. 웹서비스(SOAP, REST)": {"core_concept": "웹 서비스 연동 인터페이스 규격", "features": "SOAP(WSDL/XML 기반)과 REST(Stateless/HTTP Resource 기반)의 장단점 대조가 출제됩니다.", "scope": "개발방법론 및 플랫폼"},
    "4-j. 오픈소스 개념 및 활용방법": {"core_concept": "공개 소프트웨어 라이선스 의무사항", "features": "GPL, LGPL, Apache, BSD, MIT 라이선스의 저작권 고지 및 소스코드 공개 의무 수준을 비교 검증합니다.", "scope": "개발방법론 및 플랫폼"},

    # 5. SW 품질 및 비용산정
    "5-a. SW Product 품질": {"core_concept": "제품 품질 평가 모델", "features": "ISO/IEC 25010 제품 품질 8대 특성과 시나리오 기반 품질속성 측정 방안을 중점 질문합니다.", "scope": "SW 품질 및 비용산정"},
    "5-b. SW Process 품질(CMMi, SPICE, SP인증 등)": {"core_concept": "프로세스 역량 및 성숙도 평가 모델", "features": "CMMI 5단계 성숙도 핵심 프로세스 영역(PA)과 SP인증 등급별 판정 기준을 비교 평가합니다.", "scope": "SW 품질 및 비용산정"},
    "5-c. ISO/IEC 12207, ISO/IEC 25000, ISO/IEC 5055 등 SW품질 관련 표준": {"core_concept": "소프트웨어 국제 품질 표준", "features": "12207의 3가지 생명주기 프로세스(기본/지원/조직) 구조 및 품질 제약 조건 표준을 질문합니다.", "scope": "SW 품질 및 비용산정"},
    "5-d. 품질보증": {"core_concept": "품질 보증 및 관리 활동", "features": "품질 보증 계획 수립, QA 조직의 감사 및 품질 지표 설정을 검증합니다.", "scope": "SW 품질 및 비용산정"},
    "5-e. 기능점수산정": {"core_concept": "기능 점수 표준 산정", "features": "내부논리파일(ILF) 및 외부인터페이스파일(EIF) 가중치와 간이법/상세법 산정 방식을 검증합니다.", "scope": "SW 품질 및 비용산정"},
    "5-f. 비용산정 모델": {"core_concept": "소프트웨어 비용 예측 기법", "features": "COCOMO 및 Putnam 비용 산정 모델의 특성과 수학적 연산을 질문합니다.", "scope": "SW 품질 및 비용산정"}
}

# 5대 대단원 매핑
TOPIC_CATEGORIES = {
    "1-a. 요구사항 도출, 요구사항 분석, 요구사항 명세, 요구사항 추적": "1. 요구사항분석 및 설계",
    "1-b. 객체지향 개념": "1. 요구사항분석 및 설계",
    "1-c. 설계원리": "1. 요구사항분석 및 설계",
    "1-d. UML/SysML 모델링": "1. 요구사항분석 및 설계",
    "1-e. 아키텍처 스타일(계층구조, 클라이언트 서버, 트랜잭션 처리, mvc, 이벤트 중심 등)": "1. 요구사항분석 및 설계",
    "1-f. 설계패턴": "1. 요구사항분석 및 설계",
    "1-g. 사용자 인터페이스 설계": "1. 요구사항분석 및 설계",
    
    "2-a. 프로그래밍언어 및 환경(코딩원리, 코딩오류, 코딩 스타일, uml과 코딩)": "2. 구현 및 테스트",
    "2-b. 코드 자동생성, 로우코드/노코드": "2. 구현 및 테스트",
    "2-c. 웹접근성, 웹호환성 점검": "2. 구현 및 테스트",
    "2-d. 단위, 모듈, 연계, 통합, 시스템, 인수 등": "2. 구현 및 테스트",
    "2-e. 테스팅 방법 및 도구": "2. 구현 및 테스트",
    "2-f. KS X ISO/IEC/IEEE 29119, KS X ISO/IEC 33063 SW테스트 관련 표준": "2. 구현 및 테스트",
    
    "3-a. 유지관리 개념 및 방법": "3. 유지관리 및 운영",
    "3-b. 형상관리": "3. 유지관리 및 운영",
    "3-c. ITSM, ITIL(SLA, SLM 등)": "3. 유지관리 및 운영",
    "3-d. 재사용, 재공학, 역공학, Refactoring": "3. 유지관리 및 운영",
    "3-e. 아웃소싱": "3. 유지관리 및 운영",
    
    "4-a. 구조적, 정보공학, 객체지향": "4. 개발방법론, sw 구조 및 공개sw",
    "4-b. CBD, Agile, 데브 옵스, aop 등": "4. 개발방법론, sw 구조 및 공개sw",
    "4-c. 프로세스 모델 : 폭포수, 프로타이핑, 점진적, 진화적, 나선형, v 모델, 스크럼 등": "4. 개발방법론, sw 구조 및 공개sw",
    "4-d. 클린 아키텍처": "4. 개발방법론, sw 구조 및 공개sw",
    "4-e. 웹기반 기술주고, j2ee, 닷넷, 컨테이너 등 개발 플랫폼": "4. 개발방법론, sw 구조 및 공개sw",
    "4-f. 분산커포넌트 기술, xml 등": "4. 개발방법론, sw 구조 및 공개sw",
    "4-g. 전자정부표준프레임워크, 스프링 프레임워크": "4. 개발방법론, sw 구조 및 공개sw",
    "4-h. SOA, MSA": "4. 개발방법론, sw 구조 및 공개sw",
    "4-i. 웹서비스(SOAP, REST)": "4. 개발방법론, sw 구조 및 공개sw",
    "4-j. 오픈소스 개념 및 활용방법": "4. 개발방법론, sw 구조 및 공개sw",
    
    "5-a. SW Product 품질": "5. SW 품질 및 비용산정",
    "5-b. SW Process 품질(CMMi, SPICE, SP인증 등)": "5. SW 품질 및 비용산정",
    "5-c. ISO/IEC 12207, ISO/IEC 25000, ISO/IEC 5055 등 SW품질 관련 표준": "5. SW 품질 및 비용산정",
    "5-d. 품질보증": "5. SW 품질 및 비용산정",
    "5-e. 기능점수산정": "5. SW 품질 및 비용산정",
    "5-f. 비용산정 모델": "5. SW 품질 및 비용산정"
}

def crop_question_images(pdf_path, year, output_dir):
    """[공통 모듈 위임] PDF로부터 SE 과목 문항 영역을 추출하여 이미지로 저장하고 위치 좌표를 반환"""
    local_img_dir = r"e:\jolly-carson\reports\images"
    artifact_img_dir = os.path.join(ARTIFACT_DIR, "images")
    return image_cropper.get_question_positions_and_crop(
        pdf_path, year, "SE", local_img_dir, artifact_img_dir, force_crop=FORCE_CROP
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

def slice_se_section(full_text):
    start_pattern = r"\b26\s*[\.\)]"
    end_pattern = r"\b51\s*[\.\)]"
    
    start_match = re.search(start_pattern, full_text)
    end_match = re.search(end_pattern, full_text)
    
    if start_match:
        start_idx = start_match.start()
        end_idx = end_match.start() if end_match else len(full_text)
        return full_text[start_idx:end_idx].strip()
    return ""

def parse_questions(se_text):
    questions = []
    for num in range(26, 51):
        curr_pat = rf"(?<![\.\d]){num}\s*[\.\)]"
        next_pat = rf"(?<![\.\d]){num+1}\s*[\.\)]"
        
        curr_match = re.search(curr_pat, se_text)
        if not curr_match:
            continue
            
        start_pos = curr_match.start()
        next_match = re.search(next_pat, se_text)
        
        if next_match:
            end_pos = next_match.start()
            q_body = se_text[start_pos:end_pos].strip()
        else:
            q_body = se_text[start_pos:].strip()
            
        if "④" in q_body:
            clean_match = re.search(r"④.*?(?=(?:\r?\n)\s*(?!(?:1|2|3|4)\b)\d+\s*[\.\)])", q_body, re.DOTALL)
            if clean_match:
                q_body = q_body[:clean_match.end()].strip()
            
            for separator in ["데이터베이스", "시스템구조", "보안", "소프트웨어 공학", "=== NEW PAGE ==="]:
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

def main():
    question_db, concept_map = run_extraction_and_mapping()
    update_shared_db(question_db, "SE")
    html_content = build_html_content(question_db, concept_map)
    
    local_path, artifact_path = get_output_paths("se_official_scopes.html")
    
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
