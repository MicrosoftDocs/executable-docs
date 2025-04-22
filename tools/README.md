# ADA - AI Documentation Assistant

ADA (AI Documentation Assistant) helps you create, convert, and manage Executable Documents efficiently using Azure OpenAI and Innovation Engine.

## Features

- **Convert to Exec Docs**: Transform existing markdown files to executable documents
- **Generate New Exec Docs**: Create new executable documents from a workload description
- **Reference Integration**: Include content from URLs and local files when generating documents
- **Script Documentation**: Create comprehensive explanations for shell scripts
- **PII Redaction**: Automatically redact sensitive information from result blocks
- **Security Analysis**: Perform comprehensive security vulnerability assessments
- **SEO Optimization**: Enhance document visibility and searchability
- **Centralized Logging**: Track operations across sessions in a global log
- **Docker Support**: Run ADA in an isolated container environment

## Prerequisites

- Python 3.6 or higher
- Azure OpenAI API key and endpoint
- Docker (optional, for containerized usage)

## Installation

### Option 1: Local Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>/tools
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set Azure OpenAI API credentials as environment variables:
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
    - Click "Deploy model" and choose `gpt-4.1` from the Azure OpenAI collection.
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

4. Run ADA:
   ```bash
   python ada.py
   ```

### Option 2: Docker Installation

1. Build the Docker image:
   ```bash
   docker build -t ada-tool .
   ```

2. Run ADA in a Docker container:
   ```bash
   docker run -it --rm \
     -e AZURE_OPENAI_API_KEY="your_api_key_here" \
     -e AZURE_OPENAI_ENDPOINT="your_endpoint_here" \
     -v "$(pwd):/app/workspace" \
     -v "$HOME/.azure:/root/.azure" \
     -w /app/workspace \
     ada-tool
   ```

3. Run ADA:
   ```bash
   ./run-ada.sh
   ```
## Usage

1. Select from the available options:
   - Option 1: Convert an existing markdown file to an Exec Doc
   - Option 2: Generate a new Exec Doc from a workload description
   - Option 3: Create descriptions for your shell script
   - Option 4: Redact PII from your Doc
   - Option 5: Perform security analysis on your Doc
   - Option 6: Perform SEO optimization on your Doc

2. Follow the prompts for each option:
   - For file conversion: provide the path to your source file
   - For generating new docs: describe the workload and optionally add reference data
   - For script documentation: provide the path to your script and context
   - For PII redaction: provide the path to your source document
   - For security analysis: provide the path to the document to analyze
   - For SEO optimization: provide the path to the document to optimize

## Output Location

- When generating a new Exec Doc (option 2), ADA creates a dedicated folder for the output
- For all other operations, ADA saves output files in the same directory as the source file
- Execution logs are saved in a centralized log.json file in the script directory

## Data Sources Integration

When generating a new Exec Doc, you can incorporate content from:
- Web URLs (HTML content will be extracted)
- Local files (content will be read directly)

These sources provide additional context for more comprehensive document generation.

## Advanced Features

### Centralized Logging
ADA maintains a comprehensive log of all operations in a centralized log.json file, tracking:
- Document creation and conversion
- Script documentation
- PII redaction
- Security analysis
- SEO optimization
- Success rates and execution times

### Error Resolution System
When errors occur during testing, ADA employs a sophisticated resolution system:
- Analyzes error messages to determine their source
- Uses progressive troubleshooting strategies
- Provides specific fixes for different error patterns
- Remembers previous errors to avoid repetitive solutions

## Requirements

ADA depends on the following Python packages:
- azure-identity>=1.17.1
- beautifulsoup4>=4.12.2
- openai>=1.65.1
- requests>=2.31.0
- requests-kerberos>=0.12.0
- requests-ntlm>=1.1.0
- requests-toolbelt>=1.0.0

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.
