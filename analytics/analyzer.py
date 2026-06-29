# -*- coding: utf-8 -*-
# [Jolly-Carson 분석 패키지 - 학습이력 분석 및 예측 추천 코어]
# - 설계 의도:
#   1. DB 연결 객체(conn)와 DB 타입(db_type)을 외부에서 주입받아, SQLite/PostgreSQL 양대 DB 환경에서 정상적으로 작동하도록 쿼리 실행기 구조를 구현합니다.
#   2. 중단원(Concept) 단위로 누적 풀이 수와 정답률을 집계하여 강점(Mastery)과 약점(Weakness)을 판정합니다.
#   3. 선수학습 맵(prerequisites) 정보와 연계하여, 만약 후속 약점 단원이 존재하고 그 선행 단원 역시 이해도가 부족(정답률 60% 미만)하다면
#      선행 단원의 추천 점수(Priority Score)를 끌어올림으로써, 순차적인 학습 로드맵을 자동으로 예측/추천하도록 설계합니다.

import json
from .prerequisites import PREREQUISITE_MAP

def analyze_student_history(conn, db_type="SQLITE"):
    """
    [설계 의도]
    데이터베이스 연결 객체를 이용해 quiz_history 데이터를 전량 파악하고,
    5대 과목별 중단원 단위의 강/약점 진단 및 다음 추천 학습 개념을 산출합니다.
    """
    # 1. DB에서 과목/중단원별 누적 학습 정보 조회
    # SQLite와 PostgreSQL 모두 호환되는 표준 ANSI SQL 그룹화 쿼리를 작성합니다.
    sql = """
        SELECT subject, concept,
               CAST(SUM(total_questions) AS INTEGER) as total_solved,
               CAST(SUM(correct_count) AS INTEGER) as total_correct
        FROM quiz_history
        GROUP BY subject, concept
    """
    
    raw_rows = []
    try:
        cursor = conn.cursor()
        # DB_TYPE이 SQLITE일 때는 %s -> ? 번역이 필요할 수 있으나, 이 쿼리는 파라미터가 없어 그대로 호환됩니다.
        cursor.execute(sql)
        rows = cursor.fetchall()
        for row in rows:
            # Row 데이터를 사전형으로 안전하게 보정 (sqlite3.Row 및 dict 양방향 지원)
            raw_rows.append(dict(row))
        cursor.close()
    except Exception as e:
        print(f"[Analytics Analyzer] 데이터 조회 중 오류 발생: {e}")
        # 오류 발생 시 빈 구조 반환하여 서버 셧다운 방지
        return {"subjects": {}, "error": str(e)}

    # 2. 5대 과목 기본 구조 초기화
    subjects_data = {}
    for sub in ['DB', 'SE', 'PM', 'SA', 'SC']:
        subjects_data[sub] = {
            "concepts": {},      # 각 중단원별 상세 지표
            "strengths": [],     # 강점 토픽 목록
            "weaknesses": [],    # 약점 토픽 목록
            "in_progress": [],   # 진행 중 토픽 목록
            "recommendations": [] # 다음 우선순위 추천 예측 목록
        }

    # 3. 중단원별 정답률 집계 및 1차 분석
    for row in raw_rows:
        sub = row['subject'].upper()
        concept = row['concept']
        solved = row['total_solved'] or 0
        correct = row['total_correct'] or 0
        
        if sub not in subjects_data:
            continue
            
        accuracy = (correct / solved) if solved > 0 else 0.0
        
        # 강점/약점 진단 기준 판단
        if solved >= 3:
            if accuracy >= 0.80:
                status = "STRENGTH"
                subjects_data[sub]["strengths"].append(concept)
            elif accuracy <= 0.50:
                status = "WEAKNESS"
                subjects_data[sub]["weaknesses"].append(concept)
            else:
                status = "IN_PROGRESS"
                subjects_data[sub]["in_progress"].append(concept)
        else:
            status = "IN_PROGRESS"
            subjects_data[sub]["in_progress"].append(concept)
            
        subjects_data[sub]["concepts"][concept] = {
            "solved": solved,
            "correct": correct,
            "accuracy": round(accuracy, 2),
            "status": status
        }

    # 4. 선수학습 및 추천 예측 지수 (Priority Score) 연산 시작
    for sub, sub_info in subjects_data.items():
        concepts = sub_info["concepts"]
        prereqs = PREREQUISITE_MAP.get(sub, {})
        
        # 추천 후보군 수집
        recommendation_candidates = []
        
        for concept, metrics in concepts.items():
            solved = metrics["solved"]
            acc = metrics["accuracy"]
            
            # 기본 추천 우선도 산출 (기본값: 정답률이 낮고, 시도를 한 경우에 초점)
            # 기본식: (1.0 - 정답률) * 10
            base_score = (1.0 - acc) * 10.0
            
            # 선수 학습 보정 로직 가동
            # 만약 해당 단원에 정의된 선행 단어(선수과목)가 존재한다면
            required_prereqs = prereqs.get(concept, [])
            prereq_penalty = 0.0
            
            for pr in required_prereqs:
                # 선행 단어 정보가 DB에 존재하고
                if pr in concepts:
                    pr_metrics = concepts[pr]
                    # 선행 단원의 이해도가 60% 미만(미숙 상태)인 경우
                    if pr_metrics["accuracy"] < 0.60:
                        # 선행 단원이 덜 되었으므로 후행 단어의 학습을 후순위로 미룹니다. (패널티 부여)
                        prereq_penalty += 2.0
                else:
                    # 선행 단어 학습 이력 자체가 아직 아예 없는 경우에도 기본 패널티 부여
                    prereq_penalty += 1.5

            final_score = base_score - prereq_penalty
            # 음수 스코어 방지
            final_score = max(0.1, final_score)
            
            # 만약 이 단어 자체가 다른 단어의 선행 단어인데, 학습자의 이해도가 낮다면?
            # 반대로 가산점을 주어 먼저 해결하게 만듭니다. (부모 노드 개념)
            is_prereq_for_others = False
            for target_concept, parent_list in prereqs.items():
                if concept in parent_list:
                    # 이 개념이 다른 약점 단어의 선수과목인 경우
                    target_metrics = concepts.get(target_concept)
                    if target_metrics and target_metrics["accuracy"] < 0.60:
                        is_prereq_for_others = True
                        break
            
            if is_prereq_for_others:
                final_score += 3.0 # 선수 학습 우선 가산점 추가
                
            recommendation_candidates.append({
                "concept": concept,
                "score": round(final_score, 1),
                "accuracy": int(acc * 100),
                "solved": solved
            })
            
        # 추천 점수가 높은 순서대로 정렬
        recommendation_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        # 추천 이유 메시지 생성기
        for item in recommendation_candidates:
            concept = item["concept"]
            score = item["score"]
            acc = item["accuracy"]
            
            # 해당 토픽이 선행으로 필요했던 후속 토픽들 검색
            dependent_topics = [k for k, v in prereqs.items() if concept in v and concepts.get(k, {}).get("accuracy", 1.0) < 0.60]
            
            if dependent_topics:
                reason = f"이 단원은 [{', '.join(dependent_topics)}] 단원의 핵심 선행 개념입니다. 기초를 먼저 다지는 것이 장기적으로 고득점에 유리합니다."
            elif acc <= 50:
                reason = f"정답률이 {acc}%로 취약한 상태입니다. 기출 오답노트를 다시 복습해 보시는 것을 권장합니다."
            else:
                reason = f"이해도({acc}%)를 조금 더 보강하여 안정적인 합격권 강점 단원으로 격상시킬 수 있는 대상입니다."
                
            sub_info["recommendations"].append({
                "concept": concept,
                "score": score,
                "reason": reason
            })
            
    return {"subjects": subjects_data}

if __name__ == "__main__":
    # 백엔드 모듈 테스트용 목업 객체 구동
    class MockCursor:
        def execute(self, sql): pass
        def fetchall(self):
            return [
                {"subject": "DB", "concept": "1-b. 데이터 모델의 개념, 관계형/객체지향 DB", "total_solved": 5, "total_correct": 2},
                {"subject": "DB", "concept": "1-c. 데이터베이스 설계, 정규화", "total_solved": 4, "total_correct": 1},
                {"subject": "DB", "concept": "2-a. 관계대수", "total_solved": 6, "total_correct": 5},
                {"subject": "SE", "concept": "1-c. 설계원리", "total_solved": 3, "total_correct": 1},
                {"subject": "SE", "concept": "1-f. 설계패턴", "total_solved": 4, "total_correct": 1}
            ]
        def close(self): pass

    class MockConnection:
        def cursor(self):
            return MockCursor()

    print("=== [Analytics Analyzer 로컬 유닛 테스트 수행] ===")
    test_conn = MockConnection()
    res = analyze_student_history(test_conn, "SQLITE")
    print(json.dumps(res, indent=2, ensure_ascii=False))
