from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Union
from src.llm.base_adapter import BaseAIAdapter
from src.llm.retry_handler import AISemanticError, AITechnicalError


class MockAIAdapter(BaseAIAdapter):
    """Deterministic, offline-testable AI adapter for CI and automated testing (DEC-P01).
    
    Operates strictly on injected responses, sequence queues, or provider callables.
    Does NOT depend on filesystem test fixture paths inside production code.
    """

    def __init__(
        self,
        responses: Optional[List[Union[str, Dict[str, Any], Exception]]] = None,
        default_response: Optional[Union[str, Dict[str, Any]]] = None,
        response_fn: Optional[Callable[[str], Union[str, Dict[str, Any]]]] = None,
        technical_attempt_limit: int = 3,
        semantic_attempt_limit: int = 2,
        backoff_base_delay: float = 0.0,
    ):
        super().__init__(
            technical_attempt_limit=technical_attempt_limit,
            semantic_attempt_limit=semantic_attempt_limit,
            backoff_base_delay=backoff_base_delay,
        )
        self.response_queue = list(responses) if responses else []
        self.default_response = default_response
        self.response_fn = response_fn
        self.invocations: List[Dict[str, Any]] = []

    def invoke_raw(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        self.invocations.append({"prompt": prompt, "system_instruction": system_instruction, "kwargs": kwargs})

        if self.response_queue:
            item = self.response_queue.pop(0)
            if isinstance(item, Exception):
                raise item
            if isinstance(item, dict):
                return json.dumps(item)
            return str(item)

        if self.response_fn is not None:
            res = self.response_fn(prompt)
            if isinstance(res, Exception):
                raise res
            if isinstance(res, dict):
                return json.dumps(res)
            return str(res)

        if self.default_response is not None:
            if isinstance(self.default_response, dict):
                return json.dumps(self.default_response)
            return str(self.default_response)

        # If nothing configured, return empty JSON object
        return "{}"


__all__ = [
    "MockAIAdapter",
]
