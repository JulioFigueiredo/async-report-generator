from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    reports_dir: str = "/tmp/reports"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
