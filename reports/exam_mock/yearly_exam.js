// 실시간 AI 연동 로그 시뮬레이션 헬퍼
function startProgressiveLogSimulation(container, targetId) {
    const simulatedLogs = [
        "Gemini API Key #1 호출 시도 중... (시도 1/1)",
        "[Warning] Gemini API Key #1 429 Too Many Requests 감지.",
        "-> 백업 API Key #2로 즉시 전환하여 재시도합니다.",
        "Gemini API Key #2 호출 시도 중... (시도 1/1)",
        "[Warning] Gemini API Key #2 예외 발생: The read operation timed out",
        "[Warning] 모든 Gemini API Key 제한 또는 지연 감지. Hugging Face Llama-3 3차 폴백 가동합니다...",
        "Hugging Face Llama-3 3차 폴백 호출 시작...",
        "-> 대안 추론 엔진 보안 우회 헤더를 전송합니다.",
        "Hugging Face 백업 호출 통신 유지 중..."
    ];

    const simBox = document.createElement('div');
    simBox.id = targetId;
    simBox.style.cssText = 'background:#0f172a; color:#38bdf8; font-family:monospace, Courier; font-size:0.64rem; padding:0.5rem; border-radius:6px; border:1px solid #334155; margin-top:0.4rem; white-space:pre-line; text-align:left; max-height:140px; overflow-y:auto; line-height:1.4; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);';
    container.appendChild(simBox);

    let idx = 0;
    const interval = setInterval(() => {
        if (idx < simulatedLogs.length) {
            const line = simulatedLogs[idx];
            let html = line;
            if (line.includes('[Warning]')) {
                html = `<span style="color:#f59e0b; font-weight:600;">${line}</span>`;
            } else if (line.includes('가동합니다') || line.includes('성공')) {
                html = `<span style="color:#ec4899; font-weight:600;">${line}</span>`;
            }
            simBox.innerHTML += (simBox.innerHTML ? '\n' : '') + html;
            simBox.scrollTop = simBox.scrollHeight;
            idx++;
        }
    }, 450);

    return interval;
}

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
let currentDetailCtx = null; // 선택 문항 상세 탭의 편집 취소/저장 후 재렌더링용 원본 컨텍스트 { item, detail }
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

        // 과목별 신규 기출 연습 회차 계산
        const pmPracticeCount = item.new_trends ? item.new_trends.subjects.PM.practice_count : 0;
        const sePracticeCount = item.new_trends ? item.new_trends.subjects.SE.practice_count : 0;
        const dbPracticeCount = item.new_trends ? item.new_trends.subjects.DB.practice_count : 0;
        const saPracticeCount = item.new_trends ? item.new_trends.subjects.SA.practice_count : 0;
        const scPracticeCount = item.new_trends ? item.new_trends.subjects.SC.practice_count : 0;

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
                                    <span style="font-size:0.58rem; color:#38bdf8; font-weight:600; margin-top:2px;">${pmPracticeCount}회</span>
                                </div>
                                <div style="display:flex; flex-direction:column; gap:0.1rem;">
                                    <span style="font-size:0.62rem; color:#60a5fa; font-weight:700;">SE</span>
                                    <span style="font-size:0.74rem; font-weight:700; color:var(--text-primary);">${seMax}</span>
                                    <span style="font-size:0.58rem; color:#60a5fa; font-weight:600; text-decoration:underline; cursor:pointer; margin-top:2px;" onclick="event.stopPropagation(); startYearlyExam(${item.year}, true, 'SE')" title="클릭 시 SE 신규 기출 모의고사 시작">${seTrend}개</span>
                                    <span style="font-size:0.58rem; color:#38bdf8; font-weight:600; margin-top:2px;">${sePracticeCount}회</span>
                                </div>
                                <div style="display:flex; flex-direction:column; gap:0.1rem;">
                                    <span style="font-size:0.62rem; color:#a78bfa; font-weight:700;">DB</span>
                                    <span style="font-size:0.74rem; font-weight:700; color:var(--text-primary);">${dbMax}</span>
                                    <span style="font-size:0.58rem; color:#a78bfa; font-weight:600; text-decoration:underline; cursor:pointer; margin-top:2px;" onclick="event.stopPropagation(); startYearlyExam(${item.year}, true, 'DB')" title="클릭 시 DB 신규 기출 모의고사 시작">${dbTrend}개</span>
                                    <span style="font-size:0.58rem; color:#38bdf8; font-weight:600; margin-top:2px;">${dbPracticeCount}회</span>
                                </div>
                                <div style="display:flex; flex-direction:column; gap:0.1rem;">
                                    <span style="font-size:0.62rem; color:#fbbf24; font-weight:700;">SA</span>
                                    <span style="font-size:0.74rem; font-weight:700; color:var(--text-primary);">${saMax}</span>
                                    <span style="font-size:0.58rem; color:#fbbf24; font-weight:600; text-decoration:underline; cursor:pointer; margin-top:2px;" onclick="event.stopPropagation(); startYearlyExam(${item.year}, true, 'SA')" title="클릭 시 SA 신규 기출 모의고사 시작">${saTrend}개</span>
                                    <span style="font-size:0.58rem; color:#38bdf8; font-weight:600; margin-top:2px;">${saPracticeCount}회</span>
                                </div>
                                <div style="display:flex; flex-direction:column; gap:0.1rem;">
                                    <span style="font-size:0.62rem; color:#34d399; font-weight:700;">SC</span>
                                    <span style="font-size:0.74rem; font-weight:700; color:var(--text-primary);">${scMax}</span>
                                    <span style="font-size:0.58rem; color:#34d399; font-weight:600; text-decoration:underline; cursor:pointer; margin-top:2px;" onclick="event.stopPropagation(); startYearlyExam(${item.year}, true, 'SC')" title="클릭 시 SC 신규 기출 모의고사 시작">${scTrend}개</span>
                                    <span style="font-size:0.58rem; color:#38bdf8; font-weight:600; margin-top:2px;">${scPracticeCount}회</span>
                                </div>
                            </div>
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
                    <div id="subject-stats-card-container-left" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.4rem; margin-top: 0.2rem;"></div>
                </div>
                <!-- 오른쪽 컬럼: 학습자 맞춤형 취약점 진단 박스 -->
                <div id="ai-diagnose-card" style="background: rgba(139,92,246,0.04); border: 1px solid rgba(139,92,246,0.12); border-radius: 8px; padding: 0.6rem 0.7rem; display: flex; flex-direction: column; justify-content: center; transition: opacity 0.35s ease;">
                    <div style="font-weight: 700; color: #a78bfa; margin-bottom: 0.2rem; font-size: 0.76rem;">🔍 맞춤형 취약점 진단: ${userTypeLabel}</div>
                    <p style="color: var(--text-secondary); font-size: 0.7rem; line-height: 1.4; margin: 0 0 0.3rem 0;">${userTypeDesc}</p>
                    <div style="font-size: 0.72rem; color: var(--text-primary); line-height: 1.4; font-weight: 500;">${recommendation}</div>
                </div>
            </div>
        `;
        // 비동기 AI 진단 데이터 백그라운드 로드 개시
        fetchAIDiagnostics(result);
    }

    // 4. 과목별 취약 스코어 및 5대 도메인 통계 주입
    const totalElapsed = result.details.reduce((acc, d) => acc + (d.elapsed_time || 0), 0);
    const globalAvgTime = result.details.length > 0 ? (totalElapsed / result.details.length) : 0;
    const recurrenceInsight = getYearlyWrongRecurrenceInsight(result, result.details);
    const weaknessScores = calculateSubjectWeaknessScores(subjectStats, recurrenceInsight.recurrenceBySubject, globalAvgTime);

    const statsContainer = document.getElementById('subject-stats-card-container-left');
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
            box.innerHTML = `
                <div style="font-size: 0.72rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.25rem;">${SUBJECTS[code].name}</div>
                <div style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.15rem;">${stat.correct} / ${stat.total}문항</div>
                <div style="font-size: 0.8rem; font-weight: 700; color: ${isLow ? 'var(--error)' : 'var(--success)'}; margin-bottom: 0.25rem;">정답률: ${pct}%</div>
                <div style="font-size: 0.7rem; font-weight: 600; color: ${weaknessColor}; margin-bottom: 0.15rem;">취약도: ${weakness.weaknessScore}점 (${weaknessLabel})</div>
                <div style="font-size: 0.68rem; color: var(--text-secondary);">평균: ${avgTime}초</div>
            `;
            statsContainer.appendChild(box);
        }

        // [신규] 누적 답안 이력 비교 단독 카드로 하단에 독립 배치
        const compareContainer = document.getElementById('recurrence-compare-card-container');
        if (compareContainer) {
            compareContainer.innerHTML = '';
            const comparePanel = document.createElement('div');
            comparePanel.className = 'result-summary-card';
            comparePanel.style.padding = '0.7rem 0.8rem';
            comparePanel.style.marginBottom = '0';
            comparePanel.innerHTML = `
                <h3 style="font-family: 'Outfit', sans-serif; font-size: 0.82rem; font-weight: 700; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.3rem; color: var(--text-primary);">
                    <i data-lucide="git-branch" style="color: var(--accent-violet); width: 14px; height: 14px;"></i> 누적 답안 이력 비교
                </h3>
                <div id="recurrence-inline-compare-box" style="font-size: 0.72rem; color: var(--text-secondary); line-height: 1.4;">
                    왼쪽 OMR 보드의 문제를 클릭하면, 해당 문항의 최근 회차별 누적 정오(맞춤/틀림) 이력이 여기에 상세히 분석 출력됩니다.
                </div>
            `;
            compareContainer.appendChild(comparePanel);
        }
    }

    // 5. 오답 재발 추적 카드 렌더링
    const recCard = document.getElementById('recurrence-tracking-card');
    if (recCard) {
        const pastAttemptList = buildPastAttemptListForCard(result, 10);
        if (recurrenceInsight.previousAttemptCount > 0 || pastAttemptList.length > 0) {
            recCard.style.display = 'block';
            const recurringWrongHtml = recurrenceInsight.recurringWrong.length > 0
                ? recurrenceInsight.recurringWrong
                    .sort((a, b) => a - b)
                    .map(qNum => `<button type="button" class="yearly-recurring-chip" onclick="clickRecurrenceChip(${qNum})" style="display:inline-flex; align-items:center; padding:0.18rem 0.5rem; border-radius:999px; font-size:0.72rem; border:1px solid rgba(239,68,68,0.28); background:rgba(239,68,68,0.10); color:#fca5a5; margin-right:0.35rem; margin-bottom:0.35rem; cursor:pointer;">Q.${qNum}</button>`)
                    .join('')
                : '<span style="font-size:0.78rem; color: var(--text-secondary);">재발 오답은 없습니다.</span>';

            const pastAttemptHtml = pastAttemptList.length > 0
                ? pastAttemptList
                    .map(entry => `
                        <div style="display:flex; justify-content:space-between; gap:0.6rem; padding:0.34rem 0.45rem; border:1px solid rgba(255,255,255,0.06); border-radius:7px; background:rgba(255,255,255,0.02);">
                            <span style="font-size:0.72rem; color:var(--text-secondary);">${formatDate(entry.createdAt)} · ${entry.source}</span>
                            <span style="font-size:0.72rem; color:var(--text-primary); font-weight:600;">${entry.summary}</span>
                        </div>
                    `)
                    .join('')
                : '<span style="font-size:0.76rem; color: var(--text-secondary);">표시할 과거 풀이 이력이 없습니다.</span>';

            recCard.innerHTML = `
                <h3 style="font-size: 0.85rem; font-weight: 700; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.3rem; color: #f97316; margin-top: 0;">
                    <i data-lucide="repeat" style="width: 14px; height: 14px;"></i> 오답 재발 추적 (과거 기출이력 비교)
                </h3>
                <div style="background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.04); border-radius: 8px; padding: 0.5rem;">
                    <div style="font-size: 0.72rem; color: var(--text-secondary); margin-bottom: 0.35rem;">재발 오답 리스트 (클릭 시 누적 오답 비교)</div>
                    <div>${recurringWrongHtml}</div>
                </div>
                <div style="background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.04); border-radius: 8px; padding: 0.5rem; margin-top:0.45rem;">
                    <div style="font-size: 0.72rem; color: var(--text-secondary); margin-bottom: 0.35rem;">기존 풀이 이력 리스트 (최대 10개)</div>
                    <div style="display:flex; flex-direction:column; gap:0.3rem;">${pastAttemptHtml}</div>
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

/**
 * [설계 의도] 문항 난이도(상/중/하/예외)를 색상이 구분된 뱃지 HTML로 반환합니다.
 * dashboard_common.js의 동명 함수와 동일한 로직이지만, 이 페이지는 그 파일을 로드하지 않아 독립적으로 둡니다.
 */
function getDifficultyBadgeHtml(difficulty) {
    const d = difficulty || '중';
    const colors = {
        '상': { bg: 'rgba(239, 68, 68, 0.15)', border: 'rgba(239, 68, 68, 0.4)', color: '#f87171' },
        '중': { bg: 'rgba(251, 191, 36, 0.15)', border: 'rgba(251, 191, 36, 0.4)', color: '#fbbf24' },
        '하': { bg: 'rgba(52, 211, 153, 0.15)', border: 'rgba(52, 211, 153, 0.4)', color: '#34d399' },
        '예외': { bg: 'rgba(148, 163, 184, 0.15)', border: 'rgba(148, 163, 184, 0.4)', color: '#94a3b8' }
    };
    const c = colors[d] || colors['중'];
    return `<span style="background:${c.bg}; border:1px solid ${c.border}; color:${c.color}; padding:0.15rem 0.35rem; border-radius:4px; font-size:0.65rem; font-weight:800;">난이도 ${d}</span>`;
}

function renderQuestionDetailHtml(item, detail, q) {
    const box = document.getElementById('yearly-wrong-detail-box');
    currentDetailCtx = { item, detail, q };
    // [설계 의도] 최상위 let 변수는 window에 자동으로 붙지 않아, quick_add.js의
    // "드래그 선택 → 단어장 추가" 유틸이 window.currentDetailCtx를 참조해 정확한
    // 연도/문항번호 출처를 뽑아낼 수 있도록 명시적으로 window에도 노출합니다.
    window.currentDetailCtx = currentDetailCtx;
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
        <div class="yearly-wrong-detail-card" data-question-num="${detail.question_num}" style="background:rgba(255,255,255,0.01); border:1px solid rgba(255,255,255,0.04); border-radius:10px; padding:1rem; min-height:100%;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:0.4rem;">
                <span style="font-weight:700; font-size:0.88rem;">Q.${detail.question_num} 상세 보기</span>
                <div style="display:flex; align-items:center; gap:0.4rem;">
                    <span class="badge ${rangeInfo.code}" style="font-size:0.65rem; padding:0.15rem 0.35rem; border-radius:4px; font-weight:700; background: ${getSubjectGradient(rangeInfo.code)}; color: #ffffff; border:none;">${rangeInfo.name}</span>
                    ${getDifficultyBadgeHtml(q.difficulty)}
                    <button onclick="startEditYearlyQuestion('${q.id}')" style="background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.35); color: #c084fc; padding: 0.2rem 0.55rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700; cursor: pointer; font-family: inherit;">✏️ 수정</button>
                </div>
            </div>
            <div style="font-size:0.88rem; line-height:1.45; color:var(--text-primary); white-space:pre-wrap; margin-bottom:0.8rem;">${q.question}</div>
            
            <div style="margin-bottom:0.8rem;">${optionsHtml}</div>
            
            <details style="background:rgba(16,185,129,0.02); border:1px solid rgba(16,185,129,0.08); border-radius:8px; padding:0.6rem 0.8rem; font-size:0.8rem; line-height:1.45; margin-bottom:0.6rem;">
                <summary style="color:#c084fc; font-weight:700; display:flex; align-items:center; gap:0.25rem; cursor:pointer; user-select:none; outline:none;">
                    <i data-lucide="book-open" style="width:13px; height:13px;"></i> 정답 및 상세 해설 보기 (클릭하여 열기)
                    <i data-lucide="chevron-down" style="width:12px; height:12px; margin-left:auto;"></i>
                </summary>
                <div style="margin-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.4rem;">
                    <div style="color:var(--text-secondary); margin-bottom:0.3rem; white-space:pre-wrap;">${q.explanation || '등록된 상세 해설이 없습니다.'}</div>
                    <div class="ai-explain-section" style="margin-top:0.5rem; padding-top:0.5rem; border-top:1px dashed rgba(139,92,246,0.18);">
                        <button class="ai-explain-btn" id="ai-explain-trigger-${q.id}" onclick="fetchAiExplanation('${q.id}', 'ai-explain-box-${q.id}', false)" style="background:none; border:none; color:#a78bfa; font-size:0.72rem; font-weight:700; cursor:pointer; padding:0; font-family:inherit;">${q.ai_explanation ? '📖 AI 해설 보기' : '✨ AI 해설 생성'}</button>
                        <div id="ai-explain-box-${q.id}" class="ai-explain-box" style="margin-top:0.4rem;"></div>
                    </div>
                    ${lawBtnHtml}
                </div>
            </details>

            ${imageHtml}
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

/**
 * [설계 의도] 순수 텍스트를 contenteditable 리치 에디터에 표시 가능한 HTML로 변환합니다.
 * 이미 HTML 마크업(과거에 이미지가 붙여넣기된 해설 등)이라면 그대로 두고, 아니면 escape 후
 * 줄바꿈만 <br>로 바꿔줍니다. dashboard_common.js의 동명 함수와 동일한 로직입니다.
 */
function toEditableHtml(raw) {
    if (!raw) return '';
    const looksLikeHtml = /<[a-z][\s\S]*>/i.test(raw);
    if (looksLikeHtml) return raw;

    const escaped = raw
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    return escaped.replace(/\n/g, '<br>');
}

function insertHtmlAtCursor(html) {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;

    const range = sel.getRangeAt(0);
    range.deleteContents();
    const fragment = range.createContextualFragment(html);
    const lastNode = fragment.lastChild;
    range.insertNode(fragment);

    if (lastNode) {
        range.setStartAfter(lastNode);
        range.setEndAfter(lastNode);
        sel.removeAllRanges();
        sel.addRange(range);
    }
}

function insertTextAtCursor(text) {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;

    const range = sel.getRangeAt(0);
    range.deleteContents();
    const textNode = document.createTextNode(text);
    range.insertNode(textNode);
    range.setStartAfter(textNode);
    range.setEndAfter(textNode);
    sel.removeAllRanges();
    sel.addRange(range);
}

/**
 * [설계 의도] 리치 에디터에 붙여넣을 때 클립보드에 이미지가 있으면 base64 <img>로 삽입하고,
 * 없으면 서식이 제거된 순수 텍스트만 삽입합니다. dashboard_common.js의 handleRichEditorPaste와
 * 동일하되, 이 페이지에는 아코디언이 없어 높이 재조정 호출만 생략했습니다.
 */
function handleRichEditorPaste(event) {
    event.preventDefault();
    const clipboardData = event.clipboardData;
    const items = clipboardData ? clipboardData.items : null;

    if (items) {
        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            if (item.kind === 'file' && item.type && item.type.startsWith('image/')) {
                const file = item.getAsFile();
                if (!file) continue;

                const reader = new FileReader();
                reader.onload = () => {
                    insertHtmlAtCursor(`<img src="${reader.result}" style="max-width: 100%; border-radius: 4px; margin: 0.4rem 0; display: block;">`);
                };
                reader.readAsDataURL(file);
                return;
            }
        }
    }

    const text = clipboardData ? clipboardData.getData('text/plain') : '';
    if (text) insertTextAtCursor(text);
}

/**
 * [설계 의도] 브라우저가 빈 contenteditable에 남기는 잔여 <br> 등으로 인해
 * 실제 텍스트나 이미지가 전혀 없는데도 값이 있는 것처럼 처리되지 않도록 정규화합니다.
 */
function getRichEditorValue(elId) {
    const el = document.getElementById(elId);
    if (!el) return '';

    const hasImage = el.querySelector('img') !== null;
    const hasText = el.textContent.trim().length > 0;
    return (hasImage || hasText) ? el.innerHTML : '';
}

/**
 * [설계 의도] "선택 문항 상세" 탭에서도 대시보드와 동일하게 문항을 직접 수정할 수 있게 합니다.
 * 질문/해설은 이미지 붙여넣기가 가능한 리치 에디터로, 보기와 정답은 입력창/체크박스로 편집합니다.
 */
function startEditYearlyQuestion(qId) {
    const box = document.getElementById('yearly-wrong-detail-box');
    if (!box || !currentDetailCtx || currentDetailCtx.q.id !== qId) return;

    const q = currentDetailCtx.q;

    const numSymbols = ["①", "②", "③", "④", "⑤"];
    const options = q.options && q.options.length > 0 ? q.options : ["", "", "", ""];
    const ansArr = Array.isArray(q.answer) ? q.answer.map(Number) : (q.answer ? [Number(q.answer)] : []);

    let optionsHtml = '';
    options.forEach((opt, oIdx) => {
        const sym = numSymbols[oIdx] || `${oIdx + 1}.`;
        const escapedOpt = (opt || '').replace(/"/g, '&quot;');
        optionsHtml += `
            <div style="display:flex; align-items:center; gap:0.5rem;">
                <span style="color:#8b5cf6; font-weight:700; font-size:0.85rem; width:18px; flex-shrink:0; text-align:center;">${sym}</span>
                <input type="text" class="yearly-edit-opt-input" value="${escapedOpt}" style="flex-grow:1; background:rgba(15,23,42,0.6); border:1px solid rgba(139,92,246,0.25); color:#ffffff; padding:0.4rem 0.5rem; border-radius:4px; font-size:0.8rem; outline:none; font-family:inherit;" />
            </div>
        `;
    });

    const answerChecksHtml = [1, 2, 3, 4].map(n => {
        const sym = numSymbols[n - 1];
        const checked = ansArr.includes(n) ? 'checked' : '';
        return `
            <label style="display:flex; align-items:center; gap:0.3rem; cursor:pointer; font-size:0.8rem; color:#ffffff;">
                <input type="checkbox" class="yearly-edit-answer-chk" value="${n}" ${checked} style="accent-color:#8b5cf6; width:14px; height:14px; cursor:pointer;">
                ${sym}번
            </label>
        `;
    }).join('');

    box.innerHTML = `
        <div style="background:rgba(255,255,255,0.01); border:1px solid rgba(255,255,255,0.04); border-radius:10px; padding:1rem; display:flex; flex-direction:column; gap:0.8rem;">
            <div style="font-weight:700; font-size:0.85rem; color:#c084fc;">✏️ Q.${q.question_num} 문항 수정</div>
            <div>
                <label style="font-size:0.76rem; color:#a78bfa; font-weight:700; display:block; margin-bottom:0.3rem;">❓ 질문 본문</label>
                <div id="yearly-edit-q-text" class="rich-editor" contenteditable="true" onpaste="handleRichEditorPaste(event)" style="width:100%; min-height:110px; max-height:360px; overflow-y:auto; background:rgba(15,23,42,0.6); border:1px solid rgba(139,92,246,0.3); color:#ffffff; padding:0.55rem; border-radius:6px; font-size:0.82rem; line-height:1.5; outline:none; white-space:pre-wrap;">${toEditableHtml(q.question)}</div>
                <div style="font-size:0.68rem; color:var(--text-muted); margin-top:0.25rem;">텍스트와 이미지를 함께 붙여넣을 수 있습니다 (Ctrl+V)</div>
            </div>
            <div>
                <label style="font-size:0.76rem; color:#a78bfa; font-weight:700; display:block; margin-bottom:0.4rem;">📋 보기(선택지)</label>
                <div style="display:flex; flex-direction:column; gap:0.4rem;">${optionsHtml}</div>
            </div>
            <div>
                <label style="font-size:0.76rem; color:#a78bfa; font-weight:700; display:block; margin-bottom:0.3rem;">🔑 정답 (복수 선택 가능)</label>
                <div style="display:flex; gap:0.9rem; flex-wrap:wrap; padding:0.45rem; background:rgba(15,23,42,0.6); border:1px solid rgba(139,92,246,0.2); border-radius:4px;">${answerChecksHtml}</div>
            </div>
            <div>
                <label style="font-size:0.76rem; color:#a78bfa; font-weight:700; display:block; margin-bottom:0.3rem;">🎯 난이도</label>
                <select id="yearly-edit-q-difficulty" style="background:rgba(15,23,42,0.6); border:1px solid rgba(139,92,246,0.3); color:#ffffff; padding:0.45rem 0.6rem; border-radius:6px; font-size:0.8rem; outline:none; font-family:inherit;">
                    ${['상', '중', '하', '예외'].map(d => `<option value="${d}" ${(q.difficulty || '중') === d ? 'selected' : ''}>${d}</option>`).join('')}
                </select>
            </div>
            <div>
                <label style="font-size:0.76rem; color:#a78bfa; font-weight:700; display:block; margin-bottom:0.3rem;">📝 해설</label>
                <div id="yearly-edit-q-explanation" class="rich-editor" contenteditable="true" onpaste="handleRichEditorPaste(event)" style="width:100%; min-height:130px; max-height:480px; overflow-y:auto; background:rgba(15,23,42,0.6); border:1px solid rgba(139,92,246,0.3); color:#ffffff; padding:0.55rem; border-radius:6px; font-size:0.82rem; line-height:1.5; outline:none; white-space:pre-wrap;">${toEditableHtml(q.explanation || '')}</div>
                <div style="font-size:0.68rem; color:var(--text-muted); margin-top:0.25rem;">텍스트와 이미지를 함께 붙여넣을 수 있습니다 (Ctrl+V)</div>
            </div>
            <div>
                <label style="font-size:0.76rem; color:#a78bfa; font-weight:700; display:block; margin-bottom:0.4rem;">🖼️ 시험지 원본 이미지</label>
                <div style="display:flex; align-items:flex-start; gap:0.8rem; flex-wrap:wrap;">
                    <div id="yearly-edit-img-preview-wrap" style="min-width:110px; min-height:80px; display:flex; align-items:center; justify-content:center;">
                        <img id="yearly-edit-img-preview" src="../images/${q.id}.png?t=${Date.now()}" alt="현재 이미지" style="max-width:200px; max-height:150px; border-radius:6px; border:1px solid rgba(139,92,246,0.3);" onerror="this.style.display='none'; document.getElementById('yearly-edit-img-empty').style.display='block';">
                        <div id="yearly-edit-img-empty" style="display:none; font-size:0.74rem; color:var(--text-muted);">등록된 이미지가 없습니다.</div>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:0.4rem;">
                        <input type="file" accept="image/png" id="yearly-edit-img-file" onchange="onYearlyEditImageFileSelected(event)" style="font-size:0.76rem; color:#ffffff; max-width:200px;">
                        <span style="font-size:0.66rem; color:var(--text-muted);">PNG 파일만 지원됩니다</span>
                        <label style="display:flex; align-items:center; gap:0.35rem; font-size:0.74rem; color:var(--text-secondary); cursor:pointer;">
                            <input type="checkbox" id="yearly-edit-img-remove" onchange="onYearlyEditImageRemoveToggled('${q.id}')" style="accent-color:#8b5cf6; width:13px; height:13px; cursor:pointer;">
                            이미지 삭제
                        </label>
                    </div>
                </div>
            </div>
            <div style="display:flex; gap:0.5rem; justify-content:flex-end; margin-top:0.3rem;">
                <button onclick="saveYearlyQuestionEdit('${q.id}')" style="background:#8b5cf6; border:none; color:#ffffff; padding:0.4rem 1rem; border-radius:4px; font-size:0.8rem; font-weight:700; cursor:pointer; font-family:inherit;">💾 저장</button>
                <button onclick="cancelYearlyQuestionEdit()" style="background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15); color:var(--text-secondary); padding:0.4rem 1rem; border-radius:4px; font-size:0.8rem; cursor:pointer; font-family:inherit;">취소</button>
            </div>
        </div>
    `;

    window.yearlyPendingImageEdit = { dataUrl: null, remove: false };
}

/**
 * [설계 의도] 새 이미지 파일을 base64로 읽어 저장 시점까지 보관하고 미리보기를 즉시 교체합니다.
 */
function onYearlyEditImageFileSelected(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    if (file.type !== 'image/png') {
        alert("PNG 형식의 이미지 파일만 첨부할 수 있습니다.");
        event.target.value = '';
        return;
    }

    const reader = new FileReader();
    reader.onload = () => {
        window.yearlyPendingImageEdit = { dataUrl: reader.result, remove: false };

        const removeChk = document.getElementById('yearly-edit-img-remove');
        if (removeChk) removeChk.checked = false;

        const img = document.getElementById('yearly-edit-img-preview');
        const empty = document.getElementById('yearly-edit-img-empty');
        if (img) {
            img.onerror = null;
            img.src = reader.result;
            img.style.display = 'block';
        }
        if (empty) empty.style.display = 'none';
    };
    reader.readAsDataURL(file);
}

/**
 * [설계 의도] "이미지 삭제" 체크 상태에 따라 저장 시 삭제 여부를 결정하고,
 * 체크 해제 시에는 서버에 남아있는 기존 이미지를 다시 미리보기로 복원합니다.
 */
function onYearlyEditImageRemoveToggled(qId) {
    const removeChk = document.getElementById('yearly-edit-img-remove');
    const isRemove = removeChk ? removeChk.checked : false;

    window.yearlyPendingImageEdit = window.yearlyPendingImageEdit || { dataUrl: null, remove: false };
    window.yearlyPendingImageEdit.remove = isRemove;
    if (isRemove) window.yearlyPendingImageEdit.dataUrl = null;

    const fileInput = document.getElementById('yearly-edit-img-file');
    if (fileInput) fileInput.value = '';

    const img = document.getElementById('yearly-edit-img-preview');
    const empty = document.getElementById('yearly-edit-img-empty');
    if (!img) return;

    if (isRemove) {
        img.style.display = 'none';
        if (empty) empty.style.display = 'block';
    } else {
        img.onerror = () => { img.style.display = 'none'; if (empty) empty.style.display = 'block'; };
        img.style.display = 'block';
        if (empty) empty.style.display = 'none';
        img.src = `../images/${qId}.png?t=${Date.now()}`;
    }
}

/**
 * [설계 의도] 수정한 질문/보기/정답/해설을 /api/question/update로 저장하고,
 * 이미지 변경이 있으면 /api/question/upload-image로 별도 저장한 뒤 상세 보기로 복귀합니다.
 */
function saveYearlyQuestionEdit(qId) {
    if (!currentDetailCtx || currentDetailCtx.q.id !== qId) return;
    const q = currentDetailCtx.q;

    const questionVal = getRichEditorValue('yearly-edit-q-text');
    const optionInputs = document.querySelectorAll('.yearly-edit-opt-input');
    const optionsVal = Array.from(optionInputs).map(input => input.value);
    const answerChecks = document.querySelectorAll('.yearly-edit-answer-chk:checked');
    const answerVal = Array.from(answerChecks).map(chk => parseInt(chk.value));
    const explanationVal = getRichEditorValue('yearly-edit-q-explanation');
    const difficultySelect = document.getElementById('yearly-edit-q-difficulty');
    const difficultyVal = difficultySelect ? difficultySelect.value : '중';

    if (!questionVal.trim() || optionsVal.some(o => !o.trim())) {
        alert("질문과 모든 보기를 입력해야 합니다.");
        return;
    }

    fetch('/api/question/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: qId, question: questionVal, options: optionsVal, answer: answerVal, explanation: explanationVal, difficulty: difficultyVal })
    })
        .then(response => {
            if (!response.ok) throw new Error("HTTP error " + response.status);
            return response.json();
        })
        .then(result => {
            if (!result.success) {
                alert("저장 실패: " + (result.message || '알 수 없는 오류'));
                return Promise.reject(null);
            }

            q.question = questionVal;
            q.options = optionsVal;
            q.answer = answerVal;
            q.explanation = explanationVal;
            q.difficulty = difficultyVal;

            const imageState = window.yearlyPendingImageEdit || { dataUrl: null, remove: false };
            if (imageState.dataUrl) {
                return fetch('/api/question/upload-image', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: qId, image_data: imageState.dataUrl })
                }).then(r => r.json());
            } else if (imageState.remove) {
                return fetch('/api/question/upload-image', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: qId, delete: true })
                }).then(r => r.json());
            }
            return { success: true };
        })
        .then(imgResult => {
            if (imgResult && imgResult.success === false) {
                alert("문항 내용은 저장되었으나 이미지 저장에 실패했습니다: " + (imgResult.message || ''));
            } else {
                alert("문항이 성공적으로 저장되었습니다.");
            }
            window.yearlyPendingImageEdit = null;
            renderQuestionDetailHtml(currentDetailCtx.item, currentDetailCtx.detail, q);
        })
        .catch(err => {
            if (err !== null) {
                console.error(err);
                alert("서버와 통신 중 오류가 발생하여 저장에 실패했습니다.");
            }
        });
}

/**
 * [설계 의도] 편집을 취소하고 원래 상세 보기 화면으로 되돌립니다.
 */
function cancelYearlyQuestionEdit() {
    if (!currentDetailCtx) return;
    window.yearlyPendingImageEdit = null;
    renderQuestionDetailHtml(currentDetailCtx.item, currentDetailCtx.detail, currentDetailCtx.q);
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
            <div class="yearly-wrong-question-card" data-question-num="${d.question_num}" style="background:rgba(255,255,255,0.015); border:1px solid rgba(255,255,255,0.05); border-radius:10px; padding:0.85rem; box-shadow:0 4px 12px rgba(0,0,0,0.1); margin-bottom: 0.8rem;">
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
    const box = document.getElementById('recurrence-inline-compare-box') || document.getElementById('yearly-recurrence-compare-box');
    if (!box) return;
    box.innerHTML = '';
    box.style.display = 'none';
    const qNum = Number(detail.question_num);
    const qKey = `${item.exam_year}_${qNum}`;

    const parseJsonSafely = (value, fallback) => {
        if (value === null || value === undefined) return fallback;
        if (typeof value === 'object') return value;
        if (typeof value === 'string' && value.trim()) {
            try {
                return JSON.parse(value);
            } catch (e) {
                return fallback;
            }
        }
        return fallback;
    };

    const toAnswerText = (ans) => {
        if (Array.isArray(ans)) {
            if (ans.length === 0) return '-';
            return ans.map(v => Number(v)).filter(v => !Number.isNaN(v)).join(', ');
        }
        if (ans === null || ans === undefined || ans === '') return '-';
        const n = Number(ans);
        return Number.isNaN(n) ? String(ans) : String(n);
    };

    const currentDateTs = new Date(item.created_at || 0).getTime();
    const currentId = item.id;
    const records = [];

    // 1) 모의고사 이력(기출) 수집
    const yearlyHistory = parseJsonSafely(localStorage.getItem('selected_history_list'), []);
    yearlyHistory
        .filter(hist => String(hist.exam_year) === String(item.exam_year))
        .forEach(hist => {
            const histDetails = parseJsonSafely(hist.details, []);
            const match = Array.isArray(histDetails)
                ? histDetails.find(x => Number(x.question_num) === qNum)
                : null;
            if (!match) return;

            const dateTs = new Date(hist.created_at || 0).getTime();
            records.push({
                source: '모의고사',
                date: hist.created_at || '',
                dateTs,
                userAnswer: Array.isArray(match.user_answer) ? match.user_answer : [match.user_answer],
                isCorrect: !!match.is_correct,
                isCurrent: String(hist.id) === String(currentId)
            });
        });

    // 2) 대시보드(일반 퀴즈) 이력 수집
    const quizLogs = parseJsonSafely(localStorage.getItem('selected_quiz_logs'), []);
    quizLogs.forEach(log => {
        const logDateTs = new Date(log && log.created_at ? log.created_at : 0).getTime();
        if (Number.isNaN(logDateTs)) return;

        const d = parseJsonSafely(log && log.details, null);
        if (!d) return;

        // details 포맷 1: { q_id, user_choice/user_answer, is_correct }
        if (typeof d.q_id === 'string') {
            if (d.q_id !== qKey) return;

            const userAns = Array.isArray(d.user_answer)
                ? d.user_answer
                : (Array.isArray(d.user_choice) ? d.user_choice : [d.user_answer || d.user_choice]);

            const isCorrect = (d.is_correct !== undefined)
                ? !!d.is_correct
                : Number(log.correct_count || 0) > 0;

            records.push({
                source: '대시보드',
                date: log.created_at || '',
                dateTs: logDateTs,
                userAnswer: userAns,
                isCorrect,
                isCurrent: false
            });
            return;
        }

        // details 포맷 2: { correct: [...], wrong: [...] }
        const correctList = Array.isArray(d.correct) ? d.correct.map(String) : [];
        const wrongList = Array.isArray(d.wrong) ? d.wrong.map(String) : [];
        if (!correctList.includes(qKey) && !wrongList.includes(qKey)) return;

        records.push({
            source: '대시보드',
            date: log.created_at || '',
            dateTs: logDateTs,
            userAnswer: [],
            isCorrect: correctList.includes(qKey),
            isCurrent: false
        });
    });

    // 시간순 정렬 (과거 -> 현재)
    records.sort((a, b) => a.dateTs - b.dateTs);

    // 현재 항목만 존재할 경우에도 안내 카드를 노출해 사용자가 히스토리 부재를 인지할 수 있도록 합니다.
    box.style.display = 'block';

    const formatDateToMMDD = (dateStr) => {
        if (!dateStr) return '-';
        try {
            const d = new Date(dateStr);
            const mm = d.getMonth() + 1;
            const dd = d.getDate();
            return `${mm}/${dd}`;
        } catch (e) {
            return '-';
        }
    };

    const formatFullDateTime = (dateStr) => {
        if (!dateStr) return '-';
        try {
            const d = new Date(dateStr);
            const yyyy = d.getFullYear();
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const dd = String(d.getDate()).padStart(2, '0');
            const hh = String(d.getHours()).padStart(2, '0');
            const min = String(d.getMinutes()).padStart(2, '0');
            const ss = String(d.getSeconds()).padStart(2, '0');
            return `${yyyy}-${mm}-${dd} ${hh}:${min}:${ss}`;
        } catch (e) {
            return '-';
        }
    };

    const cellsHtml = records.map(r => {
        const isCorrect = r.isCorrect;
        const day = r.date ? formatDateToMMDD(r.date) : '-';
        const answerText = toAnswerText(r.userAnswer);

        // OMR 보드 스타일 차용
        let cellBg = isCorrect ? 'rgba(16, 185, 129, 0.04)' : 'rgba(239, 68, 68, 0.04)';
        let cellBorder = isCorrect ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(239, 68, 68, 0.25)';
        let textCol = isCorrect ? '#34d399' : '#f87171';

        // 현재 풀이 항목 스타일 강조
        if (r.isCurrent) {
            cellBg = 'rgba(139, 92, 246, 0.12)';
            cellBorder = '1.5px solid #a78bfa';
        }

        const fullTime = r.date ? formatFullDateTime(r.date) : '-';
        const tooltip = `[${r.source}]${r.isCurrent ? ' (현재 풀이)' : ''}\n풀이 시각: ${fullTime}\n결과: ${isCorrect ? '정답' : '오답'}`;

        return `
            <div title="${tooltip}" style="background: ${cellBg}; border: ${cellBorder}; border-radius: 4px; padding: 0.2rem 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0; min-height: 34px; width: 40px; flex: 0 0 40px; cursor: default; transition: transform 0.15s;">
                <span style="font-size: 0.52rem; color: var(--text-secondary); font-family: monospace; font-weight: 600;">${day}</span>
                <span style="font-size: 0.62rem; font-weight: 700; color: ${textCol};">${answerText}</span>
            </div>
        `;
    }).join('');

    const contentHtml = records.length > 0 ? `
        <div style="display: flex; gap: 0.25rem; overflow-x: auto; padding: 0.2rem 0; max-width: 100%;">
            ${cellsHtml}
        </div>
    ` : `<div style="font-size: 0.7rem; color: var(--text-secondary); padding: 0.5rem 0;">과거 풀이 이력이 없습니다.</div>`;

    box.innerHTML = `
        <div style="background: rgba(255, 255, 255, 0.015); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 8px; padding: 0.45rem; margin-top: 0.25rem;">
            ${contentHtml}
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

// 오답 재발 카드용 과거 풀이 목록(모의고사 + 대시보드) 생성
function buildPastAttemptListForCard(item, maxCount = 10) {
    const parseJsonSafely = (value, fallback) => {
        if (value === null || value === undefined) return fallback;
        if (typeof value === 'object') return value;
        if (typeof value === 'string' && value.trim()) {
            try {
                return JSON.parse(value);
            } catch (e) {
                return fallback;
            }
        }
        return fallback;
    };

    const currentId = String(item.id || '');
    const currentDateTs = new Date(item.created_at || 0).getTime();
    const list = [];

    const historyList = parseJsonSafely(localStorage.getItem('selected_history_list'), []);
    historyList.forEach(hist => {
        if (String(hist.id || '') === currentId) return;

        const ts = new Date(hist && hist.created_at ? hist.created_at : 0).getTime();
        if (Number.isNaN(ts) || ts >= currentDateTs) return;

        const score = Number(hist.score || 0);
        const correct = Number(hist.correct_count || 0);
        const total = Number(hist.total_questions || 0);

        list.push({
            ts,
            createdAt: hist.created_at || '',
            source: '모의고사',
            summary: `${correct}/${total} · ${score.toFixed(1)}점`
        });
    });

    const quizLogs = parseJsonSafely(localStorage.getItem('selected_quiz_logs'), []);
    quizLogs.forEach(log => {
        const ts = new Date(log && log.created_at ? log.created_at : 0).getTime();
        if (Number.isNaN(ts) || ts >= currentDateTs) return;

        const detail = parseJsonSafely(log && log.details, null);
        if (!detail) return;

        let isExamHistoryLike = false;

        if (typeof detail.q_id === 'string') {
            isExamHistoryLike = /^\d{4}_\d+$/.test(detail.q_id);
        }

        if (!isExamHistoryLike) {
            const correctList = Array.isArray(detail.correct) ? detail.correct.map(String) : [];
            const wrongList = Array.isArray(detail.wrong) ? detail.wrong.map(String) : [];
            const merged = correctList.concat(wrongList);
            isExamHistoryLike = merged.some(key => /^\d{4}_\d+$/.test(String(key)));
        }

        if (!isExamHistoryLike) return;

        const totalQuestions = Number(log.total_questions || 0);
        const correctCount = Number(log.correct_count || 0);
        const subject = (log.subject || '대시보드').toString();

        list.push({
            ts,
            createdAt: log.created_at || '',
            source: '대시보드',
            summary: `${subject} ${correctCount}/${totalQuestions}`
        });
    });

    list.sort((a, b) => b.ts - a.ts);
    return list.slice(0, Math.max(1, maxCount));
}

// 오답 재발 정보 수치 분석 헬퍼
function getYearlyWrongRecurrenceInsight(item, details) {
    const parseJsonSafely = (value, fallback) => {
        if (value === null || value === undefined) return fallback;
        if (typeof value === 'object') return value;
        if (typeof value === 'string' && value.trim()) {
            try {
                return JSON.parse(value);
            } catch (e) {
                return fallback;
            }
        }
        return fallback;
    };

    const historyList = parseJsonSafely(localStorage.getItem('selected_history_list'), []);
    const quizLogs = parseJsonSafely(localStorage.getItem('selected_quiz_logs'), []);

    const currentId = item.id;
    const currentYear = item.exam_year;
    const currentDateTs = new Date(item.created_at || 0).getTime();

    const prevAttempts = historyList
        .filter(h => String(h.id) !== String(currentId) && String(h.exam_year) === String(currentYear))
        .filter(h => {
            const ts = new Date(h.created_at || 0).getTime();
            return !Number.isNaN(ts) && ts < currentDateTs;
        })
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    const result = {
        previousAttemptCount: prevAttempts.length,
        currentWrongCount: details.filter(d => !d.is_correct).length,
        recurringWrong: [],
        recurrenceRate: 0,
        improvedCount: 0,
        recurrenceBySubject: { 'PM': 0, 'SE': 0, 'DB': 0, 'SA': 0, 'SC': 0 }
    };

    const prevWrongKeySet = new Set();

    // 1) 과거 모의고사 오답 키 누적
    prevAttempts.forEach(hist => {
        const histDetails = parseJsonSafely(hist.details, []);
        if (!Array.isArray(histDetails)) return;
        histDetails.forEach(d => {
            if (!d || d.is_correct) return;
            const qNum = Number(d.question_num);
            if (Number.isNaN(qNum)) return;
            prevWrongKeySet.add(`${currentYear}_${qNum}`);
        });
    });

    // 2) 과거 대시보드 로그 오답 키 누적
    quizLogs.forEach(log => {
        const ts = new Date(log && log.created_at ? log.created_at : 0).getTime();
        if (Number.isNaN(ts) || ts >= currentDateTs) return;

        const d = parseJsonSafely(log && log.details, null);
        if (!d) return;

        if (typeof d.q_id === 'string') {
            if (d.q_id.startsWith(`${currentYear}_`) && d.is_correct === false) {
                prevWrongKeySet.add(d.q_id);
            }
            return;
        }

        const wrongList = Array.isArray(d.wrong) ? d.wrong.map(String) : [];
        wrongList.forEach(key => {
            if (key.startsWith(`${currentYear}_`)) {
                prevWrongKeySet.add(key);
            }
        });
    });

    const pastQuizLogsCount = quizLogs.filter(log => {
        const ts = new Date(log && log.created_at ? log.created_at : 0).getTime();
        return !Number.isNaN(ts) && ts < currentDateTs;
    }).length;
    result.previousAttemptCount += pastQuizLogsCount;

    const currentWrongs = details.filter(d => !d.is_correct).map(d => Number(d.question_num));
    const currentCorrects = details.filter(d => d.is_correct).map(d => Number(d.question_num));

    currentWrongs.forEach(qNum => {
        const key = `${currentYear}_${qNum}`;
        if (!prevWrongKeySet.has(key)) return;
        result.recurringWrong.push(qNum);
        const code = getSubjectInfo(qNum).code;
        if (result.recurrenceBySubject[code] !== undefined) {
            result.recurrenceBySubject[code]++;
        }
    });

    currentCorrects.forEach(qNum => {
        const key = `${currentYear}_${qNum}`;
        if (prevWrongKeySet.has(key)) {
            result.improvedCount++;
        }
    });

    if (result.currentWrongCount > 0) {
        result.recurrenceRate = Math.round((result.recurringWrong.length / result.currentWrongCount) * 100);
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

async function fetchAIDiagnostics(result, forceRefresh = false) {
    const aiTargetBox = document.getElementById('ai-diagnose-card');
    if (!aiTargetBox || !result || !result.id) return;

    const loaderId = 'ai-loading-status';
    if (document.getElementById(loaderId)) return;

    if (forceRefresh) {
        aiTargetBox.innerHTML = '';
    }

    const loaderHtml = document.createElement('div');
    loaderHtml.id = loaderId;
    loaderHtml.style.cssText = 'margin-top: 0.4rem; padding-top: 0.4rem; border-top: 1px dashed rgba(139,92,246,0.18); font-size: 0.66rem; color: #a78bfa; display: flex; align-items: center; gap: 0.25rem;';
    loaderHtml.innerHTML = `
        <svg style="width:12px; height:12px; animation: spin 1s linear infinite; flex-shrink:0;" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="#a78bfa" stroke-width="4" stroke-dasharray="31.4" stroke-linecap="round" fill="none"></circle>
        </svg>
        <span>AI가 실시간 풀이 데이터 취약점을 진단 중입니다...</span>
        <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
    `;
    aiTargetBox.appendChild(loaderHtml);

    // 실시간 진행 모사 로그 가동
    const simInterval = startProgressiveLogSimulation(aiTargetBox, 'sim-logs-diagnose');

    try {
        const url = `/api/yearly-exam/ai-diagnose?id=${result.id}${forceRefresh ? '&nocache=true' : ''}`;
        const response = await fetch(url);
        const data = await response.json();

        if (simInterval) clearInterval(simInterval);
        const simBox = document.getElementById('sim-logs-diagnose');
        if (simBox) simBox.remove();

        if (data.success && data.ai_analysis) {
            const ai = data.ai_analysis;
            aiTargetBox.style.opacity = '0';
            setTimeout(() => {
                const isFallback = ai.source === 'FALLBACK_TEMPLATE';
                const aiModel = ai.ai_model || "알 수 없음";
                const logsText = (ai.logs && ai.logs.length > 0) ? ai.logs.join("\n") : "로그 정보가 없습니다.";
                const errorBadge = isFallback ? `<div style="font-size:0.58rem; color:#f87171; margin-top:0.15rem; background:rgba(248,113,113,0.08); padding:0.15rem 0.3rem; border-radius:3px; line-height: 1.3;">⚠️ 실시간 AI 연동 실패 (폴백 가동 중). 원인: ${ai.error_detail || '알 수 없음'}</div>` : '';

                aiTargetBox.innerHTML = `
                    <div style="font-weight: 700; color: #f472b6; margin-bottom: 0.2rem; font-size: 0.76rem; display: flex; align-items: center; justify-content: space-between; gap: 0.25rem; flex-wrap: wrap;">
                        <span style="display: inline-flex; align-items: center; gap: 0.25rem;">
                            <i data-lucide="sparkles" style="width:13px; height:13px; color:#f472b6;"></i> AI 맞춤형 취약점 정밀 진단
                        </span>
                        <span style="background:rgba(139, 92, 246, 0.15); color:#c084fc; border:1px solid rgba(139, 92, 246, 0.3); padding:0.05rem 0.3rem; border-radius:4px; font-size:0.58rem; font-weight:normal;">🤖 ${aiModel}</span>
                        <button onclick="refreshAIDiagnostics(${result.id})" style="background: none; border: none; color: #a78bfa; font-size: 0.62rem; cursor: pointer; display: inline-flex; align-items: center; gap: 0.15rem; padding: 0; font-weight: bold;">
                            <i data-lucide="refresh-cw" style="width:10px; height:10px;"></i> 진단 갱신
                        </button>
                    </div>
                    ${errorBadge}
                    <p style="color: var(--text-secondary); font-size: 0.7rem; line-height: 1.4; margin: 0.3rem 0 0.35rem 0;">${ai.desc}</p>
                    <div style="font-size: 0.72rem; color: var(--text-primary); line-height: 1.4; font-weight: 500; margin-bottom: 0.4rem;">💡 <b>AI 처방 가이드:</b> ${ai.recommendation}</div>
                    
                    <div style="margin-top:0.4rem; text-align:left;">
                        <details style="border:1px solid rgba(148,163,184,0.12); border-radius:6px; background:rgba(15,23,42,0.15);">
                            <summary style="font-size:0.62rem; color:#94a3b8; cursor:pointer; padding:0.2rem 0.4rem; font-weight:600; outline:none; user-select:none;">📋 AI 연동 상세 실시간 로그 보기</summary>
                            <div style="background:#0f172a; color:#38bdf8; font-family:monospace, Courier; font-size:0.62rem; padding:0.4rem 0.5rem; border-radius:0 0 6px 6px; border-top:1px solid rgba(148,163,184,0.1); white-space:pre-line; text-align:left; max-height:100px; overflow-y:auto; line-height:1.45;">${logsText}</div>
                        </details>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
                aiTargetBox.style.transition = 'opacity 0.35s ease';
                aiTargetBox.style.opacity = '1';
            }, 300);
        } else {
            loaderHtml.remove();
        }
    } catch (e) {
        if (simInterval) clearInterval(simInterval);
        const simBox = document.getElementById('sim-logs-diagnose');
        if (simBox) simBox.remove();
        loaderHtml.remove();
        console.error("AI diagnostics load error:", e);
    }
}

async function refreshAIDiagnostics(historyId) {
    if (confirm("기존의 AI 진단 캐시를 초기화하고, 실제 AI 분석을 새로 요청하시겠습니까?\n(약 3~5초 소요)")) {
        await fetchAIDiagnostics({ id: historyId }, true);
    }
}
window.refreshAIDiagnostics = refreshAIDiagnostics;

/**
 * [설계 의도] Gemini AI를 호출해 문항의 해설을 생성/갱신합니다.
 * 기존 수동 해설(explanation)은 그대로 두고, ai_explanation 캐시 컬럼만 갈아끼웁니다.
 * forceRefresh=true(해설 갱신)일 때는 API 비용 발생을 사용자에게 확인받습니다.
 */
async function fetchAiExplanation(qId, boxId, forceRefresh = false) {
    const box = document.getElementById(boxId);
    if (!box) return;

    if (forceRefresh && !confirm("기존 AI 해설을 지우고 새로 생성하시겠습니까?\n(약 3~5초 소요)")) {
        return;
    }

    box.innerHTML = `
        <div style="font-size:0.72rem; color:#a78bfa; display:flex; align-items:center; gap:0.3rem;">
            <svg style="width:12px; height:12px; animation: spin 1s linear infinite; flex-shrink:0;" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="#a78bfa" stroke-width="4" stroke-dasharray="31.4" stroke-linecap="round" fill="none"></circle>
            </svg>
            <span>AI 해설 엔진 가동 및 통신 연결 중...</span>
            <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
        </div>
    `;

    // 실시간 진행 모사 로그 가동
    const simInterval = startProgressiveLogSimulation(box, 'sim-logs-explain-' + qId);

    try {
        const url = `/api/question/ai-explain?id=${encodeURIComponent(qId)}${forceRefresh ? '&nocache=true' : ''}`;
        const response = await fetch(url);
        const data = await response.json();

        if (simInterval) clearInterval(simInterval);
        const simBox = document.getElementById('sim-logs-explain-' + qId);
        if (simBox) simBox.remove();

        if (data.success && data.ai_explanation) {
            const aiModel = data.ai_model || "알 수 없음";
            const logsText = (data.logs && data.logs.length > 0) ? data.logs.join("\n") : "로그 정보가 없습니다.";
            
            box.innerHTML = `
                <div style="font-weight:700; color:#f472b6; font-size:0.74rem; display:flex; align-items:center; justify-content:space-between; gap:0.25rem; flex-wrap:wrap; margin-bottom:0.3rem;">
                    <div style="display:flex; align-items:center; gap:0.4rem; flex-wrap:wrap;">
                        <span>✨ AI 해설</span>
                        <span style="background:rgba(139, 92, 246, 0.15); color:#c084fc; border:1px solid rgba(139, 92, 246, 0.3); padding:0.05rem 0.3rem; border-radius:4px; font-size:0.62rem; font-weight:normal;">🤖 ${aiModel}</span>
                    </div>
                    <button onclick="fetchAiExplanation('${qId}', '${boxId}', true)" style="background:none; border:none; color:#a78bfa; font-size:0.62rem; cursor:pointer; padding:0; font-family:inherit; font-weight:bold;">🔄 해설 갱신</button>
                </div>
                <p style="color:var(--text-secondary); font-size:0.78rem; line-height:1.55; white-space:pre-wrap; margin:0.35rem 0 0;">${data.ai_explanation}</p>
                <div style="margin-top:0.5rem; text-align:left;">
                    <details style="border:1px solid rgba(148,163,184,0.12); border-radius:6px; background:rgba(15,23,42,0.15);">
                        <summary style="font-size:0.65rem; color:#94a3b8; cursor:pointer; padding:0.25rem 0.5rem; font-weight:600; outline:none; user-select:none;">📋 AI 연동 상세 실시간 로그 보기</summary>
                        <div style="background:#0f172a; color:#38bdf8; font-family:monospace, Courier; font-size:0.65rem; padding:0.5rem; border-radius:0 0 6px 6px; border-top:1px solid rgba(148,163,184,0.1); white-space:pre-line; text-align:left; max-height:120px; overflow-y:auto; line-height:1.4;">${logsText}</div>
                    </details>
                </div>
            `;
            const triggerBtn = document.getElementById(`ai-explain-trigger-${qId}`);
            if (triggerBtn) triggerBtn.textContent = '📖 AI 해설 보기';
        } else {
            const logsText = (data.logs && data.logs.length > 0) ? data.logs.join("\n") : "로그 정보가 없습니다.";
            box.innerHTML = `
                <div style="font-size:0.72rem; color:#f87171; font-weight:bold; margin-bottom:0.2rem;">⚠️ AI 해설 생성 실패: ${data.error || '알 수 없는 오류'}</div>
                <div style="margin-top:0.3rem;">
                    <details open style="border:1px solid rgba(248,113,113,0.15); border-radius:6px; background:rgba(15,23,42,0.15);">
                        <summary style="font-size:0.65rem; color:#f87171; cursor:pointer; padding:0.25rem 0.5rem; font-weight:600;">📋 상세 통신 실패 로그</summary>
                        <div style="background:#0f172a; color:#f87171; font-family:monospace, Courier; font-size:0.65rem; padding:0.5rem; border-radius:0 0 6px 6px; border-top:1px solid rgba(248,113,113,0.1); white-space:pre-line; text-align:left; max-height:120px; overflow-y:auto; line-height:1.4;">${logsText}</div>
                    </details>
                </div>
            `;
        }
    } catch (e) {
        if (simInterval) clearInterval(simInterval);
        const simBox = document.getElementById('sim-logs-explain-' + qId);
        if (simBox) simBox.remove();
        box.innerHTML = `<div style="font-size:0.72rem; color:#f87171;">⚠️ 네트워크 오류로 AI 해설을 불러오지 못했습니다.</div>`;
        console.error("AI 해설 로드 오류:", e);
    }
}
window.fetchAiExplanation = fetchAiExplanation;

// 전역 바인딩
window.showLawGuideCard = showLawGuideCard;
window.closeLawGuideModal = closeLawGuideModal;
window.switchViewerTab = switchViewerTab;
window.clickRecurrenceChip = clickRecurrenceChip;
window.toggleAllTabImage = toggleAllTabImage;
window.toggleAllTabExplanation = toggleAllTabExplanation;
window.toggleDetailTabImage = toggleDetailTabImage;
window.closeResultWindow = closeResultWindow;
window.fetchAIDiagnostics = fetchAIDiagnostics;
window.startEditYearlyQuestion = startEditYearlyQuestion;
window.saveYearlyQuestionEdit = saveYearlyQuestionEdit;
window.cancelYearlyQuestionEdit = cancelYearlyQuestionEdit;
window.onYearlyEditImageFileSelected = onYearlyEditImageFileSelected;
window.onYearlyEditImageRemoveToggled = onYearlyEditImageRemoveToggled;
window.handleRichEditorPaste = handleRichEditorPaste;

// =======================================================
// [신규 기능] 문제를 풀다가 드래그 시 용어사전에 단어 추가 기능
// =======================================================
(function() {
    // 플로팅 버튼 동적 생성
    const btn = document.createElement('div');
    btn.id = 'floating-quick-add-btn';
    btn.style.position = 'absolute';
    btn.style.display = 'none';
    btn.style.zIndex = '100000';
    btn.style.background = 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)';
    btn.style.color = '#fff';
    btn.style.padding = '6px 14px';
    btn.style.borderRadius = '20px';
    btn.style.fontSize = '0.78rem';
    btn.style.cursor = 'pointer';
    btn.style.boxShadow = '0 4px 15px rgba(139, 92, 246, 0.4)';
    btn.style.border = '1px solid rgba(255,255,255,0.2)';
    btn.style.fontWeight = '600';
    btn.style.alignItems = 'center';
    btn.style.gap = '4px';
    btn.style.userSelect = 'none';
    btn.innerHTML = '✨ 단어장에 추가';
    document.body.appendChild(btn);

    // 심플한 토스트(Toast) 메시지 노출용 엘리먼트 생성
    const toast = document.createElement('div');
    toast.id = 'quick-add-toast';
    toast.style.position = 'fixed';
    toast.style.bottom = '30px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.background = 'rgba(17, 24, 39, 0.95)';
    toast.style.color = '#ffffff';
    toast.style.padding = '10px 20px';
    toast.style.borderRadius = '30px';
    toast.style.fontSize = '0.85rem';
    toast.style.fontWeight = '500';
    toast.style.zIndex = '100001';
    toast.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.3)';
    toast.style.border = '1px solid rgba(139, 92, 246, 0.2)';
    toast.style.display = 'none';
    toast.style.transition = 'opacity 0.3s ease';
    document.body.appendChild(toast);

    function showToast(msg) {
        toast.textContent = msg;
        toast.style.display = 'block';
        toast.style.opacity = '1';
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => { toast.style.display = 'none'; }, 300);
        }, 2200);
    }

    let selectedText = '';

    document.addEventListener('mouseup', function(e) {
        // 플로팅 버튼 자체를 클릭했을 때는 동작하지 않도록 예외 처리
        if (e.target.id === 'floating-quick-add-btn') return;

        const selection = window.getSelection();
        const text = selection.toString().trim();

        if (!text || text.length < 2 || text.length > 50) {
            btn.style.display = 'none';
            return;
        }

        // 특정 영역(#question-text-content 또는 .options-container 등) 내에서의 드래그만 인정
        const anchorNode = selection.anchorNode;
        if (!anchorNode) return;
        const parentElement = anchorNode.parentElement;
        if (!parentElement) return;

        const inQuestion = parentElement.closest('#question-text-content');
        const inOptions = parentElement.closest('#options-button-container');

        if (!inQuestion && !inOptions) {
            btn.style.display = 'none';
            return;
        }

        selectedText = text;

        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();

        // 플로팅 위치 설정 (선택된 단어의 상단 정중앙)
        btn.style.top = `${rect.top + window.scrollY - 38}px`;
        btn.style.left = `${rect.left + window.scrollX + (rect.width / 2) - 55}px`;
        btn.style.display = 'flex';
    });

    // 화면 아무데나 클릭 시 플로팅 닫기
    document.addEventListener('mousedown', function(e) {
        if (e.target.id !== 'floating-quick-add-btn') {
            btn.style.display = 'none';
        }
    });

    // ➕ 단어장에 추가 버튼 클릭 시 통신
    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        btn.style.display = 'none';

        if (!selectedText) return;

        // 현재 풀고 있는 문제 정보 조회
        const subjectTag = document.getElementById('current-subject-tag');
        const qNumLabel = document.getElementById('current-q-num-label');

        let rawSubject = subjectTag ? subjectTag.textContent.trim() : 'PM';
        
        // 한글 과목명 -> 데이터베이스 코드 매핑
        let subjectCode = 'PM';
        if (rawSubject.includes('소프트웨어') || rawSubject.includes('SE')) subjectCode = 'SE';
        else if (rawSubject.includes('데이터베이스') || rawSubject.includes('DB')) subjectCode = 'DB';
        else if (rawSubject.includes('시스템') || rawSubject.includes('SA')) subjectCode = 'SA';
        else if (rawSubject.includes('보안') || rawSubject.includes('SC')) subjectCode = 'SC';

        const rawSource = qNumLabel ? qNumLabel.textContent.trim() : ''; // 예: "2024년도 15번"
        
        const payload = {
            term_ko: selectedText,
            definition: "뜻을 입력해주세요.",
            subject: subjectCode,
            topic_major: "기타",
            source: rawSource ? [rawSource] : ["기출 문제 풀이 중 추가"]
        };

        fetch('/api/vocab/term', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast(`✓ [${selectedText}] 단어장에 신규 추가되었습니다.`);
                // 선택 영역 해제
                window.getSelection().removeAllRanges();
            } else {
                showToast(`⚠ 추가 실패: ${data.message || '오류 발생'}`);
            }
        })
        .catch(err => {
            console.error(err);
            showToast('⚠ 서버 연결 실패');
        });
    });
})();
