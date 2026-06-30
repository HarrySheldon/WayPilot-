from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorRecoveryPolicy:
    max_model_attempts: int = 2
    max_tool_attempts: int = 2

    def __post_init__(self) -> None:
        if self.max_model_attempts < 1:
            raise ValueError("max_model_attempts must be at least 1")
        if self.max_tool_attempts < 1:
            raise ValueError("max_tool_attempts must be at least 1")
