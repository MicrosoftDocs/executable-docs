# #!/usr/bin/env python3
# import os
# import re
# import shutil
# import json
# from pathlib import Path
# import yaml
# from openai import AzureOpenAI
# import argparse

# # Azure OpenAI configuration
# AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
# AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
# AZURE_OPENAI_DEPLOYMENT = "gpt-4.1"
# AZURE_OPENAI_API_VERSION = "2024-12-01-preview"

# def setup_azure_openai():
#     """Initialize Azure OpenAI client"""
#     if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY:
#         raise ValueError("Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables")
    
#     client = AzureOpenAI(
#         azure_endpoint=AZURE_OPENAI_ENDPOINT,
#         api_key=AZURE_OPENAI_KEY,
#         api_version=AZURE_OPENAI_API_VERSION
#     )
#     return client

# def extract_title_from_markdown(file_path):
#     """Extract title from markdown file metadata or content"""
#     with open(file_path, 'r', encoding='utf-8') as f:
#         content = f.read()
    
#     # Try to extract YAML frontmatter
#     yaml_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
#     if yaml_match:
#         try:
#             metadata = yaml.safe_load(yaml_match.group(1))
#             if metadata and 'title' in metadata:
#                 return metadata['title']
#         except:
#             pass
    
#     # Try to find the first H1 heading
#     h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
#     if h1_match:
#         return h1_match.group(1).strip()
    
#     # Fallback to filename
#     return Path(file_path).stem

# def extract_description_from_markdown(file_path):
#     """Extract description from markdown file metadata"""
#     with open(file_path, 'r', encoding='utf-8') as f:
#         content = f.read()
    
#     # Try to extract YAML frontmatter
#     yaml_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
#     if yaml_match:
#         try:
#             metadata = yaml.safe_load(yaml_match.group(1))
#             if metadata and 'description' in metadata:
#                 return metadata['description']
#         except:
#             pass
    
#     # Fallback to title
#     return extract_title_from_markdown(file_path)

# def extract_next_steps(client, file_content):
#     """Use Azure OpenAI to extract next steps from document"""
#     prompt = f"""From this document content, extract any "Next Steps" or related tutorial links mentioned.
# Return as a JSON array of objects with 'title' and 'url' fields.
# If no next steps are found, return an empty array.

# Document content:
# {file_content[:3000]}

# Return ONLY valid JSON array, nothing else."""

#     try:
#         response = client.chat.completions.create(
#             model=AZURE_OPENAI_DEPLOYMENT,
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant that extracts structured data from documents."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.3,
#             max_tokens=500
#         )
#         result = response.choices[0].message.content.strip()
#         return json.loads(result)
#     except:
#         return []

# def extract_env_variables(client, file_content):
#     """Use Azure OpenAI to extract environment variables from document"""
#     prompt = f"""From this document content, identify all environment variables that need to be set before running the commands.
# Look for patterns like:
# - export VARIABLE_NAME=
# - $VARIABLE_NAME or ${{VARIABLE_NAME}}
# - Variables mentioned in instructions

# For each variable, provide a user-friendly title.
# Return as a JSON array of objects with these fields:
# - inputType: "textInput"
# - commandKey: the exact variable name
# - title: user-friendly title in Title Case (e.g., RESOURCE_GROUP -> "Resource Group Name")
# - defaultValue: ""

# Document content:
# {file_content[:3000]}

# Return ONLY valid JSON array, nothing else."""

#     try:
#         response = client.chat.completions.create(
#             model=AZURE_OPENAI_DEPLOYMENT,
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant that extracts environment variables from technical documents."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.3,
#             max_tokens=500
#         )
#         result = response.choices[0].message.content.strip()
#         return json.loads(result)
#     except:
#         return []

# def generate_folder_name(client, title, file_content_snippet):
#     """Use Azure OpenAI to generate an intuitive folder name"""
#     prompt = f"""Given this document title: "{title}"
# And this content snippet from the document:
# {file_content_snippet[:500]}

# Generate a concise folder name following these rules:
# 1. Use PascalCase (capitalize first letter of each word)
# 2. Be descriptive but concise (2-4 words max)
# 3. Should reflect the main topic/technology
# 4. Examples: GPUNodePoolAKS, DeployIGOnAKS, AzureMLWorkspace

# Return ONLY the folder name, nothing else."""

#     try:
#         response = client.chat.completions.create(
#             model=AZURE_OPENAI_DEPLOYMENT,
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant that generates folder names."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.3,
#             max_tokens=50
#         )
#         folder_name = response.choices[0].message.content.strip()
#         # Ensure it's valid folder name
#         folder_name = re.sub(r'[^\w]', '', folder_name)
#         return folder_name
#     except Exception as e:
#         print(f"Error generating folder name with Azure OpenAI: {e}")
#         # Fallback to title-based name
#         return ''.join(word.capitalize() for word in re.findall(r'\w+', title))[:30]

# def pascal_to_kebab(name):
#     """Convert PascalCase to kebab-case, preserving acronyms like AKS."""
#     # split on transitions from uppercase to lowercase or between acronyms
#     tokens = re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))', name)
#     return '-'.join(t.lower() for t in tokens)

# def update_metadata_json(scenarios_dir, client):
#     """Update metadata.json with missing scenario entries"""
#     metadata_file = Path(scenarios_dir) / "metadata.json"
    
#     # Load existing metadata
#     if metadata_file.exists():
#         with open(metadata_file, 'r', encoding='utf-8') as f:
#             metadata = json.load(f)
#     else:
#         metadata = []
    
#     # Get all existing keys
#     existing_keys = {entry['key'] for entry in metadata}
    
#     # Check all subdirectories in scenarios folder
#     scenarios_path = Path(scenarios_dir)
#     new_entries = []
    
#     for folder in scenarios_path.iterdir():
#         if folder.is_dir() and folder.name != "__pycache__":
#             # Find markdown files in the folder
#             md_files = list(folder.glob("*.md"))
            
#             for md_file in md_files:
#                 # Create the key
#                 key = f"{folder.name}/{md_file.name}"
                
#                 # Check if this key exists in metadata
#                 if not any(key in existing_key for existing_key in existing_keys):
#                     print(f"\nProcessing new metadata entry for: {key}")
                    
#                     # Read file content
#                     with open(md_file, 'r', encoding='utf-8') as f:
#                         content = f.read()
                    
#                     # Extract information
#                     title = extract_title_from_markdown(md_file)
#                     description = extract_description_from_markdown(md_file)
                    
#                     # Use AI to extract next steps and env variables
#                     next_steps = extract_next_steps(client, content)
#                     configurable_params = extract_env_variables(client, content)
                    
#                     # Create new entry
#                     new_entry = {
#                         "status": "active",
#                         "key": key,
#                         "title": title,
#                         "description": description,
#                         "stackDetails": "",
#                         "sourceUrl": f"https://raw.githubusercontent.com/MicrosoftDocs/executable-docs/main/scenarios/{key}",
#                         "documentationUrl": "",
#                         "nextSteps": next_steps,
#                         "configurations": {
#                             "permissions": [],
#                             "configurableParams": configurable_params
#                         }
#                     }
                    
#                     new_entries.append(new_entry)
#                     print(f"  Added metadata for: {key}")
    
#     # Append new entries to metadata
#     if new_entries:
#         metadata.extend(new_entries)
        
#         # Write updated metadata back to file
#         with open(metadata_file, 'w', encoding='utf-8') as f:
#             json.dump(metadata, f, indent=4, ensure_ascii=False)
        
#         print(f"\nAdded {len(new_entries)} new entries to metadata.json")
#     else:
#         print("\nNo new entries needed for metadata.json")

# source_dir = "tools/success"
# target_dir = "scenarios"
# # Setup Azure OpenAI
# try:
#     client = setup_azure_openai()
#     print("Azure OpenAI client initialized successfully")
# except Exception as e:
#     print(f"Warning: Could not initialize Azure OpenAI: {e}")
#     print("Will use fallback naming method")
#     client = None
# print("\n" + "="*60)
# print("Updating metadata.json...")
# update_metadata_json(target_dir, client)
# import sys
# sys.exit(0)

# def process_success_files(source_dir, target_dir, dry_run=False):
#     """Process all markdown files with 'success' in filename"""
#     source_path = Path(source_dir)
#     target_path = Path(target_dir)
    
#     if not source_path.exists():
#         print(f"Source directory {source_dir} does not exist")
#         return
    
#     # Setup Azure OpenAI
#     try:
#         client = setup_azure_openai()
#         print("Azure OpenAI client initialized successfully")
#     except Exception as e:
#         print(f"Warning: Could not initialize Azure OpenAI: {e}")
#         print("Will use fallback naming method")
#         client = None
    
#     # Find all markdown files with 'success' in filename
#     success_files = []
#     for folder in source_path.iterdir():
#         if folder.is_dir():
#             for file in folder.glob("*.md"):
#                 if "success" in file.name.lower():
#                     success_files.append(file)
    
#     print(f"Found {len(success_files)} success files to process")
    
#     for file_path in success_files:
#         try:
#             print(f"\nProcessing: {file_path}")
            
#             # Extract title
#             title = extract_title_from_markdown(file_path)
#             print(f"  Title: {title}")
            
#             # Read file content for OpenAI
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 content_snippet = f.read()[:1000]
            
#             # Generate folder name
#             if client:
#                 folder_name = generate_folder_name(client, title, content_snippet)
#             else:
#                 # Fallback method
#                 folder_name = ''.join(word.capitalize() for word in re.findall(r'\w+', title))[:30]
            
#             print(f"  Folder name: {folder_name}")
            
#             # Convert to kebab-case for filename
#             file_name = pascal_to_kebab(folder_name) + ".md"
#             print(f"  File name: {file_name}")
            
#             # Create target path
#             target_folder = target_path / folder_name
#             target_file = target_folder / file_name
            
#             if dry_run:
#                 print(f"  [DRY RUN] Would create: {target_folder}")
#                 print(f"  [DRY RUN] Would copy to: {target_file}")
#             else:
#                 # Create folder and copy file
#                 target_folder.mkdir(parents=True, exist_ok=True)
#                 shutil.copy2(file_path, target_file)
#                 print(f"  Created: {target_folder}")
#                 print(f"  Copied to: {target_file}")
                
#         except Exception as e:
#             print(f"  ERROR processing {file_path}: {e}")

# def main():
#     parser = argparse.ArgumentParser(description="Process success markdown files")
#     parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
#     args = parser.parse_args()
    
#     source_dir = "tools/success"
#     target_dir = "scenarios"
    
#     print(f"Source directory: {source_dir}")
#     print(f"Target directory: {target_dir}")
    
#     if args.dry_run:
#         print("\n*** DRY RUN MODE - No files will be moved ***\n")
    
#     process_success_files(source_dir, target_dir, dry_run=args.dry_run)
#     print("\nProcessing complete!")

# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3
import json
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import time

def extract_github_path_from_url(doc_url):
    """Extract GitHub path from a documentation URL"""
    try:
        # Make request to the documentation URL
        response = requests.get(doc_url, timeout=10)
        response.raise_for_status()
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links that contain github.com and end with .md
        github_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'github.com' in href and href.endswith('.md'):
                github_links.append(href)
        
        if not github_links:
            return None
            
        # Use the first matching link
        github_url = github_links[0]
        
        # Parse the GitHub URL to extract the path
        # Example: https://github.com/MicrosoftDocs/azure-aks-docs/blob/main/articles/aks/istio-scale.md
        match = re.search(r'github\.com/([^/]+)/(.+?)(?:/blob/[^/]+)?/(.+)', github_url)
        if match:
            org = match.group(1)
            repo = match.group(2)
            path = match.group(3)
            
            # Construct the path without blob/main
            full_path = f"{repo}/{path}"
            return full_path
            
    except Exception as e:
        print(f"Error processing {doc_url}: {str(e)}")
        return None

def main():
    # Load metadata.json
    with open('scenarios/metadata.json', 'r') as f:
        metadata = json.load(f)
    
    # Find the starting index
    start_found = False
    start_key = "IstioPerformanceAKS/istio-performance-aks.md"
    
    print("Extracting GitHub paths from documentation URLs...\n")
    
    for item in metadata:
        # Skip until we find the starting key
        if not start_found:
            if item.get('key') == start_key:
                start_found = True
            else:
                continue
        
        # Only process items with active status and documentationUrl
        if item.get('status') == 'active' and item.get('documentationUrl'):
            key = item.get('key', 'Unknown')
            doc_url = item['documentationUrl']
            
            print(f"Processing: {key}")
            print(f"URL: {doc_url}")
            
            # Extract GitHub path
            github_path = extract_github_path_from_url(doc_url)
            
            if github_path:
                print(f"GitHub Path: {github_path}")
            else:
                print("No GitHub link found")
            
            print("-" * 80)
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)

if __name__ == "__main__":
    main()
