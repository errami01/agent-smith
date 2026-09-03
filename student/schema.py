from datetime import datetime
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field


# --- V.2 The Sandbox Configuration ---
class SandboxConfig(BaseModel):
    """Sandbox configuration for student solutions."""
    authorized_imports: List[str] = Field(default_factory=lambda: [
        "math", "math.*",
        "collections", "collections.*",
        "itertools", "re", "json",
        "typing", "typing.*",
        "functools", "operator",
        "heapq", "bisect", "copy",
        "string", "random",
        "datetime", "datetime.*",
        "array", "cmath",
    ])
    allowed_directories: List[str] = Field(default_factory=lambda: [
        "/testbed", "/tmp/agent"
    ])
    max_execution_time_seconds: int = 30
    max_memory_mb: int = 512


# --- V.3 & V.4 Task Inputs (Page 15/19 & 18/22) ---
class MBPPTaskInput(BaseModel):
    task_id: int
    task_definition: str
    function_definition: str
    test_imports: List[str] = Field(default_factory=list)
    test_list: List[str] = Field(default_factory=list)


class SWEBenchTaskInput(BaseModel):
    instance_id: str
    problem_statement: str
    docker_image: str
    eval_script: str
    hints_text: str = ""
    repo: str = ""


# --- V.5.3 Agent Output & Metrics ---
class StepMetrics(BaseModel):
    """Metrics for a single agent step (Thought -> Code -> Observation)."""
    step: int = Field(..., description="1-indexed iteration number")
    input_tokens: int
    output_tokens: int
    request_time_ms: float
    api_url: str = ""
    model_name: str = ""
    llm_output: str = Field("", description="Raw text before code extraction")
    sandbox_input: str = Field("", description="Python code sent to sandbox")
    sandbox_output: str = Field("", description="Result (stdout/stderr/error)")
    retries: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class SolutionOutput(BaseModel):
    """The final JSON structure your agent must produce."""
    task_id: str
    benchmark: Literal["mbpp", "swebench"]
    success: bool
    solution: str = Field(..., description="Python code for MBPP, git patch for SWE-bench")
    system_prompt: str
    iterations: int
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_time_seconds: float
    steps: List[StepMetrics] = Field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())