# -*- coding: utf-8 -*-
"""
[10종 대시보드 내비게이션 시안 A 패치 자동화 스크립트]
- 목적: 10개 빌더 파이썬 스크립트 내부의 HTML 템플릿을 파싱하여,
  모드 토글 스위치형 내비게이션(시안 A) 마크업, CSS 스타일, JS 제어 로직을 일괄 주입합니다.
- 작성자: Antigravity
"""

import os
import re
import sys

# 한글 출력 인코딩 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BUILDERS = [
    "build_premium_db_viewer.py",
    "build_premium_db_official_viewer.py",
    "build_premium_pm_viewer.py",
    "build_premium_pm_official_viewer.py",
    "build_premium_se_viewer.py",
    "build_premium_se_official_viewer.py",
    "build_premium_sa_viewer.py",
    "build_premium_sa_official_viewer.py",
    "build_premium_sc_viewer.py",
    "build_premium_sc_official_viewer.py"
]

# 1. 템플릿에 새로 주입할 공통 CSS 코드 정의
NEW_CSS = """
        /* [설계 의도] 시안A: 모드 토글 스위치 및 최적화된 내비게이션 스타일 */
        .navigation-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1.2rem;
            margin-bottom: 2rem;
            width: 100%;
        }
        .mode-switch-wrapper {
            display: flex;
            align-items: center;
            gap: 1rem;
            background: rgba(255, 255, 255, 0.02);
            padding: 0.5rem 1.2rem;
            border-radius: 50px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(8px);
        }
        .mode-label {
            font-size: 0.88rem;
            font-weight: 600;
            transition: color 0.25s ease;
        }
        .switch {
            position: relative;
            display: inline-block;
            width: 46px;
            height: 24px;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: rgba(255, 255, 255, 0.08);
            transition: .3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 18px; width: 18px;
            left: 3px; bottom: 3px;
            background-color: #ffffff;
            transition: .3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        input:checked + .slider {
            background: var(--accent-gradient);
            box-shadow: 0 0 10px rgba(139, 92, 246, 0.2);
        }
        input:checked + .slider:before {
            transform: translateX(22px);
        }
        .slider.round { border-radius: 34px; }
        .slider.round:before { border-radius: 50%; }
        
        .badge.accent {
            background: rgba(139, 92, 246, 0.12) !important;
            border-color: rgba(139, 92, 246, 0.25) !important;
            color: #ffffff !important;
        }
"""

# 2. 템플릿에 새로 주입할 공통 내비게이션 마크업 정의
NEW_HTML = """        <div class="navigation-container">
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
        </div>"""

# 3. 템플릿에 새로 주입할 제어용 공통 JS 함수 정의
NEW_JS = """
    // [설계 의도] 로컬 오프라인 실행(file:///)과 웹 서버 호스팅(http://) 환경 양쪽 모두에서 퀴즈 대시보드 홈으로 매끄럽게 이동하도록 분기 처리합니다.
    function goToHome(event) {
        event.preventDefault();
        if (window.location.protocol === 'file:') {
            window.location.href = '../index.html';
        } else {
            window.location.href = '/';
        }
    }

    // [설계 의도] 학습 모드 변경에 따라 과목 뱃지의 링크 목적지를 실시간 동적 갱신하고 즉시 이동 처리합니다.
    function toggleDashboardMode(toggleEl) {
        const isOfficial = toggleEl.checked;
        
        // 라벨 색상 하이라이트 전환
        document.getElementById('label-freq').style.color = isOfficial ? 'var(--text-secondary)' : '#ffffff';
        document.getElementById('label-official').style.color = isOfficial ? '#ffffff' : 'var(--text-secondary)';
        
        // 과목별 이동 경로 실시간 매핑
        const badges = document.querySelectorAll('.subject-badge');
        const isLocal = window.location.protocol === 'file:';
        
        badges.forEach(badge => {
            const target = isOfficial ? badge.getAttribute('data-official') : badge.getAttribute('data-freq');
            if (isLocal) {
                badge.href = target;
            } else {
                badge.href = '/reports/' + target;
            }
        });

        // 사용자의 현재 보고 있는 과목에 매칭되는 대시보드로 즉각 리다이렉트
        const currentPath = window.location.pathname;
        let targetRedirect = "";
        badges.forEach(badge => {
            const freqPath = badge.getAttribute('data-freq');
            const officialPath = badge.getAttribute('data-official');
            if (currentPath.includes(freqPath) && isOfficial) {
                targetRedirect = officialPath;
            } else if (currentPath.includes(officialPath) && !isOfficial) {
                targetRedirect = freqPath;
            }
        });

        if (targetRedirect) {
            if (isLocal) {
                window.location.href = targetRedirect;
            } else {
                window.location.href = '/reports/' + targetRedirect;
            }
        }
    }

    // [설계 의도] 페이지 로드 시 현재 페이지 파일명에 매핑되는 모드 스위치 상태 및 배지 컬러를 활성화합니다.
    function initDashboardNav() {
        const toggle = document.getElementById('dashboard-mode-toggle');
        const currentPath = window.location.pathname;
        const isOfficialPage = currentPath.includes('official_scopes');
        
        if (toggle) {
            toggle.checked = isOfficialPage;
            // 라벨 색상 하이라이트 초기화
            document.getElementById('label-freq').style.color = isOfficialPage ? 'var(--text-secondary)' : '#ffffff';
            document.getElementById('label-official').style.color = isOfficialPage ? '#ffffff' : 'var(--text-secondary)';
        }

        const badges = document.querySelectorAll('.subject-badge');
        const isLocal = window.location.protocol === 'file:';
        
        badges.forEach(badge => {
            const target = isOfficialPage ? badge.getAttribute('data-official') : badge.getAttribute('data-freq');
            if (isLocal) {
                badge.href = target;
            } else {
                badge.href = '/reports/' + target;
            }

            // 활성화 배지 하이라이트 (현재 페이지 파일명이 target을 포함하는 경우)
            if (currentPath.includes(target)) {
                badge.classList.add('accent');
                badge.style.color = '#ffffff';
                badge.style.background = 'rgba(139, 92, 246, 0.12)';
                badge.style.borderColor = 'rgba(139, 92, 246, 0.25)';
            } else {
                badge.classList.remove('accent');
            }
        });
    }

    // DOMContentLoaded 시점에 즉시 내비게이션 초기화 적용
    document.addEventListener('DOMContentLoaded', initDashboardNav);
"""

def patch_builder(file_path):
    """[설계 의도] 개별 빌더 파이썬 스크립트 파일을 읽어와 HTML 템플릿의 CSS, HTML, JS를 패치합니다."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. CSS 스타일 패치 (</style> 태그 직전 주입)
    if "/* [설계 의도] 시안A: 모드 토글 스위치 및 최적화된 내비게이션 스타일 */" not in content:
        content = content.replace("</style>", NEW_CSS + "\n    </style>")
        print(f"  - CSS 스타일 추가 완료")

    # 2. 기존 goToHome 스크립트 블록이 있으면 제거 (새로운 JS 로직에 통합)
    goToHome_pattern = r"<script>\s*// \[설계 의도\] 로컬 오프라인 실행.*?goToHome.*?<\/script>"
    content = re.sub(goToHome_pattern, "", content, flags=re.DOTALL)

    # 3. 🏠 퀴즈 홈으로가 포함된 첫 번째 뱃지 묶음 영역 교체
    # (span 또는 a 태그 등으로 다르게 구성된 뱃지 묶음 영역 매치)
    badge_group_pattern = r'<div class="meta-badges"[^>]*>.*?🏠 퀴즈 홈으로.*?</div>'
    match = re.search(badge_group_pattern, content, re.DOTALL)
    if match:
        content = content.replace(match.group(0), NEW_HTML)
        print(f"  - HTML 내비게이션 뱃지 마크업 교체 완료")
    else:
        print(f"  - [경고] 내비게이션 뱃지 마크업 영역을 매칭하지 못했습니다.")

    # 4. 공통 JS 제어 함수 주입
    # 메인 <script> 태그 직후에 새로운 JS 코드 추가
    if "function toggleDashboardMode(toggleEl)" not in content:
        # DB official 뷰어의 경우 script 구조가 살짝 다를 수 있으므로 두 조건에 대응
        script_pattern1 = r"<script>\s*const examDatabase\s*="
        script_pattern2 = r"<script>\s*// Inject mappings"
        
        if re.search(script_pattern1, content):
            content = re.sub(r"(<script>)", r"\1\n" + NEW_JS, content, count=1)
            print(f"  - JS 제어 로직 주입 완료 (패턴 1)")
        elif re.search(script_pattern2, content):
            content = re.sub(r"(<script>)", r"\1\n" + NEW_JS, content, count=1)
            print(f"  - JS 제어 로직 주입 완료 (패턴 2)")
        else:
            # 기본적으로 <script> 태그가 처음으로 등장하는 곳에 주입
            content = content.replace("<script>", "<script>\n" + NEW_JS, 1)
            print(f"  - JS 제어 로직 주입 완료 (기본 패턴)")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    print("=== [시작] Jolly-Carson 10종 대시보드 시안 A 패치 작업 ===")
    
    workspace_dir = r"e:\jolly-carson"
    for builder in BUILDERS:
        file_path = os.path.join(workspace_dir, builder)
        if not os.path.exists(file_path):
            print(f"❌ 파일을 찾을 수 없습니다: {builder}")
            continue
            
        print(f"\n👉 [{builder}] 패치 가동 중...")
        try:
            patch_builder(file_path)
            print(f"✅ {builder} 패치 성공")
        except Exception as e:
            print(f"❌ {builder} 패치 중 예외 발생: {e}")
            
    print("\n=== [완료] Jolly-Carson 10종 대시보드 시안 A 패치 작업 완료 ===")

if __name__ == "__main__":
    main()
