from __future__ import annotations

from app.settings import settings


async def complete_json(prompt_name: str, prompt: str, variables: dict, schema: type) -> object:
    if settings.mock_llm:
        return schema.model_validate({})
    raise NotImplementedError("Real LLM not yet implemented")
