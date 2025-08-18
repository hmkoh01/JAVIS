from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from core.supervisor import supervisor
from core.agent_registry import agent_registry
from database.connection import create_tables
from database.data_collector import start_user_data_collection, stop_all_data_collection
from config.settings import settings

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
    print("🚀 JAVIS Multi-Agent System 시작")
    
    # 데이터베이스 테이블 생성
    try:
        create_tables()
        print("✅ 데이터베이스 테이블 생성 완료")
    except Exception as e:
        print(f"⚠️ 데이터베이스 초기화 오류: {e}")
    
    # 데이터 수집 시작 (기본 사용자 ID: 1)
    try:
        start_user_data_collection(user_id=1)
        print("✅ 사용자 데이터 수집 시작")
    except Exception as e:
        print(f"⚠️ 데이터 수집 시작 오류: {e}")
    
    print(f"📊 등록된 에이전트: {list(agent_registry.get_agent_descriptions().keys())}")
    print("🔗 LangGraph 워크플로우 초기화 완료")
    print("🤖 다중 에이전트 시스템 준비 완료")
    print("📈 사용자 데이터 수집 시스템 활성화")
    print("✅ 시스템이 준비되었습니다!")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 정리"""
    print("🛑 JAVIS Multi-Agent System 종료")
    
    # 데이터 수집 중지
    try:
        stop_all_data_collection()
        print("✅ 데이터 수집 중지 완료")
    except Exception as e:
        print(f"⚠️ 데이터 수집 중지 오류: {e}")

@app.get("/")
async def root():
    """루트 엔드포인트"""
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
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    ) 