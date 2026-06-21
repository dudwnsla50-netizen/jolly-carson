import os
import json
import re

# 현재 대화의 아티팩트 디렉토리 경로
# render.com 등 서버 배포 환경 및 타 OS 환경(리눅스 등)에서 로컬 경로(C:\Users\...) 접근 시의 에러를 방지하기 위해 
# 환경 변수나 OS 환경을 파악하여 적절한 폴백 경로를 지정합니다.
import sys
_DEFAULT_ARTIFACT_DIR = r"C:\Users\histo\.gemini\antigravity-ide\brain\3b0b18aa-3dac-4252-8a82-888bf4634d2d"

if os.environ.get("GEMINI_ARTIFACT_DIR"):
    ARTIFACT_DIR = os.environ.get("GEMINI_ARTIFACT_DIR")
elif sys.platform == "win32" and os.path.exists(os.path.dirname(r"C:\Users\histo")):
    ARTIFACT_DIR = _DEFAULT_ARTIFACT_DIR
else:
    # render.com 등 리눅스 서버 환경 혹은 타 사용자 PC에서는 
    # 워크스페이스 내의 임시/더미 경로를 반환하여 os.path.join 시의 TypeError를 예방합니다.
    # 실제로 이 디렉토리를 물리적으로 생성하거나 쓸 때 예외가 나면 무시하도록 처리합니다.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ARTIFACT_DIR = os.path.join(base_dir, "reports", "temp_artifacts_fallback")


def get_output_paths(filename):
    """
    주어진 파일명에 대해 로컬 워크스페이스 reports 경로와 아티팩트 경로를 반환합니다.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(base_dir, "reports", filename)
    artifact_path = os.path.join(ARTIFACT_DIR, filename)
    return local_path, artifact_path

def update_shared_db(new_db, subject_code):
    """
    로컬 및 아티팩트 경로의 과목별 JS 파일에 새로운 기출문제 데이터를 머지하고 저장합니다.
    """
    filename = f"exam_db/{subject_code.lower()}_db.js"
    local_js_path, artifact_js_path = get_output_paths(filename)
    
    merged_db = {}
    
    # 정규식 기반 JS 객체 강인 파서 정의
    def parse_js_db(path):
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            match = re.search(r"const\s+examDatabase\s*=\s*(\{[\s\S]*\});", content)
            if not match:
                return {}
            js_obj_str = match.group(1)
            pairs = re.findall(r'"(\d{4}_\d+)":\s*"(.*?)"(?=,\s*"|\s*\})', js_obj_str, re.DOTALL)
            parsed = {}
            for k, v in pairs:
                parsed[k] = v.replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')
            return parsed
        except Exception as e:
            print(f"[경고] {os.path.basename(path)} 파싱 중 오류 발생: {e}")
            return {}
            
    # 1. 기존 로컬 js 파일이 존재하면 읽어서 파싱 시도
    merged_db = parse_js_db(local_js_path)
            
    # 2. 기존 아티팩트 js 파일이 존재하고 로컬에서 데이터를 못 읽었을 경우 대용으로 사용
    if not merged_db:
        merged_db = parse_js_db(artifact_js_path)

    # 3. 새로운 데이터 병합
    if new_db:
        merged_db.update(new_db)
        
    # 4. JSON 문자열로 포맷팅 및 JS 코드 작성
    db_json = json.dumps(merged_db, indent=2, ensure_ascii=False)
    js_content = f"const examDatabase = {db_json};\n"
    
    # 5. 로컬 경로에 저장
    os.makedirs(os.path.dirname(local_js_path), exist_ok=True)
    with open(local_js_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"[{subject_code} DB] 로컬 업데이트 완료: {local_js_path}")
    
    # 6. 아티팩트 경로에 저장 (배포 환경 등을 고려하여 예외 처리로 방어)
    try:
        os.makedirs(os.path.dirname(artifact_js_path), exist_ok=True)
        with open(artifact_js_path, "w", encoding="utf-8") as f:
            f.write(js_content)
        print(f"[{subject_code} DB] 아티팩트 업데이트 완료: {artifact_js_path}")
    except Exception as e:
        print(f"[{subject_code} DB] 아티팩트 업데이트 건너뜀 (배포 환경 혹은 권한 없음): {e}")

def get_dashboard_html_template(dashboard_type, subject_code, subject_name, mapping_json, filter_section_html=""):
    """
    모든 과목(5종) 및 모드(2종)에서 공유하는 공통 HTML 대시보드 구조를 반환합니다.
    동시에 대용량 mapping_json 데이터를 외부 JS 파일(js/data/)로 분리하여 로컬 및 아티팩트 경로에 저장합니다.
    """
    import os

    # 1. 외부 JS 파일 생성 및 저장 경로 획득
    js_filename = f"js/data/{subject_code.lower()}_{dashboard_type}.js"
    local_js_path, artifact_js_path = get_output_paths(js_filename)
    
    js_content = f"window.dashboardData = {mapping_json};\n"
    
    # 로컬 경로에 저장
    os.makedirs(os.path.dirname(local_js_path), exist_ok=True)
    with open(local_js_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"[{subject_code} 데이터 JS] 로컬 저장 완료: {local_js_path}")
    
    # 아티팩트 경로에 저장 (배포 환경 등을 고려하여 예외 처리로 방어)
    try:
        os.makedirs(os.path.dirname(artifact_js_path), exist_ok=True)
        with open(artifact_js_path, "w", encoding="utf-8") as f:
            f.write(js_content)
        print(f"[{subject_code} 데이터 JS] 아티팩트 저장 완료: {artifact_js_path}")
    except Exception as e:
        print(f"[{subject_code} 데이터 JS] 아티팩트 저장 건너뜀 (배포 환경 혹은 권한 없음): {e}")

    title_suffix = "공식 범위별 기출 뷰어" if dashboard_type == "official" else "12개년 빈출 개념 정밀 뷰어"
    header_title = f"{subject_name} 공식 범위별 기출분석" if dashboard_type == "official" else f"{subject_name} 기출 정밀 분석 대시보드"
    header_subtitle = "공식 시험 범위 표준 가이드를 기준으로 매핑된 세부 중단원 정밀 대시보드" if dashboard_type == "official" else "12개년 기출 전수 조사 기반 빈출 세부 토픽 분석 엔진"
    topic_badge_prefix = "매핑된 공식 중단원" if dashboard_type == "official" else "검출된 빈출 세부 토픽"

    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject_name} {title_suffix}</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="css/dashboard_common.css">
    <link rel="stylesheet" href="css/game.css">
    <script src="exam_db/{subject_code.lower()}_db.js?v=20260613"></script>
    <script src="js/dashboard_common.js?v=20260613"></script>
    <!-- 외부 데이터 스크립트 동적 로드 -->
    <script src="js/data/{subject_code.lower()}_{dashboard_type}.js?v=20260618"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>{header_title}</h1>
            <p class="subtitle">{header_subtitle}</p>
            
            <div class="navigation-container">
                <div class="mode-switch-wrapper">
                    <span class="mode-label" id="label-freq">🔥 빈출 개념순</span>
                    <label class="switch">
                        <input type="checkbox" id="dashboard-mode-toggle" onchange="toggleDashboardMode(this)">
                        <span class="slider round"></span>
                    </label>
                    <span class="mode-label" id="label-official">📋 공식 범위순</span>
                </div>
                
                <div class="meta-badges" id="dynamic-nav-badges">
                    <a href="#" class="badge home-badge" onclick="goToHome(event)" style="text-decoration: none; background: var(--accent-gradient); color: #ffffff; border: none; font-weight: 700;">🏠 퀴즈 홈으로</a>
                    <a href="se_frequent_concepts.html" class="badge subject-badge" data-freq="se_frequent_concepts.html" data-official="se_official_scopes.html" style="text-decoration: none;">소프트웨어공학</a>
                    <a href="pm_frequent_concepts.html" class="badge subject-badge" data-freq="pm_frequent_concepts.html" data-official="pm_official_scopes.html" style="text-decoration: none;">프로젝트 관리</a>
                    <a href="db_frequent_concepts.html" class="badge subject-badge" data-freq="db_frequent_concepts.html" data-official="db_official_scopes.html" style="text-decoration: none;">데이터베이스</a>
                    <a href="sa_frequent_concepts.html" class="badge subject-badge" data-freq="sa_frequent_concepts.html" data-official="sa_official_scopes.html" style="text-decoration: none;">시스템 아키텍처</a>
                    <a href="sc_frequent_concepts.html" class="badge subject-badge" data-freq="sc_frequent_concepts.html" data-official="sc_official_scopes.html" style="text-decoration: none;">보안</a>
                </div>
            </div>
            
            <div class="meta-badges">
                <span class="badge">기출 범위: 2015년 ~ 2026년</span>
                <span class="badge accent">총 분석 데이터: <span id="total-question-badge">0</span> 문항</span>
                <span class="badge" onclick="openTopicListModal()" style="cursor: pointer; transition: all 0.2s;" title="클릭 시 중단원 목록 팝업 열기">
                    {topic_badge_prefix}: <span id="topic-count-badge">0</span>개
                </span>
            </div>
        </header>

        {filter_section_html}

        <div class="accordion-list" id="accordionContainer">
            <!-- Dynamic Accordion Items Rendered by JS -->
        </div>
    </div>

    <!-- 세부 토픽 목록 팝업 모달 -->
    <div id="topic-modal" class="modal-overlay" onclick="closeTopicModal(event)">
        <div class="modal-card" onclick="event.stopPropagation()">
            <div class="modal-card-header">
                <h2 class="modal-card-title">🔍 검출된 공식 중단원 목록</h2>
                <button class="modal-close-x" onclick="closeTopicModal()">✕</button>
            </div>
            <div class="modal-card-body">
                <ul id="modal-topic-list" class="modal-topic-list">
                </ul>
            </div>
        </div>
    </div>

    <script>
        // 개별 과목 메타 선언부
        window.DASHBOARD_TYPE = "{dashboard_type}";
        window.SUBJECT_CODE = "{subject_code}";
        window.SUBJECT_NAME = "{subject_name}";
    </script>
</body>
</html>"""
    return html_template


