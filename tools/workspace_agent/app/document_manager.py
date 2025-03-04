import os
import re
import uuid
from typing import Dict, List, Optional, Any


from app.utils import (
    get_workspace_dir,
    ensure_workspace_exists,
    extract_sections,
)

import logging

logger = logging.getLogger(__name__)


class DocumentManager:
    @staticmethod
    def generate_unique_filename(prefix: str = "", extension: str = ".md") -> str:
        unique_id = str(uuid.uuid4())
        if prefix:
            return f"{prefix}_{unique_id}{extension}"
        return f"{unique_id}{extension}"

    @staticmethod
    def create_document(
        file_name: str = "",
        text_content: Optional[str] = None,
        workspace_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

        if not file_name:
            file_name = DocumentManager.generate_unique_filename()
        elif not file_name.endswith(".md"):
            file_name += ".md"

        file_path = os.path.join(workspace_dir, file_name)
        # Log the file path being created

        logger.info(f"Creating document at path: {file_path}")
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
        file_name: str,
        section_name: str,
        text_content: str,
        workspace_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

        if not file_name.endswith(".md"):
            file_name += ".md"
        file_path = os.path.join(workspace_dir, file_name)

        # Create the file if it doesn't exist
        if not os.path.isfile(file_path):
            DocumentManager.create_document(file_name, workspace_dir=workspace_dir)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            sections = extract_sections(content)
            if section_name in sections:
                return {
                    "error": f"Section '{section_name}' already exists in {file_name}"
                }

            # Prepare new section
            if not text_content.startswith(
                f"# {section_name}"
            ) and not text_content.startswith(f"## {section_name}"):
                new_section = f"## {section_name}\n\n{text_content}"
            else:
                new_section = text_content

            with open(file_path, "a", encoding="utf-8") as f:
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
        file_name: str,
        section_name: str,
        text_content: str,
        workspace_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

        if not file_name.endswith(".md"):
            file_name += ".md"
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File {file_name} not found"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            sections = extract_sections(content)
            if section_name not in sections:
                return {"error": f"Section '{section_name}' not found in {file_name}"}

            section_content = sections[section_name]
            updated_section = section_content + "\n\n" + text_content
            new_content = content.replace(section_content, updated_section)

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
        file_name: str,
        section_name: str,
        text_content: str,
        workspace_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

        if not file_name.endswith(".md"):
            file_name += ".md"
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File {file_name} not found"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            sections = extract_sections(content)
            if section_name not in sections:
                # If it doesn't exist, just add it
                return DocumentManager.add_section(
                    file_name, section_name, text_content, workspace_dir=workspace_dir
                )

            section_content = sections[section_name]
            heading_line = section_content.split("\n", 1)[0]
            new_section = heading_line + "\n\n" + text_content
            new_content = content.replace(section_content, new_section)

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
    def remove_section(
        file_name: str, section_name: str, workspace_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

        if not file_name.endswith(".md"):
            file_name += ".md"
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File {file_name} not found"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            sections = extract_sections(content)
            if section_name not in sections:
                return {"error": f"Section '{section_name}' not found in {file_name}"}

            section_content = sections[section_name]
            lines = content.split("\n")
            section_lines = section_content.split("\n")

            for i in range(len(lines) - len(section_lines) + 1):
                if "\n".join(lines[i : i + len(section_lines)]) == section_content:
                    del lines[i : i + len(section_lines)]
                    while i < len(lines) and lines[i].strip() == "":
                        del lines[i]
                    break

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
        file_name: str,
        section_name: str,
        new_name: str,
        workspace_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

        if not file_name.endswith(".md"):
            file_name += ".md"
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File {file_name} not found"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            sections = extract_sections(content)
            if section_name not in sections:
                return {"error": f"Section '{section_name}' not found in {file_name}"}
            if new_name in sections:
                return {"error": f"Section '{new_name}' already exists in {file_name}"}

            section_content = sections[section_name]
            heading_match = re.match(
                r"^(#{1,6})\s+(.+)$", section_content.split("\n", 1)[0]
            )
            if not heading_match:
                return {"error": f"Could not parse heading in section '{section_name}'"}

            heading_level = heading_match.group(1)
            new_heading = f"{heading_level} {new_name}"
            new_section = re.sub(
                r"^#{1,6}\s+.+$",
                new_heading,
                section_content,
                count=1,
                flags=re.MULTILINE,
            )
            new_content = content.replace(section_content, new_section)

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
    def export_document(
        file_name: str, export_format: str, workspace_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

        if not file_name.endswith(".md"):
            file_name += ".md"
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File {file_name} not found"}

        valid_formats = ["pdf", "docx", "html"]
        if export_format.lower() not in valid_formats:
            return {
                "error": f"Invalid export format. Supported formats: {', '.join(valid_formats)}"
            }

        try:
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
    def list_documents(workspace_dir: Optional[str] = None) -> List[str]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

        documents = []
        for file in os.listdir(workspace_dir):
            if file.endswith(".md"):
                documents.append(file)
        return documents

    @staticmethod
    def get_document_content(
        file_name: str, workspace_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

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

    @staticmethod
    def insert_section(
        file_name: str,
        section_name: str,
        text_content: str,
        position: str,
        workspace_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

        if not file_name.endswith(".md"):
            file_name += ".md"
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File {file_name} not found"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            sections = extract_sections(content)
            if section_name in sections:
                return {
                    "error": f"Section '{section_name}' already exists in {file_name}"
                }

            if not text_content.startswith(
                f"# {section_name}"
            ) and not text_content.startswith(f"## {section_name}"):
                new_section = f"## {section_name}\n\n{text_content}"
            else:
                new_section = text_content

            if position == "beginning":
                updated_content = new_section + "\n\n" + content
            elif position == "end":
                updated_content = content + "\n\n" + new_section
            elif position.startswith("after:"):
                target_section = position[6:]
                if target_section not in sections:
                    return {
                        "error": f"Target section '{target_section}' not found in {file_name}"
                    }

                parts = []
                current_part = []
                current_section = None
                for line in content.split("\n"):
                    heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
                    if (
                        heading_match
                        and heading_match.group(2).strip() == target_section
                    ):
                        current_section = target_section
                        current_part.append(line)
                    elif heading_match and current_section == target_section:
                        parts.append("\n".join(current_part))
                        current_part = [line]
                        current_section = heading_match.group(2).strip()
                    else:
                        current_part.append(line)
                if current_part:
                    parts.append("\n".join(current_part))

                if len(parts) > 1:
                    updated_content = (
                        parts[0] + "\n\n" + new_section + "\n\n" + "\n".join(parts[1:])
                    )
                else:
                    updated_content = parts[0] + "\n\n" + new_section
            else:
                return {
                    "error": (
                        f"Invalid position: {position}. "
                        "Use 'beginning', 'end', or 'after:SectionName'"
                    )
                }

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)

            return {
                "file_name": file_name,
                "section_name": section_name,
                "position": position,
                "content": new_section,
            }
        except Exception as e:
            return {"error": f"Failed to insert section: {str(e)}"}

    @staticmethod
    def validate_document(
        file_name: str, workspace_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

        if not file_name.endswith(".md"):
            file_name += ".md"
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File {file_name} not found"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            headings = {}
            duplicate_headings = []
            for i, line in enumerate(lines):
                heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
                if heading_match:
                    heading_text = heading_match.group(2).strip()
                    if heading_text in headings:
                        duplicate_headings.append(
                            (heading_text, i, headings[heading_text])
                        )
                    else:
                        headings[heading_text] = i

            if duplicate_headings:
                duplicate_headings.sort(key=lambda x: x[1], reverse=True)
                for heading, line_num, original_line in duplicate_headings:
                    del lines[line_num]
                    # optional: remove blank line after
                    if line_num < len(lines) and lines[line_num].strip() == "":
                        del lines[line_num]
                fixed_content = "\n".join(lines)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)
                return {
                    "file_name": file_name,
                    "validated": True,
                    "fixed_issues": f"Removed {len(duplicate_headings)} duplicate headings",
                    "duplicate_headings": [h[0] for h in duplicate_headings],
                    "issues_found": True,
                }

            return {
                "file_name": file_name,
                "validated": True,
                "issues_found": False,
                "message": "Document structure is valid. No issues found.",
            }
        except Exception as e:
            return {"error": f"Failed to validate document: {str(e)}"}

    @staticmethod
    def update_document(
        file_name: str, text_content: str, workspace_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        if not workspace_dir:
            workspace_dir = get_workspace_dir()
        ensure_workspace_exists(workspace_dir)

        if not file_name.endswith(".md"):
            file_name += ".md"
        file_path = os.path.join(workspace_dir, file_name)

        if not os.path.isfile(file_path):
            return {"error": f"File {file_name} not found"}

        try:
            lines = text_content.split("\n")
            headings = {}
            duplicate_headings = []
            for i, line in enumerate(lines):
                heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
                if heading_match:
                    heading_text = heading_match.group(2).strip()
                    if heading_text in headings:
                        duplicate_headings.append(
                            (heading_text, i, headings[heading_text])
                        )
                    else:
                        headings[heading_text] = i

            if duplicate_headings:
                duplicate_headings.sort(key=lambda x: x[1], reverse=True)
                for heading, line_num, original_line in duplicate_headings:
                    del lines[line_num]
                    if line_num < len(lines) and lines[line_num].strip() == "":
                        del lines[line_num]
                text_content = "\n".join(lines)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text_content)

            return {
                "file_name": file_name,
                "path": file_path,
                "size": os.path.getsize(file_path),
                "updated": True,
                "duplicate_headings_fixed": len(duplicate_headings) > 0,
                "duplicate_headings_count": len(duplicate_headings),
            }
        except Exception as e:
            return {"error": f"Failed to update document: {str(e)}"}
