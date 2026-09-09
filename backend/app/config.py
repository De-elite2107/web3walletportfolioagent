"""Central settings for the backend.

Loads the .env file from the repo root (one level above /backend) so the
frontend and backend can share a single set of environment variables.
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = REPO_ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_PATH), extra="ignore")

    anthropic_base_url: str = ""
    anthropic_auth_token: str = ""
    anthropic_api_key: str = ""
    alchemy_api_key: str = ""
    database_url: str = ""
    model_tier: str = "draft"
    # Used directly by the analysis/chat endpoints for now, ahead of the
    # full tier system - a cheap/fast model by default.
    model_name: str = "anthropic/claude-haiku-4.5"


settings = Settings()
