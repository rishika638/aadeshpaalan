from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    jwt_secret: str
    storage_path: str = "/app/storage/judgments"
    dashboard_base_url: str = "http://localhost:5173"

    llm_api_key: str | None = None
    groq_api_key: str | None = None
    nic_smtp_host: str | None = None
    nic_smtp_port: int | None = None
    nic_smtp_user: str | None = None
    nic_smtp_pass: str | None = None


settings = Settings()

