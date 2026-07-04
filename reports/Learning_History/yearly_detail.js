/* [설계 의도] 모의고사 풀이 상세 분석 독립 페이지용 컨트롤러 */

document.addEventListener('DOMContentLoaded', () => {
    initYearlyDetail();
});

// 전역 상태 관리
const State = {
    item: null,
    details: [],
    theme: 'dark'
};

const SUBJECTS = {
    'PM': { name: '감리 및 사업관리', range: [1, 25] },
    'SE': { name: '소프트웨어공학', range: [26, 50] },
    'DB': { name: '데이터베이스', range: [51, 75] },
    'SA': { name: '시스템 아키텍처', range: [76, 100] },
    'SC': { name: '보안', range: [101, 120] }
};

const SUBJECT_NAMES = {
    'PM': '감리 및 사업관리',
    'SE': '소프트웨어공학',
    'DB': '데이터베이스',
    'SA': '시스템 아키텍처',
    'SC': '보안'
};

function initYearlyDetail() {
    const body = document.getElementById('yearly-modal-body');
    if (!body) return;

    // 1. LocalStorage에서 선택된 이력 정보 로드
    const rawData = localStorage.getItem('selected_history_item');
    if (!rawData) {
        body.innerHTML = `<div style="text-align: center; padding: 5rem; color: var(--error); font-weight: 700;">로딩 에러: 전달받은 이력 분석 데이터가 없습니다. 창을 닫고 다시 시도해 주십시오.</div>`;
        return;
    }

    try {
        State.item = JSON.parse(rawData);
        State.details = parseYearlyDetails(State.item);
        renderDetailView();
    } catch (e) {
        console.error("이력 데이터 파싱 실패:", e);
        body.innerHTML = `<div style="text-align: center; padding: 5rem; color: var(--error); font-weight: 700;">데이터 오류: 이력 내역을 구성하는 중 파싱 장애가 발생했습니다.</div>`;
    }
}

// details 파싱 헬퍼
function parseYearlyDetails(item) {
    if (!item.details) return [];
    if (typeof item.details === 'string') {
        try {
            return JSON.parse(item.details);
        } catch (e) {
            console.error("details JSON 파싱 실패:", e);
            return [];
        }
    }
    return Array.isArray(item.details) ? item.details : [];
}

// 디테일 리포트 그리기
function renderDetailView() {
    const body = document.getElementById('yearly-modal-body');
    const item = State.item;
    const details = State.details;

    const neutralCardBg = 'rgba(255, 255, 255, 0.02)';
    const neutralCardBorder = '1px solid rgba(255, 255, 255, 0.06)';
    const summaryBg = 'rgba(139, 92, 246, 0.05)';
    const summaryBorder = '1px solid rgba(139, 92, 246, 0.15)';

    // 1. 과목별 통계 및 풀이 시간 집계
    const subStats = {};
    for (let code in SUBJECTS) {
        subStats[code] = { correct: 0, total: 0, timeSum: 0 };
    }

    // 신규/일반 기출별 정답률 및 통계 집계
    let normalCorrect = 0, normalTotal = 0;
    let newTrendCorrect = 0, newTrendTotal = 0;

    details.forEach(d => {
        const qNum = d.question_num;
        let subCode = null;
        for (let code in SUBJECTS) {
            const range = SUBJECTS[code].range;
            if (qNum >= range[0] && qNum <= range[1]) {
                subCode = code;
                break;
            }
        }
        if (subCode && subStats[subCode]) {
            subStats[subCode].total++;
            subStats[subCode].timeSum += (d.elapsed_time || 0);
            if (d.is_correct) {
                subStats[subCode].correct++;
            }
        }

        // 신규 기출 판정
        const mappingKey = `${item.exam_year}_${qNum}`;
        const isNew = (window.NEW_TREND_MAPPING && window.NEW_TREND_MAPPING[mappingKey] === 1);
        if (isNew) {
            newTrendTotal++;
            if (d.is_correct) newTrendCorrect++;
        } else {
            normalTotal++;
            if (d.is_correct) normalCorrect++;
        }
    });

    const normalPct = normalTotal > 0 ? Math.round((normalCorrect / normalTotal) * 100) : 0;
    const newTrendPct = newTrendTotal > 0 ? Math.round((newTrendCorrect / newTrendTotal) * 100) : 0;
    const normalPctText = normalTotal > 0 ? `${normalPct}%` : '-';
    const newTrendPctText = newTrendTotal > 0 ? `${newTrendPct}%` : '-';

    // 학습자 맞춤형 취약점 진단 (2가지 유형 분석)
    let userTypeLabel = "";
    let userTypeDesc = "";
    let recommendation = "";
    
    if (normalPct >= 80 && newTrendPct < 50) {
        userTypeLabel = "유형 A (기출 완성형 학습자)";
        userTypeDesc = "기존 기출 회독 상태는 양호하나 최신 법제도 개정이나 생소한 신규 기술 트렌드에 약점을 보입니다.";
        recommendation = "💡 <b>처방 가이드:</b> <code>감리사_시험대비/가이드및법규</code> 폴더의 최신 고시 준수 가이드 및 공공데이터 지침서 등을 중심으로 신기술 트렌드를 집중 보완하십시오.";
    } else {
        userTypeLabel = "유형 B (개념/직관형 학습자)";
        userTypeDesc = "디테일한 암기(수식 계산, 표준 표기 규칙 등)의 정확성이 부족하여 전형적인 기출 패턴에서 오답이 잦습니다.";
        recommendation = "💡 <b>처방 가이드:</b> 확실한 득점원 확보를 위해 데이터베이스 정규화 공식, PMBOK 임계경로(Critical Path) 계산식 및 오답 노트를 중심으로 회독 수를 높이십시오.";
    }
    if (normalPct >= 80 && newTrendPct >= 80) {
        userTypeLabel = "🏆 합격 안정권 마스터";
        userTypeDesc = "기출의 완성도와 최신 트렌드 대응력이 균형 있게 최상위권에 도달했습니다.";
        recommendation = "💡 <b>처방 가이드:</b> 실전 모드 하에서 실수를 방지하고 소요 시간을 80분 이내로 타이트하게 단축하는 훈련에 힘쓰십시오.";
    }

    // 모의고사 출제 난이도 예측 및 시뮬레이션
    const difficultyLevel = newTrendTotal > 24 ? "상 (체감 난이도 높음)" : "중 (보통 수준)";
    const predictedScore = (normalPct * 0.8 + newTrendPct * 0.2).toFixed(1);

    const totalElapsed = details.reduce((acc, d) => acc + (d.elapsed_time || 0), 0);
    const globalAvgTime = details.length > 0 ? (totalElapsed / details.length) : 0;
    const recurrenceInsight = getYearlyWrongRecurrenceInsight(item, details);
    const weaknessScores = calculateSubjectWeaknessScores(
        subStats,
        recurrenceInsight.recurrenceBySubject,
        globalAvgTime
    );

    // 2. 가장 오래 고민한 문항 Top 3 (시간 정렬)
    const sortedByTime = [...details].sort((a, b) => (b.elapsed_time || 0) - (a.elapsed_time || 0));
    const top3 = sortedByTime.slice(0, 3);

    // 3. 과목별 분석 카드 HTML 작성
    let subCardsHtml = '';
    let weaknessAlertHtml = '';
    for (let code in subStats) {
        const stat = subStats[code];
        if (stat.total === 0) continue;

        const pct = Math.round((stat.correct / stat.total) * 100);
        const avgTime = Math.round(stat.timeSum / stat.total);
        const isLow = pct < 60;
        const weakness = weaknessScores[code] || { weaknessScore: 0, recurrenceRate: 0 };
        const weaknessColor = getWeaknessScoreColor(weakness.weaknessScore);
        const weaknessLabel = getWeaknessScoreLabel(weakness.weaknessScore);

        if (isLow) {
            weaknessAlertHtml += `
                <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; padding: 0.5rem 0.8rem; font-size: 0.76rem; color: #f87171; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.4rem;">
                    <i data-lucide="alert-triangle" style="width: 13px; height: 13px; flex-shrink: 0;"></i>
                    <span><strong>${SUBJECTS[code].name}</strong> 과목의 정답률이 <strong>${pct}%</strong>로 취약 상태입니다.</span>
                </div>
            `;
        }

        subCardsHtml += `
            <div style="background: ${neutralCardBg}; border: ${neutralCardBorder}; border-radius: 10px; padding: 0.6rem; text-align: center;">
                <div style="font-size: 0.72rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.25rem;">${SUBJECTS[code].name}</div>
                <div style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.15rem;">${stat.correct} / ${stat.total}문항</div>
                <div style="font-size: 0.8rem; font-weight: 700; color: ${isLow ? 'var(--error)' : 'var(--success)'}; margin-bottom: 0.25rem;">정답률: ${pct}%</div>
                <div style="font-size: 0.7rem; font-weight: 600; color: ${weaknessColor}; margin-bottom: 0.15rem;">취약도: ${weakness.weaknessScore}점 (${weaknessLabel})</div>
                <div style="font-size: 0.68rem; color: var(--text-muted);">평균: ${avgTime}초</div>
            </div>
        `;
    }

    const recurringWrongHtml = recurrenceInsight.recurringWrong.length > 0
        ? recurrenceInsight.recurringWrong
            .sort((a, b) => a - b)
            .slice(0, 15)
            .map(qNum => `<button type="button" class="yearly-recurring-chip" data-qnum="${qNum}" style="display:inline-flex; align-items:center; padding:0.18rem 0.5rem; border-radius:999px; font-size:0.72rem; border:1px solid rgba(239,68,68,0.28); background:rgba(239,68,68,0.10); color:#fca5a5; margin-right:0.35rem; margin-bottom:0.35rem; cursor:pointer;">Q.${qNum}</button>`)
            .join('')
        : '<span style="font-size:0.78rem; color: var(--text-secondary);">재발 오답은 없습니다.</span>';

    // AI 신규 기출 분석 & 취약 진단 HTML 카드 조립
    const aiTrendDiagnosticHtml = `
        <div style="background: ${neutralCardBg}; border: ${neutralCardBorder}; border-radius: 10px; padding: 0.8rem; margin-bottom: 1rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #ec4899; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.3rem;">
                <i data-lucide="brain-circuit" style="width: 16px; height: 16px;"></i> AI 신규 기출 분석 & 학습 취약 진단
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.6rem;">
                <div style="background: rgba(255, 255, 255, 0.015); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 8px; padding: 0.6rem;">
                    <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.25rem;">기출 구분별 정답률</div>
                    <div style="display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.76rem;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: var(--text-secondary);">일반 기출:</span>
                            <span style="font-weight: 700; color: #c084fc;">${normalCorrect} / ${normalTotal} (${normalPctText})</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: var(--text-secondary);">신규 기출:</span>
                            <span style="font-weight: 700; color: #ec4899;">${newTrendCorrect} / ${newTrendTotal} (${newTrendPctText})</span>
                        </div>
                    </div>
                </div>
                <div style="background: rgba(255, 255, 255, 0.015); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 8px; padding: 0.6rem;">
                    <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.25rem;">출제 난이도 예측 및 시뮬레이션</div>
                    <div style="display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.76rem;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: var(--text-secondary);">체감 난이도:</span>
                            <span style="font-weight: 700; color: #fbbf24;">${difficultyLevel}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: var(--text-secondary);">예상 환산 스코어:</span>
                            <span style="font-weight: 700; color: var(--success);">${predictedScore}점</span>
                        </div>
                    </div>
                </div>
            </div>
            <div style="background: rgba(139, 92, 246, 0.03); border: 1px solid rgba(139, 92, 246, 0.1); border-radius: 8px; padding: 0.65rem; font-size: 0.78rem;">
                <div style="font-weight: 700; color: #a78bfa; margin-bottom: 0.2rem;">🔍 취약점 진단: ${userTypeLabel}</div>
                <p style="color: var(--text-secondary); font-size: 0.74rem; line-height: 1.4; margin-bottom: 0.35rem; margin-top: 0;">${userTypeDesc}</p>
                <div style="font-size: 0.74rem; color: var(--text-primary); line-height: 1.4;">${recommendation}</div>
            </div>
        </div>
    `;

    // 4. Top 3 문항 리스트 HTML
    let top3Html = '';
    top3.forEach((d, idx) => {
        const detailIndex = details.findIndex(x => Number(x.question_num) === Number(d.question_num));
        let subName = '';
        for (let code in SUBJECTS) {
            const range = SUBJECTS[code].range;
            if (d.question_num >= range[0] && d.question_num <= range[1]) {
                subName = SUBJECTS[code].name;
                break;
            }
        }
        const timeStr = formatSecondsToKorean(d.elapsed_time);
        const stBadge = d.is_correct
            ? '<span style="color: var(--success); font-weight: 600; font-size: 0.76rem;">정답</span>'
            : '<span style="color: var(--error); font-weight: 600; font-size: 0.76rem;">오답</span>';

        top3Html += `
            <div class="yearly-top3-item" data-detail-index="${detailIndex}" title="클릭하여 지문/정답 보기" style="display: flex; justify-content: space-between; align-items: center; background: ${neutralCardBg}; border: ${neutralCardBorder}; border-radius: 8px; padding: 0.45rem 0.8rem; font-size: 0.78rem; cursor: pointer; transition: background 0.15s; margin-top: 0.3rem;">
                <div style="display: flex; align-items: center; gap: 0.45rem;">
                    <span style="background: rgba(139, 92, 246, 0.15); color: #c084fc; font-weight: 700; padding: 0.15rem 0.4rem; border-radius: 4px; font-family: monospace; font-size: 0.7rem;">Top ${idx + 1}</span>
                    <span style="font-weight: 600; color: var(--text-primary);">${d.question_num}번 문제</span>
                    <span style="font-size: 0.72rem; color: var(--text-muted);">[${subName}]</span>
                </div>
                <div style="display: flex; gap: 0.8rem; align-items: center;">
                    <span style="color: var(--text-secondary); font-family: monospace; font-size: 0.74rem;">${timeStr}</span>
                    <span>${stBadge}</span>
                </div>
            </div>
        `;
    });

    // 5. 전체 OMR 바둑판 그리드 HTML
    let gridHtml = '';
    details.forEach((d, dIdx) => {
        const isCorrect = d.is_correct;
        const color = isCorrect ? 'rgba(16, 185, 129, 0.06)' : 'rgba(239, 68, 68, 0.06)';
        const borderColor = isCorrect ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)';
        const txtColor = isCorrect ? '#34d399' : '#f87171';
        const timeStr = d.elapsed_time ? `${d.elapsed_time}초` : '0초';
        const clickHint = isCorrect ? '정답 문항 - 클릭하여 지문 보기' : '오답 문항 - 클릭하여 지문 보기';

        gridHtml += `
            <div class="yearly-omr-cell ${isCorrect ? '' : 'wrong'}" data-detail-index="${dIdx}" title="${clickHint}" style="background: ${color}; border: 1px solid ${borderColor}; border-radius: 6px; padding: 0.3rem 0.1rem; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.1rem; min-height: 42px; cursor: pointer; transition: transform 0.1s;">
                <span style="font-size: 0.68rem; color: var(--text-secondary); font-family: monospace; font-weight: 600;">Q.${d.question_num}</span>
                <span style="font-size: 0.74rem; font-weight: 700; color: ${txtColor};">${isCorrect ? 'O' : 'X'}</span>
                <span style="font-size: 0.62rem; color: var(--text-muted); font-family: monospace;">${timeStr}</span>
            </div>
        `;
    });

    // 6. 전체 구조 조립
    const formattedTotalTime = formatSecondsToKorean(item.total_time);
    body.innerHTML = `
        <div class="yearly-detail-layout">
            <!-- 왼쪽 영역 (요약 분석 및 OMR 입력판) -->
            <div class="yearly-left-panel">
                <!-- 요약 정보 바 -->
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.6rem; background: ${summaryBg}; border: ${summaryBorder}; border-radius: 10px; padding: 0.6rem; text-align: center;">
                    <div>
                        <div style="font-size: 0.68rem; color: var(--text-secondary); margin-bottom: 0.15rem;">시험 구분</div>
                        <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-primary);">${item.exam_year}년도 기출</div>
                    </div>
                    <div>
                        <div style="font-size: 0.68rem; color: var(--text-secondary); margin-bottom: 0.15rem;">최종 점수</div>
                        <div style="font-size: 0.85rem; font-weight: 700; color: var(--success);">${parseFloat(item.score).toFixed(1)}점</div>
                    </div>
                    <div>
                        <div style="font-size: 0.68rem; color: var(--text-secondary); margin-bottom: 0.15rem;">정답 현황</div>
                        <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-primary);">${item.correct_count} / ${item.total_questions}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.68rem; color: var(--text-secondary); margin-bottom: 0.15rem;">총 소요 시간</div>
                        <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-primary); font-family: monospace;">${formattedTotalTime}</div>
                    </div>
                </div>

                <!-- AI 신규 기출 분석 & 취약 진단 패널 -->
                ${aiTrendDiagnosticHtml}

                <!-- 과목별 성적 분석 카드가 모인 영역 -->
                <div style="margin-bottom: 0.2rem;">
                    <h3 style="font-size: 0.85rem; font-weight: 700; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.3rem; color: #c084fc; margin-top: 0.5rem;">
                        <i data-lucide="bar-chart-2" style="width: 14px; height: 14px;"></i> 과목별 취약 도메인 및 시간 분석
                    </h3>
                    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.4rem; margin-bottom: 0.4rem;">
                        ${subCardsHtml}
                    </div>
                    ${weaknessAlertHtml}
                </div>

                <!-- 오답 재발 추적 영역 -->
                <div style="margin-bottom: 0.2rem;">
                    <h3 style="font-size: 0.85rem; font-weight: 700; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.3rem; color: #f97316; margin-top: 0.5rem;">
                        <i data-lucide="repeat" style="width: 14px; height: 14px;"></i> 오답 재발 추적
                    </h3>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.4rem; margin-bottom: 0.4rem; font-size: 0.72rem; text-align: center;">
                        <div style="background: rgba(249,115,22,0.06); border: 1px solid rgba(249,115,22,0.18); border-radius: 6px; padding: 0.35rem 0.2rem;">
                            <span style="color: var(--text-secondary); display: block; font-size: 0.62rem;">이전 풀이</span>
                            <strong style="color: #fdba74;">${recurrenceInsight.previousAttemptCount}회</strong>
                        </div>
                        <div style="background: rgba(239,68,68,0.06); border: 1px solid rgba(239,68,68,0.18); border-radius: 6px; padding: 0.35rem 0.2rem;">
                            <span style="color: var(--text-secondary); display: block; font-size: 0.62rem;">이번 오답</span>
                            <strong style="color: #fca5a5;">${recurrenceInsight.currentWrongCount}개</strong>
                        </div>
                        <div style="background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.18); border-radius: 6px; padding: 0.35rem 0.2rem;">
                            <span style="color: var(--text-secondary); display: block; font-size: 0.62rem;">재발 오답</span>
                            <strong style="color: #fcd34d;">${recurrenceInsight.recurringWrong.length}개</strong>
                        </div>
                        <div style="background: rgba(59,130,246,0.06); border: 1px solid rgba(59,130,246,0.18); border-radius: 6px; padding: 0.35rem 0.2rem;">
                            <span style="color: var(--text-secondary); display: block; font-size: 0.62rem;">재발률/개선</span>
                            <strong style="color: #93c5fd;">${recurrenceInsight.recurrenceRate}%/${recurrenceInsight.improvedCount}</strong>
                        </div>
                    </div>
                    <div style="background: ${neutralCardBg}; border: ${neutralCardBorder}; border-radius: 8px; padding: 0.5rem;">
                        <div style="font-size: 0.72rem; color: var(--text-secondary); margin-bottom: 0.35rem;">재발 오답 리스트 (칩 클릭 시 비교 분석)</div>
                        <div>${recurringWrongHtml}</div>
                    </div>
                </div>

                <!-- 고민 유발 Top 3 문항 -->
                <div style="margin-bottom: 0.2rem;">
                    <h3 style="font-size: 0.85rem; font-weight: 700; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.3rem; color: #3b82f6; margin-top: 0.5rem;">
                        <i data-lucide="timer" style="width: 14px; height: 14px;"></i> 가장 오래 고민한 문항 Top 3
                    </h3>
                    <div style="display: flex; flex-direction: column; gap: 0.35rem;">
                        ${top3Html}
                    </div>
                </div>

                <!-- OMR 반응 분석 보드 (바둑판) -->
                <div>
                    <h3 style="font-size: 0.85rem; font-weight: 700; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.3rem; color: var(--text-primary); margin-top: 0.5rem;">
                        <i data-lucide="grid" style="width: 14px; height: 14px;"></i> 전체 문항 OMR 반응 및 소요 시간 보드
                    </h3>
                    <div style="display: grid; grid-template-columns: repeat(10, 1fr); gap: 0.3rem;">
                        ${gridHtml}
                    </div>
                </div>
            </div>

            <!-- 오른쪽 영역 (문제 상세 조회 및 오답 모아보기 탭 뷰어 - 상시 고정) -->
            <div class="yearly-right-panel">
                <!-- 탭 헤더 바 -->
                <div class="viewer-tab-bar">
                    <button type="button" class="viewer-tab-btn active" id="viewer-tab-detail">선택 문항 상세</button>
                    <button type="button" class="viewer-tab-btn" id="viewer-tab-wrong-all">오답 모아보기 (${recurrenceInsight.currentWrongCount})</button>
                </div>

                <!-- 탭 컨텐츠 패널 -->
                <div id="viewer-tab-content" style="flex: 1; display: flex; flex-direction: column; min-height: 0;">
                    <!-- 탭 1. 선택 문항 상세 -->
                    <div id="viewer-panel-detail" style="display: flex; flex-direction: column; flex: 1; min-height: 0;">
                        <div id="yearly-wrong-detail-box" style="flex: 1; overflow-y: auto;">
                            <div style="font-size:0.8rem; color: var(--text-secondary); text-align:center; padding:4rem 1.5rem; border:1px dashed rgba(255,255,255,0.08); border-radius:10px; line-height: 1.6;">
                                💡 왼쪽 OMR 바둑판 보드의 각 셀이나, 고민 문항 Top 3, 재발 오답 칩을 클릭하시면 지문과 해설이 여기에 즉시 표시됩니다.
                            </div>
                        </div>
                        <div id="yearly-recurrence-compare-box" style="margin-top:0.6rem;"></div>
                    </div>

                    <!-- 탭 2. 오답 모아보기 (기본 숨김) -->
                    <div id="viewer-panel-wrong-all" style="display: none; flex: 1; min-height: 0; overflow-y: auto;">
                        <div id="yearly-wrong-all-box">
                            <!-- JS에 의해 동적 렌더링 -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // 7. 클릭 이벤트 바인딩
    // OMR 셀 클릭 바인딩
    document.querySelectorAll('.yearly-omr-cell').forEach(cell => {
        cell.addEventListener('click', () => {
            const idx = Number(cell.getAttribute('data-detail-index'));
            const d = details[idx];
            if (d) {
                switchViewerTab('detail');
                showYearlyWrongQuestionDetail(item, d);
                renderRecurrenceAnswerComparison(item, d);
            }
        });
    });

    // Top 3 클릭 바인딩
    document.querySelectorAll('.yearly-top3-item').forEach(el => {
        el.addEventListener('click', () => {
            const idx = Number(el.getAttribute('data-detail-index'));
            const d = details[idx];
            if (d) {
                switchViewerTab('detail');
                showYearlyWrongQuestionDetail(item, d);
                renderRecurrenceAnswerComparison(item, d);
            }
        });
    });

    // 재발 오답 칩 클릭 바인딩
    document.querySelectorAll('.yearly-recurring-chip').forEach(el => {
        el.addEventListener('click', () => {
            switchViewerTab('detail');
            const qNum = Number(el.getAttribute('data-qnum'));
            const targetDetail = details.find(d => Number(d.question_num) === qNum);
            if (targetDetail) {
                showYearlyWrongQuestionDetail(item, targetDetail);
                renderRecurrenceAnswerComparison(item, targetDetail);
            }
        });
    });

    // 탭 헤더 클릭 리스너 연결
    const btnDetail = document.getElementById('viewer-tab-detail');
    const btnWrongAll = document.getElementById('viewer-tab-wrong-all');
    if (btnDetail && btnWrongAll) {
        btnDetail.addEventListener('click', () => switchViewerTab('detail'));
        btnWrongAll.addEventListener('click', () => switchViewerTab('wrong-all'));
    }

    // 아이콘 생성 및 오답 모아보기 선제 렌더링
    if (window.lucide) lucide.createIcons();
    renderYearlyWrongAllTab(item, details);
}

// 탭 전환 헬퍼
function switchViewerTab(tabId) {
    const tabDetail = document.getElementById('viewer-panel-detail');
    const tabWrongAll = document.getElementById('viewer-panel-wrong-all');
    const btnDetail = document.getElementById('viewer-tab-detail');
    const btnWrongAll = document.getElementById('viewer-tab-wrong-all');

    if (tabId === 'detail') {
        if (tabDetail) tabDetail.style.display = 'flex';
        if (tabWrongAll) tabWrongAll.style.display = 'none';
        if (btnDetail) btnDetail.classList.add('active');
        if (btnWrongAll) btnWrongAll.classList.remove('active');
    } else {
        if (tabDetail) tabDetail.style.display = 'none';
        if (tabWrongAll) tabWrongAll.style.display = 'block';
        if (btnDetail) btnDetail.classList.remove('active');
        if (btnWrongAll) btnWrongAll.classList.add('active');
    }
}

// 선택 문항 지문 상세 렌더러
function showYearlyWrongQuestionDetail(item, detail) {
    const box = document.getElementById('yearly-wrong-detail-box');
    if (!box) return;

    box.innerHTML = `<div style="text-align:center; padding:3rem;"><i data-lucide="loader" class="animate-spin" style="width:20px; height:20px; margin:0 auto;"></i> 문항 세부 지문을 불러오고 있습니다...</div>`;
    if (window.lucide) lucide.createIcons();

    fetch(`/api/question?id=${encodeURIComponent(item.exam_year + '_' + detail.question_num)}`)
        .then(res => res.json())
        .then(q => {
            const isCorrect = detail.is_correct;
            const correctAns = Array.isArray(q.answer) ? q.answer[0] : q.answer;
            const uAns = Array.isArray(detail.user_answer) ? detail.user_answer[0] : detail.user_answer;

            let optionsHtml = '';
            q.options.forEach((optText, optIdx) => {
                const optNum = optIdx + 1;
                let optClass = 'review-option';
                let style = 'padding:0.5rem 0.8rem; border-radius:6px; border:1px solid rgba(255,255,255,0.04); background:rgba(255,255,255,0.01); font-size:0.8rem; margin-top:0.3rem; display:flex; gap:0.4rem;';
                
                if (optNum === correctAns) {
                    optClass += ' correct-choice';
                    style = 'padding:0.5rem 0.8rem; border-radius:6px; border:1px solid rgba(16, 185, 129, 0.2); background:rgba(16, 185, 129, 0.04); font-size:0.8rem; margin-top:0.3rem; color:#ffffff; display:flex; gap:0.4rem;';
                } else if (optNum === uAns && !isCorrect) {
                    optClass += ' wrong-choice';
                    style = 'padding:0.5rem 0.8rem; border-radius:6px; border:1px solid rgba(239, 68, 68, 0.2); background:rgba(239, 68, 68, 0.04); font-size:0.8rem; margin-top:0.3rem; color:#ffffff; display:flex; gap:0.4rem;';
                }

                optionsHtml += `
                    <div class="${optClass}" style="${style}">
                        <span style="font-weight:700;">${optNum}.</span>
                        <span>${optText}</span>
                        ${optNum === correctAns ? ' <span style="margin-left:auto; color:var(--success); font-weight:700; font-size:0.75rem;">(정답)</span>' : ''}
                        ${optNum === uAns && !isCorrect ? ' <span style="margin-left:auto; color:var(--error); font-weight:700; font-size:0.75rem;">(선택 오답)</span>' : ''}
                    </div>
                `;
            });

            // 과목 정보
            const rangeInfo = getSubjectInfo(detail.question_num);
            const reviewImgPath = `../images/${item.exam_year}_${detail.question_num}.png`;
            const imageHtml = `
                <div id="yearly-q-img-wrap-${detail.question_num}" style="display:none; margin-top:0.8rem; justify-content:center;">
                    <img src="${reviewImgPath}" alt="문제 이미지" style="max-width:100%; border-radius:6px;"
                         onload="document.getElementById('yearly-q-img-wrap-${detail.question_num}').style.display='flex';"
                         onerror="this.style.display='none';">
                </div>
            `;

            box.innerHTML = `
                <div style="background:rgba(255,255,255,0.01); border:1px solid rgba(255,255,255,0.04); border-radius:10px; padding:1rem; min-height:100%;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:0.4rem;">
                        <span style="font-weight:700; font-size:0.88rem;">Q.${detail.question_num} 상세 보기</span>
                        <span class="badge ${rangeInfo.code}" style="font-size:0.65rem; padding:0.15rem 0.35rem; border-radius:4px; font-weight:700; border:none;">${rangeInfo.name}</span>
                    </div>
                    <div style="font-size:0.88rem; line-height:1.5; color:var(--text-primary); white-space:pre-wrap; margin-bottom:0.8rem;">${q.question}</div>
                    
                    ${imageHtml}
                    
                    <div style="margin-bottom:0.8rem;">${optionsHtml}</div>
                    
                    <div style="background:rgba(16,185,129,0.02); border:1px solid rgba(16,185,129,0.08); border-radius:8px; padding:0.6rem 0.8rem; font-size:0.8rem; line-height:1.45;">
                        <div style="color:#c084fc; font-weight:700; margin-bottom:0.2rem; display:flex; align-items:center; gap:0.25rem;">
                            <i data-lucide="book-open" style="width:13px; height:13px;"></i> 해설
                        </div>
                        <div style="color:var(--text-secondary);">${q.explanation || '등록된 상세 해설이 없습니다.'}</div>
                    </div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        })
        .catch(err => {
            console.error("지문 조회 에러:", err);
            box.innerHTML = `<div style="padding:2rem; color:var(--error); text-align:center;">지문 데이터를 조회하는 과정에서 네트워크 장애가 발생했습니다.</div>`;
        });
}

// 오답 모아보기 탭 전체 렌더러
function renderYearlyWrongAllTab(item, details) {
    const box = document.getElementById('yearly-wrong-all-box');
    if (!box) return;

    const wrongs = details.filter(d => !d.is_correct);
    if (wrongs.length === 0) {
        box.innerHTML = `<div style="text-align:center; padding:4rem 1rem; color:var(--success); font-weight:600; font-size:0.8rem;">🎉 틀린 문제가 없습니다. 완벽한 합격선 통과입니다.</div>`;
        return;
    }

    box.innerHTML = `<div style="text-align:center; padding:3rem;"><i data-lucide="loader" class="animate-spin" style="width:20px; height:20px; margin:0 auto;"></i> 전체 오답 데이터를 파싱하고 있습니다...</div>`;
    if (window.lucide) lucide.createIcons();

    // 120문항 정보를 한 번에 백업 조회
    fetch(`/api/yearly-exam/questions?year=${item.exam_year}`)
        .then(res => res.json())
        .then(questions => {
            let html = '<div style="display:flex; flex-direction:column; gap:0.8rem; padding:0.2rem;">';
            wrongs.forEach(d => {
                const q = questions.find(x => Number(x.question_num) === Number(d.question_num));
                if (!q) return;

                const correctAns = Array.isArray(q.answer) ? q.answer[0] : q.answer;
                const uAns = Array.isArray(d.user_answer) ? d.user_answer[0] : d.user_answer;
                const rangeInfo = getSubjectInfo(d.question_num);

                let optionsHtml = '';
                q.options.forEach((optText, optIdx) => {
                    const optNum = optIdx + 1;
                    const isCorrect = (optNum === correctAns);
                    const isUserWrong = (optNum === uAns);
                    let optClass = 'review-option';
                    let style = 'padding:0.4rem 0.6rem; border-radius:5px; border:1px solid rgba(255,255,255,0.03); background:rgba(255,255,255,0.01); font-size:0.78rem; margin-top:0.25rem; display:flex; gap:0.4rem;';

                    if (isCorrect) {
                        optClass += ' correct-choice';
                        style = 'padding:0.4rem 0.6rem; border-radius:5px; border:1px solid rgba(16,185,129,0.15); background:rgba(16,185,129,0.03); font-size:0.78rem; margin-top:0.25rem; color:#ffffff; display:flex; gap:0.4rem;';
                    } else if (isUserWrong) {
                        optClass += ' wrong-choice';
                        style = 'padding:0.4rem 0.6rem; border-radius:5px; border:1px solid rgba(239,68,68,0.15); background:rgba(239,68,68,0.03); font-size:0.78rem; margin-top:0.25rem; color:#ffffff; display:flex; gap:0.4rem;';
                    }

                    optionsHtml += `
                        <div class="${optClass}" style="${style}">
                            <span style="font-weight:700;">${optNum}.</span>
                            <span>${optText}</span>
                            ${isCorrect ? ' <span style="margin-left:auto; color:var(--success); font-weight:700; font-size:0.72rem;">(정답)</span>' : ''}
                            ${isUserWrong ? ' <span style="margin-left:auto; color:var(--error); font-weight:700; font-size:0.72rem;">(선택 오답)</span>' : ''}
                        </div>
                    `;
                });

                const reviewImgPath = `../images/${item.exam_year}_${d.question_num}.png`;
                const imageHtml = `
                    <div id="yearly-q-all-img-wrap-${d.question_num}" style="display:none; margin-top:0.6rem; justify-content:center;">
                        <img src="${reviewImgPath}" alt="문제 이미지" style="max-width:100%; border-radius:6px;"
                             onload="document.getElementById('yearly-q-all-img-wrap-${d.question_num}').style.display='flex';"
                             onerror="this.style.display='none';">
                    </div>
                `;

                html += `
                    <div style="background:rgba(255,255,255,0.015); border:1px solid rgba(255,255,255,0.05); border-radius:10px; padding:0.85rem; box-shadow:0 4px 12px rgba(0,0,0,0.1);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem; border-bottom:1px solid rgba(255,255,255,0.04); padding-bottom:0.35rem;">
                            <span style="font-weight:700; font-size:0.8rem; color:#f87171;">Q.${d.question_num}</span>
                            <span class="badge ${rangeInfo.code}" style="font-size:0.6rem; padding:0.12rem 0.3rem; border-radius:3px; font-weight:700; border:none;">${rangeInfo.name}</span>
                        </div>
                        <div style="font-size:0.8rem; line-height:1.45; color:var(--text-secondary); white-space:pre-wrap; margin-bottom:0.6rem;">${q.question}</div>
                        
                        ${imageHtml}
                        
                        <div style="margin-bottom:0.6rem;">${optionsHtml}</div>
                        
                        <div style="background:rgba(139,92,246,0.02); border:1px solid rgba(139,92,246,0.08); border-radius:6px; padding:0.5rem 0.7rem; font-size:0.75rem; line-height:1.4;">
                            <div style="color:#c084fc; font-weight:700; margin-bottom:0.15rem; display:flex; align-items:center; gap:0.2rem;">
                                <i data-lucide="book-open" style="width:12px; height:12px;"></i> 해설
                            </div>
                            <div style="color:var(--text-muted);">${q.explanation || '등록된 상세 해설이 없습니다.'}</div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            box.innerHTML = html;
            if (window.lucide) lucide.createIcons();
        })
        .catch(err => {
            console.error("오답 모아보기 로드 실패:", err);
            box.innerHTML = `<div style="padding:2rem; text-align:center; color:var(--error);">오답 목록 데이터를 파싱하는 중 통신 장애가 생겼습니다.</div>`;
        });
}

// 오답 비교 분석 보드 조립기
function renderRecurrenceAnswerComparison(item, detail) {
    const box = document.getElementById('yearly-recurrence-compare-box');
    if (!box) return;
    box.innerHTML = ''; // 기본 비움

    // 만약 정답 문항이면 비교 분석 보드를 띄우지 않습니다.
    if (detail.is_correct) return;

    const qNum = detail.question_num;
    const currentWrongAns = Array.isArray(detail.user_answer) ? detail.user_answer[0] : detail.user_answer;

    // 히스토리 전체 목록에서 이 문제와 똑같은 번호가 오답으로 선택된 기록이 있는지 비교합니다.
    const rawHistory = localStorage.getItem('selected_history_list');
    let historyList = [];
    if (rawHistory) {
        try {
            historyList = JSON.parse(rawHistory);
        } catch {}
    }

    // 시간 순 정렬
    historyList.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

    // 이번 ID
    const currentId = item.id;
    let records = [];

    historyList.forEach(hist => {
        const histDetails = parseYearlyDetails(hist);
        const match = histDetails.find(x => Number(x.question_num) === Number(qNum));
        if (match) {
            const ans = Array.isArray(match.user_answer) ? match.user_answer[0] : match.user_answer;
            const dateStr = hist.created_at.split('T')[0];
            records.push({
                histId: hist.id,
                date: dateStr,
                userAnswer: ans,
                isCorrect: match.is_correct,
                isCurrent: hist.id === currentId
            });
        }
    });

    if (records.length <= 1) return;

    let itemsHtml = '';
    records.forEach(r => {
        const checkIcon = r.isCorrect ? 'check' : 'x';
        const checkColor = r.isCorrect ? 'var(--success)' : 'var(--error)';
        const curStyle = r.isCurrent ? 'border:1px solid rgba(139,92,246,0.3); background:rgba(139,92,246,0.06);' : 'background:rgba(255,255,255,0.01);';
        
        itemsHtml += `
            <div style="padding:0.4rem 0.5rem; border-radius:6px; ${curStyle} text-align:center; min-width:80px; flex:1;">
                <div style="font-size:0.58rem; color:var(--text-muted); margin-bottom:0.15rem;">${r.date}${r.isCurrent ? ' (현재)' : ''}</div>
                <div style="font-size:0.8rem; font-weight:700; color:${checkColor}; display:flex; align-items:center; justify-content:center; gap:0.15rem;">
                    <i data-lucide="${checkIcon}" style="width:12px; height:12px;"></i> ${r.userAnswer}번 선택
                </div>
            </div>
        `;
    });

    box.innerHTML = `
        <div style="background:rgba(249,115,22,0.04); border:1px solid rgba(249,115,22,0.12); border-radius:10px; padding:0.65rem; font-size:0.75rem;">
            <div style="color:#f97316; font-weight:700; margin-bottom:0.35rem; display:flex; align-items:center; gap:0.25rem;">
                <i data-lucide="git-branch" style="width:13px; height:13px;"></i> 누적 오답 선택 히스토리 비교
            </div>
            <div style="display:flex; gap:0.4rem; overflow-x:auto;">
                ${itemsHtml}
            </div>
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

// 오답 재발 정보 수치 분석 헬퍼
function getYearlyWrongRecurrenceInsight(item, details) {
    const rawHistory = localStorage.getItem('selected_history_list');
    let historyList = [];
    if (rawHistory) {
        try {
            historyList = JSON.parse(rawHistory);
        } catch {}
    }

    const currentId = item.id;
    const currentYear = item.exam_year;

    // 해당 연도와 일치하는 과거 기출풀이 이력 추출 (과거 기록만)
    const prevAttempts = historyList
        .filter(h => h.id !== currentId && h.exam_year === currentYear)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    const result = {
        previousAttemptCount: prevAttempts.length,
        currentWrongCount: details.filter(d => !d.is_correct).length,
        recurringWrong: [],
        recurrenceRate: 0,
        improvedCount: 0,
        recurrenceBySubject: { 'PM': 0, 'SE': 0, 'DB': 0, 'SA': 0, 'SC': 0 }
    };

    if (prevAttempts.length === 0) return result;

    // 바로 직전 시도
    const lastAttempt = prevAttempts[0];
    const lastDetails = parseYearlyDetails(lastAttempt);
    const lastWrongs = new Set(lastDetails.filter(d => !d.is_correct).map(d => Number(d.question_num)));

    const currentWrongs = details.filter(d => !d.is_correct).map(d => Number(d.question_num));
    const currentCorrects = details.filter(d => d.is_correct).map(d => Number(d.question_num));

    // 재발 오답: 직전에도 틀렸고 이번에도 틀린 문제
    currentWrongs.forEach(qNum => {
        if (lastWrongs.has(qNum)) {
            result.recurringWrong.push(qNum);
            
            // 과목별 재발 집계
            const code = getSubjectInfo(qNum).code;
            if (result.recurrenceBySubject[code] !== undefined) {
                result.recurrenceBySubject[code]++;
            }
        }
    });

    // 개선 문항: 직전에는 틀렸으나 이번에는 맞춘 문제
    currentCorrects.forEach(qNum => {
        if (lastWrongs.has(qNum)) {
            result.improvedCount++;
        }
    });

    if (lastWrongs.size > 0) {
        result.recurrenceRate = Math.round((result.recurringWrong.length / lastWrongs.size) * 100);
    }

    return result;
}

// 과목별 약점 스코어 산출식
function calculateSubjectWeaknessScores(subStats, recurrenceBySubject, globalAvgTime) {
    const scores = {};
    for (let code in subStats) {
        const stat = subStats[code];
        if (stat.total === 0) continue;

        const errorRate = 1 - (stat.correct / stat.total);
        const avgTime = stat.timeSum / stat.total;
        
        // 시간 페널티율 계산
        let timePenalty = 0;
        if (globalAvgTime > 0) {
            timePenalty = Math.max(0, (avgTime - globalAvgTime) / globalAvgTime);
        }

        const recurrenceWeight = recurrenceBySubject[code] || 0;
        
        // 약점 계산 모델식: (오답률 * 60) + (시간 지연 페널티 * 25) + (오답 재발 횟수 * 15)
        const rawScore = (errorRate * 60) + (timePenalty * 25) + (recurrenceWeight * 15);
        const weaknessScore = Math.min(100, Math.round(rawScore));
        scores[code] = { weaknessScore, recurrenceRate: recurrenceWeight };
    }
    return scores;
}

// 취약도 레벨 스타일 헬퍼
function getWeaknessScoreColor(score) {
    if (score >= 70) return '#ef4444'; // Red (위험)
    if (score >= 40) return '#f97316'; // Orange (경계)
    return '#10b981'; // Green (양호)
}

function getWeaknessScoreLabel(score) {
    if (score >= 70) return '위험';
    if (score >= 40) return '경계';
    return '양호';
}

function getSubjectInfo(qNum) {
    for (let code in SUBJECTS) {
        const range = SUBJECTS[code].range;
        if (qNum >= range[0] && qNum <= range[1]) {
            return { code, name: SUBJECTS[code].name };
        }
    }
    return { code: 'ALL', name: '공통' };
}

function formatSecondsToKorean(totalSeconds) {
    if (!totalSeconds) return '0초';
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;

    let result = [];
    if (h > 0) result.push(`${h}시간`);
    if (m > 0) result.push(`${m}분`);
    if (s > 0 || result.length === 0) result.push(`${s}초`);

    return result.join(' ');
}
