import urllib.request
import json

# 퀴즈 제출 API 테스트 요청 데이터
url = "http://localhost:8000/api/quiz/submit"
data = {
    "subject": "DB",
    "concept": "DB 표준화 단계 및 특징",
    "total_questions": 5,
    "correct_count": 4,
    "wrong_count": 1,
    "details": {
        "q_id": "2026_55",
        "user_choice": [1],
        "correct_answer": [1],
        "is_correct": True
    }
}

headers = {"Content-Type": "application/json"}
req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")

try:
    with urllib.request.urlopen(req) as res:
        print("Submit API Response Status:", res.status)
        print("Response Body:", res.read().decode("utf-8"))
except Exception as e:
    print("Submit API Request Failed:", e)

# 퀴즈 통계 API 조회
stats_url = "http://localhost:8000/api/quiz/stats?subject=DB"
try:
    with urllib.request.urlopen(stats_url) as res:
        stats = json.loads(res.read().decode("utf-8"))
        print("\n=== Updated DB Stats ===")
        print("Summary total_solved:", stats["summary"]["total_solved"])
        # logs 개수 확인
        print("Logs count:", len(stats["logs"]))
except Exception as e:
    print("Stats API Request Failed:", e)
