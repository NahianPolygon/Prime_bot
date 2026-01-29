from pydantic_settings import BaseSettings
from functools import lru_cache
from langchain_google_genai import ChatGoogleGenerativeAI


class Settings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    GOOGLE_API_KEY: str = ""
    GOOGLE_MODEL: str = "gemini-2.5-flash-lite"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()


def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.GOOGLE_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.3
    )


llm = get_llm()
