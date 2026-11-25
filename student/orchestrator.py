import re
import time
from typing import List, Dict, Any, Optional
from student.schema import SolutionOutput, StepMetrics, MBPPTaskInput
from student.sandbox import Sandbox
from student.llm_client import LLMClient


class Orchestrator:
    def __init__(
        self,
        llm: LLMClient,
        sandbox: Sandbox,
        system_prompt: str,
        max_iterations: int = 3
    ) -> None:
        self.llm = llm
        self.sandbox = sandbox
        self.max_iterations = max_iterations
        # DYNAMIC INJECTION:
        # Get the tool manual from the sandbox and append it to the prompt
        tool_manual = self.sandbox.get_tool_manual()
        self.full_system_prompt = f"{system_prompt}\n\n{tool_manual}"

    def _extract_code(self, text: str) -> Optional[str]:
        """Extracts Python code from various formats."""
        # 1. Standard Markdown blocks
        match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1)
        
        # 2. Custom tags mentioned
        match = re.search(r"<code>(.*?)</code>", text, re.DOTALL)
        if match:
            return match.group(1)
            
        return None
    def _truncate_observation(self, text: str, max_chars: int = 5000) -> str:
        """Truncates overly long tool outputs (head + tail) to save tokens."""
        if len(text) <= max_chars or "FINAL_ANSWER_TRIGGERED:" in text:
            return text
        half = max_chars // 2
        omitted = len(text) - max_chars
        notice = (
            f"\n\n... [Tool output was truncated due to size limits: "
            f"{omitted} chars omitted out of {len(text)}. "
            f"Use read_file with start_line/end_line or narrower search_code.] ...\n\n"
        )
        return text[:half] + notice + text[-half:]

    def solve(self, task_id: str, problem_desc: str) -> SolutionOutput:
        print(self.full_system_prompt)
        print(problem_desc)
        # exit()
        messages = [
            {"role": "system", "content": self.full_system_prompt},
            {"role": "user", "content": problem_desc}
        ]
        
        steps: List[StepMetrics] = []
        start_time = time.time()
        final_solution = ""
        success = False

        for i in range(1, self.max_iterations + 1):
            # 1. Get LLM Response (Thought + Code)
            step_metrics = self.llm.request(messages, i)
            print(f"llm:\n{step_metrics.llm_output}")
            # 2. Extract Code
            code = self._extract_code(step_metrics.llm_output)
            print(f"Extracted code: \n{code}")
            step_metrics.sandbox_input = code or ""
            
            if not code:
                step_metrics.sandbox_output = (
                "Error: No valid code block found. "
                "Wrap ALL Python code (including final_answer(...)) in ```python ... ```.")
                steps.append(step_metrics)
                messages.append({"role": "assistant", "content": step_metrics.llm_output})
                messages.append({"role": "user", "content": step_metrics.sandbox_output})
                continue

            # 3. Execute in Sandbox (Observation)
            observation = self.sandbox.run_code(code)
            if not observation.strip():
                observation = "Code executed with no output. Print test results or call final_answer(solution) to submit."
            observation = self._truncate_observation(observation)
            print(f"Observations: \n {observation}")
            step_metrics.sandbox_output = observation
            steps.append(step_metrics)

            # Check for termination
            if "FINAL_ANSWER_TRIGGERED:" in observation:
                success = True
                final_solution = observation.split("FINAL_ANSWER_TRIGGERED:")[1].strip()
                break

            # 4. Feed back to loop
            messages.append({"role": "assistant", "content": step_metrics.llm_output})
            messages.append({"role": "user", "content": f"Observation: {observation}"})

        return SolutionOutput(
            task_id=task_id,
            benchmark="mbpp",  # Default for now
            success=success,
            solution=final_solution,
            system_prompt=self.full_system_prompt,
            iterations=len(steps),
            total_requests=sum(1 + s.retries for s in steps),
            total_input_tokens=sum(s.input_tokens for s in steps),
            total_output_tokens=sum(s.output_tokens for s in steps),
            total_time_seconds=time.time() - start_time,
            steps=steps
        )