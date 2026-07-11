// =======================================================
// [Jolly-Carson] 전 화면 통합 드래그 퀵 추가(Quick Add) 유틸리티
// =======================================================
(function() {
    // 중복 방지
    if (document.getElementById('floating-quick-add-btn')) return;

    // 플로팅 버튼 생성
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

    // 토스트 팝업 생성
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

    // URL/타이틀 기반 디폴트 과목 검출
    function detectDefaultSubject() {
        const path = window.location.pathname.toLowerCase();
        if (path.includes('se_')) return 'SE';
        if (path.includes('db_')) return 'DB';
        if (path.includes('sa_')) return 'SA';
        if (path.includes('sc_')) return 'SC';
        if (path.includes('pm_')) return 'PM';
        
        const title = document.title;
        if (title.includes('소프트웨어') || title.includes('SE')) return 'SE';
        if (title.includes('데이터베이스') || title.includes('DB')) return 'DB';
        if (title.includes('시스템') || title.includes('SA')) return 'SA';
        if (title.includes('보안') || title.includes('SC')) return 'SC';
        if (title.includes('사업') || title.includes('PM')) return 'PM';
        return 'PM';
    }

    // 선택 영역의 노드로부터 과목 및 출처 추론
    function findDragMeta(anchorNode) {
        let parent = anchorNode.parentElement;
        const defaultSub = detectDefaultSubject();
        if (!parent) return { subject: defaultSub, source: '대시보드 기출' };

        // 1. 모의고사 풀이 화면 검출 (#practice-view 내)
        const inPractice = parent.closest('#practice-view');
        if (inPractice) {
            const subjectTag = document.getElementById('current-subject-tag');
            const qNumLabel = document.getElementById('current-q-num-label');
            let rawSub = subjectTag ? subjectTag.textContent.trim() : '';
            let subCode = 'PM';
            if (rawSub.includes('소프트웨어') || rawSub.includes('SE')) subCode = 'SE';
            else if (rawSub.includes('데이터베이스') || rawSub.includes('DB')) subCode = 'DB';
            else if (rawSub.includes('시스템') || rawSub.includes('SA')) subCode = 'SA';
            else if (rawSub.includes('보안') || rawSub.includes('SC')) subCode = 'SC';
            
            return {
                subject: subCode,
                source: qNumLabel ? qNumLabel.textContent.trim() : '모의고사'
            };
        }

        // 2. 카드형 레이아웃 검출 (.question-card, .wrong-row, .exam-row 등)
        const card = parent.closest('.question-card, .card, .term-row, .wrong-card, .wrong-row, .exam-row, .panel-body, .accordion-content');
        if (card) {
            const textContent = card.innerText || card.textContent || '';
            const match = textContent.match(/(\d{4}년도?\s*\d+\s*번)/);
            const sourceVal = match ? match[1] : '대시보드 기출';

            let subCode = defaultSub;
            const badge = card.querySelector('.subject-badge, .badge, .subject-tag, .row-tags, .subj-badge');
            const badgeText = badge ? badge.textContent.trim() : '';
            if (badgeText.includes('소프트웨어') || badgeText.includes('SE')) subCode = 'SE';
            else if (badgeText.includes('데이터베이스') || badgeText.includes('DB')) subCode = 'DB';
            else if (badgeText.includes('시스템') || badgeText.includes('SA')) subCode = 'SA';
            else if (badgeText.includes('보안') || badgeText.includes('SC')) subCode = 'SC';
            else if (badgeText.includes('사업') || badgeText.includes('PM')) subCode = 'PM';

            return { subject: subCode, source: sourceVal };
        }

        return { subject: defaultSub, source: '대시보드 기출' };
    }

    document.addEventListener('mouseup', function(e) {
        if (e.target.id === 'floating-quick-add-btn') return;

        const selection = window.getSelection();
        const text = selection.toString().trim();

        // 2자 미만 혹은 50자 초과는 단어로 부적절하므로 무시
        if (!text || text.length < 2 || text.length > 50) {
            btn.style.display = 'none';
            return;
        }

        selectedText = text;

        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();

        // 버튼 노출 위치 지정
        btn.style.top = `${rect.top + window.scrollY - 38}px`;
        btn.style.left = `${rect.left + window.scrollX + (rect.width / 2) - 55}px`;
        btn.style.display = 'flex';
    });

    document.addEventListener('mousedown', function(e) {
        if (e.target.id !== 'floating-quick-add-btn') {
            btn.style.display = 'none';
        }
    });

    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        btn.style.display = 'none';

        if (!selectedText) return;

        const selection = window.getSelection();
        const anchorNode = selection.anchorNode;
        const meta = findDragMeta(anchorNode);

        const payload = {
            term_ko: selectedText,
            definition: "뜻을 입력해주세요.",
            subject: meta.subject,
            topic_major: "기타",
            source: [meta.source]
        };

        // 절대 경로 API 호출
        fetch('/api/vocab/term', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast(`✓ [${selectedText}] 단어장에 신규 추가되었습니다.`);
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
