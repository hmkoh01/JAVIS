from typing import List, Dict, Any, Optional
from datetime import datetime
from ..base_agent import BaseAgent, AgentResponse
from .rag_engine import RAGEngine
from .embedder import Embedder
from .vector_store import MilvusVectorStore
from .graph_store import Neo4jGraphStore
from .tools import ToolManager, ToolResult
from config.settings import settings

class ChatbotAgent(BaseAgent):
    """RAG 기반 챗봇 에이전트 with React Framework Tools"""
    
    def __init__(self):
        super().__init__(
            agent_type="chatbot",
            description="RAG 기반으로 지식베이스에서 관련 정보를 검색하고 다양한 도구를 사용하여 답변을 생성합니다."
        )
        self.rag_engine = None
        self.tool_manager = None
        self._initialize_components()
    
    def _initialize_components(self):
        """RAG 엔진과 도구들을 초기화합니다."""
        try:
            # 임베딩 모델 초기화
            embedder = Embedder(
                model_name=settings.OPENAI_MODEL,
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
                embedder=embedder
            )
            
            # 도구 관리자 초기화
            self.tool_manager = ToolManager(self.rag_engine)
            
        except Exception as e:
            print(f"챗봇 에이전트 초기화 오류: {e}")
    
    async def process(self, user_input: str, user_id: Optional[int] = None) -> AgentResponse:
        """사용자 입력을 처리합니다."""
        try:
            # 1. 적절한 도구 선택
            selected_tool = self.tool_manager.select_best_tool(user_input)
            
            # 2. 도구 실행
            tool_result = await self._execute_tool(selected_tool, user_input)
            
            # 3. 결과 처리 및 응답 생성
            if tool_result.success:
                response_content = self._format_tool_response(tool_result, user_input)
                
                return AgentResponse(
                    success=True,
                    content=response_content,
                    agent_type=self.agent_type,
                    metadata={
                        "tool_used": selected_tool,
                        "tool_result": tool_result.metadata,
                        "user_id": user_id
                    }
                )
            else:
                # 도구 실행 실패 시 기본 RAG 검색 시도
                return await self._fallback_rag_search(user_input, user_id)
                
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"처리 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def _execute_tool(self, tool_name: str, user_input: str) -> ToolResult:
        """도구를 실행합니다."""
        try:
            if tool_name == "database_search":
                return await self.tool_manager.execute_tool(
                    tool_name, 
                    query=user_input,
                    search_type="hybrid",
                    top_k=5
                )
            
            elif tool_name == "internet_search":
                return await self.tool_manager.execute_tool(
                    tool_name,
                    query=user_input,
                    max_results=5
                )
            
            elif tool_name == "email":
                # 이메일 도구는 특별한 처리가 필요
                return await self._handle_email_tool(user_input)
            
            elif tool_name == "external_api":
                # 외부 API 도구는 특별한 처리가 필요
                return await self._handle_external_api_tool(user_input)
            
            else:
                return ToolResult(
                    success=False,
                    content=f"지원하지 않는 도구입니다: {tool_name}",
                    tool_name=tool_name,
                    metadata={"error": "Unsupported tool"},
                    timestamp=datetime.utcnow()
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content=f"도구 실행 중 오류가 발생했습니다: {str(e)}",
                tool_name=tool_name,
                metadata={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def _handle_email_tool(self, user_input: str) -> ToolResult:
        """이메일 도구를 처리합니다."""
        # 간단한 키워드 기반 이메일 작업 감지
        input_lower = user_input.lower()
        
        if any(keyword in input_lower for keyword in ["보내", "전송", "send"]):
            # 이메일 전송 모드
            # 실제 구현에서는 더 정교한 파싱이 필요
            return await self.tool_manager.execute_tool(
                "email",
                action="send",
                to_email="example@example.com",  # 실제로는 파싱 필요
                subject="JAVIS AI Assistant",
                body="이메일 내용"
            )
        else:
            # 이메일 읽기 모드
            return await self.tool_manager.execute_tool(
                "email",
                action="read",
                max_emails=5
            )
    
    async def _handle_external_api_tool(self, user_input: str) -> ToolResult:
        """외부 API 도구를 처리합니다."""
        # 간단한 예시 - 실제로는 더 정교한 파싱이 필요
        if "weather" in user_input.lower() or "날씨" in user_input:
            # 날씨 API 호출 예시
            return await self.tool_manager.execute_tool(
                "external_api",
                api_url="https://api.openweathermap.org/data/2.5/weather",
                method="GET",
                params={
                    "q": "Seoul",
                    "appid": "your_api_key",  # 실제로는 설정에서 가져와야 함
                    "units": "metric"
                }
            )
        else:
            # 기본 API 호출
            return await self.tool_manager.execute_tool(
                "external_api",
                api_url="https://httpbin.org/get",
                method="GET"
            )
    
    async def _fallback_rag_search(self, user_input: str, user_id: Optional[int]) -> AgentResponse:
        """도구 실행 실패 시 RAG 검색을 시도합니다."""
        try:
            rag_response = self.rag_engine.query(user_input, top_k=3, search_type="hybrid")
            
            if rag_response.sources:
                response_content = f"검색 결과:\n\n{rag_response.answer}"
            else:
                response_content = "죄송합니다. 관련 정보를 찾을 수 없습니다."
            
            return AgentResponse(
                success=True,
                content=response_content,
                agent_type=self.agent_type,
                metadata={
                    "tool_used": "rag_fallback",
                    "sources_count": len(rag_response.sources),
                    "user_id": user_id
                }
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"검색 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    def _format_tool_response(self, tool_result: ToolResult, user_input: str) -> str:
        """도구 결과를 사용자 친화적으로 포맷합니다."""
        if tool_result.tool_name == "database_search":
            return f"지식베이스에서 찾은 정보:\n\n{tool_result.content}"
        
        elif tool_result.tool_name == "internet_search":
            return f"인터넷에서 찾은 최신 정보:\n\n{tool_result.content}"
        
        elif tool_result.tool_name == "email":
            return f"이메일 작업 결과:\n\n{tool_result.content}"
        
        elif tool_result.tool_name == "external_api":
            return f"외부 API 호출 결과:\n\n{tool_result.content}"
        
        else:
            return tool_result.content
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """사용 가능한 도구 목록을 반환합니다."""
        if self.tool_manager:
            return self.tool_manager.get_available_tools()
        return []
    
    async def process_with_specific_tool(self, user_input: str, tool_name: str, 
                                       **tool_params) -> AgentResponse:
        """특정 도구를 사용하여 처리합니다."""
        try:
            tool_result = await self.tool_manager.execute_tool(tool_name, **tool_params)
            
            if tool_result.success:
                response_content = self._format_tool_response(tool_result, user_input)
                
                return AgentResponse(
                    success=True,
                    content=response_content,
                    agent_type=self.agent_type,
                    metadata={
                        "tool_used": tool_name,
                        "tool_result": tool_result.metadata
                    }
                )
            else:
                return AgentResponse(
                    success=False,
                    content=tool_result.content,
                    agent_type=self.agent_type
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"도구 실행 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            ) 