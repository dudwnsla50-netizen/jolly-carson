# -*- coding: utf-8 -*-
"""
프로젝트의 기본 원칙을 준수하여 작성된 문서 수집 및 파싱 스크립트입니다.
- 원칙 1: 모든 주석 및 콘솔 출력은 한국어로 작성합니다.
- 원칙 2: 5대 과목 코드 체계(PM, SE, DB, SA, SC)를 준수합니다.
- 원칙 3: 파이썬 내장 모듈을 최우선으로 활용하여 외부 의존성을 최소화합니다. (docx xml 직접 파싱 등)
"""

import os
import sys
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime

# 5대 과목 코드 체계 및 과목명 정의
# 정보시스템 감리사 시험의 공식 5대 과목 코드 체계를 준수합니다.
SUBJECT_MAP = {
    "1": "PM",  # 감리 및 사업관리 (Project Management)
    "2": "SE",  # 소프트웨어공학 (Software Engineering)
    "3": "DB",  # 데이터베이스 (Database)
    "4": "SA",  # 시스템구조 (System Architecture)
    "5": "SC"   # 보안 (Security / Cryptography)
}

SUBJECT_NAMES = {
    "PM": "감리 및 사업관리",
    "SE": "소프트웨어공학",
    "DB": "데이터베이스",
    "SA": "시스템구조",
    "SC": "보안"
}

# 캐시 정보 파일 경로 지정
STATUS_JSON_PATH = os.path.join("data", "data_status.json")

def load_status_json():
    """
    data_status.json 캐시 파일을 안전하게 읽어옵니다.
    파일이 없거나 문법이 깨져 있으면 크래시 없이 빈 딕셔너리를 반환하고 새로 만듭니다.
    """
    if not os.path.exists(STATUS_JSON_PATH):
        return {}
    try:
        with open(STATUS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[경고] 캐시 파일(data_status.json)을 읽는 중 오류가 발생하여 캐시를 초기화합니다: {e}")
        return {}

def save_status_json(status_data):
    """
    data_status.json 캐시 데이터를 디스크에 안전하게 씁니다.
    디렉토리가 없으면 생성하고, 쓰기 실패 시 예외 처리하여 프로그램 크래시를 방지합니다.
    """
    try:
        os.makedirs(os.path.dirname(STATUS_JSON_PATH), exist_ok=True)
        with open(STATUS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"[오류] 캐시 저장 중 입출력 에러 발생: {e}")

def get_files_from_dialog(subject_name):
    """
    tkinter를 활용하여 대화형 파일 다중 선택 창을 띄웁니다.
    디스플레이가 없는 환경(TclError 등)에서는 텍스트 경로를 수동 입력하는 CLI 폴백 모드를 실행합니다.
    """
    use_fallback = False
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        print("[안내] tkinter 모듈이 없으므로 수동 텍스트 입력 모드로 전환합니다.")
        use_fallback = True

    if not use_fallback:
        try:
            # Tk 윈도우 인스턴스를 생성하되, withdraw()를 호출하여 불필요한 빈 창이 화면에 뜨는 것을 방지합니다.
            root = tk.Tk()
            root.withdraw()
            
            # [수정 의도] 윈도우 환경에서 파일 선택 다이얼로그 창이 포커스를 잃고 다른 활성 창 뒤로 숨어서
            # 사용자가 보지 못하고 무한 대기(실행 중 상태)에 빠지는 현상을 해결하기 위한 설정입니다.
            root.lift()
            root.attributes("-topmost", True)
            
            # 파일 다중 선택 창을 띄웁니다.
            title_text = f"[{subject_name}] 시험범위 문서 파일 다중 선택"
            file_paths = filedialog.askopenfilenames(
                parent=root,  # 부모 창을 명시적으로 연결하여 topmost 설정이 전파되도록 합니다.
                title=title_text,
                filetypes=[
                    ("지원 문서 파일", "*.pdf *.docx *.txt"),
                    ("PDF 파일", "*.pdf"),
                    ("Word 파일", "*.docx"),
                    ("텍스트 파일", "*.txt"),
                    ("모든 파일", "*.*")
                ]
            )
            # [수정 의도] Tkinter 이벤트 루프와 윈도우 리소스를 명시적으로 제거하여 프로세스가 백그라운드에 남지 않게 합니다.
            root.destroy()
            return list(file_paths)
        except Exception as e:
            # TclError (디스플레이 없음) 등을 대비하여 CLI 폴백 실행
            print(f"[안내] GUI 파일 대화창을 열 수 없어 수동 텍스트 입력 모드로 전환합니다. (사유: {e})")
            use_fallback = True

    # CLI 수동 파일 입력 폴백 모드
    if use_fallback:
        print("\n* 파일 경로들을 직접 입력해 주세요.")
        print("  - 여러 파일인 경우 쉼표(,)로 구분하여 입력하십시오.")
        print("  - 예: C:\\docs\\test1.pdf, C:\\docs\\test2.docx")
        user_input = input(">> 파일 경로 입력: ").strip()
        if not user_input:
            return []
        
        # 쉼표 구분자 처리 및 공백 제거
        paths = [p.strip().strip('"').strip("'") for p in user_input.split(',')]
        # 실제로 존재하는 파일만 필터링하여 유효성 보장
        valid_paths = []
        for p in paths:
            if not p:
                continue
            if os.path.exists(p):
                valid_paths.append(p)
            else:
                print(f"  [경고] 존재하지 않는 파일 경로는 제외됩니다: {p}")
        return valid_paths

def extract_txt(file_path):
    """
    TXT 파일에서 텍스트를 디코딩하여 추출합니다.
    다양한 인코딩 포맷을 순차적으로 시도하여 한글 깨짐 및 디코딩 오류를 최소화합니다.
    """
    encodings = ["utf-8", "cp949", "euc-kr", "utf-16", "latin-1"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError("지원하지 않거나 식별할 수 없는 텍스트 인코딩 형식입니다.")

def extract_docx(file_path):
    """
    DOCX 파일을 외부 라이브러리 없이 압축을 해제하여 내부 XML을 직접 분석 및 파싱합니다.
    텍스트 본문과 표(Table) 구조의 흐름을 보존하여 마크다운 포맷으로 변환합니다.
    """
    # DOCX 파일은 내부적으로 XML 파일들이 압축된 ZIP 포맷이므로 zipfile 모듈을 사용합니다.
    if not zipfile.is_zipfile(file_path):
        raise ValueError("올바른 DOCX 파일 형식이 아닙니다 (ZIP 구조가 아님).")

    with zipfile.ZipFile(file_path) as docx:
        # 본문 데이터가 담겨있는 word/document.xml을 읽어옵니다.
        xml_content = docx.read("word/document.xml")
        root = ET.fromstring(xml_content)
        
        # XML 태그 해석을 위한 네임스페이스 정의
        namespaces = {
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        }
        
        body = root.find('w:body', namespaces)
        if body is None:
            return ""

        markdown_elements = []
        
        # 본문 영역(body)의 자식 노드들을 순서대로 탐색하여 본문 흐름과 표의 순서가 꼬이지 않도록 합니다.
        for element in body:
            tag_name = element.tag.split('}')[-1]
            
            # 1. 일반 문단 (p) 처리
            if tag_name == 'p':
                text_runs = []
                # 문단 내의 개별 텍스트 요소(t)를 찾아서 병합합니다.
                for node in element.iter():
                    if node.tag.endswith('t') and node.text:
                        text_runs.append(node.text)
                paragraph_text = "".join(text_runs).strip()
                if paragraph_text:
                    markdown_elements.append(paragraph_text)
            
            # 2. 표 (tbl) 구조 처리
            elif tag_name == 'tbl':
                table_rows = []
                # 표 내의 행(tr) 탐색
                for row in element.findall('.//w:tr', namespaces):
                    row_data = []
                    # 행 내의 셀(tc) 탐색
                    for cell in row.findall('.//w:tc', namespaces):
                        # 셀 안에 있는 모든 텍스트 요소 추출 및 정제
                        cell_texts = []
                        for node in cell.iter():
                            if node.tag.endswith('t') and node.text:
                                cell_texts.append(node.text)
                        cell_raw = "".join(cell_texts)
                        # 개행이나 마크다운 표 구분선(|) 문제를 해결하기 위해 공백으로 치환하고 파이프 기호를 이스케이프 처리합니다.
                        cell_clean = cell_raw.replace('\r', ' ').replace('\n', ' ').replace('|', '\\|').strip()
                        row_data.append(cell_clean)
                    if row_data:
                        table_rows.append(row_data)

                # 추출된 행 데이터를 기반으로 마크다운 표를 렌더링합니다.
                if table_rows:
                    table_markdown = []
                    headers = table_rows[0]
                    # 빈 컬럼명 방지 및 기본 헤더 구성
                    headers_clean = [h if h else f"열{i+1}" for i, h in enumerate(headers)]
                    table_markdown.append("| " + " | ".join(headers_clean) + " |")
                    table_markdown.append("| " + " | ".join(["---"] * len(headers_clean)) + " |")
                    
                    for row_content in table_rows[1:]:
                        # 헤더 개수보다 열이 적은 경우 보정
                        if len(row_content) < len(headers_clean):
                            row_content.extend([""] * (len(headers_clean) - len(row_content)))
                        else:
                            row_content = row_content[:len(headers_clean)]
                        table_markdown.append("| " + " | ".join(row_content) + " |")
                    
                    markdown_elements.append("\n" + "\n".join(table_markdown) + "\n")

        return "\n\n".join(markdown_elements)

def extract_pdf(file_path):
    """
    PDF 파일에서 텍스트와 표를 추출합니다.
    외부 라이브러리(pdfplumber, pypdf)의 설치 유무를 동적으로 확인하여 폴백(Fallback) 처리합니다.
    """
    # 1단계: 표 추출 성능이 뛰어난 pdfplumber 시도
    try:
        import pdfplumber
        # pdfplumber가 성공적으로 로드된 경우 표 보존 파싱을 수행합니다.
        markdown_elements = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # 2단/4단 레이아웃 꼬임을 방지하기 위해 페이지의 종횡비를 감지하여 분할(Crop) 추출을 시도합니다.
                width = page.width
                height = page.height
                
                # Landscape(가로형)인 경우 4단, Portrait(세로형)인 경우 2단 분할
                bands_count = 4 if width > height else 2
                page_text_parts = []
                
                for b in range(bands_count):
                    x0 = (width / bands_count) * b
                    x1 = (width / bands_count) * (b + 1)
                    bbox = (x0, 0, x1, height)
                    
                    cropped_page = page.crop(bbox)
                    text = cropped_page.extract_text()
                    if text:
                        page_text_parts.append(text)
                
                page_text = "\n".join(page_text_parts) if page_text_parts else ""
                tables = page.extract_tables()
                
                markdown_elements.append(page_text.strip())
                
                # 표 데이터가 감지되면 마크다운 표 양식으로 출력에 덧붙입니다.
                for table in tables:
                    if not table or not any(table):
                        continue
                    table_markdown = []
                    headers = [str(cell or "").replace('\n', ' ').replace('|', '\\|').strip() for cell in table[0]]
                    headers_clean = [h if h else f"열{idx+1}" for idx, h in enumerate(headers)]
                    
                    table_markdown.append("| " + " | ".join(headers_clean) + " |")
                    table_markdown.append("| " + " | ".join(["---"] * len(headers_clean)) + " |")
                    
                    for row in table[1:]:
                        row_cells = [str(cell or "").replace('\n', ' ').replace('|', '\\|').strip() for cell in row]
                        # 헤더 길이 맞추기
                        if len(row_cells) < len(headers_clean):
                            row_cells.extend([""] * (len(headers_clean) - len(row_cells)))
                        else:
                            row_cells = row_cells[:len(headers_clean)]
                        table_markdown.append("| " + " | ".join(row_cells) + " |")
                    
                    markdown_elements.append("\n" + "\n".join(table_markdown) + "\n")
        return "\n\n".join(markdown_elements)

    except ImportError:
        # pdfplumber가 없는 경우, pypdf 설치 여부를 확인하여 텍스트만이라도 추출합니다.
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            text_pages = []
            for page in reader.pages:
                text_pages.append(page.extract_text() or "")
            return "\n\n".join(text_pages)
        except ImportError:
            # 두 모듈이 모두 없는 경우에는 에러를 던져 호출자(main)에서 처리하게 합니다.
            raise ImportError("PDF 분석에 필요한 외부 패키지('pdfplumber' 또는 'pypdf')가 설치되어 있지 않습니다.\n"
                              "표 구조 보존을 위해 'pip install pdfplumber' 설치를 권장합니다.")

def parse_file_to_markdown(src_file_path, dest_md_path):
    """
    파일 확장자에 맞춰 적절한 파서 함수를 호출하여 마크다운 파일로 정제해 저장합니다.
    """
    ext = os.path.splitext(src_file_path)[1].lower()
    
    if ext == ".txt":
        content = extract_txt(src_file_path)
    elif ext == ".docx":
        content = extract_docx(src_file_path)
    elif ext == ".pdf":
        content = extract_pdf(src_file_path)
    else:
        raise ValueError(f"지원하지 않는 파일 확장자입니다: {ext}")
    
    # extracted 폴더가 없으면 자동 생성
    os.makedirs(os.path.dirname(dest_md_path), exist_ok=True)
    with open(dest_md_path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    print("=" * 60)
    print("  [5대 과목 대화형 시험범위 문서 수집 및 파서 프로그램]  ")
    print("=" * 60)
    
    # 1단계: 과목 코드 및 명칭 선택
    while True:
        print("\n* 수집 및 분석할 과목을 선택해 주세요:")
        for key, value in SUBJECT_MAP.items():
            code = value
            name = SUBJECT_NAMES[code]
            print(f"  [{key}] {name} ({code})")
        print("  [Q] 프로그램 종료")
        
        choice = input(">> 선택 (1~5 또는 Q): ").strip()
        if choice.upper() == 'Q':
            print("프로그램을 종료합니다.")
            sys.exit(0)
            
        if choice in SUBJECT_MAP:
            subject_code = SUBJECT_MAP[choice]
            subject_name = SUBJECT_NAMES[subject_code]
            break
        else:
            print("[경고] 올바른 번호를 입력해 주세요.")
            
    print(f"\n-> 선택 과목: {subject_name} ({subject_code})")
    
    # 2단계: 강제 재파싱 여부 입력받기
    # 캐시를 강제로 우회하여 모든 파일을 전면 재파싱할 수 있도록 유연한 옵션을 제공합니다.
    # 실행 인자에 '--force'가 들어왔거나 콘솔 입력에서 Y를 선택하면 강제 재파싱이 활성화됩니다.
    force_parse = "--force" in sys.argv
    if not force_parse:
        force_choice = input(">> 캐시를 무시하고 강제로 전체 재파싱하시겠습니까? (y/N): ").strip().lower()
        if force_choice in ['y', 'yes', '예']:
            force_parse = True
            print("-> 강제 재파싱 옵션이 활성화되었습니다.")
            
    # 3단계: tkinter 대화창으로 파일 선택
    print("\n* 문서 파일 브라우저 창이 열립니다. 시험 범위 문서들을 다중 선택해 주세요...")
    chosen_files = get_files_from_dialog(subject_name)
    
    if not chosen_files:
        print("[안내] 선택된 파일이 없거나 대화창이 닫혔습니다. 프로그램을 종료합니다.")
        return
        
    print(f"\n-> 총 {len(chosen_files)}개의 원본 파일이 선택되었습니다.")

    # 4단계: 원본 파일을 data/uploaded_inputs/{과목코드}/ 경로로 안전하게 백업 및 보관
    # 중앙 보관 폴더 경로 구성
    backup_dir = os.path.join("data", "uploaded_inputs", subject_code)
    os.makedirs(backup_dir, exist_ok=True)
    
    # 캐시 데이터 로드
    status_cache = load_status_json()
    if subject_code not in status_cache:
        status_cache[subject_code] = {}

    for src_file in chosen_files:
        filename = os.path.basename(src_file)
        dest_file_path = os.path.join(backup_dir, filename)
        
        print(f"\n[작업 시작] 파일: {filename}")
        
        # 파일이 읽기 전용 상태이거나 타 프로세스에 의해 권한 문제가 생길 경우를 대비한 촘촘한 예외 처리
        try:
            # shutil.copy2를 사용해 원본의 메타데이터(수정 시간 등)를 그대로 복사 보관합니다.
            shutil.copy2(src_file, dest_file_path)
            print(f"  - 원본 백업 복사 완료 -> {dest_file_path}")
        except PermissionError as pe:
            print(f"  [에러] 해당 파일이 다른 프로그램에 의해 열려 있어 접근할 수 없습니다: {pe}")
            print("  - 이 파일은 건너뛰고 다음 파일 처리를 시도합니다.")
            continue
        except FileNotFoundError as fnfe:
            print(f"  [에러] 원본 파일을 찾을 수 없습니다: {fnfe}")
            continue
        except Exception as e:
            print(f"  [에러] 파일 백업 중 알 수 없는 예외가 발생했습니다: {e}")
            continue

        # 복사 완료된 백업본의 속성 획득
        try:
            file_mtime = os.path.getmtime(dest_file_path)
            file_size = os.path.getsize(dest_file_path)
        except Exception as e:
            print(f"  [에러] 복사된 파일 메타데이터 획득 실패: {e}")
            continue

        # 5단계: 스마트 캐싱 체크 및 파싱 프로세스 연동
        # 캐싱 메커니즘: data_status.json에서 과목코드 하위에 해당 파일명이 존재하고
        # mtime과 파일 크기가 일치하며, 강제 옵션이 비활성화되었으며, 실제 결과 .md 파일이 존재할 때 캐시를 타게 만듭니다.
        filename_without_ext = os.path.splitext(filename)[0]
        dest_md_path = os.path.join("extracted", subject_code, f"{filename_without_ext}.md")
        
        cached_info = status_cache[subject_code].get(filename, {})
        is_cache_hit = (
            not force_parse and
            cached_info and
            cached_info.get("mtime") == file_mtime and
            cached_info.get("size") == file_size and
            cached_info.get("status") == "success" and
            os.path.exists(dest_md_path)
        )
        
        if is_cache_hit:
            print(f"  -> [스마트 캐싱 적용] 파일 내용 변경 없음. 마크다운 파싱을 건너뛰고 기존 변환 파일을 사용합니다.")
            continue

        # 6단계: 텍스트 및 표 구조 추출 및 마크다운 변환 시도
        print(f"  - 마크다운 파일 변환을 시작합니다...")
        try:
            parse_file_to_markdown(dest_file_path, dest_md_path)
            print(f"  - [성공] 마크다운 정제 저장 완료: {dest_md_path}")
            
            # 파싱 성공 후 캐시 정보 업데이트
            status_cache[subject_code][filename] = {
                "mtime": file_mtime,
                "size": file_size,
                "status": "success",
                "extracted_path": dest_md_path,
                "parsed_at": datetime.now().isoformat()
            }
            save_status_json(status_cache)
            
        except ImportError as ie:
            # PDF 분석 패키지 미설치 등 외부 모듈 부재 시 흐름 제어
            print(f"  [의존성 경고] {ie}")
            print(f"  - '{filename}' 분석은 스킵합니다. 다음 파일 처리를 계속 진행합니다.")
            status_cache[subject_code][filename] = {
                "mtime": file_mtime,
                "size": file_size,
                "status": "failed_missing_dependency",
                "error_msg": str(ie)
            }
            save_status_json(status_cache)
        except Exception as e:
            # 기타 파싱 시 생길 수 있는 파일 포맷 오류 등의 크래시 방지
            print(f"  [파싱 에러] 마크다운 변환 중 예상치 못한 문제가 발생했습니다: {e}")
            status_cache[subject_code][filename] = {
                "mtime": file_mtime,
                "size": file_size,
                "status": "failed_parsing",
                "error_msg": str(e)
            }
            save_status_json(status_cache)

    print("\n" + "=" * 60)
    print("  모든 문서 수집 및 파싱 처리가 완료되었습니다.  ")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[안내] 사용자에 의해 프로그램이 강제 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[오류] 메인 프로그램 실행 중 예기치 않은 치명적 에러가 발생했습니다: {e}")
        sys.exit(1)
