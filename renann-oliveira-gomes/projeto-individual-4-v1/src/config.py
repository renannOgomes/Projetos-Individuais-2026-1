"""Configurações globais da aplicação."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações da aplicação via variáveis de ambiente."""

    # LLM
    llm_provider: str = "gemini"
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Database
    database_url: str = "postgresql://uda_user:uda_password@postgres:5432/uda_rag"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Embeddings
    embeddings_model: str = "all-MiniLM-L6-v2"
    vector_dimension: int = 384

    # Ingestão
    scan_cron_hour: int = 6
    scan_cron_minute: int = 0
    pdf_storage_path: Path = Path("data/pdfs")

    # Webhook
    webhook_secret: str = "your-webhook-secret"

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


_settings: Settings | None = None


def get_settings() -> Settings:
    """Retorna instância global de Settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
