# sync exec docs every day, metadata.json gets updated as soon as exec docs are synced, ie test runs on all docs as soon as it is selective localization happens as soon as the localization goes through main (which is 2-3 hours post sync), portal tests every monday with all exec docs from previous week and pushes changes to be reflected the next week
import os
import github
import shutil
import subprocess
import tempfile
import re
import json
import yaml
from datetime import datetime

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
g = github.Github(GITHUB_TOKEN)

def sync_markdown_files():
    query = "innovation-engine in:file language:markdown org:MicrosoftDocs -path:/localized/ -repo:MicrosoftDocs/executable-docs" 
    result = g.search_code(query)
    for file in result:
         if '-pr' not in file.repository.name:
            content_file = file.repository.get_contents(file.path)
            file_content = content_file.decoded_content.decode('utf-8')
            if '---' in file_content:
                metadata = file_content.split('---')[1]
                if 'ms.custom:' in metadata:
                    custom_values = metadata.split('ms.custom:')[1].split(',')
                    custom_values = [value.strip() for value in custom_values]
                    if 'innovation-engine' in custom_values:
                        dir_path = f'scenarios/{file.repository.name}/{os.path.dirname(file.path)}'
                        if not os.path.exists(dir_path):
                            os.makedirs(dir_path)
                        file_path = os.path.join(dir_path, os.path.basename(file.path))
                        
                        # base_dir = 'localized'
                        # for locale in sorted(os.listdir(base_dir)):
                        #     locale_dir = os.path.join(base_dir, locale, file_path)           
                        #     print(locale_dir)
                        #     import time
                        #     time.sleep(5)
                        
                        with open(file_path, 'w') as f:
                            f.write(file_content)

def install_ie():
    """Installs IE if it is not already on the path."""
    if shutil.which("ie") is not None:
        pass# print("IE is already installed. Skipping installation...")
        return
    print("Innovation Engine not detected. Installing IE...")
    original_dir = os.getcwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        process = subprocess.Popen(
            "sudo apt install unzip", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output, error = process.communicate()
        if error:
            print("Error (fixing it): ", error)

        install_result = subprocess.run(
            "curl -Lks https://aka.ms/install-ie | /bin/bash", shell=True
        )
        if install_result.returncode != 0:
            print("Failed to install IE")
        else:
            print("Successfully installed IE.")

    os.chdir(original_dir)

    if shutil.which("ie") is None:
        print(
            "IE was successfully installed but you need to add ~/.local/bin to your PATH to access it."
        )
        print("You can do so by adding the following line to your ~/.bashrc file:")
        print("export PATH=$PATH:~/.local/bin")
        exit(0)

def get_latest_error_log():
    error_line_num = 0
    log_file = "ie.log"
    with open(log_file, "r") as file:
        for i, line in enumerate(file, 1):
            if re.search(r"level=error", line):
                error_line_num = i

    lines_from_error = []
    with open(log_file, "r") as file:
        for i, line in enumerate(file, 1):
            if i >= error_line_num:
                lines_from_error.append(line)

    error_log = " ".join(lines_from_error)
    code = re.search(r"Code: (.+?)\n", error_log)
    message = re.search(r"Message: (.+?)\n", error_log)

    if code and message:
        return f"Code: {code.group(1)}, Message: {message.group(1)}"
    else:
        message = re.search(r"msg=(.+?)\n", error_log)
        if message:
            return f"{message.group(1)}"
        else:
            return " ".join(lines_from_error)

def author_has_commented(issue, author):
    comments = issue.get_comments()
    for comment in comments:
        if comment.user.login == author:
            return True
    return False

def run_tests():
    repo = g.get_repo("MicrosoftDocs/executable-docs")

    for root, dirs, files in os.walk('scenarios'):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                result = subprocess.run(['ie', 'test', file_path, '--environment', 'github-action'])

                if result.returncode != 0:
                    if os.path.isfile('scenarios/metadata.json'):
                        with open('scenarios/metadata.json', 'r') as f:
                            metadata = json.load(f)
                            for item in metadata:
                                if item['key'] == '/'.join(file_path.split('/')[1:]):
                                    item['status'] = 'inactive'
                                    break
                    with open(file_path, 'r') as f:
                        content = f.read()
                        author = re.search(r'author: (.+)', content)
                        ms_author = re.search(r'ms.author: (.+)', content)

                        if author and ms_author:
                            author = author.group(1)
                            ms_author = ms_author.group(1)
                            doc_link = f"https://github.com/MicrosoftDocs/{file_path.split('/')[1]}/blob/main/{'/'.join(file_path.split('/')[2:])}"
                            issue_title = f"DOC FAILING TESTS: {'/'.join(file_path.split('/')[1:])}"
                            issue_body = f"Hey @{author}! Your executable document is not working. Please fix the errors given below. And reply to this issue with any questions.\n\nLink to Doc: {doc_link} \n\nAuthors: {ms_author}, {author}\n\n{get_latest_error_log()}"

                            open_issues = repo.get_issues(state='open')
                            issue_exists = False
                            for issue in open_issues:
                                if issue.title == issue_title:
                                    issue_exists = True
                                    existing_issue = issue
                                    break

                            if issue_exists:
                                if not author_has_commented(existing_issue, author):
                                    issue_creation_date = existing_issue.created_at
                                    current_date = datetime.now(issue_creation_date.tzinfo)
                                    days_since_opened = (current_date - issue_creation_date).days

                                    comment_body = f"Reminder: @{author}, it's been {days_since_opened} days since the issue was opened. Please fix the doc as previously mentioned."
                                    existing_issue.create_comment(comment_body)
                            else:
                                try:
                                    repo.create_issue(title=issue_title, body=issue_body, assignees=[author, 'naman-msft'])
                                except Exception as e:
                                    print(f"Error creating issue with author {author}: {e}")
                                    repo.create_issue(title=issue_title, body=issue_body, assignees=['naman-msft'])

def find_region_value(markdown_text):
    match = re.search(r'REGION="?([^"\n]+)"?', markdown_text, re.IGNORECASE)
    if match:
        region = str(match.group(1))
        return region
    else:
        return ""

def update_base_metadata(directory, metadata):
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if os.path.isdir(path):
            # If it's a directory, process it recursively
            update_base_metadata(path, metadata)
        else:
            # If it's a file, check if it's a README file
            if '.md' in name.lower():
                # Process the README file
                with open(path, 'r') as f:
                    metadata_lines = []
                    collecting = False
                    for line in f:
                        if line.strip() == '---':
                            if collecting:
                                break
                            else:
                                collecting = True
                                continue
                        if collecting:
                            metadata_lines.append(line)
                    # Join the lines together into a single string
                    metadata_str = '\n'.join(metadata_lines).strip('---').strip('\n')

                    # Parse the metadata from the string
                    readme_metadata = yaml.safe_load(metadata_str)
                    readme_metadata = json.loads(json.dumps(readme_metadata, ensure_ascii=False))
                    # Get the key for this file
                    key = '/'.join(path.split('/')[1:])
                    # Find the item in metadata with this key
                    
                    if metadata:
                        for item in metadata:
                            if item['key'] == key:
                                break
                        else:
                            # If the key was not found, add a new item to metadata
                            item = {'status': 'active', 'key': key}
                            metadata.append(item)
                    else:
                        item = {'status': 'active', 'key': key}
                        metadata.append(item)
                    if item is not None and readme_metadata is not None:
                        # Update the item with the metadata from the README file
                        item['title'] = readme_metadata.get('title', item.get('title', ''))
                        item['description'] = readme_metadata.get('description', item.get('description', ''))
                        item['stackDetails'] = readme_metadata.get('stackDetails', item.get('stackDetails', ''))
                        item['sourceUrl'] = item.get('sourceUrl', "https://raw.githubusercontent.com/MicrosoftDocs/executable-docs/main/scenarios/"+key)
                        item['documentationUrl'] = item.get('documentationUrl', '')
                        item.setdefault('configurations', {})["region"] = find_region_value(f.read())

    return metadata

def update_metadata():
    # Load the base metadata.json file
    if os.path.isfile('scenarios/metadata.json'):
        with open('scenarios/metadata.json', 'r') as f:
            base_metadata = json.load(f)

        # Update the metadata with the README files in the scenarios directory
        metadata = update_base_metadata('scenarios', base_metadata)

        # Write the updated metadata.json file
        with open('scenarios/metadata.json', 'w') as f:
            json.dump(metadata, f, indent=4)

    else:
        with open('scenarios/metadata.json', 'w') as f:
            base_metadata = []

        # Update the metadata with the README files in the scenarios directory
        metadata = update_base_metadata('scenarios', base_metadata)

        # Write the updated metadata.json file
        with open('scenarios/metadata.json', 'w') as f:
            json.dump(metadata, f, indent=4)

if __name__ == "__main__":
    sync_markdown_files()
    update_metadata()
    install_ie()
    run_tests()

    # run this command in the CLI to close all open issues: gh issue list --state open --json number -q '.[].number' | xargs -I % gh issue close %

        
    

