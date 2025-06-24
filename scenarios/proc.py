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
# #                 print(f"  Created: {target_folder}")
# #                 print(f"  Copied to: {target_file}")
                
# #         except Exception as e:
# #             print(f"  ERROR processing {file_path}: {e}")

# # def main():
# #     parser = argparse.ArgumentParser(description="Process success markdown files")
# #     parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
# #     args = parser.parse_args()
    
# #     source_dir = "tools/success"
# #     target_dir = "scenarios"
    
# #     print(f"Source directory: {source_dir}")
# #     print(f"Target directory: {target_dir}")
    
# #     if args.dry_run:
# #         print("\n*** DRY RUN MODE - No files will be moved ***\n")
    
# #     process_success_files(source_dir, target_dir, dry_run=args.dry_run)
# #     print("\nProcessing complete!")

# # if __name__ == "__main__":
# #     main()

# #!/usr/bin/env python3
# import json
# import requests
# from bs4 import BeautifulSoup
# import re
# import time
# import os
# import shutil
# from pathlib import Path

# def extract_github_path_from_url(doc_url):
#     """Extract GitHub path from a documentation URL"""
#     try:
#         # Make request to the documentation URL
#         response = requests.get(doc_url, timeout=10)
#         response.raise_for_status()
        
#         # Parse HTML content
#         soup = BeautifulSoup(response.text, 'html.parser')
        
#         # Find all links that contain github.com and end with .md
#         github_links = []
#         for link in soup.find_all('a', href=True):
#             href = link['href']
#             if 'github.com' in href and href.endswith('.md'):
#                 github_links.append(href)
        
#         if not github_links:
#             return None
            
#         # Use the first matching link
#         github_url = github_links[0]
        
#         # Parse the GitHub URL to extract the path
#         # Example: https://github.com/MicrosoftDocs/azure-aks-docs/blob/main/articles/aks/istio-scale.md
#         match = re.search(r'github\.com/([^/]+)/(.+?)(?:/blob/[^/]+)?/(.+)', github_url)
#         if match:
#             org = match.group(1)
#             repo = match.group(2)
#             path = match.group(3)
            
#             # Construct the path without blob/main
#             full_path = f"{repo}/{path}"
#             return full_path
            
#     except Exception as e:
#         print(f"Error processing {doc_url}: {str(e)}")
#         return None

# def move_file_to_new_location(old_path, new_path, base_dir='.'):
#     """Move file from old path to new path, creating directories as needed"""
#     try:
#         old_file_path = Path(base_dir) / old_path
#         new_file_path = Path(base_dir) / new_path
        
#         # Check if source file exists
#         if not old_file_path.exists():
#             print(f"  ⚠️  Source file not found: {old_path}")
#             return False
        
#         # Check if destination already exists
#         if new_file_path.exists():
#             print(f"  ⚠️  Destination file already exists: {new_path}")
#             return False
        
#         # Create destination directory if it doesn't exist
#         new_file_path.parent.mkdir(parents=True, exist_ok=True)
        
#         # Move the file
#         shutil.move(str(old_file_path), str(new_file_path))
#         print(f"  ✅ File moved: {old_path} → {new_path}")
        
#         # Clean up empty directories in the old path
#         try:
#             old_dir = old_file_path.parent
#             while old_dir != Path(base_dir) and not any(old_dir.iterdir()):
#                 old_dir.rmdir()
#                 print(f"  🗑️  Removed empty directory: {old_dir}")
#                 old_dir = old_dir.parent
#         except Exception:
#             pass  # Ignore errors when cleaning up directories
        
#         return True
#     except Exception as e:
#         print(f"  ❌ Error moving file: {str(e)}")
#         return False

# def update_metadata_and_move_files():
#     """Update metadata.json keys with GitHub paths and move files"""
#     # Load metadata.json
#     with open('metadata.json', 'r') as f:
#         metadata = json.load(f)
    
#     # Find the starting index
#     start_found = False
#     start_key = "IstioPerformanceAKS/istio-performance-aks.md"
    
#     print("Extracting GitHub paths, updating keys, and moving files...\n")
    
#     # Track updates
#     updates_made = 0
#     files_moved = 0
    
#     # Keep track of file movements for summary
#     file_movements = []
    
#     for item in metadata:
#         # Skip until we find the starting key
#         if not start_found:
#             if item.get('key') == start_key:
#                 start_found = True
#             else:
#                 continue
        
#         # Only process items with active status and documentationUrl
#         if item.get('status') == 'active' and item.get('documentationUrl'):
#             old_key = item.get('key', 'Unknown')
#             doc_url = item['documentationUrl']
            
#             print(f"Processing: {old_key}")
#             print(f"URL: {doc_url}")
            
#             # Extract GitHub path
#             github_path = extract_github_path_from_url(doc_url)
            
#             if github_path:
#                 # Update the key field
#                 item['key'] = github_path
#                 updates_made += 1
#                 print(f"Old key: {old_key}")
#                 print(f"New key: {github_path}")
#                 print(f"✅ Key updated successfully")
                
#                 # Move the file if paths are different
#                 if old_key != github_path:
#                     if move_file_to_new_location(old_key, github_path):
#                         files_moved += 1
#                         file_movements.append({
#                             'old_path': old_key,
#                             'new_path': github_path,
#                             'title': item.get('title', 'Unknown')
#                         })
#             else:
#                 print("❌ No GitHub link found - keeping original key and file location")
            
#             print("-" * 80)
            
#             # Add a small delay to avoid rate limiting
#             time.sleep(0.5)
    
#     # Save the updated metadata
#     with open('metadata.json', 'w') as f:
#         json.dump(metadata, f, indent=4)
    
#     print(f"\n✅ Update complete!")
#     print(f"   - {updates_made} keys were updated")
#     print(f"   - {files_moved} files were moved")
#     print("   - Updated metadata saved to: metadata_updated.json")
    
#     # Create a file movements summary
#     if file_movements:
#         print("\n📁 File Movement Summary:")
#         with open('file_movements.json', 'w') as f:
#             json.dump(file_movements, f, indent=4)
#         print("   - File movements saved to: file_movements.json")
        
#         # Also create a simple text summary
#         with open('file_movements.txt', 'w') as f:
#             f.write("FILE MOVEMENTS SUMMARY\n")
#             f.write("=" * 80 + "\n\n")
#             for movement in file_movements:
#                 f.write(f"Title: {movement['title']}\n")
#                 f.write(f"From: {movement['old_path']}\n")
#                 f.write(f"To:   {movement['new_path']}\n")
#                 f.write("-" * 80 + "\n")
#         print("   - Text summary saved to: file_movements.txt")
    
#     # Create a mapping file for reference
#     print("\nCreating key mapping file...")
    
#     # Reload original metadata to create mapping
#     with open('metadata.json', 'r') as f:
#         original_metadata = json.load(f)
    
#     mapping = []
#     for i, item in enumerate(original_metadata):
#         if i < len(metadata) and metadata[i].get('key') != item.get('key'):
#             mapping.append({
#                 'old_key': item.get('key'),
#                 'new_key': metadata[i].get('key'),
#                 'title': item.get('title')
#             })
    
#     with open('key_mapping.json', 'w') as f:
#         json.dump(mapping, f, indent=4)
    
#     print("Key mapping saved to: key_mapping.json")

# if __name__ == "__main__":
#     update_metadata_and_move_files()

#!/usr/bin/env python3
import json
import os
from pathlib import Path
from collections import defaultdict

def check_file_locations():
    """Check if physical file locations match the paths in metadata.json"""
    
    # Load metadata.json
    with open('metadata.json', 'r') as f:
        metadata = json.load(f)
    
    print("Checking file locations against metadata.json...\n")
    print("=" * 80)
    
    # Statistics
    stats = {
        'total': 0,
        'found': 0,
        'missing': 0,
        'active': 0,
        'inactive': 0,
        'no_key': 0
    }
    
    # Lists to track issues
    missing_files = []
    found_files = []
    no_key_items = []
    
    # Check each entry
    for i, item in enumerate(metadata):
        stats['total'] += 1
        
        # Check if item has a key
        if not item.get('key'):
            stats['no_key'] += 1
            no_key_items.append({
                'index': i,
                'title': item.get('title', 'No title'),
                'status': item.get('status', 'unknown')
            })
            continue
        
        key = item['key']
        status = item.get('status', 'unknown')
        title = item.get('title', 'No title')
        
        # Track active/inactive
        if status == 'active':
            stats['active'] += 1
        elif status == 'inactive':
            stats['inactive'] += 1
        
        # Check if file exists at the specified path
        file_path = Path(key)
        
        if file_path.exists():
            stats['found'] += 1
            found_files.append({
                'path': key,
                'status': status,
                'title': title
            })
        else:
            stats['missing'] += 1
            missing_files.append({
                'path': key,
                'status': status,
                'title': title,
                'expected_location': str(file_path.absolute())
            })
    
    # Print summary
    print(f"📊 SUMMARY")
    print(f"   Total entries: {stats['total']}")
    print(f"   Active: {stats['active']}")
    print(f"   Inactive: {stats['inactive']}")
    print(f"   Files found: {stats['found']}")
    print(f"   Files missing: {stats['missing']}")
    print(f"   Entries without key: {stats['no_key']}")
    print()
    
    # Report missing files
    if missing_files:
        print(f"❌ MISSING FILES ({len(missing_files)})")
        print("-" * 80)
        for item in missing_files:
            print(f"Status: {item['status']}")
            print(f"Title: {item['title']}")
            print(f"Path: {item['path']}")
            print(f"Expected at: {item['expected_location']}")
            print("-" * 40)
        print()
    
    # Report entries without keys
    if no_key_items:
        print(f"⚠️  ENTRIES WITHOUT KEY ({len(no_key_items)})")
        print("-" * 80)
        for item in no_key_items:
            print(f"Index: {item['index']}")
            print(f"Status: {item['status']}")
            print(f"Title: {item['title']}")
            print("-" * 40)
        print()
    
    # Show some found files as confirmation
    if found_files:
        print(f"✅ SAMPLE OF FOUND FILES (showing first 5)")
        print("-" * 80)
        for item in found_files[:5]:
            print(f"Status: {item['status']}")
            print(f"Title: {item['title']}")
            print(f"Path: {item['path']}")
            print("-" * 40)
        print()
    
    # Check for orphaned files (files that exist but aren't in metadata)
    print("🔍 Checking for orphaned files...")
    
    # Get all keys from metadata
    metadata_paths = set()
    for item in metadata:
        if item.get('key'):
            metadata_paths.add(item['key'])
    
    # Common directories to scan for .md files
    directories_to_scan = [
        'azure-docs',
        'azure-aks-docs', 
        'azure-databases-docs',
        'azure-compute-docs',
        'azure-management-docs',
        'azure-stack-docs',
        'SupportArticles-docs',
        'upstream'
    ]
    
    orphaned_files = []
    for directory in directories_to_scan:
        if Path(directory).exists():
            for md_file in Path(directory).rglob('*.md'):
                relative_path = str(md_file)
                if relative_path not in metadata_paths:
                    orphaned_files.append(relative_path)
    
    if orphaned_files:
        print(f"\n⚠️  ORPHANED FILES (exist but not in metadata): {len(orphaned_files)}")
        print("-" * 80)
        for file_path in orphaned_files[:10]:  # Show first 10
            print(f"   {file_path}")
        if len(orphaned_files) > 10:
            print(f"   ... and {len(orphaned_files) - 10} more")
    else:
        print("\n✅ No orphaned files found")
    
    # Final status
    print("\n" + "=" * 80)
    if stats['missing'] == 0 and stats['no_key'] == 0:
        print("✅ All files are in their correct locations!")
    else:
        print(f"❌ Issues found: {stats['missing']} missing files, {stats['no_key']} entries without keys")
    
    # Save detailed report
    report = {
        'summary': stats,
        'missing_files': missing_files,
        'found_files': found_files,
        'no_key_items': no_key_items,
        'orphaned_files': orphaned_files,
        'check_date': str(Path.cwd()),
        'working_directory': str(Path.cwd())
    }
    
    with open('file_location_check_report.json', 'w') as f:
        json.dump(report, f, indent=4)
    
    print(f"\n📄 Detailed report saved to: file_location_check_report.json")

if __name__ == "__main__":
    check_file_locations()