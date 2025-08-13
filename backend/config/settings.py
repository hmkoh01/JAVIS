import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API 설정
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./javis.db"
    
    # OpenAI 설정
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # Gemini API 설정
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Ollama 설정
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"
    
    # Multimodal RAG 설정
    IMAGE_UPLOAD_PATH: str = "./uploads/images"
    IMAGE_PROCESSING_SIZE: tuple = (448, 448)
    MAX_IMAGE_SIZE_MB: int = 10
    SUPPORTED_IMAGE_FORMATS: list = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
    
    # RAG 설정
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    VECTOR_DB_PATH: str = "./vector_db"
    
    # Milvus 설정
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "knowledge_base"
    
    # Neo4j 설정
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # 이메일 설정
    EMAIL_FROM: Optional[str] = None
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    
    # MCP 서버 설정
    MCP_SERVER_URL: str = "http://localhost:8001"
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings() 