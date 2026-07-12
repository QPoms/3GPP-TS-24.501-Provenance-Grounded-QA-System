"""Environment-backed runtime settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    openai_base_url: str | None
    max_tool_calls: int = 6

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            from dotenv import load_dotenv
        except ImportError:
            load_dotenv = None
        if load_dotenv:
            load_dotenv(dotenv_path=Path.cwd() / ".env", encoding="utf-8-sig")
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing. Put it in the local .env file.")
        if not model:
            raise RuntimeError("OPENAI_MODEL is missing. Set it to a model available to your API account.")
        return cls(
            openai_api_key=api_key,
            openai_model=model,
            openai_base_url=base_url,
            max_tool_calls=int(os.getenv("TELECOM_AGENT_MAX_TOOL_CALLS", "6")),
        )


def create_openai_client(settings: Settings):
    try:
        from openai import OpenAI
    except ImportError as error:  # pragma: no cover - environment-specific
        raise RuntimeError("Install project dependencies before using the GPT agent") from error
    options = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        options["base_url"] = settings.openai_base_url
    return OpenAI(**options)
