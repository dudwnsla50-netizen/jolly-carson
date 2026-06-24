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
    updateTabTitleWithDbMode();
});

/**
 * 서버에 설정된 DB 타입(SQLite / Postgres) 정보를 가져와 브라우저 타이틀에 주입합니다.
 */
function updateTabTitleWithDbMode() {
    fetch('/api/db-mode')
        .then(res => res.ok ? res.json() : null)
        .then(data => {
            if (data && data.db_type) {
                const dbTypeStr = data.db_type.toUpperCase();
                // 이미 추가되어 있는 경우 중복 추가 방지
                if (!document.title.includes(`[${dbTypeStr}]`)) {
                    document.title = `${document.title} [${dbTypeStr}]`;
                }
            }
        })
        .catch(err => {
            console.warn("[경고] DB 모드 정보 조회 실패:", err);
        });
}

/**
 * 배열 요소들의 순서를 무작위로 섞은 새로운 배열을 반환합니다. (Fisher-Yates Shuffle)
 */
function shuffleArray(array) {
    if (!array) return [];
    const arr = [...array];
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

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
        if (typeof initGamification === 'function') {
            initGamification();
        }
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

    // [설계 의도] 시간 문자열을 UTC 타임스탬프로 통일하여 정합성 비교를 수행하는 헬퍼 함수
    const getUTCTime = (dateStr) => {
        if (!dateStr) return 0;
        let standardized = dateStr;
        if (!dateStr.includes('T') && dateStr.includes(' ')) {
            standardized = dateStr.replace(' ', 'T') + 'Z';
        } else if (!dateStr.endsWith('Z') && dateStr.includes('T')) {
            standardized = dateStr + 'Z';
        }
        const t = new Date(standardized).getTime();
        return isNaN(t) ? 0 : t;
    };

    return fetch(`/api/quiz/stats?subject=${subject}`)
        .then(res => {
            if (!res.ok) throw new Error("HTTP error " + res.status);
            return res.json();
        })
        .then(data => {
            const mergedLogs = [];
            const serverLogs = data.logs || [];

            serverLogs.forEach(log => {
                if (log.created_at) {
                    let parsedDetails = log.details;
                    if (typeof log.details === 'string') {
                        try {
                            parsedDetails = JSON.parse(log.details);
                        } catch (e) {
                            console.warn("Failed to parse log details", e);
                        }
                    }
                    mergedLogs.push({
                        ...log,
                        details: parsedDetails
                    });
                }
            });

            // LocalStorage 백업 로그 조회 및 하이브리드 병합 (Render DB 휘발 방어)
            try {
                const localHistoryStr = localStorage.getItem('jolly_carson_quiz_history');
                if (localHistoryStr) {
                    const localLogs = JSON.parse(localHistoryStr) || [];
                    localLogs.forEach(localLog => {
                        if (localLog.subject === subject) {
                            const localQId = localLog.details ? localLog.details.q_id : null;
                            const isDuplicate = mergedLogs.some(serverLog => {
                                const serverQId = serverLog.details ? serverLog.details.q_id : null;
                                if (localQId && serverQId && localQId === serverQId) {
                                    // [버그 수정] SQLite 시간(서버 기준 UTC)과 로컬스토리지 시간(KST)의 시차(9시간) 차이로 인해 
                                    // 직접 new Date() 파싱 비교 시 중복 제거 필터(1분)가 실패하던 문제를 getUTCTime으로 정밀 대조하여 해결
                                    const diff = Math.abs(getUTCTime(localLog.created_at) - getUTCTime(serverLog.created_at));
                                    return diff < 60000; // 1분 이내 동일 문항은 중복 간주
                                }
                                return false;
                            });

                            if (!isDuplicate) {
                                mergedLogs.push(localLog);
                            }
                        }
                    });
                }
            } catch (e) {
                console.warn("[로컬스토리지 병합 실패]", e);
            }

            // 시간 정렬을 위해 정밀화된 UTC 타임스탬프 순으로 정렬
            mergedLogs.sort((a, b) => getUTCTime(b.created_at) - getUTCTime(a.created_at));
            window.quizFullHistoryList = mergedLogs;

            // 데이터베이스(서버 로그)를 전적으로 활용하여 실시간 재카운팅(집계)
            recalculateQuizSummaryAndStats();

            // 대시보드 상단 요약 카드 렌더링
            renderQuizSummarySection();
        })
        .catch(error => {
            console.error("[퀴즈 통계 오류] 퀴즈 통계 API 조회 실패.", error);
            window.quizFullHistoryList = [];
            recalculateQuizSummaryAndStats();
            renderQuizSummarySection();
        });
}

/**
 * window.quizFullHistoryList(최종 마스터 로그 배열)를 기반으로
 * 전역 통계 변수(window.quizStats, window.quizSummary)를 직접 전수 재계산(집계)합니다.
 */
function recalculateQuizSummaryAndStats() {
    const conceptStats = {};
    let totalAttempts = 0;
    let totalCorrect = 0;
    let totalSolved = 0;

    (window.quizFullHistoryList || []).forEach(log => {
        // 1) 이 로그가 가리키는 문제 ID가 무엇인지 확인
        let qId = null;
        if (log.details) {
            if (typeof log.details === 'object') {
                qId = log.details.q_id;
            } else {
                try {
                    const parsed = JSON.parse(log.details);
                    qId = parsed.q_id;
                } catch (e) { }
            }
        }

        // 2) 이 q_id를 포함하고 있는 모든 concept들을 dashboardData에서 탐색
        let targetConcepts = [];
        if (qId && window.dashboardData) {
            const parts = qId.split('_'); // [year, num]
            if (parts.length === 2) {
                const yearVal = parts[0];
                const numVal = parts[1];
                window.dashboardData.forEach(d => {
                    const hasQ = d.questions && d.questions.some(q => String(q.year) === String(yearVal) && String(q.num) === String(numVal));
                    if (hasQ) {
                        targetConcepts.push(d.concept);
                    }
                });
            }
        }

        // 3) 만약 찾지 못했다면 폴백으로 로그에 기록된 원래 concept 사용
        if (targetConcepts.length === 0) {
            targetConcepts.push(log.concept || "기타");
        }

        // 4) 탐색된 모든 targetConcepts에 해당 로그의 점수를 각각 가중 누적
        targetConcepts.forEach(con => {
            if (!conceptStats[con]) {
                conceptStats[con] = {
                    concept: con,
                    attempt_count: 0,
                    total_correct: 0,
                    total_solved: 0,
                    last_attempt_at: log.created_at
                };
            }
            const s = conceptStats[con];
            s.attempt_count += 1;
            s.total_correct += (log.correct_count || 0);
            s.total_solved += (log.total_questions || 0);
            if (new Date(log.created_at) > new Date(s.last_attempt_at)) {
                s.last_attempt_at = log.created_at;
            }
        });

        // 5) 전체 시도 요약은 중복 없이 1회만 계산
        totalAttempts += 1;
        totalCorrect += (log.correct_count || 0);
        totalSolved += (log.total_questions || 0);
    });

    // window.quizStats 초기화 및 갱신
    window.quizStats = {};
    Object.keys(conceptStats).forEach(con => {
        const s = conceptStats[con];
        window.quizStats[con] = {
            attempt_count: s.attempt_count,
            avg_score: s.total_solved > 0 ? Math.round((s.total_correct * 100.0 / s.total_solved) * 10) / 10 : 0.0,
            last_attempt_at: s.last_attempt_at
        };
    });

    // window.quizSummary 갱신
    window.quizSummary = {
        total_attempts: totalAttempts,
        total_correct: totalCorrect,
        total_solved: totalSolved,
        avg_score: totalSolved > 0 ? Math.round((totalCorrect * 100.0 / totalSolved) * 10) / 10 : 0.0
    };
}

/**
 * 1-B. 대시보드 상단에 퀴즈 누적 기록 및 취약 개념 분석 리포트를 동적으로 렌더링합니다.
 */
function renderQuizSummarySection() {
    const container = document.querySelector('.container');
    if (!container) return;

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
    if (topWeak.length > 0) {
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
    } else {
        weakListHtml = `
            <div style="color: var(--text-muted); font-size: 0.82rem; text-align: center; padding: 1.2rem 0; line-height: 1.6;">
                📢 아직 테스트한 이력이 없습니다.<br>하단의 문제를 풀면 취약 분석이 시작됩니다.
            </div>
        `;
    }

    const totalAttempts = window.quizSummary ? (window.quizSummary.total_attempts || 0) : 0;
    const totalSolved = window.quizSummary ? (window.quizSummary.total_solved || 0) : 0;
    const avgScore = window.quizSummary ? (window.quizSummary.avg_score || 0) : 0;

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
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; flex-wrap: wrap; gap: 0.5rem;">
            <h3 style="font-size: 0.95rem; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 0.3rem;">📊 나의 기출 분석 리포트</h3>
            <button onclick="startGlobalRolling(event)" style="background: var(--accent-gradient); border: none; color: #ffffff; padding: 0.4rem 0.8rem; border-radius: 8px; font-size: 0.8rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 0.3rem; box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3); transition: all 0.2s; outline: none; font-family: inherit;" onmouseover="this.style.transform='translateY(-1px)'" onmouseout="this.style.transform='none'">
                🔄 전체 문제 롤링 시작
            </button>
        </div>
        
        <div class="summary-report-grid">
            <!-- 좌측: 누적 스코어 -->
            <div class="summary-stats-column">
                <div class="summary-stat-row">
                    <span class="summary-stat-label">총 테스트 횟수</span>
                    <span class="summary-stat-val">${totalAttempts}회</span>
                </div>
                <div class="summary-stat-row">
                    <span class="summary-stat-label">해결한 문항 수</span>
                    <span class="summary-stat-val">${totalSolved}개</span>
                </div>
                <div class="summary-stat-row total">
                    <span class="summary-stat-label">평균 정답률</span>
                    <span class="summary-stat-val-big">${avgScore}%</span>
                </div>
            </div>
            
            <!-- 우측: 취약점 분석 -->
            <div class="summary-weakness-column">
                <div class="summary-weak-title">🚨 보완이 필요한 취약 개념 TOP 3</div>
                ${weakListHtml}
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
window.resetQuizHistoryLocal = function () {
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

    // 오답 복습 배지 동적 삽입 연동
    const navBadges = document.getElementById('dynamic-nav-badges');
    if (navBadges && !document.getElementById('wrong-answers-badge')) {
        const wrongBadge = document.createElement('a');
        wrongBadge.id = 'wrong-answers-badge';
        wrongBadge.href = 'wrong_answers/index.html';
        wrongBadge.className = 'badge';
        wrongBadge.style.textDecoration = 'none';
        wrongBadge.style.background = 'rgba(239, 68, 68, 0.15)';
        wrongBadge.style.borderColor = 'rgba(239, 68, 68, 0.35)';
        wrongBadge.style.color = '#f87171';
        wrongBadge.style.fontWeight = '700';
        wrongBadge.style.borderStyle = 'solid';
        wrongBadge.style.borderWidth = '1px';
        wrongBadge.innerHTML = '❌ 오답 복습';

        const homeBadge = navBadges.querySelector('.home-badge');
        if (homeBadge) {
            homeBadge.parentNode.insertBefore(wrongBadge, homeBadge.nextSibling);
        } else {
            navBadges.appendChild(wrongBadge);
        }
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
                        </div>
                        <div class="year-grid" style="margin-top: 0.6rem;">
                            ${yearButtonsHtml}
                        </div>
                    </div>
                    
                    <div class="inline-question-viewer hidden" id="viewer-${globalIdx}">
                        <div class="viewer-header" style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="viewer-title" id="viewer-title-${globalIdx}"></span>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
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

function showQuestion(idx, year, num, btnElement, isRollingTransition) {
    if (!isRollingTransition) {
        // [설계 의도] 사용자가 아코디언에서 직접 수동으로 문항 단추를 클릭한 경우,
        // 기존 전체 롤링 세션 상태를 로컬 중단원 세션으로 전환될 수 있도록 플래그를 리셋합니다.
        if (window.rollingSession) {
            window.rollingSession.isGlobal = false;
            window.rollingSession.globalIdx = parseInt(idx);
        }
    }

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
        title.innerText = `[상세 기출] ${year}년도 ${num}번 문항`;
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
            // 보기 셔플용 인덱스 배열 생성 및 저장
            if (data && data.options && data.options.length > 0) {
                const indices = Array.from({ length: data.options.length }, (_, i) => i);
                data.shuffledIndices = shuffleArray(indices);
            }
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
            let shuffledIndices = null;
            if (qAndO.options && qAndO.options.length > 0) {
                const indices = Array.from({ length: qAndO.options.length }, (_, i) => i);
                shuffledIndices = shuffleArray(indices);
            }
            window.loadedQuestions[key] = {
                id: key,
                question: qAndO.question,
                options: qAndO.options,
                answer: qAndO.answer,
                explanation: null,
                shuffledIndices: shuffledIndices
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
/**
 * 한국어 형식으로 일시를 포맷팅합니다.
 * 예시: 26년 6월 19일 3시 / 26년 6월 19일 3시 30분
 */
function formatKoreanDate(dateStr) {
    if (!dateStr) return '';
    let standardized = dateStr;
    // SQLite의 'YYYY-MM-DD HH:MM:SS' UTC 형식을 JS가 올바르게 UTC로 인식하도록 'Z' 보정
    if (!dateStr.includes('T') && dateStr.includes(' ')) {
        standardized = dateStr.replace(' ', 'T') + 'Z';
    } else if (!dateStr.endsWith('Z') && dateStr.includes('T')) {
        standardized = dateStr + 'Z';
    }
    const d = new Date(standardized);
    if (isNaN(d.getTime())) return dateStr;
    const yy = String(d.getFullYear()).slice(-2);
    const mm = d.getMonth() + 1;
    const dd = d.getDate();
    const hh = d.getHours();
    const h12 = hh % 12 === 0 ? 12 : hh % 12;
    const min = d.getMinutes();
    const minStr = min > 0 ? ` ${min}분` : '';
    return `${yy}년 ${mm}월 ${dd}일 ${h12}시${minStr}`;
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

    // 다음 문제 이동 버튼 준비 (랜덤 롤링 세션 기반)
    let nextQuestionButtonHtml = '';
    
    // 세션 조회 및 검증
    let session = window.rollingSession;
    let isSessionValid = false;

    if (session && session.isActive) {
        if (session.isGlobal) {
            // 글로벌 세션인 경우: 현재 문제(qId)가 글로벌 세션에 존재하는지만 체크
            isSessionValid = session.questions.some(sq => sq.qId === qId);
        } else {
            // 로컬 중단원 세션인 경우: 현재 중단원(idx)과 세션의 중단원이 일치하며, 
            // 현재 중단원의 문제 목록 크기가 세션 문제 목록 크기와 동일하고, 문제 구성이 일치하는지 체크
            const localQsList = getConceptQuestionsList(idx);
            isSessionValid = (String(session.globalIdx) === String(idx)) &&
                             (session.questions.length === localQsList.length) &&
                             (session.questions.every(sq => localQsList.some(aq => aq.qId === sq.qId)));
        }
    }

    if (!isSessionValid) {
        // 기존 세션이 없거나 유효하지 않다면 새로 세션 개시
        // 아코디언에서 직접 개별 문항을 클릭해 진입한 상황이므로 강제로 "로컬 중단원 롤링 세션"으로 초기화합니다.
        const localQsList = getConceptQuestionsList(idx);
        if (localQsList.length > 0) {
            const otherQs = localQsList.filter(q => q.qId !== qId);
            const shuffledOthers = shuffleArray(otherQs);
            const currentQ = localQsList.find(q => q.qId === qId);

            const newQs = [];
            if (currentQ) newQs.push(currentQ);
            newQs.push(...shuffledOthers);

            window.rollingSession = {
                isActive: true,
                questions: newQs,
                currentIndex: currentQ ? 0 : -1,
                isGlobal: false,
                globalIdx: parseInt(idx)
            };
            session = window.rollingSession;
        }
    } else {
        // 세션이 유효하다면 인덱스만 동기화
        const foundIdx = session.questions.findIndex(q => q.qId === qId);
        if (foundIdx > -1) {
            session.currentIndex = foundIdx;
        }
    }

        // 세션 인덱스를 바탕으로 다음 롤링 문제 버튼 생성
        if (session && session.isActive && session.currentIndex > -1) {
            if (session.currentIndex < session.questions.length - 1) {
                const nextQ = session.questions[session.currentIndex + 1];
                nextQuestionButtonHtml = `
                    <button onclick="moveToNextRollingQuestion('${nextQ.globalIdx}', ${nextQ.year}, ${nextQ.num}, event)" style="background: var(--accent-gradient); border: none; color: #ffffff; padding: 0.35rem 0.8rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700; cursor: pointer; transition: all 0.2s; font-family: inherit; display: inline-flex; align-items: center; gap: 0.2rem;" onmouseover="this.style.opacity='0.9'" onmouseout="this.style.opacity='1'">다음 문제 ➡️</button>
                `;
            } else {
                // 롤링 세션의 모든 문제를 다 푼 경우 새롭게 랜덤 롤링 시작
                if (session.questions.length > 1) {
                    nextQuestionButtonHtml = `
                        <button onclick="restartRollingSession(event)" style="background: rgba(139, 92, 246, 0.2); border: 1px solid rgba(139, 92, 246, 0.4); color: #ffffff; padding: 0.35rem 0.8rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700; cursor: pointer; transition: all 0.2s; font-family: inherit; display: inline-flex; align-items: center; gap: 0.2rem;" onmouseover="this.style.background='rgba(139, 92, 246, 0.3)'" onmouseout="this.style.background='rgba(139, 92, 246, 0.2)'">새 롤링 시작 🔄</button>
                    `;
                }
            }
        }

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

        // 셔플된 인덱스 배열 또는 순차 기본 배열을 이용
        const indices = data.shuffledIndices || Array.from({ length: data.options.length }, (_, i) => i);

        indices.forEach((oIdx, displayIdx) => {
            const opt = data.options[oIdx];
            const sym = numSymbols[displayIdx] || `${displayIdx + 1}`;
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

    // 해당 문항의 모든 풀이 이력을 window.quizFullHistoryList 에서 필터링하여 가져옵니다.
    const questionLogs = (window.quizFullHistoryList || []).filter(log => {
        if (!log.details) return false;
        // 신규 포맷
        if (log.details.q_id === qId) return true;
        // 구 포맷
        if (log.details.correct && log.details.correct.includes(qId)) return true;
        if (log.details.wrong && log.details.wrong.includes(qId)) return true;
        return false;
    });

    let historyHtml = '';
    if (questionLogs.length > 0) {
        historyHtml += `
            <div class="quiz-history-timeline-section" style="margin-top: 1.2rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 0.8rem;">
                <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.6rem; font-weight: 700; display: flex; align-items: center; gap: 0.3rem;">
                    ⏱️ 나의 풀이 이력
                </div>
                <ul class="timeline-list" style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.4rem;">
        `;
        const numSymbols = ["①", "②", "③", "④", "⑤"];
        questionLogs.forEach(log => {
            let text = '';
            const dateFormatted = formatKoreanDate(log.created_at);
            const isCorrect = log.details && (log.details.is_correct !== undefined ? log.details.is_correct : (log.details.correct && log.details.correct.includes(qId)));

            let itemColor, itemIcon;
            if (isSubmitted) {
                const resultText = isCorrect ? '맞음' : '틀림';
                const resultColor = isCorrect ? 'var(--success)' : '#ef4444';
                const resultIcon = isCorrect ? '✓' : '✕';
                itemColor = resultColor;
                itemIcon = resultIcon;

                if (log.details && log.details.user_choice) {
                    const choiceStr = log.details.user_choice.map(num => numSymbols[num - 1] || num).join(', ');
                    text = `${dateFormatted}에 ${choiceStr}번을 선택해서 <span style="color: ${resultColor}; font-weight: bold;">${resultText}</span>`;
                } else {
                    text = `${dateFormatted}에 답안을 제출해서 <span style="color: ${resultColor}; font-weight: bold;">${resultText}</span>`;
                }
            } else {
                itemColor = 'rgba(255,255,255,0.25)'; // 미제출 시 중립 컬러
                itemIcon = '⏱️';
                text = `${dateFormatted}에 풀었음`;
            }

            historyHtml += `
                <li style="font-size: 0.8rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.4rem; background: rgba(255,255,255,0.02); padding: 0.4rem 0.6rem; border-radius: 4px; border-left: 2px solid ${itemColor};">
                    <span style="color: ${itemColor}; font-weight: bold; font-size: 0.75rem;">[${itemIcon}]</span>
                    <span>${text}</span>
                </li>
            `;
        });
        historyHtml += `
                </ul>
            </div>
        `;
    }

    // 답안 제출 및 피드백 패널
    if (isSubmitted) {
        // 정답 피드백 렌더링 (정답일 때는 배너 미노출, 오답일 때만 노출)
        const statusClass = submittedResult.isCorrect ? 'correct' : 'wrong';

        if (!submittedResult.isCorrect) {
            htmlContent += `
                <div class="inline-quiz-feedback ${statusClass}">
                    ✕ 오답입니다. (정답: ${submittedResult.cAnsStr})
                </div>
            `;
        }

        htmlContent += `
            ${data.explanation ? `
                <div class="inline-explanation-box">
                    <strong>💡 정답 해설:</strong><br>${data.explanation}
                </div>
            ` : ''}
            ${historyHtml}
            <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 0.8rem;">
                <button onclick="retryInlineQuestion('${idx}', '${qId}', event)" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: var(--text-secondary); padding: 0.35rem 0.8rem; border-radius: 4px; font-size: 0.75rem; cursor: pointer; transition: all 0.2s; font-family: inherit;">다시 풀기</button>
                ${nextQuestionButtonHtml}
            </div>
        `;
    } else {
        // 미제출 상태 제출 버튼
        htmlContent += `
            ${historyHtml}
            <div style="display: flex; justify-content: flex-end; margin-top: 0.2rem;">
                <button onclick="submitInlineAnswer('${idx}', '${qId}', event)" class="inline-quiz-submit-btn">
                    💾 답안 제출
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

    // 채점: 답안이 여러개인 경우는 여러개 중에 1개만 선택해도 답으로 인정해 줍니다.
    let isCorrect = false;
    if (uAns.length > 0) {
        if (cAns.length > 1) {
            isCorrect = uAns.some(ans => cAns.includes(ans));
        } else {
            isCorrect = JSON.stringify(uAns.sort()) === JSON.stringify(cAns);
        }
    }
    const numSymbols = ["①", "②", "③", "④", "⑤"];
    const cAnsStr = cAns.map(num => {
        const displayIdx = data.shuffledIndices ? data.shuffledIndices.indexOf(num - 1) : (num - 1);
        return numSymbols[displayIdx] || (displayIdx + 1);
    }).join(', ');

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

    // 이력 포맷 상세화 적용: details에 q_id, user_choice, correct_answer, is_correct 적재
    const payload = {
        subject: subject,
        concept: conceptName,
        total_questions: 1,
        correct_count: isCorrect ? 1 : 0,
        wrong_count: isCorrect ? 0 : 1,
        details: {
            q_id: qId,
            user_choice: uAns,
            correct_answer: cAns,
            is_correct: isCorrect
        }
    };

    // 로컬스토리지 백업 저장 (서버 초기화 리스크 방지)
    try {
        const localHistoryStr = localStorage.getItem('jolly_carson_quiz_history');
        const localHistory = localHistoryStr ? JSON.parse(localHistoryStr) : [];
        const localPayload = {
            created_at: new Date().toISOString(),
            subject: subject,
            concept: conceptName,
            total_questions: 1,
            correct_count: isCorrect ? 1 : 0,
            wrong_count: isCorrect ? 0 : 1,
            details: {
                q_id: qId,
                user_choice: uAns,
                correct_answer: cAns,
                is_correct: isCorrect
            }
        };
        localHistory.push(localPayload);
        localStorage.setItem('jolly_carson_quiz_history', JSON.stringify(localHistory));
    } catch (e) {
        console.warn("[로컬스토리지 백업 실패]", e);
    }

    // 백엔드 API 제출 및 통계 실시간 비동기 리프레시
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
            if (isCorrect) {
                if (typeof gamOnCorrectAnswer === 'function') {
                    gamOnCorrectAnswer(idx, qId);
                }
            } else {
                if (typeof gamTriggerPetIncorrectMessage === 'function') {
                    gamTriggerPetIncorrectMessage();
                }
                if (typeof gamApplyPetAnimation === 'function') {
                    gamApplyPetAnimation('incorrect');
                }
            }
        })
        .catch(err => {
            console.error(err);
            renderLoadedQuestion(idx, qId);
            if (isCorrect) {
                if (typeof gamOnCorrectAnswer === 'function') {
                    gamOnCorrectAnswer(idx, qId);
                }
            } else {
                if (typeof gamTriggerPetIncorrectMessage === 'function') {
                    gamTriggerPetIncorrectMessage();
                }
                if (typeof gamApplyPetAnimation === 'function') {
                    gamApplyPetAnimation('incorrect');
                }
            }
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

    // 다시 풀기 시 보기를 새로운 순서로 재셔플
    const data = window.loadedQuestions[qId];
    if (data && data.options && data.options.length > 0) {
        const indices = Array.from({ length: data.options.length }, (_, i) => i);
        data.shuffledIndices = shuffleArray(indices);
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
                    ${[1, 2, 3, 4].map(n => {
        const sym = ["①", "②", "③", "④"][n - 1];
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

// [삭제됨] 정답 및 테스트 이력 팝업 모달과 관련 로직은 사용자 요청에 의해 삭제되었습니다.


/**
 * ==========================================================================
 * 🎮 게이미피케이션 (EXP/Level 시스템 및 보물상자 이펙트)
 * ==========================================================================
 */

/**
 * GAM-1. 게이미피케이션 EXP/Level 시스템을 초기화합니다.
 */
function initGamification() {
    window.gamState = {
        totalExp: 0,
        level: 1,
        expInLevel: 0
    };

    // UI 주입
    gamInjectExpCard();
    gamInjectLevelUpOverlay();

    // API 조회하여 EXP 데이터 업데이트 (로컬스토리지 비교식 이중 유실 방어막 적용)
    fetch('/api/quiz/total-exp')
        .then(res => res.ok ? res.json() : { total_exp: 0, level: 1, exp_in_level: 0 })
        .then(data => {
            const apiTotalExp = data.total_exp || 0;
            let localTotalExp = 0;
            try {
                const localHistoryStr = localStorage.getItem('jolly_carson_quiz_history');
                if (localHistoryStr) {
                    const localLogs = JSON.parse(localHistoryStr) || [];
                    localTotalExp = localLogs.reduce((sum, log) => sum + (log.correct_count || 0), 0);
                }
            } catch (e) {}

            // 서버 측 누적 경험치와 로컬스토리지 누적 경험치 중 유실 방지를 위해 더 큰 값을 최종 적용
            const finalTotalExp = Math.max(apiTotalExp, localTotalExp);
            window.gamState.totalExp = finalTotalExp;
            window.gamState.level = Math.floor(finalTotalExp / 10) + 1;
            window.gamState.expInLevel = finalTotalExp % 10;
            gamUpdateExpUI();
        })
        .catch(err => {
            console.warn("[경고] 게이미피케이션 데이터 로드 실패. 로컬 폴백을 시도합니다.", err);
            let localTotalExp = 0;
            try {
                const localHistoryStr = localStorage.getItem('jolly_carson_quiz_history');
                if (localHistoryStr) {
                    const localLogs = JSON.parse(localHistoryStr) || [];
                    localTotalExp = localLogs.reduce((sum, log) => sum + (log.correct_count || 0), 0);
                }
            } catch (e) {}
            window.gamState.totalExp = localTotalExp;
            window.gamState.level = Math.floor(localTotalExp / 10) + 1;
            window.gamState.expInLevel = localTotalExp % 10;
            gamUpdateExpUI();
        });
}

/**
 * GAM-2. EXP/Level 카드 UI를 생성하여 상단에 주입합니다. (포켓몬 응원 펫 연동)
 */
function gamInjectExpCard() {
    // 이미 존재하면 스킵
    if (document.getElementById('gam-exp-card')) return;

    // 저장된 펫 정보 로드
    const petKeys = ['pikachu', 'charmander', 'squirtle', 'bulbasaur'];
    let currentPetKey = localStorage.getItem('gam_selected_pet') || 'pikachu';
    if (!petKeys.includes(currentPetKey)) currentPetKey = 'pikachu';

    const POKEMON_PETS = {
        'pikachu': { name: '피카츄', src: '/reports/images_game/pikachuRun.gif', defaultMsg: '오늘도 합격을 향해 백만볼트! ⚡' },
        'charmander': { name: '파이리', src: '/reports/images_game/charmander_cheer.png', defaultMsg: '뜨거운 열정으로 문제를 정복해요! 🔥' },
        'squirtle': { name: '꼬부기', src: '/reports/images_game/squirtle_cheer.png', defaultMsg: '오답은 시원하게 물대포로 날려요! 💦' },
        'bulbasaur': { name: '이상해씨', src: '/reports/images_game/bulbasaur_cheer.png', defaultMsg: '천천히 씨앗을 뿌리듯 실력을 키워요! 🌱' }
    };

    const activePet = POKEMON_PETS[currentPetKey];

    const card = document.createElement('div');
    card.id = 'gam-exp-card';
    card.className = 'gamification-exp-card';
    card.innerHTML = `
        <div class="gam-pet-widget" style="display: flex; align-items: center; gap: 0.8rem; cursor: pointer; position: relative; margin-right: 0.5rem;" onclick="gamCyclePet()" title="클릭 시 포켓몬 캐릭터 교체">
            <div class="gam-pet-avatar-wrapper" style="width: 54px; height: 54px; border-radius: 50%; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative; transition: all 0.2s;">
                <img id="gam-pet-img" src="${activePet.src}" alt="${activePet.name}" style="width: 85%; height: 85%; object-fit: contain; transform: scale(1.1); transition: transform 0.2s;" />
            </div>
            <div class="gam-pet-bubble" style="background: rgba(139, 92, 246, 0.12); border: 1px solid rgba(139, 92, 246, 0.25); color: #e9d5ff; font-size: 0.72rem; padding: 0.4rem 0.6rem; border-radius: 8px; position: relative; max-width: 155px; line-height: 1.4; font-weight: 500; min-height: 38px; display: flex; align-items: center;">
                <span id="gam-pet-bubble-text">${activePet.defaultMsg}</span>
                <!-- 말풍선 꼬리 -->
                <div style="position: absolute; left: -5px; top: 50%; transform: translateY(-50%) rotate(45deg); width: 8px; height: 8px; background: #0c0f1d; border-left: 1px solid rgba(139, 92, 246, 0.25); border-bottom: 1px solid rgba(139, 92, 246, 0.25);"></div>
            </div>
        </div>
        <div class="gam-level-badge" style="margin-left: auto;">
            <span class="gam-lv-label">LV</span>
            <span class="gam-lv-num" id="gam-lv-value">1</span>
        </div>
        <div class="gam-exp-wrapper">
            <div class="gam-exp-header">
                <span class="gam-exp-title">🛡️ 수험생 경험치 (EXP)</span>
                <span class="gam-exp-value" id="gam-exp-text">0 / 10 EXP</span>
            </div>
            <div class="gam-exp-bar-bg">
                <div class="gam-exp-bar-fill" id="gam-exp-fill" style="width: 0%;"></div>
            </div>
        </div>
    `;

    // header와 quiz-summary-section 사이 또는 header 직후에 삽입
    const header = document.querySelector('header');
    if (header) {
        const summarySection = document.getElementById('quiz-summary-section');
        if (summarySection) {
            summarySection.parentNode.insertBefore(card, summarySection);
        } else {
            header.parentNode.insertBefore(card, header.nextSibling);
        }
    }
}

/**
 * GAM-3. 레벨업 전체화면 오버레이 DOM을 body에 주입합니다.
 */
function gamInjectLevelUpOverlay() {
    if (document.getElementById('gam-levelup-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'gam-levelup-overlay';
    overlay.className = 'hidden';
    overlay.innerHTML = `
        <div class="gam-beam"></div>
        <div class="gam-levelup-box">
            <h2 class="gam-levelup-title">LEVEL UP!</h2>
            <div class="gam-levelup-sub">새로운 경지에 도달했습니다!</div>
            <div class="gam-levelup-badge" id="gam-levelup-text">LV. 2</div>
        </div>
    `;
    document.body.appendChild(overlay);
}

/**
 * GAM-4. EXP UI 요소들을 현재 상태값으로 갱신합니다.
 */
function gamUpdateExpUI() {
    const { totalExp, level, expInLevel } = window.gamState;
    const expPercent = (expInLevel / 10) * 100;
    const nextLevelExp = level * 10;

    const lvValue = document.getElementById('gam-lv-value');
    const expText = document.getElementById('gam-exp-text');
    const expFill = document.getElementById('gam-exp-fill');

    if (lvValue) lvValue.textContent = level;
    if (expText) expText.textContent = `${totalExp} / ${nextLevelExp} EXP`;
    if (expFill) expFill.style.width = `${expPercent}%`;
}

/**
 * GAM-5. 정답 제출 시 호출되는 메인 게이미피케이션 핸들러
 * - EXP +1, 보물상자 + 보석 파티클, EXP 플로팅 뱃지, 레벨업 체크
 */
function gamOnCorrectAnswer(idx, qId) {
    const prevLevel = window.gamState.level;

    // EXP 증가
    window.gamState.totalExp += 1;
    window.gamState.level = Math.floor(window.gamState.totalExp / 10) + 1;
    window.gamState.expInLevel = window.gamState.totalExp % 10;

    // UI 갱신
    gamUpdateExpUI();

    // 펫 정답 축하 말풍선 트리거
    gamTriggerPetCorrectMessage();

    // 펫 정답 애니메이션 (바운스)
    gamApplyPetAnimation('correct');

    // EXP +1 플로팅 뱃지
    gamTriggerExpFloat();

    // 보물 상자 + 보석 파티클 (인라인 뷰어 내부에 삽입)
    gamTriggerTreasureChest(idx, qId);

    // 인라인 뷰어 글로우 효과
    const viewer = document.querySelector(`#item-${idx} .inline-question-viewer`);
    if (viewer) {
        viewer.classList.add('gam-correct-glow');
        setTimeout(() => viewer.classList.remove('gam-correct-glow'), 700);
    }

    // 레벨업 체크
    if (window.gamState.level > prevLevel) {
        setTimeout(() => gamTriggerLevelUp(window.gamState.level), 900);
    }
}

/**
 * GAM-5-B. 펫 캐릭터를 클릭했을 때 다음 캐릭터로 교체합니다.
 */
window.gamCyclePet = function() {
    const petKeys = ['pikachu', 'charmander', 'squirtle', 'bulbasaur'];
    let currentPetKey = localStorage.getItem('gam_selected_pet') || 'pikachu';
    let nextIdx = (petKeys.indexOf(currentPetKey) + 1) % petKeys.length;
    let nextPetKey = petKeys[nextIdx];
    localStorage.setItem('gam_selected_pet', nextPetKey);

    const POKEMON_PETS = {
        'pikachu': { name: '피카츄', src: '/reports/images_game/pikachuRun.gif', defaultMsg: '오늘도 합격을 향해 백만볼트! ⚡' },
        'charmander': { name: '파이리', src: '/reports/images_game/charmander_cheer.png', defaultMsg: '뜨거운 열정으로 문제를 정복해요! 🔥' },
        'squirtle': { name: '꼬부기', src: '/reports/images_game/squirtle_cheer.png', defaultMsg: '오답은 시원하게 물대포로 날려요! 💦' },
        'bulbasaur': { name: '이상해씨', src: '/reports/images_game/bulbasaur_cheer.png', defaultMsg: '천천히 씨앗을 뿌리듯 실력을 키워요! 🌱' }
    };

    const pet = POKEMON_PETS[nextPetKey];
    const img = document.getElementById('gam-pet-img');
    const runnerImg = document.getElementById('gam-runner-pet-img');
    const bubble = document.getElementById('gam-pet-bubble-text');
    const runnerBubble = document.getElementById('gam-runner-pet-bubble-text');
    if (img) {
        img.src = pet.src;
        img.alt = pet.name;
    }
    if (runnerImg) {
        runnerImg.src = pet.src;
        runnerImg.alt = pet.name;
    }
    if (bubble) bubble.textContent = pet.defaultMsg;
    if (runnerBubble) runnerBubble.textContent = pet.defaultMsg;

    // 교체 시 360도 스핀 애니메이션 적용
    gamApplyPetAnimation('spin');
};

// 복귀 타이머 ID를 관리할 전역 변수
window.gamPetBubbleTimeout = null;

/**
 * GAM-5-C. 정답 시 펫의 특별 칭찬 메시지를 말풍선에 띄웁니다.
 */
function gamTriggerPetCorrectMessage() {
    const PET_CORRECT_MESSAGES = {
        'pikachu': [
            '정답이에요! 짜릿한 백만볼트급 활약! ⚡',
            '합격을 향해 한 걸음 더 전진! 삐까삐까! ⚡',
            '최고의 감리사가 될 상이로군요! 삐까! 🌟'
        ],
        'charmander': [
            '정답입니다! 파이리의 불꽃 열정! 🔥',
            '뜨겁게 타오르는 실력! 멋져요! 🔥',
            '이 기세라면 고득점 합격 확정! 🔥'
        ],
        'squirtle': [
            '대단해요! 정답을 거침없이 명중! 💦',
            '정답 행진! 시원한 물대포 슛! 💦',
            '거북이처럼 우직하고 견고한 실력! 🐢'
        ],
        'bulbasaur': [
            '정답! 탄탄한 기본기가 빛을 발해요! 🌱',
            '넝쿨처럼 쑥쑥 뻗어나가는 성적! 🌿',
            '이상해씨가 봐도 너무 똑똑해요! 🍃'
        ]
    };

    const currentPetKey = localStorage.getItem('gam_selected_pet') || 'pikachu';
    const msgs = PET_CORRECT_MESSAGES[currentPetKey] || ['정답입니다! 🎉'];
    const randomMsg = msgs[Math.floor(Math.random() * msgs.length)];
    
    const bubble = document.getElementById('gam-pet-bubble-text');
    const runnerBubble = document.getElementById('gam-runner-pet-bubble-text');

    if (bubble) bubble.textContent = randomMsg;
    if (runnerBubble) runnerBubble.textContent = randomMsg;

    // 이전 복귀 타이머 제거
    if (window.gamPetBubbleTimeout) {
        clearTimeout(window.gamPetBubbleTimeout);
    }

    // 4초 후 기본 상태 메시지로 복귀
    const DEFAULT_PET_MESSAGES = {
        'pikachu': '오늘도 합격을 향해 백만볼트! ⚡',
        'charmander': '뜨거운 열정으로 문제를 정복해요! 🔥',
        'squirtle': '오답은 시원하게 물대포로 날려요! 💦',
        'bulbasaur': '천천히 씨앗을 뿌리듯 실력을 키워요! 🌱'
    };
    window.gamPetBubbleTimeout = setTimeout(() => {
        const curPet = localStorage.getItem('gam_selected_pet') || 'pikachu';
        const curBubble = document.getElementById('gam-pet-bubble-text');
        const curRunnerBubble = document.getElementById('gam-runner-pet-bubble-text');
        if (curBubble) {
            curBubble.textContent = DEFAULT_PET_MESSAGES[curPet] || '';
        }
        if (curRunnerBubble) {
            curRunnerBubble.textContent = DEFAULT_PET_MESSAGES[curPet] || '';
        }
    }, 4000);
}

/**
 * GAM-5-D. 오답 시 펫의 특별 격려 메시지를 말풍선에 띄웁니다.
 */
function gamTriggerPetIncorrectMessage() {
    const PET_INCORRECT_MESSAGES = {
        'pikachu': [
            '앗! 틀렸지만 괜찮아요! 다음 번엔 백만볼트 파워로 정답 조준! ⚡',
            '피카... 조금 아쉽네요! 삐까츄와 함께 다시 한 번 복습해봐요! ⚡',
            '괜찮아요, 피카츄도 처음엔 전기를 잘 다루지 못했답니다! 힘내세요! 🌱'
        ],
        'charmander': [
            '앗, 오답이라니! 하지만 제 불꽃은 꺼지지 않았어요! 다시 도전해요! 🔥',
            '뜨거운 열정으로 오답을 다 태워버려요! 파이팅! 🔥',
            '실패는 성공의 어머니! 다음 문제는 꼭 맞출 수 있을 거예요! 🔥'
        ],
        'squirtle': [
            '이런! 오답이네요. 하지만 시원하게 물대포 한 번 쏘고 다시 해봐요! 💦',
            '꼬북... 아쉽지만 실망하긴 일러요! 거북이처럼 우직하게 정진! 🐢',
            '괜찮아요! 물 흐르듯 유연하게 다음 문제로 나아가 볼까요? 💦'
        ],
        'bulbasaur': [
            '아쉬워요! 하지만 단단한 씨앗이 싹을 틔우듯 차근차근 배워가면 돼요! 🌱',
            '이상해씨 덩굴채찍으로 오답을 확 걷어내요! 🌿',
            '괜찮아요! 한 걸음씩 자라나는 거니까요. 이상해! 씨앗! 🍃'
        ]
    };

    const currentPetKey = localStorage.getItem('gam_selected_pet') || 'pikachu';
    const msgs = PET_INCORRECT_MESSAGES[currentPetKey] || ['괜찮아요! 다시 한 번 검토해봅시다! 💪'];
    const randomMsg = msgs[Math.floor(Math.random() * msgs.length)];
    
    const bubble = document.getElementById('gam-pet-bubble-text');
    const runnerBubble = document.getElementById('gam-runner-pet-bubble-text');

    if (bubble) bubble.textContent = randomMsg;
    if (runnerBubble) runnerBubble.textContent = randomMsg;

    // 이전 복귀 타이머 제거
    if (window.gamPetBubbleTimeout) {
        clearTimeout(window.gamPetBubbleTimeout);
    }

    // 4초 후 기본 상태 메시지로 복귀
    const DEFAULT_PET_MESSAGES = {
        'pikachu': '오늘도 합격을 향해 백만볼트! ⚡',
        'charmander': '뜨거운 열정으로 문제를 정복해요! 🔥',
        'squirtle': '오답은 시원하게 물대포로 날려요! 💦',
        'bulbasaur': '천천히 씨앗을 뿌리듯 실력을 키워요! 🌱'
    };
    window.gamPetBubbleTimeout = setTimeout(() => {
        const curPet = localStorage.getItem('gam_selected_pet') || 'pikachu';
        const curBubble = document.getElementById('gam-pet-bubble-text');
        const curRunnerBubble = document.getElementById('gam-runner-pet-bubble-text');
        if (curBubble) {
            curBubble.textContent = DEFAULT_PET_MESSAGES[curPet] || '';
        }
        if (curRunnerBubble) {
            curRunnerBubble.textContent = DEFAULT_PET_MESSAGES[curPet] || '';
        }
    }, 4000);
}

/**
 * GAM-5-E. 펫 이미지에 특정 애니메이션 효과(bounce, shake, spin)를 적용합니다.
 */
function gamApplyPetAnimation(type) {
    const mainImg = document.getElementById('gam-pet-img');
    const runnerImg = document.getElementById('gam-runner-pet-img');

    const classNameMap = {
        'correct': 'gam-pet-bounce',
        'incorrect': 'gam-pet-shake',
        'spin': 'gam-pet-spin'
    };

    const targetClass = classNameMap[type];
    if (!targetClass) return;

    [mainImg, runnerImg].forEach(img => {
        if (!img) return;

        // 기존 클래스 제거
        img.classList.remove('gam-pet-bounce', 'gam-pet-shake', 'gam-pet-spin');
        
        // 리플로우 강제 유발로 애니메이션 리셋
        void img.offsetWidth;

        img.classList.add(targetClass);

        const onAnimationEnd = () => {
            img.classList.remove(targetClass);
            img.removeEventListener('animationend', onAnimationEnd);
        };
        img.addEventListener('animationend', onAnimationEnd);
    });
}

/**
 * GAM-6. EXP +1 플로팅 뱃지를 화면 중앙에 표시합니다.
 */
function gamTriggerExpFloat() {
    const badge = document.createElement('div');
    badge.className = 'gam-exp-float';
    badge.textContent = `⚡ EXP +1 (${window.gamState.totalExp})`;
    document.body.appendChild(badge);

    setTimeout(() => {
        if (badge.parentNode) badge.parentNode.removeChild(badge);
    }, 1600);
}

/**
 * GAM-7. 보물 상자 팝업 + 보석 파티클을 인라인 뷰어의 피드백 영역에 삽입합니다.
 */
function gamTriggerTreasureChest(idx, qId) {
    const body = document.getElementById(`viewer-body-${idx}`);
    if (!body) return;

    // 기존 보물 상자가 있다면 제거
    const existing = body.querySelector('.gam-treasure-container');
    if (existing) existing.remove();

    const container = document.createElement('div');
    container.className = 'gam-treasure-container';

    // 보물 상자 이미지
    const img = document.createElement('img');
    img.src = '/reports/images_game/gems_overflowing.png';
    img.alt = '보물 상자 오픈!';
    img.className = 'gam-treasure-img';
    container.appendChild(img);

    // 메시지 텍스트
    const msg = document.createElement('div');
    msg.className = 'gam-treasure-msg';
    msg.innerHTML = `💎 보물 상자를 획득했습니다!<br>경험치 <span class="gam-exp-badge">EXP +1</span> 누적: ${window.gamState.totalExp}`;
    container.appendChild(msg);

    // 보석 파티클 생성 (10개)
    const gemEmojis = ['💎', '✨', '🌟', '💰', '⭐', '🏆'];
    for (let i = 0; i < 10; i++) {
        const particle = document.createElement('span');
        particle.className = 'gam-gem-particle';
        particle.textContent = gemEmojis[i % gemEmojis.length];

        const angle = (i / 10) * 360;
        const distance = 50 + Math.random() * 70;
        const tx = Math.cos(angle * Math.PI / 180) * distance;
        const ty = Math.sin(angle * Math.PI / 180) * distance;
        const rot = Math.random() * 720 - 360;

        particle.style.setProperty('--tx', `${tx}px`);
        particle.style.setProperty('--ty', `${ty}px`);
        particle.style.setProperty('--rot', `${rot}deg`);
        particle.style.animationDelay = `${i * 0.05}s`;

        container.appendChild(particle);
    }

    // 피드백 블록 뒤에 삽입
    const feedbackBlock = body.querySelector('.inline-quiz-feedback');
    if (feedbackBlock) {
        feedbackBlock.parentNode.insertBefore(container, feedbackBlock.nextSibling);
    } else {
        body.appendChild(container);
    }
}

/**
 * GAM-7-B. 보물 상자 팝업 + 보석 파티클을 지정된 부모 엘리먼트에 동적으로 주입합니다. (오답노트 복습 뷰어 연동)
 */
function gamSpawnTreasureChest(parentEl, insertBeforeSelector) {
    if (!parentEl) return;

    // 기존 보물 상자가 있다면 제거
    const existing = parentEl.querySelector('.gam-treasure-container');
    if (existing) existing.remove();

    const container = document.createElement('div');
    container.className = 'gam-treasure-container';

    // 보물 상자 이미지
    const img = document.createElement('img');
    img.src = '/reports/images_game/gems_overflowing.png';
    img.alt = '보물 상자 오픈!';
    img.className = 'gam-treasure-img';
    container.appendChild(img);

    // 메시지 텍스트
    const msg = document.createElement('div');
    msg.className = 'gam-treasure-msg';
    msg.innerHTML = `💎 보물 상자를 획득했습니다!<br>경험치 <span class="gam-exp-badge">EXP +1</span> 누적: ${window.gamState.totalExp}`;
    container.appendChild(msg);

    // 보석 파티클 생성 (10개)
    const gemEmojis = ['💎', '✨', '🌟', '💰', '⭐', '🏆'];
    for (let i = 0; i < 10; i++) {
        const particle = document.createElement('span');
        particle.className = 'gam-gem-particle';
        particle.textContent = gemEmojis[i % gemEmojis.length];

        const angle = (i / 10) * 360;
        const distance = 50 + Math.random() * 70;
        const tx = Math.cos(angle * Math.PI / 180) * distance;
        const ty = Math.sin(angle * Math.PI / 180) * distance;
        const rot = Math.random() * 720 - 360;

        particle.style.setProperty('--tx', `${tx}px`);
        particle.style.setProperty('--ty', `${ty}px`);
        particle.style.setProperty('--rot', `${rot}deg`);
        particle.style.animationDelay = `${i * 0.05}s`;

        container.appendChild(particle);
    }

    const target = insertBeforeSelector ? parentEl.querySelector(insertBeforeSelector) : null;
    if (target) {
        target.parentNode.insertBefore(container, target);
    } else {
        parentEl.appendChild(container);
    }
}

/**
 * GAM-8. 레벨업 전체화면 오버레이 이펙트를 구동합니다.
 */
function gamTriggerLevelUp(newLevel) {
    const overlay = document.getElementById('gam-levelup-overlay');
    if (!overlay) return;

    // ... 레벨 텍스트 업데이트
    const badge = document.getElementById('gam-levelup-text');
    if (badge) badge.textContent = `LV. ${newLevel}`;

    overlay.classList.remove('hidden');

    // 파티클 폭발
    const emojis = ['🌟', '✨', '💎', '⭐', '🏅', '🎖️', '💫', '🔥'];
    for (let i = 0; i < 20; i++) {
        const p = document.createElement('span');
        p.className = 'gam-levelup-particle';
        p.textContent = emojis[i % emojis.length];
        p.style.fontSize = `${1.1 + Math.random() * 1.1}rem`;
        p.style.left = `${45 + Math.random() * 10}%`;
        p.style.top = `${45 + Math.random() * 10}%`;

        const angle = (i / 20) * 360;
        const dist = 140 + Math.random() * 240;
        const tx = Math.cos(angle * Math.PI / 180) * dist;
        const ty = Math.sin(angle * Math.PI / 180) * dist;

        p.style.setProperty('--tx', `${tx}px`);
        p.style.setProperty('--ty', `${ty}px`);
        p.style.animationDelay = `${i * 0.06}s`;

        document.body.appendChild(p);

        setTimeout(() => {
            if (p.parentNode) p.parentNode.removeChild(p);
        }, 2500);
    }

    // 3.5초 후 자동 숨김
    setTimeout(() => {
        overlay.classList.add('hidden');
    }, 3500);
}

/**
 * ==========================================================================
 * 🔄 문제 롤링 및 순회 제어 시스템
 * ==========================================================================
 */

/**
 * 13-A. 특정 중단원(concept)에 매핑된 전체 기출문제 목록을 수집합니다.
 */
function getConceptQuestionsList(globalIdx) {
    const list = [];
    if (!window.dashboardData) return list;
    const targetData = window.dashboardData.find(d => String(d.global_idx) === String(globalIdx));
    if (targetData && targetData.questions) {
        targetData.questions.forEach(q => {
            list.push({
                globalIdx: parseInt(globalIdx),
                year: q.year,
                num: q.num,
                qId: `${q.year}_${q.num}`,
                concept: targetData.concept
            });
        });
    }
    return list;
}

/**
 * 14. 현재 화면에 표시된 (필터가 적용된) 전체 질문 목록을 순서대로 수집합니다.
 */
function getActiveQuestionsList() {
    const list = [];
    const container = document.getElementById('accordionContainer') || document.getElementById('accordion-container');
    if (!container || !window.dashboardData) return list;

    const items = container.querySelectorAll('.accordion-item');
    items.forEach(item => {
        const globalIdx = parseInt(item.id.replace('item-', ''));
        const targetData = window.dashboardData.find(d => String(d.global_idx) === String(globalIdx));
        if (targetData && targetData.questions) {
            targetData.questions.forEach(q => {
                list.push({
                    globalIdx: globalIdx,
                    year: q.year,
                    num: q.num,
                    qId: `${q.year}_${q.num}`,
                    concept: targetData.concept
                });
            });
        }
    });
    return list;
}

/**
 * 15. 다음 롤링 타겟 문제로 이동합니다. (아코디언 제어 및 질문 상세 로드)
 */
function moveToNextRollingQuestion(nextGlobalIdx, nextYear, nextNum, event) {
    if (event) event.stopPropagation();

    const container = document.getElementById('accordionContainer') || document.getElementById('accordion-container');
    if (!container) return;

    // 다른 열린 아코디언 및 뷰어는 깔끔한 전환을 위해 일괄 초기화
    container.querySelectorAll('.accordion-item').forEach(item => {
        const itemIdx = item.id.replace('item-', '');
        if (String(itemIdx) !== String(nextGlobalIdx)) {
            item.classList.remove('active');
            const content = item.querySelector('.accordion-content');
            if (content) content.style.maxHeight = null;
            const viewer = item.querySelector(`.inline-question-viewer`);
            if (viewer) viewer.classList.add('hidden');
        }
    });

    const nextItem = document.getElementById(`item-${nextGlobalIdx}`);
    if (nextItem) {
        nextItem.classList.add('active');
        const content = nextItem.querySelector('.accordion-content');
        if (content) {
            content.style.maxHeight = '2000px'; // 임시 여유값
        }

        // 포커스 이동
        nextItem.scrollIntoView({ behavior: 'smooth', block: 'center' });

        setTimeout(() => {
            const nextBtn = nextItem.querySelector(`.q-btn-${nextYear}-${nextNum}`) ||
                document.getElementById(`btn-${nextGlobalIdx}-${nextYear}-${nextNum}`);
            showQuestion(nextGlobalIdx, nextYear, nextNum, nextBtn, true); // 롤링 전환 플래그 true 전달
        }, 300);
    }
}

/**
 * 16. 전체 문제 롤링 시작 (활성 문항 전체를 랜덤하게 섞어 세션을 시작합니다)
 */
function startGlobalRolling(event) {
    if (event) event.stopPropagation();

    const activeQsList = getActiveQuestionsList();
    if (activeQsList.length === 0) {
        alert("롤링을 시작할 문항이 없습니다. 필터 조건을 확인해주세요!");
        return;
    }

    // 전체 활성 문제를 랜덤 셔플하여 롤링 세션 개시
    const shuffledQs = shuffleArray(activeQsList);
    window.rollingSession = {
        isActive: true,
        questions: shuffledQs,
        currentIndex: 0
    };

    const firstQ = shuffledQs[0];
    moveToNextRollingQuestion(firstQ.globalIdx, firstQ.year, firstQ.num);
}

/**
 * 17. 롤링 세션이 한 바퀴 다 끝났을 때 세션을 재셔플하여 롤링을 재시작합니다.
 */
function restartRollingSession(event) {
    if (event) event.stopPropagation();

    const session = window.rollingSession;
    if (session && session.isActive && !session.isGlobal && session.globalIdx !== undefined) {
        // 로컬 중단원 세션 재시작
        const localQsList = getConceptQuestionsList(session.globalIdx);
        if (localQsList.length > 0) {
            const shuffledQs = shuffleArray(localQsList);
            window.rollingSession = {
                isActive: true,
                questions: shuffledQs,
                currentIndex: 0,
                isGlobal: false,
                globalIdx: session.globalIdx
            };
            const firstQ = shuffledQs[0];
            moveToNextRollingQuestion(firstQ.globalIdx, firstQ.year, firstQ.num);
            return;
        }
    }

    // 기본은 전체 롤링 재시작
    startGlobalRolling();
}
