"""
First FastAPI slice (Phase 1 proof): sandbox code execution and terminal
simulation. Chosen because they have zero DB/session coupling — proves the
FastAPI + WSGIMiddleware pipeline works before any domain touching the
database (coins, auth, etc.) is ported.
"""
from fastapi import APIRouter

from fastapi_app.application.sandbox.run_code import available_languages, run_code
from fastapi_app.application.sandbox.execute_terminal_command import execute_command, terminal_type
from fastapi_app.interfaces.api.schemas.sandbox import (
    RunCodeRequest, RunCodeResponse, TerminalCommandRequest, TerminalCommandResponse,
)

router = APIRouter(prefix="/api/v2/sandbox", tags=["sandbox"])


@router.get("/languages")
def list_languages():
    return available_languages()


@router.post("/run", response_model=RunCodeResponse)
def run(req: RunCodeRequest):
    result = run_code(req.language, req.code)
    return RunCodeResponse(**result.__dict__)


@router.get("/terminal/{direction_slug}/type")
def get_terminal_type(direction_slug: str):
    return {"terminal_type": terminal_type(direction_slug)}


@router.post("/terminal/execute", response_model=TerminalCommandResponse)
def execute_terminal_command(req: TerminalCommandRequest):
    result = execute_command(req.direction_slug, req.command)
    return TerminalCommandResponse(**result.__dict__)
