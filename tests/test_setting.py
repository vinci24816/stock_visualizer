from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config.setting import Settings


def test_loads_values_from_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "JQUANTS_API_KEY=file-key\n"
        "DATABASE_URL=sqlite:///custom/app.db\n"
        "RAW_DATA_DIR=custom/raw\n",
        encoding="utf-8",
    )

    settings = Settings.load(env_file)

    assert settings.jquants_api_key == "file-key"
    assert settings.database_url == "sqlite:///custom/app.db"
    assert settings.raw_data_dir == Path("custom/raw")


def test_environment_takes_precedence_over_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("JQUANTS_API_KEY=file-key\n", encoding="utf-8")
    monkeypatch.setenv("JQUANTS_API_KEY", "environment-key")

    assert Settings.load(env_file).jquants_api_key == "environment-key"


def test_api_key_is_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JQUANTS_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings.load(tmp_path / "missing.env")


def test_ensure_directories_creates_required_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    settings = Settings(
        JQUANTS_API_KEY="test-key",
        DATABASE_URL="sqlite:///database/app.db",
        RAW_DATA_DIR="raw/jquants",
    )

    settings.ensure_directories()

    assert (tmp_path / "database").is_dir()
    assert (tmp_path / "raw" / "jquants").is_dir()
