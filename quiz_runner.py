# -*- coding: utf-8 -*-
"""
[소프트웨어공학 자율 퀴즈 및 약점 진단 엔진]
- 설계 목적: 소프트웨어공학(SE) 시험 범위 및 트렌드를 기반으로 AI가 4지선다 예상문제를 자동 생성하고,
  사용자의 풀이 이력을 누적 분석하여 취약한 단원을 피드백하는 오답 보강 수험 시스템입니다.
- 원칙 준수: 외부 라이브러리(SDK) 없이 urllib 및 json만을 사용하여 Gemini API와 실시간 툴 연동하며,
  API 키가 없는 환경을 위해 5대 단원별 고품질 예상문제 데이터셋을 포함한 오프라인 Mock 엔진을 완비했습니다.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
import re

# 기존 파서 모듈 로딩
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import parser

# ==========================================
# 1. 환경 설정 및 상수 정의
# ==========================================
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

SE_SCOPE_PATH = os.path.join("data", "exam_scopes", "SE.txt")
SE_TREND_PATH = os.path.join("data", "exam_analysis_reports", "SE_trend_analysis.md")
HISTORY_PATH = os.path.join("data", "quiz_history.json")

# ==========================================
# 2. 오프라인 Mock 예상문제 데이터셋
# ==========================================
MOCK_QUIZZES = [
    {
        "id": "SE_MOCK_01",
        "category": "1. 요구사항분석 및 설계",
        "question": "다음 중 SOLID 객체지향 설계 원칙에서 '서브타입은 언제나 자신의 기반타입으로 교체할 수 있어야 한다'는 리스코프 치환 원칙(LSP)에 부합하는 설계 활동으로 가장 적절한 것은?",
        "options": [
            "1. 자식 클래스가 부모 클래스의 선행 조건(Precondition)을 더 강화하여 재정의(Override)한다.",
            "2. 상속 구조 대신 컴포지션(Composition)을 활용하여 코드 재사용성을 올린다.",
            "3. 자식 클래스가 부모 클래스의 계약(Behavioral Contract)과 일관성을 유지하며 동작하도록 구현한다.",
            "4. 하위 클래스에서 부모 클래스의 메소드를 호출할 때 UnsupportedOperationException을 발생시켜 상속을 제한한다."
        ],
        "answer": 3,
        "explanation": "리스코프 치환 원칙(LSP)을 만족하려면 자식 클래스는 부모 클래스의 기능을 오동작 없이 완전히 수행할 수 있어야 합니다. 즉 부모 클래스의 행위적 계약을 위반하지 않고 일관되게 동작해야 하므로 3번이 정답입니다. 부모의 선행 조건을 강화하거나 예외를 던지는 것은 LSP를 위반하는 대표적 사례입니다."
    },
    {
        "id": "SE_MOCK_02",
        "category": "2. 구현 및 테스트",
        "question": "화이트박스 테스트 검증 기준 중, 프로그램 내의 모든 결정문(Decision) 내부의 개별 조건식(Condition)들의 참(True)과 거짓(False)을 최소한 한 번씩 실행해보며 동시에 결정문 전체의 결과도 참/거짓을 모두 만족하게 만드는 가장 적절한 검증 기준은?",
        "options": [
            "1. 구문 검증 기준 (Statement Coverage)",
            "2. 결정 검증 기준 (Branch Coverage)",
            "3. 조건 검증 기준 (Condition Coverage)",
            "4. 결정/조건 검증 기준 (Branch/Condition Coverage)"
        ],
        "answer": 4,
        "explanation": "개별 조건식의 결과와 전체 결정문의 분기 결과를 동시에 모두 최소한 한 번씩 참/거짓으로 만족하게 만드는 기준은 결정/조건 검증 기준(Branch/Condition Coverage)입니다."
    },
    {
        "id": "SE_MOCK_03",
        "category": "3. 유지관리 및 운영",
        "question": "소프트웨어 형상 관리(Configuration Management)의 활동 중, 베이스라인(Baseline)의 제어 하에 있는 형상 항목들의 변경 제안을 공식적으로 접수, 심의, 통제하여 시스템의 무분별한 갱신을 차단하는 통제 활동으로 옳은 것은?",
        "options": [
            "1. 형상 식별 (Configuration Identification)",
            "2. 형상 통제 (Configuration Control)",
            "3. 형상 감사 (Configuration Audit)",
            "4. 형상 상태 보고 (Configuration Status Accounting)"
        ],
        "answer": 2,
        "explanation": "형상 통제(Configuration Control)는 변경 제안의 타당성을 평가하고 공식 승인하는 형상 관리 심의 기구(CCB) 등을 통해 소프트웨어 변경 활동을 통제하고 기준선을 유지하는 작업입니다."
    },
    {
        "id": "SE_MOCK_04",
        "category": "4. 개발방법론, sw 구조 및 공개sw",
        "question": "애자일(Agile) 스크럼(Scrum) 방법론에서, 이전 스프린트 동안의 개발 과정에서 무엇이 잘 되었고 어떤 부분 개선이 필요한지 팀 전체가 참여하여 프로세스적 회고와 다음 개선 행동 계획을 수립하는 회의 명칭은?",
        "options": [
            "1. 스프린트 계획 회의 (Sprint Planning Meeting)",
            "2. 일일 스크럼 회의 (Daily Scrum Meeting)",
            "3. 스프린트 리뷰 회의 (Sprint Review Meeting)",
            "4. 스프린트 회고 회의 (Sprint Retrospective)"
        ],
        "answer": 4,
        "explanation": "스프린트 회고(Sprint Retrospective)는 스프린트가 끝난 시점에 팀의 프로세스, 도구, 협업 방식 등에 대해 개선할 점을 스스로 되돌아보고 액션 플랜을 도출하는 정식 스크럼 의식입니다."
    },
    {
        "id": "SE_MOCK_05",
        "category": "5. SW 품질 및 비용산정",
        "question": "ISO/IEC 25010 소프트웨어 제품 품질 모델의 8대 품질 특성 중, 시스템이 규정된 조건 하에서 규정된 기간 동안 장애 없이 작동하여 신뢰할 수 있는 수준을 나타내는 신뢰성(Reliability)의 하위 특성에 해당하지 않는 것은?",
        "options": [
            "1. 성숙성 (Maturity)",
            "2. 장애 허용성 (Fault Tolerance)",
            "3. 복구 가능성 (Recoverability)",
            "4. 보안성 (Security)"
        ],
        "answer": 4,
        "explanation": "ISO/IEC 25010에서 신뢰성(Reliability)의 하위 부특성은 성숙성, 장애 허용성, 복구 가능성, 가용성 등이 있습니다. 보안성(Security)은 신뢰성과 동등한 레벨의 독립적인 8대 품질 주특성 중 하나입니다."
    }
]

# ==========================================
# 3. 실시간 AI 다이나믹 예상문제 출제기 (Online Generation)
# ==========================================

def generate_quizzes_via_llm():
    """
    [설계 의도]
    적재된 SE 시험 범위(SE.txt)와 최신 기출분석(SE_trend_analysis.md)을 바탕으로
    Gemini API를 호출하여, 5대 대단원에 골고루 분배된 객관식 문제 5문항을 자동 빌드합니다.
    """
    scope_text = ""
    if os.path.exists(SE_SCOPE_PATH):
        with open(SE_SCOPE_PATH, "r", encoding="utf-8") as f:
            scope_text = f.read()
            
    trend_text = ""
    if os.path.exists(SE_TREND_PATH):
        with open(SE_TREND_PATH, "r", encoding="utf-8") as f:
            trend_text = f.read()

    prompt = f"""
당신은 대한민국 최고 수준의 '정보시스템 감리사 자격검정 출제위원장'입니다.
제공된 소프트웨어공학 [상세 시험 범위]와 최근 [기출문제 분석 경향]을 고려하여,
수험생들의 약점을 판단하기에 최적의 난이도를 가진 객관식 변형 예상 문제 5문항을 출제해 주세요.

[소프트웨어공학 상세 시험 범위]
{scope_text}

[소프트웨어공학 최근 기출분석 트렌드]
{trend_text}

[출제 요구사항]
1. 5개 대단원에 대해 각각 정확히 1문제씩 골고루 안배하여 총 5문항을 출제하세요.
   - 단원 1: 1. 요구사항분석 및 설계
   - 단원 2: 2. 구현 및 테스트
   - 단원 3: 3. 유지관리 및 운영
   - 단원 4: 4. 개발방법론, sw 구조 및 공개sw
   - 단원 5: 5. SW 품질 및 비용산정
2. 실제 감리사 난이도로 4지선다형 객관식 형식으로 문제를 내세요.
3. 반드시 아래의 규격화된 JSON Array 포맷으로만 답변하세요. 마크다운 기호(```json)나 여타 텍스트를 절대 덧붙이지 마십시오.

[응답 JSON 스키마 포맷]
[
  {{
    "id": "SE_AUTO_01",
    "category": "1. 요구사항분석 및 설계",
    "question": "문제 내용 지문...",
    "options": [
      "1. 보기 내용...",
      "2. 보기 내용...",
      "3. 보기 내용...",
      "4. 보기 내용..."
    ],
    "answer": 3,
    "explanation": "상세한 해설 및 공부 팁..."
  }}
]

최종 JSON 응답:"""

    try:
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            raw_response = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # 마크다운 펜스 제거 방어막
            if raw_response.startswith("```"):
                # ```json 이나 ``` 텍스트 제거
                lines = raw_response.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_response = "\n".join(lines).strip()
                
            quizzes = json.loads(raw_response)
            return quizzes
    except Exception as e:
        print(f"[경고] AI 실시간 문제 출제 실패 ({e}). 준비된 고품질 오프라인 Mock 예상문제로 전환합니다.")
        return MOCK_QUIZZES

# ==========================================
# 4. 풀이 이력 저장 및 약점 분석 모듈
# ==========================================

def save_and_analyze_quiz(new_attempts):
    """
    [설계 의도]
    새로 푼 문항 결과를 data/quiz_history.json 에 반영하고,
    역대 전체 오답 이력을 단원별로 집계하여 정답률이 60% 미만인 '가장 심각한 취약 약점'을 진단합니다.
    """
    history = {"attempts": []}
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass

    # 새 이력 누적
    history["attempts"].extend(new_attempts)
    
    # 디스크 저장
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[경고] 풀이 이력 파일 저장 실패: {e}")

    # 대분류 카테고리별 정답률 통계 계산
    stats = {}
    for att in history["attempts"]:
        cat = att["category"]
        is_correct = att["is_correct"]
        if cat not in stats:
            stats[cat] = {"total": 0, "correct": 0}
        stats[cat]["total"] += 1
        if is_correct:
            stats[cat]["correct"] += 1

    # 최저 정답률 단원 추출
    weakest_cat = None
    min_rate = 1.0
    for cat, data in stats.items():
        rate = data["correct"] / data["total"]
        # 정답률이 100%보다 낮고 최저점인 카테고리를 찾음
        if rate < min_rate:
            min_rate = rate
            weakest_cat = cat

    return weakest_cat, min_rate, stats

def print_weakness_remedy(weakest_cat, rate):
    """
    [설계 의도]
    검출된 취약점 단원에 대해, 해당 영역의 세부 공부 목차와 수험 핵심 조언을 
    RAG 형태로 보강 처방하여 사용자가 취약 영역을 바로 눈으로 극복하게 돕습니다.
    """
    print("\n" + "=" * 55)
    print("  [수험 취약점 긴급 분석 보고서 및 맞춤 학습 처방]  ")
    print("=" * 55)
    print(f"* 진단된 취약 대단원: {weakest_cat}")
    print(f"* 해당 단원 누적 정답률: {rate*100:.1f}% (보강 점검 요망)")
    print("-" * 55)
    
    # SE.txt에서 해당 단원의 세부 범위 발췌
    scope_details = ""
    if os.path.exists(SE_SCOPE_PATH):
        try:
            with open(SE_SCOPE_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                in_target = False
                for line in lines:
                    if line.strip().startswith(weakest_cat):
                        in_target = True
                        scope_details += line
                        continue
                    # 다음 번호 대단원이 시작되면 중단
                    if in_target and re.match(r"^\d+\.", line.strip()):
                        break
                    if in_target:
                        scope_details += line
        except Exception:
            pass

    if scope_details:
        print("[출제 기준에 명시된 취약 단원 세부 목차]")
        print(scope_details.strip())
        print("-" * 55)
        
    print("[에이전트 처방 수험 전략 가이드]")
    if "1." in weakest_cat:
        print("  - 요구사항 도출/분석/명세/추적의 일관성 및 역추적성에 관한 개념이 자주 나옵니다.")
        print("  - UML 2.0 구조 중 시퀀스/커뮤니케이션 다이어그램의 정적/동적 해석 및 클래스 관계 표현(집약, 합성)을 재학습하세요.")
    elif "2." in weakest_cat:
        print("  - 화이트박스 테스트(문장, 분기, 조건, 조건/결정 커버리지) 연산 문제를 매번 직접 풀어보며 훈련하세요.")
        print("  - ISO/IEC/IEEE 29119 표준에 정의된 테스트 산출물 명칭을 철저하게 분리 숙지해야 합니다.")
    elif "3." in weakest_cat:
        print("  - 형상 통제 위원회(CCB)의 역할 및 형상 베이스라인(물리, 기능, 개발, 할당)의 수립 시점을 구분하세요.")
        print("  - 재공학, 역공학, 리팩토링의 개념적 정의와 차이를 묻는 지문을 정리해 두시기 바랍니다.")
    elif "4." in weakest_cat:
        print("  - 스크럼의 주요 산출물(스프린트 백로그, 소멸 차트) 및 스프린트 계획/리뷰/회고의 성격 차이가 출제됩니다.")
        print("  - MSA 구조에서의 서비스 발견(Discovery) 기법과 전자정부 표준 프레임워크 최신 환경 특성을 암기하십시오.")
    elif "5." in weakest_cat:
        print("  - 기능점수(FP) 간이법/상세법의 차이와 데이터 기능점수(ILF, EIF), 트랜잭션 기능점수(EI, EO, EQ)를 구분해 계산하는 연습이 시급합니다.")
        print("  - ISO/IEC 25010 제품 품질 모델 8대 주특성과 30여 개 부특성의 매핑 맵을 암기해 과락을 대비하세요.")
    print("=" * 55)

# ==========================================
# 5. 메인 REPL 퀴즈 루너
# ==========================================

def main():
    print("=" * 60)
    print("  [Jolly-Carson 소프트웨어공학 예상문제 퀴즈 및 오답 진단기]  ")
    print("=" * 60)
    print("  - 출제 기준: 최신 감리사 시험 범위 및 빈출 기출 가이드 반영")
    if GEMINI_API_KEY:
        print("  - 출제 모드: 실시간 AI 지능형 다이나믹 출제 모드 가동")
    else:
        print("  - 출제 모드: 로컬 준비 고품질 예상문제 모드 가동 (환경변수 키 없음)")
    print("=" * 60)

    # 1단계: 문제 세트 획득
    print("\n* 소프트웨어공학(SE) 예상문제를 생성/로딩하는 중입니다...")
    if GEMINI_API_KEY:
        quizzes = generate_quizzes_via_llm()
    else:
        quizzes = MOCK_QUIZZES
        
    print(f"-> 총 {len(quizzes)}개의 예상문제 출제가 완료되었습니다. 문제를 시작합니다.")
    
    new_attempts = []
    
    # 2단계: 퀴즈 풀이 진행 (이모지 완전 배제 처리)
    for idx, qz in enumerate(quizzes, 1):
        print(f"\n[문제 {idx}/5] (영역: {qz['category']})")
        print(f"문 제: {qz['question']}")
        print("\n[선택지]")
        for opt in qz["options"]:
            print(opt)
            
        user_ans = None
        while True:
            try:
                ans_str = input("\n>> 정답 입력 (1~4번 중 선택): ").strip()
                if ans_str in ["1", "2", "3", "4"]:
                    user_ans = int(ans_str)
                    break
                else:
                    print("[주의] 1, 2, 3, 4번 중 하나만 입력해 주세요.")
            except (KeyboardInterrupt, EOFError):
                print("\n퀴즈를 강제 종료하고 이전까지 기록된 결과만 분석합니다.")
                break
                
        if user_ans is None:
            break
            
        is_correct = (user_ans == qz["answer"])
        new_attempts.append({
            "quiz_id": qz.get("id", f"SE_AUTO_{idx}"),
            "category": qz["category"],
            "user_answer": user_ans,
            "is_correct": is_correct,
            "timestamp": datetime.now().isoformat()
        })
        
        if is_correct:
            print("\n[결과: 정답입니다!]")
        else:
            print(f"\n[결과: 오답입니다!] (실제 정답: {qz['answer']}번)")
            
        print("[문제 해설]")
        print(qz["explanation"])
        print("-" * 50)
        
    # 3단계: 채점 및 약점 진단
    if not new_attempts:
        print("\n풀이 내역이 없어 분석을 종료합니다.")
        return
        
    correct_count = sum(1 for att in new_attempts if att["is_correct"])
    print(f"\n* 퀴즈 완료: {len(new_attempts)}문항 중 {correct_count}문항을 맞추셨습니다.")
    
    # 누적 기록 및 분석
    weakest_cat, min_rate, stats = save_and_analyze_quiz(new_attempts)
    
    # 전체 누적 통계 출력
    print("\n[단원별 누적 학습 현황 통계]")
    for cat, stat in stats.items():
        rate = stat["correct"] / stat["total"]
        print(f" - {cat}: {stat['correct']}/{stat['total']}개 맞춤 (정답률 {rate*100:.1f}%)")
        
    # 처방 보고서 출력
    if weakest_cat and min_rate < 1.0:
        print_weakness_remedy(weakest_cat, min_rate)
    else:
        print("\n[축하합니다] 모든 단원 정답률이 100%입니다. 완벽한 대비 상태입니다!")
        
    print("\n모든 예상문제 세션이 완료되었습니다. 고생하셨습니다.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n퀴즈가 중단되었습니다.")
        sys.exit(0)
