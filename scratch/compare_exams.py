import re

def main():
    js_path = r"d:\100.lyj\anti_workspace\jolly-carson\reports\exam_database.js"
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    keys = re.findall(r'"(\d{4})_\d+"', content)
    unique_years = sorted(list(set(keys)))
    print(f"Unique years in database: {unique_years}")
    
    # 2011년부터 2026년까지 각각 몇 문제씩 들어있는지 확인
    for y in unique_years:
        y_keys = re.findall(rf'"{y}_(\d+)"', content)
        print(f"  {y}년도: {len(y_keys)}개 문항 존재")

if __name__ == "__main__":
    main()
