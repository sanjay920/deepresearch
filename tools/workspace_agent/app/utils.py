import os
import re
from typing import Dict, List, Optional, Any


def get_workspace_dir() -> str:
    """Get the workspace directory from environment variable or use default."""
    return os.environ.get("WORKSPACE_DIR", "./workspace")


def ensure_workspace_exists() -> None:
    """Ensure the workspace directory exists."""
    workspace_dir = get_workspace_dir()
    os.makedirs(workspace_dir, exist_ok=True)


def list_documents() -> List[str]:
    """List all markdown documents in the workspace."""
    workspace_dir = get_workspace_dir()
    ensure_workspace_exists()

    documents = []
    for file in os.listdir(workspace_dir):
        if file.endswith(".md"):
            documents.append(file)

    return documents


def extract_sections(content: str) -> Dict[str, str]:
    """Extract sections from markdown content."""
    sections = {}
    current_section = None
    section_content = []

    # Add a special "root" section for content before any heading
    root_content = []

    for line in content.split("\n"):
        # Check if line is a heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

        if heading_match:
            # If we were building a section, save it
            if current_section:
                sections[current_section] = "\n".join(section_content)
                section_content = []
            elif root_content:
                sections["_root"] = "\n".join(root_content)
                root_content = []

            # Start a new section
            current_section = heading_match.group(2).strip()
            section_content = [line]
        else:
            # Add line to current section or root
            if current_section:
                section_content.append(line)
            else:
                root_content.append(line)

    # Save the last section
    if current_section and section_content:
        sections[current_section] = "\n".join(section_content)
    elif root_content:
        sections["_root"] = "\n".join(root_content)

    return sections


def get_document_summary(file_name: str) -> Dict[str, Any]:
    """Get a summary of a document, including its sections."""
    workspace_dir = get_workspace_dir()
    file_path = os.path.join(workspace_dir, file_name)

    if not os.path.isfile(file_path):
        return {"error": f"File {file_name} not found"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        sections = extract_sections(content)

        # Create previews for each section
        section_previews = {}
        for section_name, section_content in sections.items():
            # Skip the root section in previews
            if section_name == "_root":
                continue

            # Get first 100 characters as preview
            preview = (
                section_content.split("\n", 1)[1]
                if "\n" in section_content
                else section_content
            )
            preview = preview.strip()
            if len(preview) > 100:
                preview = preview[:97] + "..."
            section_previews[section_name] = preview

        return {
            "file_name": file_name,
            "sections": (
                list(sections.keys())
                if "_root" not in sections
                else [s for s in sections.keys() if s != "_root"]
            ),
            "section_previews": section_previews,
            "size": len(content),
            "last_modified": os.path.getmtime(file_path),
        }

    except Exception as e:
        return {"error": f"Error reading file {file_name}: {str(e)}"}


def get_workspace_summary() -> Dict[str, Any]:
    """Get a summary of all documents in the workspace."""
    documents = list_documents()

    summaries = []
    for doc in documents:
        summary = get_document_summary(doc)
        if "error" not in summary:
            summaries.append(summary)

    return {"documents": summaries}
