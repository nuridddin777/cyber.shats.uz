"""
Diagnostic test for the "stack" bug in the real, current codebase (main @ 91072a8).

Run with:
    ./.venv/bin/pytest tests/ -v
"""
import anthropic

import ai as ai_module

# Anthropic model IDs actually served today (see claude-api reference).
VALID_CLAUDE_MODELS = {
    'claude-sonnet-5',
    'claude-opus-5',
    'claude-fable-5',
    'claude-haiku-4-5-20251001',
}


class _FakeTextBlock:
    def __init__(self, text):
        self.type = 'text'
        self.text = text


class _FakeMessages:
    def __init__(self, captured):
        self._captured = captured

    def create(self, **kwargs):
        self._captured['kwargs'] = kwargs
        return type('FakeResp', (), {'content': [_FakeTextBlock('ok')]})()


class _FakeAnthropicClient:
    def __init__(self, captured):
        self.messages = _FakeMessages(captured)


def test_anthropic_fallback_uses_a_currently_valid_claude_model(monkeypatch):
    """
    ai.py:214 (_call_anthropic) hardcodes model="claude-sonnet-4-6", which is
    not a real Claude model id. Anthropic is used as the paid fallback when
    Gemini is unset or failing (see call_ai_assistant, ai.py:242-256), so
    every AI feature that reaches this fallback (main AI assistant, SMM AI,
    code help, AI test generation, AI recommendations — anything routing
    through ai.call_ai_assistant) silently fails there and falls back to the
    canned FALLBACK_REPLIES demo text instead of a real answer.
    """
    captured = {}
    monkeypatch.setattr(anthropic, 'Anthropic', lambda *a, **kw: _FakeAnthropicClient(captured))

    reply, is_live = ai_module._call_anthropic(
        system_prompt="test system prompt",
        user_message="salom",
        history=[],
        images=None,
        fallback="fallback text",
    )

    assert is_live is True
    assert 'kwargs' in captured, "_call_anthropic never called client.messages.create()"
    model = captured['kwargs'].get('model')
    assert model in VALID_CLAUDE_MODELS, (
        f"ai.py's Anthropic fallback sends model={model!r}, which is not a real "
        f"Claude model id (valid: {sorted(VALID_CLAUDE_MODELS)}). Every real "
        f"request through this path fails."
    )
