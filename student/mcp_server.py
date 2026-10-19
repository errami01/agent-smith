# from mcp.server import MCPServer
# from student.tools import Toolset
# from typing import List, Optional


# mcp = MCPServer("AgentSmithTools")

# @mcp.tool()
# def read_file(filepath: str, start_line: int = 1, end_line: Optional[int] = None) -> str:
#     """Read a file with line numbers."""
#     return Toolset.read_file(filepath, start_line, end_line)

# @mcp.tool()
# def edit_file(filepath: str, old_str: str, new_str: str) -> str:
#     """Replace exact string in file."""
#     return Toolset.edit_file(filepath, old_str, new_str)

# @mcp.tool()
# def list_files(directory: str = "/testbed", pattern: str = ".*") -> str:
#     """List files in directory."""
#     return Toolset.list_files(directory, pattern)

# @mcp.tool()
# def search_code(pattern: str, file_pattern: str = ".*") -> str:
#     """Search for code pattern."""
#     return Toolset.search_code(pattern, file_pattern)

# @mcp.tool()
# def run_tests(code: str, tests: List[str]) -> str:
#     """
#     Executes code followed by a series of assert statements.
#     Returns 'All tests passed' or the failure message.
#     """
#     return Toolset.run_tests(code, tests)

# @mcp.tool()
# def run_command(command: str, workdir: str = f"/testbed"):
#     """Executes a shell command in the specified directory."""
#     return Toolset.run_command(command,workdir)

# @mcp.tool()
# def get_patch() -> str:
#     """Retrieves the unified git diff of changes."""
#     return Toolset.get_patch()