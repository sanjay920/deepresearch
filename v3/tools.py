import requests
import logging
import json
import os
from typing import Dict, Any


def google_search(q: str) -> Dict[str, Any]:
    """
    Performs a Google search via local microservice.

    Args:
        q: The search query string

    Returns:
        Dict containing search results or error
    """
    try:
        response = requests.get("http://localhost:8085/search", params={"q": q})
        response.raise_for_status()
        result = response.json()
        logging.info(
            f"Search for '{q}' returned {len(result.get('items', []))} results"
        )
        return result
    except Exception as e:
        logging.error(f"Search error: {e}")
        return {"error": str(e), "items": []}


def web_research(url: str, query: str) -> Dict[str, Any]:
    """
    Research a specific webpage to answer a question.
    Uses the web research microservice to do targeted extraction.

    Args:
        url: The URL to research
        query: The specific question to answer

    Returns:
        Dict containing the research result or error
    """
    try:
        response = requests.post(
            "http://localhost:8090/research", json={"url": url, "query": query}
        )
        response.raise_for_status()
        result = response.json()
        logging.info(f"Web research for '{query}' on {url} completed")
        return result
    except Exception as e:
        logging.error(f"Web research error: {e}")
        return {"error": str(e), "answer": f"Failed to research {url}: {str(e)}"}


def notion_agent(query: str) -> Dict[str, Any]:
    """
    Sends a natural language query to the Notion document agent.

    Args:
        query: Natural language instruction for Notion document operations

    Returns:
        Dict containing the response from the Notion agent
    """
    try:
        # Add specific formatting guidance with examples of proper Notion blocks
        enhanced_query = (
            f"{query}\n\n"
            "IMPORTANT: The content currently being created in Notion looks poorly formatted. "
            "Please ensure all content is properly formatted using Notion's native block structure. "
            "DO NOT use raw markdown or plain text with URLs. Instead:\n\n"
            "1. For headings, use proper heading blocks:\n"
            "   - heading_1 for main titles\n"
            "   - heading_2 for section headers\n"
            "   - heading_3 for subsections\n\n"
            "2. For links, embed them properly in text using the link property:\n"
            "   - Bad: 'Check website: https://example.com'\n"
            "   - Good: Text with the URL embedded as a proper link\n\n"
            "3. For lists, use proper bulleted_list_item or numbered_list_item blocks\n\n"
            "4. For tables, use proper table blocks with table_rows and cells\n\n"
            "5. For paragraphs, use paragraph blocks with properly formatted rich_text\n\n"
            "Example of a properly formatted paragraph with a link:\n"
            "{\n"
            '  "paragraph": {\n'
            '    "rich_text": [\n'
            "      {\n"
            '        "type": "text",\n'
            '        "text": {\n'
            '          "content": "Visit ",\n'
            '          "link": null\n'
            "        }\n"
            "      },\n"
            "      {\n"
            '        "type": "text",\n'
            '        "text": {\n'
            '          "content": "Basketball Reference",\n'
            '          "link": {\n'
            '            "url": "https://www.basketball-reference.com/players/j/jamesle01.html"\n'
            "          }\n"
            "        },\n"
            '        "annotations": {\n'
            '          "bold": true,\n'
            '          "color": "blue"\n'
            "        }\n"
            "      },\n"
            "      {\n"
            '        "type": "text",\n'
            '        "text": {\n'
            '          "content": " for LeBron James statistics.",\n'
            '          "link": null\n'
            "        }\n"
            "      }\n"
            "    ]\n"
            "  }\n"
            "}\n\n"
            "Example of a proper heading:\n"
            "{\n"
            '  "heading_2": {\n'
            '    "rich_text": [\n'
            "      {\n"
            '        "type": "text",\n'
            '        "text": {\n'
            '          "content": "LeBron James Career Statistics",\n'
            '          "link": null\n'
            "        }\n"
            "      }\n"
            "    ]\n"
            "  }\n"
            "}\n\n"
            "ENSURE all content is properly structured for Notion's native display."
        )

        # Log the query for debugging
        logging.info(f"Sending query to Notion agent: {enhanced_query}")

        response = requests.post(
            "http://localhost:8092/notion/query", json={"query": enhanced_query}
        )
        response.raise_for_status()
        result = response.json()
        logging.info(f"Notion agent response: {result}")

        # Extract the important information from the response
        correlation_id = result.get("correlation_id", "")
        status = result.get("status", "")
        message = result.get("message", "")
        tool_results = result.get("tool_results", [])

        # Create a summary of operations performed
        operations_summary = ""
        if tool_results:
            operations_summary = "\n\nOperations performed:\n"
            for i, tool_result in enumerate(tool_results, 1):
                tool_name = tool_result.get("tool", "unknown")
                tool_input = tool_result.get("input", {})
                result_data = tool_result.get("result", {})

                # Extract the most relevant information based on the tool type
                if tool_name == "create_document" and result_data.get("success"):
                    page_id = result_data.get("page_id", "")
                    title = result_data.get("title", "")
                    url = result_data.get("url", "")
                    operations_summary += f"{i}. Created document: '{title}' (ID: {page_id})\n   URL: {url}\n"

                elif tool_name == "get_document" and result_data.get("success"):
                    title = result_data.get("title", "")
                    operations_summary += f"{i}. Retrieved document: '{title}'\n"

                elif tool_name == "search_documents" and result_data.get("success"):
                    documents = result_data.get("documents", [])
                    doc_count = len(documents)
                    operations_summary += f"{i}. Found {doc_count} documents\n"
                    # List the first few documents
                    for j, doc in enumerate(documents[:5], 1):
                        doc_title = doc.get("title", "")
                        doc_id = doc.get("page_id", "")
                        operations_summary += f"   {j}. '{doc_title}' (ID: {doc_id})\n"
                    if doc_count > 5:
                        operations_summary += f"   ... and {doc_count - 5} more\n"

                else:
                    # Generic handling for other tool types
                    success = result_data.get("success", False)
                    result_msg = result_data.get("message", "No details")
                    operations_summary += f"{i}. {tool_name}: {result_msg}\n"

        # Include the raw response for debugging if needed
        return {
            "status": status,
            "message": message + operations_summary,
            "correlation_id": correlation_id,
            "raw_response": result,
        }
    except Exception as e:
        error_msg = f"Notion agent error: {str(e)}"
        logging.error(error_msg)
        return {
            "error": error_msg,
            "message": f"Failed to process Notion document operation: {str(e)}",
        }


# Document manipulation functions
def _ensure_workspace_dir():
    """Ensures the workspace directory exists."""
    workspace_dir = "./workspace"
    if not os.path.exists(workspace_dir):
        os.makedirs(workspace_dir)
    return workspace_dir


def _read_file_lines(file_path):
    """Utility to read file lines safely."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.readlines()
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {str(e)}")
        return []


def _write_file_lines(file_path, lines):
    """Utility to write lines to file safely."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True
    except Exception as e:
        logging.error(f"Error writing to file {file_path}: {str(e)}")
        return False


def create_document(file_name: str, text_content: str = "") -> Dict[str, Any]:
    """
    Creates or overwrites a Markdown research document.

    Args:
        file_name: Name of the markdown file
        text_content: Optional initial text to place in the document

    Returns:
        Dict containing status information
    """
    try:
        workspace_dir = _ensure_workspace_dir()
        file_path = os.path.join(workspace_dir, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text_content)

        logging.info(f"Document created: {file_name}")
        return {"status": "created", "file": file_name}
    except Exception as e:
        error_msg = f"Failed to create document {file_name}: {str(e)}"
        logging.error(error_msg)
        return {"error": error_msg}


def add_section(
    file_name: str, section_name: str, text_content: str = ""
) -> Dict[str, Any]:
    """
    Adds a new section to an existing markdown file.

    Args:
        file_name: The markdown file to modify
        section_name: The name/title of the new section to create
        text_content: Optional text content to include below the heading

    Returns:
        Dict containing status information
    """
    try:
        workspace_dir = _ensure_workspace_dir()
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File '{file_name}' does not exist."}

        lines = _read_file_lines(file_path)
        heading_str = f"# {section_name}"

        if any(heading_str in line for line in lines):
            return {
                "error": f"Section '{section_name}' already exists in '{file_name}'."
            }

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n# {section_name}\n{text_content}\n")

        logging.info(f"Section '{section_name}' added to {file_name}")
        return {"status": "section_added", "section_name": section_name}
    except Exception as e:
        error_msg = f"Failed to add section to {file_name}: {str(e)}"
        logging.error(error_msg)
        return {"error": error_msg}


def append_block(
    file_name: str, section_name: str, text_content: str
) -> Dict[str, Any]:
    """
    Appends additional text to an existing section in a markdown file.

    Args:
        file_name: The markdown file to modify
        section_name: The name of the existing section to append to
        text_content: The text block to add at the end of that section

    Returns:
        Dict containing status information
    """
    try:
        workspace_dir = _ensure_workspace_dir()
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File '{file_name}' does not exist."}

        lines = _read_file_lines(file_path)
        heading_variants = [
            f"# {section_name}",
            f"## {section_name}",
            f"### {section_name}",
        ]

        # Check if section exists
        if not any(any(hv in line for hv in heading_variants) for line in lines):
            return {"error": f"Section '{section_name}' not found in '{file_name}'."}

        # For simplicity, we'll just append to the end of the file
        # A more sophisticated implementation would find the exact section
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n{text_content}\n")

        logging.info(f"Text appended to section '{section_name}' in {file_name}")
        return {"status": "block_appended", "section": section_name}
    except Exception as e:
        error_msg = f"Failed to append block to {file_name}: {str(e)}"
        logging.error(error_msg)
        return {"error": error_msg}


def replace_section(
    file_name: str, section_name: str, text_content: str
) -> Dict[str, Any]:
    """
    Overwrites the entire content of a named section with new text.

    Args:
        file_name: The markdown file to modify
        section_name: Name of the section to replace
        text_content: The text that replaces everything in that section

    Returns:
        Dict containing status information
    """
    try:
        workspace_dir = _ensure_workspace_dir()
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File '{file_name}' does not exist."}

        lines = _read_file_lines(file_path)
        heading_variants = [
            f"# {section_name}",
            f"## {section_name}",
            f"### {section_name}",
            f"#### {section_name}",
        ]

        new_lines = []
        inside_target = False
        replaced = False

        i = 0
        while i < len(lines):
            line = lines[i]
            if any(line.strip().startswith(hv) for hv in heading_variants):
                # Start of our section
                inside_target = True
                replaced = True
                # Insert heading
                new_lines.append(line)
                # Insert the replacement text
                new_lines.append(text_content + "\n")
                # Skip lines until next heading
                i += 1
                while i < len(lines):
                    # if we see another heading, break
                    if lines[i].startswith("#"):
                        break
                    i += 1
                # Don't increment i again here, so we check the next line in the loop
                continue
            else:
                new_lines.append(line)
            i += 1

        if not replaced:
            # If we didn't find that heading, create it at the end
            new_lines.append(f"\n# {section_name}\n{text_content}\n")

        _write_file_lines(file_path, new_lines)

        logging.info(f"Section '{section_name}' replaced in {file_name}")
        return {"status": "section_replaced", "section_name": section_name}
    except Exception as e:
        error_msg = f"Failed to replace section in {file_name}: {str(e)}"
        logging.error(error_msg)
        return {"error": error_msg}


def remove_section(file_name: str, section_name: str) -> Dict[str, Any]:
    """
    Removes an entire section by name from the markdown file.

    Args:
        file_name: The markdown file to modify
        section_name: Name of the section to remove

    Returns:
        Dict containing status information
    """
    try:
        workspace_dir = _ensure_workspace_dir()
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File '{file_name}' does not exist."}

        lines = _read_file_lines(file_path)
        heading_variants = [
            f"# {section_name}",
            f"## {section_name}",
            f"### {section_name}",
            f"#### {section_name}",
        ]

        new_lines = []
        removed = False

        i = 0
        while i < len(lines):
            line = lines[i]
            # If we see the section heading, skip until next heading
            if any(line.strip().startswith(hv) for hv in heading_variants):
                removed = True
                i += 1
                while i < len(lines):
                    if lines[i].startswith("#"):
                        break
                    i += 1
            else:
                new_lines.append(line)
                i += 1

        if not removed:
            return {"error": f"Section '{section_name}' not found in '{file_name}'."}

        _write_file_lines(file_path, new_lines)

        logging.info(f"Section '{section_name}' removed from {file_name}")
        return {"status": "section_removed", "section_name": section_name}
    except Exception as e:
        error_msg = f"Failed to remove section from {file_name}: {str(e)}"
        logging.error(error_msg)
        return {"error": error_msg}


def rename_section(
    file_name: str, section_name: str, text_content: str
) -> Dict[str, Any]:
    """
    Renames an existing section heading in the markdown file.

    Args:
        file_name: The markdown file to modify
        section_name: Existing section name to rename
        text_content: The new name for this section heading

    Returns:
        Dict containing status information
    """
    try:
        workspace_dir = _ensure_workspace_dir()
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File '{file_name}' does not exist."}

        lines = _read_file_lines(file_path)
        heading_variants = [
            f"# {section_name}",
            f"## {section_name}",
            f"### {section_name}",
            f"#### {section_name}",
        ]

        new_lines = []
        renamed = False

        for line in lines:
            stripped_line = line.strip()
            if any(stripped_line.startswith(hv) for hv in heading_variants):
                # rename the heading
                # keep the same number of #, just rename the text
                prefix = stripped_line.split(section_name)[0]  # e.g. "# " or "## "
                new_line = prefix + text_content + "\n"
                new_lines.append(new_line)
                renamed = True
            else:
                new_lines.append(line)

        if not renamed:
            return {"error": f"Section '{section_name}' not found in '{file_name}'."}

        _write_file_lines(file_path, new_lines)

        logging.info(
            f"Section '{section_name}' renamed to '{text_content}' in {file_name}"
        )
        return {
            "status": "section_renamed",
            "old_section": section_name,
            "new_section": text_content,
        }
    except Exception as e:
        error_msg = f"Failed to rename section in {file_name}: {str(e)}"
        logging.error(error_msg)
        return {"error": error_msg}


def export_document(file_name: str, export_format: str) -> Dict[str, Any]:
    """
    Converts an existing markdown file to a specified format.

    Args:
        file_name: The markdown file to export
        export_format: The desired output format (docx, pdf, md, html)

    Returns:
        Dict containing status information
    """
    try:
        workspace_dir = _ensure_workspace_dir()
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File '{file_name}' does not exist."}

        # In a real implementation, you would use a library like Pandoc to convert
        # For now, we'll just simulate the export

        output_file = os.path.splitext(file_name)[0] + "." + export_format
        output_path = os.path.join(workspace_dir, output_file)

        # Simulate export by copying the file (in a real implementation, use proper conversion)
        with open(file_path, "r", encoding="utf-8") as src:
            content = src.read()

        with open(output_path, "w", encoding="utf-8") as dest:
            dest.write(content)

        logging.info(f"Document '{file_name}' exported to {output_file}")
        return {
            "status": "exported",
            "original_file": file_name,
            "export_format": export_format,
            "output_file": output_file,
        }
    except Exception as e:
        error_msg = f"Failed to export document {file_name}: {str(e)}"
        logging.error(error_msg)
        return {"error": error_msg}
