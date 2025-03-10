# AI Documentation Assistant (ADA) REST API Specification

## 1. Introduction

This document provides the technical specifications for the AI Documentation Assistant (ADA) REST API. ADA enables users to generate, test, and validate executable documentation for Infrastructure as Code (IaC) deployments, focusing primarily on Linux and cloud native workloads.

## 2. API Design Principles

- **REST Architectural Style**: The API follows standard REST principles with resource-based URLs, appropriate HTTP methods, and stateless interactions
- **JSON**: All API requests and responses use JSON format
- **Authentication**: OAuth 2.0 integration with Azure AD
- **Performance**: Target response times under 2 seconds for document generation requests
- **Scalability**: Support for horizontal scaling to handle varying loads

## 3. Base URL

```
https://ada.azure.com/api/v1
```

## 4. Authentication and Authorization

The API requires authentication for all requests using OAuth 2.0 with Azure Active Directory.

**Headers**:
```
Authorization: Bearer {token}
```

## 5. Resources and Endpoints

### 5.1 Documents

#### Create Document
```
POST /documents
```

**Request Body**:
```json
{
  "title": "string",
  "description": "string",
  "prompt": "string",
  "targetEnvironment": "string", // e.g., "azure", "aws", "local"
  "infrastructureType": "string", // e.g., "terraform", "azcli", "bash"
  "tags": ["string"],
  "customizationParameters": {
    "key": "value"
  },
  "sourceDocument": "string", // Optional: Original markdown to convert
  "sourceType": "string" // "prompt", "markdown", "script"
}
```

**Response** (201 Created):
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "content": "string", // Generated executable documentation
  "createdAt": "string",
  "status": "string", // "draft", "validated", "failed"
  "_links": {
    "self": {"href": "string"},
    "validate": {"href": "string"},
    "execute": {"href": "string"}
  }
}
```

#### Get Document
```
GET /documents/{id}
```

**Response** (200 OK):
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "content": "string",
  "createdAt": "string",
  "updatedAt": "string",
  "status": "string",
  "validationResult": {
    "status": "string",
    "details": "string",
    "timestamp": "string"
  },
  "dependencyFiles": [
    {
      "filename": "string",
      "content": "string",
      "type": "string"
    }
  ],
  "_links": {
    "self": {"href": "string"},
    "validate": {"href": "string"},
    "execute": {"href": "string"},
    "revisions": {"href": "string"},
    "dependencies": {"href": "string"}
  }
}
```

#### Update Document
```
PUT /documents/{id}
```

**Request Body**:
```json
{
  "title": "string",
  "description": "string",
  "content": "string",
  "tags": ["string"]
}
```

**Response** (200 OK): Same as GET response

#### List Documents
```
GET /documents
```

**Query Parameters**:
- `status` - Filter by validation status
- `tag` - Filter by tag
- `infrastructureType` - Filter by type
- `page` - Pagination page number
- `pageSize` - Items per page

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "status": "string",
      "createdAt": "string",
      "updatedAt": "string",
      "_links": {
        "self": {"href": "string"}
      }
    }
  ],
  "pagination": {
    "totalItems": "number",
    "totalPages": "number",
    "currentPage": "number",
    "pageSize": "number"
  }
}
```

#### Delete Document
```
DELETE /documents/{id}
```

**Response** (204 No Content)

### 5.2 Validation and Testing

#### Validate Document
```
POST /documents/{id}/validate
```

**Request Body**:
```json
{
  "environmentParameters": {
    "key": "value"
  },
  "validateOnly": "boolean", // True for syntax check only, false for full execution test
  "maxAttempts": "number", // Max number of auto-correction attempts (default: 3)
  "timeoutSeconds": "number" // Execution timeout in seconds (default: 600)
}
```

**Response** (200 OK):
```json
{
  "id": "string",
  "status": "string", // "in_progress", "success", "failed", "timed_out"
  "details": "string",
  "attempts": "number", // Number of attempts made
  "validationSteps": [
    {
      "step": "string",
      "status": "string",
      "output": "string",
      "timestamp": "string",
      "errorDetails": "string"
    }
  ],
  "_links": {
    "status": {"href": "string"},
    "document": {"href": "string"}
  }
}
```

#### Get Validation Status
```
GET /documents/{id}/validations/{validationId}
```

**Response** (200 OK): Same as validate response

### 5.3 AI-Assisted Generation and Customization

#### Generate Document from Prompt
```
POST /ai/generate
```

**Request Body**:
```json
{
  "prompt": "string", // User's description of desired infrastructure
  "targetEnvironment": "string",
  "infrastructureType": "string", // "terraform", "azcli", "bash"
  "expertiseLevel": "string", // "beginner", "intermediate", "expert"
  "additionalContext": "string",
  "sourceType": "string", // "prompt", "markdown", "script"
  "sourceContent": "string" // Original content for conversion
}
```

**Response** (202 Accepted):
```json
{
  "requestId": "string",
  "estimatedCompletionTime": "string",
  "_links": {
    "status": {"href": "string"}
  }
}
```

#### Get Generation Status
```
GET /ai/generate/{requestId}
```

**Response** (200 OK):
```json
{
  "status": "string", // "processing", "completed", "failed"
  "progress": "number", // 0-100
  "document": {
    // Document object if completed
  },
  "error": "string" // If failed
}
```

#### AI-Assisted Document Repair
```
POST /documents/{id}/repair
```

**Request Body**:
```json
{
  "validationErrors": ["string"],
  "userGuidance": "string"
}
```

**Response** (200 OK):
```json
{
  "repairSuggestions": [
    {
      "description": "string",
      "modifiedContent": "string",
      "confidence": "number"
    }
  ],
  "_links": {
    "apply": {"href": "string"},
    "document": {"href": "string"}
  }
}
```

### 5.4 Dependency Files Management

#### List Dependency Files
```
GET /documents/{id}/dependencies
```

**Response** (200 OK):
```json
{
  "dependencies": [
    {
      "filename": "string",
      "type": "string", // "json", "yaml", "terraform", "shell", etc.
      "content": "string"
    }
  ]
}
```

#### Create or Update Dependency File
```
PUT /documents/{id}/dependencies/{filename}
```

**Request Body**:
```json
{
  "content": "string",
  "type": "string" // "json", "yaml", "terraform", "shell", etc.
}
```

**Response** (200 OK):
```json
{
  "filename": "string",
  "type": "string",
  "content": "string",
  "createdAt": "string",
  "updatedAt": "string"
}
```

#### Generate Dependency Files
```
POST /documents/{id}/dependencies/generate
```

**Response** (200 OK):
```json
{
  "generatedFiles": [
    {
      "filename": "string",
      "type": "string",
      "content": "string"
    }
  ],
  "documentUpdated": "boolean"
}
```

### 5.5 Security and Privacy

#### Redact PII
```
POST /documents/{id}/redact
```

**Request Body**:
```json
{
  "redactionLevel": "string" // "minimal", "standard", "strict"
}
```

**Response** (200 OK):
```json
{
  "id": "string",
  "redactedContent": "string",
  "redactionCount": "number",
  "redactedTypes": ["string"] // Types of PII found and redacted
}
```

#### Security Analysis
```
POST /documents/{id}/security-analysis
```

**Request Body**:
```json
{
  "analysisLevel": "string" // "basic", "standard", "comprehensive"
}
```

**Response** (202 Accepted):
```json
{
  "analysisId": "string",
  "_links": {
    "status": {"href": "string"}
  }
}
```

#### Get Security Analysis Results
```
GET /documents/{id}/security-analysis/{analysisId}
```

**Response** (200 OK):
```json
{
  "status": "string", // "in_progress", "completed", "failed"
  "findings": [
    {
      "severity": "string", // "critical", "high", "medium", "low"
      "category": "string",
      "description": "string",
      "recommendation": "string",
      "location": "string" // Location in document
    }
  ],
  "summary": {
    "criticalCount": "number",
    "highCount": "number",
    "mediumCount": "number",
    "lowCount": "number"
  }
}
```

## 6. Error Handling

The API uses standard HTTP status codes and includes detailed error information in responses:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": [
      {
        "code": "string",
        "target": "string",
        "message": "string"
      }
    ]
  }
}
```

**Common Error Codes**:
- 400 Bad Request: Invalid input parameters
- 401 Unauthorized: Missing or invalid authentication
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Resource not found
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Server error

## 7. Rate Limiting and Quotas

- Rate limiting implemented with token bucket algorithm
- Default limits:
  - 60 requests per minute per authenticated user
  - 10 AI generation requests per hour per user
  - 5 concurrent validation processes per user

**Headers**:
```
X-RateLimit-Limit: {limit}
X-RateLimit-Remaining: {remaining}
X-RateLimit-Reset: {reset_time}
```

## 8. Versioning Strategy

- API versioning in URL path (/api/v1)
- Major version increments for breaking changes
- Support for at least one previous major version after a new version is released
- Deprecation notices provided 6 months before endpoint removal

## 9. Security Considerations

- Data Protection:
  - All data encrypted in transit (TLS 1.3)
  - Secrets and credentials never stored in generated documents
  - Content scanning for sensitive information before storage
  - Automatic PII redaction in result blocks and outputs
  
- Access Controls:
  - RBAC with Azure AD integration
  - IP restrictions available for enterprise customers
  - Audit logging for all API operations

## 10. Integration Requirements

### 10.1 Innovation Engine Integration

The API must integrate with the Innovation Engine for document validation and execution:

- Support for passing documents to Innovation Engine for testing
- Ability to receive and process validation results
- Support for debugging information when validation fails
- Iterative correction based on test failures

### 10.2 LLM Integration

- RAG implementation with weighting toward tested Executable Documents
- Capability to customize generation based on user expertise level
- Support for prompt engineering to improve generation quality
- Multi-turn conversations for iterative document improvement

## 11. Monitoring and Observability

The API should expose the following metrics:

- Request latency
- Success/failure rates by endpoint
- Document generation success rates
- Validation success rates
- User adoption metrics
- Error frequency by type
- Validation attempts per document
- Common error patterns

## 12. Implementation Roadmap

1. **Phase 1 (3 months)**:
   - Core CRUD operations for documents
   - Basic validation capabilities
   - OAuth authentication
   - Terminal-based reference implementation

2. **Phase 2 (6 months)**:
   - AI-assisted document generation
   - Integration with at least one partner UX (likely Azure Portal)
   - Enhanced validation with detailed error reporting
   - Dependency file management

3. **Phase 3 (12 months)**:
   - Full Copilot integration as an agent
   - Self-healing document capabilities
   - Support for additional IaC tools beyond Terraform and Azure CLI
   - Security analysis and PII redaction

## 13. Development Guidelines

### 13.1 Technology Stack Recommendations

- Backend: .NET Core or Node.js with TypeScript
- Database: Azure Cosmos DB (for document storage)
- Authentication: Azure AD OAuth 2.0
- LLM: Azure OpenAI Service with custom RAG implementation
- Testing: Integration with Azure Innovation Engine

### 13.2 Development Process

- API-first development approach with OpenAPI/Swagger specifications
- CI/CD pipeline with automated testing
- Feature flags for gradual rollout of capabilities
- Comprehensive API documentation in Microsoft Learn

## 14. Appendix

### 14.1 Example Document Structure

```markdown
# Deploy a Highly Available Web Application on Azure with Terraform

This document will guide you through deploying a highly available web application 
infrastructure on Azure using Terraform.

## Prerequisites
- Azure CLI installed and configured
- Terraform v1.0+ installed
- Basic understanding of Terraform and Azure resources

## Step 1: Configure Azure Provider

```terraform
provider "azurerm" {
  features {}
}

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}
```

## Step 2: Create Resource Group

```terraform
resource "azurerm_resource_group" "web_app_rg" {
  name     = "web-app-resources"
  location = "East US"
}
```

# Additional steps would follow...
```

### 14.2 Recommended Testing Approaches

- Unit tests for all API endpoints
- Integration tests with Innovation Engine
- Performance testing under load
- Security scanning for generated content
### 14.2 Recommended Testing Approaches

- Unit tests for all API endpoints
- Integration tests with Innovation Engine
- Performance testing under load
- Security scanning for generated content