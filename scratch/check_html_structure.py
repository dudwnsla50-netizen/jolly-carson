# -*- coding: utf-8 -*-
import sys
import re
from html.parser import HTMLParser

class SimpleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.p_tags = []
        self.in_p = False
        self.current_p = None
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'p':
            self.in_p = True
            style = attrs_dict.get('style', '')
            top_m = re.search(r'top:\s*([\d\.]+)pt', style)
            left_m = re.search(r'left:\s*([\d\.]+)pt', style)
            self.current_p = {
                'top': float(top_m.group(1)) if top_m else 0.0,
                'left': float(left_m.group(1)) if left_m else 0.0,
                'text': ''
            }
            self.p_tags.append(self.current_p)
            
    def handle_endtag(self, tag):
        if tag == 'p':
            self.in_p = False
            self.current_p = None
            
    def handle_data(self, data):
        if self.in_p and self.current_p is not None:
            self.current_p['text'] += data

def main():
    html_2015 = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html\2015년(제16회) 정보시스템감리사 필기시험문제(답안).html"
    
    with open(html_2015, 'r', encoding='utf-8') as f:
        content = f.read()
        
    parser = SimpleHTMLParser()
    parser.feed(content)
    
    print("Searching for paragraphs around question 12-16 in 2015...")
    for idx, p in enumerate(parser.p_tags):
        text_val = p['text'].strip()
        # Find 12., 13., 14., 15., 16.
        m = re.match(r'^\s*(12|13|14|15|16)\s*\.', text_val)
        if m:
            print(f"p[{idx}]: left={p['left']} top={p['top']} | text={repr(text_val[:100])}")
            # Print surrounding tags
            start_idx = max(0, idx - 2)
            end_idx = min(len(parser.p_tags), idx + 8)
            for i in range(start_idx, end_idx):
                print(f"  p[{i}]: left={parser.p_tags[i]['left']} top={parser.p_tags[i]['top']} | text={repr(parser.p_tags[i]['text'].strip())}")

if __name__ == "__main__":
    main()
