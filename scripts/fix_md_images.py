import os
import re
from pathlib import Path

def main():
    project_root = Path(__file__).resolve().parent.parent
    markdown_dir = project_root / "markdown"
    
    if not markdown_dir.is_dir():
        print("markdown directory not found.")
        return
        
    print("Fixing image references in markdown files...")
    
    # Traverse markdown folders
    for year_dir in markdown_dir.iterdir():
        if not year_dir.is_dir():
            continue
        year = year_dir.name
        if not year.isdigit():
            continue
            
        print(f"Processing year {year}...")
        
        # Patterns to replace
        pattern_fwd = f"markdown/{year}/images/"
        pattern_bwd = f"markdown\\{year}\\images\\"
        
        # Traverse markdown files inside the year directory
        for md_file in year_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            
            # Perform replacements
            new_content = content.replace(pattern_fwd, "images/")
            new_content = new_content.replace(pattern_bwd, "images/")
            
            # Write back if changed
            if new_content != content:
                md_file.write_text(new_content, encoding="utf-8")
                print(f"  Fixed: {md_file.name}")

if __name__ == "__main__":
    main()
