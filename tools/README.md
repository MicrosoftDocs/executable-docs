# ADA - AI Documentation Assistant

Welcome to ADA! This tool helps you convert documents and troubleshoot errors efficiently using Azure OpenAI's Large Language Models and the Azure Innovation Engine.

## Features

- Converts source markdown files to Exec Docs with proper formatting.
- Generates new Exec Docs from workload descriptions with auto-generated titles.
- Creates documentation for shell scripts while preserving the original code.
- Redacts Personally Identifiable Information (PII) from Exec Doc result blocks.
- Automatically identifies and generates dependency files referenced in documents.
- Performs comprehensive security vulnerability analysis on Exec Docs.
- Runs tests on the converted document using the Innovation Engine.
- Logs execution data to a CSV file for analytics.

## Prerequisites

- Python 3.6 or higher
- An Azure OpenAI API key
- Required Python packages: `openai`, `azure-identity`, `requests`, `pyyaml`

## Installation

1. Clone the repository:
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2. Install the required Python packages:
    ```bash
    pip install openai azure-identity requests pyyaml
    ```

3. Ensure you have the Azure OpenAI API key and endpoint set as environment variables:
    ```bash
    export AZURE_OPENAI_API_KEY=<your-azure-openai-api-key>
    export AZURE_OPENAI_ENDPOINT=<your-azure-openai-endpoint>
    ```

    To obtain an Azure OpenAI API key and endpoint, follow these steps:

    1. **Sign in to the Azure Portal**:
    - Navigate to [https://portal.azure.com](https://portal.azure.com) and log in with your Azure credentials.

    2. **Create an Azure OpenAI Resource**:
    - In the Azure Portal, select "Create a resource".
    - Search for "Azure OpenAI" and select it from the results.
    - Click "Create" to begin the setup process.
    - Fill in the required details:
        - **Subscription**: Choose your Azure subscription.
        - **Resource Group**: Select an existing resource group or create a new one.
        - **Region**: Choose the region closest to your location.
        - **Name**: Provide a unique name for your Azure OpenAI resource.
        - **Pricing Tier**: Select the appropriate pricing tier (e.g., Standard S0).
    - Click "Review + create" and then "Create" to deploy the resource.

    3. **Deploy a Model in Azure AI Studio**:
    - After creating your Azure OpenAI resource, navigate to the **Overview** page of your resource.
    - Click on "Go to Azure AI Studio" to open the Azure AI Studio interface.
    - In Azure AI Studio, select "Deployments" from the left-hand menu.
    - Click "Deploy model" and choose `gpt-4o` from the Azure OpenAI collection.
    - Provide a deployment name and configure any additional settings as needed.
    - Click "Deploy" to deploy the model.

    4. **Access Keys and Endpoint**:
    - Once the deployment is complete, return to your Azure OpenAI resource in the Azure Portal.
    - In the left-hand menu under "Resource Management", select "Keys and Endpoint".
    - Here, you'll find your **Endpoint** URL and two **API keys** (`KEY1` and `KEY2`).
    - Copy the endpoint URL and one of the API keys; you'll need them to authenticate your API calls.

    5. **Set Environment Variables in Linux**:
    - Open your terminal.
    - Edit the [.bashrc](http://_vscodecontentref_/2) file using a text editor, such as `nano`:
        ```bash
        nano ~/.bashrc
        ```
    - Add the following lines at the end of the file, replacing `<your_api_key>` and `<your_endpoint>` with the values you obtained earlier:
        ```bash
        export AZURE_OPENAI_API_KEY="<your_api_key>"
        export AZURE_OPENAI_ENDPOINT="<your_endpoint>"
        ```
    - Save and exit the editor (`Ctrl + X`, then `Y`, and `Enter` for nano).
    - Apply the changes by sourcing the [.bashrc](http://_vscodecontentref_/3) file:
        ```bash
        source ~/.bashrc
        ```
    - To verify that the environment variables are set correctly, you can use the `printenv` command:
        ```bash
        printenv | grep AZURE_OPENAI
        ```
        This should display the variables you just set.

    By following these steps, you'll have your Azure OpenAI API key and endpoint configured, a model deployed, and your environment variables set up in a Linux environment, ready for integration into your applications.

    For a visual walkthrough of creating an Azure OpenAI resource and deploying a model, you might find the following video helpful:
 
## Usage

1. Run the script:
    ```bash
    python ada.py
    ```

2. Choose from the available options:
   - Option 1: Convert an existing markdown file to an Exec Doc
   - Option 2: Describe a workload to generate a new Exec Doc
   - Option 3: Add descriptions to a shell script as an Exec Doc
   - Option 4: Redact PII from an existing Exec Doc
   - Option 5: Perform security vulnerability check on an Exec Doc

3. Follow the prompts to provide the required information:
   - For file conversion, provide the path to your input file
   - For workload descriptions, describe your intended workload in detail
   - For shell script documentation, provide the path to your script and optional context
   - For PII redaction, provide the path to your Exec Doc
   - For security checks, provide the path to your Exec Doc

4. The tool will process your request based on the selected option:
   - For options 1 and 2, it will convert or create an Exec Doc and run tests using Innovation Engine
   - For options 3, 4, and 5, it will generate the requested output and save it to a file

5. For document conversion or creation, if the tests pass successfully, the final document will be saved with proper formatting.

## Script Workflow

1. **Initialization**: The script initializes the Azure OpenAI client and checks for required packages.

2. **Option Selection**: Prompts the user to select from available options for document processing.

3. **Input Collection**: Collects necessary inputs based on the selected option.

4. **Processing Based on Option**:
   - **Convert Markdown**: Converts an existing markdown file to an Exec Doc
   - **Generate New Doc**: Creates an Exec Doc from a workload description
   - **Document Script**: Adds detailed explanations to a shell script
   - **Redact PII**: Removes personally identifiable information from result blocks
   - **Security Check**: Performs comprehensive security analysis

5. **For Document Conversion and Generation**:
   - Install Innovation Engine if needed
   - Process the document using Azure OpenAI's model
   - Run tests on the document using Innovation Engine
   - If tests fail, generate troubleshooting steps and attempt corrections
   - If tests pass, finalize the document

6. **Final Output**: Saves the processed document and provides the file path.

7. **Dependency Generation**: Optionally identifies and creates dependency files referenced in the document.

8. **Logging**: Logs execution data to `execution_log.csv`.

## Logging

The script logs the following data to `execution_log.csv`:

- Timestamp: The date and time when the script was run.
- Type: The type of processing performed (file conversion, workload description, etc.).
- Input: The path to the input file or the workload description.
- Output: The path to the output file.
- Number of Attempts: The number of attempts made to generate a successful document.
- Errors Encountered: A summary of errors encountered during the process.
- Execution Time (in seconds): The total time taken to run the script.
- Success/Failure: Whether the script successfully generated a document without errors.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## Acknowledgments

- [OpenAI](https://openai.com/)
- [Azure](https://azure.microsoft.com/)