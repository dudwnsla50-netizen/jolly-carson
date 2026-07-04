// 과목 메타데이터 정의
const SUBJECTS = {
    'PM': { name: '감리 및 사업관리', range: [1, 25] },
    'SE': { name: '소프트웨어공학', range: [26, 50] },
    'DB': { name: '데이터베이스', range: [51, 75] },
    'SA': { name: '시스템 아키텍처', range: [76, 100] },
    'SC': { name: '보안', range: [101, 120] }
};

// 과목 범위 슬라이싱 옵션
const SUBJECT_RANGES = {
    'ALL': { name: '전체 (120문항)', range: [1, 120] },
    'PM': { name: '감리 및 사업관리 (25문항)', range: [1, 25] },
    'SE': { name: '소프트웨어공학 (25문항)', range: [26, 50] },
    'DB': { name: '데이터베이스 (25문항)', range: [51, 75] },
    'SA': { name: '시스템 아키텍처 (25문항)', range: [76, 100] },
    'SC': { name: '보안 (20문항)', range: [101, 120] },
    'NEW_TREND_ALL': { name: '신규 기출 전체', range: [1, 120] },
    'NEW_TREND_PM': { name: '신규 기출 감리 및 사업관리', range: [1, 25] },
    'NEW_TREND_SE': { name: '신규 기출 소프트웨어공학', range: [26, 50] },
    'NEW_TREND_DB': { name: '신규 기출 데이터베이스', range: [51, 75] },
    'NEW_TREND_SA': { name: '신규 기출 시스템 아키텍처', range: [76, 100] },
    'NEW_TREND_SC': { name: '신규 기출 보안', range: [101, 120] }
};

// 전역 상태 변수
let examYear = null;
let selectedSubjectRange = 'ALL'; // 선택된 과목 필터 키
let questions = [];          // 로드된 문제 목록
let currentIdx = 0;          // 현재 표시 중인 문제 인덱스
let userAnswers = {};        // 유저 마킹 정보 { question_num: selected_option_number(1~4) }
let isImageExpanded = false; // [NEW] 문제 이미지 펼치기 상태 변수

// 타이머 변수
let totalTimerInterval = null;
let totalSeconds = 0;
let qTimerInterval = null;
let qSeconds = [];           // 문항별 풀이 소요 시간 (초 단위 배열)

// 로컬스토리지 백업 키 및 미동기화 보류 리스트 키
const BACKUP_KEY = 'jolly_carson_yearly_exam_backup';
const PENDING_KEY = 'jolly_carson_pending_submits';
const THEME_STORAGE_KEY = 'jc_theme';

function applyYearlyTheme(theme) {
    const normalized = theme === 'light' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', normalized);
}

function initYearlyTheme() {
    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    if (savedTheme === 'light' || savedTheme === 'dark') {
        applyYearlyTheme(savedTheme);
        return;
    }

    // 메인 화면 선택 이력이 없는 경우 안전 기본값
    applyYearlyTheme('dark');
}

// 도큐먼트 로드 완료 시 구동 (독립 페이지별 분기 라우터)
document.addEventListener('DOMContentLoaded', () => {
    initYearlyTheme();
    initLucide();

    // 로컬 파일 프로토콜과 서버에 따른 홈 링크 대응
    const homeLink = document.getElementById('home-link');
    if (homeLink) {
        if (window.location.protocol === 'file:') {
            homeLink.href = '../db_official_scopes.html';
        } else {
            homeLink.href = '/reports/db_official_scopes.html';
        }
    }

    const path = window.location.pathname;
    if (path.includes('yearly_practice.html')) {
        initPracticePage();
    } else if (path.includes('yearly_result.html')) {
        initResultPage();
    } else {
        initSelectionPage();
    }
});

function initLucide() {
    if (window.lucide) {
        lucide.createIcons();
    }
}

// [NEW] 기출 원본 크롭 이미지 접기/펼치기 제어 함수
function toggleQuestionImage() {
    const imgContainer = document.getElementById('question-img-container');
    const btn = document.getElementById('toggle-img-btn');
    if (!imgContainer || !btn) return;

    isImageExpanded = !isImageExpanded;
    if (isImageExpanded) {
        imgContainer.style.display = 'flex';
        btn.innerHTML = `<i data-lucide="image-off" style="width: 15px; height: 15px;"></i> 기출 원본 이미지 접기 (접기)`;
    } else {
        imgContainer.style.display = 'none';
        btn.innerHTML = `<i data-lucide="image" style="width: 15px; height: 15px;"></i> 기출 원본 이미지 펼치기 (펼치기)`;
    }
    initLucide();
}

// 미동기화 대기열 감지 및 UI 배너 제어
function checkPendingSubmits() {
    const pending = localStorage.getItem(PENDING_KEY);
    const banner = document.getElementById('sync-banner-element');
    const countBadge = document.getElementById('pending-sync-count');

    if (pending) {
        try {
            const list = JSON.parse(pending);
            if (list.length > 0) {
                countBadge.innerText = list.length;
                banner.style.display = 'flex';
                return;
            }
        } catch (e) {
            localStorage.removeItem(PENDING_KEY);
        }
    }
    banner.style.display = 'none';
}

// 백업 세션 확인 및 초기화
function checkBackupAndInit() {
    const backupData = localStorage.getItem(BACKUP_KEY);
    if (backupData) {
        try {
            const backup = JSON.parse(backupData);
            let scopeText = SUBJECT_RANGES[backup.selectedSubjectRange || 'ALL'].name;
            if (confirm(`${backup.examYear}년도 [ ${scopeText} ] 시험을 풀던 기록이 있습니다. 이어서 푸시겠습니까?`)) {
                window.location.href = 'yearly_practice.html';
                return;
            } else {
                localStorage.removeItem(BACKUP_KEY);
            }
        } catch (e) {
            console.error("백업 파싱 에러:", e);
            localStorage.removeItem(BACKUP_KEY);
        }
    }
    loadYearlyExams();
}

/**
 * [신설] 3대 스크린별 독립 로드 초기화 함수군
 */
function initSelectionPage() {
    checkBackupAndInit();
}

function initPracticePage() {
    // 1. 임시 OMR 백업 존재 시 즉각 복원
    const backupData = localStorage.getItem(BACKUP_KEY);
    if (backupData) {
        try {
            const backup = JSON.parse(backupData);
            restoreBackup(backup);
            return;
        } catch (e) {
            console.error("백업 복원 에러:", e);
            localStorage.removeItem(BACKUP_KEY);
        }
    }

    // 2. 세션 선택 값 기반으로 실시간 시험 시작
    const year = localStorage.getItem('session_exam_year');
    const isNewTrend = localStorage.getItem('session_is_new_trend') === 'true';
    const trendSubject = localStorage.getItem('session_trend_subject') || 'ALL';

    if (!year) {
        alert("선택된 시험 정보가 없습니다. 연도 선택 화면으로 이동합니다.");
        window.location.href = 'yearly_exam.html';
        return;
    }

    startYearlyExam(year, isNewTrend, trendSubject);
}

function initResultPage() {
    const rawResult = localStorage.getItem('session_result_data');
    if (!rawResult) {
        alert("분석 결과가 존재하지 않습니다. 연도 선택 화면으로 이동합니다.");
        window.location.href = 'yearly_exam.html';
        return;
    }

    try {
        const result = JSON.parse(rawResult);
        renderResultReport(result.payload, result.practice_count);
    } catch (e) {
        console.error("결과 복원 에러:", e);
        alert("결과 상세 분석 데이터를 로드하는 중 오류가 발생했습니다.");
        window.location.href = 'yearly_exam.html';
    }
}

// 연도 목록 API 로드
function loadYearlyExams() {
    showScreen('loading-screen');
    checkPendingSubmits();

    fetch('/api/yearly-exams')
        .then(res => {
            if (!res.ok) throw new Error("API error");
            return res.json();
        })
        .then(data => {
            renderYearSelection(data);
            showScreen('selection-view');
        })
        .catch(err => {
            console.error("연도 목록 가져오기 실패, 폴백 목록 로딩:", err);
            const fallbackData = Array.from({ length: 12 }, (_, i) => ({
                year: 2026 - i,
                question_count: 120,
                max_score: 0.0,
                practice_count: 0,
                last_attempt_at: null
            }));
            renderYearSelection(fallbackData);
            showScreen('selection-view');
        });
}

// 연도 선택 뷰 렌더링
function renderYearSelection(data) {
    const container = document.getElementById('exam-card-container');
    container.innerHTML = '';

    data.forEach(item => {
        const card = document.createElement('div');
        card.className = 'exam-card';

        const lastAttempt = item.last_attempt_at
            ? formatDate(item.last_attempt_at)
            : '이력 없음';
        const maxScore = item.max_score !== undefined ? parseFloat(item.max_score).toFixed(0) : '0';

        // 과목별 최고점 연산
        const pmMax = item.subject_max_scores ? parseFloat(item.subject_max_scores.PM).toFixed(0) : '0';
        const seMax = item.subject_max_scores ? parseFloat(item.subject_max_scores.SE).toFixed(0) : '0';
        const dbMax = item.subject_max_scores ? parseFloat(item.subject_max_scores.DB).toFixed(0) : '0';
        const saMax = item.subject_max_scores ? parseFloat(item.subject_max_scores.SA).toFixed(0) : '0';
        const scMax = item.subject_max_scores ? parseFloat(item.subject_max_scores.SC).toFixed(0) : '0';

        // 신규 기출 문항 수 계산
        const pmTrend = item.new_trends ? item.new_trends.subjects.PM.count : 0;
        const seTrend = item.new_trends ? item.new_trends.subjects.SE.count : 0;
        const dbTrend = item.new_trends ? item.new_trends.subjects.DB.count : 0;
        const saTrend = item.new_trends ? item.new_trends.subjects.SA.count : 0;
        const scTrend = item.new_trends ? item.new_trends.subjects.SC.count : 0;
        const totalTrend = item.new_trends ? item.new_trends.total_count : 0;

        card.innerHTML = `
                    <div class="exam-card-header">
                        <span class="exam-year-title">${item.year}년도</span>
                        <span class="exam-badge">${item.question_count}문항 완비</span>
                    </div>
                    <div class="exam-stats">
                        <!-- 과목별 최고 점수 & 신규 비중 통합 격자 패널 -->
                        <div style="margin-top: 0.2rem; margin-bottom: 0.8rem; background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 0.5rem 0.6rem;">
                            <div style="font-size: 0.7rem; color: var(--text-secondary); font-weight: 600; margin-bottom: 0.35rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.2rem; display: flex; justify-content: space-between;">
                                <span>과목별 최고점</span>
                                <span style="color: var(--success); font-weight: 700; cursor: pointer; text-decoration: underline;" onclick="event.stopPropagation(); startYearlyExam(${item.year}, true, 'ALL')" title="클릭 시 전체 신규 기출 모의고사 풀기 시작">종합 최고: ${maxScore}점, <span style="color: var(--success);">신규: ${totalTrend}개</span></span>
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.25rem; text-align: center;">
                                <div style="display:flex; flex-direction:column; gap:0.1rem;">
                                    <span style="font-size:0.62rem; color:#f472b6; font-weight:700;">PM</span>
                                    <span style="font-size:0.74rem; font-weight:700; color:var(--text-primary);">${pmMax}</span>
                                    <span style="font-size:0.58rem; color:#f472b6; font-weight:600; text-decoration:underline; cursor:pointer; margin-top:2px;" onclick="event.stopPropagation(); startYearlyExam(${item.year}, true, 'PM')" title="클릭 시 PM 신규 기출 모의고사 시작">${pmTrend}개</span>
                                </div>
                                <div style="display:flex; flex-direction:column; gap:0.1rem;">
                                    <span style="font-size:0.62rem; color:#60a5fa; font-weight:700;">SE</span>
                                    <span style="font-size:0.74rem; font-weight:700; color:var(--text-primary);">${seMax}</span>
                                    <span style="font-size:0.58rem; color:#60a5fa; font-weight:600; text-decoration:underline; cursor:pointer; margin-top:2px;" onclick="event.stopPropagation(); startYearlyExam(${item.year}, true, 'SE')" title="클릭 시 SE 신규 기출 모의고사 시작">${seTrend}개</span>
                                </div>
                                <div style="display:flex; flex-direction:column; gap:0.1rem;">
                                    <span style="font-size:0.62rem; color:#a78bfa; font-weight:700;">DB</span>
                                    <span style="font-size:0.74rem; font-weight:700; color:var(--text-primary);">${dbMax}</span>
                                    <span style="font-size:0.58rem; color:#a78bfa; font-weight:600; text-decoration:underline; cursor:pointer; margin-top:2px;" onclick="event.stopPropagation(); startYearlyExam(${item.year}, true, 'DB')" title="클릭 시 DB 신규 기출 모의고사 시작">${dbTrend}개</span>
                                </div>
                                <div style="display:flex; flex-direction:column; gap:0.1rem;">
                                    <span style="font-size:0.62rem; color:#fbbf24; font-weight:700;">SA</span>
                                    <span style="font-size:0.74rem; font-weight:700; color:var(--text-primary);">${saMax}</span>
                                    <span style="font-size:0.58rem; color:#fbbf24; font-weight:600; text-decoration:underline; cursor:pointer; margin-top:2px;" onclick="event.stopPropagation(); startYearlyExam(${item.year}, true, 'SA')" title="클릭 시 SA 신규 기출 모의고사 시작">${saTrend}개</span>
                                </div>
                                <div style="display:flex; flex-direction:column; gap:0.1rem;">
                                    <span style="font-size:0.62rem; color:#34d399; font-weight:700;">SC</span>
                                    <span style="font-size:0.74rem; font-weight:700; color:var(--text-primary);">${scMax}</span>
                                    <span style="font-size:0.58rem; color:#34d399; font-weight:600; text-decoration:underline; cursor:pointer; margin-top:2px;" onclick="event.stopPropagation(); startYearlyExam(${item.year}, true, 'SC')" title="클릭 시 SC 신규 기출 모의고사 시작">${scTrend}개</span>
                                </div>
                            </div>
                        </div>
                        <div class="exam-stat-row">
                            <span>연습 회차</span>
                            <span class="exam-stat-val">${item.practice_count}회 완료</span>
                        </div>
                        <div class="exam-stat-row">
                            <span>최근 연습일</span>
                            <span class="exam-stat-val" style="font-size: 0.78rem;">${lastAttempt}</span>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 0.8rem; text-align: left;">
                        <label style="display: block; font-size: 0.72rem; color: var(--text-secondary); margin-bottom: 0.35rem; font-weight: 600;">🎯 응시 과목 범위</label>
                        <select class="subject-select" id="subject-select-${item.year}">
                            <option value="ALL">전체 (120문항)</option>
                            <option value="PM">감리 및 사업관리 (25문항)</option>
                            <option value="SE">소프트웨어공학 (25문항)</option>
                            <option value="DB">데이터베이스 (25문항)</option>
                            <option value="SA">시스템 아키텍처 (25문항)</option>
                            <option value="SC">보안 (20문항)</option>
                        </select>
                    </div>

                    <button class="start-btn" onclick="startYearlyExam(${item.year})">
                        <i data-lucide="edit-3" style="width: 16px; height: 16px;"></i> 풀기 시작 📝
                    </button>
                `;
        container.appendChild(card);
    });
    initLucide();
}

// 화면 전환 헬퍼 (존재하지 않는 뷰 엘리먼트에 대한 크래시 예방 조치 적용)
function showScreen(screenId) {
    const screens = ['loading-screen', 'selection-view', 'practice-view', 'result-view'];
    screens.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    const target = document.getElementById(screenId);
    if (target) target.style.display = 'block';

    const subtitle = document.getElementById('view-subtitle');
    if (screenId === 'selection-view') {
        if (subtitle) subtitle.innerText = "연도별 1회분 기출문제(120문항) 전체 또는 과목 범위를 선택해 타이머 측정과 함께 응시합니다.";
        const homeLink = document.getElementById('home-link');
        if (homeLink) homeLink.style.display = 'inline-flex';
        checkPendingSubmits();
    } else if (screenId === 'practice-view') {
        if (subtitle) subtitle.innerText = "문항당 머무른 시간 및 총 소요 시간이 실시간 기록됩니다. 중도 이탈 시 자동 저장 기능이 적용됩니다.";
        const homeLink = document.getElementById('home-link');
        if (homeLink) homeLink.style.display = 'none';
    } else if (screenId === 'result-view') {
        if (subtitle) subtitle.innerText = "응시가 완료되었습니다. 전체 문항 분석 결과 및 과목별 취약 보완 포인트를 점검하세요.";
        const homeLink = document.getElementById('home-link');
        if (homeLink) homeLink.style.display = 'inline-flex';
    }
}

// 시험 시작
function startYearlyExam(year, isNewTrendOnly = false, trendSubject = 'ALL') {
    // 1. 선택 화면(yearly_exam.html)에서 호출 시 풀이 페이지(yearly_practice.html)로 던지며 리다이렉트
    if (!window.location.pathname.includes('yearly_practice.html')) {
        localStorage.setItem('session_exam_year', year);
        localStorage.setItem('session_is_new_trend', isNewTrendOnly ? 'true' : 'false');
        localStorage.setItem('session_trend_subject', trendSubject);
        window.location.href = 'yearly_practice.html';
        return;
    }

    examYear = year;

    if (isNewTrendOnly) {
        selectedSubjectRange = 'NEW_TREND_' + trendSubject;
    } else {
        // 드롭다운 과목 필터 값 로드
        const selectEl = document.getElementById(`subject-select-${year}`);
        selectedSubjectRange = selectEl ? selectEl.value : 'ALL';
    }

    showScreen('loading-screen');

    fetch(`/api/yearly-exam/questions?year=${year}`)
        .then(res => {
            if (!res.ok) throw new Error("Questions load failed");
            return res.json();
        })
        .then(data => {
            if (data.length === 0) {
                alert("해당 연도의 기출문제가 데이터베이스에 없습니다.");
                loadYearlyExams();
                return;
            }

            // 과목별 슬라이싱 필터링 또는 신규 기출 필터 적용
            let filteredData;
            if (isNewTrendOnly) {
                filteredData = data.filter(q => {
                    const isNew = (q.is_new_trend === 1) || (window.NEW_TREND_MAPPING && window.NEW_TREND_MAPPING[`${year}_${q.question_num}`] === 1);
                    if (!isNew) return false;
                    if (trendSubject === 'ALL') return true;

                    const qSub = getSubjectInfo(q.question_num).code;
                    return qSub === trendSubject;
                });
            } else {
                const rangeInfo = SUBJECT_RANGES[selectedSubjectRange].range;
                filteredData = data.filter(q => q.question_num >= rangeInfo[0] && q.question_num <= rangeInfo[1]);
            }

            if (filteredData.length === 0) {
                alert("선택한 범위에 해당하는 문제가 존재하지 않습니다.");
                loadYearlyExams();
                return;
            }

            questions = filteredData;
            // 각 문항의 보기 셔플용 인덱스 배열 생성 (대시보드와 동일 기법)
            questions.forEach(q => {
                if (q.options && q.options.length > 0) {
                    const indices = Array.from({ length: q.options.length }, (_, i) => i);
                    q.shuffledIndices = shuffleArray(indices);
                }
            });
            currentIdx = 0;
            userAnswers = {};
            totalSeconds = 0;
            qSeconds = Array.from({ length: questions.length }, () => 0);

            initOMRCard();
            renderQuestion();
            startTimers();
            showScreen('practice-view');
            saveBackup();
        })
        .catch(err => {
            console.error(err);
            alert("문제를 로드하는 중 오류가 발생했습니다.");
            loadYearlyExams();
        });
}

// 백업 데이터 복원
function restoreBackup(backup) {
    examYear = backup.examYear;
    selectedSubjectRange = backup.selectedSubjectRange || 'ALL';
    questions = backup.questions;
    currentIdx = backup.currentIdx;
    userAnswers = backup.userAnswers;
    totalSeconds = backup.totalSeconds;
    qSeconds = backup.qSeconds;

    initOMRCard();

    for (let qNum in userAnswers) {
        const node = document.getElementById(`omr-${qNum}`);
        if (node) {
            node.classList.add('marked');
            node.querySelector('.omr-node-val').innerText = userAnswers[qNum];
        }
    }
    updateOMRCount();
    renderQuestion();
    startTimers();
    showScreen('practice-view');
}

// 진행 상태 백업
function saveBackup() {
    const backup = {
        examYear,
        selectedSubjectRange,
        questions,
        currentIdx,
        userAnswers,
        totalSeconds,
        qSeconds
    };
    localStorage.setItem(BACKUP_KEY, JSON.stringify(backup));
}

// 타이머 구동
function startTimers() {
    clearInterval(totalTimerInterval);
    clearInterval(qTimerInterval);

    totalTimerInterval = setInterval(() => {
        totalSeconds++;
        document.getElementById('total-timer-val').innerText = formatTotalTime(totalSeconds);
    }, 1000);

    qTimerInterval = setInterval(() => {
        qSeconds[currentIdx]++;
        document.getElementById('q-timer-val').innerText = formatMinSec(qSeconds[currentIdx]);
    }, 1000);
}

// 타이머 중지
function stopTimers() {
    clearInterval(totalTimerInterval);
    clearInterval(qTimerInterval);
}

// OMR 카드 초기화
function initOMRCard() {
    const container = document.getElementById('omr-grid-container');
    container.innerHTML = '';

    questions.forEach((q, idx) => {
        const node = document.createElement('div');
        node.className = 'omr-node';
        node.id = `omr-${q.question_num}`;
        node.onclick = () => jumpToQuestion(idx);

        node.innerHTML = `
                    <span class="omr-node-qnum">${q.question_num}</span>
                    <span class="omr-node-val">-</span>
                `;
        container.appendChild(node);
    });
}

// OMR 개수 갱신
function updateOMRCount() {
    const total = questions.length;
    const marked = Object.keys(userAnswers).length;
    document.getElementById('omr-marked-count').innerText = `${marked} / ${total} 완료`;
}

// 문제 점프
function jumpToQuestion(idx) {
    clearInterval(qTimerInterval);
    currentIdx = idx;
    renderQuestion();

    document.getElementById('q-timer-val').innerText = formatMinSec(qSeconds[currentIdx]);
    qTimerInterval = setInterval(() => {
        qSeconds[currentIdx]++;
        document.getElementById('q-timer-val').innerText = formatMinSec(qSeconds[currentIdx]);
    }, 1000);

    saveBackup();
}

// 문항에 따른 과목명 찾기
function getSubjectInfo(qNum) {
    for (let subCode in SUBJECTS) {
        const range = SUBJECTS[subCode].range;
        if (qNum >= range[0] && qNum <= range[1]) {
            return { code: subCode, name: SUBJECTS[subCode].name };
        }
    }
    return { code: 'ETC', name: '기타' };
}

// 문제 렌더링
function renderQuestion() {
    const q = questions[currentIdx];
    if (!q) return;

    const subInfo = getSubjectInfo(q.question_num);
    const tag = document.getElementById('current-subject-tag');
    tag.innerText = subInfo.name;
    tag.style.background = getSubjectGradient(subInfo.code);

    document.getElementById('current-q-num-label').innerText = `${q.question_num}번 문항`;

    // 신규 기출 뱃지 처리 (window.NEW_TREND_MAPPING 캐시 또는 q.is_new_trend 검출)
    const isNewTrend = (q.is_new_trend === 1) || (window.NEW_TREND_MAPPING && window.NEW_TREND_MAPPING[`${q.year}_${q.question_num}`] === 1);
    const newTrendBadge = isNewTrend ? `<span class="new-trend-badge" style="background: linear-gradient(135deg, #ec4899 0%, #db2777 100%); color: #ffffff; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.72rem; font-weight: 800; margin-right: 0.5rem; display: inline-block; vertical-align: middle; box-shadow: 0 2px 4px rgba(236, 72, 153, 0.3);">✨ 신규 기출</span>` : '';

    document.getElementById('question-text-content').innerHTML = newTrendBadge + q.question;

    // 새 문항 로드 시 이미지 접기 상태로 리셋
    isImageExpanded = false;
    const imgBtn = document.getElementById('toggle-img-btn');
    if (imgBtn) {
        imgBtn.innerHTML = `<i data-lucide="image" style="width: 15px; height: 15px;"></i> 기출 원본 이미지 펼치기 (펼치기)`;
    }

    const imgContainer = document.getElementById('question-img-container');
    const imgElement = document.getElementById('question-img-element');
    const imgBtnWrap = document.getElementById('toggle-img-btn-wrap');
    const imgPath = `../images/${q.year}_${q.question_num}.png`;

    imgElement.onerror = () => {
        imgContainer.style.display = 'none';
        if (imgBtnWrap) imgBtnWrap.style.display = 'none'; // 이미지 없으면 버튼도 숨김
    };
    imgElement.onload = () => {
        // 이미지가 존재하면 펼치기 버튼을 노출하고 실제 이미지는 숨김 상태를 유지
        if (imgBtnWrap) imgBtnWrap.style.display = 'block';
        imgContainer.style.display = 'none';
    };
    imgElement.src = imgPath;

    const optionsContainer = document.getElementById('options-button-container');
    optionsContainer.innerHTML = '';

    const markedVal = userAnswers[q.question_num];

    const indices = q.shuffledIndices || Array.from({ length: q.options.length }, (_, i) => i);

    indices.forEach((originalOptIdx, displayOptIdx) => {
        const optNum = originalOptIdx + 1;
        const displayNum = displayOptIdx + 1;
        const optText = q.options[originalOptIdx];

        const btn = document.createElement('button');
        btn.className = 'option-btn';
        if (markedVal === optNum) {
            btn.classList.add('selected');
        }
        btn.onclick = () => selectOption(q.question_num, optNum);

        btn.innerHTML = `
                    <span class="option-num">${displayNum}</span>
                    <span class="option-text">${optText}</span>
                `;
        optionsContainer.appendChild(btn);
    });

    document.querySelectorAll('.omr-node').forEach(node => node.classList.remove('current'));
    const currentNode = document.getElementById(`omr-${q.question_num}`);
    if (currentNode) {
        currentNode.classList.add('current');
        currentNode.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    const solvedCount = Object.keys(userAnswers).length;
    const pct = Math.round((solvedCount / questions.length) * 100);
    document.getElementById('progress-text-label').innerText = `진행도: ${solvedCount} / ${questions.length} 문항 완료`;
    document.getElementById('progress-pct-label').innerText = `${pct}%`;
    document.getElementById('progress-bar-fill').style.width = `${pct}%`;

    document.getElementById('prev-q-btn').disabled = (currentIdx === 0);
    document.getElementById('next-q-btn').innerHTML = (currentIdx === questions.length - 1)
        ? '마지막 문제'
        : '다음 문제 <i class="lucide-chevron-right" data-lucide="chevron-right" style="width: 16px; height: 16px;"></i>';
    initLucide();
}

// 마킹 선택
function selectOption(qNum, optNum) {
    userAnswers[qNum] = optNum;

    const node = document.getElementById(`omr-${qNum}`);
    if (node) {
        node.classList.add('marked');
        node.querySelector('.omr-node-val').innerText = optNum;
    }
    updateOMRCount();

    document.querySelectorAll('.option-btn').forEach((btn, idx) => {
        if (idx + 1 === optNum) {
            btn.classList.add('selected');
        } else {
            btn.classList.remove('selected');
        }
    });

    saveBackup();

    if (currentIdx < questions.length - 1) {
        setTimeout(() => {
            if (userAnswers[qNum] === optNum && currentIdx === questions.findIndex(q => q.question_num === qNum)) {
                goToNextQuestion();
            }
        }, 400);
    }
}

// 이전/다음
function goToPrevQuestion() {
    if (currentIdx > 0) {
        jumpToQuestion(currentIdx - 1);
    }
}

function goToNextQuestion() {
    if (currentIdx < questions.length - 1) {
        jumpToQuestion(currentIdx + 1);
    }
}

// 풀이 중 이탈
function quitExam() {
    if (confirm("정말 시험을 종료하시겠습니까? 기록 중인 데이터와 타이머는 백업에서 완전히 소멸하며, 저장되지 않습니다.")) {
        stopTimers();
        localStorage.removeItem(BACKUP_KEY);
        window.location.href = 'yearly_exam.html';
    }
}

// 풀이 중 중간 제출 (아무때나 DB 반영)
function interimSubmitExam() {
    const solved = Object.keys(userAnswers).length;
    if (solved === 0) {
        alert("최소 한 문항 이상 마킹해야 반영이 가능합니다.");
        return;
    }
    if (confirm(`현재까지 [ ${solved} / ${questions.length} 문항 ] 마킹 완료되었습니다.\n풀이를 중단하고 현재까지의 마킹 정보만 채점해 즉시 DB에 기록하시겠습니까?`)) {
        submitExam(true); // interim 플래그 전달
    }
}

// 최종 제출 의사 확인
function confirmSubmitExam() {
    const total = questions.length;
    const solved = Object.keys(userAnswers).length;
    const unsolved = total - solved;

    let alertMsg = "답안지를 정말 최종 제출하시겠습니까?";
    if (unsolved > 0) {
        alertMsg = `⚠️ 풀지 않은 문제가 [ ${unsolved}개 ] 있습니다. 마킹되지 않은 문제는 오답 처리됩니다. 정말 최종 제출하시겠습니까?`;
    }

    if (confirm(alertMsg)) {
        submitExam(false);
    }
}

// 백엔드 데이터 제출 및 임시 로컬 캐시 처리
function submitExam(isInterim = false) {
    stopTimers();
    showScreen('loading-screen');

    let correctCount = 0;
    const details = [];

    questions.forEach((q, idx) => {
        const uAns = userAnswers[q.question_num] || null;
        const correctAns = Array.isArray(q.answer) ? q.answer[0] : q.answer;
        const isCorrect = (uAns === correctAns);
        if (isCorrect) correctCount++;

        details.push({
            q_id: q.id,
            question_num: q.question_num,
            user_answer: uAns ? [uAns] : [],
            is_correct: isCorrect,
            elapsed_time: qSeconds[idx]
        });
    });

    const score = (correctCount * 100.0 / questions.length);

    const payload = {
        exam_year: examYear,
        score: parseFloat(score.toFixed(1)),
        correct_count: correctCount,
        total_questions: questions.length,
        total_time: totalSeconds,
        question_times: qSeconds,
        details: details
    };

    fetch('/api/yearly-exam/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(res => {
            if (!res.ok) throw new Error("Submit failed");
            return res.json();
        })
        .then(data => {
            localStorage.removeItem(BACKUP_KEY);
            localStorage.setItem('session_result_data', JSON.stringify({
                payload: payload,
                practice_count: data.practice_count || 1
            }));
            window.location.href = 'yearly_result.html';
        })
        .catch(err => {
            console.error("제출 실패. 로컬스토리지 임시 대기열에 저장합니다:", err);

            // 네트워크 에러 등으로 실패 시 localStorage pending 대기열에 푸시
            backupPendingSubmit(payload);

            alert("네트워크 통신 불안정으로 인해 서버 DB 반영에 실패했습니다.\n채점 결과는 브라우저 로컬 저장소에 안전하게 백업되었으며, 연결 복구 후 메인 화면 상단 배너를 통해 언제든지 수동으로 DB에 전송(반영)할 수 있습니다.");

            localStorage.removeItem(BACKUP_KEY);
            localStorage.setItem('session_result_data', JSON.stringify({
                payload: payload,
                practice_count: 1
            }));
            window.location.href = 'yearly_result.html';
        });
}

// 결과 데이터를 로컬 보류 대기열에 백업
function backupPendingSubmit(payload) {
    let pendingList = [];
    const existing = localStorage.getItem(PENDING_KEY);
    if (existing) {
        try {
            pendingList = JSON.parse(existing);
        } catch (e) { }
    }
    pendingList.push(payload);
    localStorage.setItem(PENDING_KEY, JSON.stringify(pendingList));
}

// [아무때나 DB 반영 기능] 로컬 보류 리스트를 순차적으로 백엔드 서버에 싱크
function syncPendingSubmits() {
    const pending = localStorage.getItem(PENDING_KEY);
    if (!pending) return;

    let list = [];
    try {
        list = JSON.parse(pending);
    } catch (e) {
        localStorage.removeItem(PENDING_KEY);
        return;
    }

    if (list.length === 0) return;

    showScreen('loading-screen');

    // 순차적 프로미스 체인을 통한 안전 제출 동기화
    let sequence = Promise.resolve();
    const successIndices = [];

    list.forEach((payload, index) => {
        sequence = sequence.then(() => {
            return fetch('/api/yearly-exam/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
                .then(res => {
                    if (res.ok) {
                        successIndices.push(index);
                    }
                })
                .catch(err => console.error(`동기화 항목 [${index}] 전송 실패:`, err));
        });
    });

    sequence.then(() => {
        // 성공한 항목 필터링하여 대기열에서 제거
        const remaining = list.filter((_, idx) => !successIndices.includes(idx));
        if (remaining.length === 0) {
            localStorage.removeItem(PENDING_KEY);
            alert("모든 로컬 풀이 결과 기록이 데이터베이스(DB)에 성공적으로 동기화 반영되었습니다!");
        } else {
            localStorage.setItem(PENDING_KEY, JSON.stringify(remaining));
            alert(`총 ${list.length}건 중 ${successIndices.length}건의 기록이 DB에 동기화 반영되었습니다. (실패 ${remaining.length}건)`);
        }
        loadYearlyExams();
    });
}

// 결과 분석 리포트 화면 렌더링
function renderResultReport(result, practiceCount) {
    document.getElementById('result-exam-title').innerText = `${result.exam_year}년도 모의고사 결과`;

    // 과목 필터가 적용된 경우 결과 요약 메시지 보충
    const total = result.total_questions;
    const scopeName = total < 120 ? "과목 응시" : "전체 모의고사";

    document.getElementById('result-score-display').innerText = `${result.score.toFixed(1)}점`;
    document.getElementById('result-correct-count').innerText = `${result.correct_count} / ${result.total_questions}`;
    document.getElementById('result-total-time').innerText = formatTotalTime(result.total_time);
    document.getElementById('result-practice-count').innerText = `${practiceCount}회차`;

    // 과목별 정답 분석 연산
    const subjectStats = {};
    for (let subCode in SUBJECTS) {
        subjectStats[subCode] = { correct: 0, total: 0 };
    }

    result.details.forEach(item => {
        const subInfo = getSubjectInfo(item.question_num);
        if (subjectStats[subInfo.code]) {
            subjectStats[subInfo.code].total++;
            if (item.is_correct) {
                subjectStats[subInfo.code].correct++;
            }
        }
    });

    const analysisContainer = document.getElementById('subject-analysis-container');
    analysisContainer.innerHTML = '';

    for (let code in subjectStats) {
        const stat = subjectStats[code];
        if (stat.total === 0) continue; // 과목 범위 필터 적용 시 푼 문제만 그리드에 노출시킴

        const pct = stat.total > 0 ? Math.round((stat.correct / stat.total) * 100) : 0;
        const isLow = pct < 60;

        const box = document.createElement('div');
        box.className = 'subject-analysis-box';
        box.innerHTML = `
                    <div class="subject-name-label">${SUBJECTS[code].name}</div>
                    <div class="subject-score-val">${stat.correct} / ${stat.total}</div>
                    <div class="subject-accuracy-pct ${isLow ? 'low' : ''}">${pct}% ${isLow ? '⚠️' : '✅'}</div>
                `;
        analysisContainer.appendChild(box);
    }

    // [신규 기출 vs 일반 기출 분리 정답률 계산]
    let normalTotal = 0;
    let normalCorrect = 0;
    let newTrendTotal = 0;
    let newTrendCorrect = 0;

    result.details.forEach(item => {
        const qid = `${result.exam_year}_${item.question_num}`;
        const isNew = (window.NEW_TREND_MAPPING && window.NEW_TREND_MAPPING[qid] === 1);
        if (isNew) {
            newTrendTotal++;
            if (item.is_correct) newTrendCorrect++;
        } else {
            normalTotal++;
            if (item.is_correct) normalCorrect++;
        }
    });

    const normalPct = normalTotal > 0 ? Math.round((normalCorrect / normalTotal) * 100) : 0;
    const newTrendPct = newTrendTotal > 0 ? Math.round((newTrendCorrect / newTrendTotal) * 100) : 0;
    const normalPctText = normalTotal > 0 ? `${normalPct}%` : '-';
    const newTrendPctText = newTrendTotal > 0 ? `${newTrendPct}%` : '-';

    // 학습자 맞춤형 취약점 진단 및 2가지 유형 분석
    let userTypeLabel = "";
    let userTypeDesc = "";
    let recommendation = "";

    if (normalPct >= 80 && newTrendPct < 50) {
        userTypeLabel = "유형 A (기출 완성형 학습자)";
        userTypeDesc = "기존 기출 회독 상태는 양호하나 최신 법제도 개정이나 생소한 신규 기술 트렌드에 약점을 보입니다.";
        recommendation = "💡 <b>처방 가이드:</b> <code>감리사_시험대비/가이드및법규</code> 폴더의 최신 고시 준수 가이드 및 공공데이터 지침서 등을 중심으로 신기술 트렌드를 집중 보완하십시오.";
    } else {
        userTypeLabel = "유형 B (개념/직관형 학습자)";
        userTypeDesc = "디테일한 암기(수식 계산, 표준 표기 규칙 등)의 정확성이 부족하여 전형적인 기출 패턴에서 오답이 잦습니다.";
        recommendation = "💡 <b>처방 가이드:</b> 확실한 득점원 확보를 위해 데이터베이스 정규화 공식, PMBOK 임계경로(Critical Path) 계산식 및 오답 노트를 중심으로 회독 수를 높이십시오.";
    }
    if (normalPct >= 80 && newTrendPct >= 80) {
        userTypeLabel = "🏆 합격 안정권 마스터";
        userTypeDesc = "기출의 완성도와 최신 트렌드 대응력이 균형 있게 최상위권에 도달했습니다.";
        recommendation = "💡 <b>처방 가이드:</b> 실전 모드 하에서 실수를 방지하고 소요 시간을 80분 이내로 타이트하게 단축하는 훈련에 힘쓰십시오.";
    }

    // 모의고사 출제 난이도 예측 및 시뮬레이션
    const difficultyLevel = newTrendTotal > 24 ? "상 (체감 난이도 높음)" : "중 (보통 수준)";
    const predictedScore = (normalPct * 0.8 + newTrendPct * 0.2).toFixed(1);

    const trendContainer = document.getElementById('trend-analysis-container');
    if (trendContainer) {
        trendContainer.innerHTML = `
            <div style="font-size: 0.95rem; font-weight: 700; color: #ec4899; margin-bottom: 0.8rem; display: flex; align-items: center; gap: 0.3rem;">
                <i data-lucide="brain-circuit" style="width: 18px; height: 18px;"></i> AI 신규 기출 분석 & 학습 취약 진단
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                <div style="background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; padding: 0.75rem;">
                    <div style="font-size: 0.76rem; color: var(--text-secondary); margin-bottom: 0.35rem;">기출 구분별 정답률</div>
                    <div style="display: flex; flex-direction: column; gap: 0.4rem;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                            <span>일반 기출 유형:</span>
                            <span style="font-weight: 700; color: #c084fc;">${normalCorrect} / ${normalTotal} (${normalPctText})</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                            <span>신규 기출 유형:</span>
                            <span style="font-weight: 700; color: #ec4899;">${newTrendCorrect} / ${newTrendTotal} (${newTrendPctText})</span>
                        </div>
                    </div>
                </div>
                <div style="background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; padding: 0.75rem;">
                    <div style="font-size: 0.76rem; color: var(--text-secondary); margin-bottom: 0.35rem;">출제 난이도 예측 및 시뮬레이션</div>
                    <div style="display: flex; flex-direction: column; gap: 0.4rem;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                            <span>모의고사 체감 난이도:</span>
                            <span style="font-weight: 700; color: #fbbf24;">${difficultyLevel}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                            <span>본 시험 예상 환산 점수:</span>
                            <span style="font-weight: 700; color: var(--success);">${predictedScore}점 / 88점 목표</span>
                        </div>
                    </div>
                </div>
            </div>
            <div style="background: rgba(139,92,246,0.04); border: 1px solid rgba(139,92,246,0.12); border-radius: 10px; padding: 0.8rem; font-size: 0.85rem;">
                <div style="font-weight: 700; color: #a78bfa; margin-bottom: 0.25rem;">🔍 학습자 맞춤형 취약점 진단: ${userTypeLabel}</div>
                <p style="color: var(--text-secondary); font-size: 0.8rem; line-height: 1.5; margin-bottom: 0.45rem;">${userTypeDesc}</p>
                <div style="font-size: 0.82rem; color: var(--text-primary); line-height: 1.5;">${recommendation}</div>
            </div>
        `;
    }

    renderReviewList(result.details);
    if (window.lucide) {
        lucide.createIcons();
    }
}

// 오답/전체 상세 리뷰 리스트 렌더링
function renderReviewList(details) {
    const container = document.getElementById('review-list-container');
    container.innerHTML = '';

    questions.forEach((q, idx) => {
        const itemDetail = details.find(d => d.question_num === q.question_num);
        const isCorrect = itemDetail ? itemDetail.is_correct : false;
        const uAns = (itemDetail && itemDetail.user_answer.length > 0) ? itemDetail.user_answer[0] : null;
        const correctAns = Array.isArray(q.answer) ? q.answer[0] : q.answer;

        const reviewDiv = document.createElement('div');
        reviewDiv.className = `review-item ${isCorrect ? 'correct' : 'wrong'}`;
        reviewDiv.dataset.status = isCorrect ? 'correct' : 'wrong';

        const subInfo = getSubjectInfo(q.question_num);

        let optionsHtml = '';
        q.options.forEach((optText, optIdx) => {
            const optNum = optIdx + 1;
            let optClass = 'review-option';
            if (optNum === correctAns) {
                optClass += ' correct-choice';
            } else if (optNum === uAns && !isCorrect) {
                optClass += ' wrong-choice';
            }

            optionsHtml += `
                        <div class="${optClass}">
                            <span style="font-weight: 700; margin-right: 0.5rem;">${optNum}.</span>
                            <span>${optText}</span>
                            ${optNum === correctAns ? ' (정답)' : ''}
                            ${optNum === uAns && !isCorrect ? ' (내가 고른 답)' : ''}
                        </div>
                    `;
        });

        const reviewImgPath = `images/${q.year}_${q.question_num}.png`;
        let imageHtml = `
                    <div class="question-img-wrap" id="review-img-wrap-${q.question_num}" style="display: none; margin-top: 1rem;">
                        <img src="${reviewImgPath}" alt="문제 이미지" class="question-img" 
                             onload="document.getElementById('review-img-wrap-${q.question_num}').style.display='flex';"
                             onerror="this.style.display='none';">
                    </div>
                `;

        reviewDiv.innerHTML = `
                    <div class="review-item-header">
                        <span class="review-item-qnum">
                            <span class="subject-tag" style="background: ${getSubjectGradient(subInfo.code)}; font-size: 0.7rem; padding: 0.15rem 0.4rem;">${subInfo.name}</span>
                            ${q.question_num}번 문항
                        </span>
                        <span class="review-status-badge ${isCorrect ? 'correct' : 'wrong'}">
                            ${isCorrect ? '정답' : '오답'} (풀이 시간: ${formatMinSec(qSeconds[idx])})
                        </span>
                    </div>
                    <div class="question-body" style="font-size: 0.92rem; margin-bottom: 1rem;">${q.question}</div>
                    
                    ${imageHtml}

                    <div class="review-options">
                        ${optionsHtml}
                    </div>
                    
                    <div class="review-explanation">
                        <div class="review-explanation-title">
                            <i data-lucide="book-open" style="width: 14px; height: 14px;"></i> 정답 및 상세 해설
                        </div>
                        <div style="color: var(--text-primary); font-size: 0.85rem;">
                            ${q.explanation || '등록된 상세 해설이 없습니다. 시험 범위 개념 요약을 대조해 지식을 보강해 보십시오.'}
                        </div>
                    </div>
                `;
        container.appendChild(reviewDiv);
    });

    initLucide();
    filterReview('all');
}

// 리뷰 필터 제어
function filterReview(status) {
    document.querySelectorAll('.filter-toggle-btn').forEach(btn => btn.classList.remove('active'));
    if (status === 'all') {
        document.getElementById('btn-filter-all').classList.add('active');
        document.querySelectorAll('.review-item').forEach(item => item.style.display = 'block');
    } else {
        document.getElementById('btn-filter-wrong').classList.add('active');
        document.querySelectorAll('.review-item').forEach(item => {
            if (item.dataset.status === 'wrong') {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    }
}

// 연도 선택 화면 리로딩
function reloadSelectionView() {
    window.location.href = 'yearly_exam.html';
}

// --- 헬퍼 유틸 함수 ---
function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const yy = String(d.getFullYear()).slice(-2);
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yy}.${mm}.${dd}`;
}

function formatTotalTime(sec) {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    return [
        String(h).padStart(2, '0'),
        String(m).padStart(2, '0'),
        String(s).padStart(2, '0')
    ].join(':');
}

function formatMinSec(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function getSubjectGradient(code) {
    switch (code) {
        case 'PM': return 'linear-gradient(135deg, #10b981 0%, #059669 100%)'; // Green
        case 'SE': return 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)'; // Blue
        case 'DB': return 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)'; // Violet
        case 'SA': return 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'; // Orange
        case 'SC': return 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)'; // Red
        default: return 'var(--accent-gradient)';
    }
}

// 과목 코드로 과목명을 매핑해주는 서브 헬퍼
function getSubjectNameByCode(code) {
    const map = {
        'PM': '감리 및 사업관리',
        'SE': '소프트웨어공학',
        'DB': '데이터베이스',
        'SA': '시스템 아키텍처',
        'SC': '보안'
    };
    return map[code] || code;
}

// Fisher-Yates Shuffle 헬퍼 함수
function shuffleArray(array) {
    const arr = [...array];
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}
