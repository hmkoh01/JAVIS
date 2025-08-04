import httpx
from typing import Dict, Any
from ..base_tool import BaseTool, ToolResult
from config.settings import settings

class MCPFileTool(BaseTool):
    """MCP 기반 파일 처리 도구"""
    
    def __init__(self):
        super().__init__(
            name="mcp_file_tool",
            description="파일 읽기, 쓰기, 삭제 등의 파일 시스템 작업을 수행합니다."
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        try:
            action = kwargs.get("action")
            file_path = kwargs.get("file_path")
            content = kwargs.get("content", "")
            
            async with httpx.AsyncClient() as client:
                if action == "read":
                    response = await client.get(
                        f"{settings.MCP_SERVER_URL}/file/read",
                        params={"path": file_path}
                    )
                elif action == "write":
                    response = await client.post(
                        f"{settings.MCP_SERVER_URL}/file/write",
                        json={"path": file_path, "content": content}
                    )
                elif action == "delete":
                    response = await client.delete(
                        f"{settings.MCP_SERVER_URL}/file/delete",
                        params={"path": file_path}
                    )
                else:
                    return ToolResult(
                        success=False,
                        data=None,
                        error=f"지원하지 않는 액션: {action}"
                    )
                
                if response.status_code == 200:
                    return ToolResult(
                        success=True,
                        data=response.json(),
                        metadata={"action": action, "file_path": file_path}
                    )
                else:
                    return ToolResult(
                        success=False,
                        data=None,
                        error=f"MCP 서버 오류: {response.status_code}"
                    )
                    
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"파일 도구 실행 오류: {str(e)}"
            )
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "delete"],
                    "description": "수행할 파일 작업"
                },
                "file_path": {
                    "type": "string",
                    "description": "파일 경로"
                },
                "content": {
                    "type": "string",
                    "description": "파일에 쓸 내용 (write 액션에서만 사용)"
                }
            },
            "required": ["action", "file_path"]
        } 