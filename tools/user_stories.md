# ADA (AI Documentation Assistant) API User Stories with Detailed Flows

## 1. Cloud Architect (Aarya)

### User Story 1: Infrastructure Documentation Generation

As a Cloud Architect, I want to quickly generate executable documentation for my infrastructure design
So that my operations team can reliably deploy and understand our cloud architecture.

**Experience:** Aarya accesses the ADA API through the Azure Portal integration. She enters a description of her desired infrastructure - "a highly available web application with Azure Kubernetes Service, Azure Container Registry, and Azure Front Door." The API generates a complete executable document with properly formatted code blocks, environment variables, and step-by-step instructions. Each code block is already validated to work correctly, saving her hours of documentation time while ensuring operational reliability.

**Detailed API Flow:**
1. Aarya accesses the Azure Portal integration with ADA
2. The portal frontend makes a `POST` request to `/api/v1/ai/generate` with payload:
   ```json
   {
     "prompt": "Create a highly available web application with Azure Kubernetes Service, Azure Container Registry, and Azure Front Door",
     "targetEnvironment": "azure",
     "infrastructureType": "terraform",
     "expertiseLevel": "intermediate",
     "additionalContext": "This is for a financial services company with 99.99% uptime requirements"
   }
   ```
3. API returns a `202 Accepted` response with `requestId: "gen-12345"`
4. Portal polls `GET /api/v1/ai/generate/gen-12345` every 3 seconds to check generation status
5. When complete, API returns a document object with Terraform infrastructure code and explanations
6. Portal then calls `POST /api/v1/documents/doc-12345/validate` to verify the document works
7. Innovation Engine runs the document in a sandbox environment and returns validation results
8. If validation succeeds, document status is updated to "validated" and displayed to Aarya
9. If validation fails, error details are shown with an option to call `POST /api/v1/documents/doc-12345/repair`

### User Story 2: Custom Terraform Documentation

As a Cloud Architect, I want to convert my existing Terraform scripts into educational, executable documentation so that new team members can understand our infrastructure approach while deploying resources.

**Experience:** Aarya has complex Terraform files that work but lack explanation. She submits them to the ADA API's document conversion endpoint with context about their purpose. The API returns a comprehensive markdown document that preserves all the functional code while adding clear explanations, proper environment variable declarations, appropriate headers, and validation checkpoints that can be executed by Innovation Engine. The document becomes both a deployment tool and training material.

**Detailed API Flow:**
1. Aarya has existing Terraform files in a GitHub repository
2. She integrates ADA with her CI/CD using a GitHub Action that triggers on PRs to the `/terraform` folder
3. The Action calls `POST /api/v1/documents` with:
   ```json
   {
     "title": "Production Kubernetes Infrastructure",
     "description": "Terraform modules for our production Kubernetes deployment",
     "content": "<<base64-encoded-terraform-files>>",
     "infrastructureType": "terraform",
     "tags": ["production", "kubernetes", "documentation"]
   }
   ```
4. The API processes the files and adds explanations between code blocks by analyzing the Terraform structure
5. The Action then calls `GET /api/v1/documents/{documentId}` to retrieve the generated documentation
6. For each code block, the Action verifies syntax by calling `POST /api/v1/documents/{documentId}/validate` with `validateOnly: true`
7. The completed document is committed to a new branch and a PR is created for review
8. Upon approval, the executable documentation is published to their internal knowledge base via webhook

## 2. Product Manager (Alex)

### User Story 3: Demo Script to Executable Document

As a Product Manager, I want to convert my demo scripts into customer-ready, executable documents so that customers can understand and deploy our product features without engineering support

**Experience:** Alex has created a basic demo script showing a new Azure feature. He calls the ADA API with this script and selects the option to generate dependency files. The API transforms his simple commands into a comprehensive, educational document with proper metadata, environment variables with random suffixes for idempotency, detailed explanations of each step, and expected output blocks for verification. The document automatically passes all innovation engine tests, making it immediately shareable with customers.

**Detailed API Flow:**
1. Alex uses the ADA CLI tool that wraps the REST API
2. He runs `ada convert demo.sh --target-format=executabledoc --customer-ready`
3. The CLI tool reads his demo.sh file and makes a `POST` request to `/api/v1/documents` with:
   ```json
   {
     "title": "New Feature Demo",
     "description": "Demonstration of our new feature X",
     "content": "<<content-of-demo.sh>>",
     "infrastructureType": "bash",
     "tags": ["demo", "customer-ready"],
     "customizationParameters": {
       "generateIdempotentResourceNames": true,
       "includeExpectedOutput": true,
       "addPrerequisiteChecks": true
     }
   }
   ```
4. API processes the script and returns a document ID
5. CLI tool then calls `POST /api/v1/documents/{documentId}/validate` to test the generated document
6. The API runs the document through Innovation Engine which executes each code block sequentially
7. API captures the output from each step and verifies it matches expected results
8. CLI tool receives the validated document and writes it to `demo-executable.md`
9. Alex reviews the document with embedded expected outputs and resource name randomization

### User Story 4: User Experience Documentation

As a Product Manager, I want to document customer experiences in an executable format early in the development process so that engineering teams can understand the expected behavior and validate it works as designed.

**Experience:** Alex creates a basic description of a new feature workflow, then submits it to the ADA API. The service generates a document-driven design specification that includes both narrative explanation and executable code. Engineers can run this document to see the expected behavior, while Alex can verify the feature matches his design intent. The document becomes both a specification and a validation tool.

**Detailed API Flow:**
1. Alex uses the Azure Portal ADA integration
2. He creates a new document description and submits it through a form that calls `POST /api/v1/ai/generate`
3. The request includes:
   ```json
   {
     "prompt": "Document the user experience for containerizing and deploying a Node.js app to AKS",
     "targetEnvironment": "azure",
     "infrastructureType": "azcli",
     "expertiseLevel": "beginner",
     "additionalContext": "Target audience is developers with no Kubernetes experience"
   }
   ```
4. The API generates a document and returns a document ID
5. The portal displays a preview and Alex makes edits through the UI
6. Each edit triggers a `PUT /api/v1/documents/{documentId}` call with the updated content
7. Alex shares the document with engineering by clicking "Share", which calls `GET /api/v1/documents/{documentId}?format=markdown`
8. The API returns a shareable link with appropriate permissions set
9. Engineering team members access the document and can execute it section-by-section using the Innovation Engine integration

## 3. Content Author

### User Story 5: Automated Documentation Testing

As a Content Author, I want to automatically test my infrastructure documentation for errors so that customers don't encounter issues when following our guidance.

**Experience:** A content author submits their markdown document to the ADA API's validation endpoint. The service identifies several issues: missing environment variables, commands that would fail with certain Azure regions, and dependencies not properly defined. The API automatically fixes these issues through multiple attempts, each time applying more sophisticated troubleshooting strategies until all tests pass. The author receives a fully functional document with detailed explanations of what was fixed.

**Detailed API Flow:**
1. Content author submits a document through the MS Learn authoring tool
2. The tool calls `POST /api/v1/documents` with the markdown content
3. After creation, it immediately calls `POST /api/v1/documents/{documentId}/validate` with:
   ```json
   {
     "environmentParameters": {
       "azureRegion": "eastus",
       "subscriptionType": "pay-as-you-go"
     },
     "validateOnly": false
   }
   ```
4. The API returns validation status with error details for failing steps
5. For each error, the tool calls `POST /api/v1/documents/{documentId}/repair` with:
   ```json
   {
     "validationErrors": ["Step 3 failed: Error: Resource group name already exists"],
     "userGuidance": "Please fix the resource naming to be unique"
   }
   ```
6. The API returns suggested fixes and the tool applies them with `PUT /api/v1/documents/{documentId}`
7. This process repeats until all validation passes or user intervention is required
8. The tool then executes a final validation call with different parameters to test idempotency:
   ```json
   {
     "environmentParameters": {
       "azureRegion": "westeurope",
       "subscriptionType": "enterprise"
     },
     "validateOnly": false
   }
   ```
9. Once all validations pass, the document is marked as validated and ready for publishing

### User Story 6: Shell Script Documentation

As a Content Author, I want to convert technical shell scripts into educational documents so that users understand what each part of the script accomplishes.

**Experience:** The author has a complex deployment shell script but no documentation. They call the ADA API's script documentation endpoint with the script path and receive a fully structured markdown document with proper headings, detailed explanations between code blocks, all required metadata, and preserved functionality. The document explains each section's purpose while maintaining all the original functionality.

**Detailed API Flow:**
1. Content author uses the ADA VS Code Extension
2. They open their complex deployment shell script and right-click to select "Generate Executable Documentation"
3. The extension calls `POST /api/v1/ai/generate` with:
   ```json
   {
     "prompt": "Convert this shell script into an educational executable document",
     "targetEnvironment": "bash",
     "infrastructureType": "bash",
     "additionalContext": "<<content of selected script>>",
     "expertiseLevel": "beginner"
   }
   ```
4. The API processes the request and returns a generated document
5. VS Code extension displays the document in a side panel with syntax highlighting
6. Author makes edits which are synchronized with the API via `PUT /api/v1/documents/{documentId}`
7. They click "Test" in the extension, which calls `POST /api/v1/documents/{documentId}/validate`
8. The API runs each code block in isolation and returns success/error for each section
9. Author can see exactly which parts of their script need improvement before publishing
10. Final document is exported as markdown with embedded executable code blocks

## 4. Developer/Engineer

### User Story 7: API-Driven Document Generation Pipeline

As a Developer, I want to integrate the ADA API into our CI/CD pipeline so that our infrastructure documentation is automatically generated and tested alongside code changes.

**Experience:** A developer creates a GitHub Action that calls the ADA API whenever infrastructure code is changed. The action submits the updated Terraform files to the API, which generates an updated executable document. This document is then automatically tested using the Innovation Engine. If validation passes, the updated documentation is published to their internal knowledge base. This ensures their documentation always reflects the current infrastructure state.

**Detailed API Flow:**
1. Developer creates a GitHub Action workflow file (.github/workflows/update-docs.yml)
2. The workflow triggers whenever infrastructure files change in the repo
3. Action authenticates with Azure AD and obtains a token for the ADA API
4. It identifies changed Terraform files and calls `POST /api/v1/documents` with:
   ```json
   {
     "title": "Infrastructure Documentation",
     "description": "Auto-generated from CI/CD pipeline",
     "content": "<<terraform-files-content>>",
     "infrastructureType": "terraform",
     "tags": ["cicd", "auto-generated"]
   }
   ```
5. The API processes the Terraform files and generates a structured document
6. Action then calls `POST /api/v1/documents/{documentId}/validate` to verify functionality
7. If validation succeeds, it calls `GET /api/v1/documents/{documentId}?format=markdown`
8. The action commits the generated markdown to the repo's `/docs` folder
9. For any validation failures, it opens an issue with details from the validation response
10. A scheduled job runs weekly to revalidate all documents by calling:
    ```
    GET /api/v1/documents?tag=cicd&status=validated
    ```
    And then validating each document to ensure continued functionality

### User Story 8: Self-Healing Documentation

As a Developer, I want to automatically fix broken documentation when changes occur in the underlying cloud services so that our documents remain functional even when Azure features evolve

**Experience:** The developer has scheduled a job that periodically validates all executive documents against the Innovation Engine. When a service API change breaks a document, the job sends the failing document to the ADA API's repair endpoint with the validation errors. The API analyzes the errors, makes intelligent corrections to the document, and returns an updated version that works with the changed service. The system attempts multiple strategies until it finds one that passes all tests.

**Detailed API Flow:**
1. Operations team has a scheduled Azure Function that runs nightly
2. Function retrieves all published documents via `GET /api/v1/documents?status=published`
3. For each document, it calls `POST /api/v1/documents/{documentId}/validate`
4. When a document fails validation, function calls `POST /api/v1/documents/{documentId}/repair` with:
   ```json
   {
     "validationErrors": ["Error in step 4: Azure CLI command 'az containerapp create' failed with 'unrecognized argument --environment'"],
     "userGuidance": "The Container Apps CLI commands may have changed"
   }
   ```
5. The API analyzes the error, consults updated Azure CLI documentation, and generates a fix
6. Function retrieves the suggested fix and applies it with `PUT /api/v1/documents/{documentId}`
7. Function then re-validates the document and, if successful, updates the published version
8. If repair fails, function creates a ticket in Azure DevOps with detailed diagnostics
9. Function maintains a revision history of all repairs by calling `GET /api/v1/documents/{documentId}/revisions`
10. Monthly summary reports are generated showing repair success rates and common failure patterns

## 5. Operations Engineer

### User Story 9: Security Analysis of Documentation

As an Operations Engineer, I want to analyze my deployment documents for security vulnerabilities so that I don't inadvertently introduce security risks during deployments

**Experience:** An ops engineer submits their deployment document to the ADA API's security analysis endpoint. The service returns a comprehensive report identifying several issues: overly permissive access controls, sensitive data not being properly handled, and resources exposed to the internet unnecessarily. The report provides specific remediation steps for each issue with code examples, enabling the engineer to secure their deployment process.

**Detailed API Flow:**
1. Operations engineer submits their deployment document through the ADA web portal
2. Portal uploads the document via `POST /api/v1/documents` with security scanning flag enabled:
   ```json
   {
     "title": "Production Deployment",
     "content": "<<markdown-content>>",
     "infrastructureType": "terraform",
     "securityScanEnabled": true,
     "complianceFrameworks": ["NIST", "CIS"]
   }
   ```
3. API creates the document and returns the document ID
4. Portal immediately calls `POST /api/v1/documents/{documentId}/securityAnalysis` with:
   ```json
   {
     "depth": "comprehensive",
     "includeRemediation": true
   }
   ```
5. API analyzes the document against security best practices and selected compliance frameworks
6. Results are returned with specific line numbers and security issues identified
7. For each issue, API provides `POST /api/v1/documents/{documentId}/securityFix/{issueId}` endpoint
8. Engineer reviews each issue and selects which fixes to apply
9. Portal calls the appropriate fix endpoints to apply selected security improvements
10. Final secure document is validated with `POST /api/v1/documents/{documentId}/validate`

### User Story 10: PII Detection and Redaction

As an Operations Engineer, I want to automatically detect and redact sensitive information from my deployment logs and documents so that I can safely share them with team members and in support tickets

Experience: An engineer has troubleshooting documents containing output from production systems. Before sharing them, they submit these documents to the ADA API's redaction endpoint. The service identifies and replaces all subscription IDs, resource names, IP addresses, and other sensitive information with appropriate placeholders. The engineer receives a cleaned document that maintains all the technical context while removing security-sensitive details.


**Detailed API Flow:**
1. Operations engineer uses the ADA CLI tool to process sensitive logs
2. They run `ada redact sensitive-logs.md --output=redacted-logs.md --sensitivity=high`
3. CLI tool calls `POST /api/v1/documents` to upload the sensitive document with:
   ```json
   {
     "title": "Sensitive Troubleshooting Logs",
     "content": "<<sensitive-content>>",
     "temporary": true,
     "retentionPeriod": "1h"
   }
   ```
4. Upon successful upload, CLI calls `POST /api/v1/documents/{documentId}/redact` with:
   ```json
   {
     "sensitivityLevel": "high",
     "redactionTypes": [
       "subscriptionIds", 
       "resourceNames", 
       "ipAddresses", 
       "connectionStrings",
       "emails"
     ],
     "replacementFormat": "descriptive-placeholder"
   }
   ```
5. API processes the document using NER (Named Entity Recognition) to identify sensitive data
6. Redacted document is returned with each sensitive item replaced with a descriptive placeholder
7. CLI saves the redacted content to the output file
8. After redaction is complete, CLI calls `DELETE /api/v1/documents/{documentId}` to ensure sensitive data is removed
9. An audit log of the redaction (without sensitive data) is maintained for compliance purposes

## 6. Enterprise Architect

### User Story 11: Custom Documentation Templates

As an Enterprise Architect, I want to generate documentation that follows our corporate standards and patterns so that all infrastructure documentation is consistent across the organization.

**Experience:** The architect provides the ADA API with their organization's documentation template and standards along with a workload description. The service generates executable documentation that not only works correctly but follows all company-specific naming conventions, security practices, and formatting guidelines. This ensures consistency across hundreds of projects while maintaining the executable nature of the documents.

**Detailed API Flow:**
1. Enterprise architect first registers their company template via `POST /api/v1/templates` with:
   ```json
   {
     "name": "Contoso Enterprise Template",
     "template": "<<markdown-template-with-placeholders>>",
     "rules": [
       {"type": "naming", "pattern": "contoso-{service}-{env}-{region}"},
       {"type": "security", "rule": "all-resources-require-tagging"},
       {"type": "formatting", "rule": "section-structure-preserved"}
     ]
   }
   ```
2. API returns a template ID they can reference
3. When generating new documents, architect uses `POST /api/v1/ai/generate` with:
   ```json
   {
     "prompt": "Create infrastructure for a three-tier web application",
     "templateId": "template-12345",
     "infrastructureType": "terraform",
     "organizationSpecificParameters": {
       "businessUnit": "finance",
       "costCenter": "cc-12345",
       "environment": "production"
     }
   }
   ```
4. API generates documentation following all company-specific naming conventions, security practices, and formatting guidelines
5. Architect reviews and publishes the document with `PUT /api/v1/documents/{documentId}` and `status: "approved"`
6. The document is automatically distributed via webhook to their knowledge management system
7. Monthly template compliance is checked via `GET /api/v1/templates/{templateId}/compliance` 