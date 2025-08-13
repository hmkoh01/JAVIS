from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from core.supervisor import supervisor
from core.agent_registry import agent_registry
from database.connection import create_tables
from config.settings import settings

app = FastAPI(
    title="JAVIS Multi-Agent System",
    description="LangGraph 기반의 다중 에이전트 시스템 - 멀티모달 RAG 지원",
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
    print("🚀 JAVIS Multi-Agent System (멀티모달 RAG 지원) 시작")
    
    # 데이터베이스 테이블 생성
    try:
        create_tables()
        print("✅ 데이터베이스 테이블 생성 완료")
    except Exception as e:
        print(f"⚠️ 데이터베이스 초기화 오류: {e}")
    
    print(f"📊 등록된 에이전트: {list(agent_registry.get_agent_descriptions().keys())}")
    print("🔗 LangGraph 워크플로우 초기화 완료")
    print("🤖 멀티모달 RAG 시스템 준비 완료")
    print("✅ 시스템이 준비되었습니다!")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 정리"""
    print("🛑 JAVIS Multi-Agent System 종료")

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "JAVIS Multi-Agent System (멀티모달 RAG 지원)",
        "version": "3.0.0",
        "framework": "LangGraph",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v2/health",
        "multimodal": "/api/v2/multimodal"
    }

@app.get("/info")
async def system_info():
    """시스템 정보"""
    return {
        "name": "JAVIS Multi-Agent System",
        "version": "3.0.0",
        "framework": "LangGraph",
        "description": "LangGraph 기반의 다중 에이전트 시스템 with 멀티모달 RAG",
        "features": [
            "StateGraph 기반 워크플로우",
            "다중 에이전트 지원",
            "멀티모달 RAG 챗봇",
            "이미지 업로드 및 메타데이터 추출",
            "Gemini API 통합",
            "코딩 에이전트",
            "대시보드 에이전트", 
            "추천 에이전트",
            "SQLite 데이터베이스",
            "Streamlit 프론트엔드"
        ],
        "endpoints": {
            "main": "/api/v2/process",
            "agents": "/api/v2/agents",
            "multimodal": "/api/v2/multimodal",
            "rag": "/api/v2/rag",
            "health": "/api/v2/health"
        },
        "multimodal_features": [
            "이미지 업로드 및 처리",
            "OCR 및 시각적 설명 추출",
            "이미지 기반 검색",
            "멀티모달 콘텐츠 생성",
            "Gemini API 기반 응답 생성"
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