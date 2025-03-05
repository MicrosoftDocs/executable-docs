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
import yaml  # Add this import at the top of your file

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

deployment_name = 'o3-mini'

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

8. Appropriately add metadata at the start of the Exec Doc. Here are some mandatory fields:

    - title = the title of the Exec Doc
    - description = the description of the Exec Doc
    - ms.topic = what kind of a doc it is e.g. article, blog, etc. 
    - ms.date = the date the Exec Doc was last updated by author 
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

9. Ensure the environment variable names are not placeholders i.e. <> but have a certain generic, useful name. For the location/region parameter, default to "WestUS2" or "centralindia". Additionally, appropriately add descriptions below every section explaining what is happening in that section in crisp but necessary detail so that the user can learn as they go.

10. Don't start and end your answer with ``` backticks!!! Don't add backticks to the metadata at the top!!!. 

11. Ensure that any info, literally any info whether it is a comment, tag, description, etc., which is not within a code block remains unchanged. Preserve ALL details of the doc.

12. Environment variables are dynamic values that store configuration settings, system paths, and other information that can be accessed throughout a doc. By using environment variables, you can separate configuration details from the code, making it easier to manage and deploy applications in an environment like Exec Docs. 

    Declare environment variables _as they are being used_ in the Exec Doc using the export command. This is a best practice to ensure that the variables are accessible throughout the doc. 

    ### Example Exec Doc 1 - Environment variables declared at the _top_ of an Exec Doc, not declared as used
    
    **Environment Variables Section**

    We are at the start of the Exec Doc and are declaring environment variables that will be used throughout the doc. 

    ```bash
    export REGION="eastus"
    ```
    
    **Test Section**

    We are now in the middle of the Exec Doc and we will create a resource group.

    ```bash
    az group create --name "MyResourceGroup" --location $REGION
    ```
    
    ### Example Exec Doc 2 - Environment Variables declared as used** 
    
    **Test Section**

    We are in the middle of the Exec Doc and we will create a resource group. 

    ```bash  
    export REGION="eastus"
    export MY_RESOURCE_GROUP_NAME="MyResourceGroup"
    az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
    ``` 
    
    >**Note:** If you are converting an existing Azure Doc to an Exec Doc and the Azure Doc does not environment variables at all, it is an Exec Doc writing best practice to add them. Additionally, if the Azure Doc has environment variables but they are not declared as they are being used, it is recommended to update them to follow this best practice. 

    >**Note:** Don't have any spaces around the equal sign when declaring environment variables.

13. A major component of Exec Docs is automated infrastructure deployment on the cloud. While testing the doc, if you do not update relevant environment variable names, the doc will fail when run/executed more than once as the resource group or other resources will already exist from the previous runs. 

    Add a random suffix at the end of _relevant_ environment variable(s). The example below shows how this would work when you are creating a resource group.

    **Example:** 

    ```bash  
    export RANDOM_SUFFIX=$(openssl rand -hex 3)
    export REGION="eastus"
    az group create --name "MyResourceGroup$RANDOM_SUFFIX" --location $REGION
    ```

    >**Note:** Add a random suffix to relevant variables that are likely to be unique for each deployment, such as resource group names, VM names, and other resources that need to be uniquely identifiable. However, do not add a random suffix to variables that are constant or environment-specific, such as region, username, or configuration settings that do not change between deployments. 
    
    >**Note:** You can generate your own random suffix or use the one provided in the example above. The `openssl rand -hex 3` command generates a random 3-character hexadecimal string. This string is then appended to the resource group name to ensure that the resource group name is unique for each deployment.

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

            ```JSON 
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

        ```JSON 
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

## WRITE AND ONLY GIVE THE EXEC DOC USING THE ABOVE RULES FOR THE FOLLOWING WORKLOAD: """

def install_innovation_engine():
    if shutil.which("ie") is not None:
        print("\nInnovation Engine is already installed.\n")
        return
    print("\nInstalling Innovation Engine...\n")
    subprocess.check_call(
        ["curl", "-Lks", "https://raw.githubusercontent.com/Azure/InnovationEngine/v0.2.3/scripts/install_from_release.sh", "|", "/bin/bash", "-s", "--", "v0.2.3"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print("\nInnovation Engine installed successfully.\n")

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
        print(f"\nError: The file {script_path} does not exist.")
        return None

    try:
        with open(script_path, "r") as f:
            script_content = f.read()
    except Exception as e:
        print(f"\nError reading script: {e}")
        return None

    # Create output filename
    script_name = os.path.splitext(os.path.basename(script_path))[0]
    output_file = f"{script_name}_documented.md"

    print("\nGenerating documentation for shell script...")
    
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
        print(f"\nScript documentation saved to: {output_file}")
        return output_file
    except Exception as e:
        print(f"\nError saving documentation: {e}")
        return None

def redact_pii_from_doc(doc_path):
    """Redact PII from result blocks in an Exec Doc."""
    if not os.path.isfile(doc_path):
        print(f"\nError: The file {doc_path} does not exist.")
        return None

    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
    except Exception as e:
        print(f"\nError reading document: {e}")
        return None

    # Create output filename
    doc_name = os.path.splitext(os.path.basename(doc_path))[0]
    output_file = f"{doc_name}_redacted.md"

    print("\nRedacting PII from document...")
    
    # Use the LLM to identify and redact PII
    redaction_prompt = """Redacting PII from the output helps protect sensitive information from being inadvertently shared or exposed. This is crucial for maintaining privacy, complying with data protection regulations, and furthering the company's security posture. 

    Ensure result block(s) have all the PII (Personally Identifiable Information) stricken out from them and replaced with x’s. 

    **Example:** 

    ```markdown
        Results: 

        <!-- expected_similarity=0.3 --> 

        ```JSON 
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
        print(f"\nRedacted document saved to: {output_file}")
        return output_file
    except Exception as e:
        print(f"\nError saving redacted document: {e}")
        return None

def generate_dependency_files(doc_path):
    """Extract and generate dependency files referenced in an Exec Doc."""
    if not os.path.isfile(doc_path):
        print(f"\nError: The file {doc_path} does not exist.")
        return False

    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
    except Exception as e:
        print(f"\nError reading document: {e}")
        return False

    # Directory where the doc is located
    doc_dir = os.path.dirname(doc_path) or "."
    
    print("\nAnalyzing document for dependencies...")
    
    # Enhanced prompt for better dependency file identification
    dependency_prompt = """Analyze this Exec Doc and identify ANY files that the user is instructed to create.
    
    Look specifically for:
    1. Files where the doc says "Create a file named X" or similar instructions
    2. Files that are referenced in commands (e.g., kubectl apply -f filename.yaml)
    3. YAML files (configuration, templates, manifests)
    4. JSON files (configuration, templates, API payloads)
    5. Shell scripts (.sh files)
    6. Any other files where content is provided and meant to be saved separately

    IMPORTANT: Include files even if their full content is provided in the document!
    If the doc instructs the user to create a file and provides its content, this IS a dependency file.

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
            print("\nNo dependency files identified.")
            return True
        
        # Create each dependency file with type-specific handling
        created_files = []
        for dep in dependency_list:
            filename = dep.get("filename")
            content = dep.get("content")
            file_type = dep.get("type", "").lower()
            
            if not filename or not content:
                continue
                
            file_path = os.path.join(doc_dir, filename)
            
            # Check if file already exists
            if os.path.exists(file_path):
                print(f"\nFile already exists: {filename} - Skipping")
                continue
            
            # Validate and format content based on file type
            try:
                if filename.endswith('.json') or file_type == 'json':
                    # Validate JSON
                    try:
                        parsed = json.loads(content)
                        content = json.dumps(parsed, indent=2)  # Pretty-print JSON
                    except json.JSONDecodeError:
                        print(f"\nWarning: Content for {filename} is not valid JSON. Saving as plain text.")
                
                elif filename.endswith('.yaml') or filename.endswith('.yml') or file_type == 'yaml':
                    # Validate YAML
                    try:
                        parsed = yaml.safe_load(content)
                        content = yaml.dump(parsed, default_flow_style=False)  # Pretty-print YAML
                    except yaml.YAMLError:
                        print(f"\nWarning: Content for {filename} is not valid YAML. Saving as plain text.")
                
                elif filename.endswith('.sh') or file_type == 'shell':
                    # Ensure shell scripts are executable
                    is_executable = True
                
                # Write the file
                with open(file_path, "w") as f:
                    f.write(content)
                
                # Make shell scripts executable if needed
                if (filename.endswith('.sh') or file_type == 'shell') and is_executable:
                    os.chmod(file_path, os.stat(file_path).st_mode | 0o111)  # Add executable bit
                
                created_files.append(filename)
            except Exception as e:
                print(f"\nError creating {filename}: {e}")
        
        if created_files:
            print(f"\nCreated {len(created_files)} dependency files: {', '.join(created_files)}")
        else:
            print("\nNo new dependency files were created.")
        
        return True
    except Exception as e:
        print(f"\nError generating dependency files: {e}")
        print("\nResponse from model was not valid JSON. Raw response:")
        # print(response.choices[0].message.content[:500] + "..." if len(response.choices[0].message.content) > 500 else response.choices[0].message.content)
        return False
    
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

def log_data_to_csv(data):
    file_exists = os.path.isfile('execution_log.csv')
    with open('execution_log.csv', 'a', newline='') as csvfile:
        fieldnames = ['Timestamp', 'Type', 'Input', 'Output', 'Number of Attempts', 'Errors Encountered', 'Execution Time (in seconds)', 'Success/Failure']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

def generate_title_from_description(description):
    """Generate a title for the Exec Doc based on the workload description."""
    print("\nGenerating title for your Exec Doc...")
    
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
        print(f"\nGenerated title: {title}")
        return title
    except Exception as e:
        print(f"\nError generating title: {e}")
        return "Azure Executable Documentation Guide"  # Default fallback title

def perform_security_check(doc_path):
    """Perform a comprehensive security vulnerability check on an Exec Doc."""
    if not os.path.isfile(doc_path):
        print(f"\nError: The file {doc_path} does not exist.")
        return None

    try:
        with open(doc_path, "r") as f:
            doc_content = f.read()
    except Exception as e:
        print(f"\nError reading document: {e}")
        return None

    # Create output filename
    doc_name = os.path.splitext(os.path.basename(doc_path))[0]
    output_file = f"{doc_name}_security_report.md"

    print("\nPerforming comprehensive security vulnerability analysis...")
    
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
        print(f"\nSecurity analysis report saved to: {output_file}")
        return output_file
    except Exception as e:
        print(f"\nError saving security report: {e}")
        return None
    
def main():
    print("\nWelcome to ADA - AI Documentation Assistant!")
    print("\nThis tool helps you write and troubleshoot Executable Documents efficiently!")
    print("\nPlease select one of the following options:")
    print("  1. Enter path to markdown file for conversion to Exec Doc")
    print("  2. Describe workload to generate a new Exec Doc")
    print("  3. Add descriptions to a shell script as an Exec Doc")
    print("  4. Redact PII from an existing Exec Doc")
    print("  5. Perform security vulnerability check on an Exec Doc")
    choice = input("\nEnter the number corresponding to your choice: ")

    if choice == "1":
        user_input = input("\nEnter the path to your markdown file: ")
        if not os.path.isfile(user_input) or not user_input.endswith('.md'):
            print("\nInvalid file path or file type. Please provide a valid markdown file.")
            sys.exit(1)
        input_type = 'file'
        with open(user_input, "r") as f:
            input_content = f.read()
            input_content = f"CONVERT THE FOLLOWING EXISTING DOCUMENT INTO AN EXEC DOC. THIS IS A CONVERSION TASK, NOT CREATION FROM SCRATCH. DON'T EXPLAIN WHAT YOU ARE DOING BEHIND THE SCENES INSIDE THE DOC. PRESERVE ALL ORIGINAL CONTENT, STRUCTURE, AND NARRATIVE OUTSIDE OF CODE BLOCKS:\n\n{input_content}"
            if input("\nMake new files referenced in the doc for its execution? (y/n): ").lower() == 'y':
                generate_dependency_files(user_input) 
    elif choice == "2":
        user_input = input("\nDescribe your workload for the new Exec Doc: ")
        if not user_input:
            print("\nInvalid input. Please provide a workload description.")
            sys.exit(1)
        input_type = 'workload_description'
        input_content = user_input
    elif choice == "3":
        user_input = input("\nEnter the path to your shell script: ")
        context = input("\nProvide additional context for the script (optional): ")
        if not os.path.isfile(user_input):
            print("\nInvalid file path. Please provide a valid shell script.")
            sys.exit(1)
        input_type = 'shell_script'
        output_file = generate_script_description(user_input, context)
        remove_backticks_from_file(output_file)
        sys.exit(0)
    elif choice == "4":
        user_input = input("\nEnter the path to your Exec Doc for PII redaction: ")
        if not os.path.isfile(user_input) or not user_input.endswith('.md'):
            print("\nInvalid file path or file type. Please provide a valid markdown file.")
            sys.exit(1)
        input_type = 'pii_redaction'
        output_file = redact_pii_from_doc(user_input)
        remove_backticks_from_file(output_file)
        sys.exit(0)
    elif choice == "5":
        user_input = input("\nEnter the path to your Exec Doc for security analysis: ")
        if not os.path.isfile(user_input) or not user_input.endswith('.md'):
            print("\nInvalid file path or file type. Please provide a valid markdown file.")
            sys.exit(1)
        input_type = 'security_check'
        output_file = perform_security_check(user_input)
        if output_file:
            print(f"\nSecurity analysis complete. Report saved to: {output_file}")
        sys.exit(0)
    else:
        print("\nInvalid choice. Exiting.")
        sys.exit(1)

    install_innovation_engine()

    max_attempts = 11
    attempt = 1
    if input_type == 'file':
        output_file = f"{os.path.splitext(os.path.basename(user_input))[0]}_converted.md"
    else:
        output_file = f"{generate_title_from_description(user_input)}_ai_generated.md"

    start_time = time.time()
    errors_encountered = []

    while attempt <= max_attempts:
        if attempt == 1:
            print(f"\n{'='*40}\nAttempt {attempt}: Generating Exec Doc...\n{'='*40}")
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_content}
                ]
            )
            output_file_content = response.choices[0].message.content
            with open(output_file, "w") as f:
                f.write(output_file_content)
        else:
            print(f"\n{'='*40}\nAttempt {attempt}: Generating corrections based on error...\n{'='*40}")
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_content},
                    {"role": "assistant", "content": output_file_content},
                    {"role": "user", "content": f"The following error(s) have occurred during testing:\n{errors_text}\n{additional_instruction}\n\nPlease carefully analyze these errors and make necessary corrections to the document to prevent them from happening again. Try to find different solutions if the same errors keep occurring. \nGiven that context, please think hard and don't hurry. I want you to correct the converted document in ALL instances where this error has been or can be found. Then, correct ALL other errors apart from this that you see in the doc. ONLY GIVE THE UPDATED DOC, NOTHING ELSE"}
                ]
            )
            output_file_content = response.choices[0].message.content
            with open(output_file, "w") as f:
                f.write(output_file_content)

        remove_backticks_from_file(output_file)

        print(f"\n{'-'*40}\nRunning Innovation Engine tests...\n{'-'*40}")
        try:
            result = subprocess.run(["ie", "test", output_file], capture_output=True, text=True, timeout=660)
        except subprocess.TimeoutExpired:
            print("\nThe 'ie test' command timed out after 11 minutes.")
            errors_encountered.append("The 'ie test' command timed out after 11 minutes.")
            attempt += 1
            continue  # Proceed to the next attempt
        if result.returncode == 0:
            print(f"\n{'*'*40}\nAll tests passed successfully.\n{'*'*40}")
            success = True
            print(f"\n{'='*40}\nProducing Exec Doc...\n{'='*40}")
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
            with open(output_file, "w") as f:
                f.write(output_file_content)
            remove_backticks_from_file(output_file)
            break
        else:
            print(f"\n{'!'*40}\nTests failed. Analyzing errors...\n{'!'*40}")
            error_log = get_last_error_log()
            errors_encountered.append(error_log.strip())
            errors_text = "\n\n ".join(errors_encountered)
            
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
            
            print(f"\nError: {error_log.strip()}")
            print(f"\n{'!'*40}\nApplying an error troubleshooting strategy...\n{'!'*40}")
            attempt += 1
            success = False

    if attempt > max_attempts:
        print(f"\n{'#'*40}\nMaximum attempts reached without passing all tests.\n{'#'*40}")

    end_time = time.time()
    execution_time = end_time - start_time

    log_data = {
        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'Type': input_type,
        'Input': user_input,
        'Output': output_file,
        'Number of Attempts': attempt-1,
        'Errors Encountered': "\n\n ".join(errors_encountered),
        'Execution Time (in seconds)': execution_time,
        'Success/Failure': "Success" if success else "Failure"
    }

    log_data_to_csv(log_data)

    print(f"\nThe updated file is stored at: {output_file}\n")

if __name__ == "__main__":
    main()
