from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .connection import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    interactions = relationship("UserInteraction", back_populates="user")
    analytics = relationship("UserAnalytics", back_populates="user")

class UserInteraction(Base):
    __tablename__ = "user_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    agent_type = Column(String(50))  # rag_chatbot, coding, dashboard, recommendation
    query = Column(Text)
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    interaction_metadata = Column(JSON, default={})
    
    # 관계
    user = relationship("User", back_populates="interactions")

class UserAnalytics(Base):
    __tablename__ = "user_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    metric_name = Column(String(100))
    metric_value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    user = relationship("User", back_populates="analytics")

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    content = Column(Text)
    category = Column(String(100))
    tags = Column(JSON, default=[])
    embedding = Column(JSON)  # 벡터 임베딩
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ImageMetadata(Base):
    __tablename__ = "image_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, index=True)
    file_path = Column(String(500))
    file_size = Column(Integer)  # bytes
    image_type = Column(String(50))  # jpg, png, etc.
    width = Column(Integer)
    height = Column(Integer)
    
    # 추출된 메타데이터
    extracted_text = Column(Text)
    visual_description = Column(Text)
    detected_objects = Column(JSON, default=[])
    detected_text = Column(JSON, default=[])
    image_tags = Column(JSON, default=[])
    
    # RAG 관련
    embedding = Column(JSON)  # 이미지 임베딩
    processed = Column(Boolean, default=False)
    
    # 타임스탬프
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    # 관계
    multimodal_content = relationship("MultimodalContent", back_populates="image_metadata")

class MultimodalContent(Base):
    __tablename__ = "multimodal_content"
    
    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String(50))  # text, image, mixed
    title = Column(String(255))
    description = Column(Text)
    
    # 텍스트 내용
    text_content = Column(Text)
    text_embedding = Column(JSON)
    
    # 이미지 참조
    image_metadata_id = Column(Integer, ForeignKey("image_metadata.id"))
    image_embedding = Column(JSON)
    
    # 메타데이터
    tags = Column(JSON, default=[])
    category = Column(String(100))
    source = Column(String(255))
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    image_metadata = relationship("ImageMetadata", back_populates="multimodal_content") 