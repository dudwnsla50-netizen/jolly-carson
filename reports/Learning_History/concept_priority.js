/**
 * [개념 우선순위 분석 화면]
 * - 서버의 /api/analytics/concept-priority 를 호출하여 과목별 개념 단위로
 *   "중요한 개념(최근 출제빈도 기준)"과 "자주 나오는데 약한 개념(실시간 개인 성과 교차)"을 렌더링합니다.
 * - 개인 성과 지표(내 시도/오답률)는 서버가 quiz_history/yearly_exam_history를 매 요청마다 다시 집계하므로,
 *   퀴즈를 풀고 이 화면에 돌아올 때마다 최신 값으로 반영됩니다.
 */

const CP_STATE = {
    data: null,
    activeSubject: 'PM',
    currentScored: [],
    openWeakIdx: null,
    openQid: null,
};

const CP_SUBJECT_LABELS = {
    PM: 'PM 사업관리',
    SE: 'SE 소프트웨어공학',
    DB: 'DB 데이터베이스',
    SA: 'SA 시스템아키텍처',
    SC: 'SC 보안',
};

function cpEscape(s) {
    if (s === undefined || s === null) return '';
    return String(s).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}

async function cpInit() {
    const tabBar = document.getElementById('cp-tab-bar');
    if (tabBar) {
        tabBar.querySelectorAll('.wrong-top-tab-btn').forEach((btn) => {
            btn.addEventListener('click', () => cpSwitchTab(btn.dataset.subject));
        });
    }

    const importantTbody = document.getElementById('cp-important-tbody');
    const weakTbody = document.getElementById('cp-weak-tbody');
    if (weakTbody) {
        weakTbody.addEventListener('click', (evt) => {
            const row = evt.target.closest('tr.wrong-top-row');
            if (row) {
                cpToggleWeak(Number(row.dataset.idx));
                return;
            }
            const chip = evt.target.closest('.cp-qchip');
            if (chip) {
                cpShowQuestion(chip.dataset.qid, Number(chip.dataset.idx));
            }
        });
    }

    try {
        const res = await fetch('/api/analytics/concept-priority');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        CP_STATE.data = data;
        const methoEl = document.getElementById('cp-methodology');
        if (methoEl) {
            methoEl.innerHTML =
                `최근 3개년 = <strong>${data.recent_years_from}~${data.max_year}년</strong> 출제 기준 · ` +
                `"자주 나오는데 약한 개념"은 최근 출제빈도와 실제 학습 이력(오답률)을 매번 새로 불러와 실시간으로 계산합니다.`;
        }
        cpSwitchTab(CP_STATE.activeSubject);
    } catch (e) {
        const methoEl = document.getElementById('cp-methodology');
        if (methoEl) methoEl.textContent = '데이터를 불러오지 못했습니다. 잠시 후 새로고침 해주세요.';
        if (importantTbody) importantTbody.innerHTML = `<tr><td colspan="3" class="cp-empty">불러오기 실패</td></tr>`;
        if (weakTbody) weakTbody.innerHTML = `<tr><td colspan="5" class="cp-empty">불러오기 실패</td></tr>`;
    }
}

function cpSwitchTab(subject) {
    CP_STATE.activeSubject = subject;
    CP_STATE.openWeakIdx = null;
    CP_STATE.openQid = null;

    const tabBar = document.getElementById('cp-tab-bar');
    if (tabBar) {
        tabBar.querySelectorAll('.wrong-top-tab-btn').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.subject === subject);
        });
    }
    cpRender(subject);
}

function cpRiskInfo(concept) {
    if (concept.my_attempts < 5) {
        return { level: 'unpracticed', label: '연습부족', factor: 0.4 };
    }
    if (concept.my_wrong_rate >= 30) {
        return { level: 'high', label: '취약', factor: concept.my_wrong_rate / 100 };
    }
    if (concept.my_wrong_rate >= 15) {
        return { level: 'mid', label: '주의', factor: concept.my_wrong_rate / 100 };
    }
    return { level: 'low', label: '안정', factor: concept.my_wrong_rate / 100 };
}

function cpRender(subject) {
    if (!CP_STATE.data) return;
    const all = CP_STATE.data.concepts.filter((c) => c.subject === subject);

    // ---- 1) 중요한 개념 TOP (최근 출제빈도 기준, 개인 성과와 무관) ----
    const important = [...all]
        .sort((a, b) => b.last3yr_count - a.last3yr_count || b.exam_count_12y - a.exam_count_12y)
        .slice(0, 6);

    const impTbody = document.getElementById('cp-important-tbody');
    if (impTbody) {
        impTbody.innerHTML = important.length
            ? important
                  .map(
                      (c, i) => `
            <tr>
                <td>${i + 1}. ${cpEscape(c.concept)}</td>
                <td style="text-align:center; font-weight:700;">${c.last3yr_count}회</td>
                <td style="text-align:center; color: var(--text-secondary);">${c.exam_count_12y}회</td>
            </tr>`
                  )
                  .join('')
            : `<tr><td colspan="3" class="cp-empty">데이터가 없습니다.</td></tr>`;
    }

    // ---- 2) 자주 나오는데 약한 개념 (실시간 우선순위 스코어링) ----
    const scored = all
        .filter((c) => c.last3yr_count > 0)
        .map((c) => {
            const risk = cpRiskInfo(c);
            return { ...c, risk, score: c.last3yr_count * risk.factor };
        })
        .sort((a, b) => b.score - a.score)
        .slice(0, 8);

    CP_STATE.currentScored = scored;

    const weakTbody = document.getElementById('cp-weak-tbody');
    if (weakTbody) {
        weakTbody.innerHTML = scored.length
            ? scored
                  .map((c, idx) => {
                      const rateText = c.my_attempts > 0 ? `${c.my_wrong_rate}%` : '-';
                      return `
            <tr class="wrong-top-row" data-idx="${idx}">
                <td>${cpEscape(c.concept)}</td>
                <td style="text-align:center;">${c.last3yr_count}회</td>
                <td style="text-align:center;">${c.my_attempts}회</td>
                <td style="text-align:center; font-weight:700;">${rateText}</td>
                <td><span class="risk-badge ${c.risk.level}">${c.risk.label}</span></td>
            </tr>
            <tr class="wrong-top-detail-row" id="cp-detail-${idx}" style="display:none;">
                <td colspan="5"><div id="cp-detail-body-${idx}" class="cp-qchip-wrap"></div></td>
            </tr>`;
                  })
                  .join('')
            : `<tr><td colspan="5" class="cp-empty">이 과목은 최근 출제된 개념 중 우선순위로 꼽을 만큼 뚜렷하게 약한 부분이 없습니다.</td></tr>`;
    }
}

function cpToggleWeak(idx) {
    const el = document.getElementById(`cp-detail-${idx}`);
    if (!el) return;
    const isOpen = CP_STATE.openWeakIdx === idx;

    if (CP_STATE.openWeakIdx !== null && CP_STATE.openWeakIdx !== idx) {
        const prev = document.getElementById(`cp-detail-${CP_STATE.openWeakIdx}`);
        if (prev) prev.style.display = 'none';
    }

    if (isOpen) {
        el.style.display = 'none';
        CP_STATE.openWeakIdx = null;
        return;
    }

    el.style.display = 'table-row';
    CP_STATE.openWeakIdx = idx;
    CP_STATE.openQid = null;

    const concept = CP_STATE.currentScored[idx];
    const body = document.getElementById(`cp-detail-body-${idx}`);
    if (!body) return;

    if (!concept || !concept.wrong_questions || concept.wrong_questions.length === 0) {
        body.innerHTML = `<span style="color: var(--text-muted); font-size:0.8rem;">최근 오답 이력이 없습니다.</span>`;
        return;
    }

    body.innerHTML =
        concept.wrong_questions
            .map(
                (w) =>
                    `<button type="button" class="cp-qchip" data-qid="${w.q_id}" data-idx="${idx}">${w.q_id} · 오답 ${w.wrong_count}회</button>`
            )
            .join('') + `<div id="cp-qdetail-${idx}" style="width:100%; margin-top:0.6rem;"></div>`;
}

async function cpShowQuestion(qid, idx) {
    const target = document.getElementById(`cp-qdetail-${idx}`);
    if (!target) return;

    if (CP_STATE.openQid === qid) {
        target.innerHTML = '';
        CP_STATE.openQid = null;
        return;
    }
    CP_STATE.openQid = qid;
    target.innerHTML = `<span style="color: var(--text-muted); font-size:0.8rem;">불러오는 중...</span>`;

    try {
        const res = await fetch(`/api/question?id=${encodeURIComponent(qid)}`);
        const q = await res.json();
        const answerSet = new Set((q.answer || []).map(Number));
        const optionsHtml = (q.options || [])
            .map((opt, i) => {
                const n = i + 1;
                const isAns = answerSet.has(n);
                return `<div style="padding:0.2rem 0; ${isAns ? 'color: var(--success); font-weight:700;' : ''}">${n}. ${opt}${isAns ? ' ✔' : ''}</div>`;
            })
            .join('');

        target.innerHTML = `
            <div class="wrong-top-detail-body">
                <div style="font-weight:600; margin-bottom:0.5rem;">${q.question || ''}</div>
                <div style="margin-bottom:0.6rem;">${optionsHtml}</div>
                ${q.explanation ? `<div style="border-top:1px solid var(--card-border); padding-top:0.5rem; font-size:0.82rem;"><b>해설:</b> ${q.explanation}</div>` : ''}
            </div>`;
    } catch (e) {
        target.innerHTML = `<span style="color: var(--error);">문항 정보를 불러오지 못했습니다.</span>`;
    }
}

document.addEventListener('DOMContentLoaded', cpInit);
