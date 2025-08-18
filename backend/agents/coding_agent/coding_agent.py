import subprocess
import tempfile
import os
from typing import Optional
from ..base_agent import BaseAgent, AgentResponse

class CodingAgent(BaseAgent):
    """코딩 관련 작업을 처리하는 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_type="coding",
            description="코드 작성, 디버깅, 프로그래밍 관련 질문을 처리합니다."
        )
    
    async def process(self, user_input: str, user_id: Optional[int] = None) -> AgentResponse:
        """사용자 입력을 처리합니다."""
        try:
            # 간단한 코딩 관련 응답
            response_content = f"코딩 에이전트가 '{user_input}' 요청을 처리했습니다. 현재는 기본 응답만 제공합니다."
            
            return AgentResponse(
                success=True,
                content=response_content,
                agent_type=self.agent_type,
                metadata={
                    "query": user_input,
                    "user_id": user_id,
                    "agent_type": "coding"
                }
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"코딩 에이전트 처리 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            ) 