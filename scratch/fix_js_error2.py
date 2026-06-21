# -*- coding: utf-8 -*-
import os

def main():
    filepath = r"reports/js/dashboard_common.js"
    if not os.path.exists(filepath):
        print(f"파일을 찾을 수 없습니다: {filepath}")
        return

    with open(filepath, "rb") as f:
        content = f.read()

    # 정밀한 바이너리 매칭 치환
    target = b"}\xa4.\r\n */"
    replacement = b"}"

    # LF 개행 환경 대응용 폴백
    target_lf = b"}\xa4.\n */"
    replacement_lf = b"}"

    if target in content:
        content = content.replace(target, replacement)
        print("CRLF 형식의 에러 패턴을 찾아 수정했습니다.")
    elif target_lf in content:
        content = content.replace(target_lf, replacement_lf)
        print("LF 형식의 에러 패턴을 찾아 수정했습니다.")
    else:
        print("수정할 패턴을 찾지 못했습니다.")
        return

    with open(filepath, "wb") as f:
        f.write(content)
    print("수정이 완료되었습니다!")

if __name__ == "__main__":
    main()
