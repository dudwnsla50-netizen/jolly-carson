# -*- coding: utf-8 -*-
import os

js_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports', 'js', 'dashboard_common.js')

print(f"[진행] {js_path} 파일 로드 중...")
with open(js_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# 1. gamOnCorrectAnswer 함수 내부의 정답 칭찬 & 애니메이션 구동부 교체
# 주역 코드 키워드로 위치를 계산하여 주석 깨짐에 대처합니다.
idx_start = content.find('function gamOnCorrectAnswer')
if idx_start != -1:
    idx_solved = content.find('todaySolved = (window.gamState.todaySolved || 0) + 1;', idx_start)
    if idx_solved != -1:
        idx_exp_ui = content.find('gamUpdateExpUI();', idx_solved)
        if idx_exp_ui != -1:
            idx_anim = content.find("gamApplyPetAnimation('correct');", idx_exp_ui)
            if idx_anim != -1:
                # 변경 전 타겟 블록
                target_block = content[idx_solved:idx_anim + len("gamApplyPetAnimation('correct');")]
                
                # 변경 후 대체 블록
                replacement_block = """todaySolved = (window.gamState.todaySolved || 0) + 1;

    // 연속 정답 콤보 누적
    window.gamComboCount = (window.gamComboCount || 0) + 1;
    let isComboTriggered = false;
    if (window.gamComboCount === 5) {
        isComboTriggered = true;
    }

    // UI 갱신 (경험치 바 및 오늘의 학습 목표 150문항 진척도 등)
    gamUpdateExpUI();

    // 5콤보 달성 시 특별 축하 이펙트 구동, 그 외에는 일반 칭찬 멘트
    if (isComboTriggered) {
        gamTriggerCombo5Effect();
    } else {
        gamTriggerPetCorrectMessage();
        gamApplyPetAnimation('correct');
    }"""
                content = content.replace(target_block, replacement_block)
                print("[성공] 1. gamOnCorrectAnswer 내부 콤보 로직 교체 완료.")
            else:
                print("[오류] gamApplyPetAnimation('correct') 위치를 찾지 못했습니다.")
        else:
            print("[오류] gamUpdateExpUI() 위치를 찾지 못했습니다.")
    else:
        print("[오류] todaySolved 대입문 위치를 찾지 못했습니다.")
else:
    print("[오류] function gamOnCorrectAnswer 시작점을 찾지 못했습니다.")

# 2. gamTriggerPetIncorrectMessage 함수 수정 (오답 시 콤보 리셋)
# 이것은 주석이 없는 안전한 타겟으로 매칭
target_2 = """function gamTriggerPetIncorrectMessage() {
    const PET_INCORRECT_MESSAGES = {"""

replacement_2 = """function gamTriggerPetIncorrectMessage() {
    // 오답 시 연속 콤보 초기화
    window.gamComboCount = 0;

    const PET_INCORRECT_MESSAGES = {"""

# LF/CRLF 교체 적용 헬퍼
def apply_replace(src_content, target_str, replacement_str, label):
    target_lf = target_str.replace('\r\n', '\n')
    replacement_lf = replacement_str.replace('\r\n', '\n')
    
    if target_lf in src_content:
        print(f"[성공] {label} 교체 완료. (LF)")
        return src_content.replace(target_lf, replacement_lf)
    else:
        target_crlf = target_lf.replace('\n', '\r\n')
        replacement_crlf = replacement_lf.replace('\n', '\r\n')
        if target_crlf in src_content:
            print(f"[성공] {label} 교체 완료. (CRLF)")
            return src_content.replace(target_crlf, replacement_crlf)
        else:
            print(f"[오류] {label} 대치 지점을 찾지 못했습니다.")
            return src_content

content = apply_replace(content, target_2, replacement_2, "2. gamTriggerPetIncorrectMessage")

# 3. 콤보 이펙트 함수 코드 (맨 아래에 추가)
combo_function_code = """
/**
 * GAM-X. 5연속 정답(5콤보) 달성 시 특별 이펙트와 캐릭터 축하 연출을 구동합니다.
 */
function gamTriggerCombo5Effect() {
    // 1. 화면 중앙 "HIT 5! 💥" 오버레이 엘리먼트 생성
    const comboEl = document.createElement('div');
    comboEl.className = 'gam-combo5-overlay';
    
    // 현재 과목의 기본/진화 펫의 이름을 가져옵니다.
    const defaultPetKey = gamGetDefaultPetForSubject(window.SUBJECT_CODE);
    const activePetKey = gamGetEvolvedPetKey(defaultPetKey);
    const petProfile = gamGetPetProfile(activePetKey);
    const petName = petProfile ? petProfile.name : '파트너';

    comboEl.innerHTML = `
        <div class="gam-combo5-card">
            <div class="gam-combo5-glow"></div>
            <div class="gam-combo5-badge">🔥 5 COMBO 🔥</div>
            <h1 class="gam-combo5-title">HIT 5!</h1>
            <p class="gam-combo5-sub">${petName}이(가) 연속 정답을 축하합니다! 🏆</p>
        </div>
    `;
    
    document.body.appendChild(comboEl);
    
    // 2. 펫 캐릭터 특별 축하 모션 (360도 회전 바운스)
    gamApplyPetAnimation('spin');
    
    // 3. 말풍선에 5콤보 달성 특별 축하 대사 주입
    const COMBO5_MESSAGES = {
        'charmander': '🔥 와! 벌써 5연속 정답! 파이리의 불꽃 콤보로 기세를 올리고 있어요! 🔥',
        'charmeleon': '🔥 트랜잭션 5회 연속 커밋 성공! 리자드의 뜨거운 불꽃 콤보 어택! 🔥',
        'charizard': '🐉🔥 하늘을 날아오르는 5연속 정답! 리자몽의 화염방사가 완벽한 정답 길을 엽니다! 🏆',
        'megacharizard': '⚡🏆 한계를 돌파한 5콤보! 메가리자몽의 전율하는 불꽃이 데이터베이스를 압도합니다! 🐉🔥',
        'pikachu': '⚡ 삐까삐까! 연속 5번 정답! 피카츄의 전기 콤보로 오답들을 완전 방전시켰어요! ⚡',
        'growlithe': '🚨 연속 5회 보안 위협 차단 성공! 가디 보안관의 완벽한 정답 순찰 라인 확보! 🚨',
        'arcanine': '🚨🔥 전설의 5연속 보안 점검 완료! 윈디의 질풍 같은 속도로 오답들을 완벽 소각! 🏆🚨',
        'farfetchd': '⚔️ 대파를 휘두르며 연속 5회 명중! 파오리의 예리한 검술로 PM 일정을 완전 제어! ⚖️',
        'sirfetchd': '⚔️ 기사도의 영광! 5콤보 달성! 창파나이트의 빛나는 대파 창으로 완벽 감리 수행! 🏆⚖️',
        'rotom': '⚙️ 로토무 콤보 분석 가동! 연속 5회 연산 에러율 0%! 최적의 아키텍처 아웃풋! ⚡',
        'squirtle': '🌊 시원하게 터지는 5연속 정답 물대포! 꼬부기와 함께 이대로 합격까지 서핑해요! 💦',
        'bulbasaur': '🌱 5연속 정답 씨앗이 만개했습니다! 이상해씨가 준비한 합격 꽃다발을 받아주세요! 🌸',
        'metagross': '🧠 4개의 뇌가 완벽 동기화된 5콤보! 메타그로스의 계산대로 합격을 선점합니다! ⚡'
    };
    
    const comboMsg = COMBO5_MESSAGES[activePetKey] || '🌟 대단해요! 5연속 정답 돌파! 합격의 기운이 가득합니다! 🌟';
    
    const bubble = document.getElementById('gam-pet-bubble-text');
    const runnerBubble = document.getElementById('gam-runner-pet-bubble-text');

    if (bubble) bubble.textContent = comboMsg;
    if (runnerBubble) runnerBubble.textContent = comboMsg;

    // 말풍선 대사가 6초 동안 노출되도록 복귀 타이머 연장
    if (window.gamPetBubbleTimeout) {
        clearTimeout(window.gamPetBubbleTimeout);
    }
    window.gamPetBubbleTimeout = setTimeout(() => {
        window.gamPetBubbleTimeout = null;
        gamUpdatePetMessageByProgress(window.gamState.todaySolved);
    }, 6000);

    // 4. 2.5초 후 콤보 오버레이 제거 (페이드아웃 애니메이션 완료 후)
    setTimeout(() => {
        comboEl.classList.add('fade-out');
        setTimeout(() => {
            comboEl.remove();
        }, 500);
    }, 2500);
}
"""

content = content + "\n" + combo_function_code
print("[성공] 3. gamTriggerCombo5Effect 함수 추가 완료.")

# 변경된 내용 쓰기
with open(js_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("[진행] 파일 저장 완료.")
