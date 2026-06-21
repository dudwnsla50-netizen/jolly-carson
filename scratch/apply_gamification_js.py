# -*- coding: utf-8 -*-
import os

def main():
    filepath = r"reports/js/dashboard_common.js"
    if not os.path.exists(filepath):
        print(f"파일을 찾을 수 없습니다: {filepath}")
        return
        
    with open(filepath, "rb") as f:
        content = f.read()

    # 1. initDashboard() 내부에 initGamification() 호출 추가
    target_init = b"loadQuizStatsAndMerge().then(() => {\r\n        renderDashboard();\r\n    });"
    replacement_init = b"loadQuizStatsAndMerge().then(() => {\r\n        renderDashboard();\r\n        if (typeof initGamification === 'function') {\r\n            initGamification();\r\n        }\r\n    });"
    
    target_init_lf = b"loadQuizStatsAndMerge().then(() => {\n        renderDashboard();\n    });"
    replacement_init_lf = b"loadQuizStatsAndMerge().then(() => {\n        renderDashboard();\n        if (typeof initGamification === 'function') {\n            initGamification();\n        }\n    });"

    if target_init in content:
        content = content.replace(target_init, replacement_init)
        print("initDashboard (CRLF) 수정 완료")
    elif target_init_lf in content:
        content = content.replace(target_init_lf, replacement_init_lf)
        print("initDashboard (LF) 수정 완료")
    else:
        print("Warning: initDashboard 수정 대상을 찾지 못했습니다.")

    # 2. 게이미피케이션 JS 함수 코드 추가
    gam_js = """

/**
 * ==========================================================================
 * 🎮 게이미피케이션 (EXP/Level 시스템 및 보물상자 이펙트)
 * ==========================================================================
 */

/**
 * GAM-1. 게이미피케이션 EXP/Level 시스템을 초기화합니다.
 */
function initGamification() {
    window.gamState = {
        totalExp: 0,
        level: 1,
        expInLevel: 0
    };
    
    // UI 주입
    gamInjectExpCard();
    gamInjectLevelUpOverlay();
    
    // API 조회하여 EXP 데이터 업데이트
    fetch('/api/quiz/total-exp')
        .then(res => res.ok ? res.json() : { total_exp: 0, level: 1, exp_in_level: 0 })
        .then(data => {
            window.gamState.totalExp = data.total_exp || 0;
            window.gamState.level = data.level || 1;
            window.gamState.expInLevel = data.exp_in_level || 0;
            gamUpdateExpUI();
        })
        .catch(err => {
            console.warn("[경고] 게이미피케이션 데이터 로드 실패", err);
            gamUpdateExpUI();
        });
}

/**
 * GAM-2. EXP/Level 카드 UI를 생성하여 상단에 주입합니다.
 */
function gamInjectExpCard() {
    // 이미 존재하면 스킵
    if (document.getElementById('gam-exp-card')) return;

    const card = document.createElement('div');
    card.id = 'gam-exp-card';
    card.className = 'gamification-exp-card';
    card.innerHTML = `
        <div class="gam-level-badge">
            <span class="gam-lv-label">LV</span>
            <span class="gam-lv-num" id="gam-lv-value">1</span>
        </div>
        <div class="gam-exp-wrapper">
            <div class="gam-exp-header">
                <span class="gam-exp-title">🛡️ 감리사 수험생 경험치 (EXP)</span>
                <span class="gam-exp-value" id="gam-exp-text">0 / 10 EXP</span>
            </div>
            <div class="gam-exp-bar-bg">
                <div class="gam-exp-bar-fill" id="gam-exp-fill" style="width: 0%;"></div>
            </div>
        </div>
    `;

    // header와 quiz-summary-section 사이 또는 header 직후에 삽입
    const header = document.querySelector('header');
    if (header) {
        const summarySection = document.getElementById('quiz-summary-section');
        if (summarySection) {
            summarySection.parentNode.insertBefore(card, summarySection);
        } else {
            header.parentNode.insertBefore(card, header.nextSibling);
        }
    }
}

/**
 * GAM-3. 레벨업 전체화면 오버레이 DOM을 body에 주입합니다.
 */
function gamInjectLevelUpOverlay() {
    if (document.getElementById('gam-levelup-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'gam-levelup-overlay';
    overlay.className = 'hidden';
    overlay.innerHTML = `
        <div class="gam-beam"></div>
        <div class="gam-levelup-box">
            <h2 class="gam-levelup-title">LEVEL UP!</h2>
            <div class="gam-levelup-sub">새로운 경지에 도달했습니다!</div>
            <div class="gam-levelup-badge" id="gam-levelup-text">LV. 2</div>
        </div>
    `;
    document.body.appendChild(overlay);
}

/**
 * GAM-4. EXP UI 요소들을 현재 상태값으로 갱신합니다.
 */
function gamUpdateExpUI() {
    const { totalExp, level, expInLevel } = window.gamState;
    const expPercent = (expInLevel / 10) * 100;
    const nextLevelExp = level * 10;

    const lvValue = document.getElementById('gam-lv-value');
    const expText = document.getElementById('gam-exp-text');
    const expFill = document.getElementById('gam-exp-fill');

    if (lvValue) lvValue.textContent = level;
    if (expText) expText.textContent = `${totalExp} / ${nextLevelExp} EXP`;
    if (expFill) expFill.style.width = `${expPercent}%`;
}

/**
 * GAM-5. 정답 제출 시 호출되는 메인 게이미피케이션 핸들러
 * - EXP +1, 보물상자 + 보석 파티클, EXP 플로팅 뱃지, 레벨업 체크
 */
function gamOnCorrectAnswer(idx, qId) {
    const prevLevel = window.gamState.level;

    // EXP 증가
    window.gamState.totalExp += 1;
    window.gamState.level = Math.floor(window.gamState.totalExp / 10) + 1;
    window.gamState.expInLevel = window.gamState.totalExp % 10;

    // UI 갱신
    gamUpdateExpUI();

    // EXP +1 플로팅 뱃지
    gamTriggerExpFloat();

    // 보물 상자 + 보석 파티클 (인라인 뷰어 내부에 삽입)
    gamTriggerTreasureChest(idx, qId);

    // 인라인 뷰어 글로우 효과
    const viewer = document.querySelector(`#item-${idx} .inline-question-viewer`);
    if (viewer) {
        viewer.classList.add('gam-correct-glow');
        setTimeout(() => viewer.classList.remove('gam-correct-glow'), 700);
    }

    // 레벨업 체크
    if (window.gamState.level > prevLevel) {
        setTimeout(() => gamTriggerLevelUp(window.gamState.level), 900);
    }
}

/**
 * GAM-6. EXP +1 플로팅 뱃지를 화면 중앙에 표시합니다.
 */
function gamTriggerExpFloat() {
    const badge = document.createElement('div');
    badge.className = 'gam-exp-float';
    badge.textContent = `⚡ EXP +1 (${window.gamState.totalExp})`;
    document.body.appendChild(badge);

    setTimeout(() => {
        if (badge.parentNode) badge.parentNode.removeChild(badge);
    }, 1600);
}

/**
 * GAM-7. 보물 상자 팝업 + 보석 파티클을 인라인 뷰어의 피드백 영역에 삽입합니다.
 */
function gamTriggerTreasureChest(idx, qId) {
    const body = document.getElementById(`viewer-body-${idx}`);
    if (!body) return;

    // 기존 보물 상자가 있다면 제거
    const existing = body.querySelector('.gam-treasure-container');
    if (existing) existing.remove();

    const container = document.createElement('div');
    container.className = 'gam-treasure-container';

    // 보물 상자 이미지
    const img = document.createElement('img');
    img.src = '/reports/images/gem_chest_open.png';
    img.alt = '보물 상자 오픈!';
    img.className = 'gam-treasure-img';
    container.appendChild(img);

    // 메시지 텍스트
    const msg = document.createElement('div');
    msg.className = 'gam-treasure-msg';
    msg.innerHTML = `💎 보물 상자를 획득했습니다!<br>경험치 <span class="gam-exp-badge">EXP +1</span> 누적: ${window.gamState.totalExp}`;
    container.appendChild(msg);

    // 보석 파티클 생성 (10개)
    const gemEmojis = ['💎', '✨', '🌟', '💰', '⭐', '🏆'];
    for (let i = 0; i < 10; i++) {
        const particle = document.createElement('span');
        particle.className = 'gam-gem-particle';
        particle.textContent = gemEmojis[i % gemEmojis.length];

        const angle = (i / 10) * 360;
        const distance = 50 + Math.random() * 70;
        const tx = Math.cos(angle * Math.PI / 180) * distance;
        const ty = Math.sin(angle * Math.PI / 180) * distance;
        const rot = Math.random() * 720 - 360;

        particle.style.setProperty('--tx', `${tx}px`);
        particle.style.setProperty('--ty', `${ty}px`);
        particle.style.setProperty('--rot', `${rot}deg`);
        particle.style.animationDelay = `${i * 0.05}s`;

        container.appendChild(particle);
    }

    // 피드백 블록 뒤에 삽입
    const feedbackBlock = body.querySelector('.inline-quiz-feedback');
    if (feedbackBlock) {
        feedbackBlock.parentNode.insertBefore(container, feedbackBlock.nextSibling);
    } else {
        body.appendChild(container);
    }
}

/**
 * GAM-8. 레벨업 전체화면 오버레이 이펙트를 구동합니다.
 */
function gamTriggerLevelUp(newLevel) {
    const overlay = document.getElementById('gam-levelup-overlay');
    if (!overlay) return;

    // ... 레벨 텍스트 업데이트
    const badge = document.getElementById('gam-levelup-text');
    if (badge) badge.textContent = `LV. ${newLevel}`;

    overlay.classList.remove('hidden');

    // 파티클 폭발
    const emojis = ['🌟', '✨', '💎', '⭐', '🏅', '🎖️', '💫', '🔥'];
    for (let i = 0; i < 20; i++) {
        const p = document.createElement('span');
        p.className = 'gam-levelup-particle';
        p.textContent = emojis[i % emojis.length];
        p.style.fontSize = `${1.1 + Math.random() * 1.1}rem`;
        p.style.left = `${45 + Math.random() * 10}%`;
        p.style.top = `${45 + Math.random() * 10}%`;

        const angle = (i / 20) * 360;
        const dist = 140 + Math.random() * 240;
        const tx = Math.cos(angle * Math.PI / 180) * dist;
        const ty = Math.sin(angle * Math.PI / 180) * dist;

        p.style.setProperty('--tx', `${tx}px`);
        p.style.setProperty('--ty', `${ty}px`);
        p.style.animationDelay = `${i * 0.06}s`;

        document.body.appendChild(p);

        setTimeout(() => {
            if (p.parentNode) p.parentNode.removeChild(p);
        }, 2500);
    }

    // 3.5초 후 자동 숨김
    setTimeout(() => {
        overlay.classList.add('hidden');
    }, 3500);
}
"""
    content += gam_js.encode("utf-8")

    with open(filepath, "wb") as f:
        f.write(content)
    print("게이미피케이션 코드 병합 완료!")

if __name__ == "__main__":
    main()
