import os
import github
import shutil
import subprocess
import tempfile
import re
import json
import yaml
from datetime import datetime
import time

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
g = github.Github(GITHUB_TOKEN)

def find_region_value(markdown_text):
    match = re.search(r'REGION="?([^"\n]+)"?', markdown_text, re.IGNORECASE)
    if match:
        region = str(match.group(1))
        return region
    else:
        return ""

def update_metadata(file_path, localize=False):
    try:
        if localize == False:
            # Load the base metadata.json file
            if os.path.isfile('scenarios/metadata.json'):
                with open('scenarios/metadata.json', 'r') as f:
                    base_metadata = json.load(f)

                with open(file_path, 'r') as f:
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
                    key = '/'.join(file_path.split('/')[1:])

                    # Find the item in metadata with this key
                    item = None
                    if base_metadata:
                        for _item in base_metadata:
                            if _item['key'] == key:
                                item = _item
                                break
                        if not item:
                            item = {'status': 'active', 'key': key}
                            base_metadata.append(item)
                    else:
                        item = {'status': 'active', 'key': key}
                        base_metadata.append(item)

                    if item is not None and readme_metadata is not None:
                        item['title'] = readme_metadata.get('title', item.get('title', ''))
                        item['description'] = readme_metadata.get('description', item.get('description', ''))
                        item['stackDetails'] = readme_metadata.get('stackDetails', item.get('stackDetails', ''))
                        item['sourceUrl'] = "https://raw.githubusercontent.com/MicrosoftDocs/executable-docs/main/scenarios/"+key
                        item['documentationUrl'] = readme_metadata.get('documentationUrl', item.get('documentationUrl', ''))
                        item['configurations'] = item.get('configurations', {})
                        item['configurations']["region"] = find_region_value(f.read())

        elif localize == True:
            locale = file_path.split('/')[1] 
            # Load the base metadata.json file
            if os.path.isfile(f'localized/{locale}/scenarios/metadata.json'):
                with open(f'localized/{locale}/scenarios/metadata.json', 'r') as f:
                    base_metadata = json.load(f)

                # Update the metadata with the README files in the scenarios directory
                with open(file_path, 'r') as f:
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
                    
                    key = '/'.join(file_path.split('/')[3:])      

                    # Find the item in metadata with this key
                    item = None
                    if base_metadata:
                        for _item in base_metadata:
                            if _item['key'] == key:
                                item = _item
                                break
                        if not item:
                            item = {'status': 'active', 'key': key}
                            base_metadata.append(item)
                    else:
                        item = {'status': 'active', 'key': key}
                        base_metadata.append(item)

                    if item is not None and readme_metadata is not None:
                        item['title'] = readme_metadata.get('title', item.get('title', ''))
                        item['description'] = readme_metadata.get('description', item.get('description', ''))
                        item['stackDetails'] = readme_metadata.get('stackDetails', item.get('stackDetails', ''))
                        item['sourceUrl'] = f"https://raw.githubusercontent.com/MicrosoftDocs/executable-docs/main/localized/{locale}/scenarios/{key}"
                        item['documentationUrl'] = readme_metadata.get('documentationUrl', item.get('documentationUrl'.replace('learn.microsoft.com/azure', f'learn.microsoft.com/{locale}/azure'), ''))
                        item['configurations'] = item.get('configurations', {})
                        item['configurations']["region"] = find_region_value(f.read())

    except Exception as e:
        print(f"Error updating metadata: {e}")

    print(base_metadata)
    return base_metadata   

def delete_branch(repo, branch_name):
    try:
        ref = repo.get_git_ref(f"heads/{branch_name}")
        
        # Check if there is an open PR for the branch
        pulls = repo.get_pulls(state='open', head=f"{repo.owner.login}:{branch_name}")
        if pulls.totalCount > 0:
            for pr in pulls:
                pr.edit(state='closed')
                print(f"Closed PR #{pr.number} for branch '{branch_name}'")
        
        # Delete the branch
        ref.delete()
        print(f"Deleted branch '{branch_name}'")
        
    except Exception as e:
        print(f"Branch '{branch_name}' does not exist")

def sync_markdown_files():
    query = "innovation-engine in:file language:markdown org:MicrosoftDocs -path:/localized/ -repo:MicrosoftDocs/executable-docs" 
    result = g.search_code(query)
    for file in result:
        if '-pr' not in file.repository.name:
            file_content = file.repository.get_contents(file.path).decoded_content.decode('utf-8')
            if '---' in file_content:
                metadata = file_content.split('---')[1]
                if 'ms.custom:' in metadata:
                    custom_values = metadata.split('ms.custom:')[1].split(',')
                    custom_values = [value.strip() for value in custom_values]
                    if 'innovation-engine' in custom_values:
                        # Construct the directory path for storing the file in the 'scenarios' directory
                        source_file_changed = True
                        source_file_path = os.path.join('scenarios', file.repository.name, os.path.dirname(file.path), os.path.basename(file.path))
                        print(f"Processing file: {source_file_path}")

                        # Get the directory path of the file
                        all_files = g.search_code(f'repo:{file.repository.full_name} path:{os.path.dirname(file.path)}')
                        relevant_files = [f for f in all_files if not f.path.endswith('.md')]
                        if file not in relevant_files:
                            relevant_files.append(file)

                        # Create a new branch and commit the file
                        repo = g.get_repo("MicrosoftDocs/executable-docs")
                        source_branch = repo.get_branch("main")
                        new_branch_name = f"test_{source_file_path.replace(os.sep, '_')}"
                        
                        try:
                            delete_branch(repo, new_branch_name)
                        except:
                            pass
                        
                        # Checkout to main before creating a new branch
                        try:
                            # subprocess.check_call(["git", "checkout", "main"])
                            subprocess.check_call(["git", "fetch", "origin"])
                            subprocess.check_call(["git", "checkout", "main"])
                            subprocess.check_call(["git", "pull", "origin", "main"])
                        except subprocess.CalledProcessError as e:
                            print(f"Error checking out branch main")
                            continue

                        # Check if the branch already exists
                        try:
                            repo.get_branch(new_branch_name)
                            branch_exists = True
                        except:
                            branch_exists = False
                        
                        if not branch_exists:
                            repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=source_branch.commit.sha)

                        # Checkout the new branch
                        try:
                            subprocess.check_call(["git", "checkout", new_branch_name])
                        except subprocess.CalledProcessError as e:
                            print(f"Error checking out branch {new_branch_name}")
                            continue

                        for relevant_file in relevant_files:
                            relevant_file_content = relevant_file.repository.get_contents(relevant_file.path).decoded_content.decode('utf-8')
                            
                            dir_path = os.path.join('scenarios', relevant_file.repository.name, os.path.dirname(relevant_file.path))
                            os.makedirs(dir_path, exist_ok=True)
                            file_path = os.path.join(dir_path, os.path.basename(relevant_file.path))

                            # Check if file_path already exists in the repo and if the content is different
                            try:
                                existing_file = repo.get_contents(file_path, ref="main")
                                existing_content = existing_file.decoded_content.decode('utf-8')
                                if existing_content == relevant_file_content:
                                    if existing_file.path == source_file_path:
                                        source_file_changed = False
                                    print(f"File {file_path} already exists with the same content.")
                                    continue
                            except:
                                # File does not exist, proceed with creating a branch and committing the file
                                pass
                            
                            print(f"Processing relevant file: {relevant_file.path}")
                            print(f"Creating or relevant file at: {file_path}")

                            # Create or update the file in the new branch
                            try:
                                repo.create_file(file_path, f"Add {file_path}", relevant_file_content, branch=new_branch_name)
                                print(f"Created file: {file_path}")
                            except:
                                contents = repo.get_contents(file_path, ref=new_branch_name)
                                repo.update_file(contents.path, f"Update {file_path}", relevant_file_content, contents.sha, branch=new_branch_name)
                                print(f"Updated file: {file_path}")
                        
                        if source_file_changed:
                            # Create or update the base metadata.json file
                            branch_metadata = update_metadata(source_file_path, localize=False)
                            
                            try:
                                repo.create_file('scenarios/metadata.json', f"Add metadata.json file", json.dumps(branch_metadata, indent=4), branch=new_branch_name)
                                print("Created metadata.json")
                            except:
                                metadata_contents = repo.get_contents('scenarios/metadata.json', ref=new_branch_name)
                                repo.update_file(metadata_contents.path, f"Update metadata for all files", json.dumps(branch_metadata, indent=4), metadata_contents.sha, branch=new_branch_name)
                                print("Updated metadata.json")
                            
                            time.sleep(2)
                            # Create or update the localized metadata.json files altogether
                            try:
                                for locale in sorted(os.listdir('localized')):
                                    locale_source_file_path = f'localized/{locale}/{source_file_path}'
                                    locale_metadata = update_metadata(locale_source_file_path, localize=True)
                                    repo.create_file(f'localized/{locale}/scenarios/metadata.json', f"Add metadata.json file for {locale}", json.dumps(locale_metadata, indent=4), branch=new_branch_name)
                                    print("created localized metadata")

                            except:
                                for locale in sorted(os.listdir('localized')):
                                    locale_source_file_path = f'localized/{locale}/{source_file_path}'
                                    locale_metadata = update_metadata(locale_source_file_path, localize=True)
                                    locale_metadata_path = repo.get_contents(f'localized/{locale}/scenarios/metadata.json', ref=new_branch_name)
                                    repo.update_file(locale_metadata_path.path, f"Updated localized metadata for {locale}", json.dumps(locale_metadata, indent=4), locale_metadata_path.sha, branch=new_branch_name)
                                    print("updated localized metadata")

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

                else:
                    key = '/'.join(file_path.split('/')[1:])
                    if os.path.isfile('scenarios/metadata.json'):
                        with open('scenarios/metadata.json', 'r') as f:
                            metadata = json.load(f)

                        # Find the item in metadata with this key
                        if metadata:
                            for item in metadata:
                                if item['key'] == key:
                                    item['status'] = 'active'
                            
                        with open('scenarios/metadata.json', 'w') as f:
                            json.dump(metadata, f, indent=4)

if __name__ == "__main__":
    sync_markdown_files()
    # install_ie()
    # run_tests()

    # run this command in the CLI to close all open issues: gh issue list --state open --json number -q '.[].number' | xargs -I % gh issue close %