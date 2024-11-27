"""Provide a file system operation environment for Agent."""

import os
import fnmatch
from typing import Any, Dict
from collections import defaultdict

from ..wrapper import toolwrapper

MAX_ENTRY_NUMS_FOR_LEVEL = 50

IGNORED_LIST = [
    "*/.git/*", "python_notebook.ipynb", "*/node_modules/*", "*/venv/*", "*/__pycache__/*", "*/.ipynb_checkpoints/*", "*/.vscode/*", "*/.idea/*", "*/.vs/*", "*/python*/site-packages/*"]


def _check_ignorement(path: str) -> bool:
    for pattern in IGNORED_LIST:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


# This strucure helps to get the overall dir for the current workspace.
@toolwrapper(visible=False)
def print_filesys_struture(root,return_root=False) -> str:
    """Generates a tree-like structure of all files and folders in the workspace.
    Recursively walks through directories, displaying files and directories. If a directory exceeds
    the maximum entry limit (MAX_ENTRY_NUMS_FOR_LEVEL), it shows a `wrapped` message.

    Example:
    ```root/
        - sub_directory1/
            - file1.txt
            - file2.txt
        - sub_directory2/
            - file3.txt
    ```

    :return string: Tree-like structure of the workspace."""
    full_repr = ''
    if return_root:
        full_repr += f'Global Root Work Directory: {root}\nDirectory Structure:\n'

    folder_counts = defaultdict(lambda: 0)
    for root, dirs, files in os.walk(root):
        if _check_ignorement(root):
            continue
        level = root.replace(root, '').count(os.sep)
        indent = ' ' * 4 * (level)

        folder_counts[root] += 1
        if folder_counts[root] > MAX_ENTRY_NUMS_FOR_LEVEL:
            full_repr += f'{indent}`wrapped`\n'

        full_repr += f'{indent}- {os.path.basename(root)}/\n'

        idx = 0
        subindent = ' ' * 4 * (level + 1) + '- '
        for f in files:
            if _check_ignorement(f):
                continue

            idx += 1
            if idx > MAX_ENTRY_NUMS_FOR_LEVEL:
                full_repr += f'{subindent}`wrapped`\n'
                break
            full_repr += f'{subindent}{f}\n'

    return full_repr

# This structure reads given line for the specified file.
@toolwrapper(name = 'read', visible = True)
def read_from_file(filepath: str, line_number: int = 1) -> str:
    """Reads content from a specified line in a text file within the workspace.

    :param string filepath: Absolute path from workspace root.
    :param integer? line_number: Optional. Starting line number; supports negative values for reverse indexing. Defaults to 1.

    :return string: Content from the specified line, prefixed with "line_number: "."""
    full_path = filepath

    if _check_ignorement(full_path) or not os.path.isfile(full_path):
        raise FileNotFoundError(f"File {filepath} not found in workspace.")
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File {filepath} not found in workspace.")

    content = ''
    with open(full_path, 'r') as f:
        lines = f.readlines(int(1e5))
    if len(lines) == 0:
        return ""

    read_count = 0
    if not (abs(line_number) - 1 <= len(lines)):
        raise ValueError(f"Line number {line_number} is out of range.")
    index = line_number if line_number >= 0 else len(lines) + line_number
    if index == 0:
        index = 1

    if line_number == 0:
        indexed_lines = lines
    elif line_number > 0:
        indexed_lines = lines[line_number-1:]
    else:
        indexed_lines = lines[line_number:]

    for line in indexed_lines:
        content += f'{index}'.rjust(5) + ': '
        content += line
        read_count += len(line)
        index += 1

    print(content)
    return content


@toolwrapper()
def rename_file(original_path:str, new_name:str):
    """Renames a file and open the folder for the user to check the file.

    :param string original_path: Absolute path from workspace root.
    :param string new_name: New name for the file.
    """
    directory = os.path.dirname(original_path)
    new_path = os.path.join(directory, new_name)
    os.rename(original_path, new_path)
    # after renaming, open the file folder for the user to check the file
    if os.name == 'nt':  # For Windows
        os.system(f'explorer /select,{new_path}')
    elif os.name == 'posix':  # For macOS and Linux
        if sys.platform == 'darwin':  # macOS
            os.system(f'open -R {new_path}')
        else:  # Linux
            os.system(f'xdg-open {directory}')
    return f"File {original_path} renamed to {new_name}."


# @toolwrapper()
# def read_pdf(filepath: str, pages:int = 3) -> str:
#     """Reads content from a PDF file within the workspace.

#     :param string filepath: Absolute path from workspace root.
#     :param integer? pages: Optional. Number of pages to read. Defaults to 3.

#     :return string: Content from the PDF file."""
#     from PyPDF2 import PdfReader

#     full_path = filepath
#     if _check_ignorement(full_path) or not os.path.isfile(full_path):
#         raise FileNotFoundError(f"File {filepath} not found in workspace.")
#     if not os.path.exists(full_path):
#         raise FileNotFoundError(f"File {filepath} not found in workspace.")

#     reader = PdfReader(full_path)
#     content = ''
#     for page in reader.pages[:pages]:
#         content += page.extract_text()
#     return content

# @toolwrapper()
# def read_docx(filepath: str) -> str:
#     """Reads content from a DOCX file within the workspace.

#     :param string filepath: Absolute path from workspace root.

#     :return string: Content from the DOCX file."""
#     from docx import Document

#     full_path = filepath
#     if _check_ignorement(full_path) or not os.path.isfile(full_path):
#         raise FileNotFoundError(f"File {filepath} not found in workspace.")
#     if not os.path.exists(full_path):
#         raise FileNotFoundError(f"File {filepath} not found in workspace.")

#     doc = Document(full_path)
#     content = ''
#     for para in doc.paragraphs:
#         content += para.text + '\n'
#     return content