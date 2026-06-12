import fitz  # PyMuPDF
from pathlib import Path
import re
import html

def extract_all_questions_for_year(pdf_path):
    pdf_path_obj = Path(pdf_path)
    print(f"[{pdf_path_obj.name}]에서 문제 추출 중...")
    try:
        doc = fitz.open(str(pdf_path_obj))
    except Exception as e:
        print(f"PDF 오픈 실패: {e}")
        return {}

    full_text = ""
    for i, page in enumerate(doc):
        # 1페이지는 표지(수험자 유의사항 등)인 경우 건너뛰기
        if i == 0:
            first_page_text = page.get_text()
            if "유의사항" in first_page_text or "수험번호" in first_page_text:
                pass

        # 한글 엔티티가 안전하게 보존되는 HTML 형식으로 텍스트 추출
        raw_html = page.get_text("html")
        decoded_html = html.unescape(raw_html)

        # <p style="..."> 태그와 그 안의 텍스트 파싱
        p_matches = re.finditer(r'<p\s+style="([^"]+)">(.*?)</p>', decoded_html, re.DOTALL)
        
        blocks = []
        for m in p_matches:
            style_str = m.group(1)
            inner_content = m.group(2)
            
            top_m = re.search(r'top:([\d\.]+)pt', style_str)
            left_m = re.search(r'left:([\d\.]+)pt', style_str)
            
            if top_m and left_m:
                top = float(top_m.group(1))
                left = float(left_m.group(1))
                
                # 내부 HTML 태그를 모두 지우고 순수 텍스트 획득
                clean_text = re.sub(r'<[^>]+>', '', inner_content).strip()
                if clean_text:
                    blocks.append((left, top, clean_text))

        # 2단 분할 정렬
        left_col = []
        right_col = []
        mid_x = page.rect.width / 2

        for left, top, text in blocks:
            if left < mid_x:
                left_col.append((left, top, text))
            else:
                right_col.append((left, top, text))

        left_col.sort(key=lambda x: x[1])
        right_col.sort(key=lambda x: x[1])

        page_text = "\n".join([item[2] for item in left_col + right_col])
        full_text += f"\n=== PAGE {i+1} ===\n" + page_text

    doc.close()

    # 줄바꿈 및 유니코드 공백문자 전처리
    full_text = full_text.replace('\xa0', ' ').replace('\u200b', '')
    
    # 표지에 있는 수험자 유의사항의 안내 일련번호(1. ~ 8.)가 기출문제 1~8번으로 오매칭되는 것 방지
    clean_lines = []
    for line in full_text.split('\n'):
        if any(kw in line for kw in ["답안지는", "시험 종료", "문제지 전부", "감독관의", "질문은 금지", "질문 가능", "부정행위", "답안지 작성 요령", "제출 방법", "공란에도", "유출 불가", "퇴실해야"]):
            line = re.sub(r'^\s*\d+\s*\.', '   ', line)
        clean_lines.append(line)
    full_text = '\n'.join(clean_lines)
    
    # 전체 텍스트에서 각 문제 번호의 시작 위치 탐색
    matches_dict = {}
    for num in range(1, 121):
        pat_num = rf"(?:^|\n)\s*{num}\s*\."
        matches = list(re.finditer(pat_num, full_text))
        if matches:
            matches_dict[num] = matches[0].start()

    # 인덱스 순서대로 정렬하여 텍스트 구간 분할 (2단 분할 시 꼬인 순서 그대로 보존)
    sorted_positions = sorted([(pos, num) for num, pos in matches_dict.items()])
    
    questions = {}
    for idx, (pos, num) in enumerate(sorted_positions):
        if idx + 1 < len(sorted_positions):
            next_pos = sorted_positions[idx + 1][0]
            q_text = full_text[pos:next_pos].strip()
        else:
            q_text = full_text[pos:].strip()

        q_text = re.sub(r'\n{3,}', '\n\n', q_text)

        pat_num = rf"(?:^|\n)\s*{num}\s*\."
        prefix_match = re.match(pat_num, q_text)
        if prefix_match:
            q_text = f"{num}. " + q_text[prefix_match.end():].strip()
        else:
            q_text = f"{num}. " + q_text.strip()

        if idx + 1 == len(sorted_positions):
            end_markers = ["=== PAGE", "수고하셨습니다"]
            for marker in end_markers:
                m_idx = q_text.find(marker)
                if m_idx != -1:
                    q_text = q_text[:m_idx].strip()
            q_text = re.sub(r'-\s*\d+\s*-', '', q_text).strip()
            q_text = re.sub(r'\n{3,}', '\n\n', q_text)

        questions[num] = q_text

    print(f"[{pdf_path_obj.name}]에서 총 {len(questions)}개 문항 추출 성공")
    return questions

def run_refinement():
    js_path = Path(r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_database.js")
    pdf_dir = Path(r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam")

    if not js_path.exists():
        print(f"에러: {js_path} 파일이 존재하지 않습니다.")
        return

    with open(str(js_path), "r", encoding="utf-8") as f:
        content = f.read()

    # examDatabase 로드
    match = re.search(r"const\s+examDatabase\s*=\s*(\{.*?\});", content, re.DOTALL)
    if not match:
        print("examDatabase 객체를 찾을 수 없습니다.")
        return

    js_obj_str = match.group(1)
    pairs = re.findall(r'"(\d{4}_\d+)":\s*"(.*?)"(?=,\s*"|\s*\})', js_obj_str, re.DOTALL)
    db_data = {k: v.replace('\\n', '\n').replace('\\"', '"') for k, v in pairs}

    # 연도별로 그룹화
    year_keys = {}
    for key in db_data.keys():
        year, num = key.split("_")
        num = int(num)
        year_keys.setdefault(year, []).append((key, num))

    print(f"총 {len(db_data)}개 문항의 대조 보완을 시작합니다.")

    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    updated_count = 0
    not_found_pdf = []

    for year, keys_list in year_keys.items():
        candidate_pdfs = [f for f in pdf_files if year in f.name and "답안표" not in f.name]

        if not candidate_pdfs:
            print(f"경고: {year}년도에 해당하는 문제지 PDF 파일을 찾을 수 없습니다.")
            not_found_pdf.append(year)
            continue

        candidate_pdfs.sort(key=lambda x: x.stat().st_size, reverse=True)
        target_pdf = candidate_pdfs[0]

        extracted_questions = extract_all_questions_for_year(str(target_pdf))

        for key, num in keys_list:
            orig_text = db_data[key].strip()
            
            is_placeholder = (
                orig_text.endswith("-") or 
                len(orig_text) < 15 or 
                orig_text == str(num)
            )

            if is_placeholder:
                if num in extracted_questions:
                    new_text = extracted_questions[num]
                    db_data[key] = new_text
                    updated_count += 1
                else:
                    print(f"경고: {year}년도 PDF에서 {num}번 문항(비어있음)을 추출하지 못했습니다. (Key: {key})")

    # 수정한 데이터를 다시 javascript 형식으로 저장
    formatted_pairs = []
    sorted_keys = sorted(db_data.keys(), key=lambda x: (int(x.split("_")[0]), int(x.split("_")[1])))
    
    for key in sorted_keys:
        val = db_data[key]
        escaped_val = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
        formatted_pairs.append(f'  "{key}": "{escaped_val}"')

    new_js_content = "const examDatabase = {\n" + ",\n".join(formatted_pairs) + "\n};\n"
    
    with open(str(js_path), "w", encoding="utf-8") as f:
        f.write(new_js_content)

    print(f"\n보완 완료! 업데이트된 문항 수: {updated_count}개")
    if not_found_pdf:
        print(f"누락된 PDF 연도: {not_found_pdf}")

if __name__ == "__main__":
    run_refinement()
