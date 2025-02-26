import os
import re
from typing import Dict, List, Optional, Any

from app.utils import get_workspace_dir, ensure_workspace_exists, extract_sections


class DocumentManager:
    @staticmethod
    def create_document(
        file_name: str, text_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new markdown document."""
        ensure_workspace_exists()
        workspace_dir = get_workspace_dir()

        # Ensure file has .md extension
        if not file_name.endswith(".md"):
            file_name += ".md"

        file_path = os.path.join(workspace_dir, file_name)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                if text_content:
                    f.write(text_content)

            return {
                "file_name": file_name,
                "path": file_path,
                "size": os.path.getsize(file_path) if text_content else 0,
            }

        except Exception as e:
            return {"error": f"Failed to create document: {str(e)}"}

    @staticmethod
    def add_section(
        file_name: str, section_name: str, text_content: str
    ) -> Dict[str, Any]:
        """Add a new section to a document."""
        ensure_workspace_exists()
        workspace_dir = get_workspace_dir()

        # Ensure file has .md extension
        if not file_name.endswith(".md"):
            file_name += ".md"

        file_path = os.path.join(workspace_dir, file_name)

        # Create file if it doesn't exist
        if not os.path.isfile(file_path):
            DocumentManager.create_document(file_name)

        try:
            # Read existing content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract sections
            sections = extract_sections(content)

            # Check if section already exists
            if section_name in sections:
                return {
                    "error": f"Section '{section_name}' already exists in {file_name}"
                }

            # Format the new section
            # Make sure text_content starts with the heading
            if not text_content.startswith(
                f"# {section_name}"
            ) and not text_content.startswith(f"## {section_name}"):
                new_section = f"## {section_name}\n\n{text_content}"
            else:
                new_section = text_content

            # Append the new section to the document
            with open(file_path, "a", encoding="utf-8") as f:
                # Add a newline before the new section if the file is not empty and doesn't end with newlines
                if content and not content.endswith("\n\n"):
                    f.write("\n\n" if not content.endswith("\n") else "\n")
                f.write(new_section)

            return {
                "file_name": file_name,
                "section_name": section_name,
                "content": new_section,
            }

        except Exception as e:
            return {"error": f"Failed to add section: {str(e)}"}

    @staticmethod
    def append_block(
        file_name: str, section_name: str, text_content: str
    ) -> Dict[str, Any]:
        """Append text to an existing section."""
        ensure_workspace_exists()
        workspace_dir = get_workspace_dir()

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

            # Extract sections
            sections = extract_sections(content)

            # Check if section exists
            if section_name not in sections:
                return {"error": f"Section '{section_name}' not found in {file_name}"}

            # Get the section content
            section_content = sections[section_name]

            # Append text to the section
            updated_section = section_content + "\n\n" + text_content

            # Replace the section in the document
            new_content = content.replace(section_content, updated_section)

            # Write the updated content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "file_name": file_name,
                "section_name": section_name,
                "content": updated_section,
            }

        except Exception as e:
            return {"error": f"Failed to append to section: {str(e)}"}

    @staticmethod
    def replace_section(
        file_name: str, section_name: str, text_content: str
    ) -> Dict[str, Any]:
        """Replace the content of a section."""
        ensure_workspace_exists()
        workspace_dir = get_workspace_dir()

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

            # Extract sections
            sections = extract_sections(content)

            # Check if section exists
            if section_name not in sections:
                # If section doesn't exist, add it
                return DocumentManager.add_section(
                    file_name, section_name, text_content
                )

            # Get the section content
            section_content = sections[section_name]

            # Format the new section content
            # Preserve the heading line
            heading_line = section_content.split("\n", 1)[0]
            new_section = heading_line + "\n\n" + text_content

            # Replace the section in the document
            new_content = content.replace(section_content, new_section)

            # Write the updated content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "file_name": file_name,
                "section_name": section_name,
                "content": new_section,
            }

        except Exception as e:
            return {"error": f"Failed to replace section: {str(e)}"}

    @staticmethod
    def remove_section(file_name: str, section_name: str) -> Dict[str, Any]:
        """Remove a section from a document."""
        ensure_workspace_exists()
        workspace_dir = get_workspace_dir()

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

            # Extract sections
            sections = extract_sections(content)

            # Check if section exists
            if section_name not in sections:
                return {"error": f"Section '{section_name}' not found in {file_name}"}

            # Get the section content
            section_content = sections[section_name]

            # Remove the section from the document
            # We need to handle the case where the section is at the end or in the middle
            lines = content.split("\n")
            section_lines = section_content.split("\n")

            # Find where the section starts
            for i in range(len(lines) - len(section_lines) + 1):
                if "\n".join(lines[i : i + len(section_lines)]) == section_content:
                    # Remove the section
                    del lines[i : i + len(section_lines)]

                    # Remove any extra blank lines
                    while i < len(lines) and lines[i] == "":
                        del lines[i]

                    break

            # Write the updated content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            return {
                "file_name": file_name,
                "section_name": section_name,
                "removed": True,
            }

        except Exception as e:
            return {"error": f"Failed to remove section: {str(e)}"}

    @staticmethod
    def rename_section(
        file_name: str, section_name: str, new_name: str
    ) -> Dict[str, Any]:
        """Rename a section in a document."""
        ensure_workspace_exists()
        workspace_dir = get_workspace_dir()

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

            # Extract sections
            sections = extract_sections(content)

            # Check if section exists
            if section_name not in sections:
                return {"error": f"Section '{section_name}' not found in {file_name}"}

            # Check if new section name already exists
            if new_name in sections:
                return {"error": f"Section '{new_name}' already exists in {file_name}"}

            # Get the section content
            section_content = sections[section_name]

            # Get the heading level (number of # characters)
            heading_match = re.match(
                r"^(#{1,6})\s+(.+)$", section_content.split("\n", 1)[0]
            )
            if not heading_match:
                return {"error": f"Could not parse heading in section '{section_name}'"}

            heading_level = heading_match.group(1)

            # Create the new heading
            new_heading = f"{heading_level} {new_name}"

            # Replace the heading in the section content
            new_section = re.sub(
                r"^#{1,6}\s+.+$",
                new_heading,
                section_content,
                count=1,
                flags=re.MULTILINE,
            )

            # Replace the section in the document
            new_content = content.replace(section_content, new_section)

            # Write the updated content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "file_name": file_name,
                "old_section_name": section_name,
                "new_section_name": new_name,
                "content": new_section,
            }

        except Exception as e:
            return {"error": f"Failed to rename section: {str(e)}"}

    @staticmethod
    def export_document(file_name: str, export_format: str) -> Dict[str, Any]:
        """Export a document to a different format (simulated)."""
        ensure_workspace_exists()
        workspace_dir = get_workspace_dir()

        # Ensure file has .md extension
        if not file_name.endswith(".md"):
            file_name += ".md"

        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File {file_name} not found"}

        # Validate export format
        valid_formats = ["pdf", "docx", "html"]
        if export_format.lower() not in valid_formats:
            return {
                "error": f"Invalid export format. Supported formats: {', '.join(valid_formats)}"
            }

        try:
            # For simulation purposes, we'll just copy the file with a new extension
            export_file_name = file_name.replace(".md", f".{export_format.lower()}")
            export_path = os.path.join(workspace_dir, export_file_name)

            with open(file_path, "r", encoding="utf-8") as src:
                content = src.read()

            with open(export_path, "w", encoding="utf-8") as dst:
                dst.write(content)

            return {
                "file_name": file_name,
                "export_file_name": export_file_name,
                "export_format": export_format,
                "path": export_path,
            }

        except Exception as e:
            return {"error": f"Failed to export document: {str(e)}"}

    @staticmethod
    def list_documents() -> List[str]:
        """List all markdown documents in the workspace."""
        ensure_workspace_exists()
        workspace_dir = get_workspace_dir()

        documents = []
        for file in os.listdir(workspace_dir):
            if file.endswith(".md"):
                documents.append(file)

        return documents

    @staticmethod
    def get_document_content(file_name: str) -> Dict[str, Any]:
        """Get the content of a document."""
        ensure_workspace_exists()
        workspace_dir = get_workspace_dir()

        # Ensure file has .md extension
        if not file_name.endswith(".md"):
            file_name += ".md"

        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File {file_name} not found"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            return {"file_name": file_name, "content": content, "size": len(content)}

        except Exception as e:
            return {"error": f"Failed to read document: {str(e)}"}
