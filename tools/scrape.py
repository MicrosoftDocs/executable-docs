import pandas as pd
import requests
import os
import re
from pathlib import Path
import sys

def create_smart_folder_name(title):
    """Create a clean folder name from the document title"""
    if not isinstance(title, str):
        title = str(title)
    
    # Convert to lowercase and remove special characters
    name = title.lower()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '_', name)
    
    # Limit length to 40 characters for reasonable folder names
    if len(name) > 40:
        name = name[:37] + "..."
    
    return name

def main():
    # Get the directory where the script is located
    script_dir = Path(sys.path[0])
    
    # Define and create the untested folder if it doesn't exist
    untested_dir = script_dir / "untested"
    untested_dir.mkdir(exist_ok=True)
    
    # Read the CSV file
    csv_path = script_dir / "docsforada.csv"
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: Could not find CSV file at {csv_path}")
        return
    
    # Find the eligibility column (case insensitive)
    eligibility_col = None
    for col in df.columns:
        if "eligible for exec doc conversion" in col.lower():
            eligibility_col = col
            break
    
    if not eligibility_col:
        print("Error: Could not find eligibility column in CSV")
        print(f"Available columns: {', '.join(df.columns)}")
        return
    
    # Find title and URL columns
    title_col = None
    url_col = None
    for col in df.columns:
        if col.lower() == "title":
            title_col = col
        elif "rawgithuburl" in col.lower():
            url_col = col
    
    if not title_col or not url_col:
        print("Error: Could not find required columns")
        print(f"Available columns: {', '.join(df.columns)}")
        return
    
    # Filter rows where eligibility is "yes"
    filtered_df = df[df[eligibility_col].str.lower() == "yes"]
    
    if filtered_df.empty:
        print("No eligible documents found for conversion.")
        return
    
    print(f"Found {len(filtered_df)} eligible documents for conversion.")
    
    # Process each filtered row
    for index, row in filtered_df.iterrows():
        title = row[title_col]
        github_url = row[url_col]
        
        print(f"Processing: {title}")
        
        # Skip if URL is invalid
        if not isinstance(github_url, str) or not github_url.startswith("http"):
            print(f"  Skipping: Invalid URL - {github_url}")
            continue
        
        # Create folder for the document
        folder_name = create_smart_folder_name(title)
        folder_path = untested_dir / folder_name
        folder_path.mkdir(exist_ok=True)
        
        # Fetch content from GitHub
        try:
            response = requests.get(github_url)
            response.raise_for_status()
            content = response.text
            
            # Save to markdown file
            file_path = folder_path / "README.md"
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)
            
            print(f"  ✓ Successfully saved to {folder_path}")
        
        except Exception as e:
            print(f"  ✗ Error downloading {github_url}: {str(e)}")

if __name__ == "__main__":
    main()
    print("Processing complete!")