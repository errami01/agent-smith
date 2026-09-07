from mcp.server.fastmcp import FastMCP
from student.tools import Toolset


mcp = FastMCP("AgentSmithTools")

@mcp.tool()
def read_file(filepath: str, start_line: int = 1, end_line: int = 100) -> str:
    """Read a file with line numbers."""
    return Toolset.read_file(filepath, start_line, end_line)

@mcp.tool()
def edit_file(filepath: str, old_str: str, new_str: str) -> str:
    """Replace exact string in file."""
    return Toolset.edit_file(filepath, old_str, new_str)

@mcp.tool()
def list_files(directory: str, pattern: str = ".*") -> str:
    """List files in directory."""
    return Toolset.list_files(directory, pattern)

@mcp.tool()
def search_code(pattern: str, file_pattern: str = ".*") -> str:
    """Search for code pattern."""
    return Toolset.search_code(pattern, file_pattern)