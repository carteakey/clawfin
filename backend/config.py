import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def getenv(name: str, default: str = "") -> str:
    """Read AutoFin env vars with a compatibility fallback for old ClawFin installs."""
    legacy_name = name.replace("AUTOFIN_", "CLAWFIN_", 1)
    return os.getenv(name, os.getenv(legacy_name, default))


class Settings:
    """App configuration from environment variables."""

    # Database
    DB_PATH: str = getenv("AUTOFIN_DB_PATH", str(Path.home() / ".autofin" / "autofin.db"))

    # Auth
    PASSWORD: str = getenv("AUTOFIN_PASSWORD", "")
    SECRET_KEY: str = getenv("AUTOFIN_SECRET_KEY", "autofin-dev-secret-change-me")
    TOKEN_EXPIRE_HOURS: int = int(getenv("AUTOFIN_TOKEN_EXPIRE_HOURS", "72"))
    AUTOMATION_TOKEN: str = getenv("AUTOFIN_AUTOMATION_TOKEN", "")

    # SimpleFin
    SIMPLEFIN_ACCESS_URL: str = getenv("AUTOFIN_SIMPLEFIN_ACCESS_URL", "")
    SIMPLEFIN_STALE_DAYS: int = int(getenv("AUTOFIN_SIMPLEFIN_STALE_DAYS", "3"))

    # AI — direct OpenAI-compatible HTTP calls via httpx (no litellm)
    AI_PROVIDER: str = getenv("AUTOFIN_AI_PROVIDER", "ollama")  # ollama, openai, anthropic
    AI_MODEL: str = getenv("AUTOFIN_AI_MODEL", "llama3.1")
    AI_API_KEY: str = getenv("AUTOFIN_AI_API_KEY", "")
    AI_BASE_URL: str = getenv("AUTOFIN_AI_BASE_URL", "http://localhost:11434")  # Ollama default

    # Server
    HOST: str = getenv("AUTOFIN_HOST", "0.0.0.0")
    PORT: int = int(getenv("AUTOFIN_PORT", "8000"))
    CORS_ORIGINS: list[str] = getenv(
        "AUTOFIN_CORS_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000",
    ).split(",")


settings = Settings()
