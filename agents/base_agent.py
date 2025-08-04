from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from tools.base_tool import BaseTool, ToolResult
from core.tool_registry import tool_registry

class AgentState(BaseModel):
    """에이전트 상태를 나타내는 모델"""
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    context: Dict[str, Any] = {}
    history: List[Dict[str, Any]] = []

class AgentResponse(BaseModel):
    """에이전트 응답을 나타내는 모델"""
    success: bool
    content: Any
    agent_type: str
    tools_used: List[str] = []
    metadata: Dict[str, Any] = {}

class BaseAgent(ABC):
    """모든 에이전트의 기본 클래스"""
    
    def __init__(self, agent_type: str, description: str):
        self.agent_type = agent_type
        self.description = description
        self.tools: List[BaseTool] = []
        self.state = AgentState()
    
    @abstractmethod
    async def process(self, user_input: str, user_id: Optional[int] = None) -> AgentResponse:
        """사용자 입력을 처리합니다."""
        pass
    
    def add_tool(self, tool: BaseTool):
        """에이전트에 도구를 추가합니다."""
        self.tools.append(tool)
    
    def remove_tool(self, tool_name: str):
        """에이전트에서 도구를 제거합니다."""
        self.tools = [tool for tool in self.tools if tool.name != tool_name]
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """도구를 실행합니다."""
        # 먼저 에이전트의 도구에서 찾기
        for tool in self.tools:
            if tool.name == tool_name:
                return await tool.execute(**kwargs)
        
        # 전역 레지스트리에서 찾기
        tool = tool_registry.get_tool(tool_name)
        if tool:
            return await tool.execute(**kwargs)
        
        return ToolResult(
            success=False,
            data=None,
            error=f"도구를 찾을 수 없습니다: {tool_name}"
        )
    
    def update_state(self, **kwargs):
        """에이전트 상태를 업데이트합니다."""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
            else:
                self.state.context[key] = value
    
    def get_state(self) -> AgentState:
        """현재 에이전트 상태를 반환합니다."""
        return self.state 