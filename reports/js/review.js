/**
 * ==========================================================================
 * [Jolly-Carson 오답 집중 복습 코어 스크립트 - review.js]
 * - 주요 기능: LocalStorage + 백엔드 DB 하이브리드 로그 취합
 *             최신 시도 결과 기준 오답 문항 자동 선별
 *             플래시카드 렌더링 및 실시간 채점 제출 연동
 *             🎮 게이미피케이션: EXP/Level 성장 시스템 + 보물상자 + 레벨업 이펙트
 * ==========================================================================
 */

// 전역 상태 관리 객체 (State Machine)
const ReviewState = {
    wrongQuestionsMap: {},     // 과목별 오답 문항 ID 배열 {'DB': [...], 'SE': [...]}
    questionsData: {},         // 현재 진행 과목의 전체 문항 본문 캐시
    sessionQIds: [],           // 이번 복습 세션에서 풀 문항 ID 리스트
    sessionQuizzes: [],        // 이번 복습 세션에 필터링된 문제 객체 목록
    currentIdx: 0,             // 현재 진행 중인 카드 인덱스
    userSelections: {},        // 이번 세션에서 사용자가 선택한 답 캐시
    isSubmitted: {},           // 각 카드별 제출 완료 여부
    // 🎮 게이미피케이션 EXP/Level 전역 상태
    totalExp: 0,               // 전체 누적 경험치 (=총 정답 수)
    level: 1,                  // 현재 레벨 (Math.floor(totalExp / 10) + 1)
    expInLevel: 0              // 현재 레벨 내 경험치 진행량 (totalExp % 10)
};

// 🎮 게이미피케이션 공통 전역 상태 안전 초기화 가드
window.gamState = window.gamState || { totalExp: 0, level: 1, expInLevel: 0 };

// 과목 코드와 명칭 매핑
const SUBJECT_NAMES = {
    'DB': '데이터베이스',
    'SE': '소프트웨어공학',
    'PM': '사업관리',
    'SA': '시스템구조',
    'SC': '보안'
};

const SUBJECT_DESCS = {
    'DB': '정규화, SQL, 트랜잭션, 데이터 거버넌스 등',
    'SE': '개발 방법론, 품질보증, 비용산정, 테스팅 기법 등',
    'PM': 'PMBOK 기반 범위/일정/원가 관리 및 계산 문제 등',
    'SA': '네트워크, 클라우드, 가상화, 시스템 인프라 아키텍처 등',
    'SC': '암호학, 네트워크 보안, CSAP, ISMS-P 등'
};

// 페이지 로드 시 초기화 구동
document.addEventListener('DOMContentLoaded', () => {
    initWrongAnswers();
});

/**
 * 1. 로컬 캐시와 서버 이력을 하이브리드 병합하여 오답 문항을 추출합니다.
 */
function initWrongAnswers() {
    const subjects = ['DB', 'SE', 'PM', 'SA', 'SC'];
    const fetchPromises = subjects.map(sub => {
        return fetch(`/api/quiz/stats?subject=${sub}`)
            .then(res => res.ok ? res.json() : { logs: [] })
            .catch(() => ({ logs: [] }));
    });

    // EXP 데이터도 함께 비동기 패치
    const expPromise = fetch('/api/quiz/total-exp')
        .then(res => res.ok ? res.json() : { total_exp: 0, level: 1, exp_in_level: 0 })
        .catch(() => ({ total_exp: 0, level: 1, exp_in_level: 0 }));

    Promise.all([Promise.all(fetchPromises), expPromise])
        .then(([results, expData]) => {
            // 🎮 EXP/Level 상태 적재 및 공통 gamState 연동
            window.gamState.totalExp = expData.total_exp || 0;
            window.gamState.level = expData.level || 1;
            window.gamState.expInLevel = expData.exp_in_level || 0;

            ReviewState.totalExp = window.gamState.totalExp;
            ReviewState.level = window.gamState.level;
            ReviewState.expInLevel = window.gamState.expInLevel;

            // 공통 DOM 요소 주입 및 UI 즉시 갱신
            gamInjectLevelUpOverlay();
            gamUpdateExpUI();

            const allLogs = [];
            
            // 오직 서버 이력만 누적하여 마스터 로그 리스트로 설정
            results.forEach((data, index) => {
                const sub = subjects[index];
                const sLogs = data.logs || [];
                sLogs.forEach(log => {
                    let details = log.details;
                    if (typeof log.details === 'string') {
                        try { details = JSON.parse(log.details); } catch (e) {}
                    }
                    allLogs.push({ ...log, details, subject: sub });
                });
            });

            // 시간 UTC 변환 헬퍼
            const getUTCTime = (dateStr) => {
                if (!dateStr) return 0;
                let std = dateStr;
                if (!dateStr.includes('T') && dateStr.includes(' ')) {
                    std = dateStr.replace(' ', 'T') + 'Z';
                } else if (!dateStr.endsWith('Z') && dateStr.includes('T')) {
                    std = dateStr + 'Z';
                }
                const t = new Date(std).getTime();
                return isNaN(t) ? 0 : t;
            };

            // 최신 시도 이력 순으로 정렬
            allLogs.sort((a, b) => getUTCTime(b.created_at) - getUTCTime(a.created_at));

            // 문항별 가장 최신의 풀이 결과 추출
            const latestAttempts = {}; // { '2025_45': { is_correct: true, subject: 'SE' } }

            allLogs.forEach(log => {
                const details = log.details;
                if (!details || !details.q_id) return;
                
                const qId = details.q_id;
                // 정렬을 내림차순(최신순)으로 했으므로, 처음 들어온 것이 가장 최신의 풀이 결과
                if (latestAttempts[qId] === undefined) {
                    // 세부 필드가 is_correct인 구조 또는 correct_count 등으로 판정
                    let isCorrect = details.is_correct;
                    if (isCorrect === undefined) {
                        isCorrect = log.correct_count > 0;
                    }
                    latestAttempts[qId] = {
                        isCorrect: !!isCorrect,
                        subject: log.subject ? log.subject.toUpperCase() : 'DB'
                    };
                }
            });

            // 과목별 오답 맵 구축
            ReviewState.wrongQuestionsMap = { 'DB': [], 'SE': [], 'PM': [], 'SA': [], 'SC': [] };
            
            Object.keys(latestAttempts).forEach(qId => {
                const attempt = latestAttempts[qId];
                if (!attempt.isCorrect) {
                    if (ReviewState.wrongQuestionsMap[attempt.subject]) {
                        ReviewState.wrongQuestionsMap[attempt.subject].push(qId);
                    }
                }
            });

            // 메인 대시보드 렌더링 + EXP UI 갱신
            renderDashboard();
            updateAllExpUI();
        })
        .catch(err => {
            console.error("오답 이력 초기화 오류", err);
            renderDashboard();
        });
}

/**
 * 2. 메인 대시보드 및 통계 렌더링
 */
function renderDashboard() {
    const container = document.getElementById('subject-grid-container');
    if (!container) return;

    container.innerHTML = '';
    
    let totalWrong = 0;
    let activeSubjectsCount = 0;

    const subjects = ['DB', 'SE', 'PM', 'SA', 'SC'];

    subjects.forEach(sub => {
        const wrongList = ReviewState.wrongQuestionsMap[sub] || [];
        const count = wrongList.length;
        totalWrong += count;
        if (count > 0) activeSubjectsCount++;

        const card = document.createElement('div');
        card.className = 'review-subject-card';
        
        const countClass = count === 0 ? 'wrong-count-badge zero' : 'wrong-count-badge';
        const countLabel = count === 0 ? '완료 ✓' : `${count}개 틀림`;
        const isBtnDisabled = count === 0 ? 'disabled' : '';

        card.innerHTML = `
            <div class="card-top-row">
                <span class="sub-title">${SUBJECT_NAMES[sub]}</span>
                <span class="${countClass}">${countLabel}</span>
            </div>
            <p class="card-desc">${SUBJECT_DESCS[sub]}</p>
            <button class="start-btn" onclick="startReview('${sub}')" ${isBtnDisabled}>
                <i data-lucide="play"></i> 복습 시작
            </button>
        `;
        container.appendChild(card);
    });

    // 상단 종합 스탯 업데이트
    document.getElementById('stats-total-subjects').textContent = `${activeSubjectsCount}개 과목`;
    document.getElementById('stats-total-wrong').textContent = `${totalWrong}개`;
    
    // 복습 완료 확률 계산 (합격 기준 과목별 0개 완료를 향한 진척도)
    const clearRate = totalWrong === 0 ? 100 : Math.max(0, Math.round((5 - activeSubjectsCount) * 100 / 5));
    document.getElementById('stats-clear-rate').textContent = `${clearRate}%`;

    // 아이콘 리프레시
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * 3. 오답 복습 세션 구동
 */
function startReview(subject) {
    const wrongQIds = ReviewState.wrongQuestionsMap[subject] || [];
    if (wrongQIds.length === 0) {
        alert("이 과목은 복습할 오답이 없습니다!");
        return;
    }

    ReviewState.sessionQIds = wrongQIds;
    ReviewState.currentIdx = 0;
    ReviewState.userSelections = {};
    ReviewState.isSubmitted = {};
    ReviewState.currentSubject = subject; // [설계 의도] 오답 복습 러너 뷰에서 해당 과목의 전용 캐릭터 펫을 노출할 수 있도록 세션 과목 코드를 보관합니다.

    // 로딩 인디케이터 연출
    document.getElementById('runner-subject-title').textContent = SUBJECT_NAMES[subject];
    document.getElementById('runner-progress-text').textContent = '문항 로딩 중...';
    document.getElementById('card-question-text').textContent = '서버로부터 정밀 기출문제 팩을 다운로드하고 있습니다. 잠시만 기다려 주세요...';
    document.getElementById('card-options-container').innerHTML = '';
    document.getElementById('card-feedback-box').classList.add('hidden');

    switchView('card-view');
    updateAllExpUI();

    // 1) 전체 기출문제 약정 및 2) 단원 매핑 팩 동시 비동기 로딩 (Promise.all)
    const questionsPromise = fetch(`/api/questions?subject=${subject}`)
        .then(res => {
            if (!res.ok) throw new Error("문제를 가져오지 못했습니다.");
            return res.json();
        });

    const dashboardPromise = fetch(`/api/dashboard?subject=${subject}&type=official`)
        .then(res => res.ok ? res.json() : [])
        .catch(() => []);

    Promise.all([questionsPromise, dashboardPromise])
        .then(([qData, dData]) => {
            ReviewState.questionsData = qData;
            window.dashboardData = dData; // 단원 매핑 데이터 전역 활성화

            // 이번 세션에 풀 문제들만 매핑 및 보기 셔플
            ReviewState.sessionQuizzes = ReviewState.sessionQIds.map(qId => {
                const quiz = qData[qId];
                if (quiz && quiz.options && quiz.options.length > 0) {
                    const indices = Array.from({ length: quiz.options.length }, (_, i) => i);
                    if (typeof shuffleArray === 'function') {
                        quiz.shuffledIndices = shuffleArray(indices);
                    } else {
                        // shuffleArray 폴백 구현
                        const arr = [...indices];
                        for (let i = arr.length - 1; i > 0; i--) {
                            const j = Math.floor(Math.random() * (i + 1));
                            [arr[i], arr[j]] = [arr[j], arr[i]];
                        }
                        quiz.shuffledIndices = arr;
                    }
                }
                return quiz;
            }).filter(q => q !== undefined);

            if (ReviewState.sessionQuizzes.length === 0) {
                alert("해당 문제 본문 데이터를 찾을 수 없습니다.");
                backToDashboard();
                return;
            }

            // 첫 카드 렌더링
            renderCard(0);
        })
        .catch(err => {
            alert(err.message);
            backToDashboard();
        });
}

/**
 * 4. 현재 플래시카드 화면 렌더러
 */
function renderCard(idx) {
    ReviewState.currentIdx = idx;
    const quiz = ReviewState.sessionQuizzes[idx];
    if (!quiz) return;

    const total = ReviewState.sessionQuizzes.length;
    
    // 네비게이션 진척도 업데이트
    document.getElementById('runner-progress-text').textContent = `카드 ${idx + 1} / ${total}`;
    const progressPercent = ((idx + 1) / total) * 100;
    document.getElementById('runner-progress-fill').style.width = `${progressPercent}%`;

    // 메타 정보
    const [year, num] = quiz.id.split('_');
    document.getElementById('card-q-id').textContent = `${year}년도 ${SUBJECT_NAMES[quiz.subject || 'DB']} ${num}번 문항`;
    
    // concept 매핑 (만약 존재하면)
    let conceptTag = "공통 범위";
    if (window.dashboardData) {
        const matched = window.dashboardData.find(d => d.questions && d.questions.some(q => String(q.year) === String(year) && String(q.num) === String(num)));
        if (matched) conceptTag = matched.concept.split('.')[0] + '. ' + matched.concept.split('.').slice(1).join('.');
    }
    document.getElementById('card-concept-tag').textContent = conceptTag;

    // 본문 주입
    document.getElementById('card-question-text').textContent = quiz.question;

    // 보기 옵션 렌더링
    const optionsContainer = document.getElementById('card-options-container');
    optionsContainer.innerHTML = '';

    const numSymbols = ["①", "②", "③", "④", "⑤"];
    const isSubmitted = !!ReviewState.isSubmitted[quiz.id];
    const selectedOpt = ReviewState.userSelections[quiz.id];

    // 실제 정답 리스트 파싱
    let cAns = [];
    if (quiz.answer) {
        if (Array.isArray(quiz.answer)) {
            cAns = quiz.answer;
        } else {
            cAns = [parseInt(quiz.answer)];
        }
    }

    const indices = quiz.shuffledIndices || Array.from({ length: quiz.options.length }, (_, i) => i);

    indices.forEach((oIdx, displayIdx) => {
        const optText = quiz.options[oIdx];
        const optNum = oIdx + 1;
        const sym = numSymbols[displayIdx] || `${optNum}`;
        const button = document.createElement('button');
        button.className = 'card-opt-btn';

        button.innerHTML = `
            <span class="card-opt-num">${sym}</span>
            <span class="card-opt-text">${optText}</span>
        `;

        if (isSubmitted) {
            button.disabled = true;
            // 채점 상태 오버레이 클래스 부여
            const isCorrectOpt = cAns.includes(optNum);
            const isUserChoice = (selectedOpt === optNum);

            if (isCorrectOpt) {
                button.classList.add('correct-ans');
            } else if (isUserChoice) {
                button.classList.add('wrong-ans');
            } else {
                button.classList.add('disabled-ans');
            }
        } else {
            button.addEventListener('click', () => submitAnswer(quiz.id, optNum));
        }

        optionsContainer.appendChild(button);
    });

    // 피드백 박스 노출 분기 제어
    const feedbackBox = document.getElementById('card-feedback-box');
    
    // 이전 보물 상자 이펙트 제거 (정답/오답 상태 전이에 따른 잔재 청소)
    const existingChest = feedbackBox.querySelector('.treasure-popup-container');
    if (existingChest) {
        existingChest.remove();
    }

    if (isSubmitted) {
        const isUserCorrect = cAns.includes(selectedOpt);
        const banner = document.getElementById('card-feedback-banner');
        
        if (isUserCorrect) {
            banner.className = 'feedback-banner correct hidden';
            banner.innerHTML = '';
        } else {
            const ansStr = cAns.map(n => {
                const displayIdx = quiz.shuffledIndices ? quiz.shuffledIndices.indexOf(n - 1) : (n - 1);
                return numSymbols[displayIdx] || (displayIdx + 1);
            }).join(', ');
            banner.className = 'feedback-banner wrong';
            banner.innerHTML = `<i data-lucide="x-circle"></i> 오답입니다. (정답: ${ansStr})`;
        }

        // 해설 박스 기재
        const explanationBox = document.getElementById('card-explanation-box');
        explanationBox.innerHTML = `<strong>💡 정답 해설:</strong><br>${quiz.explanation || "등록된 추가 상세 해설이 없습니다."}`;
        
        feedbackBox.classList.remove('hidden');
    } else {
        feedbackBox.classList.add('hidden');
    }

    // 컨트롤 버튼 활성화 상태 갱신
    document.getElementById('btn-prev').disabled = (idx === 0);
    
    // 제출 전에는 다음 카드 이동을 원천 차단하여 순차 풀이 강제 (WOW 기획)
    const nextBtn = document.getElementById('btn-next');
    nextBtn.disabled = !isSubmitted;

    // 아이콘 새로고침
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * 5. 카드 답안 선택 제출 및 채점
 */
function submitAnswer(qId, selectedOption) {
    const quiz = ReviewState.sessionQuizzes[ReviewState.currentIdx];
    if (!quiz) return;

    // 상태 적재
    ReviewState.userSelections[qId] = selectedOption;
    ReviewState.isSubmitted[qId] = true;

    // 정답 리스트 파싱
    let cAns = [];
    if (quiz.answer) {
        if (Array.isArray(quiz.answer)) {
            cAns = quiz.answer;
        } else {
            cAns = [parseInt(quiz.answer)];
        }
    }

    // 채점 규칙 적용: 다중 정답 시 하나만 맞아도 정답 인정
    const isCorrect = cAns.includes(selectedOption);

    // 백엔드 및 로컬스토리지 제출 데이터 payload 생성
    const subject = (quiz.subject || 'DB').toUpperCase();
    
    // 이 기출 문항이 포함된 대표 concept 탐색
    let conceptName = "기타";
    if (window.dashboardData) {
        const [year, num] = qId.split('_');
        const matched = window.dashboardData.find(d => d.questions && d.questions.some(q => String(q.year) === String(year) && String(q.num) === String(num)));
        if (matched) conceptName = matched.concept;
    }

    const payload = {
        subject: subject,
        concept: conceptName,
        total_questions: 1,
        correct_count: isCorrect ? 1 : 0,
        wrong_count: isCorrect ? 0 : 1,
        details: {
            q_id: qId,
            user_choice: [selectedOption],
            correct_answer: cAns,
            is_correct: isCorrect
        }
    };

    // 백엔드 API 비동기 발송
    fetch('/api/quiz/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }).catch(err => console.error("백엔드 이력 전송 실패", err));

    // 🎮 정답 시 게이미피케이션 이펙트 트리거 (공통 gam 기능 사용)
    if (isCorrect) {
        const prevLevel = window.gamState.level;
        window.gamState.totalExp += 1;
        window.gamState.level = Math.floor(window.gamState.totalExp / 10) + 1;
        window.gamState.expInLevel = window.gamState.totalExp % 10;
        
        // ReviewState 동기화
        ReviewState.totalExp = window.gamState.totalExp;
        ReviewState.level = window.gamState.level;
        ReviewState.expInLevel = window.gamState.expInLevel;
        
        // 공통 EXP UI 갱신 (메인 프로필 카드)
        gamUpdateExpUI();
        
        // 카드 러너 미니 EXP 바 갱신 (오답노트 전용)
        updateRunnerExpUI();

        // 연속 정답 콤보 누적
        window.gamComboCount = (window.gamComboCount || 0) + 1;
        let isComboTriggered = false;
        if (window.gamComboCount >= 4) {
            isComboTriggered = true;
        }

        // 5콤보 달성 또는 10콤보 이상 연속 정답 시 특별 축하 이펙트 구동, 그 외에는 일반 칭찬 멘트
        if (isComboTriggered) {
            if (typeof gamTriggerCombo5Effect === 'function') {
                gamTriggerCombo5Effect(window.gamComboCount);
            }
        } else {
            // 펫 정답 축하 말풍선 트리거 (공통)
            if (typeof gamTriggerPetCorrectMessage === 'function') {
                gamTriggerPetCorrectMessage();
            }

            // 펫 정답 애니메이션 트리거 (공통)
            if (typeof gamApplyPetAnimation === 'function') {
                gamApplyPetAnimation('correct');
            }
        }
        
        // EXP +1 플로팅 뱃지 연출 (공통 - 퍼펙트 이펙트 집중을 위해 비활성화)
        // if (typeof gamTriggerExpFloat === 'function') {
        //     gamTriggerExpFloat();
        // }
        
        // 보물 상자 + 보석 파티클 연출 (공통 함수 사용)
        const feedbackBox = document.getElementById('card-feedback-box');
        if (feedbackBox) {
            gamSpawnTreasureChest(feedbackBox, '.explanation-box');
        }
        
        // 카드 섬광 이펙트 (오답노트 전용)
        const flashcard = document.getElementById('active-flashcard');
        if (flashcard) {
            flashcard.classList.add('correct-flash');
            setTimeout(() => flashcard.classList.remove('correct-flash'), 600);
        }
        
        // 레벨업 체크 → 공통 전체화면 레이저 빔 오버레이 연출
        if (window.gamState.level > prevLevel) {
            if (typeof gamTriggerLevelUp === 'function') {
                setTimeout(() => gamTriggerLevelUp(window.gamState.level), 900);
            }
        }
    } else {
        // 펫 오답 격려 말풍선 트리거 (공통)
        if (typeof gamTriggerPetIncorrectMessage === 'function') {
            gamTriggerPetIncorrectMessage();
        }
        // 펫 오답 시무룩 흔들림 애니메이션 트리거 (공통)
        if (typeof gamApplyPetAnimation === 'function') {
            gamApplyPetAnimation('incorrect');
        }
    }

    // 화면 즉시 리렌더링
    renderCard(ReviewState.currentIdx);
}

/**
 * 6. 플래시카드 네비게이션 컨트롤러
 */
function prevCard() {
    if (ReviewState.currentIdx > 0) {
        renderCard(ReviewState.currentIdx - 1);
    }
}

function nextCard() {
    const total = ReviewState.sessionQuizzes.length;
    if (ReviewState.currentIdx < total - 1) {
        renderCard(ReviewState.currentIdx + 1);
    } else {
        // 마지막 카드 완료 시 자동 종료 및 목록으로 복귀 피드백
        alert("축하합니다! 이번 과목의 오답 복습 세션 카드를 모두 학습하셨습니다. 홈 화면에서 업데이트된 상태를 확인하세요!");
        backToDashboard();
    }
}

/**
 * 7. 뷰 전환 및 목록 복귀
 */
function backToDashboard() {
    switchView('dashboard-view');
    // 복귀 시 풀이 이력을 실시간 재조사하여 오답 뱃지 차감 동기화 (WOW 기획)
    initWrongAnswers();
}

function switchView(viewId) {
    document.querySelectorAll('.view-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    const target = document.getElementById(viewId);
    if (target) {
        target.classList.add('active');
    }
}

/* ==========================================================================
   🎮 게이미피케이션 시스템 - 오답노트 전용 바 동기화
   ========================================================================== */

/**
 * 카드 러너용 미니 EXP 바 UI를 업데이트합니다.
 */
function updateRunnerExpUI() {
    const { totalExp, level, expInLevel } = window.gamState;
    const expPercent = (expInLevel / 10) * 100;
    const nextLevelExp = level * 10;

    const runnerLevelValue = document.getElementById('runner-level-value');
    const runnerExpFill = document.getElementById('runner-exp-fill');
    const runnerExpValue = document.getElementById('runner-exp-value');

    if (runnerLevelValue) runnerLevelValue.textContent = level;
    if (runnerExpFill) runnerExpFill.style.width = `${expPercent}%`;
    if (runnerExpValue) runnerExpValue.textContent = `${totalExp} / ${nextLevelExp} EXP`;

    // 🎮 미니 응원 펫 위젯 삽입 (오답노트 카드 뷰어용)
    const wrapper = document.querySelector('.runner-exp-bar-wrapper');
    if (wrapper && !document.getElementById('gam-runner-pet-widget')) {
        const petWidget = document.createElement('div');
        petWidget.id = 'gam-runner-pet-widget';
        petWidget.className = 'gam-pet-widget';
        petWidget.style.cssText = 'display: flex; align-items: center; gap: 0.6rem; cursor: pointer; margin-right: 0.8rem; flex-shrink: 0;';
        petWidget.onclick = () => {
            if (typeof gamCyclePet === 'function') {
                gamCyclePet();
            }
        };
        petWidget.title = '클릭 시 포켓몬 캐릭터 교체';

        // 현재 선택된 펫 로드
        const config = window.APP_CONFIG || {};
        const petKeys = config.PET_KEYS || ['pikachu', 'charmander', 'squirtle', 'bulbasaur', 'growlithe', 'rotom', 'sirfetchd', 'metagross'];

        // [설계 의도]
        // 오답 복습 중인 과목 코드(ReviewState.currentSubject)에 적합한 기본 마스코트 펫을 매핑합니다.
        const curSub = ReviewState.currentSubject ? ReviewState.currentSubject.toUpperCase() : '';
        const defaultPet = (config.SUBJECT_DEFAULT_PETS && config.SUBJECT_DEFAULT_PETS[curSub]) || 'pikachu';

        const petStorageKey = curSub ? `gam_selected_pet_${curSub}` : 'gam_selected_pet';
        let currentPetKey = localStorage.getItem(petStorageKey) || defaultPet;
        if (!petKeys.includes(currentPetKey)) currentPetKey = defaultPet;

        const activePet = (config.PET_PROFILES && config.PET_PROFILES[currentPetKey]) || { 
            name: '피카츄', 
            src: '/reports/images_game/pikachuRun.gif', 
            defaultMsg: '오늘도 합격을 향해 백만볼트! ⚡' 
        };

        petWidget.innerHTML = `
            <div class="gam-pet-avatar-wrapper" style="width: 38px; height: 38px; border-radius: 50%; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative;">
                <img id="gam-runner-pet-img" src="${activePet.src}" alt="${activePet.name}" style="width: 85%; height: 85%; object-fit: contain; transform: scale(1.1);" />
            </div>
            <div class="gam-pet-bubble" style="background: rgba(139, 92, 246, 0.12); border: 1px solid rgba(139, 92, 246, 0.25); color: #e9d5ff; font-size: 0.65rem; padding: 0.25rem 0.5rem; border-radius: 6px; position: relative; max-width: 120px; line-height: 1.3; font-weight: 500; min-height: 28px; display: flex; align-items: center;">
                <span id="gam-runner-pet-bubble-text">${activePet.defaultMsg}</span>
                <div style="position: absolute; left: -5px; top: 50%; transform: translateY(-50%) rotate(45deg); width: 6px; height: 6px; background: #0c0f1d; border-left: 1px solid rgba(139, 92, 246, 0.25); border-bottom: 1px solid rgba(139, 92, 246, 0.25);"></div>
            </div>
        `;

        wrapper.insertBefore(petWidget, wrapper.firstChild);
    }
}

/**
 * 🎮 모든 EXP/Level 관련 UI 요소를 동기화하여 갱신합니다.
 */
function updateAllExpUI() {
    if (typeof gamUpdateExpUI === 'function') {
        gamUpdateExpUI();
    }
    if (typeof updateRunnerExpUI === 'function') {
        updateRunnerExpUI();
    }
}
