import sys
import multiprocessing
import io
import traceback
from typing import Dict, Any, Optional, List
from types import ModuleType
from student.schema import SandboxConfig
from mcp import ClientSession, StdioServerParameters
from student.tools import Toolset



class Sandbox:
    def __init__(self, config: SandboxConfig) -> None:
        self.config = config
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
            result_dict = manager.dict()
            process = multiprocessing.Process(
                target=self._execute_wrapper,
                args=(code, result_dict, self.namespace)
            )
            process.start()
            process.join(timeout=self.config.max_execution_time_seconds)

            if process.is_alive():
                process.terminate()
                return "Error: Execution timed out."

            # Update our persistent namespace with changes from the subprocess
            # Note: Only picklable objects will be preserved
            new_ns = result_dict.get("namespace")
            if isinstance(new_ns, dict):
                for key, value in new_ns.items():
                    if key != "__builtins__":
                        self.namespace[key] = value

            return str(result_dict.get("output", ""))

    def _execute_wrapper(
        self,
        code: str,
        result_dict: Any,
        current_ns: Dict[str, Any]
    ) -> None:
        buffer = io.StringIO()
        sys.stdout = buffer
        sys.stderr = buffer

        try:
            exec(code, current_ns)
            result_dict["output"] = buffer.getvalue()
            # Filter namespace to only send back picklable items
            serializable_ns = {
                k: v for k, v in current_ns.items()
                if not k.startswith("__") and not hasattr(v, "__traceback__")
            }
            result_dict["namespace"] = serializable_ns
        except Exception:
            result_dict["output"] = buffer.getvalue() + traceback.format_exc()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

    def connect_mcp(self, server_script: str) -> None:
            """
            Connects to an MCP server and exposes its tools 
            as functions in the sandbox namespace.
            """
            server_params = StdioServerParameters(
                command="uv",
                args=["run", "python", server_script],
            )
            
            # This is a simplified version for the architecture explanation.
            # In the full implementation, you'd use an async context manager
            # or a background thread to keep the session alive.
            try:
                # We fetch tool metadata and create 'proxy' functions
                # that call the MCP server.
                self.namespace["read_file"] = Toolset.read_file
                self.namespace["edit_file"] = Toolset.edit_file
                self.namespace["list_files"] = Toolset.list_files
                self.namespace["search_code"] = Toolset.search_code
                # Chapter V.2.6: Dynamically generate manual
                self._generate_manual()
            except Exception as e:
                print(f"Failed to connect MCP: {e}")

    def _generate_manual(self) -> str:
            """Mandatory Sandbox Manual (Page 12/16)."""
            manual = "Available Tools:\n"
            manual += "- read_file(filepath, start_line, end_line)\n"
            manual += "- edit_file(filepath, old_str, new_str)\n"
            manual += "- list_files(directory, pattern)\n"
            manual += "- search_code(pattern, file_pattern)\n"
            manual += "- final_answer(solution): Call this when you are done.\n"
            return manual