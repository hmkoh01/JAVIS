from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
from core.supervisor import supervisor, UserIntent, SupervisorResponse
from core.agent_registry import agent_registry
from agents.base_agent import AgentResponse

router = APIRouter()

class UserRequest(BaseModel):
    """사용자 요청 모델"""
    user_id: Optional[int] = None
    message: str
    context: Dict[str, Any] = {}

class AgentRequest(BaseModel):
    """특정 에이전트 요청 모델"""
    user_id: Optional[int] = None
    message: str
    agent_type: str

@router.post("/process", response_model=SupervisorResponse)
async def process_user_request(request: UserRequest):
    """사용자 요청을 처리하고 적절한 에이전트를 선택하여 실행합니다 (LangGraph 기반)."""
    try:
        user_intent = UserIntent(
            user_id=request.user_id,
            message=request.message,
            context=request.context
        )
        
        response = await supervisor.process_user_intent(user_intent)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요청 처리 중 오류가 발생했습니다: {str(e)}")

@router.post("/agent/{agent_type}", response_model=AgentResponse)
async def process_with_specific_agent(agent_type: str, request: AgentRequest):
    """특정 에이전트로 요청을 처리합니다."""
    try:
        agent = agent_registry.get_agent(agent_type)
        if not agent:
            raise HTTPException(status_code=404, detail=f"에이전트를 찾을 수 없습니다: {agent_type}")
        
        response = await agent.process(request.message, request.user_id)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"에이전트 실행 중 오류가 발생했습니다: {str(e)}")

@router.get("/agents", response_model=Dict[str, str])
async def get_available_agents():
    """사용 가능한 에이전트 목록을 반환합니다."""
    try:
        return supervisor.get_available_agents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"에이전트 목록 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/agents/{agent_type}/tools")
async def get_agent_tools(agent_type: str):
    """특정 에이전트의 사용 가능한 도구 목록을 반환합니다."""
    try:
        agent = agent_registry.get_agent(agent_type)
        if not agent:
            raise HTTPException(status_code=404, detail=f"에이전트를 찾을 수 없습니다: {agent_type}")
        
        # 챗봇 에이전트의 경우 도구 목록 반환
        if hasattr(agent, 'get_available_tools'):
            tools = agent.get_available_tools()
            return {"agent_type": agent_type, "tools": tools}
        elif hasattr(agent, 'get_available_operations'):
            operations = agent.get_available_operations()
            return {"agent_type": agent_type, "operations": operations}
        else:
            return {"agent_type": agent_type, "tools": []}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"도구 목록 조회 중 오류가 발생했습니다: {str(e)}")

@router.post("/agents/{agent_type}/tools/{tool_name}")
async def execute_specific_tool(agent_type: str, tool_name: str, request: AgentRequest):
    """특정 에이전트의 특정 도구를 실행합니다."""
    try:
        agent = agent_registry.get_agent(agent_type)
        if not agent:
            raise HTTPException(status_code=404, detail=f"에이전트를 찾을 수 없습니다: {agent_type}")
        
        # 챗봇 에이전트의 경우 특정 도구 실행
        if hasattr(agent, 'process_with_specific_tool'):
            response = await agent.process_with_specific_tool(
                request.message, 
                tool_name,
                user_id=request.user_id
            )
            return response
        else:
            raise HTTPException(status_code=400, detail=f"에이전트 {agent_type}는 도구 실행을 지원하지 않습니다.")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"도구 실행 중 오류가 발생했습니다: {str(e)}")

@router.get("/health")
async def health_check():
    """시스템 상태를 확인합니다."""
    try:
        available_agents = supervisor.get_available_agents()
        return {
            "status": "healthy",
            "available_agents": list(available_agents.keys()),
            "graph_execution": True,
            "langgraph_based": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시스템 상태 확인 중 오류가 발생했습니다: {str(e)}")

@router.get("/graph/info")
async def get_graph_info():
    """LangGraph 워크플로우 정보를 반환합니다."""
    try:
        return supervisor.get_graph_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"그래프 정보 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/graph/visualize")
async def visualize_graph():
    """LangGraph 워크플로우를 Mermaid 형식으로 시각화합니다."""
    try:
        mermaid_diagram = supervisor.visualize_graph()
        return {
            "mermaid": mermaid_diagram,
            "format": "mermaid",
            "description": "LangGraph 워크플로우 다이어그램"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"그래프 시각화 중 오류가 발생했습니다: {str(e)}")

@router.get("/debug/state")
async def get_debug_state():
    """디버깅을 위한 시스템 상태 정보를 반환합니다."""
    try:
        return {
            "supervisor": {
                "type": "LangGraphSupervisor",
                "llm_available": supervisor.llm is not None,
                "agent_count": len(supervisor.get_available_agents())
            },
            "agent_registry": {
                "registered_agents": list(agent_registry.get_agent_types()),
                "agent_nodes": list(agent_registry.get_all_agent_nodes().keys())
            },
            "graph": supervisor.get_graph_info(),
            "framework": "LangGraph"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"디버그 정보 조회 중 오류가 발생했습니다: {str(e)}")

# RAG 관련 라우터 추가
rag_router = APIRouter(prefix="/rag", tags=["RAG"])

@rag_router.post("/process")
async def process_knowledge(request: Dict[str, Any]):
    """지식을 처리하여 벡터 DB와 그래프 DB에 저장합니다."""
    try:
        from agents.chatbot_agent.knowledge_processor import KnowledgeProcessor
        from config.settings import settings
        
        # KnowledgeProcessor 초기화
        processor = KnowledgeProcessor(
            openai_api_key=settings.OPENAI_API_KEY,
            ollama_base_url=settings.OLLAMA_BASE_URL,
            ollama_model=settings.OLLAMA_MODEL,
            milvus_host=settings.MILVUS_HOST,
            milvus_port=settings.MILVUS_PORT,
            milvus_collection=settings.MILVUS_COLLECTION,
            neo4j_uri=settings.NEO4J_URI,
            neo4j_username=settings.NEO4J_USERNAME,
            neo4j_password=settings.NEO4J_PASSWORD
        )
        
        # 지식 처리
        result = await processor.process_knowledge(
            content=request.get("content", ""),
            title=request.get("title", ""),
            source=request.get("source", ""),
            document_type=request.get("document_type", "text"),
            metadata=request.get("metadata", {})
        )
        
        return {
            "success": True,
            "result": {
                "document_id": result.document_id,
                "chunks_created": result.chunks_created,
                "vectors_created": result.vectors_created,
                "graph_nodes_created": result.graph_nodes_created,
                "processing_time": result.processing_time,
                "status": result.status
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"지식 처리 중 오류가 발생했습니다: {str(e)}")

@rag_router.get("/search")
async def search_knowledge(query: str, top_k: int = 5, search_type: str = "hybrid"):
    """지식베이스에서 관련 정보를 검색합니다."""
    try:
        from agents.chatbot_agent.rag_engine import RAGEngine
        from agents.chatbot_agent.embedder import Embedder
        from agents.chatbot_agent.vector_store import MilvusVectorStore
        from agents.chatbot_agent.graph_store import Neo4jGraphStore
        from config.settings import settings
        
        # RAG 엔진 초기화
        embedder = Embedder(
            model_name=settings.OPENAI_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            ollama_base_url=settings.OLLAMA_BASE_URL,
            ollama_model=settings.OLLAMA_MODEL
        )
        
        vector_store = MilvusVectorStore(
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
            collection_name=settings.MILVUS_COLLECTION,
            dimension=embedder.get_embedding_dimension()
        )
        
        graph_store = Neo4jGraphStore(
            uri=settings.NEO4J_URI,
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD
        )
        
        rag_engine = RAGEngine(
            vector_store=vector_store,
            graph_store=graph_store,
            embedder=embedder
        )
        
        # 검색 실행
        response = rag_engine.query(query, top_k=top_k, search_type=search_type)
        
        return {
            "success": True,
            "query": query,
            "answer": response.answer,
            "sources": [
                {
                    "text": source.text,
                    "score": source.score,
                    "source": source.source,
                    "metadata": source.metadata
                }
                for source in response.sources
            ],
            "search_type": search_type,
            "top_k": top_k
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")

# RAG 라우터를 메인 라우터에 포함
router.include_router(rag_router)

# 멀티모달 라우터 추가
from .multimodal_routes import router as multimodal_router
router.include_router(multimodal_router) 