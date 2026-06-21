# -*- coding: utf-8 -*-
import os
import re

def main():
    target_dir = 'reports'
    files_updated = 0
    
    subjects = ['db', 'se', 'pm', 'sa', 'sc']
    
    for file in os.listdir(target_dir):
        if file.endswith('.html') and ('frequent_concepts' in file or 'official_scopes' in file):
            filepath = os.path.join(target_dir, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Replace subject badge default hrefs to official_scopes versions
            for sub in subjects:
                pattern = f'href="{sub}_frequent_concepts.html"'
                replacement = f'href="{sub}_official_scopes.html"'
                content = content.replace(pattern, replacement)
                
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated: {filepath}")
                files_updated += 1

    print(f"Update complete. Total HTML files updated: {files_updated}")

if __name__ == "__main__":
    main()
