#!/usr/bin/env python3
"""
Script to fix the test.md file by properly renaming section1 to section1.1
"""
import os
import sys
import re


def fix_test_md():
    """Fix the test.md file by properly renaming section1 to section1.1"""
    # Determine the workspace directory
    workspace_dir = os.environ.get("V3_WORKSPACE_DIR", "./v3/workspace")

    # Ensure the workspace directory exists
    if not os.path.exists(workspace_dir):
        print(f"Workspace directory {workspace_dir} does not exist")
        return False

    # Path to the test.md file
    file_path = os.path.join(workspace_dir, "test.md")

    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist")
        return False

    try:
        # Read the current content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace section1 with section1.1
        new_content = re.sub(
            r"^(#{1,6})\s+section1\s*$", r"\1 section1.1", content, flags=re.MULTILINE
        )

        # Also replace any references to section1 in the content
        new_content = new_content.replace(
            "placeholder content for section1", "placeholder content for section1.1"
        )

        # Write the updated content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"Successfully updated {file_path}")
        print("Old content:")
        print(content)
        print("\nNew content:")
        print(new_content)
        return True

    except Exception as e:
        print(f"Error fixing test.md: {str(e)}")
        return False


if __name__ == "__main__":
    success = fix_test_md()
    sys.exit(0 if success else 1)
