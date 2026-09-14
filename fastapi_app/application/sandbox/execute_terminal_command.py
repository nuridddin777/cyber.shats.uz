"""
Use case: execute a simulated-terminal command for a given learning direction.

Same reasoning as run_code.py — wraps the existing terminal_sim.py rather
than reimplementing its command allow/deny lists and safety checks.
"""
import terminal_sim
from fastapi_app.domain.sandbox.entities import TerminalCommandResult


def terminal_type(direction_slug: str) -> str:
    return terminal_sim.get_terminal_type(direction_slug)


def execute_command(direction_slug: str, command: str) -> TerminalCommandResult:
    result = terminal_sim.execute_command(direction_slug, command)
    return TerminalCommandResult(
        output=result.get("output", ""),
        is_dangerous=result.get("is_dangerous", False),
        cleared=result.get("cleared", False),
    )
