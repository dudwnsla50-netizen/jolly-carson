/**
 * ==========================================================================
 * [Jolly-Carson 학습 이력 분석 스크립트 - history.js]
 * ==========================================================================
 */

// 전역 통계 상태 객체
const HistoryState = {
    allLogs: [],         // 전체 과목의 로그 목록 병합 데이터
    dailyHistory: [],    // 일별 그룹화 학습 데이터
    currentPage: 1,      // 현재 페이징 인덱스
    pageSize: 15,        // 페이징 당 행 개수
    charts: {},          // 차트 객체 버퍼 (인스턴스 소멸용)
    analyticsData: null, // [NEW] AI 중단원 분석 데이터 버퍼
    currentSubject: 'DB', // [NEW] 현재 활성화된 분석 탭 과목
    theme: 'dark',       // 현재 테마 상태(light/dark)
    yearlyExamHistory: [],
    yearlyQuestionCache: {},
    yearlySortKey: 'created_at',
    yearlySortOrder: 'desc',
    yearlyFilterYear: 'all',
    yearlyFilterSubject: 'all',
    yearlyCurrentPage: 1,
    yearlyPageSize: 15,
    yearlyTotalPages: 1,
    yearlySelectedChartSubject: null
};

const SUBJECT_NAMES = {
    'DB': '데이터베이스',
    'SE': '소프트웨어공학',
    'PM': '사업관리',
    'SA': '시스템구조',
    'SC': '보안'
};

const YEARLY_SUBJECT_ORDER = ['PM', 'SE', 'DB', 'SA', 'SC'];

document.addEventListener('DOMContentLoaded', () => {
    initThemeFromStorage();
    loadAllHistoryData();
    updateTabTitleWithDbMode();
});

/**
 * 메인 대시보드에서 선택된 테마(jc_theme)를 읽어 적용합니다.
 */
function initThemeFromStorage() {
    const savedTheme = localStorage.getItem('jc_theme');
    if (savedTheme === 'light' || savedTheme === 'dark') {
        applyTheme(savedTheme, false);
    } else {
        applyTheme('dark', false);
    }
}

/**
 * 테마 적용 및 선택 저장
 */
function applyTheme(theme, persist = false) {
    const normalized = (theme === 'light') ? 'light' : 'dark';
    document.body.setAttribute('data-theme', normalized);
    HistoryState.theme = normalized;

    if (persist) {
        localStorage.setItem('jc_theme', normalized);
    }

    // 테마가 바뀌면 차트 색상도 즉시 재렌더링합니다.
    if (HistoryState.allLogs && HistoryState.allLogs.length > 0) {
        renderCharts();
    }
}

/**
  * 서버의 DB 타입 정보를 탭 타이틀에 주입하는 함수
  */
function updateTabTitleWithDbMode() {
    fetch('/api/db-mode')
        .then(res => res.ok ? res.json() : null)
        .then(data => {
            if (data && data.db_type) {
                const dbTypeStr = data.db_type.toUpperCase();
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
 * 1. 5대 과목의 API 이력을 병합하여 수집합니다.
 */
function loadAllHistoryData() {
    const subjects = ['DB', 'SE', 'PM', 'SA', 'SC'];
    
    // 개별 과목의 API 요청 5번을 subject=all 배치 쿼리 1회로 간소화
    const statsAllPromise = fetch('/api/quiz/stats?subject=all')
        .then(res => res.ok ? res.json() : subjects.map(() => ({ logs: [] })))
        .catch(() => subjects.map(() => ({ logs: [] })));

    // [설계 의도]
    // 과목별 학습 현황 통계 데이터와 게이미피케이션 경험치 데이터를 병합 호출하여
    // 학습 이력 분석 센터 화면에 유기적으로 연동하고, 한 번의 로딩으로 모든 정보를 노출시킵니다.
    const expPromise = fetch('/api/quiz/total-exp')
        .then(res => res.ok ? res.json() : { total_exp: 0, level: 1, exp_in_level: 0, subjects_exp: {} })
        .catch(() => ({ total_exp: 0, level: 1, exp_in_level: 0, subjects_exp: {} }));

    const yearlyExamPromise = fetch('/api/yearly-exam/history')
        .then(res => res.ok ? res.json() : [])
        .catch(() => []);

    Promise.all([statsAllPromise, expPromise, yearlyExamPromise])
        .then(([results, expData, yearlyHistory]) => {
            const merged = [];
            const subjectAccuracies = {};

            HistoryState.yearlyExamHistory = Array.isArray(yearlyHistory) ? yearlyHistory : [];

            results.forEach((data, index) => {
                const sub = subjects[index];

                // 과목별 요약 정보로부터 평균 정답률(avg_score) 추출 (데이터가 없는 경우 0.0)
                subjectAccuracies[sub] = (data.summary && data.summary.avg_score) ? data.summary.avg_score : 0.0;

                const sLogs = data.logs || [];
                sLogs.forEach(log => {
                    merged.push({
                        ...log,
                        subject: sub,
                        parsedDate: parseDate(log.created_at)
                    });
                });
            });

            // [설계 의도] 
            // 년도별 모의고사 연습 이력(yearlyHistory)을 문항 단위로 쪼개어 5대 과목 분류에 맞춰 merged에 병합합니다.
            // 이를 통해 학습 이력 분석 센터의 일별 학습량(150문항 잔디밭 및 달력 통계)에 모의고사로 푼 문제 수도 자연스럽게 합산됩니다.
            if (yearlyHistory && yearlyHistory.length > 0) {
                yearlyHistory.forEach(exam => {
                    let examDetails = [];
                    try {
                        examDetails = (typeof exam.details === 'string')
                            ? JSON.parse(exam.details)
                            : (exam.details || []);
                    } catch (e) {
                        console.error("모의고사 details 파싱 에러:", e);
                    }

                    const examDate = parseDate(exam.created_at);

                    examDetails.forEach(detail => {
                        const qNum = detail.question_num;
                        let sub = 'DB'; // default fallback
                        if (qNum >= 1 && qNum <= 25) sub = 'PM';
                        else if (qNum >= 26 && qNum <= 50) sub = 'SE';
                        else if (qNum >= 51 && qNum <= 75) sub = 'DB';
                        else if (qNum >= 76 && qNum <= 100) sub = 'SA';
                        else if (qNum >= 101 && qNum <= 120) sub = 'SC';

                        merged.push({
                            id: `yearly-${exam.id}-${qNum}`,
                            total_questions: 1,
                            correct_count: detail.is_correct ? 1 : 0,
                            wrong_count: detail.is_correct ? 0 : 1,
                            created_at: exam.created_at,
                            subject: sub,
                            parsedDate: examDate
                        });
                    });
                });
            }

            // 시간 최신순 정렬
            merged.sort((a, b) => b.parsedDate - a.parsedDate);
            HistoryState.allLogs = merged;

            // 과목별 레벨/경험치 카드 UI 렌더링 (평균 정답률 데이터 전달)
            renderSubjectExpCards(expData, subjectAccuracies);

            // [NEW] 년도별 모의고사 연습 이력 필터 및 정렬 이벤트 바인딩
            initYearlyExamFiltersAndSorting(yearlyHistory);

            // [NEW] 년도별 모의고사 연습 이력 렌더링 수행
            renderYearlyExamHistoryTable(yearlyHistory);

            if (merged.length === 0) {
                renderEmptyState();
                return;
            }

            // 일별 이력 그룹화
            generateDailyHistory();

            // 대시보드 조립 구동
            calculateSummaryStats();
            renderCharts();
            renderHistoryTable();
        })
        .catch(err => {
            console.error("이력 데이터 로드 실패", err);
            renderEmptyState();
        });
}

/**
 * 2. 날짜 가공 헬퍼 함수 (타임존 보정 포함)
 */
function parseDate(dateStr) {
    if (!dateStr) return new Date();
    let standardized = dateStr;
    if (!dateStr.includes('T') && dateStr.includes(' ')) {
        standardized = dateStr.replace(' ', 'T') + 'Z'; // SQLite UTC -> Z 추가
    } else if (!dateStr.endsWith('Z') && dateStr.includes('T')) {
        standardized = dateStr + 'Z';
    }
    const d = new Date(standardized);
    return isNaN(d.getTime()) ? new Date() : d;
}

/**
 * 4. 종합 학습 요약 통계 계산 및 화면 주입
 */
function calculateSummaryStats() {
    const logs = HistoryState.allLogs;
    let totalSolved = 0;
    let totalCorrect = 0;
    const uniqueDays = new Set();

    logs.forEach(log => {
        totalSolved += (log.total_questions || 0);
        totalCorrect += (log.correct_count || 0);


        // 로컬 YYYY-MM-DD 문자열 추출
        const localDateStr = formatDateKey(log.parsedDate);
        uniqueDays.add(localDateStr);
    });

    const avgAccuracy = totalSolved > 0 ? Math.round((totalCorrect / totalSolved) * 100) : 0;


    // 학습 시간 계산: 문제당 평균 1.5분 소요 가정
    const totalMinutes = Math.round(totalSolved * 1.5);
    const hours = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;
    const timeStr = hours > 0 ? `${hours}시간 ${mins}분` : `${mins}분`;

    // 일평균 풀이량: 총 풀이량 / 공부한 날짜 수
    const activeDaysCount = uniqueDays.size || 1;
    const dailyAvg = (totalSolved / activeDaysCount).toFixed(1);

    // UI 반영
    document.getElementById('stat-total-solved').textContent = `${totalSolved}개`;
    document.getElementById('stat-avg-accuracy').textContent = `${avgAccuracy}%`;
    document.getElementById('stat-study-time').textContent = timeStr;
    document.getElementById('stat-active-days').textContent = `${activeDaysCount}일`;


    // 서브 텍스트 보충
    document.getElementById('stat-total-solved-sub').textContent = `정답 ${totalCorrect}개 / 오답 ${totalSolved - totalCorrect}개`;
    document.getElementById('stat-avg-accuracy-sub').textContent = `공부한 요일 기준 일평균 ${dailyAvg}문항`;
    document.getElementById('stat-study-time-sub').textContent = `문제당 평균 1.5분 풀이 환산`;


    // 스트릭(연속성) 지수 계산
    const sortedDays = Array.from(uniqueDays).sort((a, b) => new Date(b) - new Date(a));
    let streak = 0;
    if (sortedDays.length > 0) {
        let current = new Date();
        current.setHours(0, 0, 0, 0);
        const lastStudy = new Date(sortedDays[0]);
        lastStudy.setHours(0, 0, 0, 0);
        // 마지막 학습일이 오늘 혹은 어제인 경우 연속 학습 카운팅 시작
        const diffDays = Math.round((current - lastStudy) / (1000 * 60 * 60 * 24));
        if (diffDays <= 1) {
            streak = 1;
            let prevDate = lastStudy;
            for (let i = 1; i < sortedDays.length; i++) {
                const nextStudy = new Date(sortedDays[i]);
                nextStudy.setHours(0, 0, 0, 0);
                const gap = Math.round((prevDate - nextStudy) / (1000 * 60 * 60 * 24));
                if (gap === 1) {
                    streak++;
                    prevDate = nextStudy;
                } else if (gap > 1) {
                    break; // 연속성 깨짐
                }
            }
        }
    }

    // [설계 의도]
    // 전체 일별 학습 이력을 순회하여 일일 권장 학습 목표(APP_CONFIG에 정의)를 
    // 돌파한 성공(Success) 일수를 합산해 누적 정보 서브텍스트에 노출시킵니다.
    const dailyGoal = (window.APP_CONFIG && window.APP_CONFIG.DAILY_STUDY_GOAL) || 150;
    let successDays = 0;
    HistoryState.dailyHistory.forEach(day => {
        if (day.totalSolved >= dailyGoal) {
            successDays++;
        }
    });

    const activeDaysSubEl = document.getElementById('stat-active-days-sub');
    if (activeDaysSubEl) {
        const streakText = streak > 0 ? `🔥 현재 ${streak}일 연속 학습 중!` : '매일 꾸준히 잔디를 채워보세요.';
        activeDaysSubEl.innerHTML = `${streakText}<br><span style="color: var(--success); font-weight: 600; font-size: 0.72rem; margin-top: 0.2rem; display: inline-block;">🎯 일일목표(${dailyGoal}개) 달성: ${successDays}일</span>`;
    }
}

/**
 * 5. 일별 학습 이력 데이터 그룹화 가공
 */
function generateDailyHistory() {
    const dailyMap = {};

    HistoryState.allLogs.forEach(log => {
        const dateKey = formatDateKey(log.parsedDate);
        if (!dailyMap[dateKey]) {
            dailyMap[dateKey] = {
                dateStr: dateKey,
                totalSolved: 0,
                totalCorrect: 0,
                subjectCounts: { 'DB': 0, 'SE': 0, 'PM': 0, 'SA': 0, 'SC': 0 }
            };
        }

        const solved = log.total_questions || 0;
        const correct = log.correct_count || 0;
        const sub = log.subject;

        dailyMap[dateKey].totalSolved += solved;
        dailyMap[dateKey].totalCorrect += correct;
        if (dailyMap[dateKey].subjectCounts[sub] !== undefined) {
            dailyMap[dateKey].subjectCounts[sub] += solved;
        }
    });

    // 일자 기준 내림차순(최신순) 정렬된 배열 생성
    const sortedDates = Object.keys(dailyMap).sort((a, b) => new Date(b) - new Date(a));
    HistoryState.dailyHistory = sortedDates.map(dateKey => dailyMap[dateKey]);
}

function formatDateKey(date) {
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

/**
 * 6. Chart.js 시각화 차트 드로잉
 */
function renderCharts() {
    // 기존 차트들 파괴(리셋용)
    if (HistoryState.charts.trend) HistoryState.charts.trend.destroy();
    if (HistoryState.charts.radar) HistoryState.charts.radar.destroy();

    const logs = HistoryState.allLogs;
    const cssVars = getComputedStyle(document.body);
    const accentColor = cssVars.getPropertyValue('--accent-primary').trim() || '#8b5cf6';
    const textSecondary = cssVars.getPropertyValue('--text-secondary').trim() || '#64748b';

    // 다크/라이트 테마별 차트 배경 보조 톤
    const lineFillColor = HistoryState.theme === 'light'
        ? 'rgba(56, 83, 216, 0.12)'
        : 'rgba(139, 92, 246, 0.08)';
    const gridColor = HistoryState.theme === 'light'
        ? 'rgba(15, 23, 42, 0.10)'
        : 'rgba(255,255,255,0.03)';

    // 6-A. 최근 30일 간의 트렌드 차트용 데이터 가공
    const dailyTrend = {};
    for (let i = 29; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const key = formatDateKey(d);
        dailyTrend[key] = 0;
    }

    logs.forEach(log => {
        const key = formatDateKey(log.parsedDate);
        if (dailyTrend[key] !== undefined) {
            dailyTrend[key] += (log.total_questions || 0);
        }
    });

    const labels = Object.keys(dailyTrend).map(dateStr => {
        const parts = dateStr.split('-');
        return `${parts[1]}/${parts[2]}`; // MM/DD 형식
    });
    const trendValues = Object.values(dailyTrend);

    const trendCtx = document.getElementById('trendChart').getContext('2d');
    HistoryState.charts.trend = new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '일별 푼 문항 수',
                data: trendValues,
                borderColor: accentColor,
                borderWidth: 2,
                backgroundColor: lineFillColor,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: accentColor,
                pointRadius: 1.5,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: textSecondary, font: { size: 9 } }
                },
                y: {
                    grid: { color: gridColor },
                    ticks: { color: textSecondary, font: { size: 9 }, stepSize: 5 }
                }
            }
        }
    });

    // 6-B. 과목별 비중 차트 데이터 가공 (도넛 차트)
    const subjectDistribution = { 'DB': 0, 'SE': 0, 'PM': 0, 'SA': 0, 'SC': 0 };
    logs.forEach(log => {
        const sub = log.subject;
        if (subjectDistribution[sub] !== undefined) {
            subjectDistribution[sub] += (log.total_questions || 0);
        }
    });

    const radarCtx = document.getElementById('radarChart').getContext('2d');
    HistoryState.charts.radar = new Chart(radarCtx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(subjectDistribution).map(k => SUBJECT_NAMES[k]),
            datasets: [{
                data: Object.values(subjectDistribution),
                backgroundColor: [
                    'rgba(139, 92, 246, 0.75)', // DB
                    'rgba(59, 130, 246, 0.75)',  // SE
                    'rgba(236, 72, 153, 0.75)',  // PM
                    'rgba(245, 158, 11, 0.75)',  // SA
                    'rgba(16, 185, 129, 0.75)'   // SC
                ],
                borderColor: '#11152c',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: textSecondary,
                        font: { size: 10 },
                        boxWidth: 10,
                        padding: 10
                    }
                }
            },
            cutout: '60%',
            onClick: (event, activeElements) => {
                if (activeElements && activeElements.length > 0) {
                    const index = activeElements[0].index;
                    const subjects = ['DB', 'SE', 'PM', 'SA', 'SC'];
                    const clickedSubject = subjects[index];

                    if (HistoryState.yearlySelectedChartSubject === clickedSubject) {
                        HistoryState.yearlySelectedChartSubject = null;
                        restoreTrendChartToTotalQuestions();
                    } else {
                        HistoryState.yearlySelectedChartSubject = clickedSubject;
                        updateTrendChartToSubjectScore(clickedSubject);
                    }
                } else {
                    HistoryState.yearlySelectedChartSubject = null;
                    restoreTrendChartToTotalQuestions();
                }
            }
        }
    });
}

/**
 * 최근 30일 학습 추이 차트를 특정 과목의 일별 평균 점수(정답률)로 변경합니다.
 */
function updateTrendChartToSubjectScore(clickedSubject) {
    const logs = HistoryState.allLogs;
    const dailySubCorrect = {};
    const dailySubSolved = {};
    
    for (let i = 29; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const key = formatDateKey(d);
        dailySubCorrect[key] = 0;
        dailySubSolved[key] = 0;
    }

    logs.forEach(log => {
        const key = formatDateKey(log.parsedDate);
        if (log.subject === clickedSubject && dailySubSolved[key] !== undefined) {
            dailySubCorrect[key] += (log.correct_count || 0);
            dailySubSolved[key] += (log.total_questions || 0);
        }
    });

    const trendValues = Object.keys(dailySubSolved).map(key => {
        const solved = dailySubSolved[key];
        const correct = dailySubCorrect[key];
        return solved > 0 ? Math.round((correct / solved) * 100) : 0;
    });

    const chart = HistoryState.charts.trend;
    if (chart) {
        chart.data.datasets[0].data = trendValues;
        chart.data.datasets[0].label = `${SUBJECT_NAMES[clickedSubject]} 일별 평균 점수 (%)`;
        chart.update();
    }
}

/**
 * 최근 30일 학습 추이 차트를 전체 푼 문제 수 기본 트렌드로 복원합니다.
 */
function restoreTrendChartToTotalQuestions() {
    const logs = HistoryState.allLogs;
    const dailyTrend = {};
    
    for (let i = 29; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const key = formatDateKey(d);
        dailyTrend[key] = 0;
    }

    logs.forEach(log => {
        const key = formatDateKey(log.parsedDate);
        if (dailyTrend[key] !== undefined) {
            dailyTrend[key] += (log.total_questions || 0);
        }
    });

    const trendValues = Object.values(dailyTrend);
    const chart = HistoryState.charts.trend;
    if (chart) {
        chart.data.datasets[0].data = trendValues;
        chart.data.datasets[0].label = '일별 푼 문항 수';
        chart.update();
    }
}

/**
 * 7. 하단 상세 기출 풀이 이력 테이블 페이징 렌더링
 */
function renderHistoryTable() {
    const tbody = document.getElementById('history-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const dailyData = HistoryState.dailyHistory;
    const totalRecords = dailyData.length;

    const startIdx = (HistoryState.currentPage - 1) * HistoryState.pageSize;
    const endIdx = startIdx + HistoryState.pageSize;
    const pageData = dailyData.slice(startIdx, endIdx);

    pageData.forEach(row => {
        const tr = document.createElement('tr');

        // 날짜 포맷 (예: 2026년 06월 23일)
        const dateParts = row.dateStr.split('-');
        const dateFormatted = `${dateParts[0]}년 ${dateParts[1]}월 ${dateParts[2]}일`;

        // 정답률 계산
        const acc = row.totalSolved > 0 ? Math.round((row.totalCorrect / row.totalSolved) * 100) : 0;


        // 추정 학습 시간 계산 (문제당 1.5분 환산)
        const totalMinutes = Math.round(row.totalSolved * 1.5);
        const hours = Math.floor(totalMinutes / 60);
        const mins = totalMinutes % 60;
        const timeStr = hours > 0 ? `${hours}시간 ${mins}분` : `${mins}분`;

        // [설계 의도]
        // 일일 학습 목표 기준 달성 여부를 검사하여 
        // 시인성이 뛰어난 성공(success)/실패(fail) 뱃지 레이아웃을 생성합니다.
        const goalLimit = (window.APP_CONFIG && window.APP_CONFIG.DAILY_STUDY_GOAL) || 150;
        const isSuccess = row.totalSolved >= goalLimit;
        const statusHtml = isSuccess
            ? `<span class="goal-badge success">성공 🎉</span>`
            : `<span class="goal-badge fail">실패 😢 (${row.totalSolved}/${goalLimit})</span>`;

        const datePart = row.dateStr.replace(/-/g, '').slice(2); // '2026-06-29' -> '260629'
        const reportUrl = `../../analytics/output/diagnostics_report_${datePart}.html`;
        const reportCellId = `report-cell-${row.dateStr}`;

        tr.innerHTML = `
            <td>${dateFormatted}</td>
            <td><strong>${row.totalSolved}개</strong></td>
            <td>${acc}%</td>
            <td>${timeStr}</td>
            <td>${statusHtml}</td>
            <td id="${reportCellId}"><span style="color: var(--text-muted); font-size: 0.75rem;">-</span></td>
        `;

        // 비동기적으로 해당 날짜의 오답분석 파일이 존재하는지 검증 (전용 API를 활용하여 404 콘솔 로그 노출 차단)
        fetch(`/api/analytics/check-report?date=${datePart}`)
            .then(res => res.ok ? res.json() : { exists: false })
            .then(data => {
                if (data.exists) {
                    const cell = document.getElementById(reportCellId);
                    if (cell) {
                        cell.innerHTML = `<a href="${reportUrl}" target="_blank" class="back-btn" style="padding: 0.25rem 0.6rem; font-size: 0.72rem; margin: 0; background: rgba(139, 92, 246, 0.15); border-color: rgba(139, 92, 246, 0.3); color: #a78bfa; text-decoration: none;" onclick="event.stopPropagation();">리포트 보기 🔍</a>`;
                    }
                }
            })
            .catch(() => { });

        // 행 클릭 이벤트 바인딩: 과목별 상세 레이어 팝업 노출
        tr.addEventListener('click', () => {
            showDailyDetail(row);
        });

        tbody.appendChild(tr);
    });

    // 페이징 버튼 제어
    const maxPage = Math.ceil(totalRecords / HistoryState.pageSize) || 1;
    document.getElementById('page-info').textContent = `페이지 ${HistoryState.currentPage} / ${maxPage}`;
    document.getElementById('btn-prev-page').disabled = (HistoryState.currentPage === 1);
    document.getElementById('btn-next-page').disabled = (HistoryState.currentPage === maxPage);
}

function prevPage() {
    if (HistoryState.currentPage > 1) {
        HistoryState.currentPage--;
        renderHistoryTable();
    }
}

function nextPage() {
    const maxPage = Math.ceil(HistoryState.dailyHistory.length / HistoryState.pageSize) || 1;
    if (HistoryState.currentPage < maxPage) {
        HistoryState.currentPage++;
        renderHistoryTable();
    }
}

/**
 * 8. 과목별 학습건수 상세 모달 레이어 표시
 */
function showDailyDetail(row) {
    const modal = document.getElementById('daily-detail-modal');
    const modalTitle = document.getElementById('daily-modal-title');
    const modalBody = document.getElementById('daily-modal-body');

    if (!modal || !modalTitle || !modalBody) return;

    const dateParts = row.dateStr.split('-');
    const dateFormatted = `${dateParts[0]}년 ${dateParts[1]}월 ${dateParts[2]}일`;
    modalTitle.innerHTML = `📅 ${dateFormatted} 학습 상세`;

    modalBody.innerHTML = '';
    const subjects = ['DB', 'SE', 'PM', 'SA', 'SC'];
    subjects.forEach(sub => {
        const count = row.subjectCounts[sub] || 0;
        const rowEl = document.createElement('div');
        rowEl.className = 'modal-subject-row';
        rowEl.innerHTML = `
            <span class="subject-badge ${sub}">${SUBJECT_NAMES[sub]}</span>
            <span style="font-weight: 600; color: var(--text-primary);">${count}개 문항 풀이</span>
        `;
        modalBody.appendChild(rowEl);
    });

    modal.classList.add('show');
}

/**
 * 9. 모달 닫기
 */
function closeDailyModal(event) {
    const modal = document.getElementById('daily-detail-modal');
    if (modal) {
        modal.classList.remove('show');
    }
}

/**
 * 8. 한국어 형식으로 일시를 예쁘게 포맷팅
 */
function formatKoreanDate(dateStr) {
    if (!dateStr) return '';
    let standardized = dateStr;
    if (!dateStr.includes('T') && dateStr.includes(' ')) {
        standardized = dateStr.replace(' ', 'T') + 'Z';
    } else if (!dateStr.endsWith('Z') && dateStr.includes('T')) {
        standardized = dateStr + 'Z';
    }
    const d = new Date(standardized);
    if (isNaN(d.getTime())) return dateStr;
    const yy = String(d.getFullYear()).slice(-2);
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${yy}/${mm}/${dd} ${hh}:${min}`;
}

/**
 * 9. 빈 기록 상태 렌더링
 */
function renderEmptyState() {
    const dashboardRows = document.querySelectorAll('.dashboard-row, .stats-grid');
    dashboardRows.forEach(row => row.style.display = 'none');

    const emptyContainer = document.createElement('div');
    emptyContainer.className = 'card empty-state';
    emptyContainer.style.marginTop = '2rem';
    emptyContainer.innerHTML = `
        <i data-lucide="bar-chart-3"></i>
        <h3>등록된 학습 이력이 존재하지 않습니다.</h3>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 0.5rem; line-height: 1.5;">
            메인 대시보드 뷰어에서 예상 기출문제를 풀거나 복습을 시작하면<br>
            자동으로 풀이 데이터가 저장되어 누적 통계 잔디를 심기 시작합니다!
        </p>
        <a href="../db_official_scopes.html" class="back-btn" style="margin-top: 1.5rem; display: inline-flex;">
            대시보드로 돌아가기
        </a>
    `;


    document.querySelector('.container').appendChild(emptyContainer);
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * 10. [설계 의도] 5대 과목별 레벨링 카드 그리드를 화면에 동적 주입합니다.
 * - 각 과목에 부합하는 응원 펫 캐릭터 이미지와 독립 레벨, 경험치 게이지를 렌더링합니다.
 * - 글래스모피즘 테마를 입혀 수려한 프리미엄 UI 디자인으로 사용자의 학습 의욕을 고취시킵니다.
 */
function renderSubjectExpCards(expData, subjectAccuracies = {}) {
    const container = document.getElementById('subject-exp-grid');
    if (!container) return;

    container.innerHTML = '';
    const subjects = ['DB', 'SE', 'PM', 'SA', 'SC'];

    const subExps = expData.subjects_exp || {};
    const config = window.APP_CONFIG || {};
    const defaultPets = config.SUBJECT_DEFAULT_PETS || {};
    const petProfiles = config.PET_PROFILES || {};

    // 2015~2017년도를 제외한 2018~2026년도 대상 과목별 신규 기출 비중 동적 연산
    const targetYears = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
    const subRanges = {
        'PM': [1, 25],
        'SE': [26, 50],
        'DB': [51, 75],
        'SA': [76, 100],
        'SC': [101, 120]
    };

    const trendStats = {};
    for (let code in subRanges) {
        let trendCount = 0;
        let totalCount = 0;
        const range = subRanges[code];

        targetYears.forEach(yr => {
            for (let q = range[0]; q <= range[1]; q++) {
                const key = `${yr}_${q}`;
                totalCount++;
                if (window.NEW_TREND_MAPPING && window.NEW_TREND_MAPPING[key] === 1) {
                    trendCount++;
                }
            }
        });

        const ratio = totalCount > 0 ? ((trendCount / totalCount) * 100).toFixed(1) : '0.0';
        trendStats[code] = `${ratio}% (${trendCount}/${totalCount})`;
    }

    subjects.forEach(sub => {
        const subData = subExps[sub] || { total_exp: 0, level: 1, exp_in_level: 0, exp_to_next: 10 };
        const petKey = defaultPets[sub] || 'pikachu';
        const pet = petProfiles[petKey] || { name: '피카츄', src: '/reports/images_game/pikachuRun.gif' };

        const card = document.createElement('div');
        card.className = 'subject-exp-card';

        // 경험치바 백분율 계산
        const expPercent = (subData.exp_in_level / 10) * 100;
        const nextLevelExp = subData.level * 10;

        // 평균 정답률 값 획득 (포맷 지정)
        const accRate = subjectAccuracies[sub] !== undefined ? subjectAccuracies[sub] : 0.0;

        card.innerHTML = `
            <div class="sub-exp-header">
                <span class="sub-exp-title">${SUBJECT_NAMES[sub]}</span>
                <span class="sub-exp-badge ${sub}">${sub}</span>
            </div>
            <div class="sub-exp-body">
                <div class="sub-exp-pet-avatar" title="${pet.name}">
                    <img src="${pet.src}" alt="${pet.name}">
                </div>
                <div class="sub-exp-level-wrap">
                    <span class="sub-exp-level-label">LEVEL</span>
                    <span class="sub-exp-level-val">${subData.level}</span>
                </div>
            </div>
            <div class="sub-exp-bar-wrap">
                <div class="sub-exp-bar-info">
                    <span>${subData.total_exp} EXP (${subData.exp_in_level} / 10)</span>
                    <span style="color: var(--success); font-weight: 700;">정답률: ${accRate}%</span>
                </div>
                <div style="font-size: 0.72rem; color: #ec4899; font-weight: 600; margin-bottom: 0.35rem; display: flex; justify-content: space-between; align-items: center;">
                    <span>신규 기출 비중:</span>
                    <span>${trendStats[sub]}</span>
                </div>
                <div class="sub-exp-bar-bg">
                    <div class="sub-exp-bar-fill" style="width: ${expPercent}%"></div>
                </div>
            </div>
        `;
        container.appendChild(card);
    });

    // 동적 아이콘 리프레시
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * ==========================================================================
 * [NEW] AI 중단원별 취약점 진단 및 추천 예측 로직
 * ==========================================================================
 */

/**
 * 11. 백엔드 분석 API로부터 데이터를 호출하여 캐싱합니다.
 */
function loadAnalyticsData() {
    fetch('/api/analytics/concept-diagnostics')
        .then(res => res.ok ? res.json() : null)
        .then(data => {
            if (data && data.subjects) {
                HistoryState.analyticsData = data.subjects;
                // 최초 진입 시 지정된 기본 과목(DB) 렌더링
                renderAnalytics(HistoryState.currentSubject);
            } else {
                console.warn("[Analytics] 학습 분석 데이터를 불러오지 못했거나 포맷이 유효하지 않습니다.");
                renderEmptyAnalytics();
            }
        })
        .catch(err => {
            console.error("[Analytics] 분석 API 호출 실패:", err);
            renderEmptyAnalytics();
        });
}

/**
 * 12. 과목 탭 전환 핸들러
 */
function switchAnalyticsTab(subject) {
    HistoryState.currentSubject = subject;

    // active 탭 버튼 클래스 교환
    const tabIds = {
        'DB': 'tab-btn-db',
        'SE': 'tab-btn-se',
        'PM': 'tab-btn-pm',
        'SA': 'tab-btn-sa',
        'SC': 'tab-btn-sc'
    };

    Object.keys(tabIds).forEach(sub => {
        const btn = document.getElementById(tabIds[sub]);
        if (btn) {
            if (sub === subject) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        }
    });

    renderAnalytics(subject);
}

/**
 * 13. 선택된 과목의 분석 결과를 화면에 렌더링합니다.
 */
function renderAnalytics(subject) {
    const data = HistoryState.analyticsData;
    if (!data || !data[subject]) {
        renderEmptyAnalytics();
        return;
    }

    const subjectInfo = data[subject];
    const strengthList = document.getElementById('strength-list');
    const weaknessList = document.getElementById('weakness-list');
    const recContainer = document.getElementById('recommendation-container');

    if (!strengthList || !weaknessList || !recContainer) return;

    // 13-A. 강점(Strengths) 렌더링
    strengthList.innerHTML = '';
    if (subjectInfo.strengths && subjectInfo.strengths.length > 0) {
        subjectInfo.strengths.forEach(topic => {
            const li = document.createElement('li');
            li.className = 'diag-list-item strength';
            const acc = Math.round((subjectInfo.concepts[topic].accuracy) * 100);
            li.innerHTML = `
                <span class="topic-name">${topic}</span>
                <span class="topic-accuracy success">${acc}% 정답</span>
            `;
            strengthList.appendChild(li);
        });
    } else {
        strengthList.innerHTML = '<li class="empty-list-item">아직 숙달된 강점 단원이 없습니다. 더 많은 문제를 맞춰보세요!</li>';
    }

    // 13-B. 약점(Weaknesses) 렌더링
    weaknessList.innerHTML = '';
    if (subjectInfo.weaknesses && subjectInfo.weaknesses.length > 0) {
        subjectInfo.weaknesses.forEach(topic => {
            const li = document.createElement('li');
            li.className = 'diag-list-item weakness';
            const acc = Math.round((subjectInfo.concepts[topic].accuracy) * 100);
            li.innerHTML = `
                <span class="topic-name">${topic}</span>
                <span class="topic-accuracy error">${acc}% 정답</span>
            `;
            weaknessList.appendChild(li);
        });
    } else {
        weaknessList.innerHTML = '<li class="empty-list-item">분석된 약점 단원이 없습니다. 아주 훌륭한 학습 성과입니다!</li>';
    }

    // 13-C. 추천 학습 순서 예측(Recommendations) 렌더링
    recContainer.innerHTML = '';

    // 유효한 추천 항목만 필터링 (학습 이력이 없는 중단원은 리스트에 포함되지 않거나 기본값 처리)
    const recs = subjectInfo.recommendations || [];

    if (recs.length > 0) {
        recs.forEach((rec, idx) => {
            const card = document.createElement('div');
            card.className = 'rec-item-card';

            // 점수에 비례해 우선순위 뱃지 설정
            let priorityBadge = '';
            if (idx === 0) {
                priorityBadge = '<span class="rec-badge rank-1">🏆 최우선 순위</span>';
            } else if (rec.score >= 5.0) {
                priorityBadge = '<span class="rec-badge rank-2">🔥 중요 추천</span>';
            } else {
                priorityBadge = '<span class="rec-badge rank-3">📘 일반 권장</span>';
            }

            // 추천 게이지 진행률 바 백분율 계산 (최대치 15점 기준 환산)
            const gaugePercent = Math.min(100, Math.round((rec.score / 15.0) * 100));

            card.innerHTML = `
                <div class="rec-header">
                    <span class="rec-topic-title">${rec.concept}</span>
                    ${priorityBadge}
                </div>
                <div class="rec-body">
                    <p class="rec-reason">${rec.reason}</p>
                    <div class="rec-score-row">
                        <span class="rec-score-label">AI 학습 우선순위 지수: <strong>${rec.score} / 15.0</strong></span>
                        <div class="rec-gauge-bg">
                            <div class="rec-gauge-fill" style="width: ${gaugePercent}%"></div>
                        </div>
                    </div>
                </div>
            `;
            recContainer.appendChild(card);
        });
    } else {
        recContainer.innerHTML = `
            <div class="empty-recommendation">
                <i data-lucide="info" style="width: 40px; height: 40px; color: var(--text-muted); margin-bottom: 0.8rem;"></i>
                <h3>추천 예측을 위한 데이터 부족</h3>
                <p>현재 과목에서 푼 문제가 너무 적어 추천 대상을 예측할 수 없습니다.<br>문제를 더 풀면 실시간으로 분석이 개시됩니다.</p>
            </div>
        `;
    }

    // 동적 아이콘 리프레시
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * 14. 학습 이력 혹은 분석 데이터가 완전 공백일 때 렌더러
 */
function renderEmptyAnalytics() {
    const strengthList = document.getElementById('strength-list');
    const weaknessList = document.getElementById('weakness-list');
    const recContainer = document.getElementById('recommendation-container');

    if (strengthList) strengthList.innerHTML = '<li class="empty-list-item">충분한 풀이 정보가 없습니다.</li>';
    if (weaknessList) weaknessList.innerHTML = '<li class="empty-list-item">충분한 풀이 정보가 없습니다.</li>';
    if (recContainer) {
        recContainer.innerHTML = `
            <div class="empty-recommendation">
                <i data-lucide="database" style="width: 40px; height: 40px; color: var(--text-muted); margin-bottom: 0.8rem;"></i>
                <h3>데이터 가용성 대기 중</h3>
                <p>서버 데이터베이스에서 기출 퀴즈 풀이 이력(quiz_history)을 읽는 중이거나 데이터가 부족합니다.</p>
            </div>
        `;
    }

    if (window.lucide) {
        lucide.createIcons();
    }
}

let isYearlyEventInitialized = false;

/**
 * [설계 의도] 기출 연도/과목 필터 드롭다운 바인딩 및 정렬 이벤트를 설정합니다.
 */
function initYearlyExamFiltersAndSorting(historyList) {
    if (isYearlyEventInitialized) return;

    // 1. 기출 연도 필터 옵션 추출 및 주입
    const yearSelect = document.getElementById('filter-exam-year');
    if (yearSelect && historyList && historyList.length > 0) {
        const years = Array.from(new Set(historyList.map(item => item.exam_year)))
            .sort((a, b) => b - a); // 최신년도 순 정렬
        years.forEach(yr => {
            const opt = document.createElement('option');
            opt.value = yr;
            opt.textContent = `${yr}년도 기출`;
            yearSelect.appendChild(opt);
        });
    }

    // 2. 필터 체인지 리스너 바인딩
    const subSelect = document.getElementById('filter-exam-subject');
    if (yearSelect) {
        yearSelect.addEventListener('change', (e) => {
            HistoryState.yearlyFilterYear = e.target.value;
            HistoryState.yearlyCurrentPage = 1;
            renderYearlyExamHistoryTable(HistoryState.yearlyExamHistory);
        });
    }
    if (subSelect) {
        subSelect.addEventListener('change', (e) => {
            HistoryState.yearlyFilterSubject = e.target.value;
            HistoryState.yearlyCurrentPage = 1;
            renderYearlyExamHistoryTable(HistoryState.yearlyExamHistory);
        });
    }

    // 3. 헤더 클릭 정렬 이벤트 바인딩
    const thRow = document.getElementById('yearly-history-th-row');
    if (thRow) {
        thRow.querySelectorAll('th').forEach(th => {
            th.addEventListener('click', () => {
                const key = th.getAttribute('data-sort-key');
                if (!key) return;

                HistoryState.yearlyCurrentPage = 1;

                if (HistoryState.yearlySortKey === key) {
                    HistoryState.yearlySortOrder = (HistoryState.yearlySortOrder === 'desc') ? 'asc' : 'desc';
                } else {
                    HistoryState.yearlySortKey = key;
                    HistoryState.yearlySortOrder = 'desc'; // 기본값 내림차순
                }

                // 화살표 상태 갱신
                thRow.querySelectorAll('th').forEach(t => {
                    const span = t.querySelector('.sort-icon');
                    if (span) {
                        const tKey = t.getAttribute('data-sort-key');
                        if (tKey === HistoryState.yearlySortKey) {
                            span.textContent = (HistoryState.yearlySortOrder === 'desc') ? ' ▼' : ' ▲';
                            span.style.color = 'var(--accent-primary)';
                            t.style.color = 'var(--accent-primary)';
                        } else {
                            span.textContent = '';
                            span.style.color = '';
                            t.style.color = '';
                        }
                    }
                });

                renderYearlyExamHistoryTable(HistoryState.yearlyExamHistory);
            });
        });
    }

    isYearlyEventInitialized = true;
}

/**
 * [설계 의도] 년도별 120제 모의고사 연습 이력 테이블을 필터링 및 정렬 기준에 맞춰 동적으로 렌더링합니다.
 */
function renderYearlyExamHistoryTable(historyList) {
    const tbody = document.getElementById('yearly-history-tbody');
    if (!tbody) return;

    if (!historyList || historyList.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2.5rem; font-size: 0.9rem;">
                    📢 아직 완료된 년도별 모의고사 연습 이력이 없습니다.
                </td>
            </tr>
        `;
        return;
    }

    // [설계 의도]
    // 동일 년도 + 동일 과목 풀이 구성에 한해서 회차를 매기기 위해
    // 전체 historyList를 시간 오름차순(과거 순)으로 정렬하여 회차 카운트 맵을 동적으로 생성합니다.
    const getSubjectKey = (item) => {
        let details = [];
        try {
            details = (typeof item.details === 'string') ? JSON.parse(item.details) : (item.details || []);
        } catch (e) {
            details = [];
        }
        if (!details || details.length === 0) return 'ALL';
        
        const codeSet = new Set();
        details.forEach(d => {
            const code = getYearlySubjectCodeByQuestionNum(d.question_num);
            if (code) codeSet.add(code);
        });
        const ordered = ['PM', 'SE', 'DB', 'SA', 'SC'].filter(code => codeSet.has(code));
        if (ordered.length === 0 || ordered.length === 5) return 'ALL';
        return ordered.join(',');
    };

    const sortedByTimeAsc = [...historyList].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    const counterMap = {};
    const computedPracticeCounts = {};

    sortedByTimeAsc.forEach(item => {
        const subKey = getSubjectKey(item);
        const compositeKey = `${item.exam_year}_${subKey}`;
        if (!counterMap[compositeKey]) {
            counterMap[compositeKey] = 0;
        }
        counterMap[compositeKey]++;
        computedPracticeCounts[item.id] = counterMap[compositeKey];
    });

    // 1. 필터링 수행
    let data = [...historyList];
    if (HistoryState.yearlyFilterYear !== 'all') {
        data = data.filter(item => String(item.exam_year) === String(HistoryState.yearlyFilterYear));
    }
    if (HistoryState.yearlyFilterSubject !== 'all') {
        data = data.filter(item => {
            const details = parseYearlyDetails(item);
            const targetSub = HistoryState.yearlyFilterSubject;

            // 과목 영역 범위 매핑
            const ranges = {
                'PM': [1, 25],
                'SE': [26, 50],
                'DB': [51, 75],
                'SA': [76, 100],
                'SC': [101, 120]
            };
            const r = ranges[targetSub];
            if (!r) return false;

            return details.some(d => Number(d.question_num) >= r[0] && Number(d.question_num) <= r[1]);
        });
    }

    // 2. 정렬 수행
    const sortKey = HistoryState.yearlySortKey;
    const orderMult = (HistoryState.yearlySortOrder === 'desc') ? -1 : 1;

    data.sort((a, b) => {
        let valA, valB;
        if (sortKey === 'created_at') {
            valA = new Date(a.created_at).getTime();
            valB = new Date(b.created_at).getTime();
        } else if (sortKey === 'exam_year') {
            valA = Number(a.exam_year);
            valB = Number(b.exam_year);
        } else if (sortKey === 'subject_summary') {
            valA = summarizeYearlyExamSubjects(a);
            valB = summarizeYearlyExamSubjects(b);
            return valA.localeCompare(valB) * orderMult;
        } else if (sortKey === 'practice_count') {
            valA = Number(a.practice_count || 0);
            valB = Number(b.practice_count || 0);
        } else if (sortKey === 'correct_count') {
            valA = Number(a.correct_count || 0);
            valB = Number(b.correct_count || 0);
        } else if (sortKey === 'total_time') {
            valA = Number(a.total_time || 0);
            valB = Number(b.total_time || 0);
        } else if (sortKey === 'score') {
            valA = parseFloat(a.score || 0.0);
            valB = parseFloat(b.score || 0.0);
        } else {
            return 0;
        }

        if (valA < valB) return -1 * orderMult;
        if (valA > valB) return 1 * orderMult;
        return 0;
    });

    // 3. 필터링된 결과가 없는 경우
    if (data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2.5rem; font-size: 0.88rem;">
                    📢 선택한 기출 연도 및 과목 필터에 부합하는 모의고사 연습 기록이 없습니다.
                </td>
            </tr>
        `;
        updateYearlyPagination(0);
        return;
    }

    const totalCount = data.length;
    HistoryState.yearlyTotalPages = Math.ceil(totalCount / HistoryState.yearlyPageSize) || 1;

    if (HistoryState.yearlyCurrentPage > HistoryState.yearlyTotalPages) {
        HistoryState.yearlyCurrentPage = HistoryState.yearlyTotalPages;
    }
    if (HistoryState.yearlyCurrentPage < 1) {
        HistoryState.yearlyCurrentPage = 1;
    }

    const startIndex = (HistoryState.yearlyCurrentPage - 1) * HistoryState.yearlyPageSize;
    const endIndex = startIndex + HistoryState.yearlyPageSize;
    const pagedData = data.slice(startIndex, endIndex);

    // 4. 테이블 행 그리기
    tbody.innerHTML = '';
    pagedData.forEach(item => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.title = '클릭하면 상세 채점 분석 및 문항별 풀이 시간 리포트 팝업이 열립니다.';
        tr.onclick = () => openYearlyModal(item);

        const formattedDate = formatYearlyKoreanDateTime(item.created_at);
        const score = item.score !== undefined ? parseFloat(item.score).toFixed(1) : '0.0';
        const subjectSummary = summarizeYearlyExamSubjects(item);
        const timeStr = formatSecondsToKorean(item.total_time);

        // details 문자열 또는 객체 파싱
        let details = [];
        try {
            details = (typeof item.details === 'string') ? JSON.parse(item.details) : (item.details || []);
        } catch (e) {
            details = [];
        }

        let normalTotal = 0;
        let normalCorr = 0;
        let newTotal = 0;
        let newCorr = 0;

        details.forEach(d => {
            const qid = `${item.exam_year}_${d.question_num}`;
            const isNew = (window.NEW_TREND_MAPPING && window.NEW_TREND_MAPPING[qid] === 1);
            if (isNew) {
                newTotal++;
                if (d.is_correct) newCorr++;
            } else {
                normalTotal++;
                if (d.is_correct) normalCorr++;
            }
        });

        const totalQuestions = newTotal + normalTotal;
        const newTrendRatio = totalQuestions > 0 ? ((newTotal / totalQuestions) * 100).toFixed(1) : '0.0';

        const trendStatsHtml = `
            <span style="color: #ec4899; font-weight: 600;">${newTrendRatio}%</span> 
            <span style="color: var(--text-secondary); font-size: 0.74rem;">(${newTotal}개)</span>
        `;

        const displayPracticeCount = computedPracticeCounts[item.id] || item.practice_count || 1;

        tr.innerHTML = `
            <td style="font-size: 0.85rem; color: var(--text-secondary);">${formattedDate}</td>
            <td style="font-family: 'Outfit', sans-serif; font-weight: 700; color: var(--text-primary); font-size: 0.9rem;">${item.exam_year}</td>
            <td style="font-size: 0.8rem; color: var(--text-primary);">${subjectSummary}</td>
            <td><span class="badge" style="background: rgba(139, 92, 246, 0.12); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.2); font-size: 0.72rem; padding: 0.2rem 0.5rem; border-radius: 6px; font-weight: 600;">${displayPracticeCount}회차</span></td>
            <td style="font-size: 0.88rem; font-weight: 500;">${item.correct_count} / ${item.total_questions}</td>
            <td style="font-size: 0.85rem; color: var(--text-secondary);">${timeStr}</td>
            <td style="font-weight: 700; color: var(--success); font-size: 0.95rem;">${score}점</td>
            <td style="font-size: 0.82rem; white-space: nowrap;">${trendStatsHtml}</td>
        `;
        tbody.appendChild(tr);
    });

    if (window.lucide) {
        lucide.createIcons();
    }
    updateYearlyPagination(HistoryState.yearlyTotalPages);
}

function getYearlySubjectCodeByQuestionNum(questionNum) {
    const q = Number(questionNum);
    if (q >= 1 && q <= 25) return 'PM';
    if (q >= 26 && q <= 50) return 'SE';
    if (q >= 51 && q <= 75) return 'DB';
    if (q >= 76 && q <= 100) return 'SA';
    if (q >= 101 && q <= 120) return 'SC';
    return null;
}

function summarizeYearlyExamSubjects(item) {
    let details = [];
    try {
        details = (typeof item.details === 'string')
            ? JSON.parse(item.details)
            : (item.details || []);
    } catch (e) {
        details = [];
    }

    if (!details || details.length === 0) {
        return '전체';
    }

    const codeSet = new Set();
    details.forEach(d => {
        const code = getYearlySubjectCodeByQuestionNum(d.question_num);
        if (code) codeSet.add(code);
    });

    const ordered = YEARLY_SUBJECT_ORDER.filter(code => codeSet.has(code));
    if (ordered.length === 0) return '전체';
    if (ordered.length === YEARLY_SUBJECT_ORDER.length) return '전체';
    return ordered.map(code => SUBJECT_NAMES[code]).join(', ');
}

function parseYearlyDetails(item) {
    try {
        return (typeof item.details === 'string')
            ? JSON.parse(item.details)
            : (item.details || []);
    } catch (e) {
        return [];
    }
}

function normalizeAnswerArray(ans) {
    const arr = Array.isArray(ans) ? ans : (ans === null || ans === undefined ? [] : [ans]);
    return Array.from(new Set(arr.map(v => Number(v)).filter(v => !Number.isNaN(v)))).sort((a, b) => a - b);
}

function answerArrayToText(ans) {
    const normalized = normalizeAnswerArray(ans);
    return normalized.length > 0 ? normalized.join(', ') : '미선택';
}

function isExactAnswerMatch(a, b) {
    const aa = normalizeAnswerArray(a);
    const bb = normalizeAnswerArray(b);
    if (aa.length !== bb.length) return false;
    for (let i = 0; i < aa.length; i++) {
        if (aa[i] !== bb[i]) return false;
    }
    return true;
}

function isCorrectByAnswer(userAnswer, correctAnswer) {
    return isExactAnswerMatch(userAnswer, correctAnswer);
}

function getWeaknessScoreLabel(score) {
    if (score >= 70) return '높음';
    if (score >= 45) return '주의';
    return '양호';
}

function getWeaknessScoreColor(score) {
    if (score >= 70) return '#f87171';
    if (score >= 45) return '#facc15';
    return '#34d399';
}

function calculateSubjectWeaknessScores(subStats, recurrenceBySubject, globalAvgTime) {
    const results = {};
    Object.keys(subStats).forEach(code => {
        const stat = subStats[code] || { correct: 0, total: 0, timeSum: 0 };
        if (stat.total <= 0) {
            results[code] = {
                weaknessScore: 0,
                wrongRate: 0,
                avgTime: 0,
                recurrenceRate: 0
            };
            return;
        }

        const wrongRate = ((stat.total - stat.correct) / stat.total) * 100;
        const avgTime = stat.timeSum / stat.total;
        const timeRisk = globalAvgTime > 0 ? Math.min(100, (avgTime / globalAvgTime) * 100) : 0;
        const recurrenceRate = Math.min(100, ((recurrenceBySubject[code] || 0) / stat.total) * 100);

        // 취약도 점수(0~100): 오답률 중심 + 시간 병목 + 재발 오답 가중치
        const weaknessScore = Math.round(
            (wrongRate * 0.60) +
            (timeRisk * 0.25) +
            (recurrenceRate * 0.15)
        );

        results[code] = {
            weaknessScore,
            wrongRate,
            avgTime,
            recurrenceRate
        };
    });

    return results;
}

function getYearlyWrongRecurrenceInsight(item, details) {
    const allHistory = Array.isArray(HistoryState.yearlyExamHistory) ? HistoryState.yearlyExamHistory : [];
    const currentDate = parseDate(item.created_at);

    const previousSameYear = allHistory.filter(h => {
        if (String(h.exam_year) !== String(item.exam_year)) return false;
        if (item.id !== undefined && h.id !== undefined && String(h.id) === String(item.id)) return false;
        const d = parseDate(h.created_at);
        return d < currentDate;
    });

    const prevWrongSet = new Set();
    previousSameYear.forEach(h => {
        const dList = parseYearlyDetails(h);
        dList.forEach(d => {
            if (!d.is_correct) {
                prevWrongSet.add(`${item.exam_year}_${Number(d.question_num)}`);
            }
        });
    });

    // 일반 퀴즈 이력(quiz_history)도 통합하여 재발 오답 집합을 생성합니다.
    // details 내부 q_id(예: 2025_17) 또는 question_num + 년도 추정값을 키로 사용합니다.
    const normalQuizLogs = Array.isArray(HistoryState.allLogs) ? HistoryState.allLogs : [];
    normalQuizLogs.forEach(log => {
        if (!log || !log.created_at) return;
        const logDate = parseDate(log.created_at);
        if (logDate >= currentDate) return;

        let dObj = null;
        if (typeof log.details === 'object' && log.details) {
            dObj = log.details;
        } else if (typeof log.details === 'string' && log.details.trim()) {
            try {
                dObj = JSON.parse(log.details);
            } catch (e) {
                dObj = null;
            }
        }
        if (!dObj) return;

        const isCorrect = !!dObj.is_correct;
        if (isCorrect) return;

        let qKey = null;
        if (typeof dObj.q_id === 'string' && dObj.q_id.includes('_')) {
            qKey = dObj.q_id;
        } else if (dObj.question_num !== undefined && dObj.question_num !== null) {
            qKey = `${item.exam_year}_${Number(dObj.question_num)}`;
        }

        if (qKey) {
            prevWrongSet.add(qKey);
        }
    });

    const currentWrong = details
        .filter(d => !d.is_correct)
        .map(d => Number(d.question_num));

    const currentWrongKeyList = currentWrong.map(qNum => `${item.exam_year}_${qNum}`);
    const recurringWrongKeyList = currentWrongKeyList.filter(qKey => prevWrongSet.has(qKey));
    const recurringWrong = recurringWrongKeyList
        .map(qKey => Number(String(qKey).split('_')[1]))
        .filter(qNum => !Number.isNaN(qNum));
    const recurringSet = new Set(recurringWrongKeyList);

    const improvedFromPast = Array.from(prevWrongSet).filter(qKey => !recurringSet.has(qKey));
    const recurrenceRate = currentWrong.length > 0
        ? Math.round((recurringWrong.length / currentWrong.length) * 100)
        : 0;

    const recurrenceBySubject = { PM: 0, SE: 0, DB: 0, SA: 0, SC: 0 };
    recurringWrong.forEach(qNum => {
        const code = getYearlySubjectCodeByQuestionNum(qNum);
        if (code && recurrenceBySubject[code] !== undefined) {
            recurrenceBySubject[code] += 1;
        }
    });

    return {
        previousAttemptCount: previousSameYear.length,
        currentWrongCount: currentWrong.length,
        recurringWrong,
        recurrenceRate,
        improvedCount: Math.max(0, improvedFromPast.length),
        recurrenceBySubject
    };
}

async function fetchYearlyQuestionData(item, detail) {
    const qNum = detail.question_num;
    const qIdCandidate = detail.q_id || `${item.exam_year}_${qNum}`;

    HistoryState.yearlyQuestionCache = HistoryState.yearlyQuestionCache || {};
    let questionData = HistoryState.yearlyQuestionCache[qIdCandidate];
    if (questionData) return questionData;

    let resp = await fetch(`/api/question?id=${encodeURIComponent(qIdCandidate)}`);

    if (!resp.ok && detail.q_id) {
        const fallbackId = `${item.exam_year}_${qNum}`;
        resp = await fetch(`/api/question?id=${encodeURIComponent(fallbackId)}`);
    }

    if (!resp.ok) {
        throw new Error(`문항 조회 실패 (HTTP ${resp.status})`);
    }

    questionData = await resp.json();
    HistoryState.yearlyQuestionCache[qIdCandidate] = questionData;
    return questionData;
}

function collectPastAnswerAttempts(item, detail) {
    const qNum = Number(detail.question_num);
    const qKey = `${item.exam_year}_${qNum}`;
    const currentDate = parseDate(item.created_at);
    const attempts = [];

    const allYearly = Array.isArray(HistoryState.yearlyExamHistory) ? HistoryState.yearlyExamHistory : [];
    allYearly.forEach(h => {
        if (String(h.exam_year) !== String(item.exam_year)) return;
        if (item.id !== undefined && h.id !== undefined && String(h.id) === String(item.id)) return;
        const hDate = parseDate(h.created_at);
        if (hDate >= currentDate) return;

        const hDetails = parseYearlyDetails(h);
        const matched = hDetails.find(d => Number(d.question_num) === qNum);
        if (!matched) return;

        attempts.push({
            source: '모의고사',
            created_at: h.created_at,
            user_answer: normalizeAnswerArray(matched.user_answer),
            is_correct: !!matched.is_correct
        });
    });

    const allLogs = Array.isArray(HistoryState.allLogs) ? HistoryState.allLogs : [];
    allLogs.forEach(log => {
        if (!log || !log.created_at) return;
        const lDate = parseDate(log.created_at);
        if (lDate >= currentDate) return;

        let dObj = null;
        if (typeof log.details === 'object' && log.details) {
            dObj = log.details;
        } else if (typeof log.details === 'string' && log.details.trim()) {
            try {
                dObj = JSON.parse(log.details);
            } catch (e) {
                dObj = null;
            }
        }
        if (!dObj) return;

        let isMatch = false;
        if (typeof dObj.q_id === 'string' && dObj.q_id.includes('_')) {
            isMatch = dObj.q_id === qKey;
        } else if (dObj.question_num !== undefined && dObj.question_num !== null) {
            isMatch = Number(dObj.question_num) === qNum;
        }
        if (!isMatch) return;

        const inferredCorrect = (dObj.is_correct !== undefined)
            ? !!dObj.is_correct
            : (Number(log.correct_count || 0) > 0);

        attempts.push({
            source: '일반퀴즈',
            created_at: log.created_at,
            user_answer: normalizeAnswerArray(dObj.user_answer),
            is_correct: inferredCorrect
        });
    });

    attempts.sort((a, b) => parseDate(b.created_at) - parseDate(a.created_at));
    return attempts;
}

async function renderRecurrenceAnswerComparison(item, detail) {
    const container = document.getElementById('yearly-recurrence-compare-box');
    if (!container) return;

    container.innerHTML = `<div style="font-size:0.78rem; color: var(--text-secondary);">${detail.question_num}번 문항의 과거 답안 이력을 분석 중...</div>`;

    try {
        const questionData = await fetchYearlyQuestionData(item, detail);
        const correctAnswer = normalizeAnswerArray(questionData.answer);
        const currentAnswer = normalizeAnswerArray(detail.user_answer);
        const currentIsCorrect = isCorrectByAnswer(currentAnswer, correctAnswer);

        const attempts = collectPastAnswerAttempts(item, detail);
        const prev = attempts.length > 0 ? attempts[0] : null;

        let transitionBadge = '<span style="font-size:0.7rem; color: var(--text-secondary);">비교 데이터 없음</span>';
        if (prev) {
            const prevIsCorrect = isCorrectByAnswer(prev.user_answer, correctAnswer);
            const sameChoice = isExactAnswerMatch(prev.user_answer, currentAnswer);

            if (!prevIsCorrect && !currentIsCorrect && sameChoice) {
                transitionBadge = '<span style="font-size:0.7rem; color:#f87171; font-weight:700;">동일 오답 반복</span>';
            } else if (!prevIsCorrect && !currentIsCorrect && !sameChoice) {
                transitionBadge = '<span style="font-size:0.7rem; color:#f59e0b; font-weight:700;">오답 이동</span>';
            } else if (!prevIsCorrect && currentIsCorrect) {
                transitionBadge = '<span style="font-size:0.7rem; color:#34d399; font-weight:700;">정답 전환</span>';
            } else if (prevIsCorrect && currentIsCorrect) {
                transitionBadge = '<span style="font-size:0.7rem; color:#60a5fa; font-weight:700;">정답 유지</span>';
            }
        }

        const timelineHtml = attempts.slice(0, 3).map((a, idx) => {
            const dateText = formatKoreanDate(a.created_at);
            const answerText = answerArrayToText(a.user_answer);
            const mark = a.is_correct ? '정답' : '오답';
            const markColor = a.is_correct ? '#34d399' : '#f87171';
            return `
                <div style="display:flex; align-items:center; justify-content:space-between; gap:0.6rem; background: rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:0.45rem 0.55rem;">
                    <span style="font-size:0.72rem; color: var(--text-secondary);">${idx + 1}회 전 · ${a.source}</span>
                    <span style="font-size:0.72rem; color: var(--text-primary);">선택: ${answerText}</span>
                    <span style="font-size:0.7rem; color:${markColor}; font-weight:700;">${mark}</span>
                    <span style="font-size:0.68rem; color: var(--text-muted);">${dateText}</span>
                </div>
            `;
        }).join('');

        container.innerHTML = `
            <div style="border:1px solid rgba(56,189,248,0.28); background: rgba(56,189,248,0.08); border-radius:10px; padding:0.7rem;">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.45rem; gap:0.8rem;">
                    <div style="font-size:0.78rem; font-weight:700; color:#38bdf8;">${detail.question_num}번 문항 답안 변화 비교</div>
                    ${transitionBadge}
                </div>
                <div style="display:flex; gap:1rem; flex-wrap:wrap; font-size:0.74rem; margin-bottom:0.55rem;">
                    <span style="color: var(--text-secondary);">이번 답: <strong style="color:#f87171;">${answerArrayToText(currentAnswer)}</strong></span>
                    <span style="color: var(--text-secondary);">정답: <strong style="color:#34d399;">${answerArrayToText(correctAnswer)}</strong></span>
                    <span style="color: var(--text-secondary);">직전 답: <strong style="color: var(--text-primary);">${prev ? answerArrayToText(prev.user_answer) : '기록 없음'}</strong></span>
                </div>
                <div style="font-size:0.72rem; color: var(--text-secondary); margin-bottom:0.35rem;">최근 선택 이력 (최대 3회)</div>
                <div style="display:flex; flex-direction:column; gap:0.35rem;">
                    ${timelineHtml || '<div style="font-size:0.72rem; color: var(--text-muted);">과거 선택 이력이 없습니다.</div>'}
                </div>
            </div>
        `;
    } catch (err) {
        container.innerHTML = `<div style="font-size:0.76rem; color:#f87171;">답안 변화 비교 정보를 불러오지 못했습니다: ${err.message}</div>`;
    }
}

async function showYearlyWrongQuestionDetail(item, detail) {
    const container = document.getElementById('yearly-wrong-detail-box');
    if (!container) return;

    const qNum = detail.question_num;
    container.innerHTML = `<div style="font-size:0.82rem; color: var(--text-secondary);">${qNum}번 문제 지문을 불러오는 중...</div>`;
    const neutralBorder = HistoryState.theme === 'light'
        ? '1px solid rgba(15,23,42,0.14)'
        : '1px solid rgba(255,255,255,0.08)';
    const neutralBg = HistoryState.theme === 'light'
        ? 'rgba(15,23,42,0.03)'
        : 'rgba(255,255,255,0.02)';

    try {
        const questionData = await fetchYearlyQuestionData(item, detail);

        const options = Array.isArray(questionData.options) ? questionData.options : [];
        const answerArr = Array.isArray(questionData.answer) ? questionData.answer : [];
        const userAnswerArr = Array.isArray(detail.user_answer) ? detail.user_answer : [];

        const optionHtml = options.map((opt, idx) => {
            const optNo = idx + 1;
            const isCorrect = answerArr.includes(optNo);
            const isUser = userAnswerArr.includes(optNo);
            const border = isCorrect ? '1px solid rgba(16,185,129,0.5)' : (isUser ? '1px solid rgba(239,68,68,0.45)' : neutralBorder);
            const bg = isCorrect ? 'rgba(16,185,129,0.10)' : (isUser ? 'rgba(239,68,68,0.08)' : neutralBg);
            const marker = isCorrect ? '✅ 정답' : (isUser ? '❌ 선택' : '');

            return `
                <div style="padding: 0.45rem 0.6rem; border-radius: 8px; border: ${border}; background: ${bg}; display:flex; justify-content:space-between; gap:0.6rem;">
                    <span style="font-size:0.8rem; color: var(--text-primary);">${optNo}. ${opt}</span>
                    <span style="font-size:0.72rem; color: var(--text-secondary); white-space:nowrap;">${marker}</span>
                </div>
            `;
        }).join('');

        const correctStr = answerArr.length > 0 ? answerArr.join(', ') : '-';
        const userStr = userAnswerArr.length > 0 ? userAnswerArr.join(', ') : '미선택';

        container.innerHTML = `
            <div style="border:1px solid rgba(59,130,246,0.28); background: rgba(59,130,246,0.08); border-radius: 10px; padding: 0.8rem; margin-bottom: 0.9rem;">
                <div style="font-size:0.82rem; font-weight:700; color:#60a5fa; margin-bottom:0.45rem;">📌 선택 문항 상세: ${qNum}번</div>
                <div style="font-size:0.84rem; color: var(--text-primary); line-height:1.55; white-space: pre-wrap; margin-bottom:0.7rem;">${questionData.question || '지문 정보 없음'}</div>
                <div style="display:flex; gap:1rem; font-size:0.78rem; margin-bottom:0.55rem;">
                    <span style="color: var(--text-secondary);">내 답: <strong style="color:#f87171;">${userStr}</strong></span>
                    <span style="color: var(--text-secondary);">정답: <strong style="color:#34d399;">${correctStr}</strong></span>
                </div>
                <div style="display:flex; flex-direction:column; gap:0.4rem;">${optionHtml}</div>
                ${questionData.explanation ? `
                <div class="explanation-toggle-container" style="margin-top: 0.7rem;">
                    <button type="button" class="explanation-toggle-btn" onclick="toggleExplanationCollapse(this)" style="background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.3); color: #c084fc; padding: 0.35rem 0.8rem; border-radius: 6px; font-size: 0.76rem; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 0.3rem; outline: none; transition: all 0.2s;">
                        <span>💡 해설보기</span>
                    </button>
                    <div class="explanation-box" style="display: none; margin-top: 0.5rem; font-size: 0.78rem; color: var(--text-secondary); line-height: 1.5;">
                        <strong style="color: var(--text-primary);">해설</strong><br>${questionData.explanation}
                    </div>
                </div>
                ` : ''}
            </div>
        `;
    } catch (err) {
        container.innerHTML = `<div style="font-size:0.8rem; color:#f87171;">오답 문항 상세를 불러오지 못했습니다: ${err.message}</div>`;
    }
}

/**
 * 년도별 모의고사 날짜 일시 포맷팅 헬퍼
 */
function formatYearlyKoreanDateTime(dateStr) {
    if (!dateStr) return '';
    const d = parseDate(dateStr);
    const yy = String(d.getFullYear()).slice(-2);
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${yy}.${mm}.${dd} ${hh}:${min}`;
}

/**
 * 초(seconds)를 한국어 시간 형태 문자열로 포맷팅
 */
function formatSecondsToKorean(totalSeconds) {
    if (!totalSeconds) return '0초';
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;

    let result = [];
    if (h > 0) result.push(`${h}시간`);
    if (m > 0) result.push(`${m}분`);
    if (s > 0 || result.length === 0) result.push(`${s}초`);

    return result.join(' ');
}

/**
 * [설계 의도] 년도별 모의고사 상세 분석 모달 오픈
 */
function openYearlyModal(item) {
    try {
        // 상세 리포트 데이터 임시 저장
        localStorage.setItem('selected_history_item', JSON.stringify(item));
        // 비교 분석용 전체 연습 이력 목록 전달
        if (HistoryState && HistoryState.yearlyExamHistory) {
            localStorage.setItem('selected_history_list', JSON.stringify(HistoryState.yearlyExamHistory));
        }
        // OMR 클릭 시 대시보드(일반 퀴즈) 이력까지 함께 비교할 수 있도록 전달
        if (HistoryState && Array.isArray(HistoryState.allLogs)) {
            localStorage.setItem('selected_quiz_logs', JSON.stringify(HistoryState.allLogs));
        }
        // 독립된 html 팝업창을 가로 1200, 세로 850 크기의 새 창으로 띄우기
        const width = 1200;
        const height = 850;
        const left = (window.screen.width - width) / 2;
        const top = (window.screen.height - height) / 2;
        window.open('../exam_mock/yearly_result.html?from_history=true', `history_detail_popup_${item.id || Date.now()}`, `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`);
    } catch (e) {
        console.error("Yearly modal redirect failed:", e);
    }
}

/**
 * 해설 영역 접기/펼치기 토글 헬퍼 함수
 */
window.toggleExplanationCollapse = function (btn) {
    const box = btn.nextElementSibling;
    if (!box) return;
    const isHidden = box.style.display === 'none';
    if (isHidden) {
        box.style.display = 'block';
        btn.querySelector('span').textContent = '💡 해설접기';
        btn.style.background = 'rgba(239, 68, 68, 0.12)';
        btn.style.borderColor = 'rgba(239, 68, 68, 0.25)';
        btn.style.color = '#fca5a5';
    } else {
        box.style.display = 'none';
        btn.querySelector('span').textContent = '💡 해설보기';
        btn.style.background = 'rgba(139, 92, 246, 0.15)';
        btn.style.borderColor = 'rgba(139, 92, 246, 0.3)';
        btn.style.color = '#c084fc';
    }
};

/**
 * 년도별 모의고사 페이징 UI 상태 업데이트
 */
function updateYearlyPagination(totalPages) {
    const prevBtn = document.getElementById('btn-prev-yearly-page');
    const nextBtn = document.getElementById('btn-next-yearly-page');
    const pageInfo = document.getElementById('yearly-page-info');

    if (!prevBtn || !nextBtn || !pageInfo) return;

    if (totalPages <= 0) {
        pageInfo.textContent = '0 / 0';
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        return;
    }

    pageInfo.textContent = `${HistoryState.yearlyCurrentPage} / ${totalPages}`;
    prevBtn.disabled = (HistoryState.yearlyCurrentPage === 1);
    nextBtn.disabled = (HistoryState.yearlyCurrentPage === totalPages);
}

/**
 * 년도별 모의고사 이전 페이지 이동
 */
function prevYearlyPage() {
    if (HistoryState.yearlyCurrentPage > 1) {
        HistoryState.yearlyCurrentPage--;
        renderYearlyExamHistoryTable(HistoryState.yearlyExamHistory);
    }
}

/**
 * 년도별 모의고사 다음 페이지 이동
 */
function nextYearlyPage() {
    if (HistoryState.yearlyCurrentPage < HistoryState.yearlyTotalPages) {
        HistoryState.yearlyCurrentPage++;
        renderYearlyExamHistoryTable(HistoryState.yearlyExamHistory);
    }
}

// 전역 스코프 노출
window.prevYearlyPage = prevYearlyPage;
window.nextYearlyPage = nextYearlyPage;
