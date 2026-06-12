# -*- coding: utf-8 -*-
"""
[10종 대시보드 일괄 리빌더 스크립트]
- 목적: 10개 과목별(빈출순 5종, 공식범위순 5종) 대시보드 빌더 스크립트를
  순차적으로 일괄 구동하여 reports 폴더 내 HTML을 재생성합니다.
"""
import subprocess
import sys
import os

BUILDERS = [
    "build_premium_db_viewer.py",
    "build_premium_db_official_viewer.py",
    "build_premium_pm_viewer.py",
    "build_premium_pm_official_viewer.py",
    "build_premium_se_viewer.py",
    "build_premium_se_official_viewer.py",
    "build_premium_sa_viewer.py",
    "build_premium_sa_official_viewer.py",
    "build_premium_sc_viewer.py",
    "build_premium_sc_official_viewer.py"
]

def main():
    print("=== [시작] Jolly-Carson 10종 대시보드 일괄 리빌드 ===")
    
    # 한글 출력 인코딩 설정
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    success_count = 0
    for builder in BUILDERS:
        print(f"\n👉 [{builder}] 빌더 구동 중...")
        try:
            # subprocess를 이용하여 빌더를 실행합니다.
            result = subprocess.run(
                [sys.executable, builder],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True
            )
            print(result.stdout)
            print(f"✅ {builder} 빌드 성공")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"❌ {builder} 빌드 실패!")
            print(e.stderr)
        except Exception as e:
            print(f"❌ {builder} 실행 중 예외 발생: {e}")
            
    print(f"\n=== [완료] 전체 {len(BUILDERS)}개 중 {success_count}개 빌드 성공 ===")

if __name__ == "__main__":
    main()
