/**
 * ==========================================================================
 * [Jolly-Carson 오답 복습 스케줄러 코어 스크립트 - review.js]
 * - 주요 기능: 서버의 망각곡선 기반 SRS(srs_review_state) 스케줄에 따라 "오늘 복습할 문항"만 선별
 *             플래시카드 렌더링 및 실시간 채점 제출 연동 (제출 시 서버가 다음 복습 간격을 재계산)
 * ==========================================================================
 */

// 전역 상태 관리 객체 (State Machine)
const ReviewState = {
    dueQuestionsMap: {},       // 과목별 "오늘 복습 대상" 문항 ID 배열 {'DB': [...], 'SE': [...]}
    upcomingCountMap: {},      // 과목별 "아직 복습 시기가 안 된" 대기중 문항 개수 {'DB': 3, ...}
    questionsData: {},         // 현재 진행 과목의 전체 문항 본문 캐시
    sessionQIds: [],           // 이번 복습 세션에서 풀 문항 ID 리스트
    sessionQuizzes: [],        // 이번 복습 세션에 필터링된 문제 객체 목록
    currentIdx: 0,             // 현재 진행 중인 카드 인덱스
    userSelections: {},        // 이번 세션에서 사용자가 선택한 답 캐시
    isSubmitted: {}            // 각 카드별 제출 완료 여부
};

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
 * 1. 망각곡선 기반 복습 스케줄러(SRS)에서 과목별 "오늘 복습 대상" 문항을 조회합니다.
 * [설계 의도] 예전에는 quiz_history 전체를 훑어 "최신 시도가 오답인 문항"을 전부 모아 보여줬지만,
 * 이제는 서버가 관리하는 next_review_at 스케줄에 따라 "오늘 복습할 때가 된 문항"만 노출합니다.
 * 아직 복습 시기가 안 된 문항은 upcomingCountMap으로 별도 집계해 대기중임을 알려줍니다.
 */
function initWrongAnswers() {
    const subjects = ['DB', 'SE', 'PM', 'SA', 'SC'];
    const fetchPromises = subjects.map(sub => {
        return fetch(`/api/srs/due?subject=${sub}`)
            .then(res => res.ok ? res.json() : { due: [], upcoming: [] })
            .catch(() => ({ due: [], upcoming: [] }));
    });

    Promise.all(fetchPromises)
        .then(results => {
            // 과목별 "오늘 복습 대상" 및 "대기중" 집계
            ReviewState.dueQuestionsMap = { 'DB': [], 'SE': [], 'PM': [], 'SA': [], 'SC': [] };
            ReviewState.upcomingCountMap = { 'DB': 0, 'SE': 0, 'PM': 0, 'SA': 0, 'SC': 0 };

            results.forEach((data, index) => {
                const sub = subjects[index];
                const dueList = data.due || [];
                const upcomingList = data.upcoming || [];
                ReviewState.dueQuestionsMap[sub] = dueList.map(item => item.q_id);
                ReviewState.upcomingCountMap[sub] = upcomingList.length;
            });

            renderReviewDashboard();
        })
        .catch(err => {
            console.error("복습 스케줄 초기화 오류", err);
            renderReviewDashboard();
        });
}

/**
 * 2. 메인 대시보드 및 통계 렌더링
 * [설계 의도] 카드에는 "오늘 복습 N개"(due)만 강조해 표시하고, 아직 복습 시기가 안 된 문항은
 * "대기중 M개"로 별도 노출해 사용자가 전체 백로그와 오늘 할 일을 구분할 수 있게 합니다.
 */
function renderReviewDashboard() {
    const container = document.getElementById('subject-grid-container');
    if (!container) return;

    container.innerHTML = '';

    let totalDue = 0;
    let totalUpcoming = 0;

    const subjects = ['DB', 'SE', 'PM', 'SA', 'SC'];

    subjects.forEach(sub => {
        const dueList = ReviewState.dueQuestionsMap[sub] || [];
        const count = dueList.length;
        const upcomingCount = ReviewState.upcomingCountMap[sub] || 0;
        totalDue += count;
        totalUpcoming += upcomingCount;

        const card = document.createElement('div');
        card.className = 'review-subject-card';

        const countClass = count === 0 ? 'wrong-count-badge zero' : 'wrong-count-badge';
        const countLabel = count === 0 ? '완료 ✓' : `오늘 ${count}개`;
        const isBtnDisabled = count === 0 ? 'disabled' : '';
        const descText = upcomingCount > 0
            ? `${SUBJECT_DESCS[sub]} (대기중 ${upcomingCount}개)`
            : SUBJECT_DESCS[sub];

        card.innerHTML = `
            <div class="card-top-row">
                <span class="sub-title">${SUBJECT_NAMES[sub]}</span>
                <span class="${countClass}">${countLabel}</span>
            </div>
            <p class="card-desc">${descText}</p>
            <button class="start-btn" onclick="startReview('${sub}')" ${isBtnDisabled}>
                <i data-lucide="play"></i> 복습 시작
            </button>
        `;
        container.appendChild(card);
    });

    // 상단 종합 스탯 업데이트
    document.getElementById('stats-total-wrong').textContent = `${totalDue}개`;
    const upcomingStatEl = document.getElementById('stats-total-upcoming');
    if (upcomingStatEl) upcomingStatEl.textContent = `${totalUpcoming}개`;

    // 아이콘 리프레시
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * 3. 오답 복습 세션 구동
 */
function startReview(subject) {
    const dueQIds = ReviewState.dueQuestionsMap[subject] || [];
    if (dueQIds.length === 0) {
        alert("이 과목은 오늘 복습할 문항이 없습니다!");
        return;
    }

    ReviewState.sessionQIds = dueQIds;
    ReviewState.currentIdx = 0;
    ReviewState.userSelections = {};
    ReviewState.isSubmitted = {};

    // 로딩 인디케이터 연출
    document.getElementById('runner-subject-title').textContent = SUBJECT_NAMES[subject];
    document.getElementById('runner-progress-text').textContent = '문항 로딩 중...';
    document.getElementById('card-question-text').textContent = '서버로부터 정밀 기출문제 팩을 다운로드하고 있습니다. 잠시만 기다려 주세요...';
    document.getElementById('card-options-container').innerHTML = '';
    document.getElementById('card-feedback-box').classList.add('hidden');

    switchView('card-view');

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

    // 본문 주입 (리치 에디터로 저장된 이미지 포함 HTML을 그대로 렌더링)
    document.getElementById('card-question-text').innerHTML = quiz.question;

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

    if (isSubmitted) {
        const isUserCorrect = cAns.includes(selectedOpt);
        const banner = document.getElementById('card-feedback-banner');

        if (isUserCorrect) {
            banner.className = 'feedback-banner correct';
            banner.innerHTML = '<i data-lucide="check-circle"></i> 정답입니다!';
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
        explanationBox.innerHTML = `
            <div class="explanation-toggle-container">
                <button class="explanation-toggle-btn" onclick="toggleExplanationCollapse(this)" style="background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.3); color: #c084fc; padding: 0.35rem 0.8rem; border-radius: 6px; font-size: 0.76rem; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 0.3rem; outline: none;">
                    <span>💡 해설보기</span>
                </button>
                <div class="explanation-text-box" style="display: none; margin-top: 0.6rem; font-size: 0.82rem; line-height: 1.5; color: var(--text-secondary);">
                    <strong>💡 정답 해설:</strong><br>${quiz.explanation || "등록된 추가 상세 해설이 없습니다."}
                </div>
            </div>
        `;

        feedbackBox.classList.remove('hidden');
    } else {
        feedbackBox.classList.add('hidden');
    }

    // 컨트롤 버튼 활성화 상태 갱신
    document.getElementById('btn-prev').disabled = (idx === 0);

    // 제출 전에는 다음 카드 이동을 원천 차단하여 순차 풀이 강제
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

    // 백엔드 제출 데이터 payload 생성
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

    // 백엔드 API 비동기 발송 (응답의 srs 필드로 다음 복습 일정을 안내)
    fetch('/api/quiz/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(res => res.ok ? res.json() : null)
        .then(resData => {
            if (resData && resData.srs) renderSrsFeedback(qId, resData.srs);
        })
        .catch(err => console.error("백엔드 이력 전송 실패", err));

    // 화면 즉시 리렌더링
    renderCard(ReviewState.currentIdx);
}

/**
 * [설계 의도] 서버가 계산한 다음 복습 일정(간격/마스터 여부)을 해설 영역 하단에 안내 문구로 덧붙입니다.
 * 응답이 도착하기 전에 사용자가 다른 카드로 넘어갔을 수 있으므로, 현재 카드가 여전히 해당 문항인지 확인 후 덧붙입니다.
 */
function renderSrsFeedback(qId, srsInfo) {
    const currentQuiz = ReviewState.sessionQuizzes[ReviewState.currentIdx];
    if (!currentQuiz || currentQuiz.id !== qId) return;

    const explanationBox = document.getElementById('card-explanation-box');
    if (!explanationBox) return;

    const existingNote = explanationBox.querySelector('.srs-schedule-note');
    if (existingNote) existingNote.remove();

    const note = document.createElement('div');
    note.className = 'srs-schedule-note';
    note.textContent = srsInfo.mastered
        ? '🎉 이 문항은 복습 완료(마스터) 처리되어 더 이상 큐에 나타나지 않습니다!'
        : `🗓️ 다음 복습: ${srsInfo.interval_days}일 후`;
    explanationBox.appendChild(note);
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
        alert("이번 과목의 오늘 복습 대상을 모두 학습했습니다!");
        backToDashboard();
    }
}

/**
 * 7. 뷰 전환 및 목록 복귀
 */
function backToDashboard() {
    switchView('dashboard-view');
    // 복귀 시 스케줄을 실시간 재조회하여 오늘 복습 대상 개수를 동기화
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
