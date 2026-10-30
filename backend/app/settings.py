from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/insurvas"
    database_url_test: str = "postgresql+asyncpg://postgres:postgres@db:5432/insurvas_test"
    serper_api_key: str = ""
    google_places_key: str = ""
    anthropic_api_key: str = ""
    mock_llm: bool = True
    llm_model: str = "claude-sonnet-5-5"
    log_level: str = "INFO"
    config_dir: str = "config"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
