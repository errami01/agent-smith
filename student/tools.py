import os
import re
from typing import List, Optional
from pathlib import Path


class Toolset:
    """Implementations for mandatory file and search tools (Page 26)."""
    SENSITIVE_PATTERNS = [
        r"^\.env$",
        r"^\.git.*",
        r"\.docker.*",
        r"__pycache__",
        r"^\.secrets$"
    ]
    ROOT = "/testbed"

    @staticmethod
    def _get_secure_path(path: str, workdir: str = f"{ROOT}") -> str:
        """
        1. Joins the user-provided path with the secure root.
        2. Resolves '..' to prevent directory traversal.
        3. Ensures the final path is still within the root.
        """
        # Ensure workdir is absolute
        base = os.path.abspath(workdir)
        # Join and resolve
        # path = path.lstrip("/\\")
        requested = os.path.abspath(path)        
        # Security: Check if requested path starts with base
        if not requested.startswith(base):
            raise PermissionError(f"Security Violation: Path {path} is outside of {workdir} directory")
        return path

    @staticmethod
    def read_file(
        filepath: str,
        start_line: int = 1,
        end_line: Optional[int] = None
    ) -> str:
        """Read file with line numbers (cat -n format)."""
        try:
            filepath = Toolset._get_secure_path(filepath)
            # filepath = Path(filepath)
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
            Toolset._get_secure_path(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            if old_str not in content:
                return f"Error: '{old_str}' not found in {filepath}."
            
            new_content = content.replace(old_str, new_str)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            return (
                f"Successfully edited {filepath}.\n"
                f"Replaced:\n{old_str}\n"
                f"With:\n{new_str}\n"
                # f"-> Changes applied successfully. You can now run tests or check the file."
            )
        except Exception as e:
            return f"Error editing file: {e}"

    @staticmethod
    def list_files(directory: str=f"{ROOT}", pattern: str = ".*") -> str:
        """List files matching a pattern, while excluding sensitive system files."""
        try:
            Toolset._get_secure_path(directory)
            files = []
            regex = re.compile(pattern)
            
            for root, d, filenames in os.walk(directory):
                for filename in filenames:
                    rel_path = os.path.relpath(os.path.join(root, filename), directory)
                    
                    # 3. Check against Sensitive Patterns
                    if any(re.search(p, rel_path) for p in Toolset.SENSITIVE_PATTERNS):
                        continue
                        
                    # 4. Check against user requested pattern
                    if regex.search(rel_path):
                        files.append(rel_path)
            
            return "\n".join(files) if files else "No files found."
        except Exception as e:
            return f"Error listing files: {e}"

    @staticmethod
    def __get_testbed_root() -> Path:
        # Start from the current file's directory
        current_dir = Path(__file__).resolve().parent
        target_dir = current_dir.parent / Toolset.ROOT
        # Look at the current directory and all its parents
        if target_dir.is_dir():
            return target_dir
        else:
            raise Exception(f"{Toolset.ROOT} not found")


    @staticmethod
    def search_code(pattern: str, file_pattern: str = ".*") -> str:
        """Grep-like search restricted to the /testbed directory."""
        results = []
        search_root = Path(Toolset.ROOT)
        try:
            search_root = Toolset.__get_testbed_root()# Mandatory restricted root
        except Exception:
            return f"Error: Search root {search_root.name} does not exist."

        try:
            regex = re.compile(pattern)
            f_regex = re.compile(file_pattern)
            for root, _, filenames in os.walk(search_root):
                for filename in filenames:
                    path = os.path.join(root, filename)
                    rel_path = os.path.relpath(path, search_root)
                    # 1. Skip sensitive files (reuse your list from list_files)
                    if any(re.search(p, rel_path) for p in Toolset.SENSITIVE_PATTERNS):
                        continue
                        
                    # 2. Filter by file_pattern
                    if not f_regex.search(rel_path):
                        continue
                        
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            for i, line in enumerate(f, 1):
                                if regex.search(line):
                                    # Security: Use relative paths in output 
                                    # to avoid leaking the full host system structure
                                    rel_path = os.path.relpath(path, search_root)
                                    results.append(f"{path}:{i} {line.strip()}")
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

    @staticmethod
    def run_command(command: str, workdir: str = f"{ROOT}") -> str:
        """Executes a shell command in the specified directory."""
        import subprocess
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=workdir, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        except Exception as e:
            return f"Command execution failed: {e}"

    @staticmethod
    def get_patch() -> str:
        """Retrieves the unified git diff of changes."""
        import subprocess
        # Mandatory command : 'git -c core.fileMode=false diff'
        try:
            result = subprocess.run(
                ['git', '-c', 'core.fileMode=false', 'diff'],
                cwd=f"/{Toolset.ROOT}",
                capture_output=True,
                text=True
            )
            return result.stdout
        except Exception as e:
            return f"Failed to get patch: {e}"

class SweBenchTools(Toolset):
    @staticmethod
    def _run_eval_script(command: str, workdir: str = f"{Toolset.ROOT}"):
        """Executes a shell command in the specified working directory."""
        import subprocess
        try:
            process = subprocess.run(
                ["bash", "-c", command],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Check if the command succeeded with no errors
            if process.returncode == 0:
                if not process.stdout.strip() and not process.stderr.strip():
                    return "SUCCESS: Command executed successfully with no output (All tests passed)."
                return f"SUCCESS (Exit Code 0):\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
            else:
                return f"FAILED (Exit Code {process.returncode}):\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
                
        except Exception as e:
            return f"Command execution failed: {e}"
    @staticmethod
    def run_tests() -> str:
        """
        Executes eval_script.
        Returns the test output and exit code.
        """
        eval_script = os.getenv("SWE_EVAL_SCRIPT")
        try:
            return SweBenchTools._run_eval_script(eval_script, Toolset.ROOT)
        
        except Exception as e:
            return f"FAILED: {str(e)}"