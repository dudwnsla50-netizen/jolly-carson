import os
import sys
import re

# extract_questions_v2가 있는 scratch 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extract_questions_v2 import reconstruct_exam_text, parse_sequential_questions, HTML_NAMES

def main():
    html_dir = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html"
    js_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_database.js"
    
    db_data = {}
    
    # 2015~2026 각 연도에 대해 지문 추출
    for y in sorted(HTML_NAMES.keys()):
        html_path = os.path.join(html_dir, HTML_NAMES[y])
        if os.path.exists(html_path):
            print(f"{y}년 기출문제 추출 중...")
            text = reconstruct_exam_text(html_path, year=y)
            qs = parse_sequential_questions(text)
            
            # 1~120번 문항을 db_data에 매핑
            for num in range(1, 121):
                key = f"{y}_{num}"
                val = qs.get(num, "").strip()
                if not val or val == f"{num} -":
                    # 혹시 비어있거나 누락된 번호가 있다면 placeholder 설정
                    val = f"{num} -"
                db_data[key] = val
        else:
            print(f"파일 없음: {HTML_NAMES[y]}")
            
    # javascript 형식 포맷팅
    formatted_pairs = []
    sorted_keys = sorted(db_data.keys(), key=lambda x: (int(x.split("_")[0]), int(x.split("_")[1])))
    
    for key in sorted_keys:
        val = db_data[key]
        # 백슬래시, 큰따옴표, 줄바꿈 이스케이프 처리
        escaped_val = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
        formatted_pairs.append(f'  "{key}": "{escaped_val}"')
        
    new_js_content = "const examDatabase = {\n" + ",\n".join(formatted_pairs) + "\n};\n"
    
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(new_js_content)
        
    print(f"\n성공적으로 {len(db_data)}개 문항 데이터베이스 반영 완료.")

if __name__ == "__main__":
    main()
