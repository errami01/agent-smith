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
        max_iterations: int = 10
    ) -> None:
        self.llm = llm
        self.sandbox = sandbox
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

    def _extract_code(self, text: str) -> Optional[str]:
        """Extracts Python code from various formats (Page 10)."""
        # 1. Standard Markdown blocks
        match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1)
        
        # 2. Custom tags mentioned in PDF
        match = re.search(r"<code>(.*?)</code>", text, re.DOTALL)
        if match:
            return match.group(1)
            
        return None

    def solve(self, task_id: str, problem_desc: str) -> SolutionOutput:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": problem_desc}
        ]
        
        steps: List[StepMetrics] = []
        start_time = time.time()
        final_solution = ""
        success = False

        for i in range(1, self.max_iterations + 1):
            # 1. Get LLM Response (Thought + Code)
            step_metrics = self.llm.request(messages, i)
            
            # 2. Extract Code
            code = self._extract_code(step_metrics.llm_output)
            step_metrics.sandbox_input = code or ""
            
            if not code:
                step_metrics.sandbox_output = "Error: No valid code block found."
                steps.append(step_metrics)
                messages.append({"role": "assistant", "content": step_metrics.llm_output})
                messages.append({"role": "user", "content": step_metrics.sandbox_output})
                continue

            # 3. Execute in Sandbox (Observation)
            observation = self.sandbox.run_code(code)
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
            system_prompt=self.system_prompt,
            iterations=len(steps),
            total_requests=len(steps),
            total_input_tokens=sum(s.input_tokens for s in steps),
            total_output_tokens=sum(s.output_tokens for s in steps),
            total_time_seconds=time.time() - start_time,
            steps=steps
        )