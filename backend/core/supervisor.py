from typing import Dict, Any, Optional, List, Annotated, Sequence, TypedDict
from pydantic import BaseModel
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from config.settings import settings
from core.agent_registry import agent_registry
from agents.base_agent import AgentResponse

class UserIntent(BaseModel):
    """사용자 의도를 나타내는 모델"""
    user_id: Optional[int] = None
    message: str
    context: Dict[str, Any] = {}

class SupervisorResponse(BaseModel):
    """Supervisor 응답을 나타내는 모델"""
    success: bool
    selected_agent: str
    response: AgentResponse
    reasoning: str
    metadata: Dict[str, Any] = {}

class AgentState(TypedDict):
    """LangGraph 상태 정의"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_input: str
    user_id: Optional[int]
    user_context: Dict[str, Any]
    selected_agent: str
    reasoning: str
    agent_response: str
    agent_success: bool
    agent_type: str
    agent_metadata: Dict[str, Any]
    available_agents: List[str]

class LangGraphSupervisor:
    """LangGraph 기반 Supervisor - 사용자 의도를 분석하고 적절한 에이전트를 선택하는 그래프 워크플로우"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.agent_descriptions = agent_registry.get_agent_descriptions()
        self.graph = self._create_agent_graph()
    
    def _initialize_llm(self):
        """LLM을 초기화합니다."""
        try:
            if settings.OPENAI_API_KEY:
                return ChatOpenAI(
                    openai_api_key=settings.OPENAI_API_KEY,
                    model_name="gpt-3.5-turbo",
                    temperature=0.1
                )
            else:
                return ChatOllama(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_MODEL
                )
        except Exception as e:
            print(f"LLM 초기화 오류: {e}")
            return None
    
    def _create_agent_graph(self) -> StateGraph:
        """에이전트 선택 및 실행 그래프를 생성합니다."""
        workflow = StateGraph(AgentState)
        
        # 노드 추가
        workflow.add_node("intent_analyzer", self._intent_analyzer_node)
        workflow.add_node("agent_selector", self._agent_selector_node)
        workflow.add_node("agent_executor", self._agent_executor_node)
        
        # 엣지 연결
        workflow.add_edge("intent_analyzer", "agent_selector")
        workflow.add_edge("agent_selector", "agent_executor")
        workflow.add_edge("agent_executor", END)
        
        return workflow.compile()
    
    def visualize_graph(self) -> str:
        """LangGraph 워크플로우를 시각화합니다."""
        try:
            return self.graph.get_graph().draw_mermaid()
        except Exception as e:
            return f"그래프 시각화 중 오류: {str(e)}"
    
    def get_graph_info(self) -> Dict[str, Any]:
        """그래프 정보를 반환합니다."""
        try:
            graph = self.graph.get_graph()
            return {
                "nodes": list(graph.nodes.keys()),
                "edges": [(edge.source, edge.target) for edge in graph.edges],
                "total_nodes": len(graph.nodes),
                "total_edges": len(graph.edges),
                "framework": "LangGraph"
            }
        except Exception as e:
            return {"error": f"그래프 정보 조회 중 오류: {str(e)}"}
    
    async def _intent_analyzer_node(self, state: AgentState) -> AgentState:
        """사용자 의도를 분석하는 노드"""
        try:
            user_input = state["user_input"]
            
            if self.llm:
                # LLM을 사용한 의도 분석
                prompt = self._create_intent_analysis_prompt(user_input)
                messages = [
                    SystemMessage(content=prompt),
                    HumanMessage(content=user_input)
                ]
                
                response = await self.llm.agenerate([messages])
                reasoning = response.generations[0][0].text
            else:
                # 규칙 기반 의도 분석 (fallback)
                reasoning = "LLM을 사용할 수 없어 규칙 기반 분석을 수행합니다."
            
            new_state = state.copy()
            new_state["reasoning"] = reasoning
            return new_state
            
        except Exception as e:
            new_state = state.copy()
            new_state["reasoning"] = f"의도 분석 중 오류: {str(e)}"
            return new_state
    
    async def _agent_selector_node(self, state: AgentState) -> AgentState:
        """적절한 에이전트를 선택하는 노드"""
        try:
            user_input = state["user_input"]
            reasoning = state["reasoning"]
            
            # 에이전트 선택 로직
            selected_agent = self._select_agent(user_input, reasoning)
            
            new_state = state.copy()
            new_state["selected_agent"] = selected_agent
            new_state["available_agents"] = list(self.agent_descriptions.keys())
            return new_state
            
        except Exception as e:
            new_state = state.copy()
            new_state["selected_agent"] = "chatbot"  # 기본값
            new_state["reasoning"] += f" 에이전트 선택 중 오류: {str(e)}"
            return new_state
    
    async def _agent_executor_node(self, state: AgentState) -> AgentState:
        """선택된 에이전트를 실행하는 노드"""
        try:
            selected_agent = state["selected_agent"]
            user_input = state["user_input"]
            user_id = state["user_id"]
            
            # 에이전트 노드 가져오기
            agent_node = agent_registry.get_agent_node(selected_agent)
            
            if agent_node:
                # 에이전트 실행
                result_state = await agent_node(state)
                return result_state
            else:
                # 에이전트를 찾을 수 없는 경우
                new_state = state.copy()
                new_state["agent_response"] = f"에이전트를 찾을 수 없습니다: {selected_agent}"
                new_state["agent_success"] = False
                new_state["agent_type"] = selected_agent
                return new_state
                
        except Exception as e:
            new_state = state.copy()
            new_state["agent_response"] = f"에이전트 실행 중 오류: {str(e)}"
            new_state["agent_success"] = False
            new_state["agent_type"] = state.get("selected_agent", "unknown")
            return new_state
    
    def _select_agent(self, user_input: str, reasoning: str) -> str:
        """사용자 입력과 분석 결과를 기반으로 적절한 에이전트를 선택합니다."""
        input_lower = user_input.lower()
        
        # 키워드 기반 에이전트 선택
        if any(keyword in input_lower for keyword in ["코드", "프로그램", "개발", "함수", "클래스", "버그", "디버그"]):
            return "coding"
        elif any(keyword in input_lower for keyword in ["대시보드", "차트", "그래프", "분석", "통계", "시각화"]):
            return "dashboard"
        elif any(keyword in input_lower for keyword in ["추천", "추천해", "추천해줘", "추천해주세요"]):
            return "recommendation"
        else:
            return "chatbot"  # 기본값
    
    def _create_intent_analysis_prompt(self, user_message: str) -> str:
        """의도 분석을 위한 프롬프트를 생성합니다."""
        agent_descriptions = "\n".join([
            f"- {agent_type}: {description}"
            for agent_type, description in self.agent_descriptions.items()
        ])
        
        return f"""
당신은 사용자의 의도를 분석하여 적절한 AI 에이전트를 선택하는 전문가입니다.

사용 가능한 에이전트들:
{agent_descriptions}

사용자의 메시지를 분석하여 어떤 에이전트가 가장 적합한지 판단하고, 그 이유를 설명해주세요.

분석 결과는 다음과 같은 형식으로 제공해주세요:
- 주요 키워드: [사용자 메시지에서 추출한 주요 키워드들]
- 의도 분석: [사용자가 원하는 것이 무엇인지 분석]
- 추천 에이전트: [가장 적합한 에이전트명]
- 선택 이유: [왜 해당 에이전트를 선택했는지 설명]

사용자 메시지: {user_message}
"""
    
    async def process_user_intent(self, user_intent: UserIntent) -> SupervisorResponse:
        """사용자 의도를 처리하고 적절한 에이전트를 선택합니다 (LangGraph 기반)."""
        try:
            # 초기 상태 설정
            initial_state = {
                "messages": [],
                "user_input": user_intent.message,
                "user_id": user_intent.user_id,
                "user_context": user_intent.context,
                "selected_agent": "",
                "reasoning": "",
                "agent_response": "",
                "agent_success": False,
                "agent_type": "",
                "agent_metadata": {},
                "available_agents": []
            }
            
            # 그래프 실행
            result = await self.graph.ainvoke(initial_state)
            
            # 결과를 SupervisorResponse로 변환
            return SupervisorResponse(
                success=result["agent_success"],
                selected_agent=result["selected_agent"],
                response=AgentResponse(
                    success=result["agent_success"],
                    content=result["agent_response"],
                    agent_type=result["agent_type"],
                    metadata=result["agent_metadata"]
                ),
                reasoning=result["reasoning"],
                metadata={
                    "available_agents": result["available_agents"],
                    "user_context": user_intent.context,
                    "graph_execution": True
                }
            )
            
        except Exception as e:
            return SupervisorResponse(
                success=False,
                selected_agent="unknown",
                response=AgentResponse(
                    success=False,
                    content=f"LangGraph 처리 중 오류가 발생했습니다: {str(e)}",
                    agent_type="unknown"
                ),
                reasoning="그래프 실행 중 오류가 발생했습니다.",
                metadata={"error": str(e), "graph_execution": True}
            )
    
    def get_available_agents(self) -> Dict[str, str]:
        """사용 가능한 에이전트 목록을 반환합니다."""
        return self.agent_descriptions
    
    def add_agent(self, agent_type: str, agent: BaseAgent):
        """새로운 에이전트를 추가합니다."""
        agent_registry.register_agent(agent)
        self.agent_descriptions = agent_registry.get_agent_descriptions()
    
    def remove_agent(self, agent_type: str):
        """에이전트를 제거합니다."""
        agent_registry.unregister_agent(agent_type)
        self.agent_descriptions = agent_registry.get_agent_descriptions()

# 전역 Supervisor 인스턴스 (LangGraph 기반)
supervisor = LangGraphSupervisor() 