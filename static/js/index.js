/* ==========================================
   [Jolly-Carson 자율 학습 플랫폼 프론트엔드 제어 스크립트]
   - 주요 역할: 대시보드 갱신, 퀴즈 상태 머신 제어, REST API 통신 및 화면 뷰 전환
   - 설계 특징:
     1. 전역 상태를 명확히 분리하여 퀴즈 세션 변수를 관리합니다.
     2. 비동기 Fetch 호출 시 적절한 Loading UI 및 예외 처리를 제공합니다.
     3. DOM을 동적으로 변경할 때마다 Lucide 아이콘을 리프레시하여 그래픽 깨짐을 막습니다.
   ========================================== */

// ==========================================
// 1. 전역 상태 관리 객체 (State Machine)
// ==========================================
const AppState = {
  currentSubject: "",       // 진행 중인 과목 코드 (PM, SE, DB, SA, SC)
  quizzes: [],              // 서버로부터 전달받은 5문항 문제 데이터셋
  currentIdx: 0,            // 현재 풀고 있는 문제 번호 인덱스 (0~4)
  sessionAttempts: [],      // 이번 세션에서 제출할 퀴즈 정보 및 사용자 입력 값
  correctCount: 0,          // 이번 세션에서 맞춘 정답 개수
  isChecking: false         // 사용자가 보기를 클릭해 채점 피드백이 노출 중인지 여부
};

// ==========================================
// 2. 초기 로드 및 이벤트 리스너 바인딩
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
  // 앱 실행과 동시에 누적 통계 데이터를 읽어옴
  fetchStats();
  
  // Lucide 아이콘 적용 호출
  lucide.createIcons();

  // 이벤트 핸들러 등록
  document.getElementById("btn-reset-stats").addEventListener("click", resetStats);
  document.getElementById("btn-back-to-dashboard").addEventListener("click", backToDashboard);
  document.getElementById("btn-next-question").addEventListener("click", goToNextQuestion);
  document.getElementById("btn-submit-quiz").addEventListener("click", submitQuizSession);
  document.getElementById("btn-close-modal").addEventListener("click", closeModalAndGoHome);
  document.getElementById("btn-close-exam-modal").addEventListener("click", closePastExamModal);
  document.getElementById("past-exam-modal").addEventListener("click", (e) => {
    if (e.target.id === "past-exam-modal") closePastExamModal();
  });
});

// ==========================================
// 3. API 통신 및 대시보드 렌더링 모듈
// ==========================================

async function fetchStats() {
  /*
  [설계 의도]
  서버로부터 학습 통계 데이터를 가져와 대시보드의 카드 및 취약점 처방 영역을 갱신합니다.
  */
  const gridContainer = document.getElementById("subject-grid");
  
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) throw new Error("서버 통계 갱신에 실패했습니다.");
    
    const data = await res.json();
    
    // 1) 종합 스탯 헤더 갱신
    document.getElementById("overall-solved").textContent = data.overall_solved;
    document.getElementById("overall-correct").textContent = data.overall_correct;
    
    let overallRate = 0;
    if (data.overall_solved > 0) {
      overallRate = Math.round((data.overall_correct / data.overall_solved) * 100);
    }
    document.getElementById("overall-rate").textContent = `${overallRate}%`;

    // 2) 5대 과목 카드 렌더링
    gridContainer.innerHTML = "";
    
    Object.keys(data.subjects).forEach(code => {
      const sub = data.subjects[code];
      const solved = sub.total_solved;
      const rate = sub.rate;
      
      const card = document.createElement("div");
      card.className = `subject-card card ${solved > 0 ? 'solved-any' : ''}`;
      
      // 정답률에 따른 프로그레스 바 컬러 차별화
      let scoreColorClass = "";
      if (solved > 0) {
        if (rate >= 80) scoreColorClass = "high-score";
        else if (rate < 60) scoreColorClass = "low-score";
      }

      card.innerHTML = `
        <div class="card-top">
          <span class="subject-code">${code}</span>
          <span class="solved-badge ${solved > 0 ? 'active' : ''}">
            ${solved > 0 ? `${solved}문제 풀음` : '미진행'}
          </span>
        </div>
        <div class="card-middle">
          <h3 class="subject-name">${sub.name}</h3>
          <div class="progress-container">
            <div class="progress-header">
              <span>누적 정답률</span>
              <span class="outfit font-weight-bold">${solved > 0 ? `${rate}%` : '-'}</span>
            </div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill ${scoreColorClass}" style="width: ${solved > 0 ? rate : 0}%"></div>
            </div>
          </div>
        </div>
        <div class="card-bottom">
          <button class="btn btn-primary btn-block" onclick="startQuiz('${code}')">
            <i data-lucide="play-circle"></i> 예상문제 풀기
          </button>
        </div>
      `;
      
      gridContainer.appendChild(card);
    });

    // 3) 약점 처방 가이드 활성화 판정
    const remedyContainer = document.getElementById("remedy-container");
    if (data.remedy) {
      document.getElementById("remedy-category").textContent = data.remedy.category;
      document.getElementById("remedy-rate").textContent = `${data.remedy.rate}%`;
      document.getElementById("remedy-scope").textContent = data.remedy.scope_details;
      document.getElementById("remedy-tip").textContent = data.remedy.tip;
      remedyContainer.style.display = "block";
    } else {
      remedyContainer.style.display = "none";
    }

    // 아이콘 새로고침
    lucide.createIcons();

  } catch (error) {
    gridContainer.innerHTML = `
      <div class="loading-spinner text-danger">
        <i data-lucide="alert-circle" style="width: 48px; height: 48px;"></i>
        <p>${error.message}</p>
      </div>
    `;
    lucide.createIcons();
  }
}


async function resetStats() {
  /*
  [설계 의도]
  사용자의 동의를 얻어 학습 데이터를 백엔드 API를 통해 전체 초기화합니다.
  */
  if (!confirm("주의: 지금까지 푼 모든 문제 풀이 이력과 정답률 기록이 완전히 삭제됩니다.\n초기화하시겠습니까?")) {
    return;
  }

  try {
    const res = await fetch("/api/stats/reset", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      alert(data.message);
      fetchStats(); // 대시보드 리로드
    } else {
      alert("이력 초기화에 실패했습니다: " + data.message);
    }
  } catch (error) {
    alert("서버 연결 실패: " + error.message);
  }
}

// ==========================================
// 4. 퀴즈 세션 구동 및 흐름 관리 모듈
// ==========================================

async function startQuiz(subjectCode) {
  /*
  [설계 의도]
  사용자가 과목을 클릭하면 API를 호출해 5문제를 생성하고, 퀴즈 풀이 인터페이스로 화면을 전환합니다.
  */
  // 상태 변수 초기화
  AppState.currentSubject = subjectCode;
  AppState.quizzes = [];
  AppState.currentIdx = 0;
  AppState.sessionAttempts = [];
  AppState.correctCount = 0;
  AppState.isChecking = false;

  // 퀴즈 뷰 상태로 DOM 전환
  switchView("quiz-view");
  
  // UI 스켈레톤 상태 생성
  const optionsContainer = document.getElementById("quiz-options-container");
  document.getElementById("quiz-question-text").textContent = "지능형 예상문제를 실시간으로 출제하는 중입니다. 잠시만 기다려 주세요...";
  optionsContainer.innerHTML = `
    <div class="loading-spinner">
      <div class="spinner"></div>
      <p>RAG 분석 및 문제 빌드 중...</p>
    </div>
  `;
  document.getElementById("btn-next-question").style.display = "none";
  document.getElementById("btn-submit-quiz").style.display = "none";
  document.getElementById("quiz-explanation-card").style.display = "none";

  try {
    const res = await fetch(`/api/quiz/${subjectCode}`);
    if (!res.ok) throw new Error("문제 출제 도중 에러가 발생했습니다.");
    
    const data = await res.json();
    AppState.quizzes = data.quizzes;
    
    // 출제 정보 메타 렌더링
    const sourceLabel = data.source === "AI_GENERATED" ? "AI 실시간 RAG" : "오프라인 고품질 Mock";
    document.getElementById("quiz-source-badge").textContent = sourceLabel;
    
    // 과목 뱃지 갱신
    const subjectNames = { PM: "사업관리", SE: "소프트웨어공학", DB: "데이터베이스", SA: "시스템구조", SC: "보안" };
    document.getElementById("quiz-subject-badge").textContent = subjectNames[subjectCode] || subjectCode;

    // 첫 문제 렌더링 진행
    renderQuestion();

  } catch (error) {
    document.getElementById("quiz-question-text").textContent = "예상문제를 가져오지 못했습니다.";
    optionsContainer.innerHTML = `
      <p style="color: var(--color-danger); text-align: center;">${error.message}</p>
      <button class="btn btn-secondary btn-block" style="margin-top: 20px;" onclick="backToDashboard()">대시보드로 돌아가기</button>
    `;
  }
}


function renderQuestion() {
  /*
  [설계 의도]
  현재 인덱스(currentIdx)에 해당하는 문제 정보를 화면에 렌더링합니다.
  */
  AppState.isChecking = false;
  
  const idx = AppState.currentIdx;
  const quiz = AppState.quizzes[idx];

  // 네비게이션 및 진척도 업데이트
  document.getElementById("current-question-num").textContent = idx + 1;
  const progressPercent = ((idx + 1) / 5) * 100;
  document.getElementById("quiz-progress-fill").style.style = `width: ${progressPercent}%;`;
  document.getElementById("quiz-progress-fill").style.width = `${progressPercent}%`;

  // 단원 카테고리 텍스트 주입
  document.getElementById("quiz-category-badge").textContent = quiz.category;
  
  // 지문 주입
  document.getElementById("quiz-question-text").textContent = quiz.question;

  // 보기 영역 빌드
  const container = document.getElementById("quiz-options-container");
  container.innerHTML = "";

  quiz.options.forEach((optText, optionIdx) => {
    // 1-based index
    const optNum = optionIdx + 1; 
    
    const button = document.createElement("button");
    button.className = "option-btn";
    button.textContent = optText;
    button.addEventListener("click", () => checkAnswer(optNum, button));
    
    container.appendChild(button);
  });

  // 이전 선택 정보 및 해설 영역 숨김
  document.getElementById("quiz-explanation-card").style.display = "none";
  document.getElementById("btn-next-question").style.display = "none";
  document.getElementById("btn-submit-quiz").style.display = "none";
}


function checkAnswer(userAnswer, selectedButton) {
  /*
  [설계 의도]
  사용자가 선택지를 클릭하면 즉시 정/오답 처리를 진행하고, 
  해설 카드를 슬라이드 형태로 열어 직관적인 피드백을 제공합니다.
  */
  if (AppState.isChecking) return; // 연속 클릭 방어
  AppState.isChecking = true;

  const idx = AppState.currentIdx;
  const quiz = AppState.quizzes[idx];
  const correctAnswer = quiz.answer;
  const isCorrect = (userAnswer === correctAnswer);

  // 정답 수 카운팅
  if (isCorrect) {
    AppState.correctCount++;
  }

  // 이번 풀이 기록 저장 배열에 누적
  AppState.sessionAttempts.push({
    quiz_id: quiz.id,
    category: quiz.category,
    user_answer: userAnswer,
    correct_answer: correctAnswer
  });

  // 모든 보기 버튼들의 스타일 적용 및 클릭 비활성화
  const container = document.getElementById("quiz-options-container");
  const buttons = container.getElementsByClassName("option-btn");

  Array.from(buttons).forEach((btn, optionIdx) => {
    btn.disabled = true; // 채점 이후에는 더 이상 선택 불가능
    const optNum = optionIdx + 1;

    if (optNum === correctAnswer) {
      // 실제 정답 문항은 항상 녹색 하이라이트
      btn.classList.add("correct-choice");
    } else if (optNum === userAnswer && !isCorrect) {
      // 틀렸을 경우 사용자가 클릭한 보기는 빨간색 하이라이트
      btn.classList.add("wrong-choice");
    }
  });

  // 해설 카드 내용 작성 및 활성화
  const expCard = document.getElementById("quiz-explanation-card");
  const statusBadge = document.getElementById("explanation-status-badge");
  
  if (isCorrect) {
    statusBadge.innerHTML = '<i data-lucide="check-circle"></i> 정답입니다!';
    statusBadge.className = "status-badge";
  } else {
    statusBadge.innerHTML = '<i data-lucide="x-circle"></i> 오답입니다!';
    statusBadge.className = "status-badge wrong";
  }
  
  document.getElementById("explanation-correct-num").textContent = correctAnswer;
  document.getElementById("explanation-text").textContent = quiz.explanation;
  
  // 근거(reference) 및 출처(source), 유사기출(similar_exam) 필드 추가 매핑
  document.getElementById("explanation-reference").textContent = quiz.reference || "자료 없음";
  document.getElementById("explanation-source").textContent = quiz.source || "출제 범위 가이드라인";
  
  const similarVal = quiz.similar_exam || "";
  const similarEl = document.getElementById("explanation-similar-exam");
  if (similarVal && similarVal !== "유사 기출 정보 없음") {
    similarEl.className = "meta-desc link-btn";
    similarEl.innerHTML = `${similarVal} <i data-lucide="external-link" class="inline-icon"></i>`;
    similarEl.onclick = () => openPastExam(similarVal);
  } else {
    similarEl.className = "meta-desc";
    similarEl.textContent = "유사 기출 정보 없음";
    similarEl.onclick = null;
  }
  
  expCard.style.display = "block";
  lucide.createIcons();

  // 하단 네비게이션 버튼 제어
  if (idx < 4) {
    // 1~4번 문제인 경우 [다음 문제로] 노출
    document.getElementById("btn-next-question").style.display = "inline-flex";
  } else {
    // 마지막 5번 문제인 경우 [결과 제출] 노출
    document.getElementById("btn-submit-quiz").style.display = "inline-flex";
  }
}


function goToNextQuestion() {
  /*
  [설계 의도]
  인덱스를 올리고 다음 문제를 화면에 띄웁니다.
  */
  if (AppState.currentIdx < 4) {
    AppState.currentIdx++;
    renderQuestion();
  }
}


async function submitQuizSession() {
  /*
  [설계 의도]
  5문제를 모두 다 푼 후 채점 이력(sessionAttempts)을 서버에 POST로 전송하여 저장하고,
  결과 요약 모달창을 띄워 성적을 최종 피드백합니다.
  */
  const submitBtn = document.getElementById("btn-submit-quiz");
  submitBtn.disabled = true;
  submitBtn.textContent = "채점 결과 기록 중...";

  try {
    const res = await fetch("/api/quiz/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: AppState.sessionAttempts })
    });
    
    if (!res.ok) throw new Error("결과 기록 도중 오류가 발생했습니다.");
    
    // 모달창 수치 매핑 및 팝업
    document.getElementById("modal-total-count").textContent = 5;
    document.getElementById("modal-correct-count").textContent = AppState.correctCount;
    
    // 성적에 따른 격려 문장 출력
    let feedback = "";
    if (AppState.correctCount === 5) {
      feedback = "완벽합니다! 모든 단원에 대해 완벽한 준비 태세를 확인했습니다.";
    } else if (AppState.correctCount >= 3) {
      feedback = "훌륭합니다! 일부 약점은 대시보드 맞춤 처방 분석표를 기반으로 세부 범위를 더 보완해 주세요.";
    } else {
      feedback = "집중 보강이 필요합니다. 대시보드의 취약 단원 목차와 에이전트 수험 전략 처방 가이드를 확인하여 보강하십시오.";
    }
    document.getElementById("modal-feedback-text").textContent = feedback;

    // 모달 오픈
    document.getElementById("result-modal").style.display = "flex";
    lucide.createIcons();

  } catch (error) {
    alert("서버 전송 에러: " + error.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = '최종 결과 제출 및 채점 <i data-lucide="check-square"></i>';
    lucide.createIcons();
  }
}


function closeModalAndGoHome() {
  /*
  [설계 의도]
  결과창 모달을 닫고 메인 대시보드로 돌아가며 통계를 리로딩합니다.
  */
  document.getElementById("result-modal").style.display = "none";
  backToDashboard();
}


function backToDashboard() {
  /*
  [설계 의도]
  퀴즈 화면에서 메인 대시보드 화면으로 뷰를 전환하고 통계를 리셋하여 불러옵니다.
  */
  switchView("dashboard-view");
  fetchStats();
}

// ==========================================
// 5. 프론트엔드 애니메이션 및 뷰 전환 헬퍼
// ==========================================

function switchView(viewId) {
  /*
  [설계 의도]
  SPA 방식의 화면 전환을 위해 특정 패널 클래스에 'active'를 부여하고 화면을 활성화합니다.
  */
  const panels = document.getElementsByClassName("view-panel");
  Array.from(panels).forEach(panel => {
    panel.classList.remove("active");
  });
  
  document.getElementById(viewId).classList.add("active");
}

// ==========================================
// 6. 유사 기출문제 팝업 조회 제어 모듈
// ==========================================

function openPastExam(similarText) {
  /*
  [설계 의도]
  '2025년 기출 55번 유사' 형식의 텍스트에서 연도와 문항 번호를 추출하여 모달 조회를 요청합니다.
  */
  const match = similarText.match(/(\d{4})년\s*기출\s*(\d+)\s*번/);
  if (!match) {
    alert("올바른 기출문제 번호를 파싱할 수 없습니다.");
    return;
  }

  const year = match[1];
  const num = match[2];

  // 모달 활성화 및 로딩 노출
  const modal = document.getElementById("past-exam-modal");
  document.getElementById("exam-loading").style.display = "flex";
  document.getElementById("exam-container").style.display = "none";
  document.getElementById("exam-fallback-container").style.display = "none";
  modal.style.display = "flex";
  lucide.createIcons();

  // API 통신
  fetchPastExam(year, num);
}

async function fetchPastExam(year, num) {
  /*
  [설계 의도]
  백엔드 API를 통해 기출문제를 조회하고, 성공 시 동적 지문을 그리고 
  실패 시 PDF 수동 링크 폴백을 활성화합니다.
  */
  try {
    const res = await fetch(`/api/exam/query?year=${year}&num=${num}`);
    const result = await res.json();

    document.getElementById("exam-loading").style.display = "none";

    if (result.success && result.data) {
      const quiz = result.data;
      
      // 뱃지 및 본문 주입
      document.getElementById("exam-year-badge").textContent = `${quiz.year}년 기출`;
      document.getElementById("exam-num-badge").textContent = `${quiz.num}번 문항`;
      document.getElementById("exam-question-text").textContent = quiz.question;

      // 4지선다 동적 빌드
      const optContainer = document.getElementById("exam-options-container");
      optContainer.innerHTML = "";
      
      quiz.options.forEach((optText, optIdx) => {
        const optNum = optIdx + 1;
        const isCorrect = (optNum === quiz.answer);
        
        const div = document.createElement("div");
        div.className = `option-btn ${isCorrect ? 'correct-choice' : ''}`;
        div.style.cursor = "default";
        div.textContent = optText;
        optContainer.appendChild(div);
      });

      // 정답 번호 및 해설
      document.getElementById("exam-correct-num").textContent = quiz.answer;
      document.getElementById("exam-explanation-text").textContent = quiz.explanation || "이 기출문제에 대한 추가 해설이 등록되어 있지 않습니다.";

      document.getElementById("exam-container").style.display = "block";
    } else {
      // 백엔드 파싱 실패 시 PDF 다운로드 링크 폴백 작동
      document.getElementById("exam-pdf-name").textContent = result.pdf_name || "기출문제 파일";
      const pdfLink = document.getElementById("exam-pdf-link");
      if (result.pdf_url) {
        pdfLink.href = result.pdf_url;
        document.getElementById("exam-fallback-container").style.display = "block";
      } else {
        const optContainer = document.getElementById("exam-options-container");
        optContainer.innerHTML = `<p style="color: var(--color-danger); text-align:center;">${result.message}</p>`;
        document.getElementById("exam-container").style.display = "block";
      }
    }
    lucide.createIcons();
  } catch (error) {
    document.getElementById("exam-loading").style.display = "none";
    alert("기출문제를 가져오는 중 네트워크 오류 발생: " + error.message);
    closePastExamModal();
  }
}

function closePastExamModal() {
  /* [설계 의도] 유사 기출 모달 팝업 비활성화 */
  document.getElementById("past-exam-modal").style.display = "none";
}
