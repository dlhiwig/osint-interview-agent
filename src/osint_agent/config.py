"""Application settings loaded from environment / .env."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["openai", "anthropic"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # LLM providers
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Search backends
    perplexity_api_key: str | None = None
    tavily_api_key: str | None = None
    serper_api_key: str | None = None
    brave_search_api_key: str | None = None

    # Public records
    fec_api_key: str | None = None
    sec_edgar_user_agent: str | None = None

    # Agent config
    osint_llm_provider: Provider = "openai"
    osint_llm_model: str = "gpt-4o"
    osint_max_tool_turns: int = Field(default=20, ge=1, le=100)
    osint_report_dir: Path = Path("reports")

    def available_tools(self) -> dict[str, bool]:
        """Map tool name → whether its required credentials are present."""
        return {
            "web_search_grounded (Perplexity)": bool(self.perplexity_api_key),
            "web_search / search_news (Tavily)": bool(self.tavily_api_key),
            "google_search (Serper)": bool(self.serper_api_key),
            "brave_search (Brave)": bool(self.brave_search_api_key),
            "search_fec (FEC)": bool(self.fec_api_key),
            "search_sec_edgar (SEC)": bool(self.sec_edgar_user_agent),
            "screen_opensanctions": True,
            "wayback_snapshot": True,
            "fetch_page": True,
            "record_evidence": True,
        }

    def validate_llm_credentials(self) -> None:
        if self.osint_llm_provider == "openai" and not self.openai_api_key:
            raise RuntimeError(
                "OSINT_LLM_PROVIDER=openai but OPENAI_API_KEY is not set."
            )
        if self.osint_llm_provider == "anthropic" and not self.anthropic_api_key:
            raise RuntimeError(
                "OSINT_LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set."
            )


def load_settings() -> Settings:
    return Settings()
