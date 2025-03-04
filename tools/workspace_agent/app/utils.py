import os
import re
from typing import Dict, List, Optional, Any, Tuple


def format_subdirectory(subdirectory: str) -> str:
    """Ensure subdirectory has 'chat_' prefix."""
    if subdirectory and not subdirectory.startswith("chat_"):
        return f"chat_{subdirectory}"
    return subdirectory


def extract_subdirectory(query: str) -> Tuple[str, str]:
    """Extract subdirectory instruction from query if present."""
    subdirectory_pattern = (
        r"[Uu]se\s+workspace\s+subdirectory\s+['\"]([^'\"]+)['\"]\.?\s*"
    )
    match = re.search(subdirectory_pattern, query)
    if match:
        subdirectory = match.group(1)
        clean_query = re.sub(subdirectory_pattern, "", query).strip()
        return format_subdirectory(subdirectory), clean_query
    return None, query


def get_workspace_dir(subdirectory: str = None) -> str:
    """
    Get the workspace directory. If 'subdirectory' is provided, use that.
    Otherwise, fall back to the default base workspace.
    """
    base_dir = os.getenv("WORKSPACE_DIR", "./workspace")
    if subdirectory:
        subdirectory = format_subdirectory(subdirectory)
        full_path = os.path.join(base_dir, subdirectory)
        os.makedirs(full_path, exist_ok=True)
        return full_path
    return base_dir


def ensure_workspace_exists(workspace_dir: Optional[str] = None) -> None:
    """Ensure the workspace directory (optionally specified) exists."""
    if not workspace_dir:
        workspace_dir = get_workspace_dir()
    os.makedirs(workspace_dir, exist_ok=True)


def list_documents(workspace_dir: Optional[str] = None) -> List[str]:
    """List all markdown documents in the given (or default) workspace directory."""
    if not workspace_dir:
        workspace_dir = get_workspace_dir()
    ensure_workspace_exists(workspace_dir)

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
    root_content = []

    for line in content.split("\n"):
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            # If we were building a section, save it
            if current_section:
                sections[current_section] = "\n".join(section_content)
                section_content = []
            elif root_content:
                sections["_root"] = "\n".join(root_content)
                root_content = []
            current_section = heading_match.group(2).strip()
            section_content = [line]
        else:
            if current_section:
                section_content.append(line)
            else:
                root_content.append(line)

    # Save last section
    if current_section and section_content:
        sections[current_section] = "\n".join(section_content)
    elif root_content:
        sections["_root"] = "\n".join(root_content)

    return sections


def get_document_summary(
    file_name: str, workspace_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Get a summary of a document, including its sections."""
    if not workspace_dir:
        workspace_dir = get_workspace_dir()
    file_path = os.path.join(workspace_dir, file_name)

    if not os.path.isfile(file_path):
        return {"error": f"File {file_name} not found"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        sections = extract_sections(content)
        section_previews = {}
        for section_name, section_content in sections.items():
            if section_name == "_root":
                continue
            preview_lines = section_content.split("\n", 1)
            preview = preview_lines[1] if len(preview_lines) > 1 else section_content
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


def get_workspace_summary(workspace_dir: Optional[str] = None) -> Dict[str, Any]:
    """Get a summary of all documents in the given (or default) workspace directory."""
    if not workspace_dir:
        workspace_dir = get_workspace_dir()
    documents = list_documents(workspace_dir=workspace_dir)

    summaries = []
    for doc in documents:
        summary = get_document_summary(doc, workspace_dir=workspace_dir)
        if "error" not in summary:
            summaries.append(summary)

    return {"documents": summaries}
