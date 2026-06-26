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
    charts: {}           // 차트 객체 버퍼 (인스턴스 소멸용)
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

    Promise.all([Promise.all(fetchPromises), expPromise])
        .then(([results, expData]) => {
            const merged = [];

            results.forEach((data, index) => {
                const sub = subjects[index];
                const sLogs = data.logs || [];
                sLogs.forEach(log => {
                    merged.push({
                        ...log,
                        subject: sub,
                        parsedDate: parseDate(log.created_at)
                    });
                });
            });

            // 시간 최신순 정렬
            merged.sort((a, b) => b.parsedDate - a.parsedDate);
            HistoryState.allLogs = merged;

            // 과목별 레벨/경험치 카드 UI 렌더링
            renderSubjectExpCards(expData);

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
    document.getElementById('stat-active-days-sub').textContent = streak > 0 ? `🔥 현재 ${streak}일 연속 학습 중!` : '매일 꾸준히 잔디를 채워보세요.';
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

        tr.innerHTML = `
            <td>${dateFormatted}</td>
            <td><strong>${row.totalSolved}개</strong></td>
            <td>${acc}%</td>
            <td>${timeStr}</td>
        `;

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
function renderSubjectExpCards(expData) {
    const container = document.getElementById('subject-exp-grid');
    if (!container) return;

    container.innerHTML = '';
    const subjects = ['DB', 'SE', 'PM', 'SA', 'SC'];
    
    // 각 과목 대시보드와 동일한 캐릭터 펫 할당
    const POKEMON_PETS = {
        'DB': { name: '꼬부기', src: '/reports/images_game/squirtle_cheer.png' },
        'SE': { name: '피카츄', src: '/reports/images_game/pikachuRun.gif' },
        'PM': { name: '파이리', src: '/reports/images_game/charmander_cheer.png' },
        'SA': { name: '로토무', src: '/reports/images_game/rotom_architect.png' }, // 시스템구조 과목 전용 캐릭터 매핑
        'SC': { name: '가디 보안관', src: '/reports/images_game/growlithe_security.png' } // 보안 과목 전용 캐릭터 매핑
    };

    const subExps = expData.subjects_exp || {};

    subjects.forEach(sub => {
        const subData = subExps[sub] || { total_exp: 0, level: 1, exp_in_level: 0, exp_to_next: 10 };
        const pet = POKEMON_PETS[sub] || { name: '피카츄', src: '/reports/images_game/pikachuRun.gif' };
        
        const card = document.createElement('div');
        card.className = 'subject-exp-card';
        
        // 경험치바 백분율 계산
        const expPercent = (subData.exp_in_level / 10) * 100;
        const nextLevelExp = subData.level * 10;
        
        card.innerHTML = `
            <div class="sub-exp-header">
                <span class="sub-exp-title">${SUBJECT_NAMES[sub]}</span>
                <span class="sub-exp-badge">${sub}</span>
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
                    <span>${subData.total_exp} EXP</span>
                    <span>${subData.exp_in_level} / 10 EXP</span>
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
