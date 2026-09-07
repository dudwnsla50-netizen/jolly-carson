/**
 * ==========================================================================
 * [예외 문제 모의고사 - exception_exam.js]
 * 중요도가 "예외"로 표시된 문항만 모아 과목/연도 구분 없이 순서대로 풀고,
 * 마지막에 한 번에 채점해 결과를 보여주는 가벼운 전용 화면입니다.
 * yearly_exam.js(년도별 120제)의 exam_year 중심 구조와는 별개로 동작하며,
 * 채점 결과는 quiz_history에 문항 단위로 기록됩니다.
 * ==========================================================================
 */

const EE_THEME_KEY = 'jc_theme';

const EEState = {
    questions: [],
    currentIdx: 0,
    answers: {},   // "{year}_{question_num}" -> 선택한 보기 번호
};

const EE_SUBJECT_NAMES = {
    PM: '사업관리', SE: '소프트웨어공학', DB: '데이터베이스', SA: '시스템아키텍처', SC: '보안'
};

function eeQKey(q) {
    return `${q.year}_${q.question_num}`;
}

/**
 * [설계 의도] 메인 대시보드/모의고사 화면과 동일하게 jc_theme 값을 읽어 적용합니다.
 */
function eeInitTheme() {
    const saved = localStorage.getItem(EE_THEME_KEY);
    document.body.setAttribute('data-theme', (saved === 'light') ? 'light' : 'dark');
}

document.addEventListener('DOMContentLoaded', () => {
    eeInitTheme();
    eeLoadQuestions();
});

function eeLoadQuestions() {
    fetch('/api/yearly-exam/exception-questions')
        .then(res => res.ok ? res.json() : [])
        .catch(() => [])
        .then(data => {
            EEState.questions = Array.isArray(data) ? data : [];
            document.getElementById('loading-view').style.display = 'none';

            if (EEState.questions.length === 0) {
                document.getElementById('empty-view').style.display = 'flex';
                return;
            }

            document.getElementById('practice-view').style.display = 'block';
            eeRenderQuestion();
        });
}

function eeRenderQuestion() {
    const q = EEState.questions[EEState.currentIdx];
    if (!q) return;

    document.getElementById('ee-progress-text').textContent =
        `문항 ${EEState.currentIdx + 1} / ${EEState.questions.length}`;
    document.getElementById('ee-progress-fill').style.width =
        `${((EEState.currentIdx + 1) / EEState.questions.length) * 100}%`;

    document.getElementById('ee-meta-subject').textContent = EE_SUBJECT_NAMES[q.subject] || q.subject;
    document.getElementById('ee-meta-qid').textContent = `${q.year}년 ${q.question_num}번`;

    const conceptEl = document.getElementById('ee-meta-concept');
    if (q.concepts && q.concepts.length > 0) {
        const text = q.concepts.join(' · ');
        conceptEl.textContent = text;
        conceptEl.title = text;
        conceptEl.style.display = '';
    } else {
        conceptEl.style.display = 'none';
    }

    // 리치 에디터로 저장된 이미지 포함 HTML을 그대로 렌더링
    document.getElementById('ee-question-text').innerHTML = q.question;

    const container = document.getElementById('ee-options-container');
    container.innerHTML = '';
    const qKey = eeQKey(q);
    const selected = EEState.answers[qKey];

    (q.options || []).forEach((optText, i) => {
        const optNum = i + 1;
        const btn = document.createElement('button');
        btn.className = 'ee-opt-btn' + (selected === optNum ? ' selected' : '');
        btn.innerHTML = `<span class="ee-opt-num">${optNum}</span><span class="ee-opt-text">${optText}</span>`;
        btn.addEventListener('click', (event) => eeHandleOptionClick(event, btn, qKey, optNum));
        container.appendChild(btn);
    });

    document.getElementById('ee-btn-prev').disabled = (EEState.currentIdx === 0);
    document.getElementById('ee-btn-next').disabled = (EEState.currentIdx === EEState.questions.length - 1);

    if (window.lucide) lucide.createIcons();
}

/**
 * [설계 의도] 보기 텍스트를 드래그해 복사하려는 시도가 클릭으로 이어졌을 때,
 * 정답 선택이 함께 토글되지 않도록 막습니다(오답 복습 스케줄러 review.js와 동일한 패턴).
 */
function eeHandleOptionClick(event, buttonEl, qKey, optNum) {
    const sel = (window.getSelection && window.getSelection()) ? window.getSelection() : null;
    const hasSelection = !!(sel && !sel.isCollapsed && sel.toString && sel.toString().trim().length > 0);
    const clickedTextNode = !!(event && event.target && event.target.closest && event.target.closest('.ee-opt-text'));

    if (hasSelection && clickedTextNode && buttonEl && sel.rangeCount > 0) {
        const range = sel.getRangeAt(0);
        if (buttonEl.contains(range.startContainer) || buttonEl.contains(range.endContainer)) {
            return;
        }
    }
    if (sel && sel.removeAllRanges) sel.removeAllRanges();

    EEState.answers[qKey] = optNum;
    eeRenderQuestion();
}

function eePrev() {
    if (EEState.currentIdx > 0) {
        EEState.currentIdx -= 1;
        eeRenderQuestion();
    }
}

function eeNext() {
    if (EEState.currentIdx < EEState.questions.length - 1) {
        EEState.currentIdx += 1;
        eeRenderQuestion();
    }
}

/**
 * [설계 의도] 실제 시험처럼 전부 답한 뒤 한 번에 채점합니다. 아직 안 푼 문항이 있으면
 * 확인을 한 번 거치고, 그래도 진행하면 미응답 문항은 오답으로 처리합니다.
 */
function eeSubmit() {
    const total = EEState.questions.length;
    const answeredCount = Object.keys(EEState.answers).length;
    if (answeredCount < total) {
        const proceed = confirm(
            `아직 ${total - answeredCount}문항에 답하지 않았습니다. 그래도 채점할까요? (안 푼 문항은 오답 처리됩니다)`
        );
        if (!proceed) return;
    }

    const details = EEState.questions.map(q => {
        const qKey = eeQKey(q);
        const userChoice = EEState.answers[qKey] ? [EEState.answers[qKey]] : [];
        const correctAnswer = Array.isArray(q.answer) ? q.answer : [];
        const isCorrect = userChoice.length > 0 && correctAnswer.length > 0 &&
            userChoice.length === correctAnswer.length &&
            userChoice.every(v => correctAnswer.includes(v));

        return {
            subject: q.subject,
            year: q.year,
            question_num: q.question_num,
            q_id: qKey,
            user_choice: userChoice,
            correct_answer: correctAnswer,
            is_correct: isCorrect,
            elapsed_time: 0
        };
    });

    fetch('/api/yearly-exam/submit-exception', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ details })
    })
        .catch(err => console.error('예외 모의고사 제출 실패:', err))
        .then(() => eeRenderResult(details));
}

function eeRenderResult(details) {
    document.getElementById('practice-view').style.display = 'none';
    document.getElementById('result-view').style.display = 'block';

    const correctCount = details.filter(d => d.is_correct).length;
    const total = details.length;
    document.getElementById('ee-result-score').textContent = `${correctCount} / ${total}`;
    document.getElementById('ee-result-rate').textContent = `${total > 0 ? Math.round(correctCount / total * 100) : 0}%`;

    const listEl = document.getElementById('ee-result-list');
    listEl.innerHTML = EEState.questions.map((q, idx) => {
        const d = details[idx];
        const qKey = eeQKey(q);
        const badge = d.is_correct
            ? '<span class="ee-result-badge correct">정답</span>'
            : '<span class="ee-result-badge wrong">오답</span>';
        const conceptText = (q.concepts && q.concepts.length > 0) ? q.concepts.join(' · ') : '미분류';
        const plainQuestion = (q.question || '').replace(/<[^>]+>/g, '');

        const optionsHtml = (q.options || []).map((opt, i) => {
            const n = i + 1;
            const isAns = (q.answer || []).includes(n);
            const isMine = (d.user_choice || []).includes(n);
            let style = '';
            if (isAns) style = 'color: var(--success); font-weight: 700;';
            else if (isMine) style = 'color: var(--error); font-weight: 700;';
            const tag = isAns ? ' ✔' : ((isMine) ? ' (내 선택)' : '');
            return `<div style="padding: 0.15rem 0; ${style}">${n}. ${opt}${tag}</div>`;
        }).join('');

        return `
            <div class="ee-result-item" onclick="eeToggleResultDetail('${qKey}')">
                <div class="ee-result-item-header">
                    ${badge}
                    <span class="ee-meta-tag" style="background: transparent; border-color: var(--card-border); color: var(--text-secondary);">${EE_SUBJECT_NAMES[q.subject] || q.subject} · ${q.year}년 ${q.question_num}번</span>
                    <span class="ee-result-item-question">${plainQuestion.slice(0, 40)}${plainQuestion.length > 40 ? '…' : ''}</span>
                </div>
                <div class="ee-result-detail" id="ee-result-detail-${qKey}" style="display: none;">
                    <div class="ee-answer-line"><b>개념:</b> ${conceptText}</div>
                    <div style="margin: 0.5rem 0;">${optionsHtml}</div>
                    ${q.explanation ? `<div style="border-top: 1px dashed var(--card-border); padding-top: 0.5rem;"><b>해설:</b> ${q.explanation}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');

    if (window.lucide) lucide.createIcons();
}

function eeToggleResultDetail(qKey) {
    const el = document.getElementById(`ee-result-detail-${qKey}`);
    if (!el) return;
    el.style.display = (el.style.display === 'none') ? 'block' : 'none';
}
