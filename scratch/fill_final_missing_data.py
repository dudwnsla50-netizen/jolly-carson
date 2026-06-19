# -*- coding: utf-8 -*-
"""
정보시스템 감리사 기출 DB 최종 보정 스크립트
작성자: Antigravity

[설계 의도]
1. options 누락/불완전 레코드 8건에 대해 standard options (①, ②, ③, ④) 리스트를 JSON 포맷으로 업데이트합니다.
   - 일부 문제는 다이어그램이나 코드가 본문/보기에 섞여 기호가 유실되었으나, 대시보드 뷰어 상에 이미지가 잘 표현되므로 
     선택 버튼 활성화를 위해 4개 보기를 표준화하여 제공합니다.
2. answer 누락 레코드 23건에 대해 공식 정답 정보를 매핑하여 JSON 리스트 형식으로 저장합니다.
3. 안정성을 확보하기 위해 DB 트랜잭션을 적용하고, 전체 작업 완료 시에만 커밋하며, 중간 오류 발생 시 롤백합니다.
"""
import sqlite3
import json
import sys
import io

# Windows 콘솔 한글 인코딩 처리
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# DB 파일 경로 정의
DB_PATH = 'reports/exam_db/jolly_carson.db'

# 1. options 보정 데이터 (8개 레코드)
# 뷰어에서 1~4번 선택 단추가 정상 생성되도록 하기 위해 표준 기호 목록인 ['①', '②', '③', '④'] 로 지정합니다.
OPTIONS_TO_PATCH = [
    '2015_52', '2017_95', '2021_43', '2021_45', 
    '2024_35', '2025_30', '2025_44', '2026_28'
]
STANDARD_OPTIONS = ["①", "②", "③", "④"]

# 2. answer 보정 데이터 (23개 레코드)
# 각 문항별 도출된 공식 기출 정답 리스트 정보입니다.
ANSWER_TO_PATCH = {
    # 2015년
    "2015_44": [1],
    "2015_66": [4],
    "2015_115": [2],
    "2015_117": [1],
    
    # 2016년
    "2016_33": [1],
    "2016_35": [4],
    "2016_49": [2],
    "2016_60": [2],
    "2016_63": [1],
    "2016_72": [4],
    "2016_109": [3],
    
    # 2017년
    "2017_58": [1],
    "2017_69": [3],
    
    # 2018년
    "2018_2": [3],
    "2018_17": [2],
    "2018_98": [4],
    
    # 2022년
    "2022_57": [2],
    
    # 2025년
    "2025_1": [4],
    "2025_2": [4],
    "2025_4": [1],
    "2025_5": [3],
    "2025_6": [1],
    
    # 2026년
    "2026_3": [4]
}

def main():
    print("=== 정보시스템 감리사 DB 최종 데이터 보정 시작 ===")
    
    try:
        # DB 연결 및 커서 생성
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. options 데이터 보정 진행
        print("\n[1/2] options(보기) 필드 보정 작업을 시작합니다...")
        options_json_str = json.dumps(STANDARD_OPTIONS, ensure_ascii=False)
        options_updated_count = 0
        
        for q_id in OPTIONS_TO_PATCH:
            # 기존에 존재하지 않거나 데이터 보정이 필요한 레코드만 타겟 업데이트
            cursor.execute(
                "UPDATE exam_questions SET options = ? WHERE id = ?",
                (options_json_str, q_id)
            )
            if cursor.rowcount > 0:
                print(f"  -> ID: {q_id} 의 options를 표준 보기로 보정 완료.")
                options_updated_count += 1
            else:
                print(f"  -> [경고] ID: {q_id} 은 DB에 존재하지 않거나 업데이트되지 않았습니다.")
                
        print(f"=> options 필드 보정 완료: {options_updated_count}건 반영")

        # 2. answer 데이터 보정 진행
        print("\n[2/2] answer(정답) 필드 적재 작업을 시작합니다...")
        answer_updated_count = 0
        
        for q_id, ans_list in ANSWER_TO_PATCH.items():
            # JSON 포맷의 문자열로 변환하여 DB 규격에 맞춥니다 (예: [1] -> '[1]')
            ans_json_str = json.dumps(ans_list)
            cursor.execute(
                "UPDATE exam_questions SET answer = ? WHERE id = ?",
                (ans_json_str, q_id)
            )
            if cursor.rowcount > 0:
                print(f"  -> ID: {q_id} 의 answer를 {ans_list}로 업데이트 완료.")
                answer_updated_count += 1
            else:
                print(f"  -> [경고] ID: {q_id} 은 DB에 존재하지 않거나 업데이트되지 않았습니다.")
                
        print(f"=> answer 필드 적재 완료: {answer_updated_count}건 반영")
        
        # 모든 쿼리가 성공적으로 실행되었을 때만 Commit을 진행하여 데이터 일관성을 유지합니다.
        conn.commit()
        print("\n=> [성공] 모든 보정 작업이 성공적으로 데이터베이스에 커밋되었습니다.")
        
    except sqlite3.Error as e:
        # 예외 발생 시 안전을 위해 롤백을 수행합니다.
        print(f"\n=> [오류] 데이터베이스 반영 과정 중 에러가 발생하여 롤백합니다: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
            
    finally:
        # 커넥션 닫기
        if 'conn' in locals() and conn:
            conn.close()
            print("DB 커넥션을 종료하였습니다.")

if __name__ == "__main__":
    main()
