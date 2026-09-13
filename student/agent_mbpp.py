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
import asyncio



def main() -> None:
    MBPP_SYSTEM_PROMPT = """You are an expert Python programmer agent.
        Your goal is to solve the provided programming task.
        Code: Write a Python code block using the tool calling format.
        If all tests passed, Call final_answer(answer:str) and pass the answer as a string

        TOOLS:
        - run_tests(): Runs the tests provided in the task description.
        - final_answer(answer:str): Call this after All tests passed.

        FORMAT:
        Always provide your code in a markdown block:
        ```python
        # your code here
        ```
        """
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--provider-url", required=True)
    args = parser.parse_args()
    # Load the variables from the .env file
    load_dotenv()
    # 1. Load API keys from Env (Mandatory Page 32)
    api_key_str = os.getenv("GEMINI_API_KEY", "")
    if not api_key_str:
        print("Error: OPENROUTER_API_KEY not found.")
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