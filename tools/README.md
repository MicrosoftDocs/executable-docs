# ADA - AI Documentation Assistant

Welcome to ADA! This tool helps you convert documents and troubleshoot errors efficiently using OpenAI's Large Language Models and the Azure Innovation Engine.

## Features

- Converts input documents using OpenAI's LLMs.
- Automatically installs required packages and the Innovation Engine.
- Runs tests on the converted document using the Innovation Engine.
- Provides detailed error logs and generates troubleshooting steps.
- Merges code blocks from the updated document with non-code content from the original document.
- Logs execution data to a CSV file for analytics.

## Prerequisites

- Python 3.6 or higher
- An Azure OpenAI API key
- Required Python packages: `openai`, `azure-identity`, `requests`

## Installation

1. Clone the repository:
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2. Install the required Python packages:
    ```bash
    pip install openai azure-identity requests 
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
        - **Name**: Provide a unique name for your OpenAI resource.
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
    - Edit the `.bashrc` file using a text editor, such as `nano`:
        ```bash
        nano ~/.bashrc
        ```
    - Add the following lines at the end of the file, replacing `<your_api_key>` and `<your_endpoint>` with the values you obtained earlier:
        ```bash
        export AZURE_OPENAI_API_KEY="<your_api_key>"
        export AZURE_OPENAI_ENDPOINT="<your_endpoint>"
        ```
    - Save and exit the editor (`Ctrl + X`, then `Y`, and `Enter` for nano).
    - Apply the changes by sourcing the `.bashrc` file:
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

2. Enter the path to the input file or describe your intended workload when prompted.

3. The script will process the file or description, convert it using OpenAI's GPT-4O model, and perform testing using the Innovation Engine.

4. If the tests fail, the script will generate troubleshooting steps and attempt to correct the document.

5. If the tests pass successfully, the script will merge code blocks from the updated document with non-code content from the original document.

6. The final merged document will be saved, and a summary will be displayed.

## Script Workflow

1. **Initialization**: The script initializes the Azure OpenAI client and checks for required packages.

2. **Input File or Workload Description**: Prompts the user to enter the path to the input file or describe their intended workload.

3. **System Prompt**: Prepares the system prompt for the AI model.

4. **File Content or Workload Description**: Reads the content of the input file or uses the provided workload description.

5. **Install Innovation Engine**: Checks if the Innovation Engine is installed and installs it if necessary.

6. **Conversion and Testing**:
    - Attempts to convert the document using OpenAI's GPT-4O model.
    - Runs tests on the converted document using the Innovation Engine.
    - If tests fail, generates troubleshooting steps and attempts to correct the document.

7. **Merge Documents**:
    - If tests pass successfully, merges code blocks from the updated document with non-code content from the original document.
    - Ensures that anything not within code blocks remains unchanged from the original document.

8. **Remove Backticks**: Ensures that backticks are properly handled in the document.

9. **Logging**: Logs execution data to `execution_log.csv`.

10. **Final Output**: Saves the final merged document and provides the path.

## Logging

The script logs the following data to `execution_log.csv`:

- Timestamp: The date and time when the script was run.
- Type: Whether the input was a file or a workload description.
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