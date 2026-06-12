# -*- coding: utf-8 -*-
import os
import re
from html.parser import HTMLParser

class StyleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.left_coords = []
        self.current_style = ''
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'p':
            style = attrs_dict.get('style', '')
            left_m = re.search(r'left:\s*([\d\.]+)pt', style)
            if left_m:
                self.left_coords.append(float(left_m.group(1)))

def analyze_file(file_path):
    if not os.path.exists(file_path):
        print(f"파일 없음: {file_path}")
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    parser = StyleParser()
    parser.feed(html)
    
    coords = sorted(parser.left_coords)
    print(f"\n파일: {os.path.basename(file_path)}")
    print(f"총 p 태그 수: {len(coords)}")
    if not coords:
        return
        
    # 분포 분석
    # 간단히 10단위 또는 50단위로 그룹화
    bins = {}
    for c in coords:
        b = int(c // 20) * 20
        bins[b] = bins.get(b, 0) + 1
        
    print("left 좌표 분포 (20pt 단위):")
    for b in sorted(bins.keys()):
        print(f"  {b:3d} ~ {b+20:3d} pt: {bins[b]:4d}개")

def main():
    html_2025 = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html\2025년 감리사 자격검정 필기시험 문제-A형(답포함).html"
    html_2026 = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html\2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.html"
    
    analyze_file(html_2025)
    analyze_file(html_2026)

if __name__ == "__main__":
    main()
