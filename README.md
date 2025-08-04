# JAVIS Multi-Agent System (LangGraph 기반)

LangGraph를 사용하여 구현된 다중 에이전트 시스템으로, 사용자 맞춤 AI 비서를 제공합니다.

## 🚀 주요 특징

- **LangGraph 기반**: StateGraph를 사용한 워크플로우 기반 아키텍처
- **다중 에이전트**: 4가지 전문 에이전트 (챗봇, 코딩, 대시보드, 추천)
- **RAG 시스템**: Milvus + Neo4j를 활용한 고급 검색 및 지식 관리
- **React Framework 도구**: 4가지 도구 (DB 검색, 인터넷 검색, 이메일, 외부 API)
- **모듈화 설계**: 에이전트와 도구의 쉬운 추가/제거

## 🏗️ 아키텍처

### LangGraph 워크플로우

```
User Input → Intent Analyzer → Agent Selector → Agent Executor → Response
```

1. **Intent Analyzer**: 사용자 의도를 LLM으로 분석
2. **Agent Selector**: 적절한 에이전트 선택
3. **Agent Executor**: 선택된 에이전트 실행

### 에이전트 구성

- **Chatbot Agent**: RAG 기반 챗봇 + 4가지 도구
- **Coding Agent**: 코드 생성 및 분석
- **Dashboard Agent**: 데이터 시각화 및 분석
- **Recommendation Agent**: 개인화된 추천

## 📦 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 설정을 추가하세요:

```env
# OpenAI 설정
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo

# Ollama 설정 (선택사항)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Milvus 설정
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=javis_knowledge

# Neo4j 설정
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# 이메일 설정 (선택사항)
EMAIL_FROM=your_email@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=your_email@example.com
EMAIL_PASSWORD=your_app_password
```

### 3. 데이터베이스 설정

#### Milvus 실행
```bash
# Docker로 Milvus 실행
docker run -d --name milvus_standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest standalone
```

#### Neo4j 실행
```bash
# Docker로 Neo4j 실행
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
```

### 4. 애플리케이션 실행

```bash
cd backend
python main.py
```

서버가 `http://localhost:8000`에서 실행됩니다.

## 🔧 API 사용법

### 1. 일반 요청 처리

```bash
curl -X POST "http://localhost:8000/api/v2/process" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "message": "파이썬으로 피보나치 수열을 계산하는 함수를 만들어줘",
    "context": {}
  }'
```

### 2. 특정 에이전트 사용

```bash
curl -X POST "http://localhost:8000/api/v2/agent/coding" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "message": "파이썬으로 피보나치 수열을 계산하는 함수를 만들어줘"
  }'
```

### 3. RAG 지식 처리

```bash
curl -X POST "http://localhost:8000/api/v2/rag/process" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "LangGraph는 LangChain에서 제공하는 그래프 기반 워크플로우 라이브러리입니다.",
    "title": "LangGraph 소개",
    "source": "documentation",
    "document_type": "text",
    "metadata": {"category": "framework", "tags": ["langgraph", "workflow"]}
  }'
```

### 4. RAG 검색

```bash
curl "http://localhost:8000/api/v2/rag/search?query=LangGraph란 무엇인가요&top_k=5&search_type=hybrid"
```

### 5. 시스템 상태 확인

```bash
curl "http://localhost:8000/api/v2/health"
```

## 🛠️ 도구 시스템

### Chatbot Agent의 4가지 도구

1. **Database Search Tool**: Milvus + Neo4j 기반 지식 검색
2. **Internet Search Tool**: 실시간 웹 검색
3. **Email Tool**: 이메일 전송 및 읽기
4. **External API Tool**: 외부 API 호출

### 도구 사용 예시

```bash
# 특정 도구 실행
curl -X POST "http://localhost:8000/api/v2/agents/chatbot/tools/database_search" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "message": "LangGraph에 대해 알려줘"
  }'
```

## 📊 LangGraph vs 기존 구현

| 구분 | 기존 구현 | LangGraph 기반 |
|------|-----------|----------------|
| **구조** | 객체지향 클래스 | 그래프 워크플로우 |
| **상태 관리** | 개별 객체 | 중앙화된 상태 |
| **에이전트 간 통신** | 직접 호출 | 메시지 기반 |
| **병렬 처리** | 제한적 | 자연스러운 병렬 처리 |
| **디버깅** | 일반적 | 시각적 그래프 디버깅 |
| **확장성** | 중간 | 높음 |

## 🔍 디버깅 및 모니터링

### LangGraph 시각화

LangGraph는 워크플로우를 시각적으로 디버깅할 수 있는 기능을 제공합니다:

```python
# 그래프 시각화
from core.supervisor import supervisor
supervisor.graph.get_graph().draw_mermaid()
```

### 로그 확인

```bash
# 애플리케이션 로그 확인
tail -f logs/app.log
```

## 🚀 확장 가이드

### 새로운 에이전트 추가

1. `agents/` 폴더에 새 에이전트 클래스 생성
2. `BaseAgent` 상속
3. `AgentRegistry`에 등록

```python
from agents.base_agent import BaseAgent, AgentResponse

class NewAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_type="new_agent",
            description="새로운 에이전트 설명"
        )
    
    async def process(self, user_input: str, user_id: Optional[int] = None) -> AgentResponse:
        # 에이전트 로직 구현
        pass
```

### 새로운 도구 추가

1. `agents/chatbot_agent/tools.py`에 새 도구 클래스 생성
2. `BaseTool` 상속
3. `ToolManager`에 등록

```python
from .tools import BaseTool, ToolResult

class NewTool(BaseTool):
    def __init__(self):
        super().__init__("new_tool", "새로운 도구 설명")
    
    async def execute(self, **kwargs) -> ToolResult:
        # 도구 로직 구현
        pass
```

## 📝 라이선스

MIT License

## 🤝 기여

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 지원

문제가 있거나 질문이 있으시면 이슈를 생성해주세요. 