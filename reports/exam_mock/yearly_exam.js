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
                // 백업 복원을 위해 세션 값을 백업 기준으로 동기화
                const backupRange = backup.selectedSubjectRange || 'ALL';
                localStorage.setItem('session_exam_year', backup.examYear);
                localStorage.setItem('session_is_new_trend', backupRange.startsWith('NEW_TREND_') ? 'true' : 'false');
                localStorage.setItem('session_trend_subject', backupRange.startsWith('NEW_TREND_') ? backupRange.replace('NEW_TREND_', '') : backupRange);
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
    // 1. 세션 선택 값 확보
    const year = localStorage.getItem('session_exam_year');
    const isNewTrend = localStorage.getItem('session_is_new_trend') === 'true';
    const trendSubject = localStorage.getItem('session_trend_subject') || 'ALL';

    // 현재 세션이 요구하는 과목 범위 키 산출
    let expectedRange;
    if (isNewTrend) {
        expectedRange = 'NEW_TREND_' + trendSubject;
    } else {
        expectedRange = trendSubject;
    }

    // 2. 임시 OMR 백업 존재 시 일치 여부 확인 후 복원
    const backupData = localStorage.getItem(BACKUP_KEY);
    if (backupData) {
        try {
            const backup = JSON.parse(backupData);
            const backupRange = backup.selectedSubjectRange || 'ALL';
            const backupYear = String(backup.examYear);
            const sessionYear = String(year);

            // 연도와 과목 범위가 모두 일치할 때만 백업 복원
            if (backupYear === sessionYear && backupRange === expectedRange) {
                restoreBackup(backup);
                return;
            } else {
                // 불일치 시 기존 백업 폐기
                localStorage.removeItem(BACKUP_KEY);
            }
        } catch (e) {
            console.error("백업 복원 에러:", e);
            localStorage.removeItem(BACKUP_KEY);
        }
    }

    // 3. 세션 선택 값 기반으로 새 시험 시작
    if (!year) {
        alert("선택된 시험 정보가 없습니다. 연도 선택 화면으로 이동합니다.");
        window.location.href = 'yearly_exam.html';
        return;
    }

    startYearlyExam(year, isNewTrend, trendSubject);
}

function initResultPage() {
    const urlParams = new URLSearchParams(window.location.search);
    const fromHistory = urlParams.get('from_history') === 'true';

    if (fromHistory) {
        // [이력 상세보기 진입]
        const rawItem = localStorage.getItem('selected_history_item');
        if (!rawItem) {
            alert("상세 이력 정보가 존재하지 않습니다. 메인 화면으로 이동합니다.");
            window.location.href = 'yearly_exam.html';
            return;
        }

        try {
            const item = JSON.parse(rawItem);
            
            // 기출문제 정보 비동기 로딩 API 호출
            fetch(`/api/yearly-exam/questions?year=${item.exam_year}`)
                .then(res => {
                    if (!res.ok) throw new Error("문항 데이터 다운로드 실패");
                    return res.json();
                })
                .then(qList => {
                    questions = qList || [];
                    
                    // details 파싱
                    let details = [];
                    if (item.details) {
                        details = typeof item.details === 'string' ? JSON.parse(item.details) : item.details;
                    }
                    
                    // qSeconds 복원
                    qSeconds = details.map(d => d.elapsed_time || 0);

                    // renderResultReport 호환용 payload 구성
                    const payload = {
                        id: item.id,
                        exam_year: item.exam_year,
                        score: parseFloat(item.score),
                        correct_count: item.correct_count,
                        total_questions: item.total_questions,
                        total_time: item.total_time,
                        question_times: qSeconds,
                        details: details
                    };

                    renderResultReport(payload, item.practice_count || 1, true);
                })
                .catch(err => {
                    console.error(err);
                    alert("해당 연도의 기출문제 원본 데이터를 백엔드 서버로부터 가져오는 중 오류가 발생했습니다.");
                    window.location.href = 'yearly_exam.html';
                });
        } catch (e) {
            console.error("이력 상세 정보 파싱 에러:", e);
            alert("이력 데이터를 로드하는 중 오류가 발생했습니다.");
            window.location.href = 'yearly_exam.html';
        }
    } else {
        // [일반적인 시험 종료 후 결과 진입]
        const rawResult = localStorage.getItem('session_result_data');
        if (!rawResult) {
            alert("분석 결과가 존재하지 않습니다. 연도 선택 화면으로 이동합니다.");
            window.location.href = 'yearly_exam.html';
            return;
        }

        try {
            const result = JSON.parse(rawResult);
            questions = result.questions || [];
            qSeconds = (result.payload && result.payload.question_times) || Array.from({ length: questions.length }, () => 0);

            renderResultReport(result.payload, result.practice_count, false);
        } catch (e) {
            console.error("결과 복원 에러:", e);
            alert("결과 상세 분석 데이터를 로드하는 중 오류가 발생했습니다.");
            window.location.href = 'yearly_exam.html';
        }
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
        let actualSubject = trendSubject;
        if (!isNewTrendOnly) {
            const selectEl = document.getElementById(`subject-select-${year}`);
            if (selectEl) {
                actualSubject = selectEl.value;
            }
        }

        localStorage.setItem('session_exam_year', year);
        localStorage.setItem('session_is_new_trend', isNewTrendOnly ? 'true' : 'false');
        localStorage.setItem('session_trend_subject', actualSubject);
        window.location.href = 'yearly_practice.html';
        return;
    }

    examYear = year;

    if (isNewTrendOnly) {
        selectedSubjectRange = 'NEW_TREND_' + trendSubject;
    } else {
        // [설계 의도] yearly_practice.html 에는 드롭다운 엘리먼트가 없으므로
        // 세션 리다이렉션을 거쳐 전달된 trendSubject 값을 직접 selectedSubjectRange로 사용하여 
        // 선택한 단일 과목으로의 정상 필터링을 보장합니다.
        selectedSubjectRange = trendSubject || 'ALL';
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
        btn.dataset.optNum = optNum;
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
        
        // [설계 의도] scrollIntoView는 다중 스크롤 영역에서 전체 브라우저 창 스크롤까지 튀게 만드는 오작동이 있습니다.
        // OMR 카드가 담긴 전용 scrollable 컨테이너(omr-grid-container) 내부에서만 상대 스크롤 위치를 부드럽게 설정하여 
        // 전체 브라우저 뷰포트의 화면 튐 및 흔들림 현상을 원천 방지합니다.
        const container = document.querySelector('.omr-grid-container');
        if (container) {
            const containerTop = container.getBoundingClientRect().top;
            const nodeTop = currentNode.getBoundingClientRect().top;
            const relativeTop = nodeTop - containerTop + container.scrollTop;
            const scrollTarget = relativeTop - (container.clientHeight / 2) + (currentNode.clientHeight / 2);
            container.scrollTo({
                top: scrollTarget,
                behavior: 'smooth'
            });
        }
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

    document.querySelectorAll('.option-btn').forEach(btn => {
        if (Number(btn.dataset.optNum) === optNum) {
            btn.classList.add('selected');
        } else {
            btn.classList.remove('selected');
        }
    });

    saveBackup();

    // 보기 버튼 선택 시 포커스가 잡힌 채로 DOM이 재구성되면 브라우저 스크롤 튐이 발생하므로 포커스를 해제합니다.
    if (document.activeElement && typeof document.activeElement.blur === 'function') {
        document.activeElement.blur();
    }

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
        let isCorrect = false;
        if (uAns !== null) {
            if (Array.isArray(q.answer)) {
                isCorrect = q.answer.map(Number).includes(Number(uAns));
            } else {
                isCorrect = (Number(uAns) === Number(q.answer));
            }
        }
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
                questions: questions,
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
                questions: questions,
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
function renderResultReport(result, practiceCount, isFromHistory = false) {
    document.getElementById('result-exam-title').innerText = `${result.exam_year}년도 학습상세분석`;

    document.getElementById('result-score-val').innerText = `${result.score.toFixed(1)}`;
    document.getElementById('result-correct-val').innerText = `${result.correct_count} / ${result.total_questions}`;
    document.getElementById('result-time-val').innerText = formatTotalTime(result.total_time);
    document.getElementById('result-attempt-val').innerText = `${practiceCount}회차`;

    // 1. 과목별 정답 및 풀이 시간 집계
    const subjectStats = {};
    for (let subCode in SUBJECTS) {
        subjectStats[subCode] = { correct: 0, total: 0, timeSum: 0 };
    }

    // 2. 신규 기출 vs 일반 기출 분리 정답률 계산
    let normalTotal = 0;
    let normalCorrect = 0;
    let newTrendTotal = 0;
    let newTrendCorrect = 0;

    result.details.forEach(item => {
        const subInfo = getSubjectInfo(item.question_num);
        if (subjectStats[subInfo.code]) {
            subjectStats[subInfo.code].total++;
            subjectStats[subInfo.code].timeSum += (item.elapsed_time || 0);
            if (item.is_correct) {
                subjectStats[subInfo.code].correct++;
            }
        }

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

    // 3. AI 신규 기출 분석 & 학습 취약 진단 조립
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

    const difficultyLevel = newTrendTotal > 24 ? "상 (체감 난이도 높음)" : "중 (보통 수준)";
    const predictedScore = (normalPct * 0.8 + newTrendPct * 0.2).toFixed(1);

    const trendContainer = document.getElementById('trend-analysis-card-container');
    if (trendContainer) {
        trendContainer.innerHTML = `
            <div style="font-size: 0.88rem; font-weight: 700; color: #ec4899; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.3rem; text-align: left;">
                <i data-lucide="brain-circuit" style="width: 15px; height: 15px;"></i> AI 신규 기출 분석 & 학습 취약 진단
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1.1fr; gap: 0.6rem; margin-top: 0.4rem; text-align: left;">
                <!-- 왼쪽 컬럼: 정답률 및 시뮬레이션 박스 -->
                <div style="display: flex; flex-direction: column; gap: 0.4rem;">
                    <!-- 기출 구분별 정답률 -->
                    <div style="background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 0.5rem 0.6rem;">
                        <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.2rem; font-weight:700;">기출 구분별 정답률</div>
                        <div style="display: flex; flex-direction: column; gap: 0.2rem;">
                            <div style="display: flex; justify-content: space-between; font-size: 0.76rem;">
                                <span>일반 기출:</span>
                                <span style="font-weight: 700; color: #c084fc;">${normalCorrect}/${normalTotal} (${normalPctText})</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.76rem;">
                                <span>신규 기출:</span>
                                <span style="font-weight: 700; color: #ec4899;">${newTrendCorrect}/${newTrendTotal} (${newTrendPctText})</span>
                            </div>
                        </div>
                    </div>
                    <!-- 출제 난이도 예측 및 시뮬레이션 -->
                    <div style="background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 0.5rem 0.6rem;">
                        <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.2rem; font-weight:700;">출제 난이도 예측 및 시뮬레이션</div>
                        <div style="display: flex; flex-direction: column; gap: 0.2rem;">
                            <div style="display: flex; justify-content: space-between; font-size: 0.76rem;">
                                <span>체감 난이도:</span>
                                <span style="font-weight: 700; color: #fbbf24;">${difficultyLevel}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.76rem;">
                                <span>예상 환산점수:</span>
                                <span style="font-weight: 700; color: var(--success);">${predictedScore}점 / 88점 목표</span>
                            </div>
                        </div>
                    </div>
                </div>
                <!-- 오른쪽 컬럼: 학습자 맞춤형 취약점 진단 박스 -->
                <div style="background: rgba(139,92,246,0.04); border: 1px solid rgba(139,92,246,0.12); border-radius: 8px; padding: 0.6rem 0.7rem; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-weight: 700; color: #a78bfa; margin-bottom: 0.2rem; font-size: 0.76rem;">🔍 맞춤형 취약점 진단: ${userTypeLabel}</div>
                    <p style="color: var(--text-secondary); font-size: 0.7rem; line-height: 1.4; margin: 0 0 0.3rem 0;">${userTypeDesc}</p>
                    <div style="font-size: 0.72rem; color: var(--text-primary); line-height: 1.4; font-weight: 500;">${recommendation}</div>
                </div>
            </div>
        `;
    }

    // 4. 과목별 취약 스코어 및 5대 도메인 통계 주입
    const totalElapsed = result.details.reduce((acc, d) => acc + (d.elapsed_time || 0), 0);
    const globalAvgTime = result.details.length > 0 ? (totalElapsed / result.details.length) : 0;
    const recurrenceInsight = getYearlyWrongRecurrenceInsight(result, result.details);
    const weaknessScores = calculateSubjectWeaknessScores(subjectStats, recurrenceInsight.recurrenceBySubject, globalAvgTime);

    const statsContainer = document.getElementById('subject-stats-card-container');
    if (statsContainer) {
        statsContainer.innerHTML = '';
        for (let code in subjectStats) {
            const stat = subjectStats[code];
            if (stat.total === 0) continue;

            const pct = Math.round((stat.correct / stat.total) * 100);
            const avgTime = Math.round(stat.timeSum / stat.total);
            const isLow = pct < 60;
            const weakness = weaknessScores[code] || { weaknessScore: 0 };
            const weaknessColor = getWeaknessScoreColor(weakness.weaknessScore);
            const weaknessLabel = getWeaknessScoreLabel(weakness.weaknessScore);

            const box = document.createElement('div');
            box.className = 'subject-analysis-box';
            box.style.cssText = 'background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 10px; padding: 0.65rem; text-align: center;';
            box.innerHTML = `
                <div style="font-size: 0.72rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.25rem;">${SUBJECTS[code].name}</div>
                <div style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.15rem;">${stat.correct} / ${stat.total}문항</div>
                <div style="font-size: 0.8rem; font-weight: 700; color: ${isLow ? 'var(--error)' : 'var(--success)'}; margin-bottom: 0.25rem;">정답률: ${pct}%</div>
                <div style="font-size: 0.7rem; font-weight: 600; color: ${weaknessColor}; margin-bottom: 0.15rem;">취약도: ${weakness.weaknessScore}점 (${weaknessLabel})</div>
                <div style="font-size: 0.68rem; color: var(--text-secondary);">평균: ${avgTime}초</div>
            `;
            statsContainer.appendChild(box);
        }
    }

    // 5. 오답 재발 추적 카드 렌더링
    const recCard = document.getElementById('recurrence-tracking-card');
    if (recCard) {
        if (recurrenceInsight.previousAttemptCount > 0) {
            recCard.style.display = 'block';
            const recurringWrongHtml = recurrenceInsight.recurringWrong.length > 0
                ? recurrenceInsight.recurringWrong
                    .sort((a, b) => a - b)
                    .map(qNum => `<button type="button" class="yearly-recurring-chip" onclick="clickRecurrenceChip(${qNum})" style="display:inline-flex; align-items:center; padding:0.18rem 0.5rem; border-radius:999px; font-size:0.72rem; border:1px solid rgba(239,68,68,0.28); background:rgba(239,68,68,0.10); color:#fca5a5; margin-right:0.35rem; margin-bottom:0.35rem; cursor:pointer;">Q.${qNum}</button>`)
                    .join('')
                : '<span style="font-size:0.78rem; color: var(--text-secondary);">재발 오답은 없습니다.</span>';

            recCard.innerHTML = `
                <h3 style="font-size: 0.85rem; font-weight: 700; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.3rem; color: #f97316; margin-top: 0;">
                    <i data-lucide="repeat" style="width: 14px; height: 14px;"></i> 오답 재발 추적 (과거 기출이력 비교)
                </h3>
                <div style="background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.04); border-radius: 8px; padding: 0.5rem;">
                    <div style="font-size: 0.72rem; color: var(--text-secondary); margin-bottom: 0.35rem;">재발 오답 리스트 (클릭 시 누적 오답 비교)</div>
                    <div>${recurringWrongHtml}</div>
                </div>
            `;
        } else {
            recCard.style.display = 'none';
        }
    }

    // 6. OMR 반응 분석 그리드 바둑판 생성
    const gridContainer = document.getElementById('omr-board-grid');
    if (gridContainer) {
        gridContainer.innerHTML = '';
        result.details.forEach((d, dIdx) => {
            const isCorrect = d.is_correct;
            const cellBg = isCorrect ? 'rgba(16, 185, 129, 0.04)' : 'rgba(239, 68, 68, 0.04)';
            const cellBorder = isCorrect ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(239, 68, 68, 0.25)';
            const textCol = isCorrect ? '#34d399' : '#f87171';
            const cell = document.createElement('div');
            cell.className = 'yearly-omr-cell';
            cell.style.cssText = `background: ${cellBg}; border: ${cellBorder}; border-radius: 4px; padding: 0.15rem 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0; min-height: 32px; cursor: pointer;`;
            cell.title = `Q.${d.question_num} - ${isCorrect ? '정답' : '오답'} (시간: ${d.elapsed_time || 0}초)`;
            cell.innerHTML = `
                <span style="font-size: 0.52rem; color: var(--text-secondary); font-family: monospace; font-weight:600;">${d.question_num}</span>
                <span style="font-size: 0.62rem; font-weight: 700; color: ${textCol};">${isCorrect ? 'O' : 'X'}</span>
            `;
            cell.onclick = () => {
                switchViewerTab('detail');
                showYearlyWrongQuestionDetail(result, d);
                renderRecurrenceAnswerComparison(result, d);
            };
            gridContainer.appendChild(cell);
        });
    }

    // 7. 우측 오답 모아보기 선제 로드 및 뱃지 숫자 지정
    const wrongsCount = result.details.filter(d => !d.is_correct).length;
    document.getElementById('viewer-tab-wrong-all').innerText = `오답 모아보기 (${wrongsCount})`;
    renderYearlyWrongAllTab(result, result.details);

    if (window.lucide) {
        lucide.createIcons();
    }
}

// 탭 전환 헬퍼
function switchViewerTab(tabId) {
    const tabDetail = document.getElementById('viewer-panel-detail');
    const tabWrongAll = document.getElementById('viewer-panel-wrong-all');
    const btnDetail = document.getElementById('viewer-tab-detail');
    const btnWrongAll = document.getElementById('viewer-tab-wrong-all');

    if (tabId === 'detail') {
        if (tabDetail) tabDetail.style.display = 'flex';
        if (tabWrongAll) tabWrongAll.style.display = 'none';
        if (btnDetail) btnDetail.classList.add('active');
        if (btnWrongAll) btnWrongAll.classList.remove('active');
    } else {
        if (tabDetail) tabDetail.style.display = 'none';
        if (tabWrongAll) tabWrongAll.style.display = 'block';
        if (btnDetail) btnDetail.classList.remove('active');
        if (btnWrongAll) btnWrongAll.classList.add('active');
    }
}

// 선택 문항 지문 상세 렌더러
function showYearlyWrongQuestionDetail(item, detail) {
    const box = document.getElementById('yearly-wrong-detail-box');
    if (!box) return;

    box.innerHTML = `<div style="text-align:center; padding:3rem;"><i data-lucide="loader" class="animate-spin" style="width:20px; height:20px; margin:0 auto;"></i> 문항 세부 지문을 불러오고 있습니다...</div>`;
    if (window.lucide) lucide.createIcons();

    // questions 배열에서 실시간 검색 복원
    const q = questions.find(x => Number(x.question_num) === Number(detail.question_num));
    if (q) {
        renderQuestionDetailHtml(item, detail, q);
    } else {
        // 백업 API 호출
        fetch(`/api/question?id=${encodeURIComponent(item.exam_year + '_' + detail.question_num)}`)
            .then(res => res.json())
            .then(qObj => {
                renderQuestionDetailHtml(item, detail, qObj);
            })
            .catch(err => {
                console.error("지문 조회 에러:", err);
                box.innerHTML = `<div style="padding:2rem; color:var(--error); text-align:center;">지문 데이터를 조회하는 과정에서 네트워크 장애가 발생했습니다.</div>`;
            });
    }
}

function renderQuestionDetailHtml(item, detail, q) {
    const box = document.getElementById('yearly-wrong-detail-box');
    const isCorrect = detail.is_correct;
    const answers = Array.isArray(q.answer) ? q.answer.map(Number) : [Number(q.answer)];
    const uAns = Array.isArray(detail.user_answer) ? Number(detail.user_answer[0]) : Number(detail.user_answer);

    let optionsHtml = '';
    q.options.forEach((optText, optIdx) => {
        const optNum = optIdx + 1;
        const isOptCorrect = answers.includes(optNum);
        const isOptUserWrong = (optNum === uAns && !isCorrect);
        
        let optClass = 'review-option';
        let style = 'padding:0.55rem 0.8rem; border-radius:6px; border:1px solid rgba(255,255,255,0.04); background:rgba(255,255,255,0.01); font-size:0.82rem; margin-top:0.35rem; display:flex; gap:0.4rem;';
        
        if (isOptCorrect) {
            optClass += ' correct-choice';
            style = 'padding:0.55rem 0.8rem; border-radius:6px; border:1px solid rgba(16, 185, 129, 0.2); background:rgba(16, 185, 129, 0.04); font-size:0.82rem; margin-top:0.35rem; color:#ffffff; display:flex; gap:0.4rem;';
        } else if (isOptUserWrong) {
            optClass += ' wrong-choice';
            style = 'padding:0.55rem 0.8rem; border-radius:6px; border:1px solid rgba(239, 68, 68, 0.2); background:rgba(239, 68, 68, 0.04); font-size:0.82rem; margin-top:0.35rem; color:#ffffff; display:flex; gap:0.4rem;';
        }

        optionsHtml += `
            <div class="${optClass}" style="${style}">
                <span style="font-weight:700;">${optNum}.</span>
                <span>${optText}</span>
                ${isOptCorrect ? ' <span style="margin-left:auto; color:var(--success); font-weight:700; font-size:0.75rem;">(정답)</span>' : ''}
                ${isOptUserWrong ? ' <span style="margin-left:auto; color:var(--error); font-weight:700; font-size:0.75rem;">(선택 오답)</span>' : ''}
            </div>
        `;
    });

    const rangeInfo = getSubjectInfo(detail.question_num);
    const imgYear = String(item.exam_year).replace(/[^0-9]/g, '');
    const imgQNum = Number(detail.question_num);
    const reviewImgPath = `../images/${imgYear}_${imgQNum}.png`;
    const imageHtml = `
        <div id="yearly-q-img-btn-wrap-${detail.question_num}" style="background:rgba(59,130,246,0.02); border:1px solid rgba(59,130,246,0.08); border-radius:6px; padding:0.4rem 0.6rem; font-size:0.75rem; line-height:1.4; margin-top:0.6rem; margin-bottom:0.6rem;">
            <div onclick="toggleDetailTabImage(${detail.question_num})" style="color:#60a5fa; font-weight:700; display:flex; align-items:center; gap:0.25rem; cursor:pointer; user-select:none;">
                <i data-lucide="image" style="width:12px; height:12px;"></i> 기출 지문 크롭 이미지 (시험지 원본)
                <i data-lucide="chevron-down" id="detail-img-chevron-${detail.question_num}" style="width:12px; height:12px; margin-left:auto;"></i>
            </div>
            <div id="yearly-q-img-wrap-${detail.question_num}" style="display:none; margin-top:0.4rem; justify-content:center; background:rgba(0,0,0,0.2); border:1px solid rgba(255,255,255,0.04); border-radius:4px; padding:0.4rem;">
                <img src="${reviewImgPath}" alt="시험지 원본 이미지" style="max-width:100%; border-radius:4px;"
                     onerror="this.style.display='none'; this.parentNode.innerHTML='<div style=\'color:var(--text-muted); font-size:0.72rem; text-align:center; padding:0.4rem;\'>이 문항은 수식 또는 다이어그램 이미지가 필요 없는 일반 텍스트 문항입니다.</div>';">
            </div>
        </div>
    `;

    // 고시 가이드 매핑 체크
    const fullText = q.question + ' ' + (q.explanation || '');
    const matched = findMatchedLawGuide(fullText);
    let lawBtnHtml = '';
    if (matched) {
        lawBtnHtml = `
            <div style="margin-top: 0.8rem; text-align: left;">
                <button class="ctrl-btn" onclick="showLawGuideCard('${matched.file}', '${matched.name}')" 
                        style="padding: 0.35rem 0.75rem; font-size: 0.76rem; border-color: var(--accent-violet); background: rgba(139, 92, 246, 0.08); color: #c084fc; display: inline-flex; align-items: center; gap: 0.3rem; outline: none; cursor: pointer;">
                    <i data-lucide="scroll" style="width: 14px; height: 14px;"></i> 관련 고시: [ ${matched.name} ] 조항 보기
                </button>
            </div>
        `;
    }

    box.innerHTML = `
        <div style="background:rgba(255,255,255,0.01); border:1px solid rgba(255,255,255,0.04); border-radius:10px; padding:1rem; min-height:100%;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:0.4rem;">
                <span style="font-weight:700; font-size:0.88rem;">Q.${detail.question_num} 상세 보기</span>
                <span class="badge ${rangeInfo.code}" style="font-size:0.65rem; padding:0.15rem 0.35rem; border-radius:4px; font-weight:700; background: ${getSubjectGradient(rangeInfo.code)}; color: #ffffff; border:none;">${rangeInfo.name}</span>
            </div>
            <div style="font-size:0.88rem; line-height:1.45; color:var(--text-primary); white-space:pre-wrap; margin-bottom:0.8rem;">${q.question}</div>
            
            <div style="margin-bottom:0.8rem;">${optionsHtml}</div>
            
            <div style="background:rgba(16,185,129,0.02); border:1px solid rgba(16,185,129,0.08); border-radius:8px; padding:0.6rem 0.8rem; font-size:0.8rem; line-height:1.45; margin-bottom:0.6rem;">
                <div style="color:#c084fc; font-weight:700; margin-bottom:0.25rem; display:flex; align-items:center; gap:0.25rem;">
                    <i data-lucide="book-open" style="width:13px; height:13px;"></i> 정답 및 상세 해설
                </div>
                <div style="color:var(--text-secondary); margin-bottom:0.3rem;">${q.explanation || '등록된 상세 해설이 없습니다.'}</div>
                ${lawBtnHtml}
            </div>

            ${imageHtml}
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

// 오답 모아보기 탭 전체 렌더러
function renderYearlyWrongAllTab(item, details) {
    const box = document.getElementById('yearly-wrong-all-box');
    if (!box) return;

    const wrongs = details.filter(d => !d.is_correct);
    if (wrongs.length === 0) {
        box.innerHTML = `<div style="text-align:center; padding:4rem 1rem; color:var(--success); font-weight:600; font-size:0.8rem;">🎉 틀린 문제가 없습니다. 완벽한 합격선 통과입니다.</div>`;
        return;
    }

    let html = '<div style="display:flex; flex-direction:column; gap:0.8rem; padding:0.2rem;">';
    wrongs.forEach(d => {
        const q = questions.find(x => Number(x.question_num) === Number(d.question_num));
        if (!q) return;

        const answers = Array.isArray(q.answer) ? q.answer.map(Number) : [Number(q.answer)];
        const uAns = Array.isArray(d.user_answer) ? Number(d.user_answer[0]) : Number(d.user_answer);
        const rangeInfo = getSubjectInfo(d.question_num);

        let optionsHtml = '';
        q.options.forEach((optText, optIdx) => {
            const optNum = optIdx + 1;
            const isOptCorrect = answers.includes(optNum);
            const isOptUserWrong = (optNum === uAns);
            let optClass = 'review-option';
            let style = 'padding:0.4rem 0.6rem; border-radius:5px; border:1px solid rgba(255,255,255,0.03); background:rgba(255,255,255,0.01); font-size:0.78rem; margin-top:0.25rem; display:flex; gap:0.4rem;';

            if (isOptCorrect) {
                optClass += ' correct-choice';
                style = 'padding:0.4rem 0.6rem; border-radius:5px; border:1px solid rgba(16,185,129,0.15); background:rgba(16,185,129,0.03); font-size:0.78rem; margin-top:0.25rem; color:#ffffff; display:flex; gap:0.4rem;';
            } else if (isOptUserWrong) {
                optClass += ' wrong-choice';
                style = 'padding:0.4rem 0.6rem; border-radius:5px; border:1px solid rgba(239,68,68,0.15); background:rgba(239,68,68,0.03); font-size:0.78rem; margin-top:0.25rem; color:#ffffff; display:flex; gap:0.4rem;';
            }

            optionsHtml += `
                <div class="${optClass}" style="${style}">
                    <span style="font-weight:700;">${optNum}.</span>
                    <span>${optText}</span>
                    ${isOptCorrect ? ' <span style="margin-left:auto; color:var(--success); font-weight:700; font-size:0.72rem;">(정답)</span>' : ''}
                    ${isOptUserWrong ? ' <span style="margin-left:auto; color:var(--error); font-weight:700; font-size:0.72rem;">(선택 오답)</span>' : ''}
                </div>
            `;
        });

        const imgYear = String(item.exam_year).replace(/[^0-9]/g, '');
        const imgQNum = Number(d.question_num);
        const reviewImgPath = `../images/${imgYear}_${imgQNum}.png`;
        const imageHtml = `
            <div id="yearly-q-all-img-btn-wrap-${d.question_num}" style="background:rgba(59,130,246,0.02); border:1px solid rgba(59,130,246,0.08); border-radius:6px; padding:0.4rem 0.6rem; font-size:0.75rem; line-height:1.4; margin-top:0.4rem; margin-bottom:0.4rem;">
                <div onclick="toggleAllTabImage(${d.question_num})" style="color:#60a5fa; font-weight:700; display:flex; align-items:center; gap:0.25rem; cursor:pointer; user-select:none;">
                    <i data-lucide="image" style="width:12px; height:12px;"></i> 기출 지문 크롭 이미지 (시험지 원본)
                    <i data-lucide="chevron-down" id="img-chevron-${d.question_num}" style="width:12px; height:12px; margin-left:auto;"></i>
                </div>
                <div id="yearly-q-all-img-wrap-${d.question_num}" style="display:none; margin-top:0.4rem; justify-content:center; background:rgba(0,0,0,0.2); border:1px solid rgba(255,255,255,0.04); border-radius:4px; padding:0.4rem;">
                    <img src="${reviewImgPath}" alt="시험지 원본 이미지" style="max-width:100%; border-radius:4px;"
                         onerror="this.style.display='none'; this.parentNode.innerHTML='<div style=\'color:var(--text-muted); font-size:0.72rem; text-align:center; padding:0.4rem;\'>이 문항은 수식 또는 다이어그램 이미지가 필요 없는 일반 텍스트 문항입니다.</div>';">
                </div>
            </div>
        `;

        // 고시 가이드 매핑 체크
        const fullText = q.question + ' ' + (q.explanation || '');
        const matched = findMatchedLawGuide(fullText);
        let lawBtnHtml = '';
        if (matched) {
            lawBtnHtml = `
                <div style="margin-top: 0.8rem; text-align: left;">
                    <button class="ctrl-btn" onclick="showLawGuideCard('${matched.file}', '${matched.name}')" 
                            style="padding: 0.35rem 0.75rem; font-size: 0.76rem; border-color: var(--accent-violet); background: rgba(139, 92, 246, 0.08); color: #c084fc; display: inline-flex; align-items: center; gap: 0.3rem; outline: none; cursor: pointer;">
                        <i data-lucide="scroll" style="width: 14px; height: 14px;"></i> 관련 고시: [ ${matched.name} ] 조항 보기
                    </button>
                </div>
            `;
        }

        html += `
            <div style="background:rgba(255,255,255,0.015); border:1px solid rgba(255,255,255,0.05); border-radius:10px; padding:0.85rem; box-shadow:0 4px 12px rgba(0,0,0,0.1); margin-bottom: 0.8rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem; border-bottom:1px solid rgba(255,255,255,0.04); padding-bottom:0.35rem;">
                    <span style="font-weight:700; font-size:0.8rem; color:#f87171;">Q.${d.question_num}</span>
                    <span class="badge ${rangeInfo.code}" style="font-size:0.6rem; padding:0.12rem 0.3rem; border-radius:3px; font-weight:700; background: ${getSubjectGradient(rangeInfo.code)}; color: #ffffff; border:none;">${rangeInfo.name}</span>
                </div>
                <div style="font-size:0.8rem; line-height:1.45; color:var(--text-secondary); white-space:pre-wrap; margin-bottom:0.6rem;">${q.question}</div>
                
                <div style="margin-bottom:0.6rem;">${optionsHtml}</div>
                
                <div style="background:rgba(139,92,246,0.02); border:1px solid rgba(139,92,246,0.08); border-radius:6px; padding:0.4rem 0.6rem; font-size:0.75rem; line-height:1.4; margin-top:0.6rem; margin-bottom:0.6rem;">
                    <div onclick="toggleAllTabExplanation(${d.question_num})" style="color:#c084fc; font-weight:700; display:flex; align-items:center; gap:0.25rem; cursor:pointer; user-select:none;">
                        <i data-lucide="book-open" style="width:12px; height:12px;"></i> 정답 및 상세 해설
                        <i data-lucide="chevron-down" id="exp-chevron-${d.question_num}" style="width:12px; height:12px; margin-left:auto;"></i>
                    </div>
                    <div id="exp-content-${d.question_num}" style="display:none; margin-top:0.4rem; border-top:1px solid rgba(139,92,246,0.1); padding-top:0.4rem;">
                        <div style="color:var(--text-muted); margin-bottom:0.3rem; white-space:pre-wrap;">${q.explanation || '등록된 상세 해설이 없습니다.'}</div>
                        ${lawBtnHtml}
                    </div>
                </div>

                ${imageHtml}
            </div>
        `;
    });
    html += '</div>';
    box.innerHTML = html;
    if (window.lucide) lucide.createIcons();
}

// 오답 비교 분석 보드 조립기
function renderRecurrenceAnswerComparison(item, detail) {
    const box = document.getElementById('yearly-recurrence-compare-box');
    if (!box) return;
    box.innerHTML = '';
    box.style.display = 'none';

    if (detail.is_correct) return;

    const qNum = detail.question_num;
    const currentWrongAns = Array.isArray(detail.user_answer) ? detail.user_answer[0] : detail.user_answer;

    const rawHistory = localStorage.getItem('selected_history_list');
    let historyList = [];
    if (rawHistory) {
        try {
            historyList = JSON.parse(rawHistory);
        } catch {}
    }

    // 같은 연도의 시험 이력만 필터링하여 날짜 순(오름차순) 정렬
    const currentYear = item.exam_year;
    const filteredHistory = historyList.filter(hist => hist.exam_year === currentYear);
    filteredHistory.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

    const currentId = item.id;
    let records = [];

    filteredHistory.forEach(hist => {
        let histDetails = [];
        if (hist.details) {
            histDetails = typeof hist.details === 'string' ? JSON.parse(hist.details) : hist.details;
        }
        const match = histDetails.find(x => Number(x.question_num) === Number(qNum));
        if (match) {
            const ans = Array.isArray(match.user_answer) ? match.user_answer[0] : match.user_answer;
            const dateStr = hist.created_at.split('T')[0];
            records.push({
                histId: hist.id,
                date: dateStr,
                userAnswer: ans,
                isCorrect: match.is_correct,
                isCurrent: hist.id === currentId
            });
        }
    });

    if (records.length <= 1) return;

    box.style.display = 'block';
    let itemsHtml = '';
    records.forEach(r => {
        const checkIcon = r.isCorrect ? 'check' : 'x';
        const checkColor = r.isCorrect ? 'var(--success)' : 'var(--error)';
        const curStyle = r.isCurrent ? 'border:1px solid rgba(139,92,246,0.3); background:rgba(139,92,246,0.06);' : 'background:rgba(255,255,255,0.01);';
        
        itemsHtml += `
            <div style="padding:0.4rem 0.5rem; border-radius:6px; ${curStyle} text-align:center; min-width:80px; flex:1;">
                <div style="font-size:0.58rem; color:var(--text-muted); margin-bottom:0.15rem;">${r.date}${r.isCurrent ? ' (현재)' : ''}</div>
                <div style="font-size:0.8rem; font-weight:700; color:${checkColor}; display:flex; align-items:center; justify-content:center; gap:0.15rem;">
                    <i data-lucide="${checkIcon}" style="width:12px; height:12px;"></i> ${r.userAnswer}번 선택
                </div>
            </div>
        `;
    });

    box.innerHTML = `
        <div style="background:rgba(249,115,22,0.04); border:1px solid rgba(249,115,22,0.12); border-radius:10px; padding:0.65rem; font-size:0.75rem;">
            <div style="color:#f97316; font-weight:700; margin-bottom:0.35rem; display:flex; align-items:center; gap:0.25rem;">
                <i data-lucide="git-branch" style="width:13px; height:13px;"></i> 누적 오답 선택 히스토리 비교
            </div>
            <div style="display:flex; gap:0.4rem; overflow-x:auto;">
                ${itemsHtml}
            </div>
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

// 오답 재발 정보 수치 분석 헬퍼
function getYearlyWrongRecurrenceInsight(item, details) {
    const rawHistory = localStorage.getItem('selected_history_list');
    let historyList = [];
    if (rawHistory) {
        try {
            historyList = JSON.parse(rawHistory);
        } catch {}
    }

    const currentId = item.id;
    const currentYear = item.exam_year;

    const prevAttempts = historyList
        .filter(h => h.id !== currentId && h.exam_year === currentYear)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    const result = {
        previousAttemptCount: prevAttempts.length,
        currentWrongCount: details.filter(d => !d.is_correct).length,
        recurringWrong: [],
        recurrenceRate: 0,
        improvedCount: 0,
        recurrenceBySubject: { 'PM': 0, 'SE': 0, 'DB': 0, 'SA': 0, 'SC': 0 }
    };

    if (prevAttempts.length === 0) return result;

    const lastAttempt = prevAttempts[0];
    let lastDetails = [];
    if (lastAttempt.details) {
        lastDetails = typeof lastAttempt.details === 'string' ? JSON.parse(lastAttempt.details) : lastAttempt.details;
    }
    const lastWrongs = new Set(lastDetails.filter(d => !d.is_correct).map(d => Number(d.question_num)));

    const currentWrongs = details.filter(d => !d.is_correct).map(d => Number(d.question_num));
    const currentCorrects = details.filter(d => d.is_correct).map(d => Number(d.question_num));

    currentWrongs.forEach(qNum => {
        if (lastWrongs.has(qNum)) {
            result.recurringWrong.push(qNum);
            const code = getSubjectInfo(qNum).code;
            if (result.recurrenceBySubject[code] !== undefined) {
                result.recurrenceBySubject[code]++;
            }
        }
    });

    currentCorrects.forEach(qNum => {
        if (lastWrongs.has(qNum)) {
            result.improvedCount++;
        }
    });

    if (lastWrongs.size > 0) {
        result.recurrenceRate = Math.round((result.recurringWrong.length / lastWrongs.size) * 100);
    }

    return result;
}

// 과목별 약점 스코어 산출식
function calculateSubjectWeaknessScores(subStats, recurrenceBySubject, globalAvgTime) {
    const scores = {};
    for (let code in subStats) {
        const stat = subStats[code];
        if (stat.total === 0) continue;

        const errorRate = 1 - (stat.correct / stat.total);
        const avgTime = stat.timeSum / stat.total;
        
        let timePenalty = 0;
        if (globalAvgTime > 0) {
            timePenalty = Math.max(0, (avgTime - globalAvgTime) / globalAvgTime);
        }

        const recurrenceWeight = recurrenceBySubject[code] || 0;
        
        const rawScore = (errorRate * 60) + (timePenalty * 25) + (recurrenceWeight * 15);
        const weaknessScore = Math.min(100, Math.round(rawScore));
        scores[code] = { weaknessScore, recurrenceRate: recurrenceWeight };
    }
    return scores;
}

function getWeaknessScoreColor(score) {
    if (score >= 70) return '#ef4444';
    if (score >= 40) return '#f97316';
    return '#10b981';
}

function getWeaknessScoreLabel(score) {
    if (score >= 70) return '위험';
    if (score >= 40) return '경계';
    return '양호';
}

function clickRecurrenceChip(qNum) {
    const cell = Array.from(document.querySelectorAll('.yearly-omr-cell')).find(el => el.textContent.includes(`Q.${qNum}`));
    if (cell) {
        cell.click();
    }
}

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

// 결과 화면 창 닫기 (window.close 불가 시 이전 화면으로 폴백)
function closeResultWindow() {
    const urlParams = new URLSearchParams(window.location.search);
    const fromHistory = urlParams.get('from_history') === 'true';

    // 1. 우선 창 닫기 시도
    window.close();

    // 2. 만약 창이 닫히지 않은 경우를 대비한 폴백 처리
    setTimeout(() => {
        // 창 닫기가 안 닫혔을 경우(동일 탭 내 이동 등) 학습이력 화면으로 리다이렉트합니다.
        window.location.href = "../Learning_History/lhistory.html";
    }, 300); // 100ms -> 300ms로 상향하여 창이 닫히는 비동기 처리 타이밍 이슈 차단
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


// 고시·가이드 키워드 매핑 테이블
const LAW_GUIDE_MAPPING = [
    {
        file: '정보시스템_감리기준.txt',
        name: '정보시스템 감리기준',
        keywords: ['감리기준', '감리인력', '감리원', '총괄감리원', '수석감리원', '감리계획서', '감리수행', '감리법인', '요구정의단계', '과업대비표', '감리수행결과보고서', '감리계약', '감리 점검항목', '감리보고서', '감리 절차', '상근 감리원', '감리비']
    },
    {
        file: 'SW사업_대가산정_가이드.txt',
        name: 'SW사업 대가산정 가이드',
        keywords: ['대가산정', '기능점수', 'FP', 'ILF', 'EIF', 'EI', 'EO', 'EQ', '보정계수', '내부논리파일', '외부연계파일', '외부입력', '외부출력', '외부조회', 'KOSA', '개발비 산정', 'SW사업 대가', '기능점수당 단가', 'IFPUG']
    },
    {
        file: '공공데이터_관리지침.txt',
        name: '공공데이터 관리지침',
        keywords: ['공공데이터', '데이터 개방', '공공데이터 품질', '표준 메타데이터', '공공데이터베이스', '데이터 품질관리', '품질 진단', '공공기관 데이터']
    },
    {
        file: '전자정부_성과관리_지침.txt',
        name: '전자정부 성과관리 지침',
        keywords: ['성과관리', '성과 측정', '전자정부', '성과평가', '가동률', '서비스 만족도', '업무 처리 효율', '성과 지표', '정보화 사업 성과']
    },
    {
        file: '초거대_AI_도입_가이드라인.txt',
        name: '초거대 AI 도입 가이드라인',
        keywords: ['초거대 AI', '생성형 AI', 'AI 윤리', '할루시네이션', '환각 현상', 'AI 데이터 품질', '가명처리', '익명화', 'AI 도입', 'AI 편향', 'AI 공정성', 'AI 투명성']
    }
];

/**
 * 문제 지문·해설 텍스트에서 법규/가이드 키워드를 매칭하여
 * 가장 연관도가 높은 법규 파일 정보를 반환합니다.
 * @param {string} text - 문제 지문 + 해설 결합 텍스트
 * @returns {{ file: string, name: string } | null}
 */
function findMatchedLawGuide(text) {
    if (!text) return null;
    const lowerText = text.toLowerCase();

    let bestMatch = null;
    let bestScore = 0;

    LAW_GUIDE_MAPPING.forEach(guide => {
        let score = 0;
        guide.keywords.forEach(kw => {
            if (lowerText.includes(kw.toLowerCase())) {
                score++;
            }
        });
        if (score > bestScore) {
            bestScore = score;
            bestMatch = { file: guide.file, name: guide.name };
        }
    });

    return bestScore >= 1 ? bestMatch : null;
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

/**
 * 고시·가이드 스마트 요약 카드 모달 팝업 열기
 */
function showLawGuideCard(fileName, lawName) {
    const modal = document.getElementById('law-guide-modal');
    const title = document.getElementById('law-modal-title');
    const body = document.getElementById('law-modal-body');

    if (!modal || !title || !body) return;

    title.innerHTML = `<i class="lucide-scroll" data-lucide="scroll" style="color: var(--accent-violet); width: 22px; height: 22px;"></i> ${lawName} 핵심 조항`;
    body.textContent = "데이터를 가져오는 중입니다...";
    modal.style.display = 'flex';

    if (window.lucide) {
        lucide.createIcons();
    }

    fetch(`/api/law-guide?file=${encodeURIComponent(fileName)}`)
        .then(res => {
            if (!res.ok) throw new Error("법규 조회 실패");
            return res.json();
        })
        .then(data => {
            if (data.success) {
                body.textContent = data.content;
            } else {
                body.textContent = "가이드 내용을 로드할 수 없습니다.";
            }
        })
        .catch(err => {
            console.error(err);
            body.textContent = "서버 통신 실패 또는 요약 파일이 부재합니다.";
        });
}

function closeLawGuideModal(event) {
    const modal = document.getElementById('law-guide-modal');
    if (modal) modal.style.display = 'none';
}

function toggleAllTabImage(qNum) {
    const imgWrap = document.getElementById(`yearly-q-all-img-wrap-${qNum}`);
    const chevron = document.getElementById(`img-chevron-${qNum}`);
    if (!imgWrap) return;
    if (imgWrap.style.display === 'none' || imgWrap.style.display === '') {
        imgWrap.style.display = 'flex';
        if (chevron) chevron.setAttribute('data-lucide', 'chevron-up');
    } else {
        imgWrap.style.display = 'none';
        if (chevron) chevron.setAttribute('data-lucide', 'chevron-down');
    }
    if (window.lucide) lucide.createIcons();
}

function toggleAllTabExplanation(qNum) {
    const content = document.getElementById(`exp-content-${qNum}`);
    const chevron = document.getElementById(`exp-chevron-${qNum}`);
    if (!content) return;
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        if (chevron) chevron.setAttribute('data-lucide', 'chevron-up');
    } else {
        content.style.display = 'none';
        if (chevron) chevron.setAttribute('data-lucide', 'chevron-down');
    }
    if (window.lucide) lucide.createIcons();
}

function toggleDetailTabImage(qNum) {
    const imgWrap = document.getElementById(`yearly-q-img-wrap-${qNum}`);
    const chevron = document.getElementById(`detail-img-chevron-${qNum}`);
    if (!imgWrap) return;
    if (imgWrap.style.display === 'none' || imgWrap.style.display === '') {
        imgWrap.style.display = 'flex';
        if (chevron) chevron.setAttribute('data-lucide', 'chevron-up');
    } else {
        imgWrap.style.display = 'none';
        if (chevron) chevron.setAttribute('data-lucide', 'chevron-down');
    }
    if (window.lucide) lucide.createIcons();
}

// 전역 바인딩
window.showLawGuideCard = showLawGuideCard;
window.closeLawGuideModal = closeLawGuideModal;
window.switchViewerTab = switchViewerTab;
window.clickRecurrenceChip = clickRecurrenceChip;
window.toggleAllTabImage = toggleAllTabImage;
window.toggleAllTabExplanation = toggleAllTabExplanation;
window.toggleDetailTabImage = toggleDetailTabImage;
window.closeResultWindow = closeResultWindow;


