# -*- coding: utf-8 -*-
"""
GitHub 원격 jolly_carson.db의 기출문제 및 맵핑 데이터만 로컬로 안전하게 병합하는 스크립트입니다.
로컬에 기록된 학습 이력(누적 EXP, 오답노트 로그)은 전혀 손상시키지 않고 보존합니다.
"""
import os
import sys
import urllib.request
import sqlite3

def main():
    remote_url = "https://raw.githubusercontent.com/dudwnsla50-netizen/jolly-carson/master/reports/exam_db/jolly_carson.db"
    temp_db_path = "reports/exam_db/jolly_carson_remote.db"
    local_db_path = "reports/exam_db/jolly_carson.db"

    # UTF-8 출력 보장
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    if not os.path.exists(local_db_path):
        print(f"[오류] 로컬 데이터베이스를 찾을 수 없습니다: {local_db_path}")
        return

    print("🔄 1. GitHub 원격 저장소에서 최신 DB 다운로드 중...")
    try:
        # User-Agent 추가하여 다운로드 차단 우회
        req = urllib.request.Request(
            remote_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            with open(temp_db_path, 'wb') as out_file:
                out_file.write(response.read())
        print("✅ 다운로드 성공!")
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}")
        return

    print("🔄 2. 기출문제 데이터 병합 시작 (로컬 학습 이력 보존)...")
    conn = None
    try:
        conn = sqlite3.connect(local_db_path)
        cursor = conn.cursor()

        # 원격 임시 DB 연결
        cursor.execute(f"ATTACH DATABASE '{temp_db_path}' AS remote_db")

        # 1) 기출문제 덮어쓰기 (INSERT OR REPLACE)
        print(" - 기출문제 테이블(exam_questions) 동기화 중...")
        cursor.execute("INSERT OR REPLACE INTO exam_questions SELECT * FROM remote_db.exam_questions")

        # 2) 대시보드 대단원/소단원 매핑 정보 덮어쓰기
        print(" - 대시보드 맵핑 테이블(dashboard_mappings) 동기화 중...")
        cursor.execute("INSERT OR REPLACE INTO dashboard_mappings SELECT * FROM remote_db.dashboard_mappings")

        conn.commit()
        print("🎉 병합 완료! 기출문제 본문 및 대시보드 구조가 최신 데이터로 업데이트되었습니다.")

    except Exception as e:
        print(f"❌ 병합 오류 발생: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
        # 임시 원격 DB 파일 제거
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
                print("🧹 임시 다운로드 파일 정리 완료.")
            except Exception as ex:
                print(f"[경고] 임시 파일 제거 실패: {ex}")

if __name__ == "__main__":
    main()
