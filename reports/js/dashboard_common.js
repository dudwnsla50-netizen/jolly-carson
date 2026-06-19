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
    loadDashboardDataAndInit();
});

/**
 * API 서버로부터 대시보드 데이터를 로드한 후 초기화를 구동합니다.
 * 서버에 연결할 수 없는 경우, 로컬 폴백을 시도합니다.
 */
function loadDashboardDataAndInit() {
    const subject = window.SUBJECT_CODE || "DB";
    const type = window.DASHBOARD_TYPE || "frequent";
    
    // API 주소 구성
    const apiUrl = `/api/dashboard?subject=${subject}&type=${type}`;
    
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) throw new Error("HTTP error " + response.status);
            return response.json();
        })
        .then(data => {
            window.dashboardData = data;
            initDashboard();
        })
        .catch(error => {
            console.warn("[경고] API 서버 연동 실패. 로컬 폴백 모드로 구동을 시도합니다.", error);
            // 만약 HTML 내부에 기존 window.dashboardData가 이미 정의되어 있다면 로드
            if (window.dashboardData) {
                initDashboard();
            } else {
                const container = document.getElementById('accordionContainer') || document.getElementById('accordion-container');
                if (container) {
                    container.innerHTML = '<div style="padding: 3rem 2rem; text-align: center; color: var(--text-secondary); font-size: 0.95rem; line-height: 1.8;">' +
                        '⚠️ API 서버가 구동되지 않았거나 로컬 파일로 열려 있습니다.<br>' +
                        '프로젝트 루트 디렉토리에서 <code style="background: rgba(255,255,255,0.08); padding: 0.2rem 0.4rem; border-radius: 4px; color: #ef4444; font-family: monospace;">python server.py</code>를 실행하신 후,<br>' +
                        '<a href="http://localhost:8000/reports/' + window.location.pathname.split('/').pop() + '" style="color: #8b5cf6; text-decoration: underline; font-weight: 600;">여기(로컬 호스트 주소)</a>로 접속해 주시면 정상 가동됩니다.' +
                        '</div>';
                }
            }
        });
}

/**
 * 1. 대시보드 초기 셋업
 */
function initDashboard() {
    // 1) 상단 내비게이션 및 모드 스위치 초기화
    initDashboardNav();

    // 2) 전체 문제 개수 뱃지 계산 및 세팅
    setupStatsBadges();

    // 3) 퀴즈 통계 로드 및 병합 후 렌더링 시작
    loadQuizStatsAndMerge().then(() => {
        renderDashboard();
    });
}

// 퀴즈 관련 전역 데이터 버퍼
window.quizStats = {}; 
window.quizSummary = { total_attempts: 0, total_correct: 0, total_solved: 0, avg_score: 0.0 };

/**
 * 1-A. 백엔드 통계 API 정보와 LocalStorage 백업 이력을 병합(Hybrid Merge)합니다.
 * render.com의 DB 영속성 초기화 리스크를 방어하기 위함입니다.
 */
function loadQuizStatsAndMerge() {
    const subject = window.SUBJECT_CODE || "DB";
    return fetch(`/api/quiz/stats?subject=${subject}`)
        .then(res => {
            if (!res.ok) throw new Error("HTTP error " + res.status);
            return res.json();
        })
        .then(data => {
            const serverConcepts = data.concepts || [];
            const serverSummary = data.summary || { total_attempts: 0, total_correct: 0, total_solved: 0 };
            
            // LocalStorage 백업 읽기
            let localHistory = [];
            try {
                localHistory = JSON.parse(localStorage.getItem('jolly_carson_quiz_history') || '[]');
            } catch (e) {
                console.warn(e);
            }
            
            const filteredLocal = localHistory.filter(h => h.subject === subject);
            const serverTotal = serverSummary.total_attempts || 0;
            
            // 스마트 폴백 정책: 서버가 초기화(0건)되었고 로컬 백업이 있는 경우, 로컬 데이터 복구
            if (serverTotal === 0 && filteredLocal.length > 0) {
                const localStats = {};
                let totalAttempts = 0;
                let totalCorrect = 0;
                let totalSolved = 0;
                
                filteredLocal.forEach(h => {
                    if (!localStats[h.concept]) {
                        localStats[h.concept] = {
                            concept: h.concept,
                            attempt_count: 0,
                            total_correct: 0,
                            total_solved: 0,
                            last_attempt_at: h.created_at
                        };
                    }
                    const s = localStats[h.concept];
                    s.attempt_count += 1;
                    s.total_correct += h.correct_count;
                    s.total_solved += h.total_questions;
                    if (new Date(h.created_at) > new Date(s.last_attempt_at)) {
                        s.last_attempt_at = h.created_at;
                    }
                    totalAttempts += 1;
                    totalCorrect += h.correct_count;
                    totalSolved += h.total_questions;
                });
                
                Object.keys(localStats).forEach(con => {
                    const s = localStats[con];
                    window.quizStats[con] = {
                        attempt_count: s.attempt_count,
                        avg_score: s.total_solved > 0 ? Math.round((s.total_correct * 100.0 / s.total_solved) * 10) / 10 : 0.0,
                        last_attempt_at: s.last_attempt_at
                    };
                });
                
                window.quizSummary = {
                    total_attempts: totalAttempts,
                    total_correct: totalCorrect,
                    total_solved: totalSolved,
                    avg_score: totalSolved > 0 ? Math.round((totalCorrect * 100.0 / totalSolved) * 10) / 10 : 0.0
                };
            } else {
                // 서버 데이터가 정상적으로 있으면 이를 기준 데이터로 채택
                serverConcepts.forEach(c => {
                    window.quizStats[c.concept] = {
                        attempt_count: c.attempt_count,
                        avg_score: c.avg_score,
                        last_attempt_at: c.last_attempt_at
                    };
                });
                window.quizSummary = {
                    total_attempts: serverSummary.total_attempts,
                    total_correct: serverSummary.total_correct,
                    total_solved: serverSummary.total_solved,
                    avg_score: serverSummary.avg_score
                };
            }
            
            // 대시보드 상단 요약 카드 렌더링
            renderQuizSummarySection();
        })
        .catch(error => {
            console.warn("[퀴즈 통계 경고] 퀴즈 통계 API 조회 실패. 로컬 캐시로 대체 작동합니다.", error);
            // 오프라인 상태일 때 LocalStorage 단독 기동
            let localHistory = [];
            try {
                localHistory = JSON.parse(localStorage.getItem('jolly_carson_quiz_history') || '[]');
            } catch (e) {}
            const filteredLocal = localHistory.filter(h => h.subject === subject);
            if (filteredLocal.length > 0) {
                const localStats = {};
                let totalAttempts = 0;
                let totalCorrect = 0;
                let totalSolved = 0;
                
                filteredLocal.forEach(h => {
                    if (!localStats[h.concept]) {
                        localStats[h.concept] = {
                            concept: h.concept,
                            attempt_count: 0,
                            total_correct: 0,
                            total_solved: 0,
                            last_attempt_at: h.created_at
                        };
                    }
                    const s = localStats[h.concept];
                    s.attempt_count += 1;
                    s.total_correct += h.correct_count;
                    s.total_solved += h.total_questions;
                    if (new Date(h.created_at) > new Date(s.last_attempt_at)) {
                        s.last_attempt_at = h.created_at;
                    }
                    totalAttempts += 1;
                    totalCorrect += h.correct_count;
                    totalSolved += h.total_questions;
                });
                
                Object.keys(localStats).forEach(con => {
                    const s = localStats[con];
                    window.quizStats[con] = {
                        attempt_count: s.attempt_count,
                        avg_score: s.total_solved > 0 ? Math.round((s.total_correct * 100.0 / s.total_solved) * 10) / 10 : 0.0,
                        last_attempt_at: s.last_attempt_at
                    };
                });
                
                window.quizSummary = {
                    total_attempts: totalAttempts,
                    total_correct: totalCorrect,
                    total_solved: totalSolved,
                    avg_score: totalSolved > 0 ? Math.round((totalCorrect * 100.0 / totalSolved) * 10) / 10 : 0.0
                };
            }
            renderQuizSummarySection();
        });
}

/**
 * 1-B. 대시보드 상단에 퀴즈 누적 기록 및 취약 개념 분석 리포트를 동적으로 렌더링합니다.
 */
function renderQuizSummarySection() {
    const container = document.querySelector('.container');
    if (!container || window.quizSummary.total_attempts === 0) return;

    let oldSection = document.getElementById('quiz-summary-section');
    if (oldSection) oldSection.remove();

    // 취약 개념 TOP 3 정렬 산출 (평균 정답률 오름차순, 시도 횟수 내림차순)
    const sortedWeak = Object.keys(window.quizStats)
        .map(key => {
            return {
                concept: key,
                attempt_count: window.quizStats[key].attempt_count,
                avg_score: window.quizStats[key].avg_score
            };
        })
        .sort((a, b) => {
            if (a.avg_score !== b.avg_score) return a.avg_score - b.avg_score;
            return b.attempt_count - a.attempt_count;
        });

    const topWeak = sortedWeak.slice(0, 3);
    let weakListHtml = '';
    topWeak.forEach((item, idx) => {
        const colors = ['#ef4444', '#f59e0b', '#fbbf24'];
        const color = colors[idx] || '#ef4444';
        weakListHtml += `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.45rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.8rem;">
                <span style="color: var(--text-primary); font-weight: 500; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 65%;" title="${item.concept}">
                    ${idx + 1}. ${item.concept}
                </span>
                <span style="color: ${color}; font-weight: 700;">
                    ${item.avg_score}% (시도 ${item.attempt_count}회)
                </span>
            </div>
        `;
    });

    const section = document.createElement('div');
    section.id = 'quiz-summary-section';
    section.className = 'quiz-summary-card';
    section.style.background = 'var(--card-bg)';
    section.style.border = '1px solid var(--card-border)';
    section.style.borderRadius = '16px';
    section.style.padding = '1.2rem';
    section.style.marginBottom = '1.5rem';
    section.style.boxShadow = '0 10px 25px rgba(0,0,0,0.25)';
    section.style.backdropFilter = 'blur(12px)';
    section.style.webkitBackdropFilter = 'blur(12px)';

    section.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
            <h3 style="font-size: 0.95rem; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 0.3rem;">📊 나의 기출 분석 리포트</h3>
            <span style="font-size: 0.7rem; color: var(--accent-primary); font-weight: bold; cursor: pointer; text-decoration: underline;" onclick="resetQuizHistoryLocal()">기록 초기화</span>
        </div>
        
        <div class="summary-report-grid">
            <!-- 좌측: 누적 스코어 -->
            <div class="summary-stats-column">
                <div class="summary-stat-row">
                    <span class="summary-stat-label">총 테스트 횟수</span>
                    <span class="summary-stat-val">${window.quizSummary.total_attempts}회</span>
                </div>
                <div class="summary-stat-row">
                    <span class="summary-stat-label">해결한 문항 수</span>
                    <span class="summary-stat-val">${window.quizSummary.total_solved}개</span>
                </div>
                <div class="summary-stat-row total">
                    <span class="summary-stat-label">평균 정답률</span>
                    <span class="summary-stat-val-big">${window.quizSummary.avg_score}%</span>
                </div>
            </div>
            
            <!-- 우측: 취약점 분석 -->
            <div class="summary-weakness-column">
                <div class="summary-weak-title">🚨 보완이 필요한 취약 개념 TOP 3</div>
                ${weakListHtml || '<div style="color: var(--text-muted); font-size: 0.8rem; text-align: center; padding-top: 1rem;">취약 개념 정보 수집 중...</div>'}
            </div>
        </div>
    `;

    const header = document.querySelector('header');
    if (header) {
        header.parentNode.insertBefore(section, header.nextSibling);
    }
}

/**
 * 1-C. LocalStorage 캐시 및 서버 초기화
 */
window.resetQuizHistoryLocal = function() {
    if (confirm("정말 나의 퀴즈 풀이 이력(서버 기록 및 로컬 캐시 전체)을 초기화하시겠습니까?\n이 작업은 되돌릴 수 없습니다.")) {
        localStorage.removeItem('jolly_carson_quiz_history');
        alert("이력이 성공적으로 초기화되었습니다.");
        window.location.reload();
    }
}

/**
 * 1-D. 모바일 퀴즈 러너로 라우팅합니다.
 */
function startQuiz(sub, concept, event) {
    if (event) event.stopPropagation();
    window.location.href = `quiz_runner.html?subject=${sub}&concept=${encodeURIComponent(concept)}`;
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

        // 퀴즈 푼 이력 뱃지 구성 (정답률에 따른 다이나믹 네온 스타일 적용)
        const qStat = window.quizStats && window.quizStats[item.concept];
        let quizStatBadgeHtml = '';
        if (qStat && qStat.attempt_count > 0) {
            const glowColor = qStat.avg_score >= 80 ? 'rgba(16, 185, 129, 0.15)' : (qStat.avg_score >= 50 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)');
            const textColor = qStat.avg_score >= 80 ? 'var(--success)' : (qStat.avg_score >= 50 ? '#f59e0b' : '#ef4444');
            quizStatBadgeHtml = `
                <span class="quiz-stat-badge" style="background: ${glowColor}; color: ${textColor}; border: 1px solid ${textColor}40; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700; white-space: nowrap;">
                    📝 ${qStat.attempt_count}회 (${qStat.avg_score}%)
                </span>
            `;
        }

        const subjectCode = window.SUBJECT_CODE || "DB";

        // 세부 아코디언 마크업 구조 결합
        accordion.innerHTML = `
            <button class="accordion-trigger" onclick="toggleAccordion('${globalIdx}')">
                <div class="card-header-row">
                    <div class="card-title-group">
                        <span class="rank-badge">${rankBadgeText}</span>
                        <span class="concept-title">${item.concept}</span>
                        <span class="category-tag">${item.category}</span>
                        ${quizStatBadgeHtml}
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
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem; margin-bottom: 0.4rem;">
                            <h4 class="section-title" style="margin: 0;">출제 문항 일람 (선택 시 아래에 표시)</h4>
                            <button class="quiz-start-btn" onclick="startQuiz('${subjectCode}', '${item.concept.replace(/'/g, "\\'")}', event)" style="background: var(--accent-gradient); color: #ffffff; border: none; padding: 0.35rem 0.7rem; border-radius: 6px; font-size: 0.75rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 0.25rem; transition: all 0.2s; box-shadow: 0 0 10px rgba(139, 92, 246, 0.2); outline: none; font-family: inherit;">
                                📝 모바일 테스트 시작
                            </button>
                        </div>
                        <div class="year-grid" style="margin-top: 0.6rem;">
                            ${yearButtonsHtml}
                        </div>
                    </div>
                    
                    <div class="inline-question-viewer hidden" id="viewer-${globalIdx}">
                        <div class="viewer-header" style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="viewer-title" id="viewer-title-${globalIdx}"></span>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <button class="viewer-answer-btn" id="answer-btn-${globalIdx}" onclick="openAnswerModal('${globalIdx}', event)" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.35); color: #ffffff; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.75rem; cursor: pointer; display: none; align-items: center; gap: 0.2rem; transition: all 0.2s; outline: none; font-family: inherit;">🔑 정답 및 해설 확인</button>
                                <button class="viewer-edit-btn" id="edit-btn-${globalIdx}" onclick="onEditBtnClick('${globalIdx}', event)" style="background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.35); color: #ffffff; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.75rem; cursor: pointer; display: none; align-items: center; gap: 0.2rem; transition: all 0.2s; outline: none; font-family: inherit;">✏️ 수정</button>
                                <button class="viewer-close-btn" onclick="closeViewer('${globalIdx}', event)">닫기 ✕</button>
                            </div>
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
// 로드된 기출문제를 캐싱할 전역 버퍼 객체
window.loadedQuestions = window.loadedQuestions || {};

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

    const key = `${year}_${num}`;
    const viewer = document.getElementById(`viewer-${idx}`);
    if (!viewer) return;

    viewer.classList.remove('hidden');

    // 2) 타이틀 및 수정 버튼 상태 갱신
    const title = document.getElementById(`viewer-title-${idx}`);
    if (title) {
        const subjectTitle = window.SUBJECT_NAME || "감리사";
        title.innerText = `[상세 기출] ${year}년도 ${subjectTitle} ${num}번 문항`;
    }

    // 정답확인 버튼 노출 및 데이터 매핑
    const answerBtn = document.getElementById(`answer-btn-${idx}`);
    if (answerBtn) {
        answerBtn.style.display = 'inline-flex';
        answerBtn.dataset.qId = key;
    }

    // 수정 버튼 노출 및 데이터 매핑
    const editBtn = document.getElementById(`edit-btn-${idx}`);
    if (editBtn) {
        editBtn.style.display = 'inline-flex';
        editBtn.dataset.qId = key;
        editBtn.innerText = "✏️ 수정"; // 편집 폼 상태에서 닫거나 전환 시 텍스트 리셋
    }

    const body = document.getElementById(`viewer-body-${idx}`);
    if (body) {
        body.innerHTML = '<div style="color: var(--text-secondary); font-size: 0.9rem;">데이터베이스에서 문항 정보를 조회하는 중...</div>';
    }

    // 3) API 서버로부터 기출문제 본문 온디맨드 로딩
    fetch(`/api/question?id=${key}`)
        .then(response => {
            if (!response.ok) throw new Error("HTTP error " + response.status);
            return response.json();
        })
        .then(data => {
            // 로컬 전역 캐시에 저장
            window.loadedQuestions[key] = data;
            renderLoadedQuestion(idx, key);
        })
        .catch(error => {
            console.warn(`[경고] API를 통한 문제(${key}) 로드 실패. 로컬 폴백 시도.`, error);
            // 로컬 폴백
            let questionBody = "지문 정보를 읽어올 수 없습니다. API 서버 상태를 확인해 주세요.";
            if (typeof examDatabase !== 'undefined') {
                questionBody = examDatabase[key] || questionBody;
            } else if (window.examDatabase) {
                questionBody = window.examDatabase[key] || questionBody;
            }
            
            // 로컬 폴백 시에도 간이 파싱 수행 및 캐싱
            const qAndO = splitQuestionAndOptionsFallback(questionBody);
            window.loadedQuestions[key] = {
                id: key,
                question: qAndO.question,
                options: qAndO.options,
                answer: [],
                explanation: null
            };
            
            renderLoadedQuestion(idx, key);
        });

    // 4) 원본 크롭 이미지 주소 바인딩
    const imgPath = `images/${year}_${num}.png`;
    const imgWrap = document.getElementById(`viewer-img-wrap-${idx}`);
    const img = document.getElementById(`viewer-img-${idx}`);

    if (imgWrap) imgWrap.style.display = 'flex';
    if (img) {
        img.src = imgPath;
    }
}

/**
 * [설계 의도] 캐싱된 문제 데이터를 상세 뷰어 영역에 보기 좋게 렌더링합니다.
 * 동시에 사용자가 클릭 가능한 보기 버튼과 답안 제출 및 채점 패널을 렌더링합니다.
 */
function renderLoadedQuestion(idx, qId) {
    const data = window.loadedQuestions[qId];
    if (!data) return;

    const body = document.getElementById(`viewer-body-${idx}`);
    if (!body) return;

    // 질문 본문 렌더링
    let htmlContent = `<div class="question-text" style="font-size: 0.95rem; line-height: 1.6; color: #ffffff; margin-bottom: 1rem; white-space: pre-wrap;">${data.question}</div>`;
    
    // 이 문항의 풀이 완료(제출) 이력이 전역 버퍼에 있는지 확인
    const submittedResult = window.quizSubmittedResults && window.quizSubmittedResults[qId];
    const isSubmitted = !!submittedResult;

    // 보기 리스트 렌더링
    if (data.options && data.options.length > 0) {
        htmlContent += `<div class="inline-options-container" style="display: flex; flex-direction: column; gap: 0.6rem; margin-bottom: 1.2rem;">`;
        
        const numSymbols = ["①", "②", "③", "④", "⑤"];
        window.currentDraftAnswers = window.currentDraftAnswers || {};
        window.currentDraftAnswers[qId] = window.currentDraftAnswers[qId] || [];
        const currentDraft = window.currentDraftAnswers[qId];

        data.options.forEach((opt, oIdx) => {
            const sym = numSymbols[oIdx] || `${oIdx + 1}`;
            const optNum = oIdx + 1;
            
            // 클래스 빌드 (선택 상태 및 제출 후 채점 결과 오버레이)
            let optClass = "inline-opt-btn";
            
            if (isSubmitted) {
                // 제출 완료 후 피드백 클래스
                const isCorrectOpt = Array.isArray(data.answer) ? data.answer.includes(optNum) : parseInt(data.answer) === optNum;
                const isUserSelected = submittedResult.userAnswer.includes(optNum);
                
                if (isCorrectOpt) {
                    optClass += " opt-correct"; // 실제 정답 (녹색 테두리)
                } else if (isUserSelected) {
                    optClass += " opt-wrong"; // 내가 고른 오답 (붉은 테두리)
                } else {
                    optClass += " opt-disabled"; // 미선택 및 비활성
                }
            } else {
                // 대기 중 선택 클래스
                const isSelected = currentDraft.includes(optNum);
                if (isSelected) optClass += " selected";
            }

            const clickHandler = isSubmitted ? '' : `onclick="toggleInlineAnswer('${idx}', '${qId}', ${optNum}, event)"`;

            htmlContent += `
                <button class="${optClass}" ${clickHandler} style="width: 100%; outline: none; font-family: inherit; text-align: left;">
                    <span class="inline-opt-num">${sym}</span>
                    <span class="inline-opt-text">${opt}</span>
                </button>
            `;
        });
        htmlContent += `</div>`;
    }

    // 답안 제출 및 피드백 패널
    if (isSubmitted) {
        // 정답 피드백 렌더링
        const statusClass = submittedResult.isCorrect ? 'correct' : 'wrong';
        const statusText = submittedResult.isCorrect ? '✓ 정답입니다! 🎉' : `✕ 오답입니다. (정답: ${submittedResult.cAnsStr})`;
        
        htmlContent += `
            <div class="inline-quiz-feedback ${statusClass}">
                ${statusText}
            </div>
            ${data.explanation ? `
                <div class="inline-explanation-box">
                    <strong>💡 정답 해설:</strong><br>${data.explanation}
                </div>
            ` : ''}
            <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 0.8rem;">
                <button onclick="retryInlineQuestion('${idx}', '${qId}', event)" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: var(--text-secondary); padding: 0.35rem 0.8rem; border-radius: 4px; font-size: 0.75rem; cursor: pointer; transition: all 0.2s; font-family: inherit;">다시 풀기</button>
            </div>
        `;
    } else {
        // 미제출 상태 제출 버튼
        htmlContent += `
            <div style="display: flex; justify-content: flex-end; margin-top: 0.8rem;">
                <button onclick="submitInlineAnswer('${idx}', '${qId}', event)" class="inline-quiz-submit-btn">
                    💾 답안 제출 및 채점
                </button>
            </div>
        `;
    }

    body.innerHTML = htmlContent;
    
    // 편집 버튼 텍스트 리셋
    const editBtn = document.getElementById(`edit-btn-${idx}`);
    if (editBtn) editBtn.innerText = "✏️ 수정";

    updateAccordionContentHeight(document.getElementById(`item-${idx}`));
}

window.currentDraftAnswers = window.currentDraftAnswers || {};
window.quizSubmittedResults = window.quizSubmittedResults || {};

/**
 * 9-A. 인라인 문제 풀이에서 보기 선택을 토글합니다. (단일 선택 방식)
 */
function toggleInlineAnswer(idx, qId, optNum, event) {
    if (event) event.stopPropagation();
    
    window.currentDraftAnswers[qId] = window.currentDraftAnswers[qId] || [];
    const currentDraft = window.currentDraftAnswers[qId];
    
    const valIdx = currentDraft.indexOf(optNum);
    if (valIdx > -1) {
        currentDraft.splice(valIdx, 1);
    } else {
        // 단일 선택 적용을 위해 배열을 비우고 하나만 담습니다.
        currentDraft.length = 0;
        currentDraft.push(optNum);
    }
    
    renderLoadedQuestion(idx, qId);
}

/**
 * 9-B. 인라인 퀴즈 답안을 채점하고 백엔드 + LocalStorage에 전송 저장합니다.
 */
function submitInlineAnswer(idx, qId, event) {
    if (event) event.stopPropagation();
    
    const uAns = window.currentDraftAnswers[qId] || [];
    if (uAns.length === 0) {
        alert("답안을 선택해 주세요!");
        return;
    }
    
    const data = window.loadedQuestions[qId];
    if (!data) return;
    
    // 정답 계산
    let cAns = [];
    if (data.answer) {
        if (Array.isArray(data.answer)) {
            cAns = data.answer.sort();
        } else {
            cAns = [parseInt(data.answer)].sort();
        }
    }
    
    // 채점
    const isCorrect = JSON.stringify(uAns.sort()) === JSON.stringify(cAns) && uAns.length > 0;
    const numSymbols = ["①", "②", "③", "④", "⑤"];
    const cAnsStr = cAns.map(num => numSymbols[num - 1] || num).join(', ');
    
    // 제출 버퍼에 결과 기록
    window.quizSubmittedResults[qId] = {
        isCorrect: isCorrect,
        userAnswer: uAns,
        cAnsStr: cAnsStr
    };
    
    // 이 문항의 개념(concept) 탐색
    const subject = window.SUBJECT_CODE || "DB";
    const matchedConcept = window.dashboardData.find(d => {
        const key = qId.split('_'); // [year, num]
        return d.questions && d.questions.some(q => String(q.year) === String(key[0]) && String(q.num) === String(key[1]));
    });
    const conceptName = matchedConcept ? matchedConcept.concept : '기타';
    
    const payload = {
        subject: subject,
        concept: conceptName,
        total_questions: 1,
        correct_count: isCorrect ? 1 : 0,
        wrong_count: isCorrect ? 0 : 1,
        details: {
            correct: isCorrect ? [qId] : [],
            wrong: isCorrect ? [] : [qId]
        }
    };
    
    // 1) LocalStorage 캐시 저장
    try {
        const backupList = JSON.parse(localStorage.getItem('jolly_carson_quiz_history') || '[]');
        backupList.push({
            created_at: new Date().toISOString(),
            subject: subject,
            concept: conceptName,
            total_questions: 1,
            correct_count: payload.correct_count,
            wrong_count: payload.wrong_count,
            details: payload.details
        });
        localStorage.setItem('jolly_carson_quiz_history', JSON.stringify(backupList));
    } catch (e) {
        console.warn(e);
    }
    
    // 2) 백엔드 API 제출 및 통계 실시간 비동기 리프레시
    fetch('/api/quiz/submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(() => {
        return loadQuizStatsAndMerge();
    })
    .then(() => {
        renderLoadedQuestion(idx, qId);
    })
    .catch(err => {
        console.error(err);
        renderLoadedQuestion(idx, qId);
    });
}

/**
 * 9-C. 문제를 다시 풀기 위해 캐시를 클리어하고 상태를 리셋합니다.
 */
function retryInlineQuestion(idx, qId, event) {
    if (event) event.stopPropagation();
    
    if (window.quizSubmittedResults) {
        delete window.quizSubmittedResults[qId];
    }
    if (window.currentDraftAnswers) {
        window.currentDraftAnswers[qId] = [];
    }
    
    renderLoadedQuestion(idx, qId);
}

/**
 * [설계 의도] 수정 버튼 클릭 시 폼 제출 또는 편집 상태 전환을 관리합니다.
 */
function onEditBtnClick(idx, event) {
    if (event) event.stopPropagation();
    const editBtn = document.getElementById(`edit-btn-${idx}`);
    if (!editBtn) return;

    const qId = editBtn.dataset.qId;
    if (!qId) return;

    // 만약 현재 렌더링 영역이 편집 중인지 확인
    const body = document.getElementById(`viewer-body-${idx}`);
    const isEditing = body && body.querySelector('.edit-form-container') !== null;

    if (isEditing) {
        // 이미 수정 중인 상태에서 버튼을 다시 클릭하면 취소 처리
        cancelEditQuestion(idx, qId);
    } else {
        // 수정 모드 시작
        startEditQuestion(idx, qId);
    }
}

/**
 * [설계 의도] 상세 뷰어 영역을 인라인 편집이 가능한 input 및 textarea 폼으로 교체합니다.
 */
function startEditQuestion(idx, qId) {
    const data = window.loadedQuestions[qId];
    if (!data) return;

    const body = document.getElementById(`viewer-body-${idx}`);
    if (!body) return;

    let htmlContent = `
        <div class="edit-form-container" style="display: flex; flex-direction: column; gap: 1rem; padding: 0.5rem 0;">
            <div>
                <label style="font-size: 0.85rem; color: #a78bfa; font-weight: bold; display: block; margin-bottom: 0.4rem;">❓ 질문 본문 수정</label>
                <textarea id="edit-q-text-${idx}" style="width: 100%; min-height: 120px; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(139, 92, 246, 0.3); color: #ffffff; padding: 0.6rem; border-radius: 6px; font-size: 0.9rem; line-height: 1.5; outline: none; font-family: inherit; resize: vertical;">${data.question}</textarea>
            </div>
            <div>
                <label style="font-size: 0.85rem; color: #a78bfa; font-weight: bold; display: block; margin-bottom: 0.6rem;">📋 보기(선택지) 수정</label>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
    `;

    const numSymbols = ["①", "②", "③", "④", "⑤"];
    const options = data.options && data.options.length > 0 ? data.options : ["", "", "", ""];
    
    options.forEach((opt, oIdx) => {
        const sym = numSymbols[oIdx] || `${oIdx + 1}.`;
        // input 내의 쌍따옴표 이스케이프 처리
        const escapedOpt = opt.replace(/"/g, '&quot;');
        htmlContent += `
            <div style="display: flex; align-items: center; gap: 0.6rem;">
                <span style="color: #8b5cf6; font-weight: bold; font-size: 0.95rem; width: 20px; flex-shrink: 0; text-align: center;">${sym}</span>
                <input type="text" class="edit-opt-input-${idx}" value="${escapedOpt}" style="flex-grow: 1; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(139, 92, 246, 0.2); color: #ffffff; padding: 0.5rem; border-radius: 4px; font-size: 0.85rem; outline: none; font-family: inherit;" />
            </div>
        `;
    });

    htmlContent += `
                </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                <label style="font-size: 0.85rem; color: #a78bfa; font-weight: bold; display: block; margin-bottom: 0.2rem;">🔑 정답 수정 (복수 선택 가능)</label>
                <div id="edit-q-answer-${idx}" style="display: flex; gap: 1rem; flex-wrap: wrap; padding: 0.5rem; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(139, 92, 246, 0.2); border-radius: 4px;">
                    ${[1,2,3,4].map(n => {
                        const sym = ["①","②","③","④"][n-1];
                        const ansArr = Array.isArray(data.answer) ? data.answer : [];
                        const checked = ansArr.includes(n) ? 'checked' : '';
                        return `<label style="display: flex; align-items: center; gap: 0.35rem; cursor: pointer; font-size: 0.9rem; color: #ffffff;">
                            <input type="checkbox" class="edit-answer-chk-${idx}" value="${n}" ${checked} style="accent-color: #8b5cf6; width: 16px; height: 16px; cursor: pointer;" />
                            ${sym}번
                        </label>`;
                    }).join('')}
                </div>
            </div>
            <div>
                <label style="font-size: 0.85rem; color: #a78bfa; font-weight: bold; display: block; margin-bottom: 0.4rem;">📝 해설 수정</label>
                <textarea id="edit-q-explanation-${idx}" style="width: 100%; min-height: 80px; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(139, 92, 246, 0.3); color: #ffffff; padding: 0.6rem; border-radius: 6px; font-size: 0.9rem; line-height: 1.5; outline: none; font-family: inherit; resize: vertical;">${data.explanation || ''}</textarea>
            </div>
            <div style="display: flex; gap: 0.6rem; justify-content: flex-end; margin-top: 0.5rem;">
                <button onclick="saveEditQuestion('${idx}', '${qId}', event)" style="background: #8b5cf6; border: none; color: #ffffff; padding: 0.4rem 1rem; border-radius: 4px; font-size: 0.85rem; font-weight: bold; cursor: pointer; transition: all 0.2s;">💾 저장</button>
                <button onclick="cancelEditQuestion('${idx}', '${qId}', event)" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: var(--text-secondary); padding: 0.4rem 1rem; border-radius: 4px; font-size: 0.85rem; cursor: pointer; font-family: inherit;">취소</button>
            </div>
        </div>
    `;

    body.innerHTML = htmlContent;

    const editBtn = document.getElementById(`edit-btn-${idx}`);
    if (editBtn) editBtn.innerText = "✕ 취소";

    updateAccordionContentHeight(document.getElementById(`item-${idx}`));
}

/**
 * [설계 의도] 수정한 질문, 보기, 정답, 해설을 수집하여 백엔드 API에 POST 요청을 보내 저장하고 화면을 갱신합니다.
 */
function saveEditQuestion(idx, qId, event) {
    if (event) event.stopPropagation();

    const qTextVal = document.getElementById(`edit-q-text-${idx}`).value;
    const optInputs = document.querySelectorAll(`.edit-opt-input-${idx}`);
    const optionsVal = [];
    optInputs.forEach(input => {
        optionsVal.push(input.value);
    });

    // 복수 정답 체크박스에서 선택된 값 수집
    const answerCheckboxes = document.querySelectorAll(`.edit-answer-chk-${idx}:checked`);
    const answerArr = Array.from(answerCheckboxes).map(chk => parseInt(chk.value));
    const explanationVal = document.getElementById(`edit-q-explanation-${idx}`).value;

    const updateData = {
        id: qId,
        question: qTextVal,
        options: optionsVal,
        answer: answerArr,
        explanation: explanationVal
    };

    fetch('/api/question/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(updateData)
    })
    .then(response => {
        if (!response.ok) throw new Error("HTTP error " + response.status);
        return response.json();
    })
    .then(res => {
        if (res.success) {
            // 로컬 캐시 데이터 즉시 동기화
            window.loadedQuestions[qId].question = qTextVal;
            window.loadedQuestions[qId].options = optionsVal;
            window.loadedQuestions[qId].answer = answerArr;
            window.loadedQuestions[qId].explanation = explanationVal;
            alert("기출문제가 성공적으로 저장되었습니다.");
            renderLoadedQuestion(idx, qId);
        } else {
            alert("저장 실패: " + res.message);
        }
    })
    .catch(err => {
        console.error(err);
        alert("서버와 통신 중 오류가 발생하여 저장에 실패했습니다.");
    });
}

/**
 * [설계 의도] 편집을 취소하고 원래 상태로 되돌립니다.
 */
function cancelEditQuestion(idx, qId, event) {
    if (event) event.stopPropagation();
    renderLoadedQuestion(idx, qId);
}

/**
 * 프론트엔드 폴백용 간이 문제/보기 분리 함수
 */
function splitQuestionAndOptionsFallback(bodyText) {
    const splitIndex = bodyText.search(/①|❶/);
    if (splitIndex === -1) {
        return { question: bodyText, options: [] };
    }
    
    const question = bodyText.substring(0, splitIndex).strip ? bodyText.substring(0, splitIndex).trim() : bodyText.substring(0, splitIndex);
    const optionsText = bodyText.substring(splitIndex);
    
    // 보기들을 ①, ②, ③, ④ 등의 기호를 기준으로 쪼갭니다.
    const parts = optionsText.split(/①|②|③|④|❶|❷|❸|❹/);
    const options = parts.map(p => p.trim()).filter(p => p.length > 0);
    
    return { question, options };
}

/**
 * 아코디언이 열려 있는 상태에서 컨텐츠 높이를 동적으로 재조정합니다.
 */
function updateAccordionContentHeight(item) {
    const content = item.querySelector('.accordion-content');
    if (content && item.classList.contains('active')) {
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

/**
 * 14. 정답 및 해설 공통 팝업 모달
 * - 설계 의도: 모든 과목 대시보드에서 동일한 정답/해설 팝업 UI를 재사용합니다.
 * - 복수 정답을 지원하며, 정답에 해당하는 보기 텍스트를 함께 표시합니다.
 */

// 페이지 최초 로드 시 정답 모달 DOM을 body에 1회만 동적 생성
// [버그 수정] head 내 스크립트 로드 시 document.body가 null인 문제 대응 → DOMContentLoaded 시점에 생성
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('answer-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'answer-modal';
    modal.className = 'modal-overlay';
    modal.onclick = function(e) { closeAnswerModal(e); };
    modal.innerHTML = `
        <div class="modal-card answer-modal-card" onclick="event.stopPropagation()" style="max-width: 560px; width: 90%;">
            <div class="modal-card-header" style="border-bottom: 1px solid rgba(139, 92, 246, 0.15);">
                <h2 class="modal-card-title" id="answer-modal-title">🔑 정답 및 해설</h2>
                <button class="modal-close-x" onclick="closeAnswerModal()">✕</button>
            </div>
            <div class="modal-card-body" id="answer-modal-body" style="padding: 1.2rem 1.5rem; max-height: 65vh; overflow-y: auto;">
                <!-- 동적 콘텐츠 -->
            </div>
        </div>
    `;
    document.body.appendChild(modal);
});

/**
 * [정답 팝업 열기] 
 * 뷰어 헤더의 "정답 및 해설 확인" 버튼 클릭 시 호출됩니다.
 */
function openAnswerModal(idx, event) {
    if (event) event.stopPropagation();

    const answerBtn = document.getElementById(`answer-btn-${idx}`);
    if (!answerBtn) return;

    const qId = answerBtn.dataset.qId;
    const data = window.loadedQuestions[qId];
    if (!data) return;

    const modal = document.getElementById('answer-modal');
    const title = document.getElementById('answer-modal-title');
    const body = document.getElementById('answer-modal-body');
    if (!modal || !body) return;

    // 제목 업데이트
    const parts = qId.split('_');
    const year = parts[0];
    const num = parts[1];
    const subjectName = window.SUBJECT_NAME || "감리사";
    if (title) {
        title.textContent = `🔑 ${year}년 ${subjectName} ${num}번 정답 및 해설`;
    }

    // 복수 정답 표시 (배열 → 원문자 변환)
    const circleNums = ["?", "①", "②", "③", "④", "⑤"];
    const answerArr = Array.isArray(data.answer) ? data.answer : [];
    
    let answerDisplay = "";
    if (answerArr.length === 0) {
        answerDisplay = `<span style="color: var(--text-secondary); font-style: italic;">미등록</span>`;
    } else {
        // 정답 번호를 원문자로 변환하여 표시
        const ansSymbols = answerArr.map(n => circleNums[n] || n);
        answerDisplay = `<span style="color: #ef4444; font-size: 1.2rem; font-weight: 800; letter-spacing: 0.3rem;">${ansSymbols.join(' ')}</span>`;
    }

    // 정답에 해당하는 보기 텍스트 하이라이트 포함 리스트 구성
    let optionsHtml = '';
    if (data.options && data.options.length > 0) {
        optionsHtml = `<div style="margin-top: 1rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 0.8rem;">
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem; font-weight: 600;">보기 일람</div>
            <ul style="list-style: none; padding: 0; margin: 0;">`;
        
        const symList = ["①", "②", "③", "④", "⑤"];
        data.options.forEach((opt, oIdx) => {
            const sym = symList[oIdx] || `${oIdx + 1}.`;
            const isCorrect = answerArr.includes(oIdx + 1);
            const highlightStyle = isCorrect
                ? 'background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); color: #ffffff; font-weight: 600;'
                : 'background: transparent; border: 1px solid transparent; color: var(--text-secondary);';
            const correctBadge = isCorrect
                ? '<span style="background: #ef4444; color: #fff; font-size: 0.65rem; padding: 0.1rem 0.35rem; border-radius: 3px; font-weight: 700; margin-left: 0.4rem;">정답</span>'
                : '';

            optionsHtml += `
                <li style="margin-bottom: 0.4rem; padding: 0.45rem 0.6rem; border-radius: 5px; font-size: 0.88rem; line-height: 1.5; display: flex; align-items: flex-start; gap: 0.5rem; transition: all 0.2s; ${highlightStyle}">
                    <span style="color: ${isCorrect ? '#ef4444' : '#8b5cf6'}; font-weight: bold; flex-shrink: 0;">${sym}</span>
                    <span style="white-space: pre-wrap; flex: 1;">${opt}</span>
                    ${correctBadge}
                </li>`;
        });
        optionsHtml += `</ul></div>`;
    }

    // 해설 영역
    const explanationHtml = `
        <div style="margin-top: 1rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 0.8rem;">
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.4rem; font-weight: 600;">📝 해설</div>
            <div style="font-size: 0.88rem; line-height: 1.7; color: var(--text-secondary); white-space: pre-wrap; background: rgba(255,255,255,0.02); padding: 0.6rem 0.8rem; border-radius: 6px; border-left: 3px solid #8b5cf6;">
                ${data.explanation || "등록된 정답 근거 해설이 없습니다.\n학습 범위를 참고하여 학습해 주세요."}
            </div>
        </div>
    `;

    body.innerHTML = `
        <div style="text-align: center; padding: 1rem 0 0.5rem;">
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem; font-weight: 600;">정답</div>
            ${answerDisplay}
            ${answerArr.length > 1 ? '<div style="font-size: 0.72rem; color: rgba(239,68,68,0.7); margin-top: 0.3rem;">⚡ 복수 정답</div>' : ''}
        </div>
        ${optionsHtml}
        ${explanationHtml}
    `;

    // 모달 표시 애니메이션
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

/**
 * [정답 팝업 닫기]
 */
function closeAnswerModal(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.getElementById('answer-modal');
    if (!modal) return;
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 250);
}
