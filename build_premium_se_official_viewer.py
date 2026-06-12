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
    artifact_img_dir = r"C:\Users\DCCIS040000\.gemini\antigravity-ide\brain\7e1fd111-1dc1-495d-82a1-c40573600184\images"
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
    
    db_json = json.dumps(question_db, ensure_ascii=False, indent=2)
    mapping_json = json.dumps(sorted_concepts, ensure_ascii=False, indent=2)
    
    html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>소프트웨어공학 공식 범위별 기출 뷰어</title>
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

        /* 스크롤바 디자인 */
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
        .viewer-body::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }
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

        /* 반응형 모바일 최적화 */
        @media (max-width: 768px) {
            body { padding: 1.5rem 0.8rem; }
            header h1 { font-size: 1.8rem; line-height: 1.3; }
            header p.subtitle { font-size: 0.88rem; padding: 0 0.5rem; word-break: keep-all; }
            .meta-badges { gap: 0.5rem; }
            .badge { padding: 0.25rem 0.6rem; font-size: 0.72rem; }
            .filter-section { gap: 0.4rem; margin-bottom: 1.5rem; }
            .filter-btn { padding: 0.35rem 0.7rem; font-size: 0.78rem; }
            .accordion-trigger { padding: 1.2rem 1rem; gap: 0.6rem; }
            .concept-title {
            user-select: text !important;
            -webkit-user-select: text !important; font-size: 1.05rem; }
            .rank-badge { font-size: 1rem; }
            .category-tag, .freq-count-badge { font-size: 0.7rem; padding: 0.1rem 0.35rem; }
            .card-meta-grid { grid-template-columns: 80px 1fr; font-size: 0.82rem; row-gap: 0.4rem; }
            .accordion-inner { padding: 1.2rem 1rem; gap: 1rem; }
            .section-title { font-size: 0.75rem; }
            .year-btn { padding: 0.3rem 0.6rem; font-size: 0.75rem; }
            .inline-question-viewer { padding: 0.9rem; }
            .viewer-body { font-size: 0.85rem; max-height: 300px; }
            .modal-card { width: 95%; max-height: 90%; }
            .modal-card-header { padding: 1rem; }
            .modal-card-title { font-size: 1.05rem; }
            .modal-card-body { padding: 0.8rem 1rem 1.2rem 1rem; }
            .modal-topic-item { padding: 0.6rem 0.8rem; }
            .modal-topic-name { font-size: 0.85rem; }
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
    <script src="exam_db/se_db.js?v=20260613"></script>
</head>
<body>

<div class="container">
    <header>
        <h1>소프트웨어공학 공식 범위별 기출 대시보드</h1>
        <p class="subtitle">공식 시험 가이드라인(SE.txt) 5대 단원 및 33개 중단원 매핑 기출 뷰어</p>
        
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
            <span class="badge" onclick="openTopicListModal()" style="cursor: pointer; transition: all 0.2s;" title="클릭 시 중단원 목록 팝업 열기">
                매핑된 공식 중단원: <span id="topic-count-badge">0</span>개
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
                            <span class="rank-badge">${item.concept.split('.')[0]}</span>
                            <span class="concept-title">${item.concept}</span>
                            <span class="category-tag">${item.category.split(' ')[1] || item.category}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.8rem;">
                            <span class="freq-count-badge">매핑 문항 ${item.count}개</span>
                            <span class="arrow">▼</span>
                        </div>
                    </div>
                    <div class="card-meta-grid">
                        <div class="meta-label">공식 영역</div>
                        <div class="meta-value accent">${item.scope}</div>
                        <div class="meta-label">핵심 개념</div>
                        <div class="meta-value" style="font-weight: 500; color: #ffffff;">${item.core_concept}</div>
                        <div class="meta-label">출제 특징</div>
                        <div class="meta-value">${item.features}</div>
                        <div class="meta-label">출제 연도</div>
                        <div class="meta-value">${item.years.length > 0 ? item.years.join(', ') + '년' : '출제 이력 없음'}</div>
                    </div>
                </button>
                <div class="accordion-content" style="max-height: 0px;">
                    <div class="accordion-inner">
                        <div class="section-title">해당 범위 기출문제 선택 (클릭 시 하단에 문제 전환)</div>
                        <div class="year-grid">
                            ${yearButtonsHtml || '<span class="memo-placeholder">이 중단원에 직접 매핑된 기출문제가 캐시 DB에 존재하지 않습니다.</span>'}
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
            if (btn.textContent === category || (category === '전체' && btn.textContent === '전체')) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        if (document.getElementById('total-question-badge')) {
            const uniqueQuestions = new Set();
            const mappingsObj = topicMapping;
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

    if (document.getElementById('total-question-badge')) {
        const uniqueQuestions = new Set();
        const mappingsObj = topicMapping;
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
    html_content = html_template.replace("%MAPPING_JSON%", mapping_json)
    return html_content

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
