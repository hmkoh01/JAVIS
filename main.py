import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from database.connection import init_db
from api.routes import router
from utils.helpers import setup_logging, create_directories

# 로깅 설정
setup_logging(settings.LOG_LEVEL)

# 필요한 디렉토리 생성
create_directories([
    settings.VECTOR_DB_PATH,
    "logs",
    "temp"
])

# FastAPI 앱 생성
app = FastAPI(
    title="JAVIS Multi-Agent System",
    description="사용자 맞춤 AI 비서를 위한 Supervisor 기반 Multi-Agent System",
    version="1.0.0"
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(router, prefix=settings.API_PREFIX)

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트"""
    print("🚀 JAVIS Multi-Agent System 시작 중...")
    
    # 데이터베이스 초기화
    try:
        init_db()
        print("✅ 데이터베이스 초기화 완료")
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
    
    print("✅ JAVIS Multi-Agent System이 성공적으로 시작되었습니다!")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행되는 이벤트"""
    print("🛑 JAVIS Multi-Agent System 종료 중...")

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "JAVIS Multi-Agent System API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    ) 