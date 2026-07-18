"""Application settings loaded from environment variables and ``.env``."""

from pathlib import Path
from typing import Self

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized and validated application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    jquants_api_key: str = Field(min_length=1, alias="JQUANTS_API_KEY")
    jquants_base_url: str = Field(
        default="https://api.jquants.com/v2", alias="JQUANTS_BASE_URL"
    )
    database_url: str = Field(
        default="sqlite:///data/app.db", alias="DATABASE_URL"
    )
    raw_data_dir: Path = Field(
        default=Path("data/raw/jquants"), alias="RAW_DATA_DIR"
    )

    @classmethod
    def load(cls, env_file: str | Path = ".env") -> Self:
        """Load settings; process environment values override the env file."""

        return cls(_env_file=env_file)

    def ensure_directories(self) -> None:
        """Create directories required for raw data and a SQLite database."""

        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        sqlite_prefix = "sqlite:///"
        if self.database_url.startswith(sqlite_prefix):
            database_path = Path(self.database_url.removeprefix(sqlite_prefix))
            if database_path.parent != Path("."):
                database_path.parent.mkdir(parents=True, exist_ok=True)
