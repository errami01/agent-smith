import os
from dotenv import load_dotenv
import json
import argparse
import sys
from typing import List

from student.schema import MBPPTaskInput, SolutionOutput, SandboxConfig
from student.llm_client import LLMClient
from student.sandbox import Sandbox
from student.orchestrator import Orchestrator



def main() -> None:
    MBPP_SYSTEM_PROMPT = """You are an expert Python programmer agent.
    Solve the given Python task inside one executable ```python code block per turn.

    Workflow:
    1. Write the solution function and test it with `run_tests(code=..., tests=...)` (or asserts).
    2. As soon as tests pass, call `final_answer(code_str)` passing ONLY the Python function code as a string.

    Example:
    ```python
    code = '''def add(a, b):
        return a + b'''
    res = run_tests(code=code, tests=["assert add(1, 2) == 3"])
    print(res)
    if "PASSED" in res:
        final_answer(code)
    ```"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--provider-url", required=True)
    args = parser.parse_args()
    # Load the variables from the .env file
    load_dotenv()
    # 1. Load API keys from Env (Mandatory Page 32)
    api_key_str = os.getenv("GROQ_API_KEY", "")
    if not api_key_str:
        print("Error: GROQ_API_KEY not found.")
        sys.exit(1)
    api_keys = api_key_str.split(",")

    # 2. Load Task
    with open(args.task_file, "r") as f:
        task_data = json.load(f)
        task = MBPPTaskInput(**task_data)

    # 3. Setup Components
    llm = LLMClient(args.model_name, args.provider_url, api_keys)
    
    # MBPP Hard Limits (Page 34)
    config = SandboxConfig(
        max_execution_time_seconds=120,
        authorized_imports=["math", "re", "collections", "itertools", "typing"]
    )
    sandbox = Sandbox(config)
    
    # Inject run_tests into sandbox specifically for this task
    # from student.tools import Toolset
    # sandbox.namespace["run_tests"] = lambda: Toolset.run_tests(
    #     sandbox.run_code("# capture state"), # Simplified for logic
    #     task.test_list
    # )
    sandbox.connect_mcp("mcp_tools_mbpp.py")
    orchestrator = Orchestrator(
        llm=llm,
        sandbox=sandbox,
        system_prompt=MBPP_SYSTEM_PROMPT,
        max_iterations=10  # MBPP Limit
    )

    # 4. Run Agent
    print(f"Solving MBPP Task {task.task_id}...")
    problem_description = (
        f"Task: {task.task_definition}\n"
        f"Function signature: {task.function_definition}\n"
        f"Test cases: {task.test_list}"
    )
    print("orchestrator")
    result: SolutionOutput
    result = orchestrator.solve(
        str(task.task_id), 
        problem_description
    )
    # sandbox.close()
    # print("after orchestrator")
    # 5. Save Output (Mandatory for evaluation)
    with open(args.output, "w") as f:
        f.write(result.model_dump_json(indent=2))
    print(f"Result saved to {args.output}. Success: {result.success}")

if __name__ == "__main__":
    main()