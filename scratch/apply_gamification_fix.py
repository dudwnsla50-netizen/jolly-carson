# -*- coding: utf-8 -*-
import os

def main():
    filepath = r"reports/js/dashboard_common.js"
    if not os.path.exists(filepath):
        print(f"파일을 찾을 수 없습니다: {filepath}")
        return

    with open(filepath, "rb") as f:
        content = f.read()

    # 1. renderLoadedQuestion 내 정답 배너 제거
    # CRLF 개행 매칭
    target_banner = (
        b"    // \xeb\x8b\xb5\xec\x95\x88 \xec\xa0\x9c\xec\xb6\x9c \xeb\xb0\x8f \xed\x94\xbc\xeb\x93\x9c\xeb\xb0\xb1 \xed\x8c\xa8\xeb\x84\x90\r\n"
        b"    if (isSubmitted) {\r\n"
        b"        // \xec\xa0\x95\xeb\x8b\xb5 \xed\x94\xbc\xeb\x93\x9c\xeb\xb0\xb1 \xeb\xa0\x8c\xeb\x8d\x94\xeb\xa7\x81\r\n"
        b"        const statusClass = submittedResult.isCorrect ? 'correct' : 'wrong';\r\n"
        b"        const statusText = submittedResult.isCorrect ? '\xe2\x9c\x93 \xec\xa0\x95\xeb\x8b\xb5\xec\x9e\x85\xeb\x8b\x88\xeb\x8b\xa4! \xf0\x9f\x8e\x89' : `\xe2\x9c\x95 \xec\x98\xa4\xeb\x8b\xb5\xec\x9e\x85\xeb\x8b\x88\xeb\x8b\xa4. (\xec\xa0\x95\xeb\x8b\xb5: ${submittedResult.cAnsStr})`;\r\n"
        b"\r\n"
        b"        htmlContent += `\r\n"
        b"            <div class=\"inline-quiz-feedback ${statusClass}\">\r\n"
        b"                ${statusText}\r\n"
        b"            </div>\r\n"
        b"            ${data.explanation ? `\r\n"
        b"                <div class=\"inline-explanation-box\">\r\n"
        b"                    <strong>\xf0\x9f\x92\xa1 \xec\xa0\x95\xeb\x8b\xb5 \xed\x95\xb4\xec\x84\xa4:</strong><br>${data.explanation}\r\n"
        b"                </div>\r\n"
        b"            ` : ''}"
    )

    replacement_banner = (
        b"    // \xeb\x8b\xb5\xec\x95\x88 \xec\xa0\x9c\xec\xb6\x9c \xeb\xb0\x8f \xed\x94\xbc\xeb\x93\x9c\xeb\xb0\xb1 \xed\x8c\xa8\xeb\x84\x90\r\n"
        b"    if (isSubmitted) {\r\n"
        b"        // \xec\xa0\x95\xeb\x8b\xb5 \xed\x94\xbc\xeb\x93\x9c\xeb\xb0\xb1 \xeb\xa0\x8c\xeb\x8d\x94\xeb\xa7\x81 (\xec\xa0\x95\xeb\x8b\xb5\xec\x9d\xbc \xeb\x95\x8c\xeb\x8a\x94 \xeb\xb0\xb0\xeb\x84\x88 \xeb\xaf\xb8\xeb\x85\xb8\xec\xb6\x9c, \xec\x98\xa4\xeb\x8b\xb5\xec\x9d\xbc \xeb\x95\x8c\xeb\xa7\x8c \xeb\x85\xb8\xec\xb6\x9c)\r\n"
        b"        const statusClass = submittedResult.isCorrect ? 'correct' : 'wrong';\r\n"
        b"\r\n"
        b"        if (!submittedResult.isCorrect) {\r\n"
        b"            htmlContent += `\r\n"
        b"                <div class=\"inline-quiz-feedback ${statusClass}\">\r\n"
        b"                    \xe2\x9c\x95 \xec\x98\xa4\xeb\x8b\xb5\xec\x9e\x85\xeb\x8b\x88\xeb\x8b\xa4. (\xec\xa0\x95\xeb\x8b\xb5: ${submittedResult.cAnsStr})\r\n"
        b"                </div>\r\n"
        b"            `;\r\n"
        b"        }\r\n"
        b"\r\n"
        b"        htmlContent += `\r\n"
        b"            ${data.explanation ? `\r\n"
        b"                <div class=\"inline-explanation-box\">\r\n"
        b"                    <strong>\xf0\x9f\x92\xa1 \xec\xa0\x95\xeb\x8b\xb5 \xed\x95\xb4\xec\x84\xa4:</strong><br>${data.explanation}\r\n"
        b"                </div>\r\n"
        b"            ` : ''}"
    )

    # LF 개행 매칭 폴백
    target_banner_lf = (
        b"    // \xeb\x8b\xb5\xec\x95\x88 \xec\xa0\x9c\xec\xb6\x9c \xeb\xb0\x8f \xed\x94\xbc\xeb\x93\x9c\xeb\xb0\xb1 \xed\x8c\xa8\xeb\x84\x90\n"
        b"    if (isSubmitted) {\n"
        b"        // \xec\xa0\x95\xeb\x8b\xb5 \xed\x94\xbc\xeb\x93\x9c\xeb\xb0\xb1 \xeb\xa0\x8c\xeb\x8d\x94\xeb\xa7\x81\n"
        b"        const statusClass = submittedResult.isCorrect ? 'correct' : 'wrong';\n"
        b"        const statusText = submittedResult.isCorrect ? '\xe2\x9c\x93 \xec\xa0\x95\xeb\x8b\xb5\xec\x9e\x85\xeb\x8b\x88\xeb\x8b\xa4! \xf0\x9f\x8e\x89' : `\xe2\x9c\x95 \xec\x98\xa4\xeb\x8b\xb5\xec\x9e\x85\xeb\x8b\x88\xeb\x8b\xa4. (\xec\xa0\x95\xeb\x8b\xb5: ${submittedResult.cAnsStr})`;\n"
        b"\n"
        b"        htmlContent += `\n"
        b"            <div class=\"inline-quiz-feedback ${statusClass}\">\n"
        b"                ${statusText}\n"
        b"            </div>\n"
        b"            ${data.explanation ? `\n"
        b"                <div class=\"inline-explanation-box\">\n"
        b"                    <strong>\xf0\x9f\x92\xa1 \xec\xa0\x95\xeb\x8b\xb5 \xed\x95\xb4\xec\x84\xa4:</strong><br>${data.explanation}\n"
        b"                </div>\n"
        b"            ` : ''}"
    )

    replacement_banner_lf = (
        b"    // \xeb\x8b\xb5\xec\x95\x88 \xec\xa0\x9c\xec\xb6\x9c \xeb\xb0\x8f \xed\x94\xbc\xeb\x93\x9c\xeb\xb0\xb1 \xed\x8c\xa8\xeb\x84\x90\n"
        b"    if (isSubmitted) {\n"
        b"        // \xec\xa0\x95\xeb\x8b\xb5 \xed\x94\xbc\xeb\x93\x9c\xeb\xb0\xb1 \xeb\xa0\x8c\xeb\x8d\x94\xeb\xa7\x81 (\xec\xa0\x95\xeb\x8b\xb5\xec\x9d\xbc \xeb\x95\x8c\xeb\x8a\x94 \xeb\xb0\xb0\xeb\x84\x88 \xeb\xaf\xb8\xeb\x85\xb8\xec\xb6\x9c, \xec\x98\xa4\xeb\x8b\xb5\xec\x9d\xbc \xeb\x95\x8c\xeb\xa7\x8c \xeb\x85\xb8\xec\xb6\x9c)\n"
        b"        const statusClass = submittedResult.isCorrect ? 'correct' : 'wrong';\n"
        b"\n"
        b"        if (!submittedResult.isCorrect) {\n"
        b"            htmlContent += `\n"
        b"                <div class=\"inline-quiz-feedback ${statusClass}\">\n"
        b"                    \xe2\x9c\x95 \xec\x98\xa4\xeb\x8b\xb5\xec\x9e\x85\xeb\x8b\x88\xeb\x8b\xa4. (\xec\xa0\x95\xeb\x8b\xb5: ${submittedResult.cAnsStr})\n"
        b"                </div>\n"
        b"            `;\n"
        b"        }\n"
        b"\n"
        b"        htmlContent += `\n"
        b"            ${data.explanation ? `\n"
        b"                <div class=\"inline-explanation-box\">\n"
        b"                    <strong>\xf0\x9f\x92\xa1 \xec\xa0\x95\xeb\x8b\xb5 \xed\x95\xb4\xec\x84\xa4:</strong><br>${data.explanation}\n"
        b"                </div>\n"
        b"            ` : ''}"
    )

    if target_banner in content:
        content = content.replace(target_banner, replacement_banner)
        print("정답 배너 제거 (CRLF) 성공")
    elif target_banner_lf in content:
        content = content.replace(target_banner_lf, replacement_banner_lf)
        print("정답 배너 제거 (LF) 성공")
    else:
        print("Warning: 정답 배너 제거 대상을 찾지 못했습니다.")

    # 2. submitInlineAnswer 내 정답 이펙트 트리거 연동
    target_submit = (
        b"    .then(() => {\r\n"
        b"        renderLoadedQuestion(idx, qId);\r\n"
        b"    })"
    )

    replacement_submit = (
        b"    .then(() => {\r\n"
        b"        renderLoadedQuestion(idx, qId);\r\n"
        b"        if (isCorrect && typeof gamOnCorrectAnswer === 'function') {\r\n"
        b"            gamOnCorrectAnswer(idx, qId);\r\n"
        b"        }\r\n"
        b"    })"
    )

    target_submit_lf = (
        b"    .then(() => {\n"
        b"        renderLoadedQuestion(idx, qId);\n"
        b"    })"
    )

    replacement_submit_lf = (
        b"    .then(() => {\n"
        b"        renderLoadedQuestion(idx, qId);\n"
        b"        if (isCorrect && typeof gamOnCorrectAnswer === 'function') {\n"
        b"            gamOnCorrectAnswer(idx, qId);\n"
        b"        }\n"
        b"    })"
    )

    if target_submit in content:
        content = content.replace(target_submit, replacement_submit)
        print("이펙트 트리거 연동 (CRLF) 성공")
    elif target_submit_lf in content:
        content = content.replace(target_submit_lf, replacement_submit_lf)
        print("이펙트 트리거 연동 (LF) 성공")
    else:
        print("Warning: 이펙트 트리거 연동 대상을 찾지 못했습니다.")

    with open(filepath, "wb") as f:
        f.write(content)
    print("변경 사항 저장 완료!")

if __name__ == "__main__":
    main()
