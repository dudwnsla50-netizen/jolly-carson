# -*- coding: utf-8 -*-
import sys
import os
import json
import traceback

# e:\jolly-carson 폴더를 path에 추가하여 server.py의 설정을 참조할 수 있게 합니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 로컬 방화벽으로 인한 원격 PostgreSQL 연결 오류를 방지하기 위해 SQLite 모드로 강제 설정
os.environ["USE_SQLITE"] = "true"

from server import get_db_connection, get_db_cursor, execute_query, GEMINI_API_KEY, call_gemini_raw_prompt, DB_TYPE

def test_integration():
    print(f"DB 유형: {DB_TYPE}")
    print(f"API Key 존재 여부: {bool(GEMINI_API_KEY)}")
    if not GEMINI_API_KEY:
        print("경고: GEMINI_API_KEY가 없습니다. 검증은 폴백 로직으로 가동됩니다.")

    try:
        with get_db_connection() as conn:
            with get_db_cursor(conn) as cursor:
                # 1. 가장 최신의 이력 id 조회
                sql = "SELECT id, exam_year, score, correct_count, total_questions, total_time, details FROM yearly_exam_history ORDER BY id DESC LIMIT 1"
                execute_query(cursor, sql)
                row = cursor.fetchone()
                
                if not row:
                    print("오류: 데이터베이스에 시험 이력이 존재하지 않습니다. 모의고사 제출을 먼저 진행해야 합니다.")
                    return
                
                row_dict = dict(row)
                history_id = row_dict["id"]
                exam_year = row_dict["exam_year"]
                score = row_dict["score"]
                correct_count = row_dict["correct_count"]
                total_questions = row_dict["total_questions"]
                total_time = row_dict.get("total_time", 0) or 0
                details_raw = row_dict["details"]
                
                print(f"\n[성공] 이력 조회 완료: ID={history_id}, 연도={exam_year}, 점수={score}, 총 소요 시간={total_time}초")
                
                details = []
                if details_raw:
                    details = json.loads(details_raw) if isinstance(details_raw, str) else details_raw

                # 과목별 풀이 소요 시간 및 병목/오답 문항 상세 분석 가공
                subject_times = {'PM': [], 'SE': [], 'DB': [], 'SA': [], 'SC': []}
                target_q_nums = []
                
                if details:
                    for item in details:
                        q_num = item.get("question_num")
                        elapsed = item.get("elapsed_time", 0)
                        is_corr = item.get("is_correct", False)
                        
                        if q_num is not None:
                            sub = None
                            if 1 <= q_num <= 25: sub = 'PM'
                            elif 26 <= q_num <= 50: sub = 'SE'
                            elif 51 <= q_num <= 75: sub = 'DB'
                            elif 76 <= q_num <= 100: sub = 'SA'
                            elif 101 <= q_num <= 120: sub = 'SC'
                            
                            if sub and elapsed is not None:
                                subject_times[sub].append(elapsed)
                                
                            if not is_corr or (elapsed and elapsed >= 90):
                                target_q_nums.append(q_num)
                                
                subject_avg_times = {}
                for sub, times in subject_times.items():
                    if times:
                        subject_avg_times[sub] = round(sum(times) / len(times), 1)
                    else:
                        subject_avg_times[sub] = 0.0
                        
                print(f"과목별 평균 풀이 소요 시간: {subject_avg_times}")
                print(f"오답 및 고민 문항 수 (최대 15개 제한 전): {len(target_q_nums)}")
                
                target_q_nums = target_q_nums[:15]
                detailed_questions = []
                
                if target_q_nums:
                    placeholders = ", ".join(["%s"] * len(target_q_nums))
                    sql_questions = f"""
                        SELECT question_num, subject, question, answer
                        FROM exam_questions
                        WHERE year = %s AND question_num IN ({placeholders})
                        ORDER BY question_num ASC
                    """
                    params = [exam_year] + target_q_nums
                    execute_query(cursor, sql_questions, tuple(params))
                    q_rows = cursor.fetchall()
                    
                    details_map = {item.get("question_num"): item for item in details} if details else {}
                    
                    for q_row in q_rows:
                        q_row_dict = dict(q_row)
                        q_num = q_row_dict["question_num"]
                        item_detail = details_map.get(q_num, {})
                        
                        user_ans = item_detail.get("user_answer", [])
                        elapsed = item_detail.get("elapsed_time", 0)
                        is_corr = item_detail.get("is_correct", False)
                        
                        question_text = q_row_dict["question"]
                        if len(question_text) > 350:
                            question_text = question_text[:350] + "..."
                            
                        raw_ans = q_row_dict["answer"]
                        correct_ans_str = str(raw_ans)
                        
                        detailed_questions.append({
                            "num": q_num,
                            "sub": q_row_dict["subject"],
                            "question": question_text,
                            "correct_answer": correct_ans_str,
                            "user_answer": str(user_ans[0]) if user_ans else "미마킹",
                            "elapsed": elapsed,
                            "is_correct": is_corr
                        })
                
                print(f"조회된 상세 문항 수: {len(detailed_questions)}")
                
                # 프롬프트 조립 테스트
                time_details_str = ""
                for dq in detailed_questions:
                    status_str = "맞춤(시간초과)" if dq["is_correct"] else "오답"
                    time_details_str += f"\n- 문항 {dq['num']}번 (과목: {dq['sub']}) [{status_str}]\n  * 문제 지문: {dq['question']}\n  * 정답: {dq['correct_answer']} / 내 답: {dq['user_answer']}\n  * 풀이 소요 시간: {dq['elapsed']}초"
                
                time_info_prompt = f"""
[시험 소요 시간 및 문제별 상세 분석 데이터]
- 총 시험 소요 시간: {total_time // 60}분 {total_time % 60}초
- 과목별 평균 풀이 소요 시간: PM({subject_avg_times['PM']}초), SE({subject_avg_times['SE']}초), DB({subject_avg_times['DB']}초), SA({subject_avg_times['SA']}초), SC({subject_avg_times['SC']}초)
- 주요 시간 지체(90초 이상) 및 오답 문항 상세 분석 리스트:
{time_details_str if time_details_str else "시간 초과 및 오답 문항이 존재하지 않습니다."}
"""
                print("\n=== 조립된 시간 및 오답 정보 프롬프트 ===")
                print(time_info_prompt)
                
                # API 호출 테스트
                if GEMINI_API_KEY:
                    print("\n[AI API 호출 시도 중...]")
                    prompt = f"""
당신은 대한민국 최고 수준의 '정보시스템 감리사 자격검정 수험 진단 시스템'입니다.
수험생이 치른 {exam_year}년도 모의고사 성적표, 그리고 문제별 풀이 소요 시간과 오답 상세 내역 데이터를 바탕으로, 냉철하고 실질적인 학습 취약점 진단서와 시간 안배 및 시간 부족 극복을 위한 추천 가이드를 작성해 주세요.

[시험 결과 요약]
- 총 문항 수: {total_questions}문항 중 {correct_count}문항 정답 (맞춤 환산 점수: {score}점)

{time_info_prompt}

[출력 요구사항]
1. 반드시 아래의 JSON 포맷 형식을 정확히 준수하여 응답하세요.
2. 백틱 기호(```json)나 여타 텍스트(설명글 등)를 절대 덧붙이지 마십시오. 순수 JSON 텍스트만 출력해야 합니다.
3. 'desc'는 수험생의 학습 패턴, 약점 단원, 일반 기출 대비 신규 기술 영역에서의 취약성과 더불어 **각 문제별 소요 시간을 종합 분석한 시간 부족 원인(특정 과목/단원에서의 지체 현상, 정답 추론 과정에서의 불필요한 생각의 지체 등) 및 실전 시간 배분 현황**을 4~5줄 분량의 예리한 분석글로 짚어내야 합니다. (한국어로 격식 있는 조언 투)
4. 'recommendation'은 향후 어떤 가이드나 과목을 어떻게 회독해야 하는지뿐 아니라 **실전 시험 시간 부족을 극복하기 위해 문제를 포기하거나 넘기는 타이밍, 문항당 적정 시간 사수법 등 구체적인 시간 안배 행동 지침**을 2~3줄 분량의 구체적인 조언으로 처방해야 합니다.
5. 오직 실제로 시험을 치른 과목(문항 수(분모)가 0보다 큰 과목)들에 대해서만 데이터 분석과 처방을 작성하세요.

최종 JSON 응답:"""
                    raw_res = call_gemini_raw_prompt(prompt)
                    print("\n=== AI 최종 수신 결과 ===")
                    print(raw_res)
                    
                    # JSON 파싱 검증
                    raw_res_clean = raw_res.strip()
                    if raw_res_clean.startswith("```"):
                        lines = raw_res_clean.split("\n")
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines[-1].startswith("```"):
                            lines = lines[:-1]
                        raw_res_clean = "\n".join(lines).strip()
                    
                    parsed = json.loads(raw_res_clean)
                    print("\n[성공] JSON 파싱 성공!")
                    print(f"진단내용 (desc): {parsed.get('desc')}")
                    print(f"추천 가이드 (recommendation): {parsed.get('recommendation')}")
                else:
                    print("\n[안내] API Key가 설정되지 않아 실제 AI 호출 검증은 건너뜁니다.")
    except Exception as e:
        print(f"\n[오류 발생] 검증 중 에러: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_integration()
