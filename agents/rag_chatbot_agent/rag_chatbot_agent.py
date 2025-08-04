from typing import List, Dict, Any, Optional
from langchain.chat_models import ChatOpenAI
from langchain_ollama import ChatOllama
from ..base_agent import BaseAgent, AgentResponse
from rag.rag_engine import RAGEngine
from rag.embedder import Embedder
from rag.vector_store import MilvusVectorStore
from rag.graph_store import Neo4jGraphStore
from config.settings import settings

class RAGChatbotAgent(BaseAgent):
    """RAG 기반 챗봇 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_type="rag_chatbot",
            description="RAG 기반으로 지식베이스에서 관련 정보를 검색하여 답변을 생성합니다."
        )
        self.rag_engine = None
        self.llm = None
        self._initialize_components()
    
    def _initialize_components(self):
        """RAG 엔진과 LLM을 초기화합니다."""
        try:
            # LLM 초기화
            if settings.OPENAI_API_KEY:
                self.llm = ChatOpenAI(
                    openai_api_key=settings.OPENAI_API_KEY,
                    model_name="gpt-3.5-turbo",
                    temperature=0.7
                )
            else:
                # Ollama 사용
                self.llm = ChatOllama(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_MODEL
                )
            
            # 임베딩 모델 초기화
            embedder = Embedder(
                openai_api_key=settings.OPENAI_API_KEY,
                ollama_base_url=settings.OLLAMA_BASE_URL,
                ollama_model=settings.OLLAMA_MODEL
            )
            
            # 벡터 스토어 초기화
            vector_store = MilvusVectorStore(
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
                collection_name=settings.MILVUS_COLLECTION,
                dimension=embedder.get_embedding_dimension()
            )
            
            # 그래프 스토어 초기화
            graph_store = Neo4jGraphStore(
                uri=settings.NEO4J_URI,
                username=settings.NEO4J_USERNAME,
                password=settings.NEO4J_PASSWORD
            )
            
            # RAG 엔진 초기화
            self.rag_engine = RAGEngine(
                vector_store=vector_store,
                graph_store=graph_store,
                embedder=embedder,
                llm_model=self.llm
            )
            
        except Exception as e:
            print(f"RAG 에이전트 초기화 오류: {e}")
    
    async def _update_knowledge_base(self):
        """지식베이스를 업데이트합니다."""
        # 새로운 RAG 시스템에서는 실시간으로 처리되므로 별도 업데이트가 필요 없음
        pass
    
    async def process(self, user_input: str, user_id: Optional[int] = None) -> AgentResponse:
        """사용자 입력을 처리합니다."""
        try:
            if not self.rag_engine:
                return AgentResponse(
                    success=False,
                    content="RAG 엔진이 초기화되지 않았습니다.",
                    agent_type=self.agent_type
                )
            
            # RAG 엔진을 사용하여 쿼리 처리
            rag_response = self.rag_engine.query(user_input, top_k=5, search_type="hybrid")
            
            # 사용자 상호작용 기록
            if user_id:
                self._log_interaction(user_id, user_input, rag_response.answer)
            
            return AgentResponse(
                success=True,
                content=rag_response.answer,
                agent_type=self.agent_type,
                metadata={
                    "sources": [{"source": s.source, "score": s.score} for s in rag_response.sources],
                    "context_length": len(rag_response.context),
                    "search_type": rag_response.metadata.get("search_type", "hybrid"),
                    "results_count": rag_response.metadata.get("results_count", 0)
                }
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"처리 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    def _log_interaction(self, user_id: int, query: str, response: str):
        """사용자 상호작용을 기록합니다."""
        try:
            # 새로운 RAG 시스템에서는 상호작용 로깅을 별도로 처리
            # 여기서는 간단히 콘솔에 출력
            print(f"사용자 {user_id} 상호작용 기록: {query[:50]}... -> {response[:50]}...")
        except Exception as e:
            print(f"상호작용 기록 오류: {e}") 