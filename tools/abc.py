import os
import re
from pathlib import Path
# filepath: [abc.py](http://_vscodecontentref_/1)
def count_code_blocks(file_path):
    """Count the number of code blocks (```) in a markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count opening triple backticks
        # This regex matches ``` with optional leading whitespace
        code_blocks = re.findall(r'^\s*```', content, re.MULTILINE)
        return len(code_blocks)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return -1

def find_markdown_files(root_dir):
    """Find all markdown files in the directory tree."""
    markdown_files = []
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                markdown_files.append(file_path)
    
    return markdown_files

def main():
    # Get the untested folder path
    untested_dir = "untested"
    
    if not os.path.exists(untested_dir):
        print(f"Error: '{untested_dir}' folder not found!")
        return
    
    # Find all markdown files
    print(f"Scanning for markdown files in '{untested_dir}'...")
    markdown_files = find_markdown_files(untested_dir)
    
    if not markdown_files:
        print("No markdown files found!")
        return
    
    print(f"Found {len(markdown_files)} markdown files\n")
    
    # Count code blocks in each file
    file_stats = []
    for file_path in markdown_files:
        count = count_code_blocks(file_path)
        if count >= 0:  # Only include files that were successfully read
            # Get relative path for cleaner display
            relative_path = os.path.relpath(file_path, untested_dir)
            file_stats.append((relative_path, count))
    
    # Sort by code block count (ascending)
    file_stats.sort(key=lambda x: x[1])
    
    # Display all files ranked by code blocks
    print("All markdown files ranked by number of code blocks (lowest to highest):")
    print("-" * 100)
    print(f"{'Rank':<6} {'Code Blocks':<12} {'File Path'}")
    print("-" * 100)
    
    for i, (file_path, count) in enumerate(file_stats, 1):
        print(f"{i:<6} {count:<12} {file_path}")
    
    # Show some statistics
    print("\n" + "-" * 100)
    print("Statistics:")
    print(f"- Total files analyzed: {len(file_stats)}")
    if file_stats:
        print(f"- Files with 0 code blocks: {sum(1 for _, count in file_stats if count == 0)}")
        print(f"- Average code blocks per file: {sum(count for _, count in file_stats) / len(file_stats):.2f}")
        print(f"- Maximum code blocks in a file: {max(count for _, count in file_stats)}")
        
        # Group by code block count
        print("\nDistribution:")
        from collections import Counter
        count_distribution = Counter(count for _, count in file_stats)
        for blocks, num_files in sorted(count_distribution.items()):
            print(f"  {blocks} code blocks: {num_files} file(s)")

if __name__ == "__main__":
    main()