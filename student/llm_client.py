import time
import httpx
from typing import List, Dict, Any, Optional
from student.schema import StepMetrics


class LLMClient:
    def __init__(
        self,
        model_name: str,
        api_url: str,
        api_keys: List[str]
    ) -> None:
        self.model_name = model_name
        self.api_url = api_url
        self.api_keys = api_keys
        self.current_key_idx = 0

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_keys[self.current_key_idx]}",
            "Content-Type": "application/json"
        }

    def _rotate_key(self) -> None:
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)

    def request(
        self,
        messages: List[Dict[str, str]],
        step_idx: int,
        stop_sequences: Optional[List[str]] = None
    ) -> StepMetrics:
        """Performs a request with retry logic and token rotation."""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stop": stop_sequences or ["Observation:", "<end_code>"],
            "temperature": 0.0  # Coding agents require determinism
        }

        start_time = time.time()
        retries = 0
        
        while retries < len(self.api_keys) * 2:
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(
                        self.api_url,
                        headers=self._get_headers(),
                        json=payload
                    )
                
                if response.status_code == 429:  # Rate limit
                    self._rotate_key()
                    retries += 1
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                
                return StepMetrics(
                    step=step_idx,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    request_time_ms=(time.time() - start_time) * 1000,
                    api_url=self.api_url,
                    model_name=self.model_name,
                    llm_output=content,
                    retries=retries
                )
            except Exception as e:
                retries += 1
                self._rotate_key()
                if retries >= len(self.api_keys) * 2:
                    raise RuntimeError(f"LLM Request failed after retries: {e}")
        
        raise RuntimeError("Unreachable")