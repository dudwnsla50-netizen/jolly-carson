/**
 * ==========================================================================
 * [법령·지침 출제 현황 - law_references.js]
 * 5대 과목 공식 시험범위 및 기출 전수 스캔으로 확인된 법령/고시/지침/가이드별
 * 실제 기출 인용 건수를 과목 탭으로 보여주고, 건수를 클릭하면 같은 화면에서
 * 해당 문항을 바로 펼쳐 볼 수 있게 합니다.
 * ==========================================================================
 */

const LAWREF_THEME_KEY = 'jc_theme';
const LAWREF_SUBJECT_NAMES = {
    PM: '사업관리', SE: '소프트웨어공학', DB: '데이터베이스', SA: '시스템구조', SC: '보안'
};
const LAWREF_SUBJECT_ORDER = ['PM', 'SE', 'DB', 'SA', 'SC'];
const LAWREF_SECTION_NAMES = {
    '1-a': '1-a. 정보화 및 소프트웨어 관련 법령·고시·가이드',
    '1-b': '1-b. 계약 관련 법령 및 예규',
    '1-c': '1-c. 대가산정 관련 고시 및 가이드',
    '1-d': '1-d. IT거버넌스, CoBIT 등 국외 관련 지침',
    '2-a': '2-a. 전자정부법, 정보시스템 감리기준 등 감리 법제도',
    '2-c': '2-c. 정보시스템 감리 관련 가이드',
    '4-a': '4-a. 프로젝트관리 관련 표준 및 가이드',
    'db-1': '관련 법령·지침',
    'sa-1': '관련 법령·고시',
    'sc-1': '정보보호·개인정보보호 관련 법규',
};
const SECTION_ORDER = ['1-a', '1-b', '1-c', '1-d', '2-a', '2-c', '4-a', 'db-1', 'sa-1', 'sc-1'];

let LawRefState = {
    documents: [],       // /api/analytics/law-references 응답
    questionMap: {},     // id -> 전체 문항 상세 (/api/questions?subject=all)
    activeSubject: 'PM',
};

function lawrefInitTheme() {
    const saved = localStorage.getItem(LAWREF_THEME_KEY);
    document.body.setAttribute('data-theme', (saved === 'light') ? 'light' : 'dark');
}

document.addEventListener('DOMContentLoaded', () => {
    lawrefInitTheme();
    loadLawReferences();
});

function loadLawReferences() {
    Promise.all([
        fetch('/api/analytics/law-references').then(res => res.ok ? res.json() : { documents: [] }),
        fetch('/api/questions?subject=all').then(res => res.ok ? res.json() : {})
    ])
        .then(([refData, questionsData]) => {
            LawRefState.documents = refData.documents || [];
            LawRefState.questionMap = questionsData || {};
            renderSubjectTabs();
            renderSections();
            document.getElementById('lawref-loading').style.display = 'none';
            document.getElementById('lawref-sections').style.display = 'block';
        })
        .catch(err => {
            console.error('법령·지침 출제 현황 로딩 실패', err);
            document.getElementById('lawref-loading').innerHTML =
                '<p style="color: var(--text-secondary); font-size: 0.9rem;">데이터를 불러오지 못했습니다.</p>';
        });
}

function renderSubjectTabs() {
    const subjectsWithDocs = new Set();
    LawRefState.documents.forEach(doc => (doc.subjects || []).forEach(s => subjectsWithDocs.add(s)));

    const tabs = LAWREF_SUBJECT_ORDER.filter(s => subjectsWithDocs.has(s));
    const container = document.getElementById('lawref-subject-tabs');
    container.innerHTML = tabs.map(s => `
        <button type="button" class="lawref-subject-tab ${s === LawRefState.activeSubject ? 'active' : ''}"
            onclick="selectLawRefSubject('${s}')">
            ${LAWREF_SUBJECT_NAMES[s] || s}
        </button>
    `).join('');
}

function selectLawRefSubject(subject) {
    LawRefState.activeSubject = subject;
    renderSubjectTabs();
    renderSections();
}

function renderSections() {
    const container = document.getElementById('lawref-sections');
    const activeSubject = LawRefState.activeSubject;

    const docsForSubject = LawRefState.documents.filter(doc => (doc.subjects || []).includes(activeSubject));
    const bySection = {};
    docsForSubject.forEach(doc => {
        (bySection[doc.section] = bySection[doc.section] || []).push(doc);
    });

    container.innerHTML = SECTION_ORDER
        .filter(sec => bySection[sec] && bySection[sec].length > 0)
        .map(sec => {
            const docsHtml = bySection[sec].map(doc => renderDocRow(doc, activeSubject)).join('');
            return `
                <div class="lawref-section">
                    <div class="lawref-section-title">${LAWREF_SECTION_NAMES[sec] || sec}</div>
                    ${docsHtml}
                </div>
            `;
        }).join('');

    if (window.lucide) lucide.createIcons();
}

function renderDocRow(doc, activeSubject) {
    const docKey = docIdKey(doc.label, activeSubject);
    const subjectQuestions = doc.questions.filter(q => q.subject === activeSubject);
    const count = subjectQuestions.length;
    const disabled = count === 0 ? 'disabled' : '';
    const linkHtml = doc.url
        ? `<a class="lawref-source-link" href="${doc.url}" target="_blank" rel="noopener" title="최신판 원문 보기" onclick="event.stopPropagation()">
               <i data-lucide="external-link"></i>
           </a>`
        : '';
    const multiSubjectHtml = (doc.subjects && doc.subjects.length > 1)
        ? `<span class="lawref-multi-subject-tag" title="이 문서는 여러 과목에서 함께 인용됩니다">${doc.subjects.join('/')}</span>`
        : '';

    return `
        <div class="lawref-doc" id="lawref-doc-${docKey}">
            <div class="lawref-doc-row">
                <span class="lawref-doc-name">${doc.label} ${linkHtml}${multiSubjectHtml}</span>
                <button type="button" class="lawref-count-btn" ${disabled} onclick="toggleLawRefDetail('${docKey}')">
                    ${count}건
                </button>
            </div>
            <div class="lawref-detail" id="lawref-detail-${docKey}" style="display: none;"></div>
        </div>
    `;
}

function docIdKey(label, subject) {
    // 문서명+과목을 DOM id로 쓸 수 있는 안전한 문자열로 변환 (같은 문서가 여러 과목 탭에 걸쳐 있어도 충돌 방지)
    return `${subject}_${label}`.replace(/[^a-zA-Z0-9가-힣]/g, '_');
}

function toggleLawRefDetail(docKey) {
    const detailEl = document.getElementById(`lawref-detail-${docKey}`);
    if (!detailEl) return;

    const isOpen = detailEl.style.display !== 'none';
    if (isOpen) {
        detailEl.style.display = 'none';
        return;
    }

    if (!detailEl.dataset.rendered) {
        const activeSubject = LawRefState.activeSubject;
        const doc = LawRefState.documents.find(d => docIdKey(d.label, activeSubject) === docKey);
        if (doc) {
            const subjectQuestions = doc.questions.filter(q => q.subject === activeSubject);
            detailEl.innerHTML = subjectQuestions
                .slice()
                .sort((a, b) => b.year - a.year || a.question_num - b.question_num)
                .map(q => renderQuestionItem(q))
                .join('');
            detailEl.dataset.rendered = '1';
        }
    }
    detailEl.style.display = 'flex';
}

function renderQuestionItem(qRef) {
    const full = LawRefState.questionMap[qRef.id];
    if (!full) {
        return `<div class="lawref-q-item">문항 정보를 찾을 수 없습니다 (${qRef.id})</div>`;
    }

    const plainQuestion = (full.question || '').replace(/<[^>]+>/g, '');
    const answerNums = Array.isArray(full.answer) ? full.answer : [];
    const optionsText = (full.options || []).map((opt, i) => {
        const n = i + 1;
        const isAns = answerNums.includes(n);
        return `${isAns ? '✔ ' : ''}${n}. ${opt}`;
    }).join('\n');

    return `
        <div class="lawref-q-item">
            <span class="lawref-q-tag">${qRef.year}년 ${qRef.question_num}번</span>
            <div class="lawref-q-text">${plainQuestion}</div>
            <div class="lawref-q-answer">${optionsText}</div>
            ${full.explanation ? `<div class="lawref-q-explanation"><b>해설:</b> ${full.explanation}</div>` : ''}
        </div>
    `;
}
