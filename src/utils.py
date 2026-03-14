"""
Utility functions for runtrace package
"""

import os
from pathlib import Path


def normalize_path(path: str) -> str:
    """Normalize a file path to absolute path."""
    return os.path.abspath(os.path.normpath(path))


def is_in_project(file_path: str, project_root: str) -> bool:
    """
    Check if a file is within the project root directory.

    Args:
        file_path: Path to the file to check
        project_root: Root directory of the project

    Returns:
        True if file is within project root, False otherwise
    """
    try:
        file_path = normalize_path(file_path)
        project_root = normalize_path(project_root)

        try:
            Path(file_path).relative_to(Path(project_root))
            return True
        except ValueError:
            return False
    except Exception:
        return False
