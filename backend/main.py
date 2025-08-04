from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from core.supervisor import supervisor
from core.agent_registry import agent_registry

app = FastAPI(
    title="JAVIS Multi-Agent System",
    description="LangGraph 기반의 다중 에이전트 시스템 - 사용자 맞춤 AI 비서",
    version="2.0.0",
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
    print("🚀 JAVIS Multi-Agent System (LangGraph 기반) 시작")
    print(f"📊 등록된 에이전트: {list(agent_registry.get_agent_descriptions().keys())}")
    print("🔗 LangGraph 워크플로우 초기화 완료")
    print("✅ 시스템이 준비되었습니다!")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 정리"""
    print("🛑 JAVIS Multi-Agent System 종료")

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "JAVIS Multi-Agent System (LangGraph 기반)",
        "version": "2.0.0",
        "framework": "LangGraph",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v2/health"
    }

@app.get("/info")
async def system_info():
    """시스템 정보"""
    return {
        "name": "JAVIS Multi-Agent System",
        "version": "2.0.0",
        "framework": "LangGraph",
        "description": "LangGraph 기반의 다중 에이전트 시스템",
        "features": [
            "StateGraph 기반 워크플로우",
            "다중 에이전트 지원",
            "RAG 기반 챗봇",
            "코딩 에이전트",
            "대시보드 에이전트", 
            "추천 에이전트",
            "Milvus + Neo4j 통합",
            "React Framework 도구"
        ],
        "endpoints": {
            "main": "/api/v2/process",
            "agents": "/api/v2/agents",
            "rag": "/api/v2/rag",
            "health": "/api/v2/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 