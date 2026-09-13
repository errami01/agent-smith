import os
import re
from typing import List, Optional


class Toolset:
    """Implementations for mandatory file and search tools (Page 26)."""

    @staticmethod
    def read_file(
        filepath: str,
        start_line: int = 1,
        end_line: Optional[int] = None
    ) -> str:
        """Read file with line numbers (cat -n format)."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Line numbers are 1-indexed
            start = max(0, start_line - 1)
            end = end_line if end_line is not None else len(lines)
            
            output = []
            for i, line in enumerate(lines[start:end], start=start + 1):
                output.append(f"{i:6}: {line}")
            return "".join(output)
        except Exception as e:
            return f"Error reading file: {e}"

    @staticmethod
    def edit_file(filepath: str, old_str: str, new_str: str) -> str:
        """Exact string replacement in a file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            if old_str not in content:
                return f"Error: '{old_str}' not found in {filepath}."
            
            new_content = content.replace(old_str, new_str)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Successfully edited {filepath}."
        except Exception as e:
            return f"Error editing file: {e}"

    @staticmethod
    def list_files(directory: str, pattern: str = ".*") -> str:
        """List files matching a regex pattern."""
        try:
            files = []
            regex = re.compile(pattern)
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    rel_path = os.path.relpath(os.path.join(root, filename), directory)
                    if regex.search(rel_path):
                        files.append(rel_path)
            return "\n".join(files) if files else "No files found."
        except Exception as e:
            return f"Error listing files: {e}"

    @staticmethod
    def search_code(pattern: str, file_pattern: str = ".*") -> str:
        """Grep-like search across the codebase."""
        results = []
        try:
            regex = re.compile(pattern)
            f_regex = re.compile(file_pattern)
            for root, _, filenames in os.walk("."):
                for filename in filenames:
                    path = os.path.join(root, filename)
                    if not f_regex.search(path):
                        continue
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            for i, line in enumerate(f, 1):
                                if regex.search(line):
                                    results.append(f"{os.path.abspath(path)}:{i} {line.strip()}")
                    except (UnicodeDecodeError, PermissionError):
                        continue
            return "\n".join(results) if results else "No matches found."
        except Exception as e:
            return f"Search error: {e}"

    @staticmethod
    def run_tests(code: str, tests: List[str]) -> str:
        """
        Executes code followed by a series of assert statements.
        Returns 'All tests passed' or the failure message.
        """
        test_script = code + "\n" + "\n".join(tests)
        # We can use a temporary local execution for tests 
        # as they run outside the primary agent loop sandbox.
        try:
            exec(test_script, {"__builtins__": __import__("builtins")})
            return "PASSED: All tests passed."
        except Exception as e:
            return f"FAILED: {str(e)}"