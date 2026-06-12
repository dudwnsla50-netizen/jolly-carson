import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from extract_questions_v2 import reconstruct_exam_text, parse_sequential_questions

def main():
    html_dir = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html"
    html_path = os.path.join(html_dir, "2015년(제16회) 정보시스템감리사 필기시험문제(답안).html")
    
    text = reconstruct_exam_text(html_path, year=2015)
    qs = parse_sequential_questions(text)
    
    print(f"2015년 총 추출 문제 수: {len(qs)}")
    for i in range(1, 6):
        if i in qs:
            print(f"\n--- {i}번 문제 ---")
            print(qs[i])

if __name__ == "__main__":
    main()
