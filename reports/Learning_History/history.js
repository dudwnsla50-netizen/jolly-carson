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
    pageSize: 30,        // 페이징 당 행 개수
    charts: {},          // 차트 객체 버퍼 (인스턴스 소멸용)
    analyticsData: null, // [NEW] AI 중단원 분석 데이터 버퍼
    currentSubject: 'DB' // [NEW] 현재 활성화된 분석 탭 과목
};

const SUBJECT_NAMES = {
    'DB': '데이터베이스',
    'SE': '소프트웨어공학',
    'PM': '사업관리',
    'SA': '시스템구조',
    'SC': '보안'
};

document.addEventListener('DOMContentLoaded', () => {
    loadAllHistoryData();
    updateTabTitleWithDbMode();
});

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
    const fetchPromises = subjects.map(sub => {
        return fetch(`/api/quiz/stats?subject=${sub}`)
            .then(res => res.ok ? res.json() : { logs: [] })
            .catch(() => ({ logs: [] }));
    });

    // [설계 의도]
    // 과목별 학습 현황 통계 데이터와 게이미피케이션 경험치 데이터를 병합 호출하여
    // 학습 이력 분석 센터 화면에 유기적으로 연동하고, 한 번의 로딩으로 모든 정보를 노출시킵니다.
    const expPromise = fetch('/api/quiz/total-exp')
        .then(res => res.ok ? res.json() : { total_exp: 0, level: 1, exp_in_level: 0, subjects_exp: {} })
        .catch(() => ({ total_exp: 0, level: 1, exp_in_level: 0, subjects_exp: {} }));

    const yearlyExamPromise = fetch('/api/yearly-exam/history')
        .then(res => res.ok ? res.json() : [])
        .catch(() => []);

    Promise.all([Promise.all(fetchPromises), expPromise, yearlyExamPromise])
        .then(([results, expData, yearlyHistory]) => {
            const merged = [];
            const subjectAccuracies = {};

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
                borderColor: '#8b5cf6',
                borderWidth: 2,
                backgroundColor: 'rgba(139, 92, 246, 0.08)',
                fill: true,
                tension: 0.35,
                pointBackgroundColor: '#8b5cf6',
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
                    ticks: { color: '#64748b', font: { size: 9 } }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: { color: '#64748b', font: { size: 9 }, stepSize: 5 }
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
                        color: '#94a3b8',
                        font: { size: 10 },
                        boxWidth: 10,
                        padding: 10
                    }
                }
            },
            cutout: '60%'
        }
    });
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

        // 비동기적으로 해당 날짜의 오답분석 파일이 존재하는지 검증 (HEAD 요청으로 리소스 낭비 최소화)
        fetch(reportUrl, { method: 'HEAD' })
            .then(res => {
                if (res.ok) {
                    const cell = document.getElementById(reportCellId);
                    if (cell) {
                        cell.innerHTML = `<a href="${reportUrl}" target="_blank" class="back-btn" style="padding: 0.25rem 0.6rem; font-size: 0.72rem; margin: 0; background: rgba(139, 92, 246, 0.15); border-color: rgba(139, 92, 246, 0.3); color: #a78bfa; text-decoration: none;" onclick="event.stopPropagation();">리포트 보기 🔍</a>`;
                    }
                }
            })
            .catch(() => {});

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
            <span style="font-weight: 600; color: #ffffff;">${count}개 문항 풀이</span>
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

/**
 * [설계 의도] 년도별 120제 모의고사 연습 이력 테이블을 동적으로 렌더링합니다.
 */
function renderYearlyExamHistoryTable(historyList) {
    const tbody = document.getElementById('yearly-history-tbody');
    if (!tbody) return;

    if (!historyList || historyList.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2.5rem; font-size: 0.9rem;">
                    📢 아직 완료된 년도별 모의고사 연습 이력이 없습니다.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = '';
    historyList.forEach(item => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.title = '클릭하면 상세 채점 분석 및 문항별 풀이 시간 리포트 팝업이 열립니다.';
        tr.onclick = () => openYearlyModal(item);
        
        // 날짜 변환
        const formattedDate = formatYearlyKoreanDateTime(item.created_at);
        const score = item.score !== undefined ? parseFloat(item.score).toFixed(1) : '0.0';
        
        // 시간 가독성 개선
        const timeStr = formatSecondsToKorean(item.total_time);

        tr.innerHTML = `
            <td style="font-size: 0.85rem; color: var(--text-secondary);">${formattedDate}</td>
            <td style="font-family: 'Outfit', sans-serif; font-weight: 700; color: #ffffff; font-size: 0.9rem;">${item.exam_year}년도 기출</td>
            <td><span class="badge" style="background: rgba(139, 92, 246, 0.12); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.2); font-size: 0.72rem; padding: 0.2rem 0.5rem; border-radius: 6px; font-weight: 600;">${item.practice_count}회차</span></td>
            <td style="font-size: 0.88rem; font-weight: 500;">${item.correct_count} / ${item.total_questions}</td>
            <td style="font-size: 0.85rem; color: var(--text-secondary);">${timeStr}</td>
            <td style="font-weight: 700; color: var(--success); font-size: 0.95rem;">${score}점</td>
        `;
        tbody.appendChild(tr);
    });

    if (window.lucide) {
        lucide.createIcons();
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
 * [설계 의도] 년도별 모의고사 상세 분석 모달 오픈 및 취약 과목 진단, 장시간 소요 문항 Top 3, OMR 시간 그리드 시각화
 */
function openYearlyModal(item) {
    const modal = document.getElementById('yearly-detail-modal');
    const body = document.getElementById('yearly-modal-body');
    if (!modal || !body) return;

    // details 파싱
    let details = [];
    try {
        details = (typeof item.details === 'string') 
            ? JSON.parse(item.details) 
            : (item.details || []);
    } catch (e) {
        console.error("details 파싱 에러:", e);
    }

    // 1. 과목별 통계 및 풀이 시간 집계
    const SUBJECTS = {
        'PM': { name: '감리 및 사업관리', range: [1, 25] },
        'SE': { name: '소프트웨어공학', range: [26, 50] },
        'DB': { name: '데이터베이스', range: [51, 75] },
        'SA': { name: '시스템 아키텍처', range: [76, 100] },
        'SC': { name: '보안', range: [101, 120] }
    };

    const subStats = {};
    for (let code in SUBJECTS) {
        subStats[code] = { correct: 0, total: 0, timeSum: 0 };
    }

    details.forEach(d => {
        const qNum = d.question_num;
        let subCode = null;
        for (let code in SUBJECTS) {
            const range = SUBJECTS[code].range;
            if (qNum >= range[0] && qNum <= range[1]) {
                subCode = code;
                break;
            }
        }
        if (subCode && subStats[subCode]) {
            subStats[subCode].total++;
            subStats[subCode].timeSum += (d.elapsed_time || 0);
            if (d.is_correct) {
                subStats[subCode].correct++;
            }
        }
    });

    // 2. 가장 오래 고민한 문항 Top 3 (시간 정렬)
    const sortedByTime = [...details].sort((a, b) => (b.elapsed_time || 0) - (a.elapsed_time || 0));
    const top3 = sortedByTime.slice(0, 3);

    // 3. 과목별 분석 카드 HTML 작성
    let subCardsHtml = '';
    let weaknessAlertHtml = '';
    for (let code in subStats) {
        const stat = subStats[code];
        if (stat.total === 0) continue; // 해당 과목 풀이 데이터가 없으면 패스

        const pct = Math.round((stat.correct / stat.total) * 100);
        const avgTime = Math.round(stat.timeSum / stat.total);
        const isLow = pct < 60;
        
        if (isLow) {
            weaknessAlertHtml += `
                <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; padding: 0.6rem 1rem; font-size: 0.8rem; color: #f87171; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.4rem;">
                    <i data-lucide="alert-triangle" style="width: 14px; height: 14px; flex-shrink: 0;"></i>
                    <span><strong>${SUBJECTS[code].name}</strong> 과목의 정답률이 <strong>${pct}%</strong>로 취약 상태입니다. 핵심 개념 요약 회독을 추천합니다.</span>
                </div>
            `;
        }

        subCardsHtml += `
            <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 1rem; text-align: center;">
                <div style="font-size: 0.78rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.4rem;">${SUBJECTS[code].name}</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: #ffffff; margin-bottom: 0.2rem;">${stat.correct} / ${stat.total}문항</div>
                <div style="font-size: 0.88rem; font-weight: 700; color: ${isLow ? 'var(--error)' : 'var(--success)'}; margin-bottom: 0.4rem;">정답률: ${pct}%</div>
                <div style="font-size: 0.72rem; color: var(--text-muted);">문항당 평균: ${avgTime}초</div>
            </div>
        `;
    }

    // 4. Top 3 문항 리스트 HTML
    let top3Html = '';
    top3.forEach((d, idx) => {
        let subName = '';
        for (let code in SUBJECTS) {
            const range = SUBJECTS[code].range;
            if (d.question_num >= range[0] && d.question_num <= range[1]) {
                subName = SUBJECTS[code].name;
                break;
            }
        }
        const timeStr = formatSecondsToKorean(d.elapsed_time);
        const stBadge = d.is_correct 
            ? '<span style="color: var(--success); font-weight: 600;">정답</span>' 
            : '<span style="color: var(--error); font-weight: 600;">오답</span>';

        top3Html += `
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.04); border-radius: 8px; padding: 0.6rem 1rem; font-size: 0.82rem;">
                <div style="display: flex; align-items: center; gap: 0.6rem;">
                    <span style="background: rgba(139, 92, 246, 0.15); color: #c084fc; font-weight: 700; padding: 0.2rem 0.5rem; border-radius: 4px; font-family: monospace;">Top ${idx+1}</span>
                    <span style="font-weight: 600; color: #ffffff;">${d.question_num}번 문제</span>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">[${subName}]</span>
                </div>
                <div style="display: flex; gap: 1rem; align-items: center;">
                    <span style="color: var(--text-secondary); font-family: monospace;">소요 시간: ${timeStr}</span>
                    <span>${stBadge}</span>
                </div>
            </div>
        `;
    });

    // 5. 전체 OMR 바둑판 그리드 HTML
    let gridHtml = '';
    details.forEach(d => {
        const isCorrect = d.is_correct;
        const color = isCorrect ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)';
        const borderColor = isCorrect ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)';
        const txtColor = isCorrect ? '#34d399' : '#f87171';
        const timeStr = d.elapsed_time ? `${d.elapsed_time}초` : '0초';

        gridHtml += `
            <div style="background: ${color}; border: 1px solid ${borderColor}; border-radius: 8px; padding: 0.4rem 0.2rem; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.15rem; min-height: 48px;">
                <span style="font-size: 0.72rem; color: var(--text-secondary); font-family: monospace; font-weight: 600;">Q.${d.question_num}</span>
                <span style="font-size: 0.78rem; font-weight: 700; color: ${txtColor};">${isCorrect ? 'O' : 'X'}</span>
                <span style="font-size: 0.65rem; color: var(--text-muted); font-family: monospace;">${timeStr}</span>
            </div>
        `;
    });

    // 6. 모달 바디 렌더링 조립
    const formattedTotalTime = formatSecondsToKorean(item.total_time);
    body.innerHTML = `
        <!-- 요약 정보 바 -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; background: rgba(139, 92, 246, 0.05); border: 1px solid rgba(139, 92, 246, 0.15); border-radius: 12px; padding: 1rem; text-align: center;">
            <div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.25rem;">시험 구분</div>
                <div style="font-size: 0.95rem; font-weight: 700; color: #ffffff;">${item.exam_year}년도 기출</div>
            </div>
            <div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.25rem;">최종 점수</div>
                <div style="font-size: 0.95rem; font-weight: 700; color: var(--success);">${parseFloat(item.score).toFixed(1)}점</div>
            </div>
            <div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.25rem;">정답 현황</div>
                <div style="font-size: 0.95rem; font-weight: 700; color: #ffffff;">${item.correct_count} / ${item.total_questions}문항</div>
            </div>
            <div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.25rem;">총 소요 시간</div>
                <div style="font-size: 0.95rem; font-weight: 700; color: #ffffff; font-family: monospace;">${formattedTotalTime}</div>
            </div>
        </div>

        <!-- 팝업 인사이트 영역 1: 과목별 분석 -->
        <div style="margin-bottom: 1.5rem;">
            <h3 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.3rem; color: #c084fc;">
                <i data-lucide="bar-chart-2" style="width: 16px; height: 16px;"></i> 과목별 취약 도메인 및 시간 정밀 분석
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.8rem; margin-bottom: 0.8rem;">
                ${subCardsHtml}
            </div>
            ${weaknessAlertHtml}
        </div>

        <!-- 팝업 인사이트 영역 2: 가장 오래 고민한 문제 Top 3 -->
        <div style="margin-bottom: 1.5rem;">
            <h3 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.3rem; color: #3b82f6;">
                <i data-lucide="timer" style="width: 16px; height: 16px;"></i> 가장 오래 고민한 문항 Top 3 (시간 초과 주의군)
            </h3>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                ${top3Html}
            </div>
        </div>

        <!-- 팝업 인사이트 영역 3: OMR 바둑판 보드 -->
        <div>
            <h3 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.3rem; color: var(--text-primary);">
                <i data-lucide="grid" style="width: 16px; height: 16px;"></i> 전체 문항 반응 및 풀이 소요 시간 보드 (바둑판)
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(68px, 1fr)); gap: 0.4rem;">
                ${gridHtml}
            </div>
        </div>
    `;

    modal.style.display = 'flex';
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * 모달 클로즈
 */
function closeYearlyModal(event) {
    const modal = document.getElementById('yearly-detail-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}
