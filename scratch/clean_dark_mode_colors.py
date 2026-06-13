# -*- coding: utf-8 -*-
import os
import sys
import re
import json

# 인코딩 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r"d:\100.lyj\anti_workspace\jolly-carson"
SE_DB_JS_PATH = os.path.join(BASE_DIR, "reports", "exam_db", "se_db.js")
SHARED_DB_JS_PATH = os.path.join(BASE_DIR, "reports", "exam_database.js")

def clean_file_colors(js_path):
    if not os.path.exists(js_path):
        print(f"파일을 찾을 수 없습니다: {js_path}")
        return False
        
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 변경 타겟이 되는 블랙 및 어두운 색상 코드 패턴들 및 폰트/위치 인라인 스타일
    replacements = [
        (r'color\s*:\s*#000000', 'color:inherit'),
        (r'color\s*:\s*#191919', 'color:inherit'),
        (r'color\s*:\s*#0c0c0c', 'color:inherit'),
        (r'color\s*:\s*black', 'color:inherit'),
        (r'color\s*:\s*rgb\(\s*0\s*,\s*0\s*,\s*0\s*\)', 'color:inherit'),
        # 인라인 폰트 및 위치 스타일 제거
        (r'font-family\s*:\s*[^;"]+;?', ''),
        (r'font-size\s*:\s*[^;"]+;?', ''),
        (r'top\s*:\s*\d+(\.\d+)?(pt|px|em|rem|%);?', ''),
        (r'left\s*:\s*\d+(\.\d+)?(pt|px|em|rem|%);?', ''),
        (r'line-height\s*:\s*\d+(\.\d+)?(pt|px|em|rem|%);?', '')
    ]
    
    modified_content = content
    total_replaced = 0
    for pattern, repl in replacements:
        # 매치 횟수 카운트
        matches = len(re.findall(pattern, modified_content, re.IGNORECASE))
        if matches > 0:
            modified_content = re.sub(pattern, repl, modified_content, flags=re.IGNORECASE)
            print(f"  - [{js_path}] 패턴 '{pattern}' -> '{repl}' 치환 완료 ({matches}회)")
            total_replaced += matches
            
    if total_replaced > 0:
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(modified_content)
        print(f"✅ [{js_path}] 저장 완료 (총 {total_replaced}개 치환됨)")
        return True
    else:
        print(f"ℹ️ [{js_path}] 치환할 어두운 색상 패턴이 발견되지 않았습니다.")
        return False

def main():
    print("=== [시작] 기출문제 지문 어두운 색상(블랙) 제거 작업 ===")
    
    changed1 = clean_file_colors(SE_DB_JS_PATH)
    changed2 = clean_file_colors(SHARED_DB_JS_PATH)
    
    if changed1 or changed2:
        print("\n데이터베이스 변경이 감지되었습니다. 10종 대시보드를 리빌드합니다...")
        import subprocess
        rebuild_script = os.path.join(BASE_DIR, "rebuild_all_dashboards.py")
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = BASE_DIR
            result = subprocess.run(
                [sys.executable, rebuild_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                cwd=BASE_DIR,
                env=env
            )
            print(result.stdout)
            print("✅ 대시보드 리빌드 완료!")
        except Exception as e:
            print(f"❌ 대시보드 리빌드 중 오류 발생: {e}")
    else:
        print("\n변경 사항이 없어 리빌드를 생략합니다.")

if __name__ == "__main__":
    main()
