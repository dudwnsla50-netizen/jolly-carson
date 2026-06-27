/**
 * [Jolly-Carson 서비스 전역 구성 설정 파일]
 * - 작성 목적: 대시보드 및 분석 센터 전반에서 사용되는 공통 상수를 중앙 제어합니다.
 */
window.APP_CONFIG = {
    // 일일 학습 목표량 (여러 화면의 게이지 바, 펫 말풍선 계산에 공통 적용)
    DAILY_STUDY_GOAL: 150,

    // 펫 피드백 말풍선 노출 시간 (밀리초)
    PET_BUBBLE_DURATION: 4000,

    // 사용 가능한 전체 펫 키 목록
    PET_KEYS: ['pikachu', 'charmander', 'charmeleon', 'charizard', 'megacharizard', 'squirtle', 'bulbasaur', 'growlithe', 'arcanine', 'rotom', 'farfetchd', 'sirfetchd', 'metagross'],

    // 과목별 기본 펫 매핑 정보
    SUBJECT_DEFAULT_PETS: {
        'DB': 'charmander', // 데이터베이스 (파이리 -> 리자드 -> 리자몽 -> 메가리자몽 진화트리)
        'SE': 'pikachu',    // 소프트웨어공학
        'PM': 'farfetchd',  // 프로젝트관리 (사업관리: 파오리 -> 창파나이트 진화트리)
        'SA': 'rotom',      // 시스템아키텍처 (시스템구조)
        'SC': 'growlithe'   // 시스템보안 (정보보안)
    },

    // 펫 캐릭터 상세 데이터 정의 (이름, 이미지 소스, 기본 대사)
    PET_PROFILES: {
        'pikachu': { name: '피카츄', src: '/reports/images_game/pikachuRun.gif', defaultMsg: '오늘도 합격을 향해 백만볼트! ⚡' },
        'charmander': { name: '파이리', src: '/reports/images_game/charmander_cheer.png', defaultMsg: '뜨거운 열정으로 문제를 녹여버려요! 🔥' },
        'charmeleon': { name: '리자드', src: '/reports/images_game/charmeleon_db.png', defaultMsg: '더욱 강력해진 리자드의 불꽃! 데이터베이스 트랜잭션을 완전 제어합니다! 🔥' },
        'charizard': { name: '리자몽', src: '/reports/images_game/charizard_db.png', defaultMsg: '마침내 리자몽으로 진화! 초대형 데이터베이스 튜닝과 인덱싱 스캔 가동! 🏆🔥' },
        'megacharizard': { name: '메가리자몽', src: '/reports/images_game/megacharizard_db.png', defaultMsg: '메가진화 완료! 한계를 초월한 메가리자몽의 화염이 데이터베이스 시스템 전체를 장악합니다! 🏆🔥⚡' },
        'squirtle': { name: '꼬부기', src: '/reports/images_game/squirtle_cheer.png', defaultMsg: '차분하게 한 걸음씩 나아가요! 🌊' },
        'bulbasaur': { name: '이상해씨', src: '/reports/images_game/bulbasaur_cheer.png', defaultMsg: '천천히 씨앗을 뿌리듯 실력을 키워요! 🌱' },
        'growlithe': { name: '가디 보안관', src: '/reports/images_game/growlithe_security.png', defaultMsg: '침입자 및 오답 철저 차단! 든든하게 지켜요! 🚨' },
        'arcanine': { name: '윈디 보안관', src: '/reports/images_game/arcanine_security.png', defaultMsg: '레전드 보안관 윈디 등장! 어떠한 오답 침입자도 신속히 추격하여 소각합니다! 🚨🔥' },
        'rotom': { name: '로토무', src: '/reports/images_game/rotom_architect.png', defaultMsg: '시스템 성능 최적화 완료! 아키텍처 설계를 지원해요! ⚙️' },
        'farfetchd': { name: '파오리', src: '/reports/images_game/paori_pm.png', defaultMsg: '대파를 들고 사업관리 순찰 개시! PMBOK 일정을 철저히 관리합니다! ⚖️' },
        'sirfetchd': { name: '창파나이트', src: '/reports/images_game/sirfetchd_pm.png', defaultMsg: '기사도 정신으로 법령 준수! 공정한 계약과 감리를 집행해요! ⚖️' },
        'metagross': { name: '메타그로스', src: '/reports/images_game/metagross.png', defaultMsg: '데이터베이스 대기 중... 메타그로스의 인덱스 연산을 시작하세요! 🧠' }
    },

    // 🔄 문제 롤링 가중치 기준 설정
    ROLLING_WEIGHT_CONFIG: {
        // 1. 미학습 문제 가중치 (+1)
        UNSTUDIED_ADDITIVE_WEIGHT: 1.0,

        // 2. 학습한 문제 가중치 공식 설정
        // 가중치 계산 식 = (오답 갯수 * wrongMultiplier) - (정답 갯수 * correctMultiplier)
        STUDIED_WEIGHT_FORMULA: {
            wrongMultiplier: 1.0,   // 오답 갯수 배율
            correctMultiplier: 1.0, // 정답 갯수 배율
            minWeight: -5.0         // 하한값 (정답을 많이 맞춘 문제의 가중치 과도한 하락 방지)
        }
    }
};
