import sys
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import WorkspaceQuery
from app.document_manager import DocumentManager
from app.utils import get_workspace_summary
from app.anthropic_client import AnthropicClient

# -------------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# -------------------------------------------------------------------------
# FastAPI App Setup
# -------------------------------------------------------------------------
app = FastAPI(
    title="Document Workspace Agent",
    description=(
        "A microservice that manages a workspace of markdown documents. "
        "It provides a natural language interface for creating, editing, and managing documents."
    ),
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------------
# Anthropic Client Setup
# -------------------------------------------------------------------------
try:
    anthropic_client = AnthropicClient()
    logger.info(f"Initialized Anthropic client with model {anthropic_client.model}")
except Exception as e:
    logger.error(f"Failed to initialize Anthropic client: {str(e)}")
    sys.exit(1)

# -------------------------------------------------------------------------
# Document Operation Tools
# -------------------------------------------------------------------------
DOCUMENT_TOOLS = [
    {
        "name": "create_document",
        "description": "Create a new markdown document in the workspace",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to create (must end with .md). If not provided, a UUID-based filename will be generated.",
                },
                "text_content": {
                    "type": "string",
                    "description": "Initial content for the document",
                },
            },
            "required": [],
        },
    },
    {
        "name": "add_section",
        "description": "Add a new section to a document",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the target file",
                },
                "section_name": {
                    "type": "string",
                    "description": "Name of the section to add",
                },
                "text_content": {
                    "type": "string",
                    "description": "Content for the new section",
                },
            },
            "required": ["file_name", "section_name", "text_content"],
        },
    },
    {
        "name": "append_block",
        "description": "Append text to an existing section",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the target file",
                },
                "section_name": {
                    "type": "string",
                    "description": "Name of the section to append to",
                },
                "text_content": {"type": "string", "description": "Text to append"},
            },
            "required": ["file_name", "section_name", "text_content"],
        },
    },
    {
        "name": "replace_section",
        "description": "Replace the content of a section",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the target file",
                },
                "section_name": {
                    "type": "string",
                    "description": "Name of the section to replace",
                },
                "text_content": {
                    "type": "string",
                    "description": "New content for the section",
                },
            },
            "required": ["file_name", "section_name", "text_content"],
        },
    },
    {
        "name": "remove_section",
        "description": "Remove a section from a document",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the target file",
                },
                "section_name": {
                    "type": "string",
                    "description": "Name of the section to remove",
                },
            },
            "required": ["file_name", "section_name"],
        },
    },
    {
        "name": "rename_section",
        "description": "Rename a section in a document",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the target file",
                },
                "section_name": {
                    "type": "string",
                    "description": "Current name of the section",
                },
                "new_name": {
                    "type": "string",
                    "description": "New name for the section",
                },
            },
            "required": ["file_name", "section_name", "new_name"],
        },
    },
    {
        "name": "export_document",
        "description": "Export a document to a different format",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to export",
                },
                "export_format": {
                    "type": "string",
                    "description": "Format to export to (pdf, docx, html)",
                },
            },
            "required": ["file_name", "export_format"],
        },
    },
    {
        "name": "list_documents",
        "description": "List all documents in the workspace",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_document_content",
        "description": "Get the content of a document",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to retrieve",
                }
            },
            "required": ["file_name"],
        },
    },
    {
        "name": "get_workspace_summary",
        "description": "Get a summary of all documents in the workspace",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "insert_section",
        "description": "Insert a new section at a specific position in a document",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the target file",
                },
                "section_name": {
                    "type": "string",
                    "description": "Name of the section to insert",
                },
                "text_content": {
                    "type": "string",
                    "description": "Content for the new section",
                },
                "position": {
                    "type": "string",
                    "description": "Where to insert the section: 'beginning', 'end', or 'after:SectionName'",
                },
            },
            "required": ["file_name", "section_name", "text_content", "position"],
        },
    },
    {
        "name": "validate_document",
        "description": "Validate a document's structure and fix common issues like duplicate headings",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to validate",
                },
            },
            "required": ["file_name"],
        },
    },
]


# -------------------------------------------------------------------------
# Tool Execution Functions
# -------------------------------------------------------------------------
def execute_tool_call(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool call based on the tool name and input."""
    logger.info(f"Executing tool call: {tool_name} with input: {tool_input}")

    try:
        if tool_name == "create_document":
            file_name = tool_input.get("file_name", "")
            text_content = tool_input.get("text_content", "")

            result = DocumentManager.create_document(file_name, text_content)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            # Get the actual filename that was used (might be UUID-generated)
            actual_filename = result["file_name"]

            return {
                "success": True,
                "message": f"Document {actual_filename} created successfully",
                "file_name": actual_filename,
            }

        elif tool_name == "add_section":
            file_name = tool_input.get("file_name", "")
            section_name = tool_input.get("section_name", "")
            text_content = tool_input.get("text_content", "")

            result = DocumentManager.add_section(file_name, section_name, text_content)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "message": f"Section {section_name} added to {file_name}",
                "file_name": file_name,
                "section_name": section_name,
            }

        elif tool_name == "append_block":
            file_name = tool_input.get("file_name", "")
            section_name = tool_input.get("section_name", "")
            text_content = tool_input.get("text_content", "")

            result = DocumentManager.append_block(file_name, section_name, text_content)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "message": f"Text appended to section {section_name} in {file_name}",
                "file_name": file_name,
                "section_name": section_name,
            }

        elif tool_name == "replace_section":
            file_name = tool_input.get("file_name", "")
            section_name = tool_input.get("section_name", "")
            text_content = tool_input.get("text_content", "")

            result = DocumentManager.replace_section(
                file_name, section_name, text_content
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "message": f"Section {section_name} replaced in {file_name}",
                "file_name": file_name,
                "section_name": section_name,
            }

        elif tool_name == "remove_section":
            file_name = tool_input.get("file_name", "")
            section_name = tool_input.get("section_name", "")

            result = DocumentManager.remove_section(file_name, section_name)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "message": f"Section {section_name} removed from {file_name}",
                "file_name": file_name,
                "section_name": section_name,
            }

        elif tool_name == "rename_section":
            file_name = tool_input.get("file_name", "")
            section_name = tool_input.get("section_name", "")
            new_name = tool_input.get("new_name", "")

            result = DocumentManager.rename_section(file_name, section_name, new_name)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "message": f"Section {section_name} renamed to {new_name} in {file_name}",
                "file_name": file_name,
                "section_name": new_name,
            }

        elif tool_name == "export_document":
            file_name = tool_input.get("file_name", "")
            export_format = tool_input.get("export_format", "")

            result = DocumentManager.export_document(file_name, export_format)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "message": f"Document {file_name} exported to {export_format} format",
                "file_name": file_name,
                "export_format": export_format,
            }

        elif tool_name == "list_documents":
            documents = DocumentManager.list_documents()

            return {
                "success": True,
                "message": f"Found {len(documents)} documents in workspace",
                "documents": documents,
            }

        elif tool_name == "get_document_content":
            file_name = tool_input.get("file_name", "")

            result = DocumentManager.get_document_content(file_name)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "message": f"Retrieved content of {file_name}",
                "file_name": file_name,
                "content": result["content"],
            }

        elif tool_name == "get_workspace_summary":
            summary = get_workspace_summary()

            return {
                "success": True,
                "message": f"Retrieved workspace summary with {len(summary['documents'])} documents",
                "summary": summary,
            }

        elif tool_name == "insert_section":
            file_name = tool_input.get("file_name", "")
            section_name = tool_input.get("section_name", "")
            text_content = tool_input.get("text_content", "")
            position = tool_input.get("position", "")

            result = DocumentManager.insert_section(
                file_name, section_name, text_content, position
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "message": f"Section {section_name} inserted at {position} in {file_name}",
                "file_name": file_name,
                "section_name": section_name,
            }

        elif tool_name == "validate_document":
            file_name = tool_input.get("file_name", "")

            result = DocumentManager.validate_document(file_name)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            if result.get("issues_found", False):
                return {
                    "success": True,
                    "message": f"Document {file_name} validated and issues fixed: {result.get('fixed_issues', '')}",
                    "file_name": file_name,
                    "fixed_issues": result.get("fixed_issues", ""),
                }
            else:
                return {
                    "success": True,
                    "message": f"Document {file_name} validated. No issues found.",
                    "file_name": file_name,
                }

        else:
            return {"success": False, "message": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error executing tool {tool_name}: {str(e)}",
        }


# -------------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------------
@app.post(
    "/workspace/query",
    summary="Process a natural language query for document operations",
)
async def process_workspace_query(query: WorkspaceQuery):
    """
    Process a natural language query and perform the requested document operations.
    This endpoint acts as a natural language interface to all document operations.
    """
    correlation_id = str(uuid.uuid4())
    logger.info(
        f"Processing workspace query (correlation_id: {correlation_id}): {query.query}"
    )

    # System instruction for the document agent
    system_instruction = (
        "You are a document workspace agent that can create, edit, and manage markdown documents. "
        "Your task is to understand the user's request and use the appropriate tools to fulfill it. "
        "You are responsible for ALL document operations - the main agent will delegate document tasks to you completely.\n\n"
        "DOCUMENT OPERATION WORKFLOW:\n"
        "1. Analyze the user's request to understand what document operations are needed.\n"
        "2. Plan the sequence of operations required (get content, modify, validate, update).\n"
        "3. Execute all necessary operations using your internal tools.\n"
        "4. Validate the final document structure before completing the task.\n"
        "5. Provide a clear summary of what was done.\n\n"
        "DOCUMENT STRUCTURE GUIDELINES:\n"
        "1. Maintain clean, consistent document structure with proper heading hierarchy.\n"
        "2. Avoid duplicate headings or sections - check for duplicates before saving.\n"
        "3. When adding new sections, place them in the logical position in the document.\n"
        "4. When updating content, preserve existing formatting unless explicitly asked to change it.\n"
        "5. Always validate document structure after making changes.\n\n"
        "CITATION AND REFERENCE GUIDELINES (CRITICAL - ALWAYS FOLLOW THESE):\n"
        "1. ALWAYS preserve citation information provided in the user's request.\n"
        "2. NEVER remove or modify citation numbers [1], [2], etc. within the text.\n"
        "3. ALWAYS maintain the 'References' section exactly as provided in the user's request.\n"
        "4. If the user's request includes citations but no References section, create one at the end.\n"
        "5. When adding new information with citations, add the corresponding references.\n"
        "6. Include full citation details: author, title, publication, date, URL (if applicable).\n"
        "7. The main agent depends on you preserving all citation information exactly as provided.\n\n"
        "ERROR HANDLING:\n"
        "1. If you encounter an error, try an alternative approach rather than giving up.\n"
        "2. For complex operations, break them down into smaller steps.\n"
        "3. If a document has structural issues, fix them before proceeding with the requested operation.\n"
        "4. Always verify the final result matches what was requested."
    )

    try:
        # Get the current workspace state to provide context
        workspace_summary = get_workspace_summary()

        # Construct the prompt with the workspace context
        workspace_context = "Current workspace state:\n"

        if not workspace_summary["documents"]:
            workspace_context += (
                "The workspace is currently empty. No documents exist yet."
            )
        else:
            workspace_context += f"The workspace contains {len(workspace_summary['documents'])} documents:\n"
            for doc in workspace_summary["documents"]:
                workspace_context += f"- {doc['file_name']} with sections: {', '.join(doc['sections'])}\n"

        prompt = (
            f"User request: {query.query}\n\n"
            f"{workspace_context}\n\n"
            "Based on the user's request and the current workspace state, determine what document operation to perform. "
            "Use the appropriate tool to fulfill the request."
        )

        # Call Anthropic with tools
        response = anthropic_client.generate_with_tools(
            prompt=prompt, system_instruction=system_instruction, tools=DOCUMENT_TOOLS
        )

        # Process tool calls if any
        tool_results = []
        for tool_call in response.get("tool_calls", []):
            tool_name = tool_call["name"]
            tool_input = tool_call["input"]

            logger.info(f"Executing tool call: {tool_name} with input: {tool_input}")

            # Execute the tool call
            result = execute_tool_call(tool_name, tool_input)
            tool_results.append(
                {"tool": tool_name, "input": tool_input, "result": result}
            )

        # Construct the final response
        if tool_results:
            # If tools were used, summarize the results
            success_count = sum(1 for r in tool_results if r["result"]["success"])
            failure_count = len(tool_results) - success_count

            status = (
                "success"
                if failure_count == 0
                else "partial_success" if success_count > 0 else "failure"
            )

            # Construct a message summarizing what was done
            message = response.get("text", "")
            if not message:
                if status == "success":
                    message = "I've successfully completed your request."
                elif status == "partial_success":
                    message = "I've partially completed your request. Some operations succeeded, but others failed."
                else:
                    message = "I couldn't complete your request due to errors."

                # Add details about each operation
                for result in tool_results:
                    message += f"\n- {result['result']['message']}"

            return {
                "correlation_id": correlation_id,
                "query": query.query,
                "status": status,
                "message": message,
                "tool_results": tool_results,
            }
        else:
            # If no tools were used, just return the model's response
            return {
                "correlation_id": correlation_id,
                "query": query.query,
                "status": "success",
                "message": response.get(
                    "text",
                    "I understood your request but didn't need to perform any document operations.",
                ),
                "tool_results": [],
            }

    except Exception as e:
        logger.error(f"Error processing workspace query: {str(e)}", exc_info=True)
        return {
            "correlation_id": correlation_id,
            "query": query.query,
            "status": "error",
            "message": f"An error occurred while processing your request: {str(e)}",
            "tool_results": [],
        }


# -------------------------------------------------------------------------
# Health Check Endpoint
# -------------------------------------------------------------------------
@app.get("/health", summary="Health check endpoint")
async def health_check():
    """Check if the service is healthy."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# -------------------------------------------------------------------------
# Main Entry Point
# -------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    # Ensure workspace directory exists
    from app.utils import ensure_workspace_exists

    ensure_workspace_exists()

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
