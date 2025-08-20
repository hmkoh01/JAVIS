from typing import List, Dict, Any, Optional
from datetime import datetime
from ..base_agent import BaseAgent, AgentResponse
from .rag.react_agent import process as react_process

class ChatbotAgent(BaseAgent):
    """멀티모달 RAG 챗봇 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_type="chatbot",
            description="멀티모달 RAG를 사용하여 사용자의 질문에 답변하는 챗봇 에이전트입니다."
        )
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """RAG 기반 처리 메서드"""
        try:
            question = state.get("question", "")
            user_id = state.get("user_id")
            
            if not question:
                return {
                    "answer": "질문이 제공되지 않았습니다.",
                    "success": False,
                    "agent_type": self.agent_type,
                    "metadata": {
                        "error": "Empty question",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            
            # react_agent의 process 함수 호출
            result = react_process(state)
            
            # 결과를 ChatbotAgent 형식에 맞게 변환
            return {
                "answer": result.get("answer", "답변을 생성할 수 없습니다."),
                "success": True,
                "agent_type": self.agent_type,
                "metadata": {
                    "query": question,
                    "user_id": user_id,
                    "agent_type": "chatbot",
                    "evidence": result.get("evidence", []),
                    "timestamp": datetime.now().isoformat()
                }
            }
                
        except Exception as e:
            return {
                "answer": f"챗봇 에이전트 처리 중 오류가 발생했습니다: {str(e)}",
                "success": False,
                "agent_type": self.agent_type,
                "metadata": {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }