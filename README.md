# Overview

Executable Documentation (a.k.a **Exec Docs**) is a novel approach to simplify the evaluation and adoption of solutions provided with a CLI tool, such as Azure services. 

It achieves this by providing one-click and interactive learning experiences for deploying recommended architectures on Azure. 

These experiences utilize [Innovation Engine](https://github.com/Azure/InnovationEngine/tree/main), an open-source project that amplifies standard markdown language such that it can be executed step-by-step in an educational manner and tested via automated CI/CD pipelines.   

## How to Write an Exec Doc

Follow these steps to write an Exec Doc either by converting an existing Azure Doc or from scratch:

1. [Set up Windows Subsystem for Linux (WSL)](https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-vscode) locally in your IDE like VS Code 

2. Set up azure-docs-pr in your local machine 
    
    - Fork the [MicrosoftDocs/azure-docs-pr](https://github.com/MicrosoftDocs/azure-docs-pr) repo, which is where docs changes are made internally. Your fork URL would contain the following within: `<your_github_username>/azure-docs-pr` 

    - Clone a copy of your fork to your local machine 

    - Make any changes to an existing/new Exec Doc in an IDE such as VS Code 

    - Push all changes to your fork as necessary 

3. Ensure your Exec Doc is a markdown file.

    >**Note:** If you are convering an existing Azure Doc to an Exec Doc, you can simply copy the raw markdown content of the Azure Doc into a new markdown file in your local repo

4. Ensure your Exec Doc is written with the LF line break type

    **Example:** 

    ![LF VSCode](https://github.com/MicrosoftDocs/executable-docs/assets/146123940/3501cd38-2aa9-4e98-a782-c44ae278fc21)

    >**Note:** It will appear according to the IDE you are using. For the VS Code IDE, it is given at the bottom right corner of the screen. 

5. Ensure all dependencies that your Exec Doc references live under the same parent folder as your Exec Doc

6. Appropriately add metadata at the start of the Exec Doc. Here are some mandatory fields:

    - title = the title of the Exec Doc
    - description = the description of the Exec Doc
    - ms.topic = what kind of a doc it is e.g. article, blog, etc. 
    - ms.date = the date the Exec Doc was last updated by author 
    - author = author's GitHub username 
    - ms.author = author's username (e.g. Microsoft Alias)
    - ms.custom = comma-separated list of tags to identify the Exec Doc (innovation-engine, linux-related-content are two tags that need to be in this list) 
        
    **Example:** 

    ```yaml 
    ---
    title: 'Quickstart: Deploy an Azure Kubernetes Service (AKS) cluster using Azure CLI' 
    description: Learn how to quickly deploy a Kubernetes cluster and deploy an application in Azure Kubernetes Service (AKS) using Azure CLI. 
    ms.topic: quickstart 
    ms.date: 04/09/2024 
    author: namanparikh 
    ms.author: namanaprikh 
    ms.custom: devx-track-azurecli, mode-api, innovation-engine, linux-related-content 
    ---
    ```

7. Ensure that the Exec Doc contains at least 1 code block   

8. Ensure every code block's type in the Exec Doc is taken from this list: 

    - azurecli 
    - bash 
    - terraform 
    - azure-cli-interactive 
    - azurecli-interactive 
    - console 
    - output 
    - json 
    - yaml 

    **Example:** 

    ```bash 
    az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION 
    ``` 

9. Declare environment variables as they are being used in the Exec Doc and add a random suffix at the end of variable(s) as needed. 

    **Example:** 
    
    ### Test Section

    We are in the middle of the doc and we will now create a resource group on Azure.

    ```bash 
    export RANDOM_ID="$(openssl rand -hex 3)" 
    export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID" 
    az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
    ``` 

    >**Note:** A major component of Exec Docs is automated infrastructure deployment on the Cloud. \
    \
    While testing the doc, if you do not update relevant variable names, when it is run more than once it will fail as the resource group or other resources will already exist. \
    \
    Hence, it is important to add a random suffix to relevant variables like resource group names, VM names, etc. However, don't add one to variables like region, username, etc. whose values are constant. 

    >**Note:** If you are converting an existing Azure Doc to an Exec Doc and the Azure Doc does not contain random suffixes for environment variables or environment variables at all, it is an Exec Doc writing best practice to add them.

10. Add result block(s) below code block(s) whose output you you want Innovation Engine to verify. And ensure it has all the PII (Personal Identifiable Information) stricken out from it and replaced with x’s.

    **Example:** 

    ```markdown
        Results: 

        <!-- expected_similarity=0.3 --> 

        ```JSON 
        { 
            "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAKSResourceGroupxxxxxx", 
            "location": "eastus" 
        } 
        ```
    ```

    >**Note:** In Exec Docs, result blocks are distinguished by a custom expected_similarity comment tag followed by a code block. \
    \
    The expected similarity value is a floating point number between 0 and 1 which specifies how closely the output needs to match the results block. 0 being no similarity, 1 being an exact match. \
    \
    These result blocks indicate to Innovation Engine what the minimum degree of similarity should be between the actual and the expected output of a code block (which returns something in the terminal). Learn More: [Result Blocks](#result-blocks)

11. If you are converting an existing Azure Doc to an Exec Doc and if the existing doc contains a “Delete Resources” (or equivalent section) and contains a command to delete resources within, remove that section entirely. 

    >**Note:** If command blocks are retained, Innovation Engine would execute the command(s) and delete the resources, which is something we do not want 

12. Ensure there is a new line before and after every content heading, subheading, description, and code block 

13. Ensure the section headings are appropriate in the Exec Doc 

    - You can have only one h1 heading 
    - You can have multiple h2s and h3s subheadings  
    - You should not have any h4 headings 

14. Test the Exec Doc using Innovation Engine (IE) inside Azure Cloudshell 

    - [Open Azure Cloudshell](https://ms.portal.azure.com/#cloudshell/) 
    - **[Optional]**: Set your active subscription to the one you are using to test Exec Docs. Ideally, this sub should have permissions to run commands in your tested Exec Docs. Run the following command: 

        ```bash
        az account set --subscription “<subscription name or id>” 
        ``` 
    - Install and set up the latest stable build of Innovation Engine (currently v0.1.3). Run the following command (ensure it is all run in one line): 

        ```bash
        curl –Lks https://raw.githubusercontent.com/Azure/InnovationEngine/v0.1.3/scripts/install_from_release.sh | /bin/bash -s -- v0.1.3 
        ``` 
    - Test your (Work In Progress) Exec Doc using Innovation Engine. Run the following command: 

        ```bash
        ie execute <URL to the raw Exec Doc markdown that lives in GitHub, etc.>
        ``` 

15. Create a PR in GitHub once a doc is ready to be uploaded, pointing to the upstream repo [MicrosoftDocs/azure-docs-pr](https://github.com/MicrosoftDocs/azure-docs-pr) 

16. Assign the original Exec Doc author (if not you) as a reviewer to the PR 

17. Add ***#sign-off***  in the PR comments once the Exec Doc is successfully reviewed  

18. Confirm that the PR has merged into the public repo after (upto) ~24 hours: [MicrosoftDocs/azure-docs](https://github.com/MicrosoftDocs/azure-docs) 

## Current Exec Docs Experience

Exec Docs is a deployment vehicle that has different entry points into the experience. Here are the current entry points:

- [MS Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/quick-create-cli): A public facing Exec Doc on Microsoft Learn that enables users to create a Linux VM and SSH into it.

- [GitHub Repository](https://github.com/MicrosoftDocs/executable-docs/tree/main/scenarios): The GitHub repository where the current exec docs are stored.

- [Portal CLI Workloads](https://ms.portal.azure.com/#view/Microsoft_Azure_CloudNative/TutorialsPage.ReactView): The Azure portal page where the current exec docs are displayed as cards.

## Exec Docs Publishing Pipeline

<img width="1060" alt="Exec Docs Pipeline" src="https://github.com/MicrosoftDocs/executable-docs/assets/146123940/0cf8844e-94c4-48c0-83bd-ee15dff7e132">

## Frequently Asked Questions (FAQs)

## Trademarks

This project may contain trademarks or logos for projects, products, or 
services. Authorized use of Microsoft trademarks or logos is subject to and 
must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must 
not cause confusion or imply Microsoft sponsorship. Any use of third-party 
trademarks or logos are subject to those third-party's policies.

## Microsoft Open Source Code of Conduct
This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
