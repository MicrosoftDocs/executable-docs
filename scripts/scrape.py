# import requests
# from bs4 import BeautifulSoup
# import csv

# def scrape_html(url):
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.text, "html.parser")
#         return soup
#     except requests.RequestException as e:
#         print(f"Error fetching {url}: {e}")
#         return None

# def github_to_raw(url):
#     # Converts GitHub file URL to raw URL (with refs/heads)
#     # Example: https://github.com/org/repo/blob/branch/path/to/file.md
#     # To:      https://raw.githubusercontent.com/org/repo/refs/heads/branch/path/to/file.md
#     if "github.com" in url and "/blob/" in url:
#         parts = url.split('/')
#         org = parts[3]
#         repo = parts[4]
#         branch = parts[6]
#         file_path = '/'.join(parts[7:])
#         return f"https://raw.githubusercontent.com/{org}/{repo}/refs/heads/{branch}/{file_path}"
#     return None

# def get_first_github_link(url):
#     soup = scrape_html(url)
#     if soup:
#         github_link = next((a['href'] for a in soup.find_all('a', href=True) if 'github.com' in a['href']), None)
#         return github_link
#     return None

# input_csv = "aks-docs.csv"
# output_csv = "new.csv"

# with open(input_csv, newline='', encoding='utf-8') as infile, \
#      open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
#     reader = csv.DictReader(infile)
#     # Insert RawGithubUrl right after Url column
#     fieldnames = []
#     for fn in reader.fieldnames:
#         fieldnames.append(fn)
#         if fn == 'Url':
#             fieldnames.append('RawGithubUrl')
#     writer = csv.DictWriter(outfile, fieldnames=fieldnames)
#     writer.writeheader()

#     for row in reader:
#         url = row.get('Url', '')
#         github_link = get_first_github_link(url)
#         raw_url = github_to_raw(github_link) if github_link else ""
#         # Insert RawGithubUrl right after Url
#         new_row = {}
#         for fn in reader.fieldnames:
#             new_row[fn] = row.get(fn, '')
#             if fn == 'Url':
#                 new_row['RawGithubUrl'] = raw_url
#         writer.writerow(new_row)



# import csv
# import requests

# input_csv = "new.csv"
# output_csv = "new_with_valid.csv"

# def has_code_block(raw_url):
#     if not raw_url:
#         return "no"
#     try:
#         resp = requests.get(raw_url, timeout=10)
#         resp.raise_for_status()
#         return "yes" if "```" in resp.text else "no"
#     except Exception:
#         return "no"

# with open(input_csv, newline='', encoding='utf-8') as infile, \
#      open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
#     reader = csv.DictReader(infile)
#     # Insert 'valid' column after 'RawGithubUrl'
#     fieldnames = []
#     for fn in reader.fieldnames:
#         fieldnames.append(fn)
#         if fn == 'RawGithubUrl':
#             fieldnames.append('valid')
#     writer = csv.DictWriter(outfile, fieldnames=fieldnames)
#     writer.writeheader()

#     for row in reader:
#         raw_url = row.get('RawGithubUrl', '')
#         valid = has_code_block(raw_url)
#         new_row = {}
#         for fn in reader.fieldnames:
#             new_row[fn] = row.get(fn, '')
#             if fn == 'RawGithubUrl':
#                 new_row['valid'] = valid
#         writer.writerow(new_row)



# import csv
# import requests

# input_csv = "new_with_valid.csv"
# output_csv = "new_with_valid_and_includes.csv"

# def has_code_block(raw_url):
#     if not raw_url:
#         return "no"
#     try:
#         resp = requests.get(raw_url, timeout=10)
#         resp.raise_for_status()
#         return "yes" if "```" in resp.text else "no"
#     except Exception:
#         return "no"

# def has_include(raw_url):
#     if not raw_url:
#         return "no"
#     try:
#         resp = requests.get(raw_url, timeout=10)
#         resp.raise_for_status()
#         return "yes" if "!INCLUDE" in resp.text else "no"
#     except Exception:
#         return "no"

# with open(input_csv, newline='', encoding='utf-8') as infile, \
#      open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
#     reader = csv.DictReader(infile)
#     # Insert 'includes' column after 'valid'
#     fieldnames = []
#     for fn in reader.fieldnames:
#         fieldnames.append(fn)
#         if fn == 'valid':
#             fieldnames.append('includes')
#     writer = csv.DictWriter(outfile, fieldnames=fieldnames)
#     writer.writeheader()

#     for row in reader:
#         raw_url = row.get('RawGithubUrl', '')
#         includes = has_include(raw_url)
#         new_row = {}
#         for fn in reader.fieldnames:
#             new_row[fn] = row.get(fn, '')
#             if fn == 'valid':
#                 new_row['includes'] = includes
#         writer.writerow(new_row)

# import csv

# input_file = "test.csv"
# output_file = "test.csv"

# # Columns to keep
# keep_columns = ["RawGithubUrl", "valid", "includes", "Title"]

# rows = []
# with open(input_file, newline='', encoding='utf-8') as csvfile:
#     reader = csv.DictReader(csvfile)
#     for row in reader:
#         # Remove rows where valid == "no" and includes == "no"
#         if row["valid"].strip().lower() == "no" and row["includes"].strip().lower() == "no":
#             continue
#         # Keep only the desired columns
#         filtered_row = {col: row[col] for col in keep_columns}
#         rows.append(filtered_row)

# # Write filtered rows back to the same file
# with open(output_file, "w", newline='', encoding='utf-8') as csvfile:
#     writer = csv.DictWriter(csvfile, fieldnames=keep_columns)
#     writer.writeheader()
#     writer.writerows(rows)


# import csv
# import os
# import requests
# from urllib.parse import urlparse
# import hashlib

# csv_path = "test.csv"
# num_to_download = 11

# def safe_folder_name(url):
#     parsed = urlparse(url)
#     base = os.path.basename(parsed.path)
#     # Remove .md extension if present
#     if base.lower().endswith('.md'):
#         base = base[:-3]
#     if not base:
#         base = hashlib.md5(url.encode()).hexdigest()
#     return base.replace('.', '_')

# with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
#     reader = csv.DictReader(csvfile)
#     # Normalize fieldnames to strip whitespace
#     reader.fieldnames = [fn.strip() for fn in reader.fieldnames]
#     for i, row in enumerate(reader):
#         if i >= num_to_download:
#             break
#         url = row.get("RawGithubUrl") or row.get("RawGithubUrl\r") or row.get("RawGithubUrl\n")
#         if not url:
#             print(f"Row {i+1}: No RawGithubUrl found, skipping.")
#             continue
#         folder = safe_folder_name(url)
#         os.makedirs(folder, exist_ok=True)
#         filename = os.path.basename(urlparse(url).path) or "document.md"
#         filepath = os.path.join(folder, filename)
#         try:
#             resp = requests.get(url, timeout=15)
#             resp.raise_for_status()
#             with open(filepath, "w", encoding="utf-8") as f:
#                 f.write(resp.text)
#             print(f"Downloaded {url} -> {filepath}")
#         except Exception as e:
#             print(f"Failed to download {url}: {e}")

import csv
import requests
import os
from openai import AzureOpenAI

# LLM setup (reuse from ada.py)
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
deployment_name = 'gpt-4.1'

def fetch_content(url):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return ""

def llm_check(content):
    prompt = """
You are an expert in technical documentation conversion. Given the following markdown content, determine if it is eligible for conversion to an Exec Doc based on these rules:

## 1. Command Execution Limitations

Supported:
- Any command that can run in a BASH terminal (e.g. bash, azurecli, azure-cli-interactive, azurecli-interactive code blocks).

Not supported:
- PowerShell scripts
- GUI-based instructions (steps that require clicking, navigating GUIs, or screenshots)
- Commands requiring sudo privileges
- Code blocks of languages that aren't bash/shell commands (e.g. SQL, Python, PowerShell, etc.)

Examples:

Supported:
```bash
export REGION="eastus"
export RESOURCE_GROUP="myResourceGroup"
az group create --name $RESOURCE_GROUP --location $REGION
```

Unsupported:
```sql
INSERT INTO myTable (name, value) VALUES ('test', 123);
```
```powershell
Get-Process
```
Instructions that require clicking buttons or using a GUI.

## 2. Azure Portal Custom Cloud Shell Constraints

Supported:
- Standard Azure resource operations (create, read, update, delete)
- Commands running within the user's subscription scope
- Standard service deployments (VMs, storage, networking)

Not supported:
- Commands requiring elevated Microsoft Graph API permissions
- Operations needing KeyVault special access
- Cross-subscription or tenant-level operations
- Commands requiring admin consent

Examples:

Supported:
```bash
export RESOURCE_GROUP="myResourceGroup"
export LOCATION="eastus"
az group create --name $RESOURCE_GROUP --location $LOCATION
```

Unsupported:
```bash
export APP_NAME="myApp"
# This requires elevated Graph API permissions and would fail
az ad app create --display-name $APP_NAME --native-app
```

**Instructions:**  
If eligible, answer ONLY "yes".  
If not, answer "no: <short reason>".

Content:
""" + content
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are a technical documentation eligibility checker."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.choices[0].message.content.strip()
        if answer.lower().startswith("yes"):
            return "yes", ""
        else:
            # Extract reason if present
            reason = answer.split(":", 1)[-1].strip() if ":" in answer else answer
            return "no", reason
    except Exception as e:
        return "no", f"LLM error: {e}"

input_csv = "new.csv"
output_csv = "updated.csv"
keywords = ["bash", "azurecli", "azure-cli-interactive", "azurecli-interactive"]

with open(input_csv, newline='', encoding='utf-8') as infile, \
     open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
    reader = csv.DictReader(infile)
    fieldnames = [f for f in reader.fieldnames if f not in ("valid", "includes")]
    fieldnames += ["eligible", "reason for ineligibility"]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        url = row["RawGithubUrl"]
        content = fetch_content(url)
        has_triple_backtick = "```" in content
        has_keyword = any(k in content for k in keywords)
        if has_triple_backtick and has_keyword:
            row["eligible"] = "yes"
            row["reason for ineligibility"] = ""
        else:
            # Use LLM for further eligibility check
            eligible, reason = llm_check(content)
            row["eligible"] = eligible
            row["reason for ineligibility"] = reason if not eligible == "yes" else ""
        # Remove unwanted columns
        row = {k: v for k, v in row.items() if k in fieldnames}
        writer.writerow(row)

print(f"Processed CSV written to {output_csv}")