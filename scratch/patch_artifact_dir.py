# -*- coding: utf-8 -*-
"""
[아티팩트 경로 하드코딩 리팩토링 및 갱신 스크립트]
- 작성자: Antigravity
- 목적: 컴팩션 등으로 인해 세션 아티팩트 디렉토리가 변경되었을 때, 
  하드코딩된 예전 아티팩트 경로를 최신 경로(67ae5d2c-bc8c-43a5-8e13-47848b2d1ce9)로 일괄 수정하고,
  각 빌더에서 build_utils.py의 ARTIFACT_DIR을 참조하도록 리팩토링합니다.
"""
import os

NEW_ARTIFACT_ID = "67ae5d2c-bc8c-43a5-8e13-47848b2d1ce9"
NEW_ARTIFACT_DIR = rf"C:\Users\DCCIS040000\.gemini\antigravity-ide\brain\{NEW_ARTIFACT_ID}"
OLD_ARTIFACT_DIR = r"C:\Users\DCCIS040000\.gemini\antigravity-ide\brain\7e1fd111-1dc1-495d-82a1-c40573600184"

BASE_DIR = r"e:\jolly-carson"

def patch_build_utils():
    path = os.path.join(BASE_DIR, "build_utils.py")
    print(f"[패치] {path} 수정 중...")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 단순 문자열 치환 적용 (백슬래시 이스케이프 문제 방지)
    old_line = f'ARTIFACT_DIR = r"{OLD_ARTIFACT_DIR}"'
    new_line = f'ARTIFACT_DIR = r"{NEW_ARTIFACT_DIR}"'
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  -> ARTIFACT_DIR을 새 경로로 변경 완료")
    else:
        # 혹시 기존 경로가 다른 값일 수도 있으므로 정규식 대신 정교한 replace 방식을 활용하거나,
        # regex 치환 시 replacement 문자열을 이스케이프합니다.
        import re
        pattern = r'ARTIFACT_DIR\s*=\s*r"C:\\Users\\DCCIS040000\\\.gemini\\antigravity-ide\\brain\\[a-f0-9\-]+"'
        # replacement에 백슬래시가 들어가므로 re.escape 대신 raw string 이스케이프 처리
        escaped_replacement = NEW_ARTIFACT_DIR.replace('\\', '\\\\')
        replacement_str = f'ARTIFACT_DIR = r"{escaped_replacement}"'
        
        new_content, count = re.subn(pattern, replacement_str, content)
        if count > 0:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  -> ARTIFACT_DIR을 정규식 매칭을 통해 새 경로로 변경 완료 ({count}개 수정)")
        else:
            print("  -> ARTIFACT_DIR 변경 대상 없음 혹은 이미 반영됨")

def patch_builders():
    builders = [
        "build_premium_db_viewer.py",
        "build_premium_db_official_viewer.py",
        "build_premium_pm_viewer.py",
        "build_premium_pm_official_viewer.py",
        "build_premium_se_viewer.py",
        "build_premium_se_official_viewer.py",
        "build_premium_sa_viewer.py",
        "build_premium_sa_official_viewer.py",
        "build_premium_sc_viewer.py",
        "build_premium_sc_official_viewer.py"
    ]

    for builder in builders:
        path = os.path.join(BASE_DIR, builder)
        print(f"[패치] {builder} 수정 중...")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        modified = False

        # 1. build_utils import 구문에 ARTIFACT_DIR 추가
        old_import = "from build_utils import get_output_paths, update_shared_db"
        new_import = "from build_utils import get_output_paths, update_shared_db, ARTIFACT_DIR"
        if old_import in content:
            content = content.replace(old_import, new_import)
            modified = True
            print("  -> import 구문에 ARTIFACT_DIR 추가")

        # 2. 하드코딩된 이미지 아티팩트 경로 변경 (정규식 사용)
        import re
        pattern = r'artifact_img_dir\s*=\s*r"C:\\Users\\DCCIS040000\\\.gemini\\antigravity-ide\\brain\\[a-f0-9\-]+\\images"'
        replacement = 'artifact_img_dir = os.path.join(ARTIFACT_DIR, "images")'
        
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            content = new_content
            modified = True
            print(f"  -> artifact_img_dir 하드코딩 제거 및 ARTIFACT_DIR 연동 완료 ({count}개 수정)")

        # 3. 혹시 이미 ARTIFACT_DIR 연동은 되었는데 import 구문만 누락되었거나 하는 케이스 체크
        if "os.path.join(ARTIFACT_DIR" in content and "ARTIFACT_DIR" not in content.split('\n')[12:25]:
            # import 라인에 추가되었는지 재검사
            pass

        if modified:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            print("  -> 수정할 내용 없음 (이미 리팩토링 되었을 수 있음)")

def main():
    patch_build_utils()
    patch_builders()
    print("[완료] 모든 파일 패치 완료!")

if __name__ == "__main__":
    main()
