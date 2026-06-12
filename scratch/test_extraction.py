import fitz # PyMuPDF
import re

def test_extract():
    pdf_path = r"d:\100.lyj\anti_workspace\jolly-carson\data\past_exam\2025년 감리사 자격검정 필기시험 문제-A형(답포함).pdf"
    doc = fitz.open(pdf_path)
    
    all_pages_text = []
    
    for i, page in enumerate(doc):
        blocks = page.get_text("blocks")
        left_col = []
        right_col = []
        mid_x = page.rect.width / 2
        
        for b in blocks:
            x0, y0, x1, y1, text, block_no, block_type = b
            if block_type == 0:
                center_x = (x0 + x1) / 2
                if center_x < mid_x:
                    left_col.append(b)
                else:
                    right_col.append(b)
                    
        left_col.sort(key=lambda x: x[1])
        right_col.sort(key=lambda x: x[1])
        
        page_text = "\n".join([b[4] for b in left_col + right_col])
        all_pages_text.append(f"=== Page {i+1} ===\n{page_text}")
        
    full_text = "\n\n".join(all_pages_text)
    with open(r"d:\100.lyj\anti_workspace\jolly-carson\scratch\extracted_test.txt", "w", encoding="utf-8") as out_f:
        out_f.write(full_text)
    print("Success: saved all pages to extracted_test.txt")
    
    doc.close()

if __name__ == "__main__":
    test_extract()
