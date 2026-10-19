from mcp.server import MCPServer
from student.tools import SweBenchTools
from typing import Optional
from mcp.server import MCPServer


mcp = MCPServer("SweBenchTools")

@mcp.tool()
def read_file(filepath: str, start_line: int = 1, end_line: Optional[int] = None) -> str:
    """Read a file with line numbers."""
    return SweBenchTools.read_file(filepath=filepath, start_line=start_line, end_line=end_line)

@mcp.tool()
def edit_file(filepath: str, old_str: str, new_str: str) -> str:
    """Replace exact string in file."""
    return SweBenchTools.edit_file(filepath, old_str, new_str)

@mcp.tool()
def list_files(directory: str = "/testbed", pattern: str = ".*") -> str:
    """List files in directory."""
    return SweBenchTools.list_files(directory, pattern)

@mcp.tool()
def search_code(pattern: str, file_pattern: str = ".*") -> str:
    """Search for code pattern."""
    return SweBenchTools.search_code(pattern, file_pattern)

@mcp.tool()
def run_tests() -> str:
    """
    Executes eval_script.
    Returns the test output and exit code.
    """
    return SweBenchTools.run_tests()

@mcp.tool()
def run_command(command: str, workdir: str = f"/testbed"):
    """Executes a shell command in the specified directory."""
    return SweBenchTools.run_command(command,workdir)

@mcp.tool()
def get_patch() -> str:
    """Retrieves the unified git diff of changes."""
    return SweBenchTools.get_patch()

if __name__ == "__main__":
    mcp.run()