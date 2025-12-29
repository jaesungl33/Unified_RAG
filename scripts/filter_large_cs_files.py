#!/usr/bin/env python3
"""
Script to filter out all .cs files in Assets folder with more than 200 lines of code.
"""

import os
from pathlib import Path

# Configuration
ASSETS_DIR = Path(__file__).parent.parent / "Assets"
MIN_LINES = 200
OUTPUT_FILE = Path(__file__).parent.parent / "large_cs_files.txt"

def count_lines(file_path):
    """Count the number of lines in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

def find_large_cs_files(root_dir, min_lines):
    """Find all .cs files with more than min_lines."""
    large_files = []
    root_path = Path(root_dir)
    
    if not root_path.exists():
        print(f"Error: Directory {root_dir} does not exist!")
        return large_files
    
    print(f"Scanning {root_path} for .cs files with more than {min_lines} lines...")
    
    for cs_file in root_path.rglob("*.cs"):
        line_count = count_lines(cs_file)
        if line_count > min_lines:
            # Get relative path from Assets folder
            rel_path = cs_file.relative_to(root_path)
            large_files.append({
                'path': str(rel_path).replace('\\', '/'),
                'full_path': str(cs_file),
                'lines': line_count
            })
            print(f"Found: {rel_path} ({line_count} lines)")
    
    return large_files

def main():
    """Main function."""
    large_files = find_large_cs_files(ASSETS_DIR, MIN_LINES)
    
    # Sort by line count (descending)
    large_files.sort(key=lambda x: x['lines'], reverse=True)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Summary: Found {len(large_files)} .cs files with more than {MIN_LINES} lines")
    print(f"{'='*60}\n")
    
    # Print detailed list
    print("Files sorted by line count (descending):")
    print("-" * 60)
    for file_info in large_files:
        print(f"{file_info['lines']:5d} lines | {file_info['path']}")
    
    # Write to output file
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(f"List of .cs files in Assets with more than {MIN_LINES} lines\n")
            f.write(f"Total: {len(large_files)} files\n")
            f.write("=" * 60 + "\n\n")
            for file_info in large_files:
                f.write(f"{file_info['lines']:5d} lines | {file_info['path']}\n")
        print(f"\nOutput written to: {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error writing output file: {e}")
    
    # Also output as JSON for programmatic use
    import json
    json_output = OUTPUT_FILE.with_suffix('.json')
    try:
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(large_files, f, indent=2)
        print(f"JSON output written to: {json_output}")
    except Exception as e:
        print(f"Error writing JSON file: {e}")

if __name__ == "__main__":
    main()

