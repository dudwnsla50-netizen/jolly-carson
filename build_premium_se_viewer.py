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
from build_utils import get_output_paths, update_shared_db
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
    artifact_img_dir = r"C:\Users\DCCIS040000\.gemini\antigravity-ide\brain\7e1fd111-1dc1-495d-82a1-c40573600184\images"
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
    html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>소프트웨어공학 12개년 빈출 개념 정밀 뷰어</title>
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

        /* Card Layout 내부 요소 */
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

        /* Year Badges Grid */
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

        /* Inline Question Viewer */
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
    <script src="exam_db/se_db.js?v=20260613"></script>
</head>
<body>

<div class="container">
    <header>
        <h1>소프트웨어공학 기출 정밀 분석 대시보드</h1>
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
    
    const topicMapping = %MAPPING_JSON%;
    let currentCategory = '전체';

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
            
            const viewer = document.getElementById(`viewer-${index}`);
            const isViewerOpen = viewer.style.display === 'flex';
            
            if (!isViewerOpen && dataObj.rep_year && dataObj.rep_num) {
                openQuestion(dataObj.rep_year, dataObj.rep_num, index);
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
    # 템플릿 대체 처리
    html_content = html_template.replace("%MAPPING_JSON%", mapping_json)
    return html_content

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
