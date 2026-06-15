/**
 * ==========================================================================
 * [Jolly-Carson 기출 분석 대시보드 공통 스크립트 - dashboard_common.js]
 * - 작성 목적: 대시보드 내 아코디언 렌더링, 필터링, 이미지 크롭 뷰어 연동 및 모드 토글을 공통화합니다.
 * - 설계 특징: HTML 내에서 선언한 DASHBOARD_TYPE("official" / "frequent")에 맞춰 
 *             UI 구성을 실시간으로 커스터마이징 렌더링합니다.
 * ==========================================================================
 */

// 페이지 로드 완료 시 초기화 구동
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
});

/**
 * 1. 대시보드 초기 셋업
 */
function initDashboard() {
    // 1) 상단 내비게이션 및 모드 스위치 초기화
    initDashboardNav();

    // 2) 전체 문제 개수 뱃지 계산 및 세팅
    setupStatsBadges();

    // 3) 대시보드 아코디언 목록 최초 렌더링
    renderDashboard();
}

/**
 * 2. 상단 헤더의 통계 뱃지 데이터 자동 계산
 */
function setupStatsBadges() {
    const topicCountEl = document.getElementById('topic-count-badge');
    const totalQuestionEl = document.getElementById('total-question-badge');

    if (topicCountEl && window.dashboardData) {
        topicCountEl.textContent = window.dashboardData.length;
    }

    if (totalQuestionEl && window.dashboardData) {
        const uniqueQuestions = new Set();
        window.dashboardData.forEach(item => {
            if (item.questions) {
                item.questions.forEach(q => {
                    uniqueQuestions.add(`${q.year}_${q.num}`);
                });
            }
        });
        totalQuestionEl.textContent = uniqueQuestions.size;
    }
}

/**
 * 3. 퀴즈 홈 이동 (로컬 file:/// 및 웹 서버 경로 분기 처리)
 */
function goToHome(event) {
    if (event) event.preventDefault();
    if (window.location.protocol === 'file:') {
        window.location.href = '../index.html';
    } else {
        window.location.href = '/';
    }
}

/**
 * 4. 빈출순 🔥 <-> 공식범위순 📋 토글 제어 및 즉시 이동
 */
function toggleDashboardMode(toggleEl) {
    const isOfficial = toggleEl.checked;

    // 라벨 텍스트 하이라이트 색상 교체
    const freqLabel = document.getElementById('label-freq');
    const officialLabel = document.getElementById('label-official');
    if (freqLabel) freqLabel.style.color = isOfficial ? 'var(--text-secondary)' : '#ffffff';
    if (officialLabel) officialLabel.style.color = isOfficial ? '#ffffff' : 'var(--text-secondary)';

    // 상단 과목 배지들의 링크 이동 타겟 정보 갱신
    const badges = document.querySelectorAll('.subject-badge');
    badges.forEach(badge => {
        const target = isOfficial ? badge.getAttribute('data-official') : badge.getAttribute('data-freq');
        if (target) {
            badge.href = target + '?v=20260613';
        }
    });

    // 현재 과목의 반대편 모드 뷰어로 리다이렉트 수행
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
        window.location.href = targetRedirect + '?v=20260613';
    }
}

/**
 * 5. 페이지 진입 시 내비게이션바 하이라이트 매핑
 */
function initDashboardNav() {
    const toggle = document.getElementById('dashboard-mode-toggle');
    const currentPath = window.location.pathname;
    const isOfficialPage = currentPath.includes('official_scopes');

    if (toggle) {
        toggle.checked = isOfficialPage;
        const freqLabel = document.getElementById('label-freq');
        const officialLabel = document.getElementById('label-official');
        if (freqLabel) freqLabel.style.color = isOfficialPage ? 'var(--text-secondary)' : '#ffffff';
        if (officialLabel) officialLabel.style.color = isOfficialPage ? '#ffffff' : 'var(--text-secondary)';
    }

    const badges = document.querySelectorAll('.subject-badge');
    badges.forEach(badge => {
        const target = isOfficialPage ? badge.getAttribute('data-official') : badge.getAttribute('data-freq');
        if (target) {
            badge.href = target + '?v=20260613';

            // 현재 페이지 파일명이 타겟 주소와 매칭되면 퍼플 글로우 테마 활성화
            if (currentPath.includes(target)) {
                badge.classList.add('accent');
                badge.style.color = '#ffffff';
                badge.style.background = 'rgba(139, 92, 246, 0.12)';
                badge.style.borderColor = 'rgba(139, 92, 246, 0.25)';
            } else {
                badge.classList.remove('accent');
                badge.style.color = '';
                badge.style.background = '';
                badge.style.borderColor = '';
            }
        }
    });
}

/**
 * 6. 카테고리(대단원) 필터 기능
 */
function filterCategory(category) {
    // 1) 필터 버튼 액티브 토글
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
        const btnTxt = btn.innerText.trim();
        if (btnTxt === category || (category === 'all' && btnTxt === '전체 대단원') || (category === '전체' && btnTxt === '전체')) {
            btn.classList.add('active');
        }
    });

    // 2) 필터링된 아코디언 재렌더링
    renderDashboard(category);
}

/**
 * 7. 아코디언 메인 목록 통합 렌더러
 */
function renderDashboard(filter = 'all') {
    const container = document.getElementById('accordionContainer') || document.getElementById('accordion-container');
    if (!container || !window.dashboardData) return;

    container.innerHTML = '';
    const isOfficial = (window.DASHBOARD_TYPE === 'official');

    // 필터 조건 처리 ('all' 또는 '전체'는 모든 카테고리)
    const filteredData = window.dashboardData.filter(item => {
        if (filter === 'all' || filter === '전체') return true;
        return item.category === filter;
    });

    // 필터링된 카운트 헤더 동기화
    const countBadge = document.getElementById('topic-count-badge');
    if (countBadge) {
        countBadge.textContent = filteredData.length;
    }

    filteredData.forEach((item, index) => {
        // [버그 해결] 빈출순 데이터 등 global_idx가 누락된 데이터셋에서도 고유한 DOM ID를 가질 수 있도록 
        // 루프 인덱스를 활용해 global_idx 값을 보장합니다.
        if (item.global_idx === undefined || item.global_idx === null) {
            item.global_idx = index;
        }
        const globalIdx = item.global_idx;
        const totalCount = item.count;
        const yearsStr = item.years && item.years.length > 0 ? item.years.join(', ') : '없음';

        const accordion = document.createElement('div');
        accordion.className = 'accordion-item';
        accordion.dataset.category = item.category;
        accordion.id = `item-${globalIdx}`;

        // 연도별 기출 선택 버튼 생성
        let yearButtonsHtml = '';
        if (item.questions) {
            item.questions.forEach(q => {
                yearButtonsHtml += `
                    <button class="year-btn q-btn-${q.year}-${q.num}" id="btn-${globalIdx}-${q.year}-${q.num}" onclick="showQuestion('${globalIdx}', ${q.year}, ${q.num}, this)">
                        ${q.year}년 <span class="num-label">${q.num}번</span>
                    </button>
                `;
            });
        }

        // 공식범위순 vs 빈출순 메타 정보 레이아웃 차별화
        let metaGridHtml = '';
        let rankBadgeText = '';

        if (isOfficial) {
            rankBadgeText = item.concept.split('.')[0]; // 예: "1-a"
            metaGridHtml = `
                <div class="meta-label">핵심 요약</div>
                <div class="meta-value">${item.core_concept}</div>
                <div class="meta-label">기출 연도</div>
                <div class="meta-value accent">${yearsStr}</div>
            `;
        } else {
            rankBadgeText = `RANK ${String(globalIdx + 1).padStart(2, '0')}`;
            metaGridHtml = `
                <div class="meta-label">출제 범위</div>
                <div class="meta-value accent">${item.scope}</div>
                <div class="meta-label">핵심 개념</div>
                <div class="meta-value" style="font-weight: 500; color: #ffffff;">${item.core_concept}</div>
                <div class="meta-label">출제 특징</div>
                <div class="meta-value">${item.features}</div>
                <div class="meta-label">기출 연도</div>
                <div class="meta-value">${yearsStr}년</div>
            `;
        }

        // 세부 아코디언 마크업 구조 결합
        accordion.innerHTML = `
            <button class="accordion-trigger" onclick="toggleAccordion('${globalIdx}')">
                <div class="card-header-row">
                    <div class="card-title-group">
                        <span class="rank-badge">${rankBadgeText}</span>
                        <span class="concept-title">${item.concept}</span>
                        <span class="category-tag">${item.category}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.8rem;">
                        <span class="freq-count-badge">기출 ${totalCount}회</span>
                        <span class="arrow">▼</span>
                    </div>
                </div>
                <div class="card-meta-grid">
                    ${metaGridHtml}
                </div>
            </button>
            <div class="accordion-content">
                <div class="accordion-inner">
                    ${isOfficial ? `
                    <div>
                        <h4 class="section-title">출제 범위 및 핵심 특징</h4>
                        <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.4rem; line-height: 1.6;">
                            <strong>세부 범위:</strong> ${item.scope}<br>
                            <strong>핵심 특징:</strong> ${item.features}
                        </p>
                    </div>
                    ` : ''}
                    <div>
                        <h4 class="section-title">출제 문항 일람 (선택 시 아래에 시험지와 원본 크롭 이미지가 표시됩니다)</h4>
                        <div class="year-grid" style="margin-top: 0.6rem;">
                            ${yearButtonsHtml}
                        </div>
                    </div>
                    
                    <div class="inline-question-viewer hidden" id="viewer-${globalIdx}">
                        <div class="viewer-header">
                            <span class="viewer-title" id="viewer-title-${globalIdx}"></span>
                            <button class="viewer-close-btn" onclick="closeViewer('${globalIdx}', event)">닫기 ✕</button>
                        </div>
                        <div class="viewer-body" id="viewer-body-${globalIdx}"></div>
                        
                        <div class="viewer-image-wrapper" id="viewer-img-wrap-${globalIdx}">
                            <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.6rem; font-weight: 700;">
                                ▼ 시험지 원본 이미지 (다이어그램 및 수식 확인용)
                            </div>
                            <img class="viewer-img" id="viewer-img-${globalIdx}" src="" alt="크롭 문제지 영역" onerror="hideImageContainer('${globalIdx}')">
                        </div>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(accordion);
    });
}

/**
 * 8. 아코디언 토글 제어 (대표 문제 자동 노출 탑재)
 */
function toggleAccordion(idx) {
    const item = document.getElementById(`item-${idx}`);
    if (!item) return;

    const content = item.querySelector('.accordion-content');
    const isActive = item.classList.contains('active');

    // 1) 다른 아코디언은 모두 닫기 처리 (사용자 요청에 따라 주석 처리)
    /*
    document.querySelectorAll('.accordion-item').forEach(el => {
        el.classList.remove('active');
        const c = el.querySelector('.accordion-content');
        if (c) c.style.maxHeight = null;
    });
    */

    // 2) 현재 아코디언 활성화 처리
    if (!isActive) {
        item.classList.add('active');

        // 대표 문제가 존재할 경우 대표 문제를 기본적으로 자동 노출
        const targetData = window.dashboardData.find(d => String(d.global_idx) === String(idx));
        if (targetData && targetData.rep_question) {
            const activeBtn = item.querySelector(`.q-btn-${targetData.rep_year}-${targetData.rep_num}`) ||
                document.getElementById(`btn-${idx}-${targetData.rep_year}-${targetData.rep_num}`);
            showQuestion(idx, targetData.rep_year, targetData.rep_num, activeBtn);
        }

        content.style.maxHeight = content.scrollHeight + 1000 + 'px'; // 여유 마진 추가
    } else {
        // [잠재 리스크 보완] 일괄 닫기 로직이 주석처리 됨에 따라,
        // 이미 열려 있는 아코디언을 사용자가 다시 클릭했을 때 정상적으로 닫힐 수 있도록 예외 처리합니다.
        item.classList.remove('active');
        if (content) content.style.maxHeight = null;
    }
}

/**
 * 9. 개별 기출문항 클릭 시 상세 문제지 및 이미지 로드
 */
function showQuestion(idx, year, num, btnElement) {
    // 1) 연도별 클릭 버튼 액티브 스타일 교체
    const item = document.getElementById(`item-${idx}`);
    if (item) {
        item.querySelectorAll('.year-btn').forEach(btn => btn.classList.remove('active-btn'));
    }
    if (btnElement) {
        btnElement.classList.add('active-btn');
    } else {
        const backupBtn = document.getElementById(`btn-${idx}-${year}-${num}`);
        if (backupBtn) backupBtn.classList.add('active-btn');
    }

    // 2) 기출문제 본문 가져오기 (examDatabase 객체 활용)
    const key = `${year}_${num}`;
    let questionBody = "지문 정보를 읽어올 수 없습니다.";
    if (typeof examDatabase !== 'undefined') {
        questionBody = examDatabase[key] || "지문 정보를 읽어올 수 없습니다.";
    } else if (window.examDatabase) {
        questionBody = window.examDatabase[key] || "지문 정보를 읽어올 수 없습니다.";
    }

    const viewer = document.getElementById(`viewer-${idx}`);
    if (!viewer) return;

    viewer.classList.remove('hidden');

    // 3) 타이틀 및 본문 텍스트 갱신
    const title = document.getElementById(`viewer-title-${idx}`);
    if (title) {
        const subjectTitle = window.SUBJECT_NAME || "감리사";
        title.innerText = `[상세 기출] ${year}년도 ${subjectTitle} ${num}번 문항`;
    }

    const body = document.getElementById(`viewer-body-${idx}`);
    if (body) {
        body.innerText = questionBody;
    }

    // 4) 원본 크롭 이미지 주소 바인딩 (로컬/웹서버 지원 분기)
    const isLocal = (window.location.protocol === 'file:');
    const imgPath = isLocal ? `images/${year}_${num}.png` : `images/${year}_${num}.png`;

    const imgWrap = document.getElementById(`viewer-img-wrap-${idx}`);
    const img = document.getElementById(`viewer-img-${idx}`);

    if (imgWrap) imgWrap.style.display = 'flex';
    if (img) {
        img.src = imgPath;
    }

    // 5) 스크롤 영역 높이 갱신
    const content = item.querySelector('.accordion-content');
    if (content) {
        content.style.maxHeight = content.scrollHeight + 500 + 'px';
    }
}

/**
 * 10. 기출문제 뷰어 이미지 없을 때 컨테이너 가림 처리
 */
function hideImageContainer(idx) {
    const imgWrap = document.getElementById(`viewer-img-wrap-${idx}`);
    if (imgWrap) {
        imgWrap.style.display = 'none';
    }
}

/**
 * 11. 기출 상세 뷰어 영역 숨기기
 */
function closeViewer(idx, event) {
    if (event) event.stopPropagation();

    const viewer = document.getElementById(`viewer-${idx}`);
    if (viewer) viewer.classList.add('hidden');

    const item = document.getElementById(`item-${idx}`);
    if (item) {
        item.querySelectorAll('.year-btn').forEach(btn => btn.classList.remove('active-btn'));

        // 아코디언 컨텐트 스크롤 높이 재조정
        const content = item.querySelector('.accordion-content');
        if (content) {
            content.style.maxHeight = content.scrollHeight + 'px';
        }
    }
}

// 닫기 래퍼 호환용
function closeInlineViewer(idx, event) {
    closeViewer(idx, event);
}

/**
 * 12. 세부 토픽 목록 팝업 모달 열기
 */
window.openTopicListModal = function () {
    const modal = document.getElementById('topic-modal');
    const listEl = document.getElementById('modal-topic-list');
    if (!modal || !listEl || !window.dashboardData) return;

    listEl.innerHTML = '';

    window.dashboardData.forEach((item) => {
        const li = document.createElement('li');
        li.className = 'modal-topic-item';
        li.style.cursor = 'pointer';

        // 클릭 시 모달을 닫고 해당 아코디언으로 강제 스크롤 포커스 이동
        li.onclick = () => {
            closeTopicModal();

            // 필터링 적용 중 타겟 카테고리가 달라 가려져 있는 상태라면 필터를 강제 해제
            const activeFilterBtn = document.querySelector('.filter-btn.active');
            const activeFilter = activeFilterBtn ? activeFilterBtn.innerText.trim() : '전체';
            if (activeFilter !== '전체 대단원' && activeFilter !== '전체' && item.category !== activeFilter) {
                filterCategory('all');
            }

            setTimeout(() => {
                const itemEl = document.getElementById(`item-${item.global_idx}`);
                if (itemEl) {
                    const trigger = itemEl.querySelector('.accordion-trigger');
                    const content = itemEl.querySelector('.accordion-content');
                    if (content && (!content.style.maxHeight || content.style.maxHeight === '0px')) {
                        if (trigger) trigger.click();
                    }
                    itemEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 200);
        };

        const countSuffix = window.DASHBOARD_TYPE === 'official' ? '개 문항 매핑' : '회 출제';
        li.innerHTML = `
            <span class="modal-topic-name">${item.concept}</span>
            <span class="modal-topic-count">${item.count}${countSuffix}</span>
        `;
        listEl.appendChild(li);
    });

    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
};

/**
 * 13. 팝업 모달 닫기
 */
window.closeTopicModal = function (event) {
    const modal = document.getElementById('topic-modal');
    if (!modal) return;
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 250);
};
