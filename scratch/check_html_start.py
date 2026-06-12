# -*- coding: utf-8 -*-
import sys
sys.path.append(r"d:\100.lyj\anti_workspace\jolly-carson\scratch")
from extract_questions_v2 import reconstruct_exam_text

def main():
    html_2025 = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html\2025년 감리사 자격검정 필기시험 문제-A형(답포함).html"
    
    print("=== 2025 HTML START ===")
    text_2025 = reconstruct_exam_text(html_2025, is_2025=True)
    lines_2025 = text_2025.split("\n")
    for idx, line in enumerate(lines_2025[:100]):
        print(f"{idx+1}: {line}")

if __name__ == "__main__":
    main()
