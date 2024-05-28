import os
import github
import shutil
import subprocess
import tempfile

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

def run_tests():
    success_count = 0
    failure_count = 0

    for root, dirs, files in os.walk('scenarios'):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                result = subprocess.run(['ie', 'test', file_path])

                if result.returncode == 0:
                    success_count += 1
                else:
                    failure_count += 1

    print(f'Successfully tested docs: {success_count}')
    print(f'Failed docs: {failure_count}')
if __name__ == "__main__":
    # sync_markdown_files()
    install_ie()
    run_tests()