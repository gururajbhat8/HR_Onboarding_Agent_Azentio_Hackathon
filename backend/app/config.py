from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://hr_user:hr_password@localhost:5432/hr_onboarding"
    gemini_api_key: str = ""
    embedding_model: str = "models/gemini-embedding-001"
    llm_model: str = "gemini-2.5-flash"
    embedding_dimensions: int = 768
    upload_dir: str = "uploads"
    max_upload_mb: int = 10
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
