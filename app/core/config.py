from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    # App Config
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "default-secret")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    REDIS_URL: str = os.getenv("REDIS_URL")

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET")
    GITHUB_REDIRECT_URI: str = os.getenv("GITHUB_REDIRECT_URI")
    GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET")

    # xAI Grok API
    XAI_API_KEY: str = os.getenv("XAI_API_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
