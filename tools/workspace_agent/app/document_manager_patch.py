"""
Patch for DocumentManager class to fix section renaming issues.
"""

import os
import re
import logging
from typing import Dict, Any


def improved_rename_section(
    file_name: str, section_name: str, new_name: str, workspace_dir: str
) -> Dict[str, Any]:
    """
    Improved implementation of rename_section that properly handles section renaming.

    Args:
        file_name: Name of the file to modify
        section_name: Name of the section to rename
        new_name: New name for the section
        workspace_dir: Path to the workspace directory

    Returns:
        Dict containing the result of the operation
    """
    # Ensure file has .md extension
    if not file_name.endswith(".md"):
        file_name += ".md"

    file_path = os.path.join(workspace_dir, file_name)

    if not os.path.isfile(file_path):
        return {"error": f"File {file_name} not found"}

    try:
        # Read existing content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Create heading patterns to match
        heading_patterns = [
            re.compile(f"^(#{1,6})\\s+{re.escape(section_name)}\\s*$", re.MULTILINE),
        ]

        # Check if any heading pattern matches
        found_match = False
        for pattern in heading_patterns:
            if pattern.search(content):
                found_match = True
                break

        if not found_match:
            return {"error": f"Section '{section_name}' not found in {file_name}"}

        # Replace the heading with the new name, preserving the heading level
        new_content = content
        for pattern in heading_patterns:
            new_content = pattern.sub(f"\\1 {new_name}", new_content)

        # Write the updated content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        logging.info(f"Section '{section_name}' renamed to '{new_name}' in {file_name}")

        return {
            "file_name": file_name,
            "old_section_name": section_name,
            "new_section_name": new_name,
            "updated": True,
        }

    except Exception as e:
        error_msg = f"Failed to rename section: {str(e)}"
        logging.error(error_msg)
        return {"error": error_msg}
