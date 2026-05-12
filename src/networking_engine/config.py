from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", validation_alias="OPENAI_MODEL")

    search_provider: Literal["tavily", "brave"] = Field(
        default="tavily",
        validation_alias="SEARCH_PROVIDER",
    )
    tavily_api_key: str | None = Field(default=None, validation_alias="TAVILY_API_KEY")
    brave_api_key: str | None = Field(default=None, validation_alias="BRAVE_API_KEY")

    max_urls: int = Field(default=25, ge=1, le=100, validation_alias="MAX_URLS")
    max_people: int = Field(default=12, ge=1, le=50, validation_alias="MAX_PEOPLE")

    http_timeout_s: float = Field(default=20.0, validation_alias="HTTP_TIMEOUT_S")
    user_agent: str = Field(
        default="networking-engine/0.1 (+https://github.com/local/networking-engine)",
        validation_alias="HTTP_USER_AGENT",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
