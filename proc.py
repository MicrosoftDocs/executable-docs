#!/usr/bin/env python3
import os
import re
import shutil
from pathlib import Path
import yaml
from openai import AzureOpenAI
import argparse

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_DEPLOYMENT = "gpt-4.1"
AZURE_OPENAI_API_VERSION = "2024-12-01-preview"

def setup_azure_openai():
    """Initialize Azure OpenAI client"""
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY:
        raise ValueError("Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables")
    
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )
    return client

def extract_title_from_markdown(file_path):
    """Extract title from markdown file metadata or content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Try to extract YAML frontmatter
    yaml_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if yaml_match:
        try:
            metadata = yaml.safe_load(yaml_match.group(1))
            if metadata and 'title' in metadata:
                return metadata['title']
        except:
            pass
    
    # Try to find the first H1 heading
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()
    
    # Fallback to filename
    return Path(file_path).stem

def generate_folder_name(client, title, file_content_snippet):
    """Use Azure OpenAI to generate an intuitive folder name"""
    prompt = f"""Given this document title: "{title}"
And this content snippet from the document:
{file_content_snippet[:500]}

Generate a concise folder name following these rules:
1. Use PascalCase (capitalize first letter of each word)
2. Be descriptive but concise (2-4 words max)
3. Should reflect the main topic/technology
4. Examples: GPUNodePoolAKS, DeployIGOnAKS, AzureMLWorkspace

Return ONLY the folder name, nothing else."""

    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates folder names."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=50
        )
        folder_name = response.choices[0].message.content.strip()
        # Ensure it's valid folder name
        folder_name = re.sub(r'[^\w]', '', folder_name)
        return folder_name
    except Exception as e:
        print(f"Error generating folder name with Azure OpenAI: {e}")
        # Fallback to title-based name
        return ''.join(word.capitalize() for word in re.findall(r'\w+', title))[:30]

def pascal_to_kebab(name):
    """Convert PascalCase to kebab-case, preserving acronyms like AKS."""
    # split on transitions from uppercase to lowercase or between acronyms
    tokens = re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))', name)
    return '-'.join(t.lower() for t in tokens)

def process_success_files(source_dir, target_dir, dry_run=False):
    """Process all markdown files with 'success' in filename"""
    source_path = Path(source_dir)
    target_path = Path(target_dir)
    
    if not source_path.exists():
        print(f"Source directory {source_dir} does not exist")
        return
    
    # Setup Azure OpenAI
    try:
        client = setup_azure_openai()
        print("Azure OpenAI client initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize Azure OpenAI: {e}")
        print("Will use fallback naming method")
        client = None
    
    # Find all markdown files with 'success' in filename
    success_files = []
    for folder in source_path.iterdir():
        if folder.is_dir():
            for file in folder.glob("*.md"):
                if "success" in file.name.lower():
                    success_files.append(file)
    
    print(f"Found {len(success_files)} success files to process")
    
    for file_path in success_files:
        try:
            print(f"\nProcessing: {file_path}")
            
            # Extract title
            title = extract_title_from_markdown(file_path)
            print(f"  Title: {title}")
            
            # Read file content for OpenAI
            with open(file_path, 'r', encoding='utf-8') as f:
                content_snippet = f.read()[:1000]
            
            # Generate folder name
            if client:
                folder_name = generate_folder_name(client, title, content_snippet)
            else:
                # Fallback method
                folder_name = ''.join(word.capitalize() for word in re.findall(r'\w+', title))[:30]
            
            print(f"  Folder name: {folder_name}")
            
            # Convert to kebab-case for filename
            file_name = pascal_to_kebab(folder_name) + ".md"
            print(f"  File name: {file_name}")
            
            # Create target path
            target_folder = target_path / folder_name
            target_file = target_folder / file_name
            
            if dry_run:
                print(f"  [DRY RUN] Would create: {target_folder}")
                print(f"  [DRY RUN] Would copy to: {target_file}")
            else:
                # Create folder and copy file
                target_folder.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, target_file)
                print(f"  Created: {target_folder}")
                print(f"  Copied to: {target_file}")
                
        except Exception as e:
            print(f"  ERROR processing {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Process success markdown files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    args = parser.parse_args()
    
    source_dir = "tools/success"
    target_dir = "scenarios"
    
    print(f"Source directory: {source_dir}")
    print(f"Target directory: {target_dir}")
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No files will be moved ***\n")
    
    process_success_files(source_dir, target_dir, dry_run=args.dry_run)
    print("\nProcessing complete!")

if __name__ == "__main__":
    main()