import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API 설정
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./javis.db"

    # Gemini API 설정
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Multimodal RAG 설정
    IMAGE_UPLOAD_PATH: str = "./uploads/images"
    IMAGE_PROCESSING_SIZE: tuple = (448, 448)
    MAX_IMAGE_SIZE_MB: int = 10
    SUPPORTED_IMAGE_FORMATS: list = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
    
    # RAG 설정
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    VECTOR_DB_PATH: str = "./vector_db"

    # ColQwen2 설정
    COLQWEN2_BASE_URL: str = "http://localhost:11434"
    COLQWEN2_MODEL: str = "qwen2.5-72b-instruct"
    
    # 이메일 설정
    EMAIL_FROM: Optional[str] = None
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None

    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings() 