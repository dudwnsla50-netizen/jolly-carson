import fitz # PyMuPDF
import os
import html
import re

def convert_pdfs():
    # 경로 설정
    pdf_dir = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam"
    out_dir = os.path.join(pdf_dir, "html")
    os.makedirs(out_dir, exist_ok=True)
    
    # PDF 파일 목록 가져오기
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    # 연도별 정렬을 위해 파일명 내 숫자 기준 등으로 정렬
    pdf_files.sort(reverse=True)
    
    print(f"총 {len(pdf_files)}개의 PDF 파일을 찾았습니다.")
    
    for filename in pdf_files:
        pdf_path = os.path.join(pdf_dir, filename)
        html_filename = filename[:-4] + ".html"
        html_path = os.path.join(out_dir, html_filename)
        
        print(f"변환 중: {filename} -> {html_filename}")
        try:
            doc = fitz.open(pdf_path)
            pages_html = []
            
            # 각 페이지 변환
            for page_num in range(len(doc)):
                page = doc[page_num]
                # HTML 텍스트 추출
                raw_html = page.get_text("html")
                # 한글 엔티티 디코딩 (&#xb144; -> 년 등)
                decoded_html = html.unescape(raw_html)
                
                # 가독성을 높이기 위해 페이지 구분 div 추가
                pages_html.append(f"""
                <div class="page-wrapper" id="page-section-{page_num + 1}">
                    <div class="page-header-bar">
                        <span>페이지 {page_num + 1} / {len(doc)}</span>
                        <span>{filename[:-4]}</span>
                    </div>
                    <div class="page-content-box">
                        {decoded_html}
                    </div>
                </div>
                """)
                
            doc.close()
            
            # 스타일 및 템플릿 입혀서 HTML 합치기
            title = filename[:-4]
            full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 정보시스템감리사 기출문제</title>
    <style>
        :root {{
            --primary-color: #2563eb;
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --border-color: #334155;
            --header-bg: #1e293b;
        }}
        
        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        
        header {{
            background-color: var(--header-bg);
            width: 100%;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
            position: fixed;
            top: 0;
            left: 0;
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 24px;
            box-sizing: border-box;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .header-title {{
            font-size: 1.15rem;
            font-weight: bold;
            color: #38bdf8;
        }}
        
        .nav-buttons {{
            display: flex;
            gap: 12px;
        }}
        
        .btn {{
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: bold;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }}
        
        .btn:hover {{
            background-color: #1d4ed8;
            transform: translateY(-1px);
        }}
        
        .btn-secondary {{
            background-color: #475569;
        }}
        
        .btn-secondary:hover {{
            background-color: #334155;
        }}

        .main-content {{
            margin-top: 80px;
            padding: 20px;
            max-width: 1000px;
            width: 100%;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 35px;
        }}
        
        .page-wrapper {{
            background-color: #ffffff; /* PDF 가시성을 위해 화이트 배경 */
            color: #000000;
            border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
            width: 100%;
            border: 1px solid var(--border-color);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}
        
        .page-header-bar {{
            background-color: #f1f5f9;
            border-bottom: 1px solid #e2e8f0;
            padding: 10px 20px;
            font-size: 0.85rem;
            color: #64748b;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
        }}
        
        .page-content-box {{
            padding: 20px;
            position: relative;
            box-sizing: border-box;
            background-color: #ffffff;
            display: flex;
            justify-content: center;
            overflow-x: auto;
        }}
        
        /* PyMuPDF 절대 위치 div 및 p 태그 스타일 오버라이드 */
        .page-content-box > div {{
            position: relative !important;
            box-shadow: none !important;
            border: none !important;
            background: #ffffff !important;
            margin: 0 auto !important;
        }}
        
        .page-content-box p {{
            position: absolute !important;
            margin: 0 !important;
            white-space: nowrap !important;
        }}

        .page-content-box span {{
            font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
        }}

        /* 프린트 스타일 */
        @media print {{
            body {{
                background-color: #ffffff;
                color: #000000;
            }}
            header {{
                display: none;
            }}
            .main-content {{
                margin-top: 0;
                padding: 0;
            }}
            .page-wrapper {{
                box-shadow: none;
                border: none;
                page-break-after: always;
            }}
            .page-header-bar {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-title">📖 {title}</div>
        <div class="nav-buttons">
            <a href="index.html" class="btn btn-secondary">목록으로</a>
            <button onclick="window.print()" class="btn">PDF 저장 / 인쇄</button>
        </div>
    </header>
    
    <div class="main-content">
        {"".join(pages_html)}
    </div>
</body>
</html>
"""
            with open(html_path, "w", encoding="utf-8") as out_f:
                out_f.write(full_html)
            
            print(f"성공: {html_filename} 변환 완료.")
        except Exception as e:
            print(f"에러 발생 ({filename}): {e}")

if __name__ == '__main__':
    convert_pdfs()
