# Overview

Executable Documentation (a.k.a **Exec Docs**) is a novel approach to simplify the evaluation and adoption of solutions provided with a CLI tool, such as Azure services. 

It achieves this by providing one-click and interactive learning experiences for deploying recommended architectures on Azure. 

These experiences utilize [Innovation Engine](https://github.com/Azure/InnovationEngine/tree/main), an open-source project that amplifies standard markdown language such that it can be executed step-by-step in an educational manner and tested via automated CI/CD pipelines.   

## How to Write an Exec Doc

Follow these steps to write an Exec Doc either by converting an existing Azure Doc or from scratch _(read the Notes in any step for more information)_:

1. Set up [Windows Subsystem for Linux (WSL)](https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-vscode) locally in your IDE such as VS Code and use the Linux terminal while writing the Exec Doc.

    >**Note:** Innovation Engine is a Linux-based tool and hence it is recommended to write Exec Docs in a Linux environment. Most doc authors use WSL in VS Code to write Exec Docs.

2. Set up the relevant repository in your local machine. This example covers the **azure-docs-pr** repo.
    
    - Get access to the relevant repo in [MicrosoftDocs](https://github.com/MicrosoftDocs) in case it is private and/or you do not have access to it. 
    
    - Fork the [MicrosoftDocs/azure-docs-pr](https://github.com/MicrosoftDocs/azure-docs-pr) repo, which is where docs changes are made internally. Your fork URL would contain the following within: `<your_github_username>/azure-docs-pr`. [Guidance on how to fork a GitHub repo](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo)  

    - Clone a copy of your fork to your local machine. [Guidance on how to clone a forked GitHub repo](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo#cloning-your-forked-repository)

    - Make any changes to an existing/new Exec Doc in an IDE, such as VS Code. 
    
    - If you are converting an Azure Doc to Exec Doc and have a hard time finding the Azure doc in your fork, click the pencil icon in the public Azure doc and use the resultant filepath to find it in your fork.

    >**Note:** Push all changes to your fork as necessary
    
    >**Note:** You are not confined to use VS Code in WSL. You can use any IDE that supports markdown language. However, VS Code is recommended as it is the most common setup among doc authors.

3. Check if all prerequisites below are met before writing the Exec Doc. ***If any of the below prerequisites are not met, then either add them to the Exec Doc in progress or find another valid doc that can fulfill them. Do not move to the next step until then***

    - Ensure your Exec Doc is a markdown file. 

        >**Note:** If you are converting an existing Azure Doc to an Exec Doc, you can either find it in your fork or copy the raw markdown content of the Azure Doc into a new markdown file in your local repo (this can be found by clicking "Raw" in the GitHub view of the Azure Doc). 

    - Ensure your Exec Doc is written with the LF line break type.

        **Example:** 

        ![LF VSCode](https://github.com/MicrosoftDocs/executable-docs/assets/146123940/3501cd38-2aa9-4e98-a782-c44ae278fc21)

        >**Note:** The button will appear according to the IDE you are using. For the VS Code IDE, you can check this by clicking on the LF/CLRF button at the bottom right corner of the screen.

    - Ensure all files that your Exec Doc references live under the same parent folder as your Exec Doc

        **Example:** 

        If your Exec Doc ***my-exec-doc.md*** references a script file ***my-script.yaml*** within, the script file should be in the same folder as the Exec Doc. 

        ```bash 
        ├── master-folder
        │   └── parent-folder
        │       ├── my-exec-doc.md 
        │       └── my-script.yaml 
        ``` 

    - Ensure that the Exec Doc contains at least 1 code block and every input code block's type in the Exec Doc is taken from this list: 
    
        - bash 
        - azurecli
        - azure-cli-interactive 
        - azurecli-interactive  

        **Example:** 

        ```bash 
        az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION 
        ``` 

        >**Note:** Code blocks are used to provide examples, commands, or other code snippets in Exec Docs. They are distinguished by a triple backtick (```) at the start and end of the block.

        >**Note:** This rule does not apply to output code blocks, which are used to display the results of commands, scripts, or other operations. These blocks help in illustrating what the expected output should look like. They include, but are not limited to, the following types: _output, json, yaml, console, text, and log._

        >**Note:** While Innovation Engine can _parse_ a code block of any type, given its current features, it can only _execute_ code blocks of the types above. So, it is important to ensure that the code blocks in your Exec Doc are of the types above. 

    - Ensure there is at least one h1 heading in the Exec Doc, denoted by a single hash (#) at the start of the line. 

        **Example:** 

        ```markdown 
        # Quickstart: Deploy an Azure Kubernetes Service (AKS) cluster using Azure CLI 
        ``` 

        >**Note:** Headings are used to organize content in a document. The number of hashes indicates the level of the heading. For example, a single hash (#) denotes an h1 heading, two hashes (##) denote an h2 heading, and so on. Innovation Engine uses headings to structure the content of an Exec Doc and to provide a clear outline of the document's contents

4. Appropriately add metadata at the start of the Exec Doc. Here are some mandatory fields:

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

5. Declare environment variables _as they are being used_ in the Exec Doc using the export command. This is a best practice to ensure that the variables are accessible throughout the doc. \
    \
    **Example (BEFORE - ENVIRONMENT VARIABLES SECTION AT TOP, NOT DECLARED AS USED):** 
    
    ### Environment Variables Section

    We are at the start of the Exec Doc and are declaring environment variables that will be used throughout the doc. 

    ```bash
    export REGION="eastus"
    ```
    
    ### Test Section

    We are now in the middle of the Exec Doc and we will create a resource group.

    ```bash
    az group create --name "MyResourceGroup" --location $REGION
    ```
    \
    **Example (AFTER - ENVIRONMENT VARIABLES DECLARED AS USED):** 
    
    ### Test Section

    We are in the middle of the Exec Doc and we will create a resource group. 

    ```bash  
    export REGION="eastus"
    export MY_RESOURCE_GROUP_NAME="MyResourceGroup"
    az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
    ``` 

    >**Note:** Environment variables are dynamic values that store configuration settings, system paths, and other information that can be accessed throughout a doc. By using environment variables, you can separate configuration details from the code, making it easier to manage and deploy applications in an environment like Exec Docs. 
    
    >**Note:** If you are converting an existing Azure Doc to an Exec Doc and the Azure Doc does not environment variables at all, it is an Exec Doc writing best practice to add them. Additionally, if the Azure Doc has environment variables but they are not declared as they are being used, it is recommended to update them to follow this best practice. 

    >**Note:** Don't have any spaces around the equal sign when declaring environment variables.

6. Add a random suffix at the end of _relevant_ environment variable(s). The example below shows how this would work when you are creating a resource group.

    **Example:** 

    ```bash  
    export RANDOM_SUFFIX=$(openssl rand -hex 3)
    export REGION="eastus"
    az group create --name "MyResourceGroup$RANDOM_SUFFIX" --location $REGION
    ```

    >**Note:** A major component of Exec Docs is automated infrastructure deployment on the cloud. While testing the doc, if you do not update relevant environment variable names, the doc will fail when run/executed more than once as the resource group or other resources will already exist from the previous runs. \
    \
    Hence, it is important to add a random suffix to variables that are likely to be unique for each deployment, such as resource group names, VM names, and other resources that need to be uniquely identifiable. However, do not add a random suffix to variables that are constant or environment-specific, such as region, username, or configuration settings that do not change between deployments. 
    
    >**Note:** You can generate your own random suffix or use the one provided in the example above. The `openssl rand -hex 3` command generates a random 3-character hexadecimal string. This string is then appended to the resource group name to ensure that the resource group name is unique for each deployment.

7. Add result block(s) below code block(s) that you would want Innovation Engine to verify i.e. code block(s) which produce an output in the terminal that is relevant to benchmark against. Follow these steps when adding a result block below a code block for the first time:

    - Check if the code block does not already have a result block below it. If it does, ensure the result block is formatted correctly, as shown in the example below, and move to the next code block.
    - [Open Azure Cloudshell](https://ms.portal.azure.com/#cloudshell/) 
    - **[Optional]**: Set your active subscription to the one you are using to test Exec Docs. Ideally, this sub should have permissions to run commands in your tested Exec Docs. Run the following command: 

        ```bash
        az account set --subscription "<subscription name or id>"
        ``` 
    - Run the command in the code block in cloudshell. If it returns an output that you would want Innovation Engine to verify, copy the output from the terminal and paste it in a new code block below the original code block. The way a result code block should be formatted has been shown below, in this case for the command `az group create --name "MyResourceGroup123" --location eastus`.

        **Example:**
        ```markdown            
            Results: 

            <!-- expected_similarity=0.3 --> 

            ```JSON 
            {
                "id": "/subscriptions/abcabc-defdef-ghighi-jkljkl/resourceGroups/MyResourceGroup123",
                "location": "eastus",
                "managedBy": null,
                "name": "MyResourceGroup123",
                "properties": {
                    "provisioningState": "Succeeded"
                },
                "tags": null,
                "type": "Microsoft.Resources/resourceGroups"
            }
            ```
        ```
    - If you run into an error while executing a code block or the code block is running in an infinite loop, update the Exec Doc based on the error stack trace, restart/clear Cloudshell, and rerun the command block(s) from the start until you reach that command block. This is done to override any potential issues that may have occurred during the initial run. More guidance is given in the [FAQ section](#frequently-asked-questions-faqs) below.
    
    >**Note:** In Exec Docs, result blocks are distinguished by a custom expected_similarity comment tag followed by a code block. These result blocks indicate to Innovation Engine what the minimum degree of similarity should be between the actual and the expected output of a code block (one which returns something in the terminal that is relevant to benchmark against). Learn More: [Result Blocks](https://github.com/Azure/InnovationEngine/blob/main/README.md#result-blocks).
    
    >**Note:** The expected similarity value is a floating point number between 0 and 1 which specifies how closely the true output needs to match the template output given in the results block - 0 being no similarity, 1 being an exact match. If you are uncertain about the value, it is recommended to set the expected similarity to 0.3 to account for small variations. Once you have run the command multiple times and are confident that the output is consistent, you can adjust the expected similarity value accordingly.

    >**Note:** If you are executing a command in Cloudshell which references a yaml/json file, you would need to create the yaml/json file in Cloudshell and then run the command. This is because Cloudshell does not support the execution of commands that reference local files. You can add the file via the cat command or by creating the file in the Cloudshell editor. 

    >**Note:** Result blocks are not required but recommended for commands that return some output in the terminal. They help Innovation Engine verify the output of a command and act as checkpoints to ensure that the doc is moving in the right direction.

8. Ensure result block(s) have all the PII (Personally Identifiable Information) stricken out from them and replaced with x’s. 

    **Example:** 

    ```markdown
        Results: 

        <!-- expected_similarity=0.3 --> 

        ```JSON 
        { 
            "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxx",
                "location": "eastus",
                "managedBy": null,
                "name": "MyResourceGroupxxx",
                "properties": {
                    "provisioningState": "Succeeded"
                },
                "tags": null,
                "type": "Microsoft.Resources/resourceGroups" 
        } 
        ```
    ```

    >**Note:** The number of x's used to redact PII need not be the same as the number of characters in the original PII. Furthermore, it is recommended not to redact the key names in the output, only the values containing the PII (which are usually strings).
    
    >**Note:** Redacting PII from the output helps protect sensitive information from being inadvertently shared or exposed. This is crucial for maintaining privacy, complying with data protection regulations, and furthering the company's security posture. \
    \
    Here are some examples of PII in result blocks: Unique identifiers for resources, Email Addresses, Phone Numbers, IP Addresses, Credit Card Numbers, Social Security Numbers (SSNs), Usernames, Resource Names, Subscription IDs, Resource Group Names, Tenant IDs, Service Principal Names, Client IDs, Secrets and Keys.

9. If you are converting an existing Azure Doc to an Exec Doc and if the existing doc contains a "Delete Resources" (or equivalent section) comprising resource/other deletion command(s), remove the code blocks in that section or remove that section entirely 

    >**Note:** We remove commands from this section ***only*** in Exec Docs. This is because Innovation Engine executes all relevant command(s) that it encounters, inlcuding deleting the resources. That would be counterproductive to automated deployment of cloud infrastructure

10. Test the Exec Doc using Innovation Engine (IE) inside Azure Cloudshell 

    - [Open Azure Cloudshell](https://ms.portal.azure.com/#cloudshell/) 
    - **[Optional]**: Set your active subscription to the one you are using to test Exec Docs. Ideally, this sub should have permissions to run commands in your tested Exec Docs. Run the following command: 

        ```bash
        az account set --subscription "<subscription name or id>"
        ``` 
    - Install and set up the latest stable build of [Innovation Engine](https://github.com/Azure/InnovationEngine) (currently v0.1.3). Run the following command (ensure it is all run in one line): 
        ```bash
        curl –Lks https://raw.githubusercontent.com/Azure/InnovationEngine/v0.1.3/scripts/install_from_release.sh | /bin/bash -s -- v0.1.3 
        ``` 
    - Test your (Work In Progress) Exec Doc using Innovation Engine. Run the following command **(this command will automatically delete the resources at the end of the test)**: 

        ```bash
        ie test <URL to the raw Exec Doc markdown file>
        ``` 

        >**Note:** The URL to the raw Exec Doc markdown can be found by clicking "Raw" in the GitHub view of the Exec Doc. Also, ensure the GitHub repo is public otherwise Innovation Engine will not be able to access the raw markdown file.

        >**Note:** You can also test the Exec Doc by running the command "ie execute <URL to the raw Exec Doc markdown file>". This command will execute the code blocks in the Exec Doc but will not delete the resources at the end of the test. [Guidance on Innovation Engine's modes of operations](https://github.com/Azure/InnovationEngine?tab=readme-ov-file#modes-of-operation)
    
    - If you run into any errors, update the source doc in your upstream repo accordingly and retest it using Innovation Engine. For more guidance on troubleshooting errors, refer to the [FAQ section](#frequently-asked-questions-faqs) below. 

    >**Note:** Some code blocks may take a while to execute, especially if they are creating resources in Azure. You can finish other tasks while waiting for the code block to complete in the active Cloudshell window.

11. Submit and review the Exec Doc in the upstream repo once the doc passes all Innovation Engine tests
    - Create a PR in GitHub once the Exec Doc is ready to be uploaded, pointing to the upstream repo from your fork. [Guidance on creating a PR in GitHub from a fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork)
    - Assign the original Exec Doc author (if it is not you) as a reviewer to the PR. In most cases, this assignment should happen automatically and should also include a reviewer from the Skilling team.
    - Add the comment ***#sign-off***  in the PR comments section once the Exec Doc is successfully reviewed. This will trigger the automated pipeline to merge the PR into the public repo.

12. Test the Exec Doc on the Azure Portal test environment once the PR is merged at source. The steps below explain the process with an example [Exec Doc](https://learn.microsoft.com/en-us/azure/aks/learn/quick-kubernetes-deploy-cli) that deploys an Azure Kubernetes Service (AKS) cluster using Azure CLI.
    - The [executable-docs repo](https://github.com/MicrosoftDocs/executable-docs/tree/main) is used to render the experience on Portal. A GitHub Action will sync your published Exec Doc in the executable-docs repo and create a PR to merge it in its main branch. Wait until you receive a notification from that PR: it will tag you and request you to test your Exec Doc before the merge happens

        **Example:**
      
      ![PR Template for Exec Docs Testing](https://github.com/user-attachments/assets/860e6153-5f95-4ebc-b774-2f30ef3a6219)
        
    - Click the URL in the PR description, which will take you to the test environment. Locate your Exec Doc from the cards page using doc metadata, etc.
    
        **Example:**

      ![Exec Docs Test Environment ](https://github.com/user-attachments/assets/8ab578a7-8b2f-4099-a34a-8824ba6bf50b)

    - Click either **Quick deployment** or **Guided deployment** and follow the instructions to test the Exec Doc
    - If the test fails, update the source doc in your upstream repo so that the GitHub action can sync the updated doc and allow you to test it. 
    
        >**Note:** Refer to the [FAQ section](#frequently-asked-questions-faqs) below for troubleshooting tips. If you are unable to resolve the issue, reach out to the [Exec Docs Team](#points-of-contact-for-exec-docs) for help.
    - Once the test passes, send a screenshot of the post-deployment success page in the PR where you got tagged to test the Exec Doc. An example of the screenshot has been given below. After this gets approved, the PR will be merged into the main branch

        **Example:**

      ![Post Deployment Success Page Test Environment](https://github.com/user-attachments/assets/f002cd97-6bab-41a9-8c83-227e9b2da9cf)

13. Add the ***Deploy to Azure*** button to the source doc published on [Microsoft Learn](https://learn.microsoft.com/en-us/) or elsewhere once the PR is merged in the [executable-docs repo](https://github.com/MicrosoftDocs/executable-docs/tree/main). Follow these steps to add the button:

    - Get the file path of your Exec Doc _relative_ to MicrosoftDocs/other GitHub organization. 
    
        **Example:** 

        If your source Exec Doc is located at `MicrosoftDocs/azure-docs/articles/aks/quick-kubernetes-deploy-cli.md` file, the file path for this purpose would be `azure-docs/articles/aks/quick-kubernetes-deploy-cli.md`

    - Add the code snippet (template given below) before the doc content starts (and after the table of contents if there is one). Replace all ***'/'*** signs in the file path with ***%2f*** for URL. So, for the example above, the file path would be `azure-docs%2farticles%2faks%2fquick-kubernetes-deploy-cli.md`

        **Deeplink Template:**
        ```markdown
        [![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://ms.portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/isLearnMode~/true/referer/docs/tutorialKey/<add_file_path_of_Exec_Doc>)
        ```

        **Deeplink for Example Exec Doc:**
        ```markdown
        [![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://ms.portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/isLearnMode~/true/referer/docs/tutorialKey/azure-docs%2farticles%2faks%2fquick-kubernetes-deploy-cli.md)
        ```

        **Example of Button in Live Exec Doc:**
        
      ![Deploy to Azure Button on Live Exec Doc](https://github.com/user-attachments/assets/3bfc1df7-8e33-4f22-b070-c365a6c3e917)

        >**Note:** The ***Deploy to Azure*** button is a clickable button that allows users to deploy the architecture described in the Exec Doc directly to their Azure subscription. This button is added to the source doc published on Microsoft Learn or elsewhere.

        >**Note:** The reason why we replace the '/' signs with '%2f' is because the '/' sign is a reserved character in URLs and needs to be encoded as '%2f' to be used in a URL.

## Current Exec Docs Experience

Exec Docs is a deployment vehicle that has different entry points into the experience. Here are the current entry points:

- [MS Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/quick-create-cli): A public facing Exec Doc on Microsoft Learn that enables users to create a Linux VM and SSH into it.

- [GitHub Repository](https://github.com/MicrosoftDocs/executable-docs/tree/main/scenarios): The GitHub repository where the current exec docs are stored.

- [Portal CLI Workloads](https://ms.portal.azure.com/#view/Microsoft_Azure_CloudNative/TutorialsPage.ReactView): The Azure portal page where the current exec docs are displayed as cards.

## Exec Docs Publishing Pipeline

![Exec Docs Pipeline](https://github.com/user-attachments/assets/8102b631-634a-498c-a3a5-c099380acb07)

## Frequently Asked Questions (FAQs)

## Points of Contact for Exec Docs

- PM for Exec Docs E2E Experience: [Naman Parikh](mailto:namanparikh@microsoft.com)
- PM for Exec Docs Portal Experience: [Varun Desai](mailto:varun.desai@microsoft.com)
- PM for Innovation Engine: [Mitchell Bifeld](mailto:mbifeld@microsoft.com)
- Devs for Exec Docs: [PJ Singh](mailto:pjsingh@microsoft.com), [Aria Amini](mailto:ariaamini@microsoft.com), [Abhishek Bhombore](mailto:abhishek.bhombore@microsoft.com)
- Dev for Innovation Engine: [Vincenzo Marcella](mailto:vmarcella@microsoft.com), [Rahul Gupta](mailto:guptar@microsoft.com)

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
