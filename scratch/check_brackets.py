# -*- coding: utf-8 -*-
import sys

def main():
    filepath = "reports/js/dashboard_common.js"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Simple parenthesis and brace analyzer
    stack = []
    lines = content.split('\n')
    
    current_function = "Global"
    function_stack = []
    
    for idx, line in enumerate(lines):
        line_num = idx + 1
        
        # Look for function declarations in the line to track names
        if "function " in line and not line.strip().startswith("//"):
            # Simple extractor of function name
            parts = line.split("function ")
            if len(parts) > 1:
                func_name = parts[1].split("(")[0].strip()
                # print(f"Line {line_num}: Found function declaration {func_name}")
        
        for char_idx, char in enumerate(line):
            if char == '{':
                stack.append((line_num, char_idx, line.strip()))
            elif char == '}':
                if not stack:
                    print(f"Error: Unmatched '}}' at line {line_num}, char {char_idx}: {line.strip()}")
                else:
                    open_line, open_char, open_content = stack.pop()
                    # If this matching brace brings us back to global scope (nesting level 0)
                    # or we want to log the closed blocks:
                    # pass

    if stack:
        print(f"Error: {len(stack)} unmatched '{{' braces remain open at EOF:")
        for line_num, char_idx, content in stack[-10:]:
            print(f"  - Line {line_num}: {content}")
    else:
        print("Success: All curly braces match perfectly.")

if __name__ == "__main__":
    main()
