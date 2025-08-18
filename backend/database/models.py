from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float, Boolean, LargeBinary
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
    files = relationship("UserFile", back_populates="user")
    browser_history = relationship("BrowserHistory", back_populates="user")
    active_apps = relationship("ActiveApplication", back_populates="user")
    screen_activities = relationship("ScreenActivity", back_populates="user")

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

# 새로운 모델들 - 사용자 데이터 수집용

class UserFile(Base):
    __tablename__ = "user_files"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # 파일 정보
    file_path = Column(String(1000), index=True)
    file_name = Column(String(255))
    file_size = Column(Integer)  # bytes
    file_type = Column(String(50))  # 확장자
    file_category = Column(String(100))  # 문서, 이미지, 비디오 등
    
    # 파일 내용 (텍스트 파일의 경우)
    content_preview = Column(Text)  # 파일 내용 미리보기
    content_embedding = Column(JSON)  # 텍스트 임베딩
    
    # 메타데이터
    created_date = Column(DateTime)
    modified_date = Column(DateTime)
    accessed_date = Column(DateTime)
    
    # 처리 상태
    processed = Column(Boolean, default=False)
    processing_error = Column(Text)
    
    # 타임스탬프
    discovered_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    # 관계
    user = relationship("User", back_populates="files")

class BrowserHistory(Base):
    __tablename__ = "browser_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # 브라우저 정보
    browser_name = Column(String(50))  # Chrome, Firefox, Edge 등
    browser_version = Column(String(50))
    
    # 방문 정보
    url = Column(String(2000))
    title = Column(String(500))
    visit_count = Column(Integer, default=1)
    
    # 시간 정보
    visit_time = Column(DateTime)
    last_visit_time = Column(DateTime)
    
    # 메타데이터
    page_transition = Column(String(100))  # 링크, 타이핑 등
    visit_duration = Column(Integer)  # 초 단위
    
    # 처리 상태
    content_analyzed = Column(Boolean, default=False)
    content_summary = Column(Text)
    content_embedding = Column(JSON)
    
    # 타임스탬프
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    user = relationship("User", back_populates="browser_history")

class ActiveApplication(Base):
    __tablename__ = "active_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # 애플리케이션 정보
    app_name = Column(String(255))
    app_path = Column(String(1000))
    app_version = Column(String(100))
    app_category = Column(String(100))  # 생산성, 엔터테인먼트, 개발 등
    
    # 실행 정보
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Integer)  # 초 단위
    
    # 윈도우 정보
    window_title = Column(String(500))
    window_state = Column(String(50))  # active, minimized, maximized
    
    # 메타데이터
    cpu_usage = Column(Float)  # CPU 사용률
    memory_usage = Column(Float)  # 메모리 사용률 (MB)
    
    # 타임스탬프
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    user = relationship("User", back_populates="active_apps")

class ScreenActivity(Base):
    __tablename__ = "screen_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # 스크린샷 정보
    screenshot_path = Column(String(1000))
    screenshot_data = Column(LargeBinary)  # 이미지 바이너리 데이터
    
    # 화면 분석 결과
    activity_description = Column(Text)  # LLM이 분석한 활동 설명
    activity_category = Column(String(100))  # 작업, 브라우징, 엔터테인먼트 등
    activity_confidence = Column(Float)  # 분석 신뢰도 (0-1)
    
    # 감지된 요소들
    detected_apps = Column(JSON)  # 감지된 애플리케이션들
    detected_text = Column(JSON)  # 감지된 텍스트들
    detected_objects = Column(JSON)  # 감지된 객체들
    
    # 메타데이터
    screen_resolution = Column(String(50))  # 1920x1080
    color_mode = Column(String(20))  # light, dark
    
    # 임베딩
    screenshot_embedding = Column(JSON)  # 이미지 임베딩
    activity_embedding = Column(JSON)  # 활동 설명 임베딩
    
    # 타임스탬프
    captured_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime)
    
    # 관계
    user = relationship("User", back_populates="screen_activities")

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