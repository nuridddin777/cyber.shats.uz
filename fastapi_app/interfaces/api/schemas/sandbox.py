from pydantic import BaseModel, Field


class RunCodeRequest(BaseModel):
    language: str
    code: str = Field(max_length=20000)


class RunCodeResponse(BaseModel):
    success: bool
    output: str
    error: str
    execution_time_ms: int


class TerminalCommandRequest(BaseModel):
    direction_slug: str
    command: str


class TerminalCommandResponse(BaseModel):
    output: str
    is_dangerous: bool
    cleared: bool
