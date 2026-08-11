# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

"""
[초프리미엄 소프트웨어공학 기출문제 뷰어 자동 빌더]
- 목적: 2015년~2026년 기출 PDF에서 소프트웨어공학 전체 문항(26~50번)을 읽어와서 
  구조화된 데이터베이스를 빌드하고, 이를 수려한 다크모드 대시보드 HTML 파일 안에 
  임베딩(JS 변수로 주입)하여 사용자 인터랙티브 뷰어 웹앱을 자동 생성합니다.
- 특징: 외부 웹 프레임워크나 서버 없이 HTML 더블클릭만으로 모든 12개년 기출문제를 
  토픽별/연도별 클릭하여 즉각 모달 팝업으로 확인할 수 있습니다.
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

# 한글 윈도우 환경에서 콘솔 출력 깨짐 방지
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 경로 상수의 직관적인 매핑
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

# 24대 정밀 세부 개념 분류 사전
CONCEPT_KEYWORDS = {
    "클래스 다이어그램 (UML)": ["클래스 다이어그램", "class diagram", "클래스설계"],
    "시퀀스 다이어그램 (UML)": ["시퀀스 다이어그램", "sequence diagram", "실행 흐름"],
    "상태/활동 다이어그램 (UML)": ["상태 다이어그램", "활동 다이어그램", "상태머신", "state machine", "activity diagram"],
    "SysML 모델링": ["sysml", "requirement diagram", "parametric diagram"],
    "요구사항 분석 및 명세": ["요구사항 명세", "요구사항 도출", "요구사항 분석", "요구사항 추적", "유스케이스", "use case", "사용사례"],
    "ISO/IEC 25010 품질 표준": ["iso/iec 25010", "iso 25010", "품질 특성", "신뢰성", "사용성", "이식성", "유지보수성", "품질 모델", "품질주특성", "품질 주특성"],
    "CMMI 모델": ["cmmi", "성숙도"],
    "화이트박스 테스팅 & 커버리지": ["화이트박스", "구문 검증", "구문 커버리지", "분기 검증", "분기 커버리지", "조건 검증", "조건 커버리지", "결정 검증", "결정 커버리지", "경로 검증", "경로 커버리지", "결정/조건", "다중 조건", "문장 커버리지", "분기 커버리지"],
    "블랙박스 테스팅 기법": ["블랙박스", "동등 분할", "경계값", "경계치", "경계값 분석", "동등분할 기법"],
    "ISO/IEC/IEEE 29119 표준": ["29119", "iso/iec/ieee 29119"],
    "애자일 및 스크럼 방법론": ["애자일", "agile", "스크럼", "scrum", "스프린트", "플래닝 포커", "백로그", "사용자 스토리", "xp", "익스트림 프로그래밍"],
    "SDLC 프로세스 모델 (폭포수/나선형/V-모델)": ["폭포수", "나선형", "v 모델", "v-모델", "프로토타이핑", "점진적", "진화적", "프로세스 모델"],
    "MSA (마이크로서비스 아키텍처)": ["msa", "마이크로서비스", "domain driven", "bounded context"],
    "리팩토링 기법 (Refactoring)": ["리팩토링", "refactoring", "리팩터링", "임시변수 분리", "매개변수 할당", "메서드 추출"],
    "코드 스멜 (Bad Smell)": ["코드 냄새", "악취", "smell", "bad smell"],
    "클린 아키텍처 (Clean Architecture)": ["클린 아키텍처", "clean architecture"],
    "GoF 디자인 패턴 (행위/구조/생성)": ["디자인 패턴", "디자인패턴", "설계 패턴", "싱글톤", "singleton", "팩토리", "factory", "빌더", "builder", "어댑터", "adapter", "데코레이터", "decorator", "옵저버", "observer", "상태 패턴", "state pattern", "전략 패턴", "strategy pattern", "템플릿 메서드", "template method", "프록시", "proxy", "gof"],
    "SOLID 객체지향 설계 원칙": ["solid", "객체지향 설계 원칙", "단일 책임", "srp", "개방 폐쇄", "ocp", "리스코프 치환", "lsp", "인터페이스 분리", "isp", "의존 역전", "의존역전", "dip"],
    "3R (역공학/재공학/재사용)": ["역공학", "재공학", "재사용", "3r"],
    "ITIL / ITSM 및 SLA": ["itil", "itsm", "sla", "slm", "서비스 수준", "서비스 관리"],
    "기능 점수 (Function Point) 산정": ["기능 점수", "기능점수", "fp", "function point", "일반 기능점수", "ilf", "eif", "ei", "eo", "eq", "기능점수분석"],
    "COCOMO / 비용산정 모델": ["cocomo", "비용 산정", "비용산정", "대가산정", "sw사업 대가", "보정계수"],
    "형상 관리 활동 (식별/통제/감사/기록)": ["형상 관리", "형상관리", "scm", "베이스라인", "baseline", "형상 통제", "형상 식별", "형상 감사", "ccb", "형상통제위원회"],
    "모듈화 (결합도 및 응집도)": ["결합도", "응집도", "coupling", "cohesion"]
}

# 24대 정밀 세부 개념 설명 메타데이터 정의
CONCEPT_METADATA = {
    "클래스 다이어그램 (UML)": {
        "core_concept": "클래스 간의 정적 관계(일반화, 실현, 연관, 집합, 합성, 의존) 및 다중도 설계",
        "features": "다이어그램 해석을 기반으로 소스 코드 매핑 구조를 파악하고, 집합(Aggregation)과 합성(Composition)의 객체 생명주기 의존성 차이를 구별하는 능력을 검증합니다.",
        "scope": "요구분석/설계 -> 정적 모델링"
    },
    "시퀀스 다이어그램 (UML)": {
        "core_concept": "객체 간 주고받는 동적 메시지 흐름을 시간 순서에 따라 시각화 및 분석",
        "features": "동기 메시지(채워진 실선), 비동기 메시지(선형 실선), 반환 메시지(점선) 및 Alt, Opt, Loop, Par 복합 프레임 내 실행 제어 흐름과 객체 간 생명주기 분석이 출제됩니다.",
        "scope": "요구분석/설계 -> 동적 모델링"
    },
    "상태/활동 다이어그램 (UML)": {
        "core_concept": "단일 객체의 상태 전이(State Machine) 및 업무 프로세스의 제어 흐름(Activity) 분석",
        "features": "상태 전이 이벤트, Guard 조건, 내부 액션(entry, do, exit) 해석과 활동 다이어그램의 병렬 분기/결합(Fork/Join, Decision/Merge) 메커니즘을 주로 묻습니다.",
        "scope": "요구분석/설계 -> 동적 모델링"
    },
    "SysML 모델링": {
        "core_concept": "하드웨어와 소프트웨어가 융합된 복잡한 시스템 엔지니어링 모델링 표준 명세",
        "features": "요구사항 간 추적을 표시하는 요구사항 다이어그램(Requirement Diagram)과 물리 수식/수학적 제약조건을 정의하는 파라메트릭 다이어그램(Parametric Diagram)의 특징 비교가 출제됩니다.",
        "scope": "요구분석/설계 -> 시스템 모델링"
    },
    "요구사항 분석 및 명세": {
        "core_concept": "사용자 및 시스템 요구사항 도출, 분석, 명세, 검증 및 추적성 관리",
        "features": "기능적/비기능적 요구사항 식별 기준과 요구사항 추적성 매트릭스(Traceability Matrix) 작성 및 유스케이스 모델링의 기본/대안 흐름 명세 구조에 대한 출제가 많습니다.",
        "scope": "요구분석/설계 -> 요구공학"
    },
    "ISO/IEC 25010 품질 표준": {
        "core_concept": "소프트웨어 제품 품질 평가를 위한 8대 주특성 및 하위 31개 부특성 체계",
        "features": "매년 출제되는 초빈출 단골 영역으로, 신뢰성(장애 허용성, 복구 가능성), 유지보수성(모듈성, 재사용성, 테스트 가능성), 이식성(설치성, 대체성) 등의 부특성 매핑을 중점 질문합니다.",
        "scope": "품질/비용산정 -> 품질 평가 표준"
    },
    "CMMI 모델": {
        "core_concept": "소프트웨어 개발 프로세스 역량 평가 및 프로세스 성숙도 평가 모델",
        "features": "단계형 표현의 5가지 성숙도 수준(Initial->Managed->Defined->Quantitatively Managed->Optimizing)의 고유 특징과 각 수준별 핵심 프로세스 영역(PA) 매핑을 물어봅니다.",
        "scope": "품질/비용산정 -> 프로세스 개선 모델"
    },
    "화이트박스 테스팅 & 커버리지": {
        "core_concept": "코드의 내부 제어 구조를 기반으로 경로를 실행하여 검증하는 동적 테스트 기법",
        "features": "구문(Statement), 결정(Decision), 조건(Condition), 결정/조건, 다중 조건 커버리지의 포함 관계와 제어 흐름 그래프(CFG)에서의 순환 복잡도(McCabe: E - N + 2) 및 최소 테스트 케이스 계산이 매년 출제됩니다.",
        "scope": "구현/테스트 -> 화이트박스 테스팅"
    },
    "블랙박스 테스팅 기법": {
        "core_concept": "프로그램의 내부 논리 구조를 배제하고 외부 명세를 기반으로 수행하는 기능 테스트 기법",
        "features": "동등 분할(Equivalence Partitioning)과 경계값 분석(Boundary Value Analysis)의 테스트 케이스 설계 원리, 의사결정 테이블 및 상태 전이 테스팅 기법의 설계 과정을 집중 평가합니다.",
        "scope": "구현/테스트 -> 블랙박스 테스팅"
    },
    "ISO/IEC/IEEE 29119 표준": {
        "core_concept": "소프트웨어 테스팅 국제 표준 구조 및 전 수명주기 테스트 프로세스 체계",
        "features": "Part 1(개념/정의)~Part 5(키워드 드리븐 테스팅)의 구성 요소 및 테스트 계획서, 테스트 시나리오 등 산출물 표준 정의를 평가합니다.",
        "scope": "구현/테스트 -> 테스트 표준"
    },
    "애자일 및 스크럼 방법론": {
        "core_concept": "지속적 소통과 빠른 피드백을 강조하는 기민한 반복형 소프트웨어 개발 패러다임",
        "features": "스크럼(Scrum)의 3대 산출물(백로그)과 4대 회의(계획, 스크럼, 리뷰, 회고), 사용자 스토리 규모 추정을 위한 플래닝 포커(Planning Poker) 및 XP의 12대 실천수칙을 주로 출제합니다.",
        "scope": "방법론/플랫폼 -> 애자일 기법"
    },
    "SDLC 프로세스 모델 (폭포수/나선형/V-모델)": {
        "core_concept": "소프트웨어 개발 전 주기 ",
        "features": "폭포수(선형 순차형), V-모델(개발과 테스트 단계 간 1:1 대칭 검증), 나선형(위험 분석 및 완화를 통한 점진적 진화) 모델의 고유 특징과 적합 프로젝트 선정을 출제합니다.",
        "scope": "방법론/플랫폼 -> 프로세스 모델"
    },
    "MSA (마이크로서비스 아키텍처)": {
        "core_concept": "하나의 거대 서비스를 여러 개의 독립 배포 가능한 초소형 서비스로 결합하는 아키텍처",
        "features": "도메인 주도 설계(DDD)의 Bounded Context 활용, 서비스별 독립 DB(Database per Service) 패턴, Saga 패턴을 이용한 분산 트랜잭션 처리, API Gateway 적용에 초점이 맞춰집니다.",
        "scope": "방법론/플랫폼 -> 아키텍처 패턴"
    },
    "리팩토링 기법 (Refactoring)": {
        "core_concept": "외부 동작은 변경하지 않고 내부 소스 코드를 재구성하여 가독성과 유지보수성을 극대화",
        "features": "메서드 추출(Extract Method), 임시변수 분리(Split Temporary Variable), 다형성을 활용한 조건문 제거 등 중복 및 구조 결함을 안전하게 교정하는 구체적 실천법이 출제됩니다.",
        "scope": "유지관리/운영 -> 코드 품질 개선"
    },
    "코드 스멜 (Bad Smell)": {
        "core_concept": "시스템 아키텍처나 소스 코드에서 유지보수성 저하를 유발하는 잘못된 설계 징후",
        "features": "중복 코드, 너무 긴 메서드, 거대한 클래스, 기능에 대한 욕심(Feature Envy), 산재한 변경(Shotgun Surgery) 등 코드 악취 유형을 정의하고 적합한 리팩토링 전략을 맵핑하는 문제입니다.",
        "scope": "유지관리/운영 -> 코드 품질 개선"
    },
    "클린 아키텍처 (Clean Architecture)": {
        "core_concept": "비즈니스 규칙(Core Domain) 중심 설계와 외부 기술(DB, 프레임워크)의 철저한 관심사 격리",
        "features": "의존성 방향은 항상 고수준 핵심 비즈니스 영역(안쪽 엔티티)으로만 흐르며, 제어 흐름 역전을 통해 외부 어댑터 레이어와의 결합을 낮추는 의존성 제어 규칙이 핵심 출제 주제입니다.",
        "scope": "방법론/플랫폼 -> 아키텍처 패턴"
    },
    "GoF 디자인 패턴 (행위/구조/생성)": {
        "core_concept": "자주 마주하는 클래스 설계 문제들에 대해 입증된 23대 객체지향 설계 재사용 솔루션",
        "features": "행위(State, Strategy, Observer, Template Method), 구조(Decorator, Proxy, Adapter), 생성(Singleton, Factory Method, Builder) 패턴의 차이를 파악하고 Java 소스 코드 매핑 구조를 이해해야 합니다.",
        "scope": "방법론/플랫폼 -> 디자인 패턴"
    },
    "SOLID 객체지향 설계 원칙": {
        "core_concept": "유지보수와 확장에 유리한 객체지향 클래스 설계를 위한 5가지 원칙",
        "features": "단일 책임(SRP), 개방 폐쇄(OCP), 리스코프 치환(LSP - 상속 계약 준수), 인터페이스 분리(ISP), 의존 역전(DIP - 추상화 의존)의 의미를 이해하고 코드가 어떤 원칙을 위배했는지 평가합니다.",
        "scope": "요구분석/설계 -> 객체지향 설계"
    },
    "3R (역공학/재공학/재사용)": {
        "core_concept": "레거시 시스템을 분석하여 현대적으로 재설계 및 자산화하는 소프트웨어 진화 활동",
        "features": "대상 소스 코드로부터 추상화 모델을 복원(역공학), 기존 소스를 분석하여 새로운 요건과 기술을 적용해 개선(재공학), 범용 모듈을 자산화하여 신규 개발 비용을 절감(재사용)을 구분합니다.",
        "scope": "유지관리/운영 -> 소프트웨어 진화"
    },
    "ITIL / ITSM 및 SLA": {
        "core_concept": "고객 관점의 안정적인 IT 서비스 운영 및 유지관리를 위한 표준 품질 관리 체계",
        "features": "ITIL v4 서비스 가치 시스템, SLA(서비스 수준 계약) 상의 가용성/장애 처리 속도 등 정량 평가지표, 이를 관리하는 SLM(서비스 수준 관리) 수명주기 활동을 주로 묻습니다.",
        "scope": "유지관리/운영 -> IT 서비스 관리"
    },
    "기능 점수 (Function Point) 산정": {
        "core_concept": "LOC가 아닌 사용자 요구 기능 사양(데이터 및 트랜잭션 크기)을 정량 평가하여 SW 규모를 산정하는 표준",
        "features": "데이터 기능(ILF 내부논리파일, EIF 외부연계파일)과 트랜잭션 기능(EI 외부입력, EO 외부출력, EQ 외부조회)의 가중치를 계산하고, 보정계수를 곱하여 소프트웨어 대가를 정밀 계산하는 문항입니다.",
        "scope": "품질/비용산정 -> 비용 산정"
    },
    "COCOMO / 비용산정 모델": {
        "core_concept": "소프트웨어의 원시 코드 라인수(LOC) 기반의 비용 및 노력 추정 모델",
        "features": "COCOMO II 단계(애플리케이션 조성, 초기 설계, 포스트 아키텍처)의 차이점, 규모에 따른 프로젝트 유형(유기형, 반결합형, 내장형) 특징 및 노력보정계수를 반영한 M/M(Man-Month) 연산이 핵심입니다.",
        "scope": "품질/비용산정 -> 비용 산정"
    },
    "형상 관리 활동 (식별/통제/감사/기록)": {
        "core_concept": "소프트웨어 생명주기 전반에 걸쳐 모든 개발 산출물의 버전 및 변경 이력을 통제하는 활동",
        "features": "베이스라인(Baseline) 설정, 변경 관리의 최종 의결 기구인 형상 통제 위원회(CCB)의 승인 프로세스, 그리고 식별->통제->감사->기록으로 이어지는 4대 고유 활동 순서와 정의를 검증합니다.",
        "scope": "유지관리/운영 -> 형상 관리"
    },
    "모듈화 (결합도 및 응집도)": {
        "core_concept": "모듈 독립성을 극대화하기 위해 '강한 응집도, 약한 결합도'를 지향하는 아키텍처 설계 지표",
        "features": "응집도 7단계(우연->논리->시간->절차->통신->순차->기능적 응집도) 및 결합도 6단계(자료->스탬프->제어->외부->공통->내용 결합도)의 강약 순서와 소스 코드 모듈 분석을 질문합니다.",
        "scope": "요구분석/설계 -> 아키텍처 품질"
    }
}

# 5대 대분류 맵핑 (UI상 뱃지 필터 처리를 위함)
TOPIC_CATEGORIES = {
    "클래스 다이어그램 (UML)": "요구분석/설계",
    "시퀀스 다이어그램 (UML)": "요구분석/설계",
    "상태/활동 다이어그램 (UML)": "요구분석/설계",
    "SysML 모델링": "요구분석/설계",
    "요구사항 분석 및 명세": "요구분석/설계",
    "SOLID 객체지향 설계 원칙": "요구분석/설계",
    "모듈화 (결합도 및 응집도)": "요구분석/설계",
    
    "ISO/IEC 25010 품질 표준": "품질/비용산정",
    "CMMI 모델": "품질/비용산정",
    "기능 점수 (Function Point) 산정": "품질/비용산정",
    "COCOMO / 비용산정 모델": "품질/비용산정",
    
    "화이트박스 테스팅 & 커버리지": "구현/테스트",
    "블랙박스 테스팅 기법": "구현/테스트",
    "ISO/IEC/IEEE 29119 표준": "구현/테스트",
    
    "리팩토링 기법 (Refactoring)": "유지관리/운영",
    "코드 스멜 (Bad Smell)": "유지관리/운영",
    "3R (역공학/재공학/재사용)": "유지관리/운영",
    "ITIL / ITSM 및 SLA": "유지관리/운영",
    "형상 관리 활동 (식별/통제/감사/기록)": "유지관리/운영",
    
    "애자일 및 스크럼 방법론": "방법론/플랫폼",
    "SDLC 프로세스 모델 (폭포수/나선형/V-모델)": "방법론/플랫폼",
    "MSA (마이크로서비스 아키텍처)": "방법론/플랫폼",
    "클린 아키텍처 (Clean Architecture)": "방법론/플랫폼",
    "GoF 디자인 패턴 (행위/구조/생성)": "방법론/플랫폼"
}

def crop_question_images(pdf_path, year, output_dir):
    """[공통 모듈 위임] PDF로부터 SE 과목 문항 영역을 추출하여 이미지로 저장하고 위치 좌표를 반환"""
    local_img_dir = r"e:\jolly-carson\reports\images"
    artifact_img_dir = os.path.join(ARTIFACT_DIR, "images")
    return image_cropper.get_question_positions_and_crop(
        pdf_path, year, "SE", local_img_dir, artifact_img_dir, force_crop=FORCE_CROP
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

def slice_se_section(full_text):
    """소프트웨어공학(26번~50번) 범위 슬라이싱"""
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
    """문항 분절화"""
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
            
        # [방어 코드] 보기 ④번 이후에 다단 텍스트 등의 영향으로 타 문제(예: 33번)가 달라붙는 버그 방지
        if "④" in q_body:
            clean_match = re.search(r"④.*?(?=(?:\r?\n)\s*(?!(?:1|2|3|4)\b)\d+\s*[\.\)])", q_body, re.DOTALL)
            if clean_match:
                q_body = q_body[:clean_match.end()].strip()
            
            # 과목 경계를 알리는 한글 구분자나 페이지 지시문이 붙어 있으면 잘라냅니다.
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
    # 빈출 빈도 순 정렬
    sorted_concepts = []
    for concept, items in concept_map.items():
        # 연도 정렬 및 유일한 연도 추출
        years = sorted(list(set([it["year"] for it in items])))
        
        # 대표 문제 추출 (가장 최근 기출문제)
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

    # [기타]는 항상 정렬의 맨 마지막에 위치하도록 키 조정 (-1로 부여하여 reverse=True일 때 맨 뒤로 가도록 설정)
    sorted_concepts.sort(key=lambda x: (-1 if x["concept"] == "[기타]" else x["count"]), reverse=True)
    
    # 3회 이상 출제된 세부 토픽만 필터링하되, [기타]는 항상 표시
    filtered_concepts = [c for c in sorted_concepts if c["count"] >= 3 or c["concept"] == "[기타]"]
    
    # JSON 직렬화
    db_json = json.dumps(question_db, ensure_ascii=False, indent=2)
    mapping_json = json.dumps(filtered_concepts, ensure_ascii=False, indent=2)
    
    # HTML 템플릿 코드
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
    
    local_path, artifact_path = get_output_paths("se_frequent_concepts.html")
    
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
