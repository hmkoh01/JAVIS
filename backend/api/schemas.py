from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class ChatRequest(BaseModel):
    """채팅 요청 스키마"""
    user_id: Optional[int] = None
    message: str
    context: Dict[str, Any] = {}

class ChatResponse(BaseModel):
    """채팅 응답 스키마"""
    success: bool
    message: str
    selected_agent: str
    reasoning: str
    metadata: Dict[str, Any] = {}

class AgentInfo(BaseModel):
    """에이전트 정보 스키마"""
    agent_type: str
    description: str

class ToolInfo(BaseModel):
    """도구 정보 스키마"""
    name: str
    description: str
    parameters: Dict[str, Any]

class SystemStatus(BaseModel):
    """시스템 상태 스키마"""
    status: str
    available_agents: List[AgentInfo]
    available_tools: List[ToolInfo]
    metadata: Dict[str, Any] = {}

class UserCreateRequest(BaseModel):
    """사용자 생성 요청 스키마"""
    username: str
    email: str
    preferences: Dict[str, Any] = {}

class UserResponse(BaseModel):
    """사용자 응답 스키마"""
    id: int
    username: str
    email: str
    preferences: Dict[str, Any]
    created_at: str
    updated_at: str

class KnowledgeBaseRequest(BaseModel):
    """지식베이스 요청 스키마"""
    title: str
    content: str
    category: str
    tags: List[str] = []

class KnowledgeBaseResponse(BaseModel):
    """지식베이스 응답 스키마"""
    id: int
    title: str
    content: str
    category: str
    tags: List[str]
    created_at: str
    updated_at: str 