import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    gemini_api_key: str = ""
    chroma_persist_dir: str = str(BASE_DIR / "chroma_db")
    data_dir: str = str(Path(__file__).resolve().parent / "data")
    max_input_length: int = 4000
    max_tokens: int = 8192
    rate_limit_rpm: int = 30
    cors_origins: list[str] = [
        "https://himanshu-suri.azurewebsites.net",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://127.0.0.1:8080",
    ]
    daily_ip_limit: int = 50

    model_config = {"env_file": str(BASE_DIR / ".env"), "extra": "ignore"}


settings = Settings()
