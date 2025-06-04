# WELCOME TO ADA - AI DOCUMENTATION ASSISTANT

import os
import sys
import subprocess
import shutil
from importlib.metadata import version, PackageNotFoundError
import csv
import time
from datetime import datetime
from openai import AzureOpenAI
from collections import defaultdict
import re
import json
import yaml 
import requests
from bs4 import BeautifulSoup 
import difflib

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

deployment_name = 'gpt-4.1'

REQUIRED_PACKAGES = [
    'openai',
    'azure-identity',
    'requests',
]

for package in REQUIRED_PACKAGES:
    try:
        # Attempt to get the package version
        version(package)
    except PackageNotFoundError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

system_prompt = """Exec Docs is a vehicle that transforms standard markdown into interactive, executable learning content, allowing code commands within the document to be run step-by-step or “one-click”. This is powered by the Innovation Engine, an open-source CLI tool that powers the execution and testing of these markdown scripts and can integrate with automated CI/CD pipelines. You are an Exec Doc writing expert. You will either write a new exec doc from scratch if no doc is attached or update an existing one if it is attached. You must adhere to the following rules while presenting your output:

## IF YOU ARE UPDATING AN EXISTING DOC

Ensure that every piece of information outside of code blocks – such as metadata, descriptions, comments, instructions, and any other narrative content – is preserved. The final output should be a comprehensive document that retains all correct code blocks as well as the rich contextual and descriptive details from the source doc, creating the best of both worlds. 

### Prerequisites

Check if all prerequisites below are met before writing the Exec Doc. ***If any of the below prerequisites are not met, then either add them to the Exec Doc in progress or find another valid doc that can fulfill them. Do not move to the next step until then***

1. Ensure your Exec Doc is a markdown file. 

    >**Note:** If you are converting an existing Azure Doc to an Exec Doc, you can either find it in your fork or copy the raw markdown content of the Azure Doc into a new markdown file in your local repo (this can be found by clicking "Raw" in the GitHub view of the Azure Doc). 

2. Ensure your Exec Doc is written with the LF line break type.

    **Example:** 

    ![LF VSCode](https://github.com/MicrosoftDocs/executable-docs/assets/146123940/3501cd38-2aa9-4e98-a782-c44ae278fc21)

    >**Note:** The button will appear according to the IDE you are using. For the VS Code IDE, you can check this by clicking on the LF/CLRF button at the bottom right corner of the screen.

3. Ensure all files that your Exec Doc references live under the same parent folder as your Exec Doc

    **Example:** 

    If your Exec Doc ***my-exec-doc.md*** references a script file ***my-script.yaml*** within, the script file should be in the same folder as the Exec Doc. 

    ```bash 
    ├── master-folder
    │   └── parent-folder
    │       ├── my-exec-doc.md 
    │       └── my-script.yaml 
    ``` 

4. Code blocks are used to provide examples, commands, or other code snippets in Exec Docs. They are distinguished by a triple backtick (```) at the start and end of the block. 

    Ensure that the Exec Doc contains at least 1 code block and every input code block's type in the Exec Doc is taken from this list: 

    - bash 
    - azurecli
    - azure-cli-interactive 
    - azurecli-interactive  

    **Example:** 

    ```bash 
    az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION 
    ``` 

    >**Note:** This rule does not apply to output code blocks, which are used to display the results of commands, scripts, or other operations. These blocks help in illustrating what the expected output should look like. They include, but are not limited to, the following types: _output, json, yaml, console, text, and log._

    >**Note:** While Innovation Engine can _parse_ a code block of any type, given its current features, it can only _execute_ code blocks of the types above. So, it is important to ensure that the code blocks in your Exec Doc are of the types above. 

5. Headings are used to organize content in a document. The number of hashes indicates the level of the heading. For example, a single hash (#) denotes an h1 heading, two hashes (##) denote an h2 heading, and so on. Innovation Engine uses headings to structure the content of an Exec Doc and to provide a clear outline of the document's contents. 

    Ensure there is at least one h1 heading in the Exec Doc, denoted by a single hash (#) at the start of the line. 

    **Example:** 

    ```markdown 
    # Quickstart: Deploy an Azure Kubernetes Service (AKS) cluster using Azure CLI 
    ``` 

### Writing Requirements

6. Ensure that the Exec Doc does not include any commands or descriptions related to logging into Azure (e.g., `az login`) or setting the subscription ID. The user is expected to have already logged in to Azure and set their subscription beforehand. Do not include these commands or any descriptions about them in the Exec Doc.

7. Ensure that the Exec Doc does not require any user interaction during its execution. The document should not include any commands or scripts that prompt the user for input or expect interaction with the terminal. All inputs must be predefined and handled automatically within the script.

8. IMPORTANT: NEVER change the language type of code blocks. If a code block is specified as 'shell', do not change it to 'bash' or any other type. Preserve the exact code block language type from the original document. The language type specified after the opening triple backticks must remain exactly as it was in the source document.

8. Appropriately add metadata at the start of the Exec Doc. Here are some mandatory fields:

    - title = the title of the Exec Doc
    - description = the description of the Exec Doc
    - ms.topic = what kind of a doc it is e.g. article, blog, etc. 
    - ms.date = the current date in the format MM/DD/YYYY 
    - author = author's GitHub username 
    - ms.author = author's username (e.g. Microsoft Alias)
    - **ms.custom = comma-separated list of tags to identify the Exec Doc (innovation-engine is the one tag that is mandatory in this list)**
        
    **Example:** 

    ```yaml 
    ---
    title: 'Quickstart: Deploy an Azure Kubernetes Service (AKS) cluster using Azure CLI' 
    description: Learn how to quickly deploy a Kubernetes cluster and deploy an application in Azure Kubernetes Service (AKS) using Azure CLI. 
    ms.topic: quickstart 
    ms.date: 11/11/2021 
    author: namanparikh 
    ms.author: namanaprikh 
    ms.custom: devx-track-azurecli, mode-api, innovation-engine, linux-related-content 
    ---
    ```

9. Ensure the environment variable names are not placeholders i.e. <> but have a certain generic, useful name. For the location/region parameter, default to "eastus2" or "canadacentral" or "centralindia". Additionally, appropriately add descriptions below every section explaining what is happening in that section in crisp but necessary detail so that the user can learn as they go.

10. Don't start and end your answer with ``` backticks!!! Don't add backticks to the metadata at the top!!!. 

11. Ensure that any info, literally any info whether it is a comment, tag, description, etc., which is not within a code block remains unchanged. Preserve ALL details of the doc.

12. Environment variables are dynamic values that store configuration settings, system paths, and other information that can be accessed throughout a doc. By using environment variables, you can separate configuration details from the code, making it easier to manage and deploy applications in an environment like Exec Docs. 

    Declare environment variables _as they are being used_ in the Exec Doc using the export command. This is a best practice to ensure that the variables are accessible throughout the doc. 

    ### Example Exec Doc 1 - Environment variables declared at the _top_ of an Exec Doc, not declared as used
    
    **Environment Variables Section**

    We are at the start of the Exec Doc and are declaring environment variables that will be used throughout the doc. 

    ```bash
    export REGION="canadacentral"
    ```
    
    **Test Section**

    We are now in the middle of the Exec Doc and we will create an AKS cluster.

    ```bash
    az aks create --resource-group MyResourceGroup --name MyAKSCluster --location $REGION
    ```
    
    ### Example Exec Doc 2 - Environment Variables declared as used** 
    
    **Test Section**

    We are in the middle of the Exec Doc and we will create an AKS cluster.

    ```bash  
    export REGION="candacentral"
    export RESOURCE_GROUP_NAME="MyResourceGroup"
    export AKS_CLUSTER_NAME="MyAKSCluster"
    az aks create --resource-group $RESOURCE_GROUP_NAME --name $AKS_CLUSTER_NAME --location $REGION
    ``` 
    
    >**Note:** If you are converting an existing Azure Doc to an Exec Doc and the Azure Doc does not environment variables at all, it is an Exec Doc writing best practice to add them. Additionally, if the Azure Doc has environment variables but they are not declared as they are being used, it is recommended to update them to follow this best practice. 

    >**Note:** Don't have any spaces around the equal sign when declaring environment variables.

13. A major component of Exec Docs is automated infrastructure deployment on the cloud. While testing the doc, if you do not update relevant environment variable names, the doc will fail when run/executed more than once as the resource group or other resources will already exist from the previous runs. 

    Add a random suffix at the end of _relevant_ environment variable(s). The example below shows how this would work when you are creating a resource group.

    **Example:** 

    ```bash  
    export RANDOM_SUFFIX=$(head -c 3 /dev/urandom | xxd -p)
    export REGION="eastus"
    az group create --name "MyResourceGroup$RANDOM_SUFFIX" --location $REGION
    ```

    >**Note:** Add a random suffix to relevant variables that are likely to be unique for each deployment, such as resource group names, VM names, and other resources that need to be uniquely identifiable. However, do not add a random suffix to variables that are constant or environment-specific, such as region, username, or configuration settings that do not change between deployments. 
    
    >**Note:** You can generate your own random suffix or use the one provided in the example above. The `head -c 3 /dev/urandom | xxd -p` command generates a random 3-character hexadecimal string. This string is then appended to the resource group name to ensure that the resource group name is unique for each deployment.

14. In Exec Docs, result blocks are distinguished by a custom expected_similarity comment tag followed by a code block. These result blocks indicate to Innovation Engine what the minimum degree of similarity should be between the actual and the expected output of a code block (one which returns something in the terminal that is relevant to benchmark against). Learn More: [Result Blocks](https://github.com/Azure/InnovationEngine/blob/main/README.md#result-blocks). 

    Add result block(s) below code block(s) that you would want Innovation Engine to verify i.e. code block(s) which produce an output in the terminal that is relevant to benchmark against. Follow these steps when adding a result block below a code block for the first time:

    - Check if the code block does not already have a result block below it. If it does, ensure the result block is formatted correctly, as shown in the example below, and move to the next code block.
    - [Open Azure Cloudshell](https://ms.portal.azure.com/#cloudshell/) 
    - **[Optional]**: Set your active subscription to the one you are using to test Exec Docs. Ideally, this sub should have permissions to run commands in your tested Exec Docs. Run the following command: 

        ```bash
        az account set --subscription "<subscription name or id>"
        ``` 
    - Run the command in the code block in cloudshell. If it returns an output that you would want Innovation Engine to verify, copy the output from the terminal and paste it in a new code block below the original code block. The way a result code block should be formatted has been shown below, in this case for the command [az group create --name "MyResourceGroup123" --location eastus](http://_vscodecontentref_/1).

        **Example:**
        ```markdown            
            Results: 

            <!-- expected_similarity=0.3 --> 

            ```output 
            {{
                "id": "/subscriptions/abcabc-defdef-ghighi-jkljkl/resourceGroups/MyResourceGroup123",
                "location": "eastus",
                "managedBy": null,
                "name": "MyResourceGroup123",
                "properties": {{
                    "provisioningState": "Succeeded"
                }},
                "tags": null,
                "type": "Microsoft.Resources/resourceGroups"
            }}
            ```
    - If you run into an error while executing a code block or the code block is running in an infinite loop, update the Exec Doc based on the error stack trace, restart/clear Cloudshell, and rerun the command block(s) from the start until you reach that command block. This is done to override any potential issues that may have occurred during the initial run. More guidance is given in the [FAQ section](#frequently-asked-questions-faqs) below.
    
    >**Note:** The expected similarity value is a percentage of similarity between 0 and 1 which specifies how closely the true output needs to match the template output given in the results block - 0 being no similarity, 1 being an exact match. If you are uncertain about the value, it is recommended to set the expected similarity to 0.3 i.e. 30% expected similarity to account for small variations. Once you have run the command multiple times and are confident that the output is consistent, you can adjust the expected similarity value accordingly.

    >**Note:** If you are executing a command in Cloudshell which references a yaml/json file, you would need to create the yaml/json file in Cloudshell and then run the command. This is because Cloudshell does not support the execution of commands that reference local files. You can add the file via the cat command or by creating the file in the Cloudshell editor. 

    >**Note:** Result blocks are not required but recommended for commands that return some output in the terminal. They help Innovation Engine verify the output of a command and act as checkpoints to ensure that the doc is moving in the right direction.

15. Redacting PII from the output helps protect sensitive information from being inadvertently shared or exposed. This is crucial for maintaining privacy, complying with data protection regulations, and furthering the company's security posture. 

    Ensure result block(s) have all the PII (Personally Identifiable Information) stricken out from them and replaced with x’s. 

    **Example:** 

    ```markdown
        Results: 

        <!-- expected_similarity=0.3 --> 

        ```output 
        {{ 
            "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxx",
                "location": "eastus",
                "managedBy": null,
                "name": "MyResourceGroupxxx",
                "properties": {{
                    "provisioningState": "Succeeded"
                }},
                "tags": null,
                "type": "Microsoft.Resources/resourceGroups" 
        }} 
        ```
    ```

    >**Note:** The number of x's used to redact PII need not be the same as the number of characters in the original PII. Furthermore, it is recommended not to redact the key names in the output, only the values containing the PII (which are usually strings).
    
    >**Note:** Here are some examples of PII in result blocks: Unique identifiers for resources, Email Addresses, Phone Numbers, IP Addresses, Credit Card Numbers, Social Security Numbers (SSNs), Usernames, Resource Names, Subscription IDs, Resource Group Names, Tenant IDs, Service Principal Names, Client IDs, Secrets and Keys.

16. If you are converting an existing Azure Doc to an Exec Doc and if the existing doc contains a "Delete Resources" (or equivalent section) comprising resource/other deletion command(s), remove the code blocks in that section or remove that section entirely 

    >**Note:** We remove commands from this section ***only*** in Exec Docs. This is because Innovation Engine executes all relevant command(s) that it encounters, inlcuding deleting the resources. That would be counterproductive to automated deployment of cloud infrastructure

17. If the original document lists a prerequisite resource (such as an AKS cluster, VM, storage account, etc.), you MUST NOT add any new commands to create that resource in the Exec Doc.

    - **Example:** If the doc says "This article assumes you have an existing AKS cluster," do NOT add `az aks create` or any equivalent cluster creation commands. Only include steps for interacting with or managing the existing resource.
    - This rule applies to any resource type, not just AKS. Always respect explicit prerequisites and never override them by adding creation steps for that resource.
    - If the prerequisite is stated in any form (e.g., "Before you begin, create a resource group"), treat that resource as pre-existing and do not add creation commands for it.
    - If you are unsure whether a resource should be created, always preserve the prerequisite as stated and avoid introducing creation commands for that resource.


## WRITE AND ONLY GIVE THE EXEC DOC USING THE ABOVE RULES FOR THE FOLLOWING WORKLOAD: """

# Add this after imports
def print_header(text, style=None):
    """Print a header with customized boundary symbols based on content importance.
    
    Args:
        text: The header text to display
        style: Symbol style or None for automatic selection
    """
    # Auto-select symbol based on text content if style is None
    # if style is None:
    if "WELCOME" in text or "TITLE" in text.upper():
        style = "="  # Most important - main titles
    elif "ERROR" in text.upper() or "FAILED" in text.upper():
        style = "!"  # Errors and failures
    elif "SUCCESS" in text.upper() or "COMPLETED" in text.upper():
        style = "+"  # Success messages
    elif "MENU" in text.upper() or "OPTIONS" in text.upper():
        style = "-"  # Menu sections
    elif "STEPS" in text.upper() or "PROCEDURE" in text.upper():
        style = "~"  # Procedural sections
    elif "NOTE" in text.upper() or "TIP" in text.upper():
        style = "*"  # Notes and tips
    else:
        style = "·"  # Default for other sections
    
    width = min(os.get_terminal_size().columns, 70)
    border = style * width
    print(f"\n{border}")
    
    # Center the text if it's shorter than the width
    if len(text) < width - 4:
        padding = (width - len(text)) // 2
        print(" " * padding + text)
    else:
        # If text is too long, wrap it
        import textwrap
        for line in textwrap.wrap(text, width=width-4):
            print(f"  {line}")
    
    print(f"{border}\n")
    
def print_message(text, prefix="", indent=0, color=None):
    """Print formatted message with optional prefix."""
    indent_str = " " * indent
    for line in text.split("\n"):
        print(f"{indent_str}{prefix}{line}")

def install_innovation_engine():
    if shutil.which("ie") is not None:
        print_message("\nInnovation Engine is already installed.")
        return
    print_message("Installing Innovation Engine...", prefix="🔧 ")
    subprocess.check_call(
        "curl -Lks https://raw.githubusercontent.com/Azure/InnovationEngine/v0.2.3/scripts/install_from_release.sh | /bin/bash -s -- v0.2.3",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print_message("\nInnovation Engine installed successfully.\n")

def get_last_error_log():
    log_file = "ie.log"
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            lines = f.readlines()
            error_index = None
            for i in range(len(lines) - 1, -1, -1):
                if "level=error" in lines[i]:
                    error_index = i
                    break
            if error_index is not None:
                return "".join(lines[error_index:])
    return "No error log found."

def generate_script_description(script_path, context=""):
    """Generate descriptions around a shell script without modifying the code."""
    if not os.path.isfile(script_path):
        print_message(f"\nError: The file {script_path} does not exist.")
        return None

    try:
        with open(script_path, "r") as f:
            script_content = f.read()
    except Exception as e:
        print_message(f"\nError reading script: {e}")
        return None

    # Create output filename
    script_name = os.path.splitext(os.path.basename(script_path))[0]
    output_file = f"{script_name}_documented.md"

    print_message("\nGenerating documentation for shell script...")
    
    # Prepare prompt for the LLM
    script_prompt = f"""Create an Exec Doc that explains this shell script in detail.
    DO NOT CHANGE ANY CODE in the script. Instead:
    1. Add clear descriptions before and after each functional block
    2. Explain what each section does
    3. Format as a proper markdown document with appropriate headings and structure
    4. Include all the necessary metadata in the front matter
    
    Script context provided by user: {context}
    
    Here is the script content:
    ```
    {script_content}
    ```
    """

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": script_prompt}
        ]
    )
    
    doc_content = response.choices[0].message.content
    
    # Save the generated documentation
    try:
        with open(output_file, "w") as f:
            f.write(doc_content)
        print_message(f"\nScript documentation saved to: {output_file}")
        return output_file
    except Exception as e:
        print_message(f"\nError saving documentation: {e}")
        return None

def redact_pii_from_doc(doc_path):
    """Redact PII from result blocks in an Exec Doc."""
    if not os.path.isfile(doc_path):
        print_message(f"\nError: The file {doc_path} does not exist.")
        return None

    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
    except Exception as e:
        print_message(f"\nError reading document: {e}")
        return None

    # Create output filename
    doc_name = os.path.splitext(os.path.basename(doc_path))[0]
    output_file = f"{doc_name}_redacted.md"

    print_message("\nRedacting PII from document...")
    
    # Use the LLM to identify and redact PII
    redaction_prompt = """Redacting PII from the output helps protect sensitive information from being inadvertently shared or exposed. This is crucial for maintaining privacy, complying with data protection regulations, and furthering the company's security posture. 

    Ensure result block(s) have all the PII (Personally Identifiable Information) stricken out from them and replaced with x’s. 

    **Example:** 

    ```markdown
        Results: 

        <!-- expected_similarity=0.3 --> 

        ```output 
        {{ 
            "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxx",
                "location": "eastus",
                "managedBy": null,
                "name": "MyResourceGroupxxx",
                "properties": {{
                    "provisioningState": "Succeeded"
                }},
                "tags": null,
                "type": "Microsoft.Resources/resourceGroups" 
        }} 
        ```
    ```

    >**Note:** The number of x's used to redact PII need not be the same as the number of characters in the original PII. Furthermore, it is recommended not to redact the key names in the output, only the values containing the PII (which are usually strings).
    
    >**Note:** Here are some examples of PII in result blocks: Unique identifiers for resources, Email Addresses, Phone Numbers, IP Addresses, Credit Card Numbers, Social Security Numbers (SSNs), Usernames, Resource Names, Subscription IDs, Resource Group Names, Tenant IDs, Service Principal Names, Client IDs, Secrets and Keys.
    
    Document content:
    """

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are an AI specialized in PII redaction. Either redact the PII or return the document as is - nothing els is acceptable."},
            {"role": "user", "content": redaction_prompt + "\n\n" + doc_content}
        ]
    )
    
    redacted_content = response.choices[0].message.content
    
    # Save the redacted document
    try:
        with open(output_file, "w") as f:
            f.write(redacted_content)
        print_message(f"\nRedacted document saved to: {output_file}")
        return output_file
    except Exception as e:
        print_message(f"\nError saving redacted document: {e}")
        return None

def generate_dependency_files(doc_path):
    """Extract and generate dependency files referenced in an Exec Doc."""
    if not os.path.isfile(doc_path):
        print_message(f"\nError: The file {doc_path} does not exist.")
        return False, []

    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
    except Exception as e:
        print_message(f"\nError reading document: {e}")
        return False, []

    # Directory where the doc is located
    doc_dir = os.path.dirname(doc_path) or "."
    
    print_message("\nAnalyzing document for dependencies...")
    
    # First, detect file creation patterns in the document to avoid conflicts
    file_creation_patterns = [
        # Cat heredoc to a file
        (r'cat\s*<<\s*[\'"]?(EOF|END)[\'"]?\s*>\s*([^\s;]+)', 1),
        # Echo content to a file
        (r'echo\s+.*?>\s*([^\s;]+)', 0),
        # Tee command
        (r'tee\s+([^\s;]+)', 0)
    ]
    
    doc_created_files = []
    for pattern, group_idx in file_creation_patterns:
        matches = re.findall(pattern, doc_content, re.DOTALL)
        for match in matches:
            if isinstance(match, tuple):
                filename = match[group_idx]
            else:
                filename = match
            doc_created_files.append(filename)
    
    if doc_created_files:
        print_message("\nDetected file creation commands in document:")
        for file in doc_created_files:
            print_message(f"  - {file}")
    
    # Enhanced prompt for better dependency file identification
    dependency_prompt = """Analyze this Exec Doc and identify ANY files that the user is instructed to create.
    
    Look specifically for:
    1. Files where the doc says "Create a file named X" or similar instructions
    2. Files that are referenced in commands (e.g., kubectl apply -f filename.yaml)
    3. YAML files (configuration, templates, manifests)
    4. JSON files (configuration, templates, API payloads)
    5. Shell scripts (.sh files)
    6. Terraform files (.tf or .tfvars)
    7. Any other files where content is provided and meant to be saved separately

    IMPORTANT: Include files even if their full content is provided in the document!
    If the doc instructs the user to create a file and provides its content, this IS a dependency file.
    Look for patterns like "create the following file" or "save this content to filename.xyz".

    For each file you identify:
    1. Extract the exact filename with its extension
    2. Use the exact content provided in the document
    3. Format your response as a JSON list
    """

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are an AI specialized in extracting and generating dependency files."},
            {"role": "user", "content": dependency_prompt + "\n\n" + doc_content}
        ]
    )
    
    created_dep_files = []
    
    try:
        # Extract the JSON part from the response with improved robustness
        response_text = response.choices[0].message.content
        
        # Find JSON content between triple backticks with more flexible pattern matching
        json_match = re.search(r'```(?:json)?(.+?)```', response_text, re.DOTALL)
        if json_match:
            # Clean the extracted JSON content
            json_content = json_match.group(1).strip()
            try:
                dependency_list = json.loads(json_content)
            except json.JSONDecodeError:
                # Try removing any non-JSON text at the beginning or end
                json_content = re.search(r'(\[.+?\])', json_content, re.DOTALL)
                if json_content:
                    dependency_list = json.loads(json_content.group(1))
                else:
                    raise ValueError("Could not extract valid JSON from response")
        else:
            # Try to parse the entire response as JSON
            try:
                dependency_list = json.loads(response_text)
            except json.JSONDecodeError:
                # Last resort: look for anything that looks like a JSON array
                array_match = re.search(r'\[(.*?)\]', response_text.replace('\n', ''), re.DOTALL)
                if array_match:
                    try:
                        dependency_list = json.loads('[' + array_match.group(1) + ']')
                    except:
                        raise ValueError("Could not extract valid JSON from response")
                else:
                    raise ValueError("Response did not contain valid JSON")
        
        if not dependency_list:
            print_message("\nNo dependency files identified.")
            return True, []
        
        # Filter out dependency files that have inline creation commands in the document
        filtered_deps = []
        for dep in dependency_list:
            filename = dep.get("filename")
            if not filename:
                continue
                
            if filename in doc_created_files:
                print_message(f"\nWARNING: File '{filename}' is both created in document and identified as a dependency.")
                print_message(f"  - Skipping dependency management for this file to avoid conflicts.")
                continue
            
            filtered_deps.append(dep)
        
        # Create each dependency file with type-specific handling
        created_files = []
        for dep in filtered_deps:
            filename = dep.get("filename")
            content = dep.get("content")
            file_type = dep.get("type", "").lower()
            
            if not filename or not content:
                continue
                
            file_path = os.path.join(doc_dir, filename)
            
            # Check if file already exists
            if os.path.exists(file_path):
                print_message(f"\nFile already exists: {filename} - Skipping")
                # Load content from existing file
                try:
                    with open(file_path, "r") as f:
                        existing_content = f.read()
                    created_dep_files.append({
                        "filename": filename,
                        "path": file_path,
                        "type": file_type,
                        "content": existing_content  # Include content
                    })
                except Exception as e:
                    print_message(f"\nWarning: Could not read content from {filename}: {e}")
                    created_dep_files.append({
                        "filename": filename,
                        "path": file_path,
                        "type": file_type
                    })
                continue
                        
            # Validate and format content based on file type
            try:
                if filename.endswith('.json') or file_type == 'json':
                    # Validate JSON
                    try:
                        parsed = json.loads(content)
                        content = json.dumps(parsed, indent=2)  # Pretty-print_message JSON
                    except json.JSONDecodeError:
                        print_message(f"\nWarning: Content for {filename} is not valid JSON. Saving as plain text.")
                
                elif filename.endswith('.yaml') or filename.endswith('.yml') or file_type == 'yaml':
                    # Validate YAML
                    try:
                        parsed = yaml.safe_load(content)
                        content = yaml.dump(parsed, default_flow_style=False)  # Pretty-print_message YAML
                    except yaml.YAMLError:
                        print_message(f"\nWarning: Content for {filename} is not valid YAML. Saving as plain text.")
                
                elif filename.endswith('.tf') or filename.endswith('.tfvars') or file_type == 'terraform':
                    # Just store terraform files as-is
                    pass
                
                elif filename.endswith('.sh') or file_type == 'shell':
                    # Ensure shell scripts are executable
                    is_executable = True
                
                # Write the file
                with open(file_path, "w") as f:
                    f.write(content)
                
                # Make shell scripts executable if needed
                if (filename.endswith('.sh') or file_type == 'shell') and 'is_executable' in locals() and is_executable:
                    os.chmod(file_path, os.stat(file_path).st_mode | 0o111)  # Add executable bit
                
                created_files.append(filename)
                created_dep_files.append({
                    "filename": filename,
                    "path": file_path,
                    "type": file_type,
                    "content": content
                })
            except Exception as e:
                print_message(f"\nError creating {filename}: {e}")
        
        if created_files:
            print_message(f"\nCreated {len(created_files)} dependency files: {', '.join(created_files)}")
        else:
            print_message("\nNo new dependency files were created.")
        
        return True, created_dep_files
    except Exception as e:
        print_message(f"\nError generating dependency files: {e}")
        print_message("\nResponse from model was not valid JSON. Raw response:")
        return False, []

# Add this function after generate_dependency_files function (approximately line 609)

def transform_document_for_dependencies(doc_path, dependency_files):
    """Remove file creation commands from document when using dependency files."""
    if not dependency_files:
        return False
    
    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
            
        original_content = doc_content
        modified = False
        
        for dep_file in dependency_files:
            filename = dep_file["filename"]
            
            # Pattern to match cat/EOF blocks for file creation
            cat_pattern = re.compile(
                r'```(?:bash|azurecli|azure-cli-interactive|azurecli-interactive)\s*\n'
                r'(.*?cat\s*<<\s*[\'"]?(EOF|END)[\'"]?\s*>\s*' + re.escape(filename) + r'.*?EOF.*?)'
                r'\n```',
                re.DOTALL
            )
            
            # Replace with a reference to the external file
            if cat_pattern.search(doc_content):
                replacement = f"```bash\n# Using external file: {filename}\n```\n\n"
                doc_content = cat_pattern.sub(replacement, doc_content)
                modified = True
                print_message(f"\nTransformed document to use external {filename} instead of inline creation")
                
            # Handle other file creation patterns (echo, tee)
            echo_pattern = re.compile(
                r'```(?:bash|azurecli|azure-cli-interactive|azurecli-interactive)\s*\n'
                r'(.*?echo\s+.*?>\s*' + re.escape(filename) + r'.*?)'
                r'\n```',
                re.DOTALL
            )
            if echo_pattern.search(doc_content):
                replacement = f"```bash\n# Using external file: {filename}\n```\n\n"
                doc_content = echo_pattern.sub(replacement, doc_content)
                modified = True
                
        if modified:
            with open(doc_path, "w") as f:
                f.write(doc_content)
            print_message("\nDocument transformed to use external dependency files")
            return True
        return False
    except Exception as e:
        print_message(f"\nError transforming document: {e}")
        return False
    
def update_dependency_file(file_info, error_message, main_doc_path):
    """Update a dependency file based on error message."""
    filename = file_info["filename"]
    file_path = file_info["path"]
    file_type = file_info["type"]
    
    print_message(f"\nUpdating dependency file: {filename} based on error...")
    
    try:
        with open(file_path, "r") as f:
            file_content = f.read()
        
        with open(main_doc_path, "r") as f:
            doc_content = f.read()
        
        # Prompt for fixing the dependency file
        fix_prompt = f"""The following dependency file related to the Exec Doc is causing errors:

        File: {filename}
        Type: {file_type}
        Error: {error_message}

        Here is the current content of the file: 
        
        {file_content}
        
        Here is the main Exec Doc for context:

        {doc_content}

        Please fix the issue in the dependency file. Return ONLY the corrected file content, nothing else.
        """
        
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are an AI specialized in fixing technical issues in configuration and code files."},
                {"role": "user", "content": fix_prompt}
            ]
        )
        
        updated_content = response.choices[0].message.content
        
        # Remove any markdown formatting that might have been added
        updated_content = re.sub(r'^```.*$', '', updated_content, flags=re.MULTILINE)
        updated_content = re.sub(r'^```$', '', updated_content, flags=re.MULTILINE)
        updated_content = updated_content.strip()
        
        # Validate the updated content based on file type
        if filename.endswith('.json') or file_type == 'json':
            try:
                parsed = json.loads(updated_content)
                updated_content = json.dumps(parsed, indent=2)  # Pretty-print_message JSON
            except json.JSONDecodeError:
                print_message(f"\nWarning: Updated content for {filename} is not valid JSON.")
        
        elif filename.endswith('.yaml') or filename.endswith('.yml') or file_type == 'yaml':
            try:
                parsed = yaml.safe_load(updated_content)
                updated_content = yaml.dump(parsed, default_flow_style=False)  # Pretty-print_message YAML
            except yaml.YAMLError:
                print_message(f"\nWarning: Updated content for {filename} is not valid YAML.")
        
        # Write the updated content to the file
        with open(file_path, "w") as f:
            f.write(updated_content)
        
        print_message(f"\nUpdated dependency file: {filename}")
        return True
    except Exception as e:
        print_message(f"\nError updating dependency file {filename}: {e}")
        return False

def analyze_error(error_log, dependency_files=[]):
    """Analyze error log to determine if issue is in main doc or dependency files."""
    if not dependency_files:
        return {"type": "main_doc", "file": None}
    
    for dep_file in dependency_files:
        filename = dep_file["filename"]
        # Check if error mentions the dependency file name
        if filename in error_log:
            return {
                "type": "dependency_file",
                "file": dep_file,
                "message": error_log
            }
    # If no specific dependency file is mentioned, check for patterns
    error_patterns = [
        r"Error: open (.*?): no such file or directory",
        r"couldn't find file (.*?)( |$|\n)",
        r"failed to read (.*?):( |$|\n)",
        r"file (.*?) not found",
        r"YAML|yaml parsing error",
        r"JSON|json parsing error",
        r"invalid format in (.*?)( |$|\n)"
    ]
    
    for pattern in error_patterns:
        matches = re.search(pattern, error_log, re.IGNORECASE)
        if matches and len(matches.groups()) > 0:
            file_mentioned = matches.group(1)
            for dep_file in dependency_files:
                if dep_file["filename"] in file_mentioned:
                    return {
                        "type": "dependency_file",
                        "file": dep_file,
                        "message": error_log
                    }
    
    # Default to main doc if no specific dependency file issues found
    return {"type": "main_doc", "file": None}

def remove_backticks_from_file(file_path):
    with open(file_path, "r") as f:
        lines = f.readlines()

    if lines and "```" in lines[0]:
        lines = lines[1:]

    if lines and "```" in lines[-1]:
        lines = lines[:-1]

    # Remove backticks before and after the metadata section
    if lines and "---" in lines[0]:
        for i in range(1, len(lines)):
            if "---" in lines[i]:
                if "```" in lines[i + 1]:
                    lines = lines[:i + 1] + lines[i + 2:]
                break

    with open(file_path, "w") as f:
        f.writelines(lines)

def setup_output_folder(input_type, input_name, title=None):
    """Create a folder to store all iterations of the document."""
    if title:
        # Use the title if provided (cleaner folder name)
        base_name = title.replace(' ', '_').replace(':', '').replace(';', '').replace('/', '_')
        base_name = re.sub(r'[^\w\-_]', '', base_name)  # Remove special chars
    else:
        # Fallback to old naming scheme if title not available
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if input_type == 'file':
            base_name = os.path.splitext(os.path.basename(input_name))[0]
        elif input_type == 'workload_description':
            base_name = "_".join(input_name.split()[:3])
        else:
            base_name = "exec_doc"
        base_name = f"{timestamp}_{input_type}_{base_name}"
    
    # Handle duplicate folder names
    folder_name = base_name
    counter = 1
    while os.path.exists(folder_name):
        folder_name = f"{base_name}_{counter}"
        counter += 1
    
    # Create the folder at the script's location
    os.makedirs(folder_name, exist_ok=True)
    
    return folder_name

def check_existing_log(input_path=None):
    """Check if global log.json exists at the script level.
    
    Args:
        input_path: Optional path (no longer needed for logging)
    
    Returns:
        Tuple of (exists, log_path, existing_data)
        exists: Boolean indicating if log.json exists
        log_path: Path to the log file
        existing_data: Dictionary containing the existing log data
    """
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.realpath(__file__))
    log_file_path = os.path.join(script_dir, "log.json")
    
    # Check if log.json exists in the script directory
    if os.path.isfile(log_file_path):
        try:
            with open(log_file_path, 'r') as f:
                existing_data = json.load(f)
                return True, log_file_path, existing_data
        except Exception as e:
            print_message(f"\nWarning: Found log.json but couldn't read it: {e}")
    
    return False, log_file_path, None

def calculate_success_rate(log_data):
    """Calculate success rate for doc creation/conversion attempts."""
    entries = log_data.get("doc_creation", []) + log_data.get("doc_conversion", [])
    if not entries:
        return 0
    success_count = sum(1 for entry in entries if entry.get("Result") == "Success")
    return round(success_count / len(entries), 2)

def calculate_total_execution_time(log_data):
    """Sum up execution time across all operations."""
    total = 0
    for section in log_data:
        if section != "info" and isinstance(log_data[section], list):
            total += sum(entry.get("Execution Time (in seconds)", 0) for entry in log_data[section])
    return total

def update_progress_log(output_folder, new_data, input_type, user_intent=None, existing_data=None):
    """Update the JSON progress log with the new structure."""
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.realpath(__file__))
    log_file = os.path.join(script_dir, "log.json")
    
    # Map input_type to appropriate section name
    section_map = {
        'file': 'doc_conversion',
        'workload_description': 'doc_creation',
        'shell_script': 'script_documentation',
        'pii_redaction': 'pii_redaction',
        'security_check': 'security_analysis',
        'seo_optimization': 'seo_optimization'
    }
    
    section_name = section_map.get(input_type, 'other_operations')
    
    # Start with a clean structure
    if not existing_data or not isinstance(existing_data, dict):
        # Initialize brand new log structure
        log_data = {
            "info": {
                "Creation Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Last Modified Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Total Operations": 1,  # Starting with this operation
                "Success Rate": 0,      # No previous data
                "Operation Summary": {
                    "doc_creation": 0,
                    "doc_conversion": 0,
                    "script_documentation": 0,
                    "security_analysis": 0,
                    "pii_redaction": 0,
                    "seo_optimization": 0
                },
                "Total Execution Time (in seconds)": 0  # No previous data
            },
            section_name: []  # Initialize the current section
        }
        # Update the operation count for this type
        log_data["info"]["Operation Summary"][section_name] = 1
    else:
        # Use existing structure
        log_data = existing_data
        
        # Ensure info section exists with proper structure
        if "info" not in log_data:
            log_data["info"] = {
                "Creation Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Last Modified Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Total Operations": 0,
                "Success Rate": 0,
                "Operation Summary": {
                    "doc_creation": 0,
                    "doc_conversion": 0,
                    "script_documentation": 0,
                    "security_analysis": 0,
                    "pii_redaction": 0,
                    "seo_optimization": 0
                },
                "Total Execution Time (in seconds)": 0
            }
    
    # Add project folder information to each entry
    for entry in new_data:
        entry["Project Folder"] = output_folder
        # Add user intent if provided
        if user_intent:
            entry["User Intent"] = user_intent
    
    # Create section if it doesn't exist
    if section_name not in log_data:
        log_data[section_name] = []
    
    # Add new data to the appropriate section
    if isinstance(new_data, list):
        log_data[section_name].extend(new_data)
    else:
        log_data[section_name].append(new_data)
    
    # Update metrics in info section
    log_data["info"]["Last Modified Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_data["info"]["Total Operations"] = sum(len(log_data.get(section, [])) for section in log_data if section != "info")
    log_data["info"]["Success Rate"] = calculate_success_rate(log_data)
    
    for section in section_map.values():
        if section in log_data:
            log_data["info"]["Operation Summary"][section] = len(log_data[section])
    
    log_data["info"]["Total Execution Time (in seconds)"] = calculate_total_execution_time(log_data)
    
    # Write updated log to file with pretty formatting
    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=4)

def collect_iteration_data(input_type, user_input, output_file, attempt, errors, start_time, success):
    """Collect data for a single iteration."""
    return {
        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'Type': input_type,
        'Input': user_input,
        'Output': output_file,
        'Attempt Number': attempt,
        'Errors Encountered': errors,
        'Execution Time (in seconds)': round(time.time() - start_time),  # Rounded to nearest second
        'Result': "Success" if success else "Failure"
    }

def generate_title_from_description(description, display=False):
    """Generate a title for the Exec Doc based on the workload description."""
    
    title_prompt = """Create a concise, descriptive title for an Executable Document (Exec Doc) based on the following workload description. 
    The title should:
    1. Be clear and informative
    2. Start with an action verb (Deploy, Create, Configure, etc.) when appropriate
    3. Mention the main Azure service(s) involved
    4. Be formatted like a typical Azure quickstart or tutorial title
    5. Not exceed 10 words
    
    Return ONLY the title text, nothing else.
    
    Workload description:
    """
    
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are an AI specialized in creating concise, descriptive titles."},
                {"role": "user", "content": title_prompt + description}
            ]
        )
        
        title = response.choices[0].message.content.strip()
        # Remove any quotes, backticks or other formatting that might be included
        title = title.strip('"\'`')
        
        # Only print the header if display is True
        if display:
            print_header(f"Title: {title}", "=")
        
        return title
    except Exception as e:
        print_message(f"\nError generating title: {e}")
        return "Azure Executable Documentation Guide"  # Default fallback title
    
def perform_security_check(doc_path):
    """Perform a comprehensive security vulnerability check on an Exec Doc."""
    if not os.path.isfile(doc_path):
        print_message(f"\nError: The file {doc_path} does not exist.")
        return None

    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
    except Exception as e:
        print_message(f"\nError reading document: {e}")
        return None

    # Create output filename
    doc_name = os.path.splitext(os.path.basename(doc_path))[0]
    output_file = f"{doc_name}_security_report.md"

    print_message("\nPerforming comprehensive security vulnerability analysis...")
    
    # Use the LLM to analyze security vulnerabilities
    security_prompt = """Conduct a thorough, state-of-the-art security vulnerability analysis of this Exec Doc. Analyze both static aspects (code review) and dynamic aspects (runtime behavior).

    Focus on:
    1. Authentication and authorization vulnerabilities
    2. Potential for privilege escalation
    3. Resource exposure risks
    4. Data handling and privacy concerns
    5. Network security considerations
    6. Input validation vulnerabilities
    7. Command injection risks
    8. Cloud-specific security threats
    9. Compliance issues with security best practices
    10. Secret management practices
    
    Structure your report with the following sections:
    1. Executive Summary - Overall risk assessment
    2. Methodology - How the analysis was performed
    3. Findings - Detailed description of each vulnerability found
    4. Recommendations - Specific remediation steps for each issue
    5. Best Practices - General security improvements
    
    For each vulnerability found, include:
    - Severity (Critical, High, Medium, Low)
    - Location in code
    - Description of the vulnerability
    - Potential impact
    - Recommended fix with code example where appropriate
    
    Use the OWASP Top 10 and cloud security best practices as frameworks for your analysis.
    Format the output as a professional Markdown document with appropriate headings, tables, and code blocks.
    
    Document content:
    """

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are an AI specialized in security vulnerability assessment and report generation."},
            {"role": "user", "content": security_prompt + "\n\n" + doc_content}
        ]
    )
    
    report_content = response.choices[0].message.content
    
    # Save the security report
    try:
        with open(output_file, "w") as f:
            f.write(report_content)
        print_message(f"\nSecurity analysis report saved to: {output_file}")
        return output_file
    except Exception as e:
        print_message(f"\nError saving security report: {e}")
        return None

def perform_seo_check(doc_path, checklist_path="seo-checklist.md"):
    """Perform an SEO optimization check on an Exec Doc using the SEO checklist."""
    if not os.path.isfile(doc_path):
        print_message(f"\nError: The file {doc_path} does not exist.")
        return None
        
    if not os.path.isfile(checklist_path):
        print_message(f"\nError: The SEO checklist file {checklist_path} does not exist.")
        return None

    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
            
        with open(checklist_path, "r") as f:
            checklist_content = f.read()
    except Exception as e:
        print_message(f"\nError reading files: {e}")
        return None

    # Create output filename
    doc_name = os.path.splitext(os.path.basename(doc_path))[0]
    output_file = f"{doc_name}_seo_optimized.md"

    print_message("\nPerforming SEO optimization check...")
    
    # Use the LLM to analyze and optimize the document for SEO
    seo_prompt = """You are an SEO optimization expert. Analyze and optimize the provided document according to the SEO checklist.
    
    For each item in the checklist:
    1. Check if the document meets the criteria
    2. If not, optimize the document to meet the criteria
    3. Comment on the changes you made
    
    When optimizing:
    - Preserve the document's original meaning and technical accuracy
    - Make sure the document flows naturally and reads well
    - Only change what needs to be changed for SEO purposes
    
    Provide your output as the fully optimized document. Return ONLY the updated document, nothing else.
    
    SEO Checklist:
    
    {checklist_content}
    
    Document to optimize:
    
    {doc_content}
    """
    
    seo_prompt = seo_prompt.format(
        checklist_content=checklist_content,
        doc_content=doc_content
    )

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are an AI specialized in SEO optimization for technical documentation."},
            {"role": "user", "content": seo_prompt}
        ]
    )
    
    optimized_content = response.choices[0].message.content
    
    # Save the optimized document
    try:
        with open(output_file, "w") as f:
            f.write(optimized_content)
        print_message(f"\nSEO optimized document saved to: {output_file}")
        return output_file
    except Exception as e:
        print_message(f"\nError saving optimized document: {e}")
        return None
    
def analyze_user_intent(user_input, input_type):
    """Analyze the user's intent based on their input."""
    if input_type == 'file':
        # For file input, we'll analyze the file content
        try:
            with open(user_input, "r") as f:
                file_content = f.read()[:1000]  # Read first 1000 chars for analysis
            prompt = f"Analyze this document beginning and summarize what the user is trying to do in one concise sentence:\n\n{file_content}"
        except:
            return "Convert an existing document to an executable format"
    else:
        # For workload descriptions, analyze the description
        prompt = f"Analyze the following user request and summarize their core intent in one concise sentence:\n\n\"{user_input}\""
    
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You analyze user requests and extract the core intent."},
                {"role": "user", "content": prompt + "\n\nStart with 'User intends to...' and keep it short."}
            ]
        )
        
        intent = response.choices[0].message.content.strip()
        # Remove any quotes or formatting
        intent = intent.strip('"\'`')
        print_message(f"\nUser intent: {intent}")
        return intent
    except Exception as e:
        print_message(f"\nError analyzing user intent: {e}")
        return "Execute commands related to Azure resources"  # Default fallback

def generate_script_description_with_content(script_path, context="", output_file_path=None):
    """Generate descriptions around a shell script without modifying the code with custom output path."""
    if not os.path.isfile(script_path):
        print_message(f"\nError: The file {script_path} does not exist.")
        return None

    try:
        with open(script_path, "r") as f:
            script_content = f.read()
    except Exception as e:
        print_message(f"\nError reading script: {e}")
        return None

    # Create default output filename if not provided
    if not output_file_path:
        script_name = os.path.splitext(os.path.basename(script_path))[0]
        output_file_path = f"{script_name}_documented.md"

    # Prepare prompt for the LLM
    script_prompt = f"""Create an Exec Doc that explains this shell script in detail.
    DO NOT CHANGE ANY CODE in the script. Instead:
    1. Add clear descriptions before and after each functional block
    2. Explain what each section does
    3. Format as a proper markdown document with appropriate headings and structure
    4. Include all the necessary metadata in the front matter
    
    Script context provided by user: {context}
    
    Here is the script content:
    ```
    {script_content}
    ```
    """

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": script_prompt}
        ]
    )
    
    doc_content = response.choices[0].message.content
    
    # Save the generated documentation
    try:
        with open(output_file_path, "w") as f:
            f.write(doc_content)
        remove_backticks_from_file(output_file_path)
        return doc_content
    except Exception as e:
        print_message(f"\nError saving documentation: {e}")
        return None

def redact_pii_from_doc_with_path(doc_path, output_file_path=None):
    """Redact PII from result blocks in an Exec Doc with custom output path."""
    if not os.path.isfile(doc_path):
        print_message(f"\nError: The file {doc_path} does not exist.")
        return None

    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
    except Exception as e:
        print_message(f"\nError reading document: {e}")
        return None

    # Create default output filename if not provided
    if not output_file_path:
        doc_name = os.path.splitext(os.path.basename(doc_path))[0]
        output_file_path = f"{doc_name}_redacted.md"

    # Use the LLM to identify and redact PII
    redaction_prompt = """Redacting PII from the output helps protect sensitive information from being inadvertently shared or exposed. This is crucial for maintaining privacy, complying with data protection regulations, and furthering the company's security posture. 

    Ensure result block(s) have all the PII (Personally Identifiable Information) stricken out from them and replaced with x’s. 

    **Example:** 

    ```markdown
        Results: 

        <!-- expected_similarity=0.3 --> 

        ```output 
        {{ 
            "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxx",
                "location": "eastus",
                "managedBy": null,
                "name": "MyResourceGroupxxx",
                "properties": {{
                    "provisioningState": "Succeeded"
                }},
                "tags": null,
                "type": "Microsoft.Resources/resourceGroups" 
        }} 
        ```
    ```

    >**Note:** The number of x's used to redact PII need not be the same as the number of characters in the original PII. Furthermore, it is recommended not to redact the key names in the output, only the values containing the PII (which are usually strings).
    
    >**Note:** Here are some examples of PII in result blocks: Unique identifiers for resources, Email Addresses, Phone Numbers, IP Addresses, Credit Card Numbers, Social Security Numbers (SSNs), Usernames, Resource Names, Subscription IDs, Resource Group Names, Tenant IDs, Service Principal Names, Client IDs, Secrets and Keys.
    
    Document content:
    """

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are an AI specialized in PII redaction. Either redact the PII or return the document as is - nothing els is acceptable."},
            {"role": "user", "content": redaction_prompt + "\n\n" + doc_content}
        ]
    )
    
    redacted_content = response.choices[0].message.content
    
    # Save the redacted document
    try:
        with open(output_file_path, "w") as f:
            f.write(redacted_content)
        remove_backticks_from_file(output_file_path)
        return redacted_content
    except Exception as e:
        print_message(f"\nError saving redacted document: {e}")
        return None

def perform_security_check_with_path(doc_path, output_file_path=None):
    """Perform a comprehensive security vulnerability check on an Exec Doc with custom output path."""
    if not os.path.isfile(doc_path):
        print_message(f"\nError: The file {doc_path} does not exist.")
        return None

    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
    except Exception as e:
        print_message(f"\nError reading document: {e}")
        return None

    # Create default output filename if not provided
    if not output_file_path:
        doc_name = os.path.splitext(os.path.basename(doc_path))[0]
        output_file_path = f"{doc_name}_security_report.md"

    # Use the LLM to analyze security vulnerabilities
    security_prompt = """Conduct a thorough, state-of-the-art security vulnerability analysis of this Exec Doc. Analyze both static aspects (code review) and dynamic aspects (runtime behavior).

    Focus on:
    1. Authentication and authorization vulnerabilities
    2. Potential for privilege escalation
    3. Resource exposure risks
    4. Data handling and privacy concerns
    5. Network security considerations
    6. Input validation vulnerabilities
    7. Command injection risks
    8. Cloud-specific security threats
    9. Compliance issues with security best practices
    10. Secret management practices
    
    Structure your report with the following sections:
    1. Executive Summary - Overall risk assessment
    2. Methodology - How the analysis was performed
    3. Findings - Detailed description of each vulnerability found
    4. Recommendations - Specific remediation steps for each issue
    5. Best Practices - General security improvements
    
    For each vulnerability found, include:
    - Severity (Critical, High, Medium, Low)
    - Location in code
    - Description of the vulnerability
    - Potential impact
    - Recommended fix with code example where appropriate
    
    Use the OWASP Top 10 and cloud security best practices as frameworks for your analysis.
    Format the output as a professional Markdown document with appropriate headings, tables, and code blocks.
    
    Document content:
    """

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are an AI specialized in security vulnerability assessment and report generation."},
            {"role": "user", "content": security_prompt + "\n\n" + doc_content}
        ]
    )
    
    report_content = response.choices[0].message.content
    
    # Save the security report
    try:
        with open(output_file_path, "w") as f:
            f.write(report_content)
        remove_backticks_from_file(output_file_path)
        return report_content
    except Exception as e:
        print_message(f"\nError saving security report: {e}")
        return None

def perform_seo_check_with_path(doc_path, checklist_path="seo-checklist.md", output_file_path=None):
    """Perform an SEO optimization check on an Exec Doc using the SEO checklist with custom output path."""
    if not os.path.isfile(doc_path):
        print_message(f"\nError: The file {doc_path} does not exist.")
        return None
        
    if not os.path.isfile(checklist_path):
        print_message(f"\nError: The SEO checklist file {checklist_path} does not exist.")
        return None

    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
            
        with open(checklist_path, "r") as f:
            checklist_content = f.read()
    except Exception as e:
        print_message(f"\nError reading files: {e}")
        return None

    # Create default output filename if not provided
    if not output_file_path:
        doc_name = os.path.splitext(os.path.basename(doc_path))[0]
        output_file_path = f"{doc_name}_seo_optimized.md"

    # Use the LLM to analyze and optimize the document for SEO
    seo_prompt = """You are an SEO optimization expert. Analyze and optimize the provided document according to the SEO checklist.
    
    For each item in the checklist:
    1. Check if the document meets the criteria
    2. If not, optimize the document to meet the criteria
    3. Comment on the changes you made
    
    When optimizing:
    - Preserve the document's original meaning and technical accuracy
    - Make sure the document flows naturally and reads well
    - Only change what needs to be changed for SEO purposes
    
    Provide your output as the fully optimized document. Return ONLY the updated document, nothing else.
    
    SEO Checklist:
    
    {checklist_content}
    
    Document to optimize:
    
    {doc_content}
    """
    
    seo_prompt = seo_prompt.format(
        checklist_content=checklist_content,
        doc_content=doc_content
    )

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are an AI specialized in SEO optimization for technical documentation."},
            {"role": "user", "content": seo_prompt}
        ]
    )
    
    optimized_content = response.choices[0].message.content
    
    # Save the optimized document
    try:
        with open(output_file_path, "w") as f:
            f.write(optimized_content)
        remove_backticks_from_file(output_file_path)
        return optimized_content
    except Exception as e:
        print_message(f"\nError saving optimized document: {e}")
        return None

# Add this function to get user feedback
def get_user_feedback(document_path):
    """Get user feedback by allowing direct edits or text input."""
    # Extract attempt number from filename for better messaging
    attempt_info = ""
    if "attempt_" in document_path:
        attempt_num = document_path.split("attempt_")[1].split("_")[0]
        result = "successful" if "success" in document_path else "failed"
        attempt_info = f"Attempt #{attempt_num} ({result})"
    
    print_header(f"FEEDBACK REQUESTED FOR {attempt_info}", "-")
    print_message(f"Document location: {document_path}")
    print_message("\nYou can provide feedback in two ways:")
    print_message("1. Edit the document directly in your editor, then return here", prefix="  ✏️  ")
    print_message("2. Type your suggestions below", prefix="  💬 ")
    
    # Save original state to detect changes
    with open(document_path, "r") as f:
        original_content = f.read()
    
    # Get text feedback if any
    cli_feedback = input("\n>> Your feedback (or press Enter to keep going): ")
    
    # Check if file was modified
    with open(document_path, "r") as f:
        current_content = f.read()
    
    # Return a dictionary with both types of feedback
    result = {"cli_feedback": cli_feedback.strip() if cli_feedback.strip() else None}
    
    if current_content != original_content:
        print_message("\n✅ Document changes detected and will be incorporated!")
        # Restore original for proper AI processing
        # with open(document_path, "w") as f:
        #     f.write(original_content)
        # Include the edited content in the result
        result["doc_edit"] = current_content
    
    # Return both types of feedback or None if neither provided
    if result["cli_feedback"] or "doc_edit" in result:
        return result
    else:
        return None

def get_content_from_url(url):
    """Extract content from a URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        # Get text content
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        print_message(f"Error fetching content from URL {url}: {e}", color="red")
        return f"[Failed to fetch content from {url}]"

def get_content_from_file(file_path):
    """Extract content from a local file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print_message(f"Error reading file {file_path}: {e}", color="red")
        return f"[Failed to read file {file_path}]"

def collect_data_sources():
    """Collect data sources from the user."""
    
    choice = input("\nWould you like to add data sources the AI should use to generate the doc? (y/n): ").lower().strip()
    
    if choice != 'y':
        return ""
    
    sources = []
    print_message("\nEnter data sources (URLs or local file paths) one per line. When finished, enter a blank line:")

    line_num = 1
    while True:
        source = input(f"\n{line_num}. ").strip()        
        if not source:
            break
            
        # Detect if it's a URL or file path
        if source.startswith(('http://', 'https://')):
            print_message("")
            print_message(f"Fetching content from URL: {source}...", prefix="🔗 ")
            content = get_content_from_url(source)
            sources.append(f"--- Content from URL: {source} ---\n{content}\n")
        else:
            if os.path.exists(source):
                print_message(f"Reading file: {source}...", prefix="📄 ")
                content = get_content_from_file(source)
                sources.append(f"\n--- Content from file: {source} ---\n{content}\n")
            else:
                print_message(f"File not found: {source}", color="red")
        
        line_num += 1
    
    if sources:
        print_message(f"\nCollected content from {len(sources)} source(s).", prefix="✓ ")
        return "\n\n".join(sources)
    else:
        print_message("\nNo valid sources provided.", color="yellow")
        return ""

def requires_aks_cluster(doc_path):
    """
    Determine if the Exec Doc requires an existing AKS cluster as a prerequisite.
    If 'az aks create' is present, ask the LLM for clarification.
    If not present, assume AKS cluster is a prerequisite.
    """
    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
        # Simple string match for 'az aks create' (case-insensitive)
        if "az aks create" not in doc_content.lower():
            aks_prompt = f"""
You are an expert in Azure and Kubernetes documentation. Given the following markdown document, answer with ONLY 'yes' or 'no' (no punctuation, no explanation): Does this document require an existing Azure Kubernetes Service (AKS) cluster as a prerequisite (i.e., does it assume the cluster is already created and available for use, rather than creating it as part of the steps)? Only answer 'yes' or 'no'.

Document:
---
{doc_content}
---
"""
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert in Azure and Kubernetes documentation."},
                    {"role": "user", "content": aks_prompt}
                ]
            )
            answer = response.choices[0].message.content.strip().lower()
            return answer.startswith("y")
        else:
            # If 'az aks create' is present, assume AKS cluster is not a prerequisite
            return False
    except Exception:
        return False

def extract_aks_env_vars(doc_path):
    """Use LLM to extract AKS-related environment variable names from the Exec Doc."""
    var_map = {
        "resource_group": "RESOURCE_GROUP_NAME",
        "cluster_name": "AKS_CLUSTER_NAME",
        "region": "REGION"
    }
    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
        aks_var_prompt = """
You are an expert in Azure and Kubernetes documentation. Given the following markdown document, extract the actual environment variable names used for:
1. Resource group name
2. AKS cluster name
3. Region

Return your answer as a JSON object with the following keys:
- resource_group
- cluster_name
- region

If any variable is not found, use the default values:
- resource_group: RESOURCE_GROUP_NAME
- cluster_name: AKS_CLUSTER_NAME
- region: REGION

ONLY return the JSON object, nothing else.

Document:
---
{doc}
---
""".format(doc=doc_content[:6000])  # Limit to first 6000 chars for prompt size

        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are an expert in Azure and Kubernetes documentation."},
                {"role": "user", "content": aks_var_prompt}
            ]
        )
        import json
        answer = response.choices[0].message.content.strip()
        # Try to parse the JSON from the LLM response
        var_map_llm = json.loads(answer)
        # Fallback to defaults if any key is missing
        for k in var_map:
            if not var_map_llm.get(k):
                var_map_llm[k] = var_map[k]
        return var_map_llm
    except Exception:
        return var_map

def get_user_defined_variables():
    """Prompt the user to define environment variables and their values."""
    print_message("\nDo you want to define specific environment variables and their values for this run?")
    print_message("If yes, these will be used to guide document generation and for 'ie test/execute'.")
    print_message("Example: RESOURCE_GROUP_NAME=my-test-rg")
    choice = input("Define variables? (y/n, default n): ").lower().strip()
    
    if choice != 'y':
        return {}
        
    variables = {}
    print_message("Enter variables one per line (e.g., VAR_NAME=var_value). Press Enter on an empty line to finish.")
    while True:
        entry = input(">> ").strip()
        if not entry:
            break
        if '=' not in entry:
            print_message("Invalid format. Please use NAME=value. Skipping this entry.")
            continue
        name, value = entry.split('=', 1)
        name = name.strip()
        value = value.strip()
        if not name:
            print_message("Variable name cannot be empty. Skipping this entry.")
            continue
        variables[name] = value
        
    if variables:
        print_message(f"\nUser-defined variables: {variables}", prefix="🔧 ")
    return variables

# Replace the menu display in main() function
def main():
    while True:
        print_header("WELCOME TO ADA - AI DOCUMENTATION ASSISTANT", "=")
        print_message("This tool helps you write and troubleshoot Executable Documents efficiently!\n")
        
        print_header("MENU OPTIONS", "-")
        print_message("1. Convert file to Exec Doc", prefix="  📄 ")
        print_message("2. Generate new Exec Doc from scratch", prefix="  🔍 ")
        print_message("3. Create descriptions for your shell script", prefix="  📝 ")
        print_message("4. Redact PII from your Doc", prefix="  🔒 ")
        print_message("5. Give security analysis report on your Doc", prefix="  🛡️  ")
        print_message("6. Perform SEO optimization check on your Doc", prefix="  📊 ")
        print_message("\nEnter 1-6 to select an option or any other key to exit.")
        
        choice = input("\n>> Your choice: ")
        

        if choice not in ["1", "2", "3", "4", "5", "6"]:
            print_message("\nThank you for using ADA! Goodbye!")
            break

        if choice == "1":
            user_input = input("\nEnter the path to your markdown file: ")
            if not os.path.isfile(user_input) or not user_input.endswith('.md'):
                print_message("\nInvalid file path or file type. Please provide a valid markdown file.")
                continue
            
            user_defined_vars = get_user_defined_variables() # Get user variables
            
            # Add new option for interactive mode
            interactive_mode = input("\nEnable interactive mode (you will be prompted for feedback after each step)? (y/n): ").lower() == 'y'
                
            input_type = 'file'
            with open(user_input, "r") as f:
                input_content = f.read()
                input_content = f"CONVERT THE FOLLOWING EXISTING DOCUMENT INTO AN EXEC DOC. THIS IS A CONVERSION TASK, NOT CREATION FROM SCRATCH. DON'T EXPLAIN WHAT YOU ARE DOING BEHIND THE SCENES INSIDE THE DOC. PRESERVE ALL ORIGINAL CONTENT, STRUCTURE, AND NARRATIVE OUTSIDE OF CODE BLOCKS. CRITICALLY IMPORTANT: NEVER CHANGE THE LANGUAGE TYPE OF CODE BLOCKS. KEEP THE EXACT SAME LANGUAGE IDENTIFIER AFTER TRIPLE BACKTICKS AS IN THE ORIGINAL DOCUMENT:\n\n{input_content}"
            # We'll generate dependency files later in the process
            dependency_files = []
            generate_deps = input("\nMake new files referenced in the doc for its execution? (y/n): ").lower() == 'y'
        elif choice == "2":
            user_input = input("\nDescribe your workload for the new Exec Doc: ")
            if not user_input:
                print_message("\nInvalid input. Please provide a workload description.")
                continue
            
            user_defined_vars = get_user_defined_variables() # Get user variables
            
            workload_description = user_input.strip()
            
            # Ask for additional data sources
            reference_data = collect_data_sources()
            
            # Add reference data to the workload description if available
            if reference_data:
                print_message("\nReference data will be incorporated into document generation.", prefix="📚 ")
                user_input = f"{workload_description}\n\nREFERENCE DATA:\n{reference_data}"
            else:
                user_input = workload_description
                
            # Add new option for interactive mode
            interactive_mode = input("\nEnable interactive mode (you will be prompted for feedback after each step)? (y/n): ").lower() == 'y'

            input_type = 'workload_description'
            input_content = user_input
            dependency_files = []
            generate_deps = True
        elif choice == "3":
            user_input = input("\nEnter the path to your shell script: ")
            context = input("\nProvide additional context for the script (optional): ")
            if not os.path.isfile(user_input):
                print_message("\nInvalid file path. Please provide a valid shell script.")
                continue
            input_type = 'shell_script'
            
            # Get user intent
            user_intent = analyze_user_intent(user_input, input_type)

            # Check for existing log.json
            log_exists, log_path, existing_data = check_existing_log()
                    
            if log_exists:
                print_message(f"\nFound existing progress log. Will append results.")
            else:
                print_message(f"\nCreating new progress log.")
                
            # Create a new folder for outputs
            output_folder = os.path.dirname(user_input) or "."
            print_message(f"\nAll files will be saved to: {output_folder}")
            
            # Initialize tracking
            all_iterations_data = []
            start_time = time.time()
            
            # Generate documentation
            print_message("\nGenerating documentation for shell script...")
            output_file_name = os.path.join(output_folder, f"{os.path.splitext(os.path.basename(user_input))[0]}_documented.md")
            
            # Store output in the same directory as the source script
            output_file_name = f"{os.path.splitext(user_input)[0]}_documented.md"
            
            # Call the function with modified path
            output_content = generate_script_description_with_content(user_input, context, output_file_name)
            
            # Create iteration data
            iteration_data = collect_iteration_data(
                input_type,
                user_input,
                output_file_name,
                1,  # First attempt
                "",  # No errors
                start_time,
                True  # Assume success
            )
            all_iterations_data.append(iteration_data)
            
            if log_exists:
                update_progress_log(output_folder, all_iterations_data, input_type, user_intent, existing_data)
            else:
                update_progress_log(output_folder, all_iterations_data, input_type, user_intent)
            
            print_message(f"\nScript documentation saved to: {output_file_name}")
            continue
        elif choice == "4":
            user_input = input("\nEnter the path to your Exec Doc for PII redaction: ")
            if not os.path.isfile(user_input) or not user_input.endswith('.md'):
                print_message("\nInvalid file path or file type. Please provide a valid markdown file.")
                continue
            input_type = 'pii_redaction'
            
            # Get user intent
            user_intent = analyze_user_intent(user_input, input_type)

            # Check for existing log.json
            log_exists, log_path, existing_data = check_existing_log()
            
            if log_exists:
                print_message(f"\nFound existing progress log. Will append results.")
            else:
                print_message(f"\nCreating new progress log.")
            
            # Create output folder
            doc_title = f"Documentation_for_{os.path.basename(user_input)}"
            output_folder = os.path.dirname(user_input) or "."
            
            # Initialize tracking
            all_iterations_data = []
            start_time = time.time()
            
            # Perform redaction
            print_message("\nRedacting PII from document...")

            # Store output in the same directory as the source doc
            output_file_name = f"{os.path.splitext(user_input)[0]}_redacted.md"
            
            # Call with modified path
            output_content = redact_pii_from_doc_with_path(user_input, output_file_name)
            
            # Create iteration data
            iteration_data = collect_iteration_data(
                input_type,
                user_input,
                output_file_name,
                1,  # First attempt
                "",  # No errors
                start_time,
                True  # Assume success
            )
            all_iterations_data.append(iteration_data)
            
            if log_exists:
                update_progress_log(output_folder, all_iterations_data, input_type, user_intent, existing_data)
            else:
                update_progress_log(output_folder, all_iterations_data, input_type, user_intent)
            
            print_message(f"\nRedacted document saved to: {output_file_name}")
            continue
        elif choice == "5":
            user_input = input("\nEnter the path to your Exec Doc for security analysis: ")
            if not os.path.isfile(user_input) or not user_input.endswith('.md'):
                print_message("\nInvalid file path or file type. Please provide a valid markdown file.")
                continue
            input_type = 'security_check'
            
            # Get user intent
            user_intent = analyze_user_intent(user_input, input_type)

            # Check for existing log.json
            log_exists, log_path, existing_data = check_existing_log()
                    
            if log_exists:
                print_message(f"\nFound existing progress log. Will append results.")
            else:
                print_message(f"\nCreating new progress log.")
                
            # Create a new folder for outputs
            output_folder = os.path.dirname(user_input) or "."
            print_message(f"\nAll files will be saved to: {output_folder}")
            
            # Initialize tracking
            all_iterations_data = []
            start_time = time.time()
            
            # Perform security check
            print_message("\nPerforming comprehensive security vulnerability analysis...")

            # Store output in the same directory as the source doc
            output_file_name = f"{os.path.splitext(user_input)[0]}_security_report.md"
            
            # Call with modified path
            output_content = perform_security_check_with_path(user_input, output_file_name)
            
            # Create iteration data
            iteration_data = collect_iteration_data(
                input_type,
                user_input,
                output_file_name,
                1,  # First attempt
                "",  # No errors
                start_time,
                True  # Assume success
            )
            all_iterations_data.append(iteration_data)
            
            if log_exists:
                update_progress_log(output_folder, all_iterations_data, input_type, user_intent, existing_data)
            else:
                update_progress_log(output_folder, all_iterations_data, input_type, user_intent)
                
            print_message(f"\nSecurity analysis complete. Report saved to: {output_file_name}")
            continue
        elif choice == "6":
            user_input = input("\nEnter the path to your Exec Doc for SEO optimization: ")
            checklist_path = input("\nEnter the path to the SEO checklist (default: seo-checklist.md): ") or "seo-checklist.md"
            
            if not os.path.isfile(user_input) or not user_input.endswith('.md'):
                print_message(f"\nError: {user_input} is not a valid markdown file.")
                continue
                
            input_type = 'seo_optimization'
            
            # Get user intent
            user_intent = analyze_user_intent(user_input, input_type)

            # Check for existing log.json
            log_exists, log_path, existing_data = check_existing_log()
                    
            if log_exists:
                print_message(f"\nFound existing progress log. Will append results.")
            else:
                print_message(f"\nCreating new progress log.")
                
            # Create a new folder for outputs
            output_folder = os.path.dirname(user_input) or "."
            print_message(f"\nAll files will be saved to: {output_folder}")
            
            # Initialize tracking
            all_iterations_data = []
            start_time = time.time()
            
            # Perform SEO check
            print_message("\nPerforming SEO optimization check...")
            
            # Store output in the same directory as the source doc
            output_file_name = f"{os.path.splitext(user_input)[0]}_seo_optimized.md"
            
            # Call with modified path
            output_content = perform_seo_check_with_path(user_input, checklist_path, output_file_name)
            
            # Create iteration data
            iteration_data = collect_iteration_data(
                input_type,
                user_input,
                output_file_name,
                1,  # First attempt
                "",  # No errors
                start_time,
                True  # Assume success
            )
            all_iterations_data.append(iteration_data)

            if log_exists:
                update_progress_log(output_folder, all_iterations_data, input_type, user_intent, existing_data)
            else:
                update_progress_log(output_folder, all_iterations_data, input_type, user_intent)
            
            print_message(f"\nSEO optimized document saved to: {output_file_name}")
            continue
        else:
            print_message("\nInvalid choice. Exiting.")
            continue

        # Generate title first if it's a workload description
        if input_type == 'workload_description':
            doc_title = generate_title_from_description(user_input, display=True)
        else:
            doc_title = os.path.splitext(os.path.basename(user_input))[0]
        
        # Analyze user intent
        user_intent = analyze_user_intent(user_input, input_type)
        
        # Check for existing log.json
        log_exists, log_path, existing_data = check_existing_log()
                
        if log_exists:
            print_message(f"\nFound existing progress log. Will append results.")
        else:
            print_message(f"\nCreating new progress log.")
            
        # Create a new folder only for option 2 (workload description)
        if input_type == 'workload_description':
            output_folder = setup_output_folder(input_type, user_input, doc_title)
            print_message(f"\nAll files will be saved to: {output_folder}")
        else:
            # For other options, use the source file's directory
            output_folder = os.path.dirname(user_input) or "."
        
        # Initialize tracking
        all_iterations_data = []

        install_innovation_engine()

        max_attempts = 11
        attempt = 1
        # if input_type == 'file':
        #     output_file = f"{os.path.splitext(user_input)[0]}_converted.md"
        # else:
        #     output_file = f"{generate_title_from_description(user_input)}_ai_generated.md"

        start_time = time.time()
        errors_encountered = []
        errors_text = ""  # Initialize errors_text here
        success = False
        dependency_files_generated = False
        additional_instruction = ""
        user_edited_content = None  # Add this line to initialize the flag

        while attempt <= max_attempts:
            iteration_start_time = time.time()
            iteration_errors = []
            made_dependency_change = False
            output_file = os.path.join(output_folder, f"attempt_{attempt}.md")
            
            llm_variable_instruction = ""
            if user_defined_vars:
                var_names_list = ", ".join(f"'{k}'" for k in user_defined_vars.keys())
                llm_variable_instruction = (
                    f"\n\nUSER-DEFINED VARIABLE NAMES: The user has specified the following environment variable "
                    f"NAMES that you MUST prioritize using in the document where appropriate: {var_names_list}. "
                    f"When you need to define an environment variable for a concept (e.g., resource group name, location), "
                    f"if a user-provided name seems relevant for that concept, use the user's variable name. For example, "
                    f"if the user provides 'MY_RG' and the document needs a resource group name, use 'MY_RG' "
                    f"instead of a default like 'RESOURCE_GROUP_NAME'. You are still responsible for generating the "
                    f"'export' statements and appropriate values (e.g., export MY_RG=\\\"my-resource-group$RANDOM_SUFFIX\\\" "
                    f"or export MY_LOCATION=\\\"eastus2\\\"). The primary goal is to use the user's *names*."
                )
            

            if attempt == 1:
                print_header(f"Attempt {attempt}: Generating Exec Doc", "-")

                current_input_content = input_content + llm_variable_instruction
                
                response = client.chat.completions.create(
                    model=deployment_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": current_input_content}
                    ]
                )
                output_file_content = response.choices[0].message.content

                with open(output_file, "w") as f:
                    f.write(output_file_content)
                    
                # Generate dependency files after first creation
                if generate_deps and not dependency_files_generated:
                    _, dependency_files = generate_dependency_files(output_file)
                    dependency_files_generated = True
                    
                    # Add this new line to transform the document after dependency generation
                    if dependency_files:
                        transform_document_for_dependencies(output_file, dependency_files)
            else:
                print_header(f"Attempt {attempt}: Fixing Exec Doc", "-")
                
                # Check if this is a retry after user feedback with document edits only
                if attempt > 1 and 'user_edited_content' in locals() and user_edited_content:
                    print_message("\nUsing your directly edited version without AI modifications...")
                    output_file_content = user_edited_content
                    with open(output_file, "w") as f:
                        f.write(output_file_content)
                    # Clear the flag
                    user_edited_content = None
                else:
                    # Analyze if the error is in the main doc or in dependency files
                    error_analysis = analyze_error(errors_text, dependency_files)
                    
                    if error_analysis["type"] == "dependency_file" and error_analysis["file"]:
                        # If error is in a dependency file, try to fix it
                        dep_file = error_analysis["file"]
                        print_message(f"\nDetected issue in dependency file: {dep_file['filename']}")
                        update_dependency_file(dep_file, error_analysis["message"], output_file)
                        made_dependency_change = True  # Set the flag
                    else:
                        # If error is in main doc or unknown, update the main doc
                        user_prompt_for_fix = (
                            f"The following error(s) have occurred during testing:\n{errors_text}\n{additional_instruction}\n\n"
                            f"Please carefully analyze these errors and make necessary corrections to the document to prevent them "
                            f"from happening again. Try to find different solutions if the same errors keep occurring. \n"
                            f"IMPORTANT: NEVER change the code block language types "
                            f"Keep the exact same language identifier after triple backticks as in the current document."
                            f"{llm_variable_instruction}" # Add variable instruction here as well
                            f"\nGiven that context, please think hard and don't hurry. I want you to correct the converted document "
                            f"in ALL instances where this error has been or can be found. Then, correct ALL other errors apart "
                            f"from this that you see in the doc. ONLY GIVE THE UPDATED DOC, NOTHING ELSE"
                        )
                        response = client.chat.completions.create(
                            model=deployment_name,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": input_content},
                                {"role": "assistant", "content": output_file_content},
                                {"role": "user", "content": user_prompt_for_fix}
                            ]
                        )
                        output_file_content = response.choices[0].message.content

                        with open(output_file, "w") as f:
                            f.write(output_file_content)    
                    # Check if we need to regenerate dependency files after updating main doc
                    if generate_deps and dependency_files_generated:
                        # Regenerate dependency files if major changes were made to the main doc
                        _, updated_dependency_files = generate_dependency_files(output_file)
                        if updated_dependency_files:
                            dependency_files = updated_dependency_files

            remove_backticks_from_file(output_file)

            aks_prereq = requires_aks_cluster(output_file)
            if user_defined_vars:
                print_header(f"Running Innovation Engine with user-defined variables", "-")
                base_command = "execute" if aks_prereq else "test"
                ie_cmd = ["ie", base_command, output_file]
                for var_name, var_value in user_defined_vars.items():
                    ie_cmd.extend(["--var", f"{var_name}={var_value}"])
            elif aks_prereq:
                print_header(f"Running Innovation Engine using an existing AKS cluster since its a prerequisite to run this doc", "-")
                var_names = extract_aks_env_vars(output_file)
                ie_cmd = [
                    "ie", "execute", output_file,
                    "--var", f"{var_names['resource_group']}=aks-rg",
                    "--var", f"{var_names['cluster_name']}=aks-cluster",
                    "--var", f"{var_names['region']}=eastus2"
                ]
            else:
                print_header(f"Running Innovation Engine tests", "-")
                ie_cmd = ["ie", "test", output_file]
            try:
                result = subprocess.run(ie_cmd, capture_output=True, text=True, timeout=660)
            except subprocess.TimeoutExpired:
                print_message("\nThe 'ie test' command timed out after 11 minutes.")
                errors_encountered.append("The 'ie test' command timed out after 11 minutes.")
                attempt += 1
                continue  # Proceed to the next attempt
                
            if result.returncode == 0:
                print_message("All tests passed successfully!", prefix="✅ ")
                success = True

                # Update the iteration file
                iteration_file = os.path.join(output_folder, f"attempt_{attempt}_success.md")
                os.rename(output_file, iteration_file)          # ⬅️ move, don't duplicate
                output_file = iteration_file   
                with open(iteration_file, "w") as f:
                    f.write(output_file_content)
                    
                # Collect iteration data
                iteration_data = collect_iteration_data(
                    input_type, 
                    user_input, 
                    iteration_file, 
                    attempt, 
                    "", # No errors in successful run
                    start_time,
                    True  # Assume success
                )
                all_iterations_data.append(iteration_data)

                print_header(f"Producing Exec Doc...", "-")
                
                if input_type == 'file':
                    response = client.chat.completions.create(
                        model=deployment_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": input_content},
                            {"role": "assistant", "content": output_file_content},
                            {"role": "user", "content": f"Take the working converted Exec Doc and merge it with the original source document provided for conversion as needed. Ensure that every piece of information outside of code blocks – such as metadata, descriptions, comments, instructions, and any other narrative content – is preserved. The final output should be a comprehensive document that retains all correct code blocks as well as the rich contextual and descriptive details from the source doc, creating the best of both worlds. ONLY GIVE THE UPDATED DOC, NOTHING ELSE"}
                        ]
                    )
                    output_file_content = response.choices[0].message.content
                    
                    iteration_file = os.path.join(output_folder, f"attempt_{attempt}_{'success' if success else 'failure'}.md")
                    with open(iteration_file, "w") as f:
                        f.write(output_file_content)
                    with open(output_file, "w") as f:
                        f.write(output_file_content)
                        
                # Generate dependency files for successful docs if not already done
                if (input_type == 'file' or input_type == 'workload_description') and not dependency_files_generated and generate_deps:
                    print_message("\nGenerating dependency files for the successful document...")
                    _, dependency_files = generate_dependency_files(output_file)
                    
                remove_backticks_from_file(output_file)
                break
            else:
                error_log = get_last_error_log()
                errors_encountered.append(error_log.strip())  # Keep for overall tracking
                iteration_errors.append(error_log.strip())    # For this iteration only
                errors_text = "\n\n ".join(errors_encountered)
                iteration_errors_text = "\n\n ".join(iteration_errors)
                
                # Process and categorize error messages
                error_counts = defaultdict(int)
                # Extract the core error message - focus on the actual error type
                error_key = ""
                for line in error_log.strip().split('\n'):
                    if 'Error:' in line:
                        error_key = line.strip()
                        break
                
                if not error_key and error_log.strip():
                    error_key = error_log.strip().split('\n')[0]  # Use first line if no clear error
                
                # Store this specific error type and count occurrences
                if error_key:
                    error_counts[error_key] += 1
                    for prev_error in errors_encountered[:-1]:  # Check previous errors
                        if error_key in prev_error:
                            error_counts[error_key] += 1
                
                # Progressive strategies based on error repetition
                strategies = [
                    "Look carefully at the exact error message and fix that specific issue.",
                    "Simplify the code block causing the error. Break it into smaller, simpler steps.",
                    "Remove the result block from the code block causing the error.",
                    "Try a completely different command or approach that achieves the same result.",
                    "Fundamentally reconsider this section. Replace it with the most basic, reliable approach possible.",
                    "Remove the problematic section entirely and rebuild it from scratch with a minimalist approach."
                ]
                
                # Determine which strategy to use based on error count
                if error_key in error_counts:
                    strategy_index = min(error_counts[error_key] - 1, len(strategies) - 1)
                    current_strategy = strategies[strategy_index]
                    
                    additional_instruction = f"""
                    Error '{error_key}' has occurred {error_counts[error_key]} times.
                    
                    NEW STRATEGY: {current_strategy}
                    
                    Previous approaches aren't working. Make a significant change following this strategy.
                    Focus on reliability over complexity. Remember to provide valid JSON output where needed.
                    """
                else:
                    additional_instruction = ""
                
                print_message(f"\nError: {error_log.strip()}")
                
                # Update the iteration file
                iteration_file = os.path.join(output_folder, f"attempt_{attempt}_failure.md")
                os.rename(output_file, iteration_file)          # ⬅️ move, don't duplicate
                output_file = iteration_file
                with open(iteration_file, "w") as f:
                    f.write(output_file_content)
                
                # Collect iteration data
                iteration_data = collect_iteration_data(
                    input_type, 
                    user_input, 
                    iteration_file, 
                    attempt, 
                    iteration_errors_text,  # Only errors from this iteration
                    start_time, 
                    False
                )
                all_iterations_data.append(iteration_data)
                
                if 'interactive_mode' in locals() and interactive_mode:
                    feedback = get_user_feedback(iteration_file)
                    if feedback:
                        print_message("\nIncorporating your feedback for the next attempt...")
                        
                        doc_edited = "doc_edit" in feedback
                        cli_feedback_provided = feedback.get("cli_feedback")
                        
                        # Build the feedback prompt based on what the user provided
                        if doc_edited and cli_feedback_provided:
                            # User provided both types of feedback
                            revised_content = feedback["doc_edit"]
                            cli_text = feedback["cli_feedback"]
                            
                            # Special handling for code block type changes
                            original_blocks = re.findall(r'```(\w+)', output_file_content) 
                            revised_blocks = re.findall(r'```(\w+)', revised_content) 
                            
                            block_changes = ""
                            if original_blocks != revised_blocks:
                                block_changes = "\n\nIMPORTANT: The user has changed code block types which MUST be preserved exactly as edited when you update your previous response:\n"
                                for i in range(min(len(original_blocks), len(revised_blocks))):
                                    if original_blocks[i] != revised_blocks[i]:
                                        block_changes += f"- Changed '```{original_blocks[i]}' to '```{revised_blocks[i]}'\n"

                            # Compute the diff for context
                            diff = '\n'.join(difflib.unified_diff(
                                output_file_content.splitlines(),
                                revised_content.splitlines(),
                                fromfile='before.md',
                                tofile='after.md',
                                lineterm=''
                            ))
                            
                            # Save user's direct edits first
                            output_file_content = revised_content
                            
                            # Then call LLM only to incorporate the CLI text feedback while preserving edits
                            feedback_prompt = (
                                "The user has provided two types of feedback on your previous output:\n\n"
                                "1. DOCUMENT EDITS: They've directly edited your previous output. Here is the unified diff showing their changes:\n\n"
                                f"{diff}\n\n"
                                f"{block_changes}"
                                "2. ADDITIONAL COMMENTS: They've also provided these additional instructions:"
                                f"\n\n{cli_text}\n\n"
                                "Incorporate BOTH the document edits (apply them to your previous output as shown in the diff) AND the additional instructions into an updated document. "
                                "STRICTLY follow these user edits - preserve ALL formatting changes EXACTLY as made by the user, "
                                "especially changes to code block types (like bash→shell). "
                                "DO NOT revert any user edits when creating the updated document. "
                                "Ensure all Exec Doc requirements and formatting rules are still met while maintaining the user's exact changes. "
                                "ONLY GIVE THE UPDATED DOC, NOTHING ELSE."
                            )
                            
                            # LLM call to incorporate CLI feedback while respecting document edits
                            response = client.chat.completions.create(
                                model=deployment_name,
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": input_content},
                                    {"role": "assistant", "content": output_file_content},
                                    {"role": "user", "content": feedback_prompt}
                                ]
                            )
                            output_file_content = response.choices[0].message.content
                                        
                        elif doc_edited:
                            # Only document edits - no need to call LLM again
                            revised_content = feedback["doc_edit"]
                            
                            # Set a flag for the next iteration to use this content directly
                            user_edited_content = revised_content
                            
                            # Just use the user's edited version directly
                            output_file_content = revised_content
                            
                            print_message("\nUsing your directly edited version for the next attempt...")

                        elif cli_feedback_provided:
                            # Only CLI feedback - need LLM call to incorporate feedback
                            cli_text = feedback["cli_feedback"]
                            feedback_prompt = (
                                "Please incorporate the following feedback into the document while maintaining all Exec Doc requirements and formatting rules:\n\n"
                                f"{cli_text}\n\n"
                                "ONLY GIVE THE UPDATED DOC, NOTHING ELSE."
                            )
                            
                            # Call LLM to incorporate CLI feedback
                            response = client.chat.completions.create(
                                model=deployment_name,
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": input_content},
                                    {"role": "assistant", "content": output_file_content},
                                    {"role": "user", "content": feedback_prompt}
                                ]
                            )
                            output_file_content = response.choices[0].message.content

                        # Save the updated content back to the file
                        with open(iteration_file, "w") as f:
                            f.write(output_file_content)

                        print_message("\nFeedback incorporated. Running tests with your changes...")
                else:
                    iteration_feedback = ""

                # Only increment attempt if we didn't make a dependency change
                if not made_dependency_change:
                    attempt += 1
                success = False

        if log_exists:
            update_progress_log(output_folder, all_iterations_data, input_type, user_intent, existing_data)
        else:
            update_progress_log(output_folder, all_iterations_data, input_type, user_intent)

        # Replace this section after the while loop
        if success:
            # Don't create a duplicate file if attempt was successful - just copy/rename the last one
            last_success_file = os.path.join(output_folder, f"attempt_{attempt}_success.md")
            # final_file = os.path.join(output_folder, f"FINAL_OUTPUT_success.md")
            # shutil.copy2(last_success_file, final_file)
            # Update output_file variable to point to final file
            output_file = last_success_file
        else:
            # For failures, create a new final file
            final_file = os.path.join(output_folder, f"FINAL_OUTPUT_failure_final.md")
            with open(final_file, "w") as f:
                f.write(output_file_content)
            # Update output_file variable to point to final file
            output_file = final_file

        # # Update output_file variable to point to the final file
        # output_file = final_file

        if attempt > max_attempts:
            print_message(f"\n{'#'*40}\nMaximum attempts reached without passing all tests.\n{'#'*40}")

        end_time = time.time()
        execution_time = end_time - start_time

        print_message(f"\nThe updated file is stored at: {output_file}\n")

if __name__ == "__main__":
    main()
