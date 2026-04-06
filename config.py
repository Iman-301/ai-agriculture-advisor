"""Application configuration. Override via environment variables or `.env`."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(default=_ROOT / "data")
    mock_dir: Path = Field(default=_ROOT / "data" / "mock")

    # Optional API keys (replace mocks when set)
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    google_application_credentials: str | None = Field(
        default=None, alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")

    # Behaviour
    asr_confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    nlu_confidence_rag_min: float = Field(default=0.45, ge=0.0, le=1.0)
    rag_top_k: int = Field(default=4, ge=1, le=20)

    @property
    def knowledge_base_path(self) -> Path:
        return self.mock_dir / "knowledge_base.json"

    @property
    def market_prices_path(self) -> Path:
        return self.mock_dir / "market_prices.json"

    @property
    def farmer_profiles_path(self) -> Path:
        return self.mock_dir / "farmer_profiles.json"


settings = Settings()
