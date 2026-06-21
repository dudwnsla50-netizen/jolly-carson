# -*- coding: utf-8 -*-
import os

def main():
    errors = 0
    for root, dirs, files in os.walk('reports'):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Normalize spaces / check
                is_wrong_answers = 'wrong_answers' in root
                
                if is_wrong_answers:
                    # check ../css/dashboard_common.css and ../js/review.js
                    has_css = '../css/dashboard_common.css' in content
                    has_game_css = '../css/game.css' in content
                    has_js = '../js/dashboard_common.js' in content
                    has_review = '../js/review.js' in content
                    
                    if not (has_css and has_game_css and has_js and has_review):
                        print(f"Path issue in {filepath}:")
                        print(f"  - has ../css/dashboard_common.css: {has_css}")
                        print(f"  - has ../css/game.css: {has_game_css}")
                        print(f"  - has ../js/dashboard_common.js: {has_js}")
                        print(f"  - has ../js/review.js: {has_review}")
                        errors += 1
                else:
                    # check css/dashboard_common.css and js/dashboard_common.js
                    has_css = 'css/dashboard_common.css' in content
                    has_game_css = 'css/game.css' in content
                    has_js = 'js/dashboard_common.js' in content
                    
                    if not (has_css and has_game_css and has_js):
                        print(f"Path issue in {filepath}:")
                        print(f"  - has css/dashboard_common.css: {has_css}")
                        print(f"  - has css/game.css: {has_game_css}")
                        print(f"  - has js/dashboard_common.js: {has_js}")
                        errors += 1

    print(f"Validation complete. Total files with path errors: {errors}")

if __name__ == "__main__":
    main()
