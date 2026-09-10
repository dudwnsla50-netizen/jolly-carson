/**
 * ==========================================================================
 * [법령·지침 출제 현황 - law_references.js]
 * 5대 과목 공식 시험범위 및 기출 전수 스캔으로 확인된 법령/고시/지침/가이드별
 * 실제 기출 인용 건수를 과목 구분과 함께 한 화면에 보여주고, 건수를 클릭하면
 * 같은 화면에서 해당 문항을 바로 펼쳐 볼 수 있게 합니다. 연도별 건수 표의 숫자를
 * 클릭하면 그 해에 인용된 법령/지침 목록을 확인할 수 있습니다.
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
    questionMap: {},     // id -> 문항 상세 (펼쳐볼 때 /api/questions?ids=...로 필요한 것만 지연 조회해 채움)
    selectedYear: null,  // 연도별 건수 표에서 클릭한 연도 (없으면 null)
    searchQuery: '',     // 가이드·지침명 검색어
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
    fetch('/api/analytics/law-references')
        .then(res => res.ok ? res.json() : { documents: [] })
        .then(refData => {
            LawRefState.documents = refData.documents || [];
            renderYearSummary();
            renderSections();
            document.getElementById('lawref-loading').style.display = 'none';
            document.getElementById('lawref-sections').style.display = 'block';
        })
        .catch(err => {
            console.error('법령·지침 로딩 실패', err);
            document.getElementById('lawref-loading').innerHTML =
                '<p style="color: var(--text-secondary); font-size: 0.9rem;">데이터를 불러오지 못했습니다.</p>';
        });
}

// 문항 원문(질문/보기/정답/해설)은 목록 로딩 시점엔 필요 없고 펼쳐볼 때만 필요하므로,
// 아직 확보하지 못한 id만 골라 그때그때 조회해 questionMap에 채워 넣습니다.
async function ensureQuestionDetails(ids) {
    const missing = ids.filter(id => !LawRefState.questionMap[id]);
    if (missing.length === 0) return;
    try {
        const res = await fetch(`/api/questions?ids=${encodeURIComponent(missing.join(','))}`);
        if (res.ok) {
            Object.assign(LawRefState.questionMap, await res.json());
        }
    } catch (err) {
        console.error('문항 상세 조회 실패', err);
    }
}

function renderYearSummary() {
    const seenIds = new Set();
    const yearCounts = {};
    LawRefState.documents.forEach(doc => {
        doc.questions.forEach(q => {
            if (seenIds.has(q.id)) return;
            seenIds.add(q.id);
            yearCounts[q.year] = (yearCounts[q.year] || 0) + 1;
        });
    });

    const years = Object.keys(yearCounts).map(Number).sort((a, b) => a - b);
    const headerCells = years.map(y => `<th>${y}</th>`).join('') + '<th class="lawref-year-total-cell">합계</th>';
    const dataCells = years.map(y => {
        const isSelected = LawRefState.selectedYear === y;
        return `<td class="lawref-year-count ${isSelected ? 'selected' : ''}" onclick="toggleYearDetail(${y})">${yearCounts[y]}</td>`;
    }).join('') + `<td class="lawref-year-total-cell">${seenIds.size}</td>`;

    document.getElementById('lawref-year-summary').innerHTML = `
        <table class="lawref-year-table">
            <thead><tr>${headerCells}</tr></thead>
            <tbody><tr>${dataCells}</tr></tbody>
        </table>
    `;

    const detailContainer = document.getElementById('lawref-year-detail');
    if (LawRefState.selectedYear !== null && years.includes(LawRefState.selectedYear)) {
        renderYearDetail(LawRefState.selectedYear);
        detailContainer.style.display = 'block';
    } else {
        LawRefState.selectedYear = null;
        detailContainer.style.display = 'none';
        detailContainer.innerHTML = '';
    }
}

function toggleYearDetail(year) {
    LawRefState.selectedYear = (LawRefState.selectedYear === year) ? null : year;
    renderYearSummary();
}

function renderYearDetail(year) {
    const container = document.getElementById('lawref-year-detail');

    const hits = LawRefState.documents
        .map(doc => {
            const yearQuestions = doc.questions.filter(q => q.year === year);
            return yearQuestions.length ? { doc, yearQuestions } : null;
        })
        .filter(Boolean)
        .sort((a, b) => b.yearQuestions.length - a.yearQuestions.length);

    if (hits.length === 0) {
        container.innerHTML = `
            <div class="lawref-year-detail-title">${year}년에 인용된 법령·지침</div>
            <p style="color: var(--text-muted); font-size: 0.82rem;">해당 연도에 인용된 법령·지침이 없습니다.</p>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    const rowsHtml = hits.map(({ doc, yearQuestions }) => {
        const docKey = `year${year}_${docIdKey(doc.label, doc.subjects.join('-'))}`;
        const linkHtml = doc.url
            ? `<a class="lawref-source-link" href="${doc.url}" target="_blank" rel="noopener" title="최신판 원문 보기" onclick="event.stopPropagation()">
                   <i data-lucide="external-link"></i>
               </a>`
            : '';
        const subjectTagHtml = `<span class="lawref-multi-subject-tag">${doc.subjects.join('/')}</span>`;

        return `
            <div class="lawref-doc" id="lawref-doc-${docKey}">
                <div class="lawref-doc-row">
                    <span class="lawref-doc-name">${doc.label}${recentYearsLabel(doc.questions)} ${linkHtml}${subjectTagHtml}</span>
                    <button type="button" class="lawref-count-btn" onclick="toggleDetailPanel('${docKey}', '${yearQuestions.map(q => q.id).join(',')}')">
                        ${yearQuestions.length}건
                    </button>
                </div>
                <div class="lawref-detail" id="lawref-detail-${docKey}" style="display: none;"></div>
            </div>
        `;
    }).join('');

    container.innerHTML = `
        <div class="lawref-year-detail-title">${year}년에 인용된 법령·지침 (${hits.length}종)</div>
        ${rowsHtml}
    `;

    if (window.lucide) lucide.createIcons();
}

function setLawRefSearch(value) {
    LawRefState.searchQuery = value;
    renderSections();
}

function renderSections() {
    const container = document.getElementById('lawref-sections');
    const query = searchStripWhitespace(LawRefState.searchQuery).toLowerCase();

    const matchesQuery = doc => !query || searchStripWhitespace(doc.label).toLowerCase().includes(query);

    const subjectsWithDocs = LAWREF_SUBJECT_ORDER.filter(s =>
        LawRefState.documents.some(doc => (doc.subjects || []).includes(s) && matchesQuery(doc))
    );

    const html = subjectsWithDocs.map(subject => {
        const docsForSubject = LawRefState.documents.filter(doc => (doc.subjects || []).includes(subject) && matchesQuery(doc));
        const bySection = {};
        docsForSubject.forEach(doc => {
            (bySection[doc.section] = bySection[doc.section] || []).push(doc);
        });

        const sectionsHtml = SECTION_ORDER
            .filter(sec => bySection[sec] && bySection[sec].length > 0)
            .map(sec => {
                const docsHtml = bySection[sec].map(doc => renderDocRow(doc, subject)).join('');
                return `
                    <div class="lawref-section">
                        <div class="lawref-section-title">${LAWREF_SECTION_NAMES[sec] || sec}</div>
                        ${docsHtml}
                    </div>
                `;
            }).join('');

        return `
            <div class="lawref-subject-group">
                <div class="lawref-subject-heading">${LAWREF_SUBJECT_NAMES[subject] || subject}</div>
                ${sectionsHtml}
            </div>
        `;
    }).join('');

    container.innerHTML = html || '<div class="lawref-no-results">검색 결과가 없습니다.</div>';

    if (window.lucide) lucide.createIcons();
}

function recentYearsLabel(questions) {
    const years = [...new Set(questions.map(q => q.year))].sort((a, b) => b - a).slice(0, 3);
    if (years.length === 0) return '';
    return ` <span class="lawref-recent-years">(${years.map(y => `${String(y).slice(-2)}`).join(', ')})</span>`;
}

function renderDocRow(doc, subject) {
    const docKey = docIdKey(doc.label, subject);
    const subjectQuestions = doc.questions.filter(q => q.subject === subject);
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
                <span class="lawref-doc-name">${doc.label}${recentYearsLabel(subjectQuestions)} ${linkHtml}${multiSubjectHtml}</span>
                <button type="button" class="lawref-count-btn" ${disabled} onclick="toggleLawRefDetail('${docKey}')">
                    ${count}건
                </button>
            </div>
            <div class="lawref-detail" id="lawref-detail-${docKey}" style="display: none;"></div>
        </div>
    `;
}

function docIdKey(label, subject) {
    // 문서명+과목을 DOM id로 쓸 수 있는 안전한 문자열로 변환 (같은 문서가 여러 과목 구간에 걸쳐 있어도 충돌 방지)
    return `${subject}_${label}`.replace(/[^a-zA-Z0-9가-힣]/g, '_');
}

async function toggleLawRefDetail(docKey) {
    const detailEl = document.getElementById(`lawref-detail-${docKey}`);
    if (!detailEl) return;

    const isOpen = detailEl.style.display !== 'none';
    if (isOpen) {
        detailEl.style.display = 'none';
        return;
    }

    if (!detailEl.dataset.rendered) {
        const subject = docKey.split('_')[0];
        const doc = LawRefState.documents.find(d => docIdKey(d.label, subject) === docKey);
        if (doc) {
            const subjectQuestions = doc.questions
                .filter(q => q.subject === subject)
                .slice()
                .sort((a, b) => b.year - a.year || a.question_num - b.question_num);
            detailEl.innerHTML = '<div class="lawref-q-loading">불러오는 중...</div>';
            detailEl.style.display = 'flex';
            await ensureQuestionDetails(subjectQuestions.map(q => q.id));
            detailEl.innerHTML = subjectQuestions.map(q => renderQuestionItem(q)).join('');
            detailEl.dataset.rendered = '1';
            return;
        }
    }
    detailEl.style.display = 'flex';
}

async function toggleDetailPanel(docKey, questionIdsCsv) {
    const detailEl = document.getElementById(`lawref-detail-${docKey}`);
    if (!detailEl) return;

    const isOpen = detailEl.style.display !== 'none';
    if (isOpen) {
        detailEl.style.display = 'none';
        return;
    }

    if (!detailEl.dataset.rendered) {
        const questionIds = questionIdsCsv.split(',');
        const allQuestions = LawRefState.documents.flatMap(d => d.questions);
        const byId = {};
        allQuestions.forEach(q => { byId[q.id] = q; });
        const orderedRefs = questionIds.map(id => byId[id]).filter(Boolean).sort((a, b) => a.question_num - b.question_num);

        detailEl.innerHTML = '<div class="lawref-q-loading">불러오는 중...</div>';
        detailEl.style.display = 'flex';
        await ensureQuestionDetails(questionIds);
        detailEl.innerHTML = orderedRefs.map(q => renderQuestionItem(q)).join('');
        detailEl.dataset.rendered = '1';
        return;
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
    const subjectLabel = LAWREF_SUBJECT_NAMES[qRef.subject] || qRef.subject;

    return `
        <div class="lawref-q-item">
            <span class="lawref-q-tag">${qRef.year}년 ${subjectLabel} ${qRef.question_num}번</span>
            <div class="lawref-q-text">${plainQuestion}</div>
            <div class="lawref-q-answer">${optionsText}</div>
            ${full.explanation ? `<div class="lawref-q-explanation"><b>해설:</b> ${full.explanation}</div>` : ''}
        </div>
    `;
}
