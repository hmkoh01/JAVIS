from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from ..base_agent import BaseAgent
from .rag_engine import RAGEngine, SearchResult
from config.settings import settings

@dataclass
class ToolResult:
    """도구 실행 결과를 나타내는 데이터 클래스"""
    success: bool
    content: str
    tool_name: str
    metadata: Dict[str, Any]
    timestamp: datetime

class BaseTool:
    """도구의 기본 클래스"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    async def execute(self, **kwargs) -> ToolResult:
        """도구를 실행합니다."""
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")

class DatabaseSearchTool(BaseTool):
    """데이터베이스 검색 도구"""
    
    def __init__(self, rag_engine: RAGEngine):
        super().__init__(
            name="database_search",
            description="지식베이스에서 관련 정보를 검색합니다."
        )
        self.rag_engine = rag_engine
    
    async def execute(self, query: str, search_type: str = "vector", top_k: int = 5) -> ToolResult:
        """데이터베이스에서 검색을 수행합니다."""
        try:
            # RAG 엔진을 사용하여 검색
            rag_response = self.rag_engine.query(query, top_k=top_k, search_type=search_type)
            
            if rag_response.sources:
                sources_text = "\n\n".join([
                    f"출처: {source.source}\n내용: {source.text[:200]}..."
                    for source in rag_response.sources[:3]
                ])
                content = f"검색 결과:\n\n{rag_response.answer}\n\n참고 자료:\n{sources_text}"
            else:
                content = "관련 정보를 찾을 수 없습니다."
            
            return ToolResult(
                success=True,
                content=content,
                tool_name=self.name,
                metadata={
                    "query": query,
                    "search_type": search_type,
                    "results_count": len(rag_response.sources),
                    "sources": [{"source": s.source, "score": s.score} for s in rag_response.sources]
                },
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content=f"데이터베이스 검색 중 오류가 발생했습니다: {str(e)}",
                tool_name=self.name,
                metadata={"error": str(e)},
                timestamp=datetime.utcnow()
            )

class InternetSearchTool(BaseTool):
    """인터넷 검색 도구"""
    
    def __init__(self):
        super().__init__(
            name="internet_search",
            description="인터넷에서 실시간 정보를 검색합니다."
        )
    
    async def execute(self, query: str, max_results: int = 5) -> ToolResult:
        """인터넷에서 검색을 수행합니다."""
        try:
            # Google Custom Search API 또는 DuckDuckGo API 사용
            # 여기서는 DuckDuckGo Instant Answer API 사용 (무료)
            search_results = self._search_duckduckgo(query, max_results)
            
            if search_results:
                content = f"인터넷 검색 결과:\n\n"
                for i, result in enumerate(search_results[:max_results], 1):
                    content += f"{i}. {result['title']}\n"
                    content += f"   URL: {result['link']}\n"
                    content += f"   요약: {result['snippet'][:150]}...\n\n"
            else:
                content = "인터넷 검색 결과를 찾을 수 없습니다."
            
            return ToolResult(
                success=True,
                content=content,
                tool_name=self.name,
                metadata={
                    "query": query,
                    "results_count": len(search_results),
                    "search_engine": "DuckDuckGo"
                },
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content=f"인터넷 검색 중 오류가 발생했습니다: {str(e)}",
                tool_name=self.name,
                metadata={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """DuckDuckGo에서 검색을 수행합니다."""
        try:
            # DuckDuckGo Instant Answer API 사용
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Abstract 결과 추가
            if data.get("Abstract"):
                results.append({
                    "title": data["Abstract"],
                    "link": data.get("AbstractURL", ""),
                    "snippet": data.get("AbstractText", "")
                })
            
            # Related Topics 추가
            for topic in data.get("RelatedTopics", [])[:max_results-1]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({
                        "title": topic["Text"],
                        "link": topic.get("FirstURL", ""),
                        "snippet": topic["Text"][:150] + "..." if len(topic["Text"]) > 150 else topic["Text"]
                    })
            
            return results
            
        except Exception as e:
            print(f"DuckDuckGo 검색 오류: {e}")
            return []

class EmailTool(BaseTool):
    """이메일 도구"""
    
    def __init__(self):
        super().__init__(
            name="email",
            description="이메일을 보내거나 읽습니다."
        )
    
    async def execute(self, action: str, **kwargs) -> ToolResult:
        """이메일 작업을 수행합니다."""
        if action == "send":
            return await self._send_email(**kwargs)
        elif action == "read":
            return await self._read_emails(**kwargs)
        else:
            return ToolResult(
                success=False,
                content=f"지원하지 않는 이메일 작업입니다: {action}",
                tool_name=self.name,
                metadata={"error": "Unsupported action"},
                timestamp=datetime.utcnow()
            )
    
    async def _send_email(self, to_email: str, subject: str, body: str, 
                         from_email: str = None, smtp_server: str = None, 
                         smtp_port: int = None, username: str = None, 
                         password: str = None) -> ToolResult:
        """이메일을 보냅니다."""
        try:
            # 설정에서 이메일 정보 가져오기
            from_email = from_email or settings.EMAIL_FROM
            smtp_server = smtp_server or settings.SMTP_SERVER
            smtp_port = smtp_port or settings.SMTP_PORT
            username = username or settings.EMAIL_USERNAME
            password = password or settings.EMAIL_PASSWORD
            
            if not all([from_email, smtp_server, username, password]):
                return ToolResult(
                    success=False,
                    content="이메일 설정이 완료되지 않았습니다.",
                    tool_name=self.name,
                    metadata={"error": "Email configuration incomplete"},
                    timestamp=datetime.utcnow()
                )
            
            # 이메일 메시지 생성
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # SMTP 서버에 연결하여 이메일 전송
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            
            return ToolResult(
                success=True,
                content=f"이메일이 성공적으로 전송되었습니다.\n받는 사람: {to_email}\n제목: {subject}",
                tool_name=self.name,
                metadata={
                    "to_email": to_email,
                    "subject": subject,
                    "from_email": from_email
                },
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content=f"이메일 전송 중 오류가 발생했습니다: {str(e)}",
                tool_name=self.name,
                metadata={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def _read_emails(self, email_address: str = None, max_emails: int = 5) -> ToolResult:
        """이메일을 읽습니다."""
        try:
            # 실제 구현에서는 IMAP을 사용하여 이메일을 읽어야 함
            # 여기서는 간단한 예시만 제공
            content = "이메일 읽기 기능은 현재 구현 중입니다."
            
            return ToolResult(
                success=True,
                content=content,
                tool_name=self.name,
                metadata={
                    "email_address": email_address,
                    "max_emails": max_emails
                },
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content=f"이메일 읽기 중 오류가 발생했습니다: {str(e)}",
                tool_name=self.name,
                metadata={"error": str(e)},
                timestamp=datetime.utcnow()
            )

class ExternalAPITool(BaseTool):
    """외부 API 호출 도구"""
    
    def __init__(self):
        super().__init__(
            name="external_api",
            description="외부 API를 호출하여 정보를 검색하거나 작업을 수행합니다."
        )
    
    async def execute(self, api_url: str, method: str = "GET", 
                     headers: Dict[str, str] = None, 
                     data: Dict[str, Any] = None,
                     params: Dict[str, Any] = None) -> ToolResult:
        """외부 API를 호출합니다."""
        try:
            # 기본 헤더 설정
            default_headers = {
                "User-Agent": "JAVIS-AI-Assistant/1.0",
                "Content-Type": "application/json"
            }
            if headers:
                default_headers.update(headers)
            
            # API 호출
            if method.upper() == "GET":
                response = requests.get(
                    api_url, 
                    headers=default_headers, 
                    params=params,
                    timeout=30
                )
            elif method.upper() == "POST":
                response = requests.post(
                    api_url, 
                    headers=default_headers, 
                    json=data,
                    params=params,
                    timeout=30
                )
            else:
                return ToolResult(
                    success=False,
                    content=f"지원하지 않는 HTTP 메서드입니다: {method}",
                    tool_name=self.name,
                    metadata={"error": "Unsupported HTTP method"},
                    timestamp=datetime.utcnow()
                )
            
            response.raise_for_status()
            
            # 응답 처리
            try:
                response_data = response.json()
                content = f"API 호출 성공:\n\n응답 데이터:\n{json.dumps(response_data, indent=2, ensure_ascii=False)}"
            except:
                content = f"API 호출 성공:\n\n응답 내용:\n{response.text}"
            
            return ToolResult(
                success=True,
                content=content,
                tool_name=self.name,
                metadata={
                    "api_url": api_url,
                    "method": method,
                    "status_code": response.status_code,
                    "response_size": len(response.content)
                },
                timestamp=datetime.utcnow()
            )
            
        except requests.exceptions.RequestException as e:
            return ToolResult(
                success=False,
                content=f"API 호출 중 오류가 발생했습니다: {str(e)}",
                tool_name=self.name,
                metadata={"error": str(e)},
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content=f"예상치 못한 오류가 발생했습니다: {str(e)}",
                tool_name=self.name,
                metadata={"error": str(e)},
                timestamp=datetime.utcnow()
            )

class ToolManager:
    """도구 관리자"""
    
    def __init__(self, rag_engine: RAGEngine):
        self.tools = {
            "database_search": DatabaseSearchTool(rag_engine),
            "internet_search": InternetSearchTool(),
            "email": EmailTool(),
            "external_api": ExternalAPITool()
        }
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """사용 가능한 도구 목록을 반환합니다."""
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self.tools.values()
        ]
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """지정된 도구를 실행합니다."""
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                content=f"알 수 없는 도구입니다: {tool_name}",
                tool_name=tool_name,
                metadata={"error": "Unknown tool"},
                timestamp=datetime.utcnow()
            )
        
        return await self.tools[tool_name].execute(**kwargs)
    
    def select_best_tool(self, user_input: str) -> str:
        """사용자 입력에 가장 적합한 도구를 선택합니다."""
        input_lower = user_input.lower()
        
        # 키워드 기반 도구 선택
        if any(keyword in input_lower for keyword in ["검색", "찾아", "알려", "정보"]):
            if any(keyword in input_lower for keyword in ["인터넷", "웹", "실시간", "최신"]):
                return "internet_search"
            else:
                return "database_search"
        elif any(keyword in input_lower for keyword in ["이메일", "메일", "전송", "보내"]):
            return "email"
        elif any(keyword in input_lower for keyword in ["api", "외부", "호출", "요청"]):
            return "external_api"
        else:
            # 기본적으로 데이터베이스 검색 사용
            return "database_search" 