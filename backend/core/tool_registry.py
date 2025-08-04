from typing import Dict, List, Type
from tools.base_tool import BaseTool
from tools.mcp_tools.file_tool import MCPFileTool
from tools.react_tools.web_search_tool import WebSearchTool

class ToolRegistry:
    """도구들을 등록하고 관리하는 레지스트리"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """기본 도구들을 등록합니다."""
        default_tools = [
            MCPFileTool(),
            WebSearchTool()
        ]
        
        for tool in default_tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: BaseTool):
        """새로운 도구를 등록합니다."""
        self._tools[tool.name] = tool
    
    def unregister_tool(self, tool_name: str):
        """도구를 등록 해제합니다."""
        if tool_name in self._tools:
            del self._tools[tool_name]
    
    def get_tool(self, tool_name: str) -> BaseTool:
        """도구를 가져옵니다."""
        return self._tools.get(tool_name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """모든 도구를 반환합니다."""
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """모든 도구 이름을 반환합니다."""
        return list(self._tools.keys())
    
    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """카테고리별로 도구를 반환합니다."""
        # 카테고리별 필터링 로직 구현
        return [tool for tool in self._tools.values() if hasattr(tool, 'category') and tool.category == category]

# 전역 도구 레지스트리 인스턴스
tool_registry = ToolRegistry() 