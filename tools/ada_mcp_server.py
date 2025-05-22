#!/usr/bin/env python3
"""ADA MCP Server - AI Documentation Assistant as an MCP Service"""
import asyncio
import json
import os
import traceback
from typing import Any, Dict, List, Union

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Attempt to import the ada module
try:
    import ada
except ImportError:
    print("Error: The 'ada' module is not found. Please ensure it's in the PYTHONPATH.")
    # Define a dummy ada module if the import fails, so the server can start and report this via tools
    class AdaMock:
        def __getattr__(self, name):
            def method_not_found(*args, **kwargs):
                return f"Error: 'ada.{name}' not found. The 'ada' module failed to import."
            return method_not_found
    ada = AdaMock()
    ada.client = None # type: ignore
    ada.deployment_name = None # type: ignore
    ada.system_prompt = "System prompt not available as ada module failed to import." # type: ignore


app = Server("ada-mcp-server")

def _read_file_content(file_path: str) -> Union[str, None]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

async def list_tools() -> List[Tool]:
    tools = [
        Tool(
            name="convert_to_exec_doc",
            description="Convert an existing markdown file to an Executable Document using ADA's core LLM.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the markdown file to convert."},
                    "output_file_path": {"type": "string", "description": "Absolute path to save the converted document.", "default": "converted_exec_doc.md"},
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="generate_exec_doc",
            description="Generate a new Executable Document from a workload description using ADA's core LLM.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workload_description": {"type": "string", "description": "Description of the workload for the new Exec Doc."},
                    "output_file_path": {"type": "string", "description": "Absolute path to save the generated document.", "default": "generated_exec_doc.md"},
                    "reference_data": {
                        "type": "array",
                        "description": "Optional list of URLs or absolute file paths for additional context.",
                        "items": {"type": "string"},
                        "default": []
                    },
                },
                "required": ["workload_description"]
            }
        ),
        Tool(
            name="document_shell_script",
            description="Generate documentation for a shell script using ada.generate_script_description_with_content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_path": {"type": "string", "description": "Absolute path to the shell script."},
                    "context": {"type": "string", "description": "Additional context for the script.", "default": ""},
                    "output_file_path": {"type": "string", "description": "Optional absolute path to save the documented script. If None, a default name is used.", "default": None}
                },
                "required": ["script_path"]
            }
        ),
        Tool(
            name="redact_pii",
            description="Redact PII from an Executable Document using ada.redact_pii_from_doc_with_path.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_path": {"type": "string", "description": "Absolute path to the document."},
                    "output_file_path": {"type": "string", "description": "Optional absolute path to save the redacted document. If None, a default name is used.", "default": None}
                },
                "required": ["doc_path"]
            }
        ),
        Tool(
            name="security_analysis",
            description="Perform security vulnerability analysis on an Executable Document using ada.perform_security_check.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_path": {"type": "string", "description": "Absolute path to the document."}
                },
                "required": ["doc_path"]
            }
        ),
        Tool(
            name="seo_optimization",
            description="Perform SEO optimization on an Executable Document using ada.perform_seo_check.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_path": {"type": "string", "description": "Absolute path to the document."},
                    "checklist_path": {"type": "string", "description": "Absolute path to SEO checklist.", "default": "seo-checklist.md"}
                },
                "required": ["doc_path"]
            }
        ),
        Tool(
            name="install_innovation_engine",
            description="Installs Innovation Engine using ada.install_innovation_engine. This might require sudo and internet access.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_last_error_log",
            description="Gets the last error log content from 'ie.log' using ada.get_last_error_log.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="generate_dependency_files",
            description="Generates dependency files for a document using ada.generate_dependency_files.",
            inputSchema={"type": "object", "properties": {"doc_path": {"type": "string", "description": "Absolute path to the document."}}, "required": ["doc_path"]}
        ),
        Tool(
            name="get_content_from_url",
            description="Fetches main content from a URL using ada.get_content_from_url (if available in ada.py).",
            inputSchema={"type": "object", "properties": {"url": {"type": "string", "description": "The URL to fetch content from."}}, "required": ["url"]}
        ),
        Tool(
            name="get_content_from_file",
            description="Fetches content from a file path using ada.get_content_from_file (if available in ada.py).",
            inputSchema={"type": "object", "properties": {"file_path": {"type": "string", "description": "Absolute path to the file."}}, "required": ["file_path"]}
        ),
        Tool(
            name="remove_backticks_from_file",
            description="Removes starting/ending triple backticks from a file's content in-place, using ada.remove_backticks_from_file.",
            inputSchema={"type": "object", "properties": {"file_path": {"type": "string", "description": "Absolute path to the file to modify."}}, "required": ["file_path"]}
        ),
        Tool(
            name="generate_title_from_description",
            description="Generates a document title from its description using an LLM via ada.generate_title_from_description.",
            inputSchema={"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]}
        ),
        Tool(
            name="requires_aks_cluster",
            description="Checks if a document implies an existing AKS cluster is required using ada.requires_aks_cluster (if available in ada.py).",
            inputSchema={"type": "object", "properties": {"doc_path": {"type": "string", "description": "Absolute path to the document."}}, "required": ["doc_path"]}
        ),
        Tool(
            name="extract_aks_env_vars",
            description="Extracts AKS related environment variables from a document using ada.extract_aks_env_vars (if available in ada.py).",
            inputSchema={"type": "object", "properties": {"doc_path": {"type": "string", "description": "Absolute path to the document."}}, "required": ["doc_path"]}
        ),
        Tool(
            name="transform_document_for_dependencies",
            description="Transforms a document for dependencies using ada.transform_document_for_dependencies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_path": {"type": "string", "description": "Absolute path to the document."},
                    "dependency_files": {"type": "array", "items": {"type": "string"}, "description": "List of dependency file paths."}
                },
                "required": ["doc_path", "dependency_files"]
            }
        ),
        Tool(
            name="update_dependency_file",
            description="Updates a dependency file using ada.update_dependency_file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_info": {"type": "object", "description": "Information about the file to update."},
                    "error_message": {"type": "string", "description": "Error message to include."},
                    "main_doc_path": {"type": "string", "description": "Path to the main document."}
                },
                "required": ["file_info", "error_message", "main_doc_path"]
            }
        ),
        Tool(
            name="analyze_error",
            description="Analyzes an error log using ada.analyze_error.",
            inputSchema={
                "type": "object",
                "properties": {
                    "error_log": {"type": "string", "description": "The error log content."},
                    "dependency_files": {"type": "array", "items": {"type": "string"}, "description": "List of dependency file paths.", "default": []}
                },
                "required": ["error_log"]
            }
        ),
        Tool(
            name="setup_output_folder",
            description="Sets up an output folder using ada.setup_output_folder.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_type": {"type": "string", "description": "Type of input (e.g., 'url', 'file')."},
                    "input_name": {"type": "string", "description": "Name of the input."},
                    "title": {"type": "string", "description": "Optional title for the output folder.", "default": None}
                },
                "required": ["input_type", "input_name"]
            }
        ),
        Tool(
            name="check_existing_log",
            description="Checks for an existing log file using ada.check_existing_log.",
            inputSchema={"type": "object", "properties": {"input_path": {"type": "string", "description": "Optional path to the input.", "default": None}}}
        ),
        Tool(
            name="calculate_success_rate",
            description="Calculates the success rate from log data using ada.calculate_success_rate.",
            inputSchema={"type": "object", "properties": {"log_data": {"type": "object", "description": "Log data to analyze."}}, "required": ["log_data"]}
        ),
        Tool(
            name="calculate_total_execution_time",
            description="Calculates total execution time from log data using ada.calculate_total_execution_time.",
            inputSchema={"type": "object", "properties": {"log_data": {"type": "object", "description": "Log data to analyze."}}, "required": ["log_data"]}
        ),
        Tool(
            name="update_progress_log",
            description="Updates a progress log using ada.update_progress_log.",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_folder": {"type": "string", "description": "Path to the output folder."},
                    "new_data": {"type": "object", "description": "New data to add to the log."},
                    "input_type": {"type": "string", "description": "Type of input."},
                    "user_intent": {"type": "string", "description": "User intent for the operation.", "default": None},
                    "existing_data": {"type": "object", "description": "Existing log data.", "default": None}
                },
                "required": ["output_folder", "new_data", "input_type"]
            }
        ),
        Tool(
            name="collect_iteration_data",
            description="Collects iteration data using ada.collect_iteration_data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_type": {"type": "string", "description": "Type of input."},
                    "user_input": {"type": "string", "description": "User input for the iteration."},
                    "output_file": {"type": "string", "description": "Path to the output file."},
                    "attempt": {"type": "integer", "description": "Current attempt number."},
                    "errors": {"type": "string", "description": "Errors encountered during the iteration."},
                    "start_time": {"type": "number", "description": "Start time of the iteration (timestamp)."},
                    "success": {"type": "boolean", "description": "Whether the iteration was successful."}
                },
                "required": ["input_type", "user_input", "output_file", "attempt", "errors", "start_time", "success"]
            }
        ),
        Tool(
            name="analyze_user_intent",
            description="Analyzes user intent using ada.analyze_user_intent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_input": {"type": "string", "description": "The user's input string."},
                    "input_type": {"type": "string", "description": "The type of input (e.g., 'query', 'command')."}
                },
                "required": ["user_input", "input_type"]
            }
        )
    ]
    return tools

app.list_tools()(list_tools)

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        if name == "convert_to_exec_doc":
            file_path = arguments["file_path"]
            output_file_path = arguments.get("output_file_path", "converted_exec_doc.md")
            existing_doc_content = _read_file_content(file_path)
            if existing_doc_content is None:
                return [TextContent(type="text", text=f"Error: Could not read file {file_path}")]

            user_prompt_for_llm = f"""Please update the following Executable Document based on the rules provided in the system prompt:

```markdown
{existing_doc_content}
```"""
            if ada.client is None or not hasattr(ada, 'client'):
                return [TextContent(type="text", text="Error: ada.client is not initialized. Cannot call LLM.")]
            response = ada.client.chat.completions.create(
                model=ada.deployment_name,
                messages=[
                    {"role": "system", "content": ada.system_prompt},
                    {"role": "user", "content": user_prompt_for_llm}
                ]
            )
            doc_content = response.choices[0].message.content
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(doc_content)
            return [TextContent(type="text", text=f"Document converted and saved to: {output_file_path}")]

        elif name == "generate_exec_doc":
            workload_description = arguments["workload_description"]
            output_file_path = arguments.get("output_file_path", "generated_exec_doc.md")
            reference_data_paths = arguments.get("reference_data", [])
            reference_texts = []
            if reference_data_paths:
                for path_or_url in reference_data_paths:
                    content = ""
                    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
                        if hasattr(ada, 'get_content_from_url'):
                            fetched_content = ada.get_content_from_url(path_or_url)
                            if fetched_content and not (isinstance(fetched_content, str) and fetched_content.startswith("Error:")):
                                content = fetched_content
                            else:
                                print(f"Warning: Could not fetch content from URL {path_or_url}. Response: {fetched_content}")
                        else:
                            print(f"Warning: ada.get_content_from_url function not found.")
                    else:
                        content = _read_file_content(path_or_url)
                    
                    if content:
                        reference_texts.append(f"""Reference content from {path_or_url}:
{content}"""
                        )
            
            full_workload_description = workload_description
            if reference_texts:
                full_workload_description += "\n\nAdditional reference information:\n" + "\n\n".join(reference_texts)
            
            user_prompt_for_llm = full_workload_description
            if ada.client is None or not hasattr(ada, 'client'):
                return [TextContent(type="text", text="Error: ada.client is not initialized. Cannot call LLM.")]
            response = ada.client.chat.completions.create(
                model=ada.deployment_name,
                messages=[
                    {"role": "system", "content": ada.system_prompt},
                    {"role": "user", "content": user_prompt_for_llm}
                ]
            )
            doc_content = response.choices[0].message.content
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(doc_content)
            return [TextContent(type="text", text=f"Document generated and saved to: {output_file_path}")]

        elif name == "document_shell_script":
            script_path = arguments["script_path"]
            context = arguments.get("context", "")
            output_fp = arguments.get("output_file_path")
            if hasattr(ada, 'generate_script_description_with_content'):
                result_message = ada.generate_script_description_with_content(script_path, context, output_file_path=output_fp)
                return [TextContent(type="text", text=str(result_message))]
            else:
                return [TextContent(type="text", text="Error: document_shell_script function (ada.generate_script_description_with_content) not found in ada module.")]

        elif name == "redact_pii":
            doc_path = arguments["doc_path"]
            output_fp = arguments.get("output_file_path")
            if hasattr(ada, 'redact_pii_from_doc_with_path'):
                result_message = ada.redact_pii_from_doc_with_path(doc_path, output_file_path=output_fp)
                return [TextContent(type="text", text=str(result_message))]
            else:
                return [TextContent(type="text", text="Error: redact_pii function (ada.redact_pii_from_doc_with_path) not found in ada module.")]

        elif name == "security_analysis":
            doc_path = arguments["doc_path"]
            if hasattr(ada, 'perform_security_check'):
                result_message = ada.perform_security_check(doc_path)
                return [TextContent(type="text", text=str(result_message))]
            else:
                return [TextContent(type="text", text="Error: security_analysis function (ada.perform_security_check) not found in ada module.")]

        elif name == "seo_optimization":
            doc_path = arguments["doc_path"]
            checklist_path = arguments.get("checklist_path", "seo-checklist.md")
            if hasattr(ada, 'perform_seo_check'):
                result_message = ada.perform_seo_check(doc_path, checklist_path=checklist_path)
                return [TextContent(type="text", text=str(result_message))]
            else:
                return [TextContent(type="text", text="Error: seo_optimization function (ada.perform_seo_check) not found in ada module.")]

        elif name == "install_innovation_engine":
            if hasattr(ada, 'install_innovation_engine'):
                result = ada.install_innovation_engine()
                return [TextContent(type="text", text=f"Innovation Engine installation initiated. Result: {result}")]
            else:
                return [TextContent(type="text", text="Error: install_innovation_engine function not found in ada module.")]

        elif name == "get_last_error_log":
            if hasattr(ada, 'get_last_error_log'):
                log_content = ada.get_last_error_log()
                return [TextContent(type="text", text=str(log_content))]
            else:
                return [TextContent(type="text", text="Error: get_last_error_log function not found in ada module.")]

        elif name == "generate_dependency_files":
            doc_path = arguments["doc_path"]
            if hasattr(ada, 'generate_dependency_files'):
                result = ada.generate_dependency_files(doc_path)
                return [TextContent(type="text", text=f"Dependency files generation result: {result}")]
            else:
                return [TextContent(type="text", text="Error: generate_dependency_files function not found in ada module.")]

        elif name == "get_content_from_url":
            url = arguments["url"]
            if hasattr(ada, 'get_content_from_url'):
                content = ada.get_content_from_url(url)
                return [TextContent(type="text", text=str(content))]
            else:
                return [TextContent(type="text", text="Error: get_content_from_url function not found in ada module.")]
        
        elif name == "get_content_from_file":
            file_path = arguments["file_path"]
            if hasattr(ada, 'get_content_from_file'):
                content = ada.get_content_from_file(file_path)
                return [TextContent(type="text", text=str(content))]
            else: # Fallback to _read_file_content if specific ada function is missing
                content = _read_file_content(file_path)
                if content is not None:
                    return [TextContent(type="text", text=content)]
                else:
                    return [TextContent(type="text", text=f"Error: Could not read file {file_path} and ada.get_content_from_file not found.")]

        elif name == "remove_backticks_from_file":
            file_path = arguments["file_path"]
            if hasattr(ada, 'remove_backticks_from_file'):
                result = ada.remove_backticks_from_file(file_path)
                return [TextContent(type="text", text=f"Backtick removal for {file_path}. Result: {result}")]
            else:
                return [TextContent(type="text", text="Error: remove_backticks_from_file function not found in ada module.")]

        elif name == "generate_title_from_description":
            description = arguments["description"]
            if hasattr(ada, 'generate_title_from_description'):
                title = ada.generate_title_from_description(description, display=False) # Assuming display=False is desired for server context
                return [TextContent(type="text", text=str(title))]
            else:
                return [TextContent(type="text", text="Error: generate_title_from_description function not found in ada module.")]

        elif name == "requires_aks_cluster":
            doc_path = arguments["doc_path"]
            if hasattr(ada, 'requires_aks_cluster'):
                result = ada.requires_aks_cluster(doc_path)
                return [TextContent(type="text", text=f"Requires AKS cluster check: {result}")]
            else:
                return [TextContent(type="text", text="Error: requires_aks_cluster function not found in ada module.")]

        elif name == "extract_aks_env_vars":
            doc_path = arguments["doc_path"]
            if hasattr(ada, 'extract_aks_env_vars'):
                result = ada.extract_aks_env_vars(doc_path)
                return [TextContent(type="text", text=f"Extracted AKS env vars: {json.dumps(result) if isinstance(result, (dict, list)) else str(result)}")]
            else:
                return [TextContent(type="text", text="Error: extract_aks_env_vars function not found in ada module.")]
        
        elif name == "transform_document_for_dependencies":
            doc_path = arguments["doc_path"]
            dependency_files = arguments["dependency_files"]
            if hasattr(ada, 'transform_document_for_dependencies'):
                result = ada.transform_document_for_dependencies(doc_path, dependency_files)
                return [TextContent(type="text", text=str(result))]
            else:
                return [TextContent(type="text", text="Error: transform_document_for_dependencies function not found in ada module.")]

        elif name == "update_dependency_file":
            file_info = arguments["file_info"]
            error_message = arguments["error_message"]
            main_doc_path = arguments["main_doc_path"]
            if hasattr(ada, 'update_dependency_file'):
                result = ada.update_dependency_file(file_info, error_message, main_doc_path)
                return [TextContent(type="text", text=str(result))]
            else:
                return [TextContent(type="text", text="Error: update_dependency_file function not found in ada module.")]

        elif name == "analyze_error":
            error_log = arguments["error_log"]
            dependency_files = arguments.get("dependency_files", [])
            if hasattr(ada, 'analyze_error'):
                result = ada.analyze_error(error_log, dependency_files)
                return [TextContent(type="text", text=str(result))]
            else:
                return [TextContent(type="text", text="Error: analyze_error function not found in ada module.")]

        elif name == "setup_output_folder":
            input_type = arguments["input_type"]
            input_name = arguments["input_name"]
            title = arguments.get("title")
            if hasattr(ada, 'setup_output_folder'):
                result = ada.setup_output_folder(input_type, input_name, title=title)
                return [TextContent(type="text", text=f"Setup output folder result: {result}")]
            else:
                return [TextContent(type="text", text="Error: setup_output_folder function not found in ada module.")]

        elif name == "check_existing_log":
            input_path = arguments.get("input_path")
            if hasattr(ada, 'check_existing_log'):
                result = ada.check_existing_log(input_path=input_path)
                return [TextContent(type="text", text=f"Check existing log result: {str(result)}")]
            else:
                return [TextContent(type="text", text="Error: check_existing_log function not found in ada module.")]

        elif name == "calculate_success_rate":
            log_data = arguments["log_data"]
            if hasattr(ada, 'calculate_success_rate'):
                result = ada.calculate_success_rate(log_data)
                return [TextContent(type="text", text=f"Success rate: {result}")]
            else:
                return [TextContent(type="text", text="Error: calculate_success_rate function not found in ada module.")]

        elif name == "calculate_total_execution_time":
            log_data = arguments["log_data"]
            if hasattr(ada, 'calculate_total_execution_time'):
                result = ada.calculate_total_execution_time(log_data)
                return [TextContent(type="text", text=f"Total execution time: {result}")]
            else:
                return [TextContent(type="text", text="Error: calculate_total_execution_time function not found in ada module.")]

        elif name == "update_progress_log":
            output_folder = arguments["output_folder"]
            new_data = arguments["new_data"]
            input_type = arguments["input_type"]
            user_intent = arguments.get("user_intent")
            existing_data = arguments.get("existing_data")
            if hasattr(ada, 'update_progress_log'):
                result = ada.update_progress_log(output_folder, new_data, input_type, user_intent=user_intent, existing_data=existing_data)
                return [TextContent(type="text", text=f"Update progress log result: {result}")]
            else:
                return [TextContent(type="text", text="Error: update_progress_log function not found in ada module.")]

        elif name == "collect_iteration_data":
            # Ensure all required arguments are present
            required_args = ["input_type", "user_input", "output_file", "attempt", "errors", "start_time", "success"]
            for arg_name in required_args:
                if arg_name not in arguments:
                    return [TextContent(type="text", text=f"Error: Missing required argument '{arg_name}' for collect_iteration_data.")]

            if hasattr(ada, 'collect_iteration_data'):
                result = ada.collect_iteration_data(
                    arguments["input_type"],
                    arguments["user_input"],
                    arguments["output_file"],
                    arguments["attempt"],
                    arguments["errors"],
                    arguments["start_time"],
                    arguments["success"]
                )
                return [TextContent(type="text", text=f"Collect iteration data result: {result}")]
            else:
                return [TextContent(type="text", text="Error: collect_iteration_data function not found in ada module.")]

        elif name == "analyze_user_intent":
            user_input = arguments["user_input"]
            input_type = arguments["input_type"]
            if hasattr(ada, 'analyze_user_intent'):
                result = ada.analyze_user_intent(user_input, input_type)
                return [TextContent(type="text", text=str(result))]
            else:
                return [TextContent(type="text", text="Error: analyze_user_intent function not found in ada module.")]
        else:
            return [TextContent(type="text", text=f"Error: Unknown tool name '{name}'")]
    
    except AttributeError as e:
        error_message = f"Error calling tool '{name}': An attribute was not found. This might indicate a missing function or variable in the 'ada' module or its dependencies. Details: {str(e)}"
        print(f"{error_message}\n{traceback.format_exc()}")
        return [TextContent(type="text", text=error_message)]
    except Exception as e:
        error_message = f"An unexpected error occurred while calling tool '{name}': {str(e)}"
        print(f"{error_message}\n{traceback.format_exc()}")
        return [TextContent(type="text", text=f"{error_message}\nTraceback:\n{traceback.format_exc()}")]

async def mcp_server_main():
    options = InitializationOptions(
        server_version="1.4.0", # Or your server's actual version
        display_name="ADA - AI Documentation Assistant",
        # Add other options as needed, e.g., information about the server
    )
    async with stdio_server() as (read_stream, write_stream):
        await app.run_server(read_stream, write_stream, options)

if __name__ == "__main__":
    asyncio.run(mcp_server_main())
