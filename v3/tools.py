import requests
import logging
import json
import os
import anthropic
import time
import uuid
from typing import Dict, Any
from config import CONFIG, SYSTEM_PROMPT, TOOLS

# Define a maximum recursion depth to prevent infinite loops
MAX_DEEPSEARCH_DEPTH = 20


def google_search(q: str, include_images: bool = False) -> Dict[str, Any]:
    """
    Performs a Google search via local microservice.

    Args:
        q: The search query string
        include_images: Whether to include image-related fields in the results (default: False)

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

        # Optimize search results to reduce token usage
        optimized_result = _optimize_search_results(result, include_images)

        # Save search results to a JSON file (save both original and optimized)
        _save_search_to_json(q, result, optimized_result)

        return optimized_result
    except Exception as e:
        logging.error(f"Search error: {e}")
        error_result = {"error": str(e), "items": []}

        # Save error result to a JSON file
        _save_search_to_json(q, error_result)

        return error_result


def _optimize_search_results(
    result: Dict[str, Any], include_images: bool = False
) -> Dict[str, Any]:
    """
    Optimize search results to reduce token usage.

    This function:
    1. Trims snippets to a reasonable length
    2. Removes unnecessary fields from pagemap
    3. Keeps only the most relevant information
    4. Optionally includes or excludes image-related fields

    Args:
        result: The original search result dictionary
        include_images: Whether to include image-related fields (default: False)

    Returns:
        Dict containing optimized search results
    """
    optimized = {}

    # Copy only essential top-level fields
    if "items" in result:
        items = result["items"]

        optimized_items = []
        for item in items:
            optimized_item = {}

            # Keep only essential fields
            for key in ["title", "link", "displayLink", "snippet"]:
                if key in item:
                    # For snippet, truncate if too long (over 150 chars)
                    if key == "snippet" and len(item[key]) > 150:
                        optimized_item[key] = item[key][:147] + "..."
                    else:
                        optimized_item[key] = item[key]

            # Handle pagemap more carefully - it can be very token-heavy
            if "pagemap" in item:
                optimized_pagemap = {}
                pagemap = item["pagemap"]

                # Determine which fields to keep based on include_images parameter
                useful_fields = ["metatags"]
                if include_images:
                    useful_fields.extend(["cse_thumbnail", "cse_image"])

                for field in useful_fields:
                    if field in pagemap:
                        # For thumbnails and images, just keep the src URL
                        if (
                            include_images
                            and field in ["cse_thumbnail", "cse_image"]
                            and isinstance(pagemap[field], list)
                        ):
                            optimized_entries = []
                            for entry in pagemap[field]:
                                if isinstance(entry, dict) and "src" in entry:
                                    optimized_entries.append({"src": entry["src"]})
                            if optimized_entries:
                                optimized_pagemap[field] = optimized_entries

                        # For metatags, only keep a few important ones
                        elif field == "metatags" and isinstance(pagemap[field], list):
                            optimized_metatags = []
                            for metatag in pagemap[field]:
                                if isinstance(metatag, dict):
                                    important_tags = {}
                                    for tag_key, tag_value in metatag.items():
                                        # Check if tag contains important keywords
                                        keywords = ["title", "description"]
                                        keywords.extend(["og:", "twitter:"])

                                        # Only include image-related metatags if include_images is True
                                        image_keywords = [
                                            "image",
                                            "thumbnail",
                                            "icon",
                                            "logo",
                                        ]
                                        if include_images and any(
                                            img_kw in tag_key.lower()
                                            for img_kw in image_keywords
                                        ):
                                            important_tags[tag_key] = tag_value
                                        elif any(
                                            keyword in tag_key.lower()
                                            for keyword in keywords
                                        ):
                                            important_tags[tag_key] = tag_value

                                    if important_tags:
                                        optimized_metatags.append(important_tags)
                            if optimized_metatags:
                                optimized_pagemap[field] = optimized_metatags

                # Only add pagemap if we have optimized content
                if optimized_pagemap:
                    optimized_item["pagemap"] = optimized_pagemap

            optimized_items.append(optimized_item)

        optimized["items"] = optimized_items

    # Add any error information if present
    if "error" in result:
        optimized["error"] = result["error"]

    # Add a flag indicating whether images were included
    optimized["_includes_images"] = include_images

    return optimized


def _save_search_to_json(
    query: str, result: Dict[str, Any], optimized_result: Dict[str, Any] = None
) -> None:
    """
    Save Google search results to a JSON file in the workspace directory.

    Args:
        query: The search query
        result: The original search result dictionary
        optimized_result: The optimized search result dictionary (optional)
    """
    try:
        # Ensure workspace directory exists
        workspace_dir = _ensure_workspace_dir()

        # Create a searches directory if it doesn't exist
        searches_dir = os.path.join(workspace_dir, "searches")
        if not os.path.exists(searches_dir):
            os.makedirs(searches_dir)

        # Create a filename using UUID for uniqueness
        unique_id = str(uuid.uuid4())
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"search_{timestamp}_{unique_id}.json"
        filepath = os.path.join(searches_dir, filename)

        # Create metadata to include with the results
        search_data = {
            "query": query,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": result,
        }

        # Add optimized results if provided
        if optimized_result is not None:
            search_data["optimized_results"] = optimized_result

            # Add image inclusion information to metadata
            if "_includes_images" in optimized_result:
                search_data["includes_images"] = optimized_result["_includes_images"]

            # Calculate token savings if possible
            try:
                import json

                original_json = json.dumps(result)
                optimized_json = json.dumps(optimized_result)
                original_size = len(original_json)
                optimized_size = len(optimized_json)
                savings_percent = (
                    ((original_size - optimized_size) / original_size) * 100
                    if original_size > 0
                    else 0
                )

                search_data["optimization_stats"] = {
                    "original_size_chars": original_size,
                    "optimized_size_chars": optimized_size,
                    "size_reduction_percent": round(savings_percent, 2),
                }

                logging.info(
                    f"Search result optimization: {round(savings_percent, 2)}% reduction in size"
                )
            except Exception as e:
                logging.error(f"Error calculating optimization stats: {e}")

        # Write to file with pretty formatting
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(search_data, f, indent=2, ensure_ascii=False)

        logging.info(f"Saved search results to {filepath}")

        # Add file path to result for reference
        if optimized_result is not None:
            optimized_result["_saved_to_file"] = filepath
        else:
            result["_saved_to_file"] = filepath

    except Exception as e:
        logging.error(f"Failed to save search to JSON: {e}")
        # Don't raise the exception, just log it


def web_research(url: str, query: str) -> Dict[str, Any]:
    """
    Research a specific webpage to answer a question.
    Uses the web research microservice to do targeted extraction.
    Saves the research results to a markdown file in the workspace directory.

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

        # Save the research result to a markdown file
        _save_research_to_markdown(url, query, result)

        return result
    except Exception as e:
        logging.error(f"Web research error: {e}")
        error_result = {
            "error": str(e),
            "answer": f"Failed to research {url}: {str(e)}",
        }

        # Save the error result to a markdown file
        _save_research_to_markdown(url, query, error_result)

        return error_result


def _save_research_to_markdown(url: str, query: str, result: Dict[str, Any]) -> None:
    """
    Save web research results to a markdown file in the workspace directory.

    Args:
        url: The URL that was researched
        query: The query that was asked
        result: The research result dictionary
    """
    try:
        # Ensure workspace directory exists
        workspace_dir = _ensure_workspace_dir()

        # Create a research directory if it doesn't exist
        research_dir = os.path.join(workspace_dir, "research")
        if not os.path.exists(research_dir):
            os.makedirs(research_dir)

        # Create a filename using UUID for uniqueness
        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}.md"
        filepath = os.path.join(research_dir, filename)

        # Format the content
        content = f"# Web Research: {query}\n\n"
        content += f"## URL\n{url}\n\n"
        content += f"## Query\n{query}\n\n"
        content += "## Result\n"

        if "error" in result:
            content += f"### Error\n{result['error']}\n\n"

        if "answer" in result:
            content += f"### Answer\n{result['answer']}\n\n"

        # Add any additional data from the result
        for key, value in result.items():
            if key not in ["error", "answer"]:
                content += f"### {key.capitalize()}\n"
                if isinstance(value, dict) or isinstance(value, list):
                    content += f"```json\n{json.dumps(value, indent=2)}\n```\n\n"
                else:
                    content += f"{value}\n\n"

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logging.info(f"Saved research results to {filepath}")

        # Add file path to result for reference
        result["_saved_to_file"] = filepath

    except Exception as e:
        logging.error(f"Failed to save research to markdown: {e}")
        # Don't raise the exception, just log it


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


def workspace_agent(query: str) -> Dict[str, Any]:
    """
    Sends a natural language query to the Document Workspace agent.

    Args:
        query: Natural language instruction for document operations

    Returns:
        Dict containing the response from the Workspace agent
    """
    try:
        response = requests.post(
            "http://localhost:8091/workspace/query", json={"query": query}, timeout=180
        )
        response.raise_for_status()
        result = response.json()
        logging.info(f"Workspace agent query completed: {query}")

        # Extract the most relevant information from the result
        operations_summary = ""

        # Check if there are tool results in the response
        if "tool_results" in result and result["tool_results"]:
            operations_summary = "Operations performed:\n"

            for i, tool_result in enumerate(result["tool_results"], 1):
                tool_name = tool_result.get("tool", "unknown")
                result_data = tool_result.get("result", {})

                # Extract information based on the tool type
                if result_data.get("success", False):
                    message = result_data.get("message", "Operation completed")
                    operations_summary += f"{i}. {message}\n"
                else:
                    error_msg = result_data.get("message", "Operation failed")
                    operations_summary += f"{i}. Error: {error_msg}\n"

        return {
            "status": result.get("status", "unknown"),
            "message": result.get("message", ""),
            "operations_summary": operations_summary,
            "correlation_id": result.get("correlation_id", ""),
        }
    except Exception as e:
        error_msg = f"Workspace agent error: {str(e)}"
        logging.error(error_msg)
        return {
            "error": error_msg,
            "message": f"Failed to process document operation: {str(e)}",
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


def deepsearch_tool(
    query: str, context: str = "", max_depth: int = None
) -> Dict[str, Any]:
    """
    Invokes a new DeepSearch 'mini-session' to handle a sub-task.
    It returns a structured result that can be used by the main conversation.
    This tool runs for as long as needed without a maximum depth restriction.

    Args:
        query: The main question or task to handle
        context: Optional additional context needed by DeepSearch
        max_depth: Optional parameter (ignored, kept for backward compatibility)

    Returns:
        Dict containing the research result or error
    """
    # Track recursion depth for informational purposes only
    current_depth = 0
    if context and '"__deepsearch_depth__":' in context:
        try:
            # Extract the current depth from the context
            depth_start = context.find('"__deepsearch_depth__":')
            depth_start += len('"__deepsearch_depth__":')
            depth_end = context.find(",", depth_start)
            if depth_end == -1:
                depth_end = context.find("}", depth_start)
            current_depth = int(context[depth_start:depth_end].strip())
        except Exception as e:
            logging.error(f"Error extracting recursion depth: {str(e)}")

    # Increment the recursion depth for this call (for tracking only)
    new_depth = current_depth + 1

    try:
        # Import here to avoid circular imports
        from conversation import Conversation

        # Create a new conversation object for this sub-task
        sub_conversation = Conversation()

        # Add context if provided
        if context.strip():
            # Add metadata about recursion depth to the context
            if '"__deepsearch_depth__":' not in context:
                # If context is JSON, add the depth to it
                if context.strip().startswith("{") and context.strip().endswith("}"):
                    try:
                        context_json = json.loads(context)
                        context_json["__deepsearch_depth__"] = new_depth
                        context = json.dumps(context_json)
                    except Exception:
                        # If not valid JSON, just append the depth info
                        context = f"{context}\n\n__deepsearch_depth__: {new_depth}"
                else:
                    # Not JSON, just append the depth info
                    context = f"{context}\n\n__deepsearch_depth__: {new_depth}"

            # Add the context as a system message
            sub_conversation.add_user_message(
                f"[Context for this DeepSearch sub-task]\n{context}"
            )

        # Add the actual query as the next user message
        sub_conversation.add_user_message(query)

        # Set up the anthropic client
        client = anthropic.Anthropic(api_key=CONFIG["anthropic_api_key"])

        # Create a modified system prompt for the sub-task
        sub_system_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"You are running in a DeepSearch sub-task mode with recursion "
            f"depth {new_depth}. "
            f"You must produce a concise, well-structured result that can be "
            f"used by the main conversation. "
            f"Focus on answering the specific query without unnecessary "
            f"elaboration. "
            f"You still have access to all tools, including nested DeepSearch "
            f"calls. "
            f"DO NOT engage in conversation or ask questions - your goal is "
            f"to independently research and provide a complete answer."
        )

        # Get current timestamp for this request
        current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        timestamped_system_prompt = (
            f"{sub_system_prompt}\n\nCurrent time: {current_timestamp}"
        )

        # Define a list to collect all content blocks
        all_content_blocks = []
        tool_calls = []

        # Stream the response from Claude
        with client.messages.stream(
            model=CONFIG["model"],
            max_tokens=CONFIG["max_tokens"],
            system=timestamped_system_prompt,
            messages=sub_conversation.get_messages(),
            temperature=CONFIG["temperature"],
            tools=TOOLS,
        ) as stream:
            current_block = None
            tool_input_json_parts = {}

            for event in stream:
                if event.type == "content_block_start":
                    block_type = event.content_block.type
                    current_block = {"type": block_type}

                    if block_type == "text":
                        current_block["text"] = ""
                    elif block_type == "tool_use":
                        current_block["id"] = event.content_block.id
                        current_block["name"] = event.content_block.name
                        current_block["input"] = event.content_block.input

                        # Only add to tool_calls if we have input parameters
                        if event.content_block.input:
                            tool_calls.append(
                                {
                                    "id": event.content_block.id,
                                    "name": event.content_block.name,
                                    "input": event.content_block.input,
                                }
                            )

                elif event.type == "content_block_delta":
                    delta_type = event.delta.type

                    if delta_type == "text_delta":
                        current_block["text"] += event.delta.text
                    elif delta_type == "input_json_delta":
                        # Handle partial JSON for tool inputs
                        if current_block and current_block["type"] == "tool_use":
                            tool_id = current_block.get("id")
                            if tool_id not in tool_input_json_parts:
                                tool_input_json_parts[tool_id] = ""

                            # Append the partial JSON
                            if hasattr(event.delta, "partial_json"):
                                tool_input_json_parts[
                                    tool_id
                                ] += event.delta.partial_json

                                # Try to parse the JSON if it looks complete
                                json_str = tool_input_json_parts[tool_id]
                                if json_str and (
                                    json_str.startswith("{") and json_str.endswith("}")
                                ):
                                    try:
                                        # Parse the complete JSON
                                        input_params = json.loads(json_str)

                                        # Update the current block
                                        current_block["input"] = input_params

                                        # Update or add to tool_calls
                                        tool_call_exists = False
                                        for tool_call in tool_calls:
                                            if tool_call["id"] == tool_id:
                                                tool_call["input"] = input_params
                                                tool_call_exists = True
                                                break

                                        if not tool_call_exists:
                                            tool_calls.append(
                                                {
                                                    "id": tool_id,
                                                    "name": current_block["name"],
                                                    "input": input_params,
                                                }
                                            )
                                    except Exception:
                                        # JSON is not complete yet, continue collecting
                                        pass

                elif event.type == "content_block_stop":
                    if current_block:
                        all_content_blocks.append(current_block)
                        current_block = None

            # Add assistant's response to conversation history
            sub_conversation.add_assistant_message(all_content_blocks)

            # Handle tool calls if any
            for tool_call in tool_calls:
                # Import here to avoid circular imports
                from cli import execute_tool_call

                # Execute the tool call
                result = execute_tool_call(tool_call)

                # Add the tool result to the conversation
                try:
                    result_str = json.dumps(result)
                except Exception:
                    result_str = json.dumps(
                        {"error": "Failed to convert result to JSON"}
                    )

                sub_conversation.add_tool_result(tool_call["id"], result_str)

                # Process the conversation again to get the final result
                with client.messages.stream(
                    model=CONFIG["model"],
                    max_tokens=CONFIG["max_tokens"],
                    system=timestamped_system_prompt,
                    messages=sub_conversation.get_messages(),
                    temperature=CONFIG["temperature"],
                    tools=TOOLS,
                ) as stream:
                    final_content_blocks = []
                    current_block = None

                    for event in stream:
                        if event.type == "content_block_start":
                            block_type = event.content_block.type
                            current_block = {"type": block_type}

                            if block_type == "text":
                                current_block["text"] = ""
                            elif block_type == "tool_use":
                                current_block["id"] = event.content_block.id
                                current_block["name"] = event.content_block.name
                                current_block["input"] = event.content_block.input

                        elif event.type == "content_block_delta":
                            delta_type = event.delta.type

                            if delta_type == "text_delta":
                                current_block["text"] += event.delta.text

                        elif event.type == "content_block_stop":
                            if current_block:
                                final_content_blocks.append(current_block)
                                current_block = None

                    # Add assistant's final response to conversation history
                    sub_conversation.add_assistant_message(final_content_blocks)

        # Extract the final text response from the conversation
        final_response = ""
        for message in reversed(sub_conversation.get_messages()):
            if message["role"] == "assistant":
                for block in message.get("content", []):
                    if block["type"] == "text":
                        final_response = block.get("text", "")
                        break
                if final_response:
                    break

        # Return the result in a standardized format
        return {
            "result": final_response,
            "metadata": {
                "subtask": True,
                "recursion_depth": new_depth,
                "context_used": context,
                "query": query,
            },
        }

    except Exception as e:
        logging.error(f"DeepSearch sub-task error: {str(e)}")
        return {
            "error": f"DeepSearch sub-task failed: {str(e)}",
            "metadata": {"subtask": True, "recursion_depth": new_depth, "error": True},
        }
