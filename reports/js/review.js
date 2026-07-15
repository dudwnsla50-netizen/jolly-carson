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

            // AI 해설 즉시 보기(viewAiExplanation)가 캐시를 조회할 수 있도록 전역 저장소에도 등록합니다.
            window.loadedQuestions = window.loadedQuestions || {};
            ReviewState.sessionQuizzes.forEach(quiz => {
                window.loadedQuestions[quiz.id] = quiz;
            });

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
    document.getElementById('card-difficulty-tag').innerHTML = getDifficultyBadgeHtml(quiz.difficulty);

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
            // [설계 의도] 클릭 즉시 채점하지 않고 선택만 표시합니다. 실제 채점은 "답안 제출" 버튼을 눌러야 진행됩니다.
            if (selectedOpt === optNum) {
                button.classList.add('selected');
            }
            button.addEventListener('click', () => selectOption(quiz.id, optNum));
        }

        optionsContainer.appendChild(button);
    });

    // 답안 제출 버튼 상태 갱신: 제출 전엔 선택된 보기가 있어야만 활성화, 제출 후엔 숨김
    const submitBtn = document.getElementById('btn-submit-answer');
    if (submitBtn) {
        if (isSubmitted) {
            submitBtn.classList.add('hidden');
        } else {
            submitBtn.classList.remove('hidden');
            submitBtn.disabled = (selectedOpt === undefined || selectedOpt === null);
        }
    }

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
                <div class="explanation-text-box" style="display: none; margin-top: 0.6rem; font-size: 0.82rem; line-height: 1.5; color: var(--text-secondary); white-space: pre-wrap;">
                    <strong>💡 정답 해설:</strong><br>${quiz.explanation || "등록된 추가 상세 해설이 없습니다."}
                    <div class="ai-explain-section" style="margin-top: 0.6rem; padding-top: 0.6rem; border-top: 1px dashed rgba(139, 92, 246, 0.18); white-space: normal;">
                        <button class="ai-explain-btn" id="ai-explain-trigger-${quiz.id}" onclick="viewAiExplanation('${quiz.id}', 'ai-explain-box-${quiz.id}')" style="background: none; border: none; color: #a78bfa; font-size: 0.72rem; font-weight: 700; cursor: pointer; padding: 0; font-family: inherit;">${quiz.ai_explanation ? '📖 AI 해설 보기' : '✨ AI 해설 생성'}</button>
                        <div id="ai-explain-box-${quiz.id}" class="ai-explain-box" style="margin-top: 0.4rem;"></div>
                    </div>
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

/* ==========================================================================
   문제 수정 (대시보드의 리치 에디터 + 이미지 업로드 기능을 동일하게 재사용)
   [설계 의도] dashboard_common.js에 정의된 공용 헬퍼(toEditableHtml, handleRichEditorPaste,
   getRichEditorValue, initEditImagePreview 등)는 idx로 element id를 구성할 뿐 아코디언 구조에
   의존하지 않으므로, 고정 idx('review')로 그대로 재사용해 대시보드와 완전히 동일한 편집 동작을
   보장합니다. 다만 저장/취소 후 되돌아갈 화면은 아코디언 렌더러가 아닌 review.js 자신의
   renderCard()이므로, startEditQuestion/saveEditQuestion 자체는 재사용하지 않고 이 전용 버전을 둡니다.
   ========================================================================== */
const REVIEW_EDIT_IDX = 'review';

function onEditReviewBtnClick(event) {
    if (event) event.stopPropagation();
    const isEditing = document.getElementById('card-edit-form-container') !== null;
    if (isEditing) {
        cancelEditReviewQuestion();
    } else {
        startEditReviewQuestion();
    }
}

function startEditReviewQuestion() {
    const quiz = ReviewState.sessionQuizzes[ReviewState.currentIdx];
    if (!quiz) return;

    const idx = REVIEW_EDIT_IDX;
    const qId = quiz.id;
    const data = quiz;

    // 편집 중에는 문제 풀이 UI(보기/제출/피드백)를 숨기고 편집 폼만 노출합니다.
    document.getElementById('card-question-section').classList.add('hidden');
    document.getElementById('card-options-container').classList.add('hidden');
    const submitRow = document.getElementById('answer-submit-row');
    if (submitRow) submitRow.classList.add('hidden');
    document.getElementById('card-feedback-box').classList.add('hidden');

    let htmlContent = `
        <div class="edit-form-container" id="card-edit-form-container" style="display: flex; flex-direction: column; gap: 1rem; padding: 0.5rem 0;">
            <div>
                <label style="font-size: 0.85rem; color: #a78bfa; font-weight: bold; display: block; margin-bottom: 0.4rem;">❓ 질문 본문 수정</label>
                <div id="edit-q-text-${idx}" class="rich-editor" contenteditable="true" onpaste="handleRichEditorPaste(event)" oninput="refreshAccordionHeightFor(this)" style="width: 100%; min-height: 120px; max-height: 420px; overflow-y: auto; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(139, 92, 246, 0.3); color: #ffffff; padding: 0.6rem; border-radius: 6px; font-size: 0.9rem; line-height: 1.5; outline: none; white-space: pre-wrap;">${toEditableHtml(data.question)}</div>
                <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.3rem;">텍스트와 이미지를 함께 붙여넣을 수 있습니다 (Ctrl+V)</div>
            </div>
            <div>
                <label style="font-size: 0.85rem; color: #a78bfa; font-weight: bold; display: block; margin-bottom: 0.6rem;">📋 보기(선택지) 수정</label>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
    `;

    const numSymbols = ["①", "②", "③", "④", "⑤"];
    const options = data.options && data.options.length > 0 ? data.options : ["", "", "", ""];

    options.forEach((opt, oIdx) => {
        const sym = numSymbols[oIdx] || `${oIdx + 1}.`;
        const escapedOpt = (opt || '').replace(/"/g, '&quot;');
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
                <div style="display: flex; gap: 1rem; flex-wrap: wrap; padding: 0.5rem; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(139, 92, 246, 0.2); border-radius: 4px;">
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
                <label style="font-size: 0.85rem; color: #a78bfa; font-weight: bold; display: block; margin-bottom: 0.4rem;">🎯 난이도 수정</label>
                <select id="edit-q-difficulty-${idx}" style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(139, 92, 246, 0.3); color: #ffffff; padding: 0.5rem 0.7rem; border-radius: 6px; font-size: 0.85rem; outline: none; font-family: inherit;">
                    ${['상', '중', '하', '예외'].map(d => `<option value="${d}" ${(data.difficulty || '중') === d ? 'selected' : ''}>${d}</option>`).join('')}
                </select>
            </div>
            <div>
                <label style="font-size: 0.85rem; color: #a78bfa; font-weight: bold; display: block; margin-bottom: 0.4rem;">📝 해설 수정</label>
                <div id="edit-q-explanation-${idx}" class="rich-editor" contenteditable="true" onpaste="handleRichEditorPaste(event)" oninput="refreshAccordionHeightFor(this)" onmouseup="refreshAccordionHeightFor(this)" style="width: 100%; min-height: 150px; max-height: 800px; overflow-y: auto; resize: vertical; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(139, 92, 246, 0.3); color: #ffffff; padding: 0.6rem; border-radius: 6px; font-size: 0.9rem; line-height: 1.5; outline: none; white-space: pre-wrap;">${toEditableHtml(data.explanation || '')}</div>
                <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.3rem;">텍스트와 이미지를 함께 붙여넣을 수 있습니다 (Ctrl+V)</div>
            </div>
            <div>
                <label style="font-size: 0.85rem; color: #a78bfa; font-weight: bold; display: block; margin-bottom: 0.6rem;">🖼️ 시험지 원본 이미지 수정</label>
                <div style="display: flex; align-items: flex-start; gap: 1rem; flex-wrap: wrap;">
                    <div id="edit-img-preview-wrap-${idx}" style="min-width: 120px; min-height: 90px; display: flex; align-items: center; justify-content: center;">
                        <img id="edit-img-preview-${idx}" src="" alt="현재 이미지" style="max-width: 220px; max-height: 160px; border-radius: 6px; border: 1px solid rgba(139, 92, 246, 0.3); display: none;" onerror="onEditImagePreviewError('${idx}')">
                        <div id="edit-img-empty-${idx}" style="font-size: 0.8rem; color: var(--text-muted);">등록된 이미지가 없습니다.</div>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                        <input type="file" accept="image/png" id="edit-img-file-${idx}" onchange="onEditImageFileSelected('${idx}', event)" style="font-size: 0.8rem; color: #ffffff; max-width: 220px;">
                        <span style="font-size: 0.7rem; color: var(--text-muted);">PNG 파일만 지원됩니다</span>
                        <label style="display: flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; color: var(--text-secondary); cursor: pointer;">
                            <input type="checkbox" id="edit-img-remove-${idx}" onchange="onEditImageRemoveToggled('${idx}')" style="accent-color: #8b5cf6; width: 14px; height: 14px; cursor: pointer;">
                            이미지 삭제
                        </label>
                    </div>
                </div>
            </div>
            <div style="display: flex; gap: 0.6rem; justify-content: flex-end; margin-top: 0.5rem;">
                <button onclick="saveEditReviewQuestion(event)" style="background: #8b5cf6; border: none; color: #ffffff; padding: 0.4rem 1rem; border-radius: 4px; font-size: 0.85rem; font-weight: bold; cursor: pointer;">💾 저장</button>
                <button onclick="cancelEditReviewQuestion(event)" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: var(--text-secondary); padding: 0.4rem 1rem; border-radius: 4px; font-size: 0.85rem; cursor: pointer; font-family: inherit;">취소</button>
            </div>
        </div>
    `;

    const editContainer = document.getElementById('card-edit-container');
    editContainer.innerHTML = htmlContent;
    editContainer.classList.remove('hidden');

    initEditImagePreview(idx, qId);

    const editBtn = document.getElementById('edit-question-btn');
    if (editBtn) editBtn.innerText = '✕ 취소';
}

/**
 * [설계 의도] 수정한 질문/보기/정답/해설/이미지를 대시보드와 동일한 API(/api/question/update,
 * /api/question/upload-image)로 저장하고, 현재 세션에 로드된 문제 객체를 즉시 동기화합니다.
 */
function saveEditReviewQuestion(event) {
    if (event) event.stopPropagation();

    const quiz = ReviewState.sessionQuizzes[ReviewState.currentIdx];
    if (!quiz) return;

    const idx = REVIEW_EDIT_IDX;
    const qId = quiz.id;

    const qTextVal = getRichEditorValue(`edit-q-text-${idx}`);
    const optInputs = document.querySelectorAll(`.edit-opt-input-${idx}`);
    const optionsVal = [];
    optInputs.forEach(input => optionsVal.push(input.value));

    const answerCheckboxes = document.querySelectorAll(`.edit-answer-chk-${idx}:checked`);
    const answerArr = Array.from(answerCheckboxes).map(chk => parseInt(chk.value));
    const explanationVal = getRichEditorValue(`edit-q-explanation-${idx}`);
    const difficultySelect = document.getElementById(`edit-q-difficulty-${idx}`);
    const difficultyVal = difficultySelect ? difficultySelect.value : '중';

    const updateData = { id: qId, question: qTextVal, options: optionsVal, answer: answerArr, explanation: explanationVal, difficulty: difficultyVal };
    const imageState = (window.pendingImageEdits && window.pendingImageEdits[idx]) || { dataUrl: null, remove: false };

    fetch('/api/question/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
    })
        .then(response => {
            if (!response.ok) throw new Error("HTTP error " + response.status);
            return response.json();
        })
        .then(res => {
            if (!res.success) {
                alert("저장 실패: " + res.message);
                return Promise.reject(null);
            }

            // 현재 세션에 로드된 문제 객체(캐시 포함, 동일 참조)를 즉시 동기화
            quiz.question = qTextVal;
            quiz.options = optionsVal;
            quiz.answer = answerArr;
            quiz.explanation = explanationVal;
            quiz.difficulty = difficultyVal;
            document.getElementById('card-difficulty-tag').innerHTML = getDifficultyBadgeHtml(difficultyVal);

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
        .then(imgRes => {
            if (imgRes && imgRes.success === false) {
                alert("문제 내용은 저장되었으나 이미지 저장에 실패했습니다: " + imgRes.message);
            } else {
                alert("문제가 성공적으로 저장되었습니다.");
            }
            if (window.pendingImageEdits) delete window.pendingImageEdits[idx];
            closeEditReviewQuestion();
        })
        .catch(err => {
            if (err !== null) {
                console.error(err);
                alert("서버와 통신 중 오류가 발생하여 저장에 실패했습니다.");
            }
        });
}

function cancelEditReviewQuestion(event) {
    if (event) event.stopPropagation();
    if (window.pendingImageEdits) delete window.pendingImageEdits[REVIEW_EDIT_IDX];
    closeEditReviewQuestion();
}

/**
 * [설계 의도] 편집 폼을 정리하고 문제 풀이 UI(보기/제출/피드백)를 원래 상태로 복원합니다.
 */
function closeEditReviewQuestion() {
    const editContainer = document.getElementById('card-edit-container');
    if (editContainer) {
        editContainer.innerHTML = '';
        editContainer.classList.add('hidden');
    }

    document.getElementById('card-question-section').classList.remove('hidden');
    document.getElementById('card-options-container').classList.remove('hidden');
    const submitRow = document.getElementById('answer-submit-row');
    if (submitRow) submitRow.classList.remove('hidden');

    const editBtn = document.getElementById('edit-question-btn');
    if (editBtn) editBtn.innerText = '✏️ 수정';

    renderCard(ReviewState.currentIdx);
}

/**
 * [설계 의도] 보기를 클릭하면 채점 없이 선택 상태만 기록하고 카드를 다시 그려 하이라이트와
 * "답안 제출" 버튼 활성화 상태를 갱신합니다. 실제 채점은 submitCurrentAnswer()에서 이뤄집니다.
 */
function selectOption(qId, optNum) {
    if (ReviewState.isSubmitted[qId]) return;
    ReviewState.userSelections[qId] = optNum;
    renderCard(ReviewState.currentIdx);
}

/**
 * [설계 의도] "답안 제출" 버튼 클릭 시, 현재 카드에서 선택해 둔 보기를 가져와 실제 채점을 진행합니다.
 */
function submitCurrentAnswer() {
    const quiz = ReviewState.sessionQuizzes[ReviewState.currentIdx];
    if (!quiz) return;

    const selectedOpt = ReviewState.userSelections[quiz.id];
    if (selectedOpt === undefined || selectedOpt === null) return;

    submitAnswer(quiz.id, selectedOpt);
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
