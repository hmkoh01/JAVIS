import subprocess
import tempfile
import os
from typing import Optional
from ..base_agent import BaseAgent, AgentResponse
from tools.mcp_tools.file_tool import MCPFileTool
from database.connection import get_db_session
from database.models import UserInteraction

class CodingAgent(BaseAgent):
    """코딩 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_type="coding",
            description="코드 생성, 분석, 실행을 담당하는 에이전트"
        )
        self.file_tool = MCPFileTool()
        self.add_tool(self.file_tool)
    
    async def process(self, user_input: str, user_id: Optional[int] = None) -> AgentResponse:
        """사용자 입력을 처리합니다."""
        try:
            # 입력 분석
            intent = self._analyze_intent(user_input)
            
            if intent == "code_generation":
                return await self._generate_code(user_input, user_id)
            elif intent == "code_analysis":
                return await self._analyze_code(user_input, user_id)
            elif intent == "code_execution":
                return await self._execute_code(user_input, user_id)
            else:
                return AgentResponse(
                    success=False,
                    content="코딩 관련 요청을 이해할 수 없습니다. 코드 생성, 분석, 실행 중 어떤 것을 원하시나요?",
                    agent_type=self.agent_type
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"코딩 에이전트 처리 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    def _analyze_intent(self, user_input: str) -> str:
        """사용자 의도를 분석합니다."""
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ["생성", "만들", "작성", "generate", "create", "write"]):
            return "code_generation"
        elif any(word in input_lower for word in ["분석", "검토", "리뷰", "analyze", "review", "check"]):
            return "code_analysis"
        elif any(word in input_lower for word in ["실행", "런", "run", "execute", "test"]):
            return "code_execution"
        else:
            return "unknown"
    
    async def _generate_code(self, user_input: str, user_id: Optional[int]) -> AgentResponse:
        """코드를 생성합니다."""
        try:
            # LLM을 사용한 코드 생성 (실제 구현에서는 더 정교한 프롬프트 필요)
            prompt = f"""
            다음 요청에 따라 코드를 생성해주세요:
            {user_input}
            
            코드는 실행 가능하고 깔끔해야 합니다.
            """
            
            # 임시 파일에 코드 저장
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                temp_file_path = f.name
                # 실제로는 LLM 호출로 코드 생성
                sample_code = f"""
# Generated code for: {user_input}
def main():
    print("Hello, World!")
    # TODO: Implement the requested functionality
    
if __name__ == "__main__":
    main()
"""
                f.write(sample_code)
            
            # 파일 도구를 사용하여 코드 저장
            result = await self.execute_tool(
                "mcp_file_tool",
                action="write",
                file_path=f"generated_code_{user_id}.py",
                content=sample_code
            )
            
            if result.success:
                return AgentResponse(
                    success=True,
                    content=f"코드가 성공적으로 생성되었습니다.\n\n```python\n{sample_code}\n```",
                    agent_type=self.agent_type,
                    tools_used=["mcp_file_tool"],
                    metadata={"file_path": f"generated_code_{user_id}.py"}
                )
            else:
                return AgentResponse(
                    success=False,
                    content=f"코드 생성 중 오류가 발생했습니다: {result.error}",
                    agent_type=self.agent_type
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"코드 생성 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def _analyze_code(self, user_input: str, user_id: Optional[int]) -> AgentResponse:
        """코드를 분석합니다."""
        try:
            # 파일에서 코드 읽기
            result = await self.execute_tool(
                "mcp_file_tool",
                action="read",
                file_path=user_input
            )
            
            if result.success:
                code_content = result.data.get("content", "")
                
                # 코드 분석 (실제로는 더 정교한 분석 필요)
                analysis = self._perform_code_analysis(code_content)
                
                return AgentResponse(
                    success=True,
                    content=f"코드 분석 결과:\n\n{analysis}",
                    agent_type=self.agent_type,
                    tools_used=["mcp_file_tool"]
                )
            else:
                return AgentResponse(
                    success=False,
                    content=f"코드 파일을 읽을 수 없습니다: {result.error}",
                    agent_type=self.agent_type
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"코드 분석 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def _execute_code(self, user_input: str, user_id: Optional[int]) -> AgentResponse:
        """코드를 실행합니다."""
        try:
            # 파일에서 코드 읽기
            result = await self.execute_tool(
                "mcp_file_tool",
                action="read",
                file_path=user_input
            )
            
            if result.success:
                code_content = result.data.get("content", "")
                
                # 임시 파일에 코드 저장하고 실행
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(code_content)
                    temp_file_path = f.name
                
                try:
                    # 코드 실행
                    result = subprocess.run(
                        ["python", temp_file_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    output = result.stdout
                    error = result.stderr
                    
                    # 임시 파일 삭제
                    os.unlink(temp_file_path)
                    
                    if result.returncode == 0:
                        return AgentResponse(
                            success=True,
                            content=f"코드 실행 결과:\n\n{output}",
                            agent_type=self.agent_type,
                            tools_used=["mcp_file_tool"]
                        )
                    else:
                        return AgentResponse(
                            success=False,
                            content=f"코드 실행 중 오류가 발생했습니다:\n\n{error}",
                            agent_type=self.agent_type,
                            tools_used=["mcp_file_tool"]
                        )
                        
                except subprocess.TimeoutExpired:
                    return AgentResponse(
                        success=False,
                        content="코드 실행 시간이 초과되었습니다.",
                        agent_type=self.agent_type
                    )
                    
            else:
                return AgentResponse(
                    success=False,
                    content=f"코드 파일을 읽을 수 없습니다: {result.error}",
                    agent_type=self.agent_type
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"코드 실행 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    def _perform_code_analysis(self, code_content: str) -> str:
        """코드 분석을 수행합니다."""
        lines = code_content.split('\n')
        analysis = []
        
        analysis.append(f"총 라인 수: {len(lines)}")
        analysis.append(f"빈 라인 수: {len([line for line in lines if line.strip() == ''])}")
        analysis.append(f"주석 라인 수: {len([line for line in lines if line.strip().startswith('#')])}")
        
        # 함수 정의 찾기
        functions = [line for line in lines if line.strip().startswith('def ')]
        analysis.append(f"함수 정의 수: {len(functions)}")
        
        # 클래스 정의 찾기
        classes = [line for line in lines if line.strip().startswith('class ')]
        analysis.append(f"클래스 정의 수: {len(classes)}")
        
        return "\n".join(analysis) 