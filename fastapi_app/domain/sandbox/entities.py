"""Pure value objects for the sandbox domain — no framework, no I/O."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CodeExecutionResult:
    success: bool
    output: str
    error: str
    execution_time_ms: int


@dataclass(frozen=True)
class TerminalCommandResult:
    output: str
    is_dangerous: bool
    cleared: bool
