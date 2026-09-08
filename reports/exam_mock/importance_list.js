/**
 * ==========================================================================
 * [중요도별 문제 리스트 - importance_list.js]
 * 과목/중요도 조건으로 문제·정답·해설을 리스트로 훑어보고, 중요도를 바로
 * 수정할 수 있는 가벼운 전용 화면입니다.
 * ==========================================================================
 */

const IL_THEME_KEY = 'jc_theme';
const IL_IMPORTANCE_ORDER = { '상': 0, '중': 1, '하': 2, '예외': 3 };
const IL_SUBJECT_NAMES = {
    PM: '사업관리', SE: '소공', DB: 'DB', SA: '시구', SC: '보안'
};

const ILState = {
    subject: 'all',
    items: [],       // 현재 선택된 과목 조건으로 서버에서 받아온 원본 문항 목록
    pending: {},     // qId -> 아직 저장하지 않은 새 중요도 값
};

function ilInitTheme() {
    const saved = localStorage.getItem(IL_THEME_KEY);
    document.body.setAttribute('data-theme', (saved === 'light') ? 'light' : 'dark');
}

document.addEventListener('DOMContentLoaded', () => {
    ilInitTheme();

    document.getElementById('il-filter-subject').addEventListener('change', (e) => {
        ILState.subject = e.target.value;
        ilLoadQuestions();
    });
    document.getElementById('il-filter-importance').addEventListener('change', ilRenderList);

    ilLoadQuestions();
});

function ilLoadQuestions() {
    document.getElementById('il-loading-view').style.display = 'flex';
    document.getElementById('il-empty-view').style.display = 'none';
    document.getElementById('il-list').style.display = 'none';
    ILState.pending = {};
    ilUpdateSaveAllButton();

    fetch(`/api/questions?subject=${encodeURIComponent(ILState.subject)}`)
        .then(res => res.ok ? res.json() : {})
        .catch(() => ({}))
        .then(data => {
            ILState.items = Object.values(data || {});
            document.getElementById('il-loading-view').style.display = 'none';
            ilRenderList();
        });
}

function ilPlainText(html) {
    return (html || '').replace(/<[^>]+>/g, '');
}

function ilRenderList() {
    const importanceFilter = document.getElementById('il-filter-importance').value;

    let items = ILState.items.slice();
    if (importanceFilter !== 'all') {
        items = items.filter(q => (q.importance || '중') === importanceFilter);
    }
    items.sort((a, b) => {
        const rankDiff = (IL_IMPORTANCE_ORDER[a.importance] ?? 1) - (IL_IMPORTANCE_ORDER[b.importance] ?? 1);
        if (rankDiff !== 0) return rankDiff;
        return String(a.subject).localeCompare(String(b.subject)) || String(a.id).localeCompare(String(b.id));
    });

    document.getElementById('il-count-text').textContent = `${items.length}문항`;

    if (items.length === 0) {
        document.getElementById('il-empty-view').style.display = 'flex';
        document.getElementById('il-list').style.display = 'none';
        return;
    }

    document.getElementById('il-empty-view').style.display = 'none';
    const listEl = document.getElementById('il-list');
    listEl.style.display = 'flex';

    listEl.innerHTML = items.map(q => {
        const plainQuestion = ilPlainText(q.question);
        const answerNums = Array.isArray(q.answer) ? q.answer : [];
        const optionsHtml = (q.options || []).map((opt, i) => {
            const n = i + 1;
            const isAns = answerNums.includes(n);
            const style = isAns ? 'color: var(--success); font-weight: 700;' : '';
            const tag = isAns ? ' ✔' : '';
            return `<div style="padding: 0.15rem 0; ${style}">${n}. ${opt}${tag}</div>`;
        }).join('');
        const savedImportance = q.importance || '중';
        const displayImportance = ILState.pending[q.id] || savedImportance;

        return `
            <div class="il-item" onclick="ilToggleDetail('${q.id}')">
                <div class="il-item-header">
                    <span class="il-meta-tag">${IL_SUBJECT_NAMES[q.subject] || q.subject}</span>
                    <span class="il-item-question">${plainQuestion.slice(0, 50)}${plainQuestion.length > 50 ? '…' : ''}</span>
                    <select class="il-importance-select" id="il-importance-${q.id}" data-original="${savedImportance}" onclick="event.stopPropagation()" onchange="ilOnImportanceChange('${q.id}')">
                        ${['상', '중', '하', '예외'].map(d => `<option value="${d}" ${displayImportance === d ? 'selected' : ''}>${d}</option>`).join('')}
                    </select>
                </div>
                <div class="il-item-detail" id="il-detail-${q.id}" style="display: none;">
                    <div class="il-question-line">${q.question}</div>
                    <div style="margin-bottom: 0.5rem;">${optionsHtml}</div>
                    ${q.explanation ? `<div class="il-explanation-line"><b>해설:</b> ${q.explanation}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');

    if (window.lucide) lucide.createIcons();
}

function ilToggleDetail(qId) {
    const el = document.getElementById(`il-detail-${qId}`);
    if (!el) return;
    el.style.display = (el.style.display === 'none') ? 'block' : 'none';
}

function ilOnImportanceChange(qId) {
    const selectEl = document.getElementById(`il-importance-${qId}`);
    if (!selectEl) return;

    if (selectEl.value === selectEl.dataset.original) {
        delete ILState.pending[qId];
    } else {
        ILState.pending[qId] = selectEl.value;
    }
    ilUpdateSaveAllButton();
}

function ilUpdateSaveAllButton() {
    const btn = document.getElementById('il-save-all-btn');
    if (!btn) return;
    const count = Object.keys(ILState.pending).length;
    btn.disabled = count === 0;
    btn.textContent = count > 0 ? `저장 (${count})` : '저장';
}

function ilSaveAllChanges() {
    const entries = Object.entries(ILState.pending);
    if (entries.length === 0) return;

    const btn = document.getElementById('il-save-all-btn');
    if (btn) btn.disabled = true;

    const requests = entries.map(([qId, newImportance]) => {
        const item = ILState.items.find(q => String(q.id) === String(qId));
        if (!item) return Promise.resolve({ qId, ok: false });

        return fetch('/api/question/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: item.id,
                question: item.question,
                options: item.options,
                answer: item.answer,
                explanation: item.explanation,
                importance: newImportance
            })
        })
            .then(res => ({ qId, ok: res.ok, item, newImportance }))
            .catch(() => ({ qId, ok: false, item, newImportance }));
    });

    Promise.all(requests).then(results => {
        let successCount = 0;
        results.forEach(r => {
            if (r.ok) {
                r.item.importance = r.newImportance;
                delete ILState.pending[r.qId];
                successCount++;
            }
        });

        const failCount = results.length - successCount;
        if (failCount === 0) {
            ilShowToast(`중요도 ${successCount}건이 저장되었습니다.`, 'success');
        } else {
            ilShowToast(`${successCount}건 저장, ${failCount}건은 실패했습니다. 다시 시도해 주세요.`, 'error');
        }

        ilUpdateSaveAllButton();
        ilRenderList();
    });
}

let ilToastTimer = null;

function ilShowToast(message, type) {
    const toast = document.getElementById('il-toast');
    const textEl = document.getElementById('il-toast-text');
    const icon = toast.querySelector('i');
    if (!toast || !textEl) return;

    textEl.textContent = message;
    toast.classList.remove('il-toast-success', 'il-toast-error');
    toast.classList.add(type === 'error' ? 'il-toast-error' : 'il-toast-success');
    if (icon) icon.setAttribute('data-lucide', type === 'error' ? 'alert-circle' : 'check-circle');
    if (window.lucide) lucide.createIcons();

    toast.classList.add('il-toast-visible');
    if (ilToastTimer) clearTimeout(ilToastTimer);
    ilToastTimer = setTimeout(() => toast.classList.remove('il-toast-visible'), 2200);
}
