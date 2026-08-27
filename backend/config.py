import os

from dotenv import load_dotenv

load_dotenv()


def _env_or_none(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _default_api_key_env(provider: str) -> str | None:
    return {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "qwen": "DASHSCOPE_API_KEY",
    }.get(provider)


class Config:
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

    PREVIEW_LLM_PROVIDER = os.getenv("PREVIEW_LLM_PROVIDER", "ollama")
    PREVIEW_LLM_MODEL = _env_or_none("PREVIEW_LLM_MODEL")
    PREVIEW_LLM_BASE_URL = _env_or_none("PREVIEW_LLM_BASE_URL")
    PREVIEW_LLM_API_KEY_ENV = _env_or_none("PREVIEW_LLM_API_KEY_ENV") or _default_api_key_env(
        PREVIEW_LLM_PROVIDER
    )

    MAPPING_LLM_PROVIDER = os.getenv("MAPPING_LLM_PROVIDER", "deepseek")
    MAPPING_LLM_MODEL = _env_or_none("MAPPING_LLM_MODEL") or "deepseek-v4-flash"
    MAPPING_LLM_BASE_URL = _env_or_none("MAPPING_LLM_BASE_URL") or DEEPSEEK_BASE_URL
    MAPPING_LLM_API_KEY_ENV = _env_or_none("MAPPING_LLM_API_KEY_ENV") or _default_api_key_env(
        MAPPING_LLM_PROVIDER
    )
