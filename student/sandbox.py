import sys
import multiprocessing
import io
import os
import traceback
from typing import Dict, Any, Optional, List
from types import ModuleType
from student.schema import SandboxConfig
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
from student.tools import Toolset



class Sandbox:
    def __init__(self, config: SandboxConfig) -> None:
        self.config = config
        self.loop = asyncio.new_event_loop()
        self.exit_stack = AsyncExitStack()
        self.session = None
        # Persistent state for the REPL/Agent loop
        self.namespace: Dict[str, Any] = {
            "__builtins__": __builtins__.copy(),
            "final_answer": self._final_answer_callback,
        }
        # Override import in the namespace
        self.namespace["__builtins__"]["__import__"] = self._safe_import

    def _final_answer_callback(self, answer: Any) -> None:
        print(f"FINAL_ANSWER_TRIGGERED: {answer}")

    def _safe_import(
        self,
        name: str,
        globals: Optional[Dict[str, Any]] = None,
        locals: Optional[Dict[str, Any]] = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0
    ) -> ModuleType:
        allowed = False
        for pattern in self.config.authorized_imports:
            if pattern.endswith(".*"):
                base = pattern[:-2]
                if name == base or name.startswith(base + "."):
                    allowed = True
                    break
            elif name == pattern:
                allowed = True
                break

        if not allowed:
            raise ImportError(f"Import of '{name}' is forbidden.")

        return __import__(name, globals, locals, fromlist, level)

    def run_code(self, code: str) -> str:
        """Executes code and returns stdout/stderr string."""
        with multiprocessing.Manager() as manager:
            # We use a manager dict to capture the output and updated namespace
            # result_dict = manager.dict()
            parent_conn, child_conn = multiprocessing.Pipe()
            process = multiprocessing.Process(
                target=self._execute_wrapper,
                args=(code, child_conn, self.namespace)
            )
            process.start()
            # Close child end in parent
            child_conn.close()
            process.join(timeout=self.config.max_execution_time_seconds)
            if process.is_alive():
                process.terminate()
                return "Error: Execution timed out."

            # Update our persistent namespace with changes from the subprocess
            # Note: Only picklable objects will be preserved
            # new_ns = result_dict.get("namespace")
            # if isinstance(new_ns, dict):
            #     for key, value in new_ns.items():
            #         if key != "__builtins__":
            #             self.namespace[key] = value

            # Receive the output string from the child
            if parent_conn.poll():
                return parent_conn.recv()
            return "Error: No output received from sandbox."

    def _execute_wrapper(
        self,
        code: str,
        conn: Any,
        current_ns: Dict[str, Any]
    ) -> None:
        buffer = io.StringIO()
        sys.stdout = buffer
        sys.stderr = buffer

        try:
            exec(code, current_ns)
            output = buffer.getvalue()
        except Exception:
            output = buffer.getvalue() + traceback.format_exc()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            conn.send(output)
            conn.close()

    def connect_mcp(self, server_script: str) -> None:
        """Synchronously connects to the MCP server."""
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "python", server_script],
            env=os.environ.copy()
        )

        # Force execution of the async connection stack synchronously
        self.loop.run_until_complete(self._async_connect(server_params))
        
        # Pull tools synchronously using the event loop
        tools_result = self.loop.run_until_complete(self.session.list_tools())
        
        # Register tools (adjust based on SDK v1 or v2 object structures)
        # Note: list_tools returns a list wrapped in a ToolsResult object usually
        for tool in getattr(tools_result, 'tools', tools_result):
            self.namespace[tool.name] = self._create_tool_wrapper(tool.name)

    async def _async_connect(self, server_params: StdioServerParameters) -> None:
        """Internal async method to construct the connection state."""
        # Enter the async context managers and store them on the exit stack
        read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        
        # Initialize the connection protocol
        await self.session.initialize()

    def _create_tool_wrapper(self, tool_name: str):
        def wrapper(*args, **kwargs):
            # No async/await! This is purely synchronous.
            if not self.session:
                return "Error: MCP session not connected."
            
            result = self.loop.run_until_complete(
                self.session.call_tool(tool_name, arguments=kwargs)
            )
            # Access text content (simplified for standard MCP tool responses)
            tool_output = result.content[0].text
            print(f"{tool_output}") # Bubbles up to host via stdout
            return tool_output
        return wrapper
    def close(self):
        """Ensure cleanup of the subprocess and loop when sandbox terminates."""
        self.loop.run_until_complete(self.exit_stack.aclose())
        self.loop.close()

    def get_tool_manual(self) -> str:
        """Dynamically generates a manual from the MCP server's tool schemas."""
        if not self.session:
            return "No tools connected."
        
        tools_result = self.loop.run_until_complete(self.session.list_tools())
        tools = getattr(tools_result, 'tools', tools_result)
        
        manual = "AVAILABLE TOOLS (Call these as Python functions):\n"
        for tool in tools:
            # tool.name, tool.description, and tool.inputSchema are standard MCP fields
            desc = tool.description or "No description provided."
            manual += f"- {tool.name}(...): {desc}\n"
            manual += f"  Parameters: {tool.input_schema.get('properties', {})}\n"
            
        manual += """\n- You MUST use keyword arguments when calling tools:
        Example: read_file(filepath="/testbed/main.py").
        DO NOT write: read_file("/testbed/main.py")"""
        return manual

