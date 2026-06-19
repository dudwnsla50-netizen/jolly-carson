# -*- coding: utf-8 -*-
import os
import sys
import json
import urllib.request

# Windows 콘솔 인코딩 에러 방지
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

def test_gemini():
    print(f"API Key 존재 여부: {bool(GEMINI_API_KEY)}")
    if not GEMINI_API_KEY:
        print("API Key가 설정되어 있지 않습니다.")
        return
        
    payload = {
        "contents": [{"parts": [{"text": "Hello, Gemini! Please respond with 'OK' if you can read this."}]}]
    }
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            response_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"응답 결과: {response_text}")
    except Exception as e:
        print(f"API 호출 실패: {e}")

if __name__ == "__main__":
    test_gemini()
