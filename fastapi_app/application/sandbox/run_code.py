"""
Use case: run user code in the sandbox.

Deliberately calls the existing, already-hardened code_runner.py at the repo
root rather than reimplementing the sandboxing (resource limits, timeouts,
temp-dir isolation) — that logic is security-sensitive and already proven in
production; duplicating it here would just create a second copy to keep in
sync and audit.
"""
import code_runner
from fastapi_app.domain.sandbox.entities import CodeExecutionResult


def available_languages() -> dict:
    return code_runner.LANGUAGES


def run_code(language: str, code: str) -> CodeExecutionResult:
    # code_runner.run_code() already returns a graceful error result for an
    # unsupported language or empty/oversized code — no need to duplicate
    # that validation here.
    result = code_runner.run_code(language, code)
    return CodeExecutionResult(
        success=result["success"],
        output=result.get("output", ""),
        error=result.get("error", ""),
        execution_time_ms=result.get("execution_time_ms", 0),
    )
