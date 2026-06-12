# -*- coding: utf-8 -*-
import os
import re
from html.parser import HTMLParser

class SimpleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pages = []  # list of pages, each page is a list of p-tags (dict)
        self.current_page = None
        self.current_p = None
        self.in_p = False
        self.in_div = False
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # Check if we are entering a page division
        if tag == 'div' and 'class' in attrs_dict and attrs_dict['class'] == 'page-wrapper':
            self.current_page = []
            self.pages.append(self.current_page)
            self.in_div = True
            
        elif tag == 'p':
            self.in_p = True
            style = attrs_dict.get('style', '')
            top_m = re.search(r'top:\s*([\d\.]+)pt', style)
            left_m = re.search(r'left:\s*([\d\.]+)pt', style)
            
            top_val = float(top_m.group(1)) if top_m else 0.0
            left_val = float(left_m.group(1)) if left_m else 0.0
            
            self.current_p = {
                'top': top_val,
                'left': left_val,
                'text': ''
            }
            if self.current_page is not None:
                self.current_page.append(self.current_p)
                
    def handle_endtag(self, tag):
        if tag == 'p':
            self.in_p = False
            self.current_p = None
        elif tag == 'div':
            self.in_div = False
            
    def handle_data(self, data):
        if self.in_p and self.current_p is not None:
            self.current_p['text'] += data

def clean_text(text):
    # Remove excessive spaces and clean up
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def reconstruct_exam(html_path, is_2025=True):
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    parser = SimpleHTMLParser()
    parser.feed(html_content)
    
    threshold = 420.5 if is_2025 else 297.5
    page_bottom_limit = 550.0 if is_2025 else 780.0
    
    exam_text = ""
    
    for page_idx, page in enumerate(parser.pages):
        left_col = []
        right_col = []
        
        for p in page:
            # Skip page numbers at the very bottom
            if p['top'] > page_bottom_limit and abs(p['left'] - (200.0 if is_2025 else 287.0)) < 50.0:
                continue
            if p['top'] > page_bottom_limit and "- " in p['text']:
                continue
                
            text_val = p['text'].strip()
            if not text_val:
                continue
                
            if p['left'] < threshold:
                left_col.append(p)
            else:
                right_col.append(p)
                
        # Sort by top coordinate (ascending)
        left_col.sort(key=lambda x: x['top'])
        right_col.sort(key=lambda x: x['top'])
        
        # Merge text
        left_text = "\n".join([p['text'] for p in left_col])
        right_text = "\n".join([p['text'] for p in right_col])
        
        exam_text += f"\n=== PAGE {page_idx + 1} ===\n"
        if left_text:
            exam_text += left_text + "\n"
        if right_text:
            exam_text += right_text + "\n"
            
    return exam_text

def extract_questions(exam_text):
    # Split questions by number format (e.g. 1. or 110.)
    # Match lines starting with a number followed by a dot
    lines = exam_text.split('\n')
    questions = {}
    current_q_num = None
    current_q_text = []
    
    for line in lines:
        match = re.match(r'^\s*(\d+)\s*\.\s*(.*)', line)
        if match:
            if current_q_num is not None:
                questions[current_q_num] = "\n".join(current_q_text).strip()
            current_q_num = int(match.group(1))
            current_q_text = [str(current_q_num) + ". " + match.group(2)]
        else:
            if current_q_num is not None:
                # Skip PAGE markers
                if not re.match(r'^=== PAGE \d+ ===', line):
                    current_q_text.append(line)
                    
    if current_q_num is not None:
        questions[current_q_num] = "\n".join(current_q_text).strip()
        
    return questions

def main():
    html_2025 = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html\2025년 감리사 자격검정 필기시험 문제-A형(답포함).html"
    html_2026 = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html\2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.html"
    
    print("2025년 문제 추출 중...")
    text_2025 = reconstruct_exam(html_2025, is_2025=True)
    qs_2025 = extract_questions(text_2025)
    print(f"2025년 추출된 문제 개수: {len(qs_2025)}")
    
    print("2026년 문제 추출 중...")
    text_2026 = reconstruct_exam(html_2026, is_2025=False)
    qs_2026 = extract_questions(text_2026)
    print(f"2026년 추출된 문제 개수: {len(qs_2026)}")
    
    # 임시 출력 파일 저장
    output_path = r"d:\100.lyj\anti_workspace\jolly-carson\scratch\extracted_preview.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=== 2025년 기출문제 맛보기 ===\n")
        for i in sorted(qs_2025.keys())[:5]:
            f.write(f"\n[{i}번]\n{qs_2025[i]}\n")
            
        f.write("\n=== 2026년 기출문제 맛보기 ===\n")
        for i in sorted(qs_2026.keys())[:5]:
            f.write(f"\n[{i}번]\n{qs_2026[i]}\n")
            
    print(f"미리보기가 {output_path}에 저장되었습니다.")

if __name__ == "__main__":
    main()
