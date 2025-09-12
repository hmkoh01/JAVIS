import os
import sys
from pathlib import Path

# 현재 스크립트의 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from core.supervisor import supervisor
from core.agent_registry import agent_registry
from database.sqlite_meta import SQLiteMeta
from database.data_collector import stop_all_data_collection
from config.settings import settings
from config.logging_config import setup_logging, get_logger
import time
from tqdm import tqdm

# 로깅 설정 초기화
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="JAVIS Multi-Agent System",
    description="LangGraph 기반의 다중 에이전트 시스템",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(router, prefix="/api/v2")

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 초기화"""
    logger.info("🚀 JAVIS Multi-Agent System 시작")
    
    # SQLite 데이터베이스 초기화
    try:
        sqlite_meta = SQLiteMeta()
        logger.info("✅ SQLite 데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"⚠️ 데이터베이스 초기화 오류: {e}")
    
    # 데이터 수집은 start.py에서 관리됩니다
    logger.info("📊 데이터 수집은 start.py에서 관리됩니다")
    
    logger.info(f"📊 등록된 에이전트: {list(agent_registry.get_agent_descriptions().keys())}")
    logger.info("🔗 LangGraph 워크플로우 초기화 완료")
    logger.info("🤖 다중 에이전트 시스템 준비 완료")
    logger.info("📈 사용자 데이터 수집 시스템 활성화")
    logger.info("✅ 시스템이 준비되었습니다!")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 정리"""
    logger.info("🛑 JAVIS Multi-Agent System 종료")
    
    # 데이터 수집 중지
    try:
        stop_all_data_collection()
        logger.info("✅ 데이터 수집 중지 완료")
    except Exception as e:
        logger.error(f"⚠️ 데이터 수집 중지 오류: {e}")

@app.get("/")
async def root():
    """루트 엔드포인트"""
    logger.debug("루트 엔드포인트 접근")
    return {
        "message": "JAVIS Multi-Agent System",
        "version": "3.0.0",
        "framework": "LangGraph",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v2/health",
        "chat": "/api/v2/chat"
    }

@app.get("/info")
async def system_info():
    """시스템 정보"""
    logger.debug("시스템 정보 엔드포인트 접근")
    return {
        "name": "JAVIS Multi-Agent System",
        "version": "3.0.0",
        "framework": "LangGraph",
        "description": "LangGraph 기반의 다중 에이전트 시스템",
        "features": [
            "StateGraph 기반 워크플로우",
            "다중 에이전트 지원",
            "챗봇 에이전트",
            "코딩 에이전트",
            "대시보드 에이전트", 
            "추천 에이전트",
            "SQLite 데이터베이스",
            "데스크톱 플로팅 채팅 앱",
            "자동 데이터 수집 시스템"
        ],
        "endpoints": {
            "main": "/api/v2/process",
            "chat": "/api/v2/chat",
            "agents": "/api/v2/agents",
            "health": "/api/v2/health"
        },
        "data_collection_features": [
            "파일 시스템 스캔",
            "브라우저 히스토리 수집",
            "활성 애플리케이션 모니터링",
            "화면 활동 분석 (LLM 기반)",
            "자동 데이터베이스 저장"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    logger.info(f"서버 시작: {settings.API_HOST}:{settings.API_PORT}")
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
        timeout_keep_alive=settings.KEEP_ALIVE_TIMEOUT,
        timeout_graceful_shutdown=30
    ) 