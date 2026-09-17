"""
[일회성 정리 스크립트] exam_questions.question / explanation 필드 안에 base64로 그대로
박혀 있는 원본 이미지(다이어그램·코드 스크린샷 등)를 리사이즈+재압축해 같은 자리에 다시 저장합니다.

배경: 운영 DB(Supabase Postgres)를 직접 조회해보니 2015~2026년 전체 333개 문항에
data:image/...;base64,... 형태의 이미지가 압축 없이 그대로 박혀 있었고 합계 약 36MB였습니다.
이 때문에 연도별 모의고사 시작 시 매번 해당 연도 120문항(수 MB)을 통째로 내려받아야 했고,
모바일 등 불안정한 네트워크에서는 다운로드가 중간에 끊겨 JSON 파싱이 실패하면서
"문제를 로드하는 중 오류가 발생했습니다" 에러로 이어졌습니다.

화면에 보여주는 방식(인라인 <img src="data:...">)은 그대로 유지하고, 이미지 자체만
최대 1200px 변으로 축소 + JPEG 품질 80으로 재압축합니다. 실행 전 영향받는 행의
원본 question/explanation을 로컬 JSON 파일로 백업한 뒤 UPDATE합니다.

사용법: python scripts/compress_embedded_images.py [--dry-run]
"""
import base64
import io
import json
import os
import re
import sys
import time
import urllib.parse

import psycopg2
import psycopg2.extras
from PIL import Image

IMAGE_DATA_URI_PATTERN = re.compile(r'data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]+)')

MAX_DIMENSION = 1200
JPEG_QUALITY = 80
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_connection():
    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url:
        print("[오류] 환경변수 DATABASE_URL이 설정되어 있지 않습니다.")
        print("운영 DB 접속 문자열을 DATABASE_URL로 지정한 뒤 다시 실행해 주세요.")
        sys.exit(1)
    parsed = urllib.parse.urlparse(raw_url)
    conn_kwargs = {
        "dbname": urllib.parse.unquote(parsed.path.lstrip("/")) if parsed.path else None,
        "user": urllib.parse.unquote(parsed.username) if parsed.username else None,
        "password": urllib.parse.unquote(parsed.password) if parsed.password else None,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
    }
    conn = psycopg2.connect(**conn_kwargs, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.set_client_encoding('UTF8')
    return conn


def compress_field(text):
    """text 안의 모든 data:image 임베드를 리사이즈+재압축한 것으로 치환합니다.
    반환: (치환된 텍스트, 발견된 이미지 개수, 원본 바이트 합, 압축 후 바이트 합)"""
    if not text or 'data:image' not in text:
        return text, 0, 0, 0

    stats = {"count": 0, "before": 0, "after": 0}

    def _replace(match):
        original_b64 = match.group(2)
        stats["before"] += len(original_b64)
        try:
            raw = base64.b64decode(original_b64)
            with Image.open(io.BytesIO(raw)) as img:
                img = img.convert("RGB")
                img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=JPEG_QUALITY)
                new_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception as e:
            print(f"    [경고] 이미지 압축 실패, 원본 유지: {e}")
            stats["count"] += 1
            stats["after"] += len(original_b64)
            return match.group(0)

        stats["count"] += 1
        stats["after"] += len(new_b64)
        return f"data:image/jpeg;base64,{new_b64}"

    new_text = IMAGE_DATA_URI_PATTERN.sub(_replace, text)
    return new_text, stats["count"], stats["before"], stats["after"]


def main():
    dry_run = "--dry-run" in sys.argv

    conn = get_connection()
    cursor = conn.cursor()

    print("영향받는 행 조회 중...")
    cursor.execute("""
        SELECT id, year, subject, question_num, question, explanation
        FROM exam_questions
        WHERE question LIKE %s OR explanation LIKE %s
        ORDER BY year, question_num
    """, ('%data:image%', '%data:image%'))
    rows = cursor.fetchall()
    print(f"대상 행: {len(rows)}개\n")

    backup = []
    total_before = 0
    total_after = 0
    updated = 0

    for row in rows:
        q_id = row["id"]
        new_question, cnt_q, before_q, after_q = compress_field(row["question"])
        new_explanation, cnt_e, before_e, after_e = compress_field(row["explanation"])

        img_count = cnt_q + cnt_e
        before_total = before_q + before_e
        after_total = after_q + after_e
        if img_count == 0:
            continue

        backup.append({
            "id": q_id,
            "question": row["question"],
            "explanation": row["explanation"],
        })

        total_before += before_total
        total_after += after_total
        updated += 1

        reduction_pct = (1 - after_total / before_total) * 100 if before_total else 0
        print(f"  {q_id} ({row['year']}년 {row['subject']} {row['question_num']}번): "
              f"이미지 {img_count}개, {before_total:,} -> {after_total:,} bytes ({reduction_pct:.1f}% 감소)")

        if not dry_run:
            cursor.execute(
                "UPDATE exam_questions SET question = %s, explanation = %s WHERE id = %s",
                (new_question, new_explanation, q_id)
            )

    print(f"\n총 {updated}개 문항 처리")
    print(f"base64 합계: {total_before:,} -> {total_after:,} bytes "
          f"({(1 - total_after / total_before) * 100 if total_before else 0:.1f}% 감소)")

    if dry_run:
        print("\n[--dry-run] 실제 DB 변경 없이 종료합니다.")
        cursor.close()
        conn.close()
        return

    backup_path = os.path.join(BASE_DIR, f"backup_embedded_images_{time.strftime('%Y%m%d_%H%M%S')}.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False)
    print(f"\n원본 백업 저장: {backup_path}")

    conn.commit()
    print("커밋 완료.")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
