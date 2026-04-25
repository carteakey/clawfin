import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """App configuration from environment variables."""

    # Database
    DB_PATH: str = os.getenv("CLAWFIN_DB_PATH", str(Path.home() / ".clawfin" / "clawfin.db"))

    # Auth
    PASSWORD: str = os.getenv("CLAWFIN_PASSWORD", "")
    SECRET_KEY: str = os.getenv("CLAWFIN_SECRET_KEY", "clawfin-dev-secret-change-me")
    TOKEN_EXPIRE_HOURS: int = int(os.getenv("CLAWFIN_TOKEN_EXPIRE_HOURS", "72"))
    AUTOMATION_TOKEN: str = os.getenv("CLAWFIN_AUTOMATION_TOKEN", "")

    # SimpleFin
    SIMPLEFIN_ACCESS_URL: str = os.getenv("CLAWFIN_SIMPLEFIN_ACCESS_URL", "")

    # AI — direct OpenAI-compatible HTTP calls via httpx (no litellm)
    AI_PROVIDER: str = os.getenv("CLAWFIN_AI_PROVIDER", "ollama")  # ollama, openai, anthropic
    AI_MODEL: str = os.getenv("CLAWFIN_AI_MODEL", "llama3.1")
    AI_API_KEY: str = os.getenv("CLAWFIN_AI_API_KEY", "")
    AI_BASE_URL: str = os.getenv("CLAWFIN_AI_BASE_URL", "http://localhost:11434")  # Ollama default

    # Server
    HOST: str = os.getenv("CLAWFIN_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("CLAWFIN_PORT", "8000"))
    CORS_ORIGINS: list[str] = os.getenv(
        "CLAWFIN_CORS_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000",
    ).split(",")


settings = Settings()
