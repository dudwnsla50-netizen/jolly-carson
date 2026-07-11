/**
 * [단어장(Vocabulary)] JavaScript 로직
 * - API 통신, 용어 목록 렌더링, 토픽 트리(대분류>소분류) 필터/검색, SM-2 스페이스드 리피티션, 약자 분해 3단계 학습
 * - 설계 원칙: 외부 라이브러리 없이 Vanilla JS로 구현
 */

// ==========================================
// 1. 전역 상태 관리
// ==========================================
const API_BASE = '/api/vocab';
let currentSubject = 'PM';
let currentTopicId = null;
let currentSort = 'topic';
let showTrash = false; // true면 숨김(휴지통) 용어만 조회
let allTerms = [];
let topicTree = []; // [{id, name, count, direct_count, children:[...]}]
let studyCards = [];
let studyIndex = 0;
let studyStep = 0; // 0: 약자, 1: 영문, 2: 한글+정의

// ==========================================
// 1-1. 테마 (다크/라이트) — 다른 대시보드 페이지와 동일한 localStorage 키(jc_theme) 공유
// ==========================================
const THEME_STORAGE_KEY = 'jc_theme';

function applyTheme(theme) {
    const normalized = theme === 'light' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', normalized);
    const select = document.getElementById('theme-select');
    if (select) select.value = normalized;
}

function onThemeChange(theme) {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    applyTheme(theme);
}

// 스타일 깜빡임 방지를 위해 스크립트 로드 시점에 즉시 적용 (DOMContentLoaded 이전)
applyTheme(localStorage.getItem(THEME_STORAGE_KEY) || 'dark');

// ==========================================
// 1-2. 사이드바(토픽 그룹) 접기/펼치기
// ==========================================
const SIDEBAR_STORAGE_KEY = 'vocab_sidebar_collapsed';

function applySidebarCollapsed(collapsed) {
    const sidebar = document.getElementById('sidebar');
    const btn = document.getElementById('sidebar-toggle-btn');
    if (!sidebar) return;
    sidebar.classList.toggle('collapsed', collapsed);
    if (btn) btn.textContent = collapsed ? '▶' : '◀';
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const collapsed = !sidebar.classList.contains('collapsed');
    localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? '1' : '0');
    applySidebarCollapsed(collapsed);
}

applySidebarCollapsed(localStorage.getItem(SIDEBAR_STORAGE_KEY) === '1');

// ==========================================
// 2. API 통신 헬퍼
// ==========================================
async function apiGet(endpoint, params = {}) {
    const qs = new URLSearchParams(params).toString();
    const url = qs ? `${API_BASE}${endpoint}?${qs}` : `${API_BASE}${endpoint}`;
    const res = await fetch(url);
    return res.json();
}

async function apiPost(endpoint, body) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    return res.json();
}

// ==========================================
// 3. 초기화 및 데이터 로드
// ==========================================
async function init() {
    await loadStats();
    await loadTopics();
    await loadTerms();
}

async function loadStats() {
    try {
        const data = await apiGet('/stats', currentSubject ? { subject: currentSubject } : {});
        if (!data.success) return;

        document.getElementById('stat-total').textContent = data.total || 0;
        document.getElementById('stat-abbr').textContent = data.abbreviation_count || 0;
        document.getElementById('stat-starred').textContent = data.starred_count || 0;
        document.getElementById('stat-due').textContent = data.due_today || 0;

        // 암기 분포
        const m = data.mastery_distribution || {};
        const learned = (parseInt(m['1']) || 0) + (parseInt(m['2']) || 0);
        document.getElementById('stat-learned').textContent = learned;
    } catch (e) {
        console.error('통계 로드 실패:', e);
    }
}

// ==========================================
// 4. 토픽 트리 (대분류 > 소분류) 렌더링
// ==========================================
async function loadTopics() {
    try {
        // 현재 collapsed된 토픽 ID 백업
        const collapsedIds = [];
        document.querySelectorAll('.topic-children.collapsed').forEach(wrap => {
            if (wrap.dataset.parentId) {
                collapsedIds.push(String(wrap.dataset.parentId));
            }
        });

        const data = await apiGet('/topics', currentSubject ? { subject: currentSubject } : {});
        if (!data.success) return;

        topicTree = data.topics || [];

        const sidebar = document.getElementById('topic-list');
        sidebar.innerHTML = '';

        // "전체" 항목 (대분류 count 합산)
        const totalCount = topicTree.reduce((sum, t) => sum + (t.count || 0), 0);
        sidebar.appendChild(createTopicItem('전체', totalCount, null, 0));

        for (const major of topicTree) {
            const hasChildren = major.children && major.children.length > 0;
            const row = document.createElement('div');
            row.className = 'topic-major-row';

            const isCollapsed = collapsedIds.includes(String(major.id));
            const majorItem = createTopicItem(major.name, major.count, major.id, 0, hasChildren, isCollapsed);
            row.appendChild(majorItem);

            if (hasChildren) {
                const childWrap = document.createElement('div');
                childWrap.className = 'topic-children';
                childWrap.dataset.parentId = major.id;
                if (isCollapsed) {
                    childWrap.classList.add('collapsed');
                }
                for (const minor of major.children) {
                    childWrap.appendChild(createTopicItem(minor.name, minor.count, minor.id, 1));
                }
                row.appendChild(childWrap);
            }

            sidebar.appendChild(row);
        }

        // "휴지통" 항목 (숨긴 용어 — 별도 그룹, 대분류 트리와 무관하게 항상 하단 고정)
        sidebar.appendChild(createTrashItem(data.trash_count || 0));

        populateTopicMajorSelect();
    } catch (e) {
        console.error('토픽 로드 실패:', e);
    }
}

function createTopicItem(name, count, topicId, level, hasChildren = false, isCollapsed = false) {
    const div = document.createElement('div');
    div.className = 'topic-item' + (!showTrash && currentTopicId === topicId ? ' active' : '');
    div.style.paddingLeft = `${12 + level * 16}px`;

    const toggleHtml = hasChildren ? `<span class="topic-toggle" data-parent-id="${topicId}">${isCollapsed ? '▸' : '▾'}</span>` : '';
    div.innerHTML = `${toggleHtml}<span class="topic-name">${name}</span><span class="topic-count">${count}</span>`;

    div.onclick = (ev) => {
        if (ev.target.classList.contains('topic-toggle')) {
            ev.stopPropagation();
            const wrap = document.querySelector(`.topic-children[data-parent-id="${topicId}"]`);
            if (wrap) {
                wrap.classList.toggle('collapsed');
                ev.target.textContent = wrap.classList.contains('collapsed') ? '▸' : '▾';
            }
            return;
        }
        currentTopicId = topicId;
        showTrash = false;
        document.querySelectorAll('.topic-item').forEach(el => el.classList.remove('active'));
        div.classList.add('active');
        loadTerms();
    };
    return div;
}

// "휴지통" 그룹 항목 — 숨긴(암기 완료 등으로 감춘) 용어를 모아서 보여주는 가상 그룹
function createTrashItem(count) {
    const div = document.createElement('div');
    div.className = 'topic-item trash-item' + (showTrash ? ' active' : '');
    div.style.marginTop = '10px';
    div.innerHTML = `<span class="topic-name">🗑 휴지통</span><span class="topic-count">${count}</span>`;

    div.onclick = () => {
        showTrash = true;
        document.querySelectorAll('.topic-item').forEach(el => el.classList.remove('active'));
        div.classList.add('active');
        loadTerms();
    };
    return div;
}

// 트리 전체 펼치기 / 전체 접기
function expandAllTopics() {
    document.querySelectorAll('.topic-children').forEach(wrap => wrap.classList.remove('collapsed'));
    document.querySelectorAll('.topic-toggle').forEach(t => t.textContent = '▾');
}

function collapseAllTopics() {
    document.querySelectorAll('.topic-children').forEach(wrap => wrap.classList.add('collapsed'));
    document.querySelectorAll('.topic-toggle').forEach(t => t.textContent = '▸');
}

// 용어 추가/편집 폼의 대분류 드롭다운을 현재 토픽 트리 기준으로 채웁니다.
function populateTopicMajorSelect() {
    const select = document.querySelector('#term-form select[name="topic_major"]');
    if (!select) return;
    const current = select.value;
    select.innerHTML = topicTree.map(t => `<option value="${t.name}">${t.name}</option>`).join('')
        || '<option value="기타">기타</option>';
    if (current && topicTree.some(t => t.name === current)) select.value = current;
    updateTopicMinorSuggestions();
}

// 선택된 대분류 아래 존재하는 소분류 이름들을 datalist로 제안합니다.
function updateTopicMinorSuggestions() {
    const select = document.querySelector('#term-form select[name="topic_major"]');
    const datalist = document.getElementById('topic-minor-suggestions');
    if (!select || !datalist) return;
    const major = topicTree.find(t => t.name === select.value);
    const minors = major ? major.children.map(c => c.name) : [];
    datalist.innerHTML = minors.map(m => `<option value="${m}"></option>`).join('');
}

async function loadTerms() {
    try {
        const params = { sort: currentSort };
        if (currentSubject) params.subject = currentSubject;

        if (showTrash) {
            params.trash = 'true';
        } else {
            if (currentTopicId) params.topic_id = currentTopicId;

            const starredOnly = document.getElementById('starred-filter')?.checked;
            if (starredOnly) params.starred = 'true';
        }

        const searchVal = document.getElementById('search-input').value.trim();
        if (searchVal) params.q = searchVal;

        const data = await apiGet('/terms', params);
        if (!data.success) return;

        allTerms = data.terms;
        renderTerms(allTerms);

        document.getElementById('terms-count').textContent = `${data.count}개 용어`;
    } catch (e) {
        console.error('용어 로드 실패:', e);
    }
}

// ==========================================
// 5. 용어 카드 렌더링
// ==========================================
function renderTerms(terms) {
    const grid = document.getElementById('terms-grid');

    if (!terms.length) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="emoji">📚</div>
                <p>등록된 용어가 없습니다.</p>
                <p style="font-size:0.8rem; margin-top:8px; color:var(--text-muted)">AI 추출을 실행하거나 직접 용어를 추가해보세요.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = terms.map(t => {
        const abbr = t.abbreviation || '';
        const en = t.term_en || '';
        const starred = t.is_starred ? 'starred' : '';
        const masteryClass = `mastery-${t.mastery_level || 0}`;
        const masteryLabels = { 0: '미학습', 1: '학습중', 2: '완료' };
        const masteryLabel = masteryLabels[t.mastery_level || 0];
        const freq = t.frequency || 1;

        const keywords = (t.related_keywords || []).slice(0, 3).map(k =>
            `<span class="term-tag">${k}</span>`
        ).join('');

        const topicLabel = t.topic_minor ? `${t.topic_major} · ${t.topic_minor}` : t.topic_major;
        
        // 뜻 미입력 여부 판단
        const isPending = !t.definition || t.definition.includes("뜻을 입력해주세요.");
        const pendingBadge = isPending ? `<span class="pending-badge" style="background:rgba(239, 68, 68, 0.15); color:#ef4444; border: 1px solid rgba(239,68,68,0.3); font-size:0.7rem; padding:2px 6px; border-radius:4px; font-weight:600; margin-left:8px; display:inline-flex; align-items:center; gap:3px;">⚠️ 뜻 미입력</span>` : '';

        return `
        <div class="term-row ${isPending ? 'pending-term' : ''}" onclick="showTermDetail(${t.id})" data-term-id="${t.id}">
            <span class="row-mastery-dot ${masteryClass}" title="${masteryLabel}"></span>
            <span class="row-ko">${t.term_ko}${pendingBadge}</span>
            <span class="row-abbr ${abbr ? '' : 'row-abbr-empty'}">${abbr || '—'}</span>
            <span class="row-en">${en || ''}</span>
            <div class="term-def" style="${isPending ? 'color:var(--text-muted); font-style:italic;' : ''}">${t.definition}</div>
            <div class="row-tags">
                <span class="term-topic-tag">${topicLabel}</span>
                ${keywords}
            </div>
            <div class="row-actions">
                <span class="term-freq" title="기출 등장 횟수">🔥${freq}</span>
                <span class="term-star ${starred}" onclick="event.stopPropagation(); toggleStar(${t.id})" title="즐겨찾기">
                    ${t.is_starred ? '⭐' : '☆'}
                </span>
                <span class="term-hide" onclick="event.stopPropagation(); toggleHideTerm(${t.id})" title="${showTrash ? '복원' : '숨기기(암기 완료)'}">
                    ${showTrash ? '♻️' : '🙈'}
                </span>
                <span class="term-delete" onclick="event.stopPropagation(); quickDeleteTerm(${t.id})" title="삭제">🗑</span>
            </div>
        </div>
        `;
    }).join('');
}

// ==========================================
// 6. 즐겨찾기 토글 / 숨기기(휴지통) / 빠른 삭제
// ==========================================
async function toggleStar(termId) {
    const row = document.querySelector(`.term-row[data-term-id="${termId}"]`);
    const starBtn = row ? row.querySelector('.term-star') : null;
    
    if (starBtn) {
        const isStarred = starBtn.classList.contains('starred');
        starBtn.classList.toggle('starred', !isStarred);
        starBtn.textContent = isStarred ? '☆' : '⭐';
        
        // 메모리 상의 allTerms 상태도 업데이트하여 무결성 유지
        const term = allTerms.find(t => t.id === termId);
        if (term) term.is_starred = !isStarred;
    }
    
    try {
        await apiPost('/term/star', { id: termId });
        await loadStats();
    } catch (e) {
        console.error('즐겨찾기 토글 실패:', e);
    }
}

async function toggleHideTerm(termId) {
    const row = document.querySelector(`.term-row[data-term-id="${termId}"]`);
    if (row) {
        row.classList.add('fade-out');
        setTimeout(() => row.remove(), 300);
    }
    
    try {
        await apiPost('/term/hide', { id: termId });
        // 데이터 정합성을 위해 백그라운드 갱신
        loadTopics();
        loadStats();
    } catch (e) {
        console.error('숨기기 토글 실패:', e);
    }
}

async function quickDeleteTerm(termId) {
    if (!confirm('이 용어를 삭제하시겠습니까?')) return;
    
    const row = document.querySelector(`.term-row[data-term-id="${termId}"]`);
    if (row) {
        row.classList.add('fade-out');
        setTimeout(() => row.remove(), 300);
    }
    
    try {
        await apiPost('/term/delete', { id: termId });
        // 데이터 정합성을 위해 백그라운드 갱신
        loadTopics();
        loadStats();
    } catch (e) {
        console.error('삭제 실패:', e);
    }
}

// ==========================================
// 7. 용어 상세 / 편집 모달
// ==========================================
function showTermDetail(termId) {
    const term = allTerms.find(t => t.id === termId);
    if (!term) return;
    openEditModal(term);
}

function openAddModal() {
    openEditModal(null);
}

function openEditModal(term) {
    const overlay = document.getElementById('form-modal-overlay');
    const title = document.getElementById('form-modal-title');
    const form = document.getElementById('term-form');

    title.textContent = term ? '용어 편집' : '새 용어 추가';

    form.elements['term_ko'].value = term?.term_ko || '';
    form.elements['term_en'].value = term?.term_en || '';
    form.elements['abbreviation'].value = term?.abbreviation || '';
    form.elements['definition'].value = term?.definition || '';
    populateTopicMajorSelect();
    form.elements['topic_major'].value = term?.topic_major || (topicTree[0]?.name || '기타');
    updateTopicMinorSuggestions();
    form.elements['topic_minor'].value = term?.topic_minor || '';
    form.elements['related_keywords'].value = (term?.related_keywords || []).join(', ');
    form.elements['source'].value = (term?.source || []).join(', ');
    form.dataset.termId = term?.id || '';

    overlay.classList.add('active');
}

function closeFormModal() {
    document.getElementById('form-modal-overlay').classList.remove('active');
}

async function submitTermForm(e) {
    e.preventDefault();
    const form = e.target;
    const termId = form.dataset.termId;

    const body = {
        term_ko: form.elements['term_ko'].value.trim(),
        term_en: form.elements['term_en'].value.trim(),
        abbreviation: form.elements['abbreviation'].value.trim(),
        definition: form.elements['definition'].value.trim(),
        subject: currentSubject || 'PM',
        topic_major: form.elements['topic_major'].value.trim() || '기타',
        topic_minor: form.elements['topic_minor'].value.trim(),
        related_keywords: form.elements['related_keywords'].value.split(',').map(s => s.trim()).filter(Boolean),
        source: form.elements['source'].value.split(',').map(s => s.trim()).filter(Boolean)
    };

    if (!body.term_ko) {
        alert('한글 용어명은 필수입니다.');
        return;
    }
    if (!body.definition) {
        body.definition = '뜻을 입력해주세요.';
    }

    try {
        if (termId) {
            body.id = parseInt(termId);
            await apiPost('/term/update', body);
        } else {
            await apiPost('/term', body);
        }
        closeFormModal();
        await loadTerms();
        await loadTopics();
        await loadStats();
    } catch (e) {
        console.error('저장 실패:', e);
        alert('저장 중 오류가 발생했습니다.');
    }
}

async function deleteCurrentTerm() {
    const form = document.getElementById('term-form');
    const termId = form.dataset.termId;
    if (!termId) return;

    if (!confirm('이 용어를 삭제하시겠습니까?')) return;

    try {
        await apiPost('/term/delete', { id: parseInt(termId) });
        closeFormModal();
        await loadTerms();
        await loadTopics();
        await loadStats();
    } catch (e) {
        console.error('삭제 실패:', e);
    }
}

// ==========================================
// 8. 학습 모드 (SRS + 약자 분해 3단계)
// ==========================================
async function startStudySession() {
    try {
        const params = { limit: 20 };
        if (currentSubject) params.subject = currentSubject;

        const data = await apiGet('/srs/due', params);
        if (!data.success || !data.cards.length) {
            alert('오늘 복습할 카드가 없습니다! 🎉');
            return;
        }

        studyCards = data.cards;
        studyIndex = 0;
        studyStep = 0;

        document.getElementById('study-modal-overlay').classList.add('active');
        renderStudyCard();
    } catch (e) {
        console.error('학습 세션 시작 실패:', e);
    }
}

function closeStudyModal() {
    document.getElementById('study-modal-overlay').classList.remove('active');
    // 닫을 때 통계 갱신
    loadStats();
    loadTerms();
}

function renderStudyCard() {
    if (studyIndex >= studyCards.length) {
        // 학습 완료
        document.getElementById('study-body').innerHTML = `
            <div style="padding: 40px;">
                <div style="font-size: 3rem; margin-bottom: 16px;">🎉</div>
                <h3 style="margin-bottom: 8px;">학습 세션 완료!</h3>
                <p style="color: var(--text-muted);">총 ${studyCards.length}개 카드를 복습했습니다.</p>
            </div>
        `;
        document.getElementById('study-footer').style.display = 'none';
        return;
    }

    const card = studyCards[studyIndex];
    const abbr = card.abbreviation || card.term_ko.substring(0, 4);
    const en = card.term_en || '';
    const ko = card.term_ko;
    const def = card.definition;

    // 진행률
    document.getElementById('study-progress').textContent = `${studyIndex + 1} / ${studyCards.length}`;
    document.getElementById('study-footer').style.display = 'block';

    // 3단계 스텝 도트
    const dots = document.querySelectorAll('.step-dot');
    dots.forEach((d, i) => {
        d.className = 'step-dot';
        if (i < studyStep) d.classList.add('done');
        if (i === studyStep) d.classList.add('active');
    });

    const body = document.getElementById('study-body');

    if (studyStep === 0) {
        // Step 1: 약자만 표시
        body.innerHTML = `
            <div class="study-step-label">Step 1 — 약자 보기</div>
            <div class="study-abbr">${abbr}</div>
            <div class="study-hint" style="margin-top: 24px;">이 약자의 뜻을 떠올려보세요</div>
            <button class="btn btn-primary" style="margin-top: 20px;" onclick="advanceStep()">확인하기 →</button>
        `;
    } else if (studyStep === 1) {
        // Step 2: 영문 풀네임 (+ 글자 분해)
        let decomposed = '';
        if (abbr && en) {
            const words = en.split(' ');
            decomposed = words.map(w => {
                const firstChar = w.charAt(0).toUpperCase();
                const isMatch = abbr.toUpperCase().includes(firstChar);
                return `<span style="color: ${isMatch ? 'var(--accent-violet)' : 'var(--text-secondary)'}; font-weight: ${isMatch ? '700' : '400'}">${isMatch ? '<u>' + firstChar + '</u>' + w.slice(1) : w}</span>`;
            }).join(' ');
        }

        body.innerHTML = `
            <div class="study-step-label">Step 2 — 영문 풀네임</div>
            <div class="study-abbr" style="font-size: 1.8rem; margin-bottom: 8px;">${abbr}</div>
            <div style="font-size: 1.1rem; line-height: 1.6; margin-top: 12px;">${decomposed || en || '(영문명 없음)'}</div>
            <div class="study-hint" style="margin-top: 20px;">각 글자의 의미를 분해해서 이해하세요</div>
            <button class="btn btn-primary" style="margin-top: 20px;" onclick="advanceStep()">뜻 확인 →</button>
        `;
    } else {
        // Step 3: 한글 뜻 + 정의 → 난이도 평가
        body.innerHTML = `
            <div class="study-step-label">Step 3 — 한글 뜻 + 정의</div>
            <div class="study-abbr" style="font-size: 1.5rem;">${abbr}</div>
            <div class="study-ko" style="margin-top: 12px;">${ko}</div>
            ${en ? `<div style="font-size: 0.85rem; color: var(--text-muted); font-style: italic;">${en}</div>` : ''}
            <div class="study-def" style="margin-top: 12px; text-align: left; max-width: 400px; margin-left: auto; margin-right: auto;">${def}</div>
            ${card.related_keywords && card.related_keywords.length ? `
                <div class="term-tags" style="justify-content: center; margin-top: 12px;">
                    ${card.related_keywords.map(k => `<span class="term-tag">${k}</span>`).join('')}
                </div>
            ` : ''}
        `;
    }
}

function advanceStep() {
    studyStep++;
    if (studyStep > 2) studyStep = 2;
    renderStudyCard();

    // Step 도트 갱신
    const dots = document.querySelectorAll('.step-dot');
    dots.forEach((d, i) => {
        d.className = 'step-dot';
        if (i < studyStep) d.classList.add('done');
        if (i === studyStep) d.classList.add('active');
    });
}

async function submitReview(quality) {
    const card = studyCards[studyIndex];
    if (!card) return;

    try {
        await apiPost('/srs/review', {
            term_id: card.id,
            quality: quality
        });
    } catch (e) {
        console.error('복습 기록 실패:', e);
    }

    // 다음 카드로
    studyIndex++;
    studyStep = 0;
    renderStudyCard();
}

// ==========================================
// 9. 이벤트 핸들러
// ==========================================
function onSubjectChange(subject) {
    currentSubject = subject;
    currentTopicId = null;
    showTrash = false;

    // 과목 탭 활성화
    document.querySelectorAll('.subject-tab').forEach(el => {
        el.classList.toggle('active', el.dataset.subject === subject);
    });

    loadStats();
    loadTopics();
    loadTerms();
}

function onSortChange(sort) {
    currentSort = sort;
    loadTerms();
}

function onSearch() {
    loadTerms();
}

// 검색 입력 시 디바운스
let searchTimer;
function onSearchInput() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadTerms(), 300);
}

// ==========================================
// 10. 페이지 로드 시 초기화
// ==========================================
document.addEventListener('DOMContentLoaded', init);
