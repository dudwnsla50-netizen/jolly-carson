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
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'div' and 'class' in attrs_dict and attrs_dict['class'] == 'page-wrapper':
            self.current_page = []
            self.pages.append(self.current_page)
            
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
            
    def handle_data(self, data):
        if self.in_p and self.current_p is not None:
            self.current_p['text'] += data

# Layout configs for each year
LAYOUT_CONFIGS = {
    2015: {"cols": 2, "left_ranges": [(50.0, 65.0), (365.0, 385.0)], "bottom": 1000.0},
    2016: {"cols": 2, "left_ranges": [(44.0, 52.0), (304.0, 311.0)], "bottom": 1000.0},
    2017: {"cols": 2, "left_ranges": [(44.0, 52.0), (304.0, 311.0)], "bottom": 1000.0},
    2018: {"cols": 2, "left_ranges": [(44.0, 52.0), (304.0, 311.0)], "bottom": 1000.0},
    2019: {"cols": 2, "left_ranges": [(44.0, 55.0), (304.0, 311.0)], "bottom": 1000.0},
    2020: {"cols": 2, "left_ranges": [(54.0, 65.0), (370.0, 385.0)], "bottom": 1000.0},
    2021: {"cols": 2, "left_ranges": [(54.0, 65.0), (370.0, 385.0)], "bottom": 1000.0},
    2022: {"cols": 2, "left_ranges": [(54.0, 65.0), (370.0, 385.0)], "bottom": 1000.0},
    2023: {"cols": 2, "left_ranges": [(54.0, 65.0), (370.0, 385.0)], "bottom": 1000.0},
    2024: {"cols": 2, "left_ranges": [(44.0, 52.0), (304.0, 311.0)], "bottom": 1000.0},
    2025: {"cols": 4, "left_ranges": [(31.0, 36.0), (215.0, 221.0), (451.0, 457.0), (636.0, 642.0)], "bottom": 550.0},
    2026: {"cols": 2, "left_ranges": [(44.0, 52.0), (304.0, 311.0)], "bottom": 1000.0}
}

HTML_NAMES = {
    2015: "2015년(제16회) 정보시스템감리사 필기시험문제(답안).html",
    2016: "2016년(제17회) 정보시스템 감리사 필기시험 문제 및 답안.html",
    2017: "2017년(제18회) 정보시스템 감리사 필기시험 문제 및 답안.html",
    2018: "2018년(제19회)정보시스템 감리사 필기시험 문제 및 답안.html",
    2019: "2019년(제20회)정보시스템 감리사 필기시험 문제 및 답안.html",
    2020: "2020년(제21회) 정보시스템 감리사 필기시험 문제 및 답안.html",
    2021: "2021년(제22회) 정보시스템 감리사 필기시험 문제 및 답안.html",
    2022: "2022년(제23회) 정보시스템 감리사 필기시험 문제 및 답안.html",
    2023: "2023년 정보시스템 감리사 자격검정 필기시험 문제 A형(답안포함).html",
    2024: "2024년(제25회) 감리사 자격검정 필기시험 문제-A형.html",
    2025: "2025년 감리사 자격검정 필기시험 문제-A형(답포함).html",
    2026: "2026년 감리사 자격검정 필기시험 문제 및 가답안（A형）.html"
}

def is_valid_question_left(left, year):
    config = LAYOUT_CONFIGS.get(year)
    if not config:
        return False
    for low, high in config["left_ranges"]:
        if low <= left <= high:
            return True
    return False

def reconstruct_exam_text(html_path, year):
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    # [방어 코드] Base64 이미지 데이터가 개행 문자를 포함하고 있으므로, 
    # flags=re.DOTALL 및 [\s\S]*? 패턴을 명시하여 모든 <img> 태그를 사전에 완벽하게 제거합니다.
    html_content = re.sub(r'<img[\s\S]*?>', '', html_content, flags=re.DOTALL)
    
    # [방어 코드] C++ 제네릭 코드(예: vector<Course*>)의 꺽쇠 괄호 '<'를 HTMLParser가 태그로 오인하여 
    # 파싱 에러 및 문자열 유실을 일으키는 현상을 원천 방지하기 위해, 진짜 HTML 태그가 아닌 '<'를 '&lt;'로 사전 치환합니다.
    html_content = re.sub(r'<(?!(?:/?(?:p|span|div|html|head|body|style|meta|title|a|button|ul|li|h2|b|i|br|hr|!DOCTYPE)\b))', '&lt;', html_content, flags=re.IGNORECASE)
        
    parser = SimpleHTMLParser()
    parser.feed(html_content)
    
    config = LAYOUT_CONFIGS.get(year)
    if not config:
        raise ValueError(f"No configuration found for year {year}")
        
    page_bottom_limit = config["bottom"]
    is_4_cols = (config["cols"] == 4)
    
    full_text_runs = []
    
    for page_idx, page in enumerate(parser.pages):
        columns = []
        if is_4_cols:
            columns = [[], [], [], []]
            for p in page:
                if p['top'] > page_bottom_limit:
                    continue
                l = p['left']
                if l < 200.0:
                    columns[0].append(p)
                elif l < 410.0:
                    columns[1].append(p)
                elif l < 600.0:
                    columns[2].append(p)
                else:
                    columns[3].append(p)
        else:
            columns = [[], []]
            for p in page:
                if p['top'] > page_bottom_limit:
                    continue
                l = p['left']
                if l < 298.0:
                    columns[0].append(p)
                else:
                    columns[1].append(p)
                    
        page_runs = []
        for col in columns:
            col.sort(key=lambda x: x['top'])
            col_text = ""
            for p in col:
                text_val = p['text'].strip()
                if text_val:
                    m = re.match(r'^(\d+)\s*\.', text_val)
                    if m and is_valid_question_left(p['left'], year):
                        col_text += f"\n[Q_START_{m.group(1)}]\n" + p['text'] + "\n"
                    else:
                        col_text += p['text'] + "\n"
            if col_text.strip():
                page_runs.append(col_text.strip())
                
        full_text_runs.extend(page_runs)
        
    return "\n\n".join(full_text_runs)

def parse_sequential_questions(full_text):
    start_idx = full_text.find("감리 및 사업관리")
    if start_idx != -1:
        full_text = full_text[start_idx:]
        
    questions = {}
    current_num = 1
    current_text = []
    
    lines = full_text.split('\n')
    
    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue
            
        marker_match = re.match(rf'^\[Q_START_({current_num})\]$', cleaned_line)
        
        if marker_match:
            if current_num > 1:
                questions[current_num - 1] = "\n".join(current_text).strip()
            current_text = []
            current_num += 1
        else:
            other_marker = re.match(r'^\[Q_START_(\d+)\]$', cleaned_line)
            if other_marker:
                continue
            if current_num > 1:
                current_text.append(line)
                
    if current_num > 120:
        questions[120] = "\n".join(current_text).strip()
    elif current_num > 1:
        questions[current_num - 1] = "\n".join(current_text).strip()
        
    return questions

def main():
    html_dir = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\html"
    
    for y in sorted(HTML_NAMES.keys()):
        html_path = os.path.join(html_dir, HTML_NAMES[y])
        if os.path.exists(html_path):
            print(f"{y}년 정렬 파싱 중...")
            text = reconstruct_exam_text(html_path, year=y)
            qs = parse_sequential_questions(text)
            print(f"  {y}년 추출된 문제 개수: {len(qs)}")
            missing = [i for i in range(1, 121) if i not in qs]
            if missing:
                print(f"  Warning: 누락된 번호들 (총 {len(missing)}개): {missing}")
            else:
                print(f"  {y}년 누락 없음 (120문항 완벽 추출)")
        else:
            print(f"파일을 찾을 수 없음: {HTML_NAMES[y]}")

if __name__ == "__main__":
    main()
