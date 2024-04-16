import os
import github

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
g = github.Github(GITHUB_TOKEN)

def sync_markdown_files():
    query = "innovation-engine in:file language:markdown org:MicrosoftDocs -path:/localized/ -repo:MicrosoftDocs/executable-docs"
    result = g.search_code(query)
    for file in result:
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
                    with open(file_path, 'w') as f:
                        f.write(file_content)

if __name__ == "__main__":
    sync_markdown_files()