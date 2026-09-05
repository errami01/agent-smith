import sys
import multiprocessing
import io
import traceback
from typing import Dict, Any, Optional, List
from types import ModuleType
from student.schema import SandboxConfig


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