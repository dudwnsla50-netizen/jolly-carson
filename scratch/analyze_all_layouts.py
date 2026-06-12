# -*- coding: utf-8 -*-
import os
import re
from html.parser import HTMLParser

class SimpleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pages = []
        self.current_page = None
        self.current_p = None
        self.in_p = False
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'div' and attrs_dict.get('class') == 'page-wrapper':
            self.current_page = []
            self.pages.append(self.current_page)
        elif tag == 'p':
            self.in_p = True
            style = attrs_dict.get('style', '')
            top_m = re.search(r'top:\s*([\d\.]+)pt', style)
            left_m = re.search(r'left:\s*([\d\.]+)pt', style)
            self.current_p = {
                'top': float(top_m.group(1)) if top_m else 0.0,
                'left': float(left_m.group(1)) if left_m else 0.0,
                'text': ''
            }
            if self.current_page is not None:
                self.current_page.append(self.current_p)
                
    def handle_endtag(self, tag):
        if tag == 'p':
            self.in_p = False
            self.current_p = None
            
    def handle_data(self, data):
        if self.in_p and self.current_p is not None:
            self.current_p['text'] += data

def analyze_html_file(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    parser = SimpleHTMLParser()
    parser.feed(content)
    
    # We find all paragraphs starting with a number between 1 and 120
    # and look at their 'left' coordinate distribution.
    left_coords = []
    for page in parser.pages:
        for p in page:
            if p['top'] > 780.0:  # skip footer
                continue
            text_val = p['text'].strip()
            m = re.match(r'^\s*(\d+)\s*\.', text_val)
            if m:
                num = int(m.group(1))
                if 1 <= num <= 120:
                    left_coords.append(p['left'])
                    
    # Basic statistical analysis to find clusters of left coordinates
    # We round to nearest integer to group them
    from collections import Counter
    counts = Counter([round(x) for x in left_coords])
    
    # Sort by frequency, print top coordinates
    top_coords = sorted([coord for coord, count in counts.items() if count >= 3])
    
    # Let's decide if 4 columns or 2 columns based on coordinate clusters
    col_count = 2
    if len(top_coords) >= 4:
        # Check if they span across larger values
        # e.g., if there's a cluster near 600, it's likely 4 columns
        if any(c > 500 for c in top_coords):
            col_count = 4
            
    print(f"File: {os.path.basename(html_path)}")
    print(f"  Top left coordinates detected: {top_coords}")
    print(f"  Detected Column Count: {col_count}")
    return top_coords, col_count

def main():
    html_dir = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html"
    files = [
        "2016년(제17회) 정보시스템 감리사 필기시험 문제 및 답안.html",
        "2017년(제18회) 정보시스템 감리사 필기시험 문제 및 답안.html",
        "2018년(제19회)정보시스템 감리사 필기시험 문제 및 답안.html",
        "2019년(제20회)정보시스템 감리사 필기시험 문제 및 답안.html",
        "2020년(제21회) 정보시스템 감리사 필기시험 문제 및 답안.html",
        "2021년(제22회) 정보시스템 감리사 필기시험 문제 및 답안.html",
        "2022년(제23회) 정보시스템 감리사 필기시험 문제 및 답안.html",
        "2023년 정보시스템 감리사 자격검정 필기시험 문제 A형(답안포함).html",
        "2024년(제25회) 감리사 자격검정 필기시험 문제-A형.html"
    ]
    
    for f in files:
        path = os.path.join(html_dir, f)
        if os.path.exists(path):
            analyze_html_file(path)
        else:
            print(f"File not found: {f}")

if __name__ == "__main__":
    main()
