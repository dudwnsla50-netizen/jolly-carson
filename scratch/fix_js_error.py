# -*- coding: utf-8 -*-
import os
import re

def main():
    filepath = r"reports/js/dashboard_common.js"
    if not os.path.exists(filepath):
        print(f"파일을 찾을 수 없습니다: {filepath}")
        return

    with open(filepath, "rb") as f:
        content = f.read()

    # 정규식 패턴: li.innerHTML = ` 뒤에 백틱이 닫히지 않고 바로 /* ... GAM-7-Core. 주석이 이어지는 부분 매치
    pattern = re.compile(
        br"(const\s+countSuffix\s*=\s*window\.DASHBOARD_TYPE\s*===\s*'official'\s*\?\s*'.*?'\s*:\s*'.*?';\s*li\.innerHTML\s*=\s*\x60)\s*(/\*\*[\s\S]*?\*\s*GAM-7-Core\.)"
    )

    match = pattern.search(content)
    if not match:
        print("수정할 오류 패턴을 찾지 못했습니다. 이미 수정되었거나 패턴이 다릅니다.")
        return

    print("오류 패턴을 찾았습니다! 수정을 진행합니다.")
    
    # 교체할 템플릿 리터럴 닫는 부분과 listEl append 로직 (백틱 직접 삽입)
    replacement = (
        b"\\1\n            <span class=\"modal-topic-name\">${item.title}</span>\n"
        b"            <span class=\"modal-topic-count\">${item.count}${countSuffix}</span>\n"
        b"        `;\n"
        b"        listEl.appendChild(li);\n"
        b"    });\n"
        b"}\n\n\\2"
    )

    fixed_content = pattern.sub(replacement, content)

    with open(filepath, "wb") as f:
        f.write(fixed_content)

    print("파일 수정을 완료했습니다!")

if __name__ == "__main__":
    main()
