# -*- coding: utf-8 -*-
import re

text1 = "ISO/IEC 5055의 품질 특성"
text2 = "ISO/IEC 5055 의 품질 특성"
text3 = "ISO/IEC 5055"

pattern = r"\b5055\b"

print("pattern:", pattern)
print(f"Match in '{text1}':", bool(re.search(pattern, text1)))
print(f"Match in '{text2}':", bool(re.search(pattern, text2)))
print(f"Match in '{text3}':", bool(re.search(pattern, text3)))
