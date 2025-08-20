# 🦜🕸️ JAVIS - LangGraph 기반 멀티 에이전트 시스템

JAVIS는 LangGraph를 기반으로 한 지능형 멀티 에이전트 시스템입니다. ColQwen2, Qdrant, Gemini API, Tavily Search를 활용한 멀티모달 RAG(Retrieval-Augmented Generation) 기능을 제공합니다.

## 🆕 로컬 멀티모달 RAG 시스템

### 주요 특징
- **ColQwen2 임베더**: 텍스트/이미지/스크린샷을 128D 공통 벡터 공간으로 임베딩
- **Qdrant 벡터 DB**: 멀티벡터 저장 및 ANN 검색
- **MonoVLM 재랭커**: MonoQwen2-VL-v0.1을 사용한 이미지 재랭킹
- **Qwen2-VL VLM**: 4bit 양자화된 비전 언어 모델
- **로컬 데이터 수집**: 파일/웹/앱/화면 활동 자동 수집

### RAG 파이프라인
```
[사용자 질문] → [ColQwen2 임베딩] → [Qdrant 검색] → [MonoVLM 재랭킹] → [Qwen2-VL 응답] → [최종 답변]
```

## 🚀 주요 기능

### 🤖 멀티 에이전트 시스템
- **LangGraph 기반 워크플로우**: 상태 기반 그래프 워크플로우로 에이전트 간 협업
- **지능형 에이전트 라우팅**: Gemini API를 사용한 사용자 의도 분석 및 적절한 에이전트 선택
- **플러그인 아키텍처**: 새로운 에이전트와 도구를 쉽게 추가 가능

### 🔍 멀티모달 RAG 시스템
- **ColQwen2**: 멀티모달 분석 및 이해
- **Milvus**: 벡터 데이터베이스를 통한 이미지 검색
- **Gemini API**: 최종 응답 생성 및 멀티모달 처리
- **Tavily Search**: 실시간 웹 검색 및 정보 수집

### 🖥️ 사용자 인터페이스
- **플로팅 채팅 앱**: 데스크톱 플로팅 버튼으로 언제든지 접근 가능
- **웹 기반 시각화**: LangGraph 워크플로우 실시간 시각화
- **멀티모달 지원**: 텍스트, 이미지, 웹 검색 결과 통합

### 📊 자동 데이터 수집 및 RAG 연동
- **파일 수집**: 1시간마다 사용자 파일 시스템 스캔 및 RAG 인덱싱
- **웹 히스토리**: 30분마다 브라우저 히스토리 수집 및 검색 가능
- **앱 활동**: 5분마다 활성 애플리케이션 정보 수집
- **화면 활동**: 1분마다 스크린샷 캡처 및 Gemini 분석 후 RAG 인덱싱

## 🏗️ 시스템 아키텍처

### LangGraph 워크플로우
```
[사용자 입력] 
    ↓
[의도 분석 노드] → Gemini API 기반 의도 분석
    ↓
[에이전트 선택 노드] → 적절한 에이전트 선택
    ↓
[에이전트 실행 노드] → 선택된 에이전트 실행
    ↓
[응답 반환]
```

### RAG 시스템 구조
```
database/
├── sqlite_meta.py      # SQLite 메타데이터 관리
├── qdrant_client.py    # Qdrant 벡터 DB 클라이언트
└── repository.py       # 통합 Repository API

chatbot_agent/rag/
├── models/
│   └── colqwen2_embedder.py  # ColQwen2 임베더
├── retrievers.py       # 검색 로직
├── rerankers.py        # 재랭킹 로직
├── answerer.py         # 응답 생성
└── react_agent.py      # ReAct 에이전트 엔트리
```

### 멀티모달 RAG 파이프라인
```
[사용자 질문]
    ↓
[ColQwen2 임베딩] → 질문을 128D 벡터로 변환
    ↓
[Qdrant 검색] → text/image/screen 컬렉션에서 ANN 검색
    ↓
[MonoVLM 재랭킹] → 이미지 후보 재랭킹 (선택적)
    ↓
[Qwen2-VL 분석] → 멀티모달 응답 생성 (선택적)
    ↓
[응답 생성] → 근거 기반 텍스트 응답
    ↓
[사용자에게 응답]
```

## 🛠️ 설치 및 설정

### 1. 저장소 클론
```bash
git clone <repository-url>
cd JAVIS_MAS
```

### 2. 가상환경 설정
```bash
python -m venv javis
source javis/bin/activate  # Linux/Mac
# 또는
javis\Scripts\activate  # Windows
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

#### RAG 시스템 의존성
```bash
# 핵심 의존성
pip install torch transformers numpy Pillow PyYAML

# 벡터 데이터베이스
pip install qdrant-client

# 임베딩 및 재랭킹
pip install byaldi rerankers[monovlm]

# VLM 의존성
pip install qwen-vl-utils bitsandbytes

# 데이터베이스
pip install psutil
```

### 4. 환경 변수 설정
`.env` 파일을 생성하고 다음 설정을 추가하세요:

```env
# API 설정
API_HOST=0.0.0.0
API_PORT=8000

# 데이터베이스 설정
DATABASE_URL=sqlite:///./javis.db

# Gemini API 설정 (필수)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash

# Tavily API 설정 (선택사항)
TAVILY_API_KEY=your_tavily_api_key

# Milvus 설정 (선택사항)
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=image_embeddings

# ColQwen2 설정 (선택사항)
COLQWEN2_BASE_URL=http://localhost:11434
COLQWEN2_MODEL=qwen2.5-72b-instruct

# 이미지 업로드 설정
IMAGE_UPLOAD_PATH=./uploads/images
MAX_IMAGE_SIZE_MB=10

# Qdrant 설정
QDRANT_URL=http://localhost:6333

# RAG 설정
EMBEDDING_DIM=128
RETRIEVAL_K_CANDIDATES=40
RETRIEVAL_K_FINAL=10
VLM_ENABLED=true
```

### 5. RAG 설정 파일 (configs.yaml)
프로젝트 루트에 `configs.yaml` 파일을 생성하세요:

```yaml
qdrant:
  url: "http://localhost:6333"
  collections:
    text: "text_chunks"
    image: "image_patches"
    screen: "screens_patches"
embedding:
  dim: 128
  batch_size: 32
sqlite:
  path: "./var/meta.db"
retrieval:
  k_candidates: 40
  k_final: 10
security:
  redact_patterns:
    - "(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}"
    - "\\b01[016789]-?\\d{3,4}-?\\d{4}\\b"
vlm:
  enabled: true
  model_name: "Qwen/Qwen2-VL-7B-Instruct"
  quantization: true
  max_new_tokens: 500
```

## 🚀 실행 방법

### 전체 시스템 시작
```bash
python start.py
```

### RAG 시스템 테스트
```bash
python test_rag.py
```

### Qdrant 서버 시작
```bash
# Docker로 Qdrant 실행
docker run -p 6333:6333 qdrant/qdrant

# 또는 바이너리 다운로드
wget https://github.com/qdrant/qdrant/releases/download/v1.7.0/qdrant-v1.7.0-x86_64-unknown-linux-gnu.tar.gz
tar -xzf qdrant-v1.7.0-x86_64-unknown-linux-gnu.tar.gz
./qdrant
```

### 개별 컴포넌트 시작

#### 백엔드 서버
```bash
cd backend
python main.py
```

#### 프론트엔드 (플로팅 채팅)
```bash
cd frontend
python front.py
```

## 📊 LangGraph 워크플로우 시각화

시스템이 실행된 후 다음 URL에서 LangGraph 워크플로우를 시각화할 수 있습니다:

```
http://localhost:8000/graph
```

이 페이지에서는:
- 실시간 워크플로우 다이어그램
- 등록된 에이전트 목록
- 시스템 상태 정보
- 노드 및 엣지 정보

를 확인할 수 있습니다.

## 🔧 API 엔드포인트

### 멀티모달 채팅
```bash
POST /api/v2/multimodal/chat
Content-Type: application/x-www-form-urlencoded

message=사용자 질문
user_id=1 (선택사항)
```

### LangGraph 워크플로우 정보
```bash
GET /api/v2/graph/info
GET /api/v2/graph/visualization
```

### 시스템 상태
```bash
GET /api/v2/health
```

### RAG 시스템 API
```bash
# 로컬 RAG 질문 처리
POST /api/v2/rag/query
Content-Type: application/json

{
  "question": "지난주 내가 가장 오래 본 웹페이지는?",
  "user_id": "user123",
  "filters": {},
  "time_hint": null
}
```

## 📊 자동 데이터 수집 시스템

### 개요
JAVIS는 사용자의 디지털 활동을 자동으로 수집하고 RAG 시스템에 실시간으로 인덱싱하는 통합 시스템을 제공합니다. 수집된 모든 데이터는 즉시 검색 가능한 지식베이스가 되어, 사용자가 "내가 어디에 뭘 썼더라?" 같은 질문에도 정확한 답변을 받을 수 있습니다.

### 수집 및 인덱싱 과정

#### 1. 파일 시스템 스캔 및 RAG 인덱싱
- **수집 주기**: 1시간마다
- **수집 범위**: 사용자 드라이브의 모든 파일
- **제외 디렉토리**: Windows, Program Files, 시스템 폴더 등
- **RAG 인덱싱**: 
  - 텍스트 파일: 내용 추출 → 청킹 → ColQwen2 벡터화 → Qdrant 저장
  - 이미지 파일: PIL 로드 → 패치 분할 → ColQwen2 벡터화 → Qdrant 저장
  - 문서 파일: PyPDF2/python-docx로 텍스트 추출 → 벡터화 → 저장
- **수집 정보**:
  - 파일 경로, 이름, 크기, 타입
  - 생성/수정/접근 시간
  - 파일 카테고리 (문서, 이미지, 비디오, 코드 등)
  - 텍스트 파일의 경우 내용 미리보기

#### 2. 브라우저 히스토리 수집 및 RAG 인덱싱
- **수집 주기**: 30분마다
- **지원 브라우저**: Chrome, Firefox, Edge
- **RAG 인덱싱**: 
  - URL/제목/방문시간을 텍스트로 변환
  - ColQwen2로 벡터화 → Qdrant 저장
  - 도메인별 분류 및 메타데이터 저장
- **수집 정보**:
  - 방문한 URL과 제목
  - 방문 횟수와 시간
  - 페이지 전환 방식
  - 브라우저 버전 정보

#### 3. 활성 애플리케이션 모니터링
- **수집 주기**: 5분마다
- **수집 정보**:
  - 실행 중인 애플리케이션 목록
  - CPU 및 메모리 사용률
  - 실행 시간과 윈도우 정보
  - 애플리케이션 카테고리 분류

#### 4. 화면 활동 분석 (LLM 기반)
- **수집 주기**: 1분마다
- **분석 방식**: Gemini API를 사용한 스크린샷 분석
- **RAG 인덱싱**:
  - 스크린샷 이미지를 ColQwen2로 벡터화
  - Gemini 분석 결과를 텍스트로 벡터화
  - 앱 이름, 활동 설명, 감지된 텍스트를 메타데이터로 저장
- **수집 정보**:
  - 사용자 활동 설명
  - 활동 카테고리 (작업, 브라우징, 엔터테인먼트 등)
  - 감지된 애플리케이션과 텍스트
  - 분석 신뢰도

### 데이터베이스 구조

#### 새로운 테이블들
- `user_files`: 사용자 파일 정보
- `browser_history`: 브라우저 히스토리
- `active_applications`: 활성 애플리케이션 정보
- `screen_activities`: 화면 활동 분석 결과

### API 엔드포인트

#### 데이터 수집 제어
```bash
# 데이터 수집 시작
POST /api/v2/data-collection/start/{user_id}

# 데이터 수집 중지
POST /api/v2/data-collection/stop/{user_id}

# 모든 데이터 수집 중지
POST /api/v2/data-collection/stop-all

# 데이터 수집 상태 확인
GET /api/v2/data-collection/status

# 데이터 수집 통계
GET /api/v2/data-collection/stats
```

### RAG 데이터 인덱싱
```bash
# 파일 인덱싱
POST /api/v2/rag/index/file
Content-Type: application/json

{
  "doc_id": "file_123",
  "path": "/path/to/file.pdf",
  "vectors": [[0.1, 0.2, ...]],
  "metas": [{"page": 1, "snippet": "..."}]
}

# 스크린샷 인덱싱
POST /api/v2/rag/index/screenshot
Content-Type: application/json

{
  "doc_id": "screen_123",
  "path": "/path/to/screenshot.png",
  "vectors": [[0.1, 0.2, ...]],
  "metas": [{"bbox": [0, 0, 100, 100], "app_name": "chrome"}]
}
```

### 보안 및 개인정보 보호

#### 데이터 보호
- 모든 데이터는 로컬 데이터베이스에만 저장
- 외부 전송 없음
- 사용자 동의 기반 수집

#### RAG 시스템 보안
- 민감 정보 정규식 마스킹 (이메일, 전화번호 등)
- 로컬 벡터 DB로 데이터 외부 전송 방지
- 사용자별 데이터 필터링
- 응답 생성 시 보안 패턴 적용

#### 수집 제어
- 언제든지 수집 중지 가능
- 특정 사용자별 수집 제어
- 수집 주기 조정 가능

### 시스템 요구사항

#### 필수 패키지
```bash
pip install psutil pywin32 pillow google-generativeai
```

#### RAG 시스템 요구사항
```bash
# GPU 메모리: 최소 8GB (VLM 사용 시 16GB 권장)
# CPU: 4코어 이상
# RAM: 16GB 이상
# 저장공간: 10GB 이상 (모델 및 데이터)

# 필수 패키지
pip install torch transformers qdrant-client byaldi rerankers[monovlm]
pip install qwen-vl-utils bitsandbytes pillow numpy pyyaml
```

#### 권한 요구사항
- 파일 시스템 접근 권한
- 브라우저 프로필 접근 권한
- 화면 캡처 권한

### 사용법

#### 자동 시작
JAVIS 애플리케이션을 실행하면 자동으로 데이터 수집이 시작됩니다.

#### 수동 제어
```python
from database.data_collector import start_user_data_collection, stop_user_data_collection

# 사용자 1의 데이터 수집 시작
start_user_data_collection(user_id=1)

# 사용자 1의 데이터 수집 중지
stop_user_data_collection(user_id=1)
```

#### RAG 시스템 사용
```python
from agents.chatbot_agent.rag.react_agent import process

# 질문 처리
state = {
    "question": "지난주 내가 가장 오래 본 웹페이지는?",
    "user_id": "user123",
    "filters": {},
    "time_hint": None
}

result = process(state)
print(result["answer"])
print(f"찾은 근거: {len(result['evidence'])}개")
```

### 성능 최적화

#### 메모리 사용량
- 스크린샷은 압축하여 저장
- 오래된 데이터는 자동 정리
- 데이터베이스 인덱싱으로 빠른 검색

#### CPU 사용량
- 비동기 처리로 시스템 부하 최소화
- 수집 주기 조정 가능
- 백그라운드 스레드 사용

### RAG 시스템 성능 최적화

#### 메모리 최적화
- ColQwen2 모델 캐싱 및 싱글톤 패턴
- 배치 처리로 GPU 메모리 효율적 사용
- 4bit 양자화로 VLM 메모리 사용량 감소

#### 검색 성능
- Qdrant HNSW 인덱스로 빠른 ANN 검색
- 컬렉션별 병렬 검색
- MaxSim 점수 계산 최적화

#### 응답 생성
- MonoVLM 재랭킹은 이미지가 있는 경우만 수행
- VLM 호출은 설정으로 on/off 가능
- 근거 기반 텍스트 응답으로 빠른 응답

## 🤖 등록된 에이전트

모든 에이전트는 통일된 `process(state) -> state` 패턴을 따릅니다:

### 1. Multimodal Chatbot Agent
- **기능**: 멀티모달 RAG 기반 대화
- **도구**: ColQwen2, Qdrant, Gemini API, Tavily Search
- **사용법**: 일반적인 질문이나 이미지 관련 질문
- **패턴**: `process(state) -> state`

### 2. Local RAG Agent
- **기능**: 로컬 데이터 기반 RAG 질의응답
- **도구**: ColQwen2, Qdrant, MonoVLM, Qwen2-VL
- **사용법**: "지난주 내가 가장 오래 본 웹페이지는?", "최근에 작업한 문서는?" 등
- **패턴**: `process(state) -> state`

### 3. Coding Agent
- **기능**: 코드 생성, 디버깅, 리팩토링
- **도구**: 코드 분석 도구, 디버거
- **사용법**: "코드를 작성해줘", "버그를 찾아줘" 등
- **패턴**: `process(state) -> state`

### 4. Dashboard Agent
- **기능**: 데이터 시각화, 차트 생성
- **도구**: 차트 라이브러리, 데이터 분석 도구
- **사용법**: "차트를 만들어줘", "데이터를 분석해줘" 등
- **패턴**: `process(state) -> state`

### 5. Recommendation Agent
- **기능**: 개인화된 추천
- **도구**: 추천 알고리즘, 사용자 프로필 분석
- **사용법**: "추천해줘", "추천해주세요" 등
- **패턴**: `process(state) -> state`

### 에이전트 사용 예시

```python
from backend.agents.chatbot_agent import process as chatbot_process
from backend.agents.coding_agent import CodingAgent
from backend.agents.dashboard_agent import DashboardAgent
from backend.agents.recommendation_agent import RecommendationAgent

# 상태 정의
state = {
    "question": "파이썬으로 간단한 계산기 만들기",
    "user_id": "user123",
    "session_id": "session456"
}

# RAG 에이전트 사용
result = chatbot_process(state)

# 다른 에이전트들 사용
coding_agent = CodingAgent()
result = coding_agent.process(state)

dashboard_agent = DashboardAgent()
result = dashboard_agent.process(state)

recommendation_agent = RecommendationAgent()
result = recommendation_agent.process(state)
```

## 🧠 LLM 기반 지능형 선택 시스템

### 에이전트 선택
- **기존**: 키워드 매칭 기반 선택
- **개선**: LLM을 사용한 자연어 의도 분석
- **장점**: 
  - 더 정확한 에이전트 선택
  - 맥락 이해 능력 향상
  - 자연스러운 대화 처리

### 도구 선택 (React 툴)
- **기존**: 하드코딩된 키워드 기반 선택
- **개선**: LLM 기반 동적 도구 선택
- **장점**:
  - 질문에 맞는 최적의 도구 조합 선택
  - 도구 실행 순서 최적화
  - 더 정확한 결과 생성

### 선택 기준
```json
{
  "selected_agent": "에이전트명",
  "confidence": 0.95,
  "reasoning": "선택 이유 설명",
  "keywords": ["키워드1", "키워드2"],
  "intent": "사용자 의도 요약"
}
```

## 🔄 워크플로우 처리 과정

### 일반 워크플로우
1. **사용자 입력 수신**: 프론트엔드에서 사용자 메시지 전송
2. **LLM 의도 분석**: Gemini API를 사용하여 사용자 의도 분석
3. **에이전트 선택**: LLM 분석 결과를 바탕으로 적절한 에이전트 선택
4. **도구 선택**: LLM이 질문에 맞는 최적의 도구들을 선택
5. **에이전트 실행**: 선택된 에이전트가 선택된 도구들로 작업 수행
6. **응답 생성**: 도구 실행 결과를 바탕으로 최종 응답 생성
7. **사용자에게 전달**: 프론트엔드로 응답 전송

### RAG 워크플로우
1. **질문 수신**: 사용자 질문 입력
2. **ColQwen2 임베딩**: 질문을 128D 벡터로 변환
3. **Qdrant 검색**: text/image/screen 컬렉션에서 ANN 검색
4. **후보 통합**: 각 소스에서 검색된 후보들을 통합
5. **MonoVLM 재랭킹**: 이미지가 있는 경우 재랭킹 수행
6. **Qwen2-VL 분석**: 이미지가 있는 경우 VLM 응답 생성
7. **응답 생성**: 근거 기반 텍스트 응답 또는 VLM 응답
8. **결과 반환**: 사용자에게 최종 응답 전달

## 🎯 사용 예시

### 로컬 RAG 질문
```python
from agents.chatbot_agent.rag.react_agent import process

# 질문 처리
state = {
    "question": "지난주 내가 가장 오래 본 웹페이지는?",
    "user_id": "user123",
    "filters": {},
    "time_hint": None
}

result = process(state)
print(result["answer"])
```

### 멀티모달 질문
```
사용자: "이 이미지에서 무엇을 볼 수 있나요?"
시스템: 
1. Tavily Search로 관련 정보 검색
2. Qdrant에서 유사한 이미지 검색
3. ColQwen2로 멀티모달 분석
4. Gemini API로 최종 응답 생성
```

### 코딩 질문
```
사용자: "Python으로 웹 스크래퍼를 만들어줘"
시스템:
1. 의도 분석 → 코딩 관련
2. Coding Agent 선택
3. 코드 생성 및 설명 제공
```

## 🔧 개발 및 확장

### 새로운 에이전트 추가
1. `agents/` 디렉토리에 새 에이전트 클래스 생성
2. `BaseAgent`를 상속받아 구현
3. `agent_registry.py`에 등록

### 새로운 도구 추가
1. `tools/` 디렉토리에 새 도구 클래스 생성
2. `BaseTool`를 상속받아 구현
3. 에이전트에 도구 등록

### RAG 시스템 확장
1. **새로운 임베더 추가**: `rag/models/` 디렉토리에 새 임베더 클래스 구현
2. **새로운 재랭커 추가**: `rag/rerankers.py`에 새 재랭킹 함수 추가
3. **새로운 VLM 추가**: `rag/answerer.py`에 새 VLM 호출 함수 추가
4. **새로운 데이터 소스 추가**: `database/` 디렉토리에 새 메타데이터 관리자 추가

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

### 사용된 모델 라이선스
- **ColQwen2**: Apache 2.0 License
- **Qwen2-VL**: Tongyi Qianwen License
- **MonoQwen2-VL**: Apache 2.0 License
- **Byaldi**: MIT License

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 🔧 트러블슈팅

### RAG 시스템 문제 해결

#### Qdrant 연결 오류
```bash
# Qdrant 서버 상태 확인
curl http://localhost:6333/collections

# Docker로 재시작
docker stop qdrant
docker run -p 6333:6333 qdrant/qdrant
```

#### 모델 로드 오류
```bash
# CUDA 사용 가능 여부 확인
python -c "import torch; print(torch.cuda.is_available())"

# CPU 모드로 강제 실행
export CUDA_VISIBLE_DEVICES=""
```

#### 메모리 부족 오류
```bash
# VLM 비활성화
# configs.yaml에서 vlm.enabled: false로 설정

# 배치 크기 줄이기
# configs.yaml에서 embedding.batch_size: 16으로 설정
```

## 📞 지원

문제가 있거나 질문이 있으시면 이슈를 생성해주세요.

---

**JAVIS** - Just A Very Intelligent System 🚀

---

## 🎉 RAG 시스템 구현 완료

### 추가/변경된 파일 목록
```
configs.yaml                           # 설정 파일
backend/database/
├── sqlite_meta.py                     # SQLite 메타데이터 관리
├── qdrant_client.py                   # Qdrant 벡터 DB 클라이언트
└── repository.py                      # 통합 Repository API

backend/agents/chatbot_agent/rag/
├── __init__.py                        # RAG 패키지 초기화
├── models/
│   ├── __init__.py                    # 모델 패키지 초기화
│   └── colqwen2_embedder.py           # ColQwen2 임베더
├── retrievers.py                      # 검색 로직
├── rerankers.py                       # 재랭킹 로직
├── answerer.py                        # 응답 생성
└── react_agent.py                     # ReAct 에이전트 엔트리

test_rag.py                           # RAG 시스템 테스트
requirements.txt                      # 의존성 목록
```

### 간단 실행 예제
```python
from agents.chatbot_agent.rag.react_agent import process

# 질문 처리
result = process({
    "question": "지난주 내가 가장 오래 본 웹페이지는?",
    "user_id": "user123"
})

print(result["answer"])
```

## 🔄 최근 업데이트 (2025년 1월)

### 에이전트 통일 패턴 적용
- 모든 에이전트가 `process(state) -> state` 패턴으로 통일
- 기존 async 메서드는 `process_async()`로 유지하여 호환성 보장
- 상태 기반 처리로 더 일관된 에이전트 인터페이스 제공

### 제거된 파일들
- **Alembic 관련 파일들**: 기존 DB 마이그레이션 도구 제거
  - `alembic/` 디렉토리 전체
  - `alembic.ini`
  - `alembic/env.py`
  - `alembic/script.py.mako`
  - `alembic/versions/25fb98aeebd6_add_user_data_collection_models.py`

### 수정된 파일들
- `backend/agents/coding_agent/coding_agent.py` - process(state) 패턴 추가
- `backend/agents/dashboard_agent/dashboard_agent.py` - process(state) 패턴 추가  
- `backend/agents/recommendation_agent/recommendation_agent.py` - process(state) 패턴 추가
- `backend/agents/__init__.py` - 새로운 process 함수들 export
- `README.md` - 에이전트 사용 예시 및 패턴 설명 추가

### 테스트
```python
# 모든 에이전트 테스트
python test_agents.py

# Data Collector와 RAG 연동 테스트
python test_data_collector_rag.py
```

## 🆕 Data Collector와 RAG 시스템 연동 완료

### 주요 변경사항
- **FileCollector**: 파일 수집 시 자동으로 RAG 시스템에 인덱싱
- **BrowserHistoryCollector**: 웹 히스토리 수집 시 RAG 인덱싱
- **ScreenActivityCollector**: 스크린샷 분석 결과를 RAG에 인덱싱
- **통합 인덱싱**: 모든 수집된 데이터가 즉시 검색 가능

### 지원하는 파일 타입
- **텍스트 파일**: .txt, .py, .js, .html, .css, .md, .json, .xml, .csv
- **문서 파일**: .pdf (PyPDF2), .docx, .doc (python-docx)
- **스프레드시트**: .xlsx, .xls (pandas)
- **이미지 파일**: .jpg, .jpeg, .png, .gif, .bmp, .tiff, .webp

### 연동 동작 과정
1. **파일 수집** (1시간마다)
   - 파일 시스템 스캔 → 내용 추출 → 청킹 → 벡터화 → Qdrant 저장
2. **웹 히스토리** (30분마다)
   - 브라우저 히스토리 수집 → 텍스트 변환 → 벡터화 → 저장
3. **화면 활동** (1분마다)
   - 스크린샷 캡처 → Gemini 분석 → 이미지/텍스트 벡터화 → 저장

### 사용 예시
```python
# 파일이 자동으로 인덱싱된 후 검색 가능
result = process({
    "question": "내가 작성한 매출 보고서에서 1분기 실적은?",
    "user_id": "user123"
})

# 웹 히스토리 검색
result = process({
    "question": "지난주에 가장 많이 방문한 웹사이트는?",
    "user_id": "user123"
})

# 화면 활동 검색
result = process({
    "question": "오늘 오후에 어떤 앱을 사용했어?",
    "user_id": "user123"
})
```

### 추가된 의존성
- PyPDF2>=3.0.0 (PDF 파일 처리)
- python-docx>=0.8.11 (Word 문서 처리)
- pandas>=2.0.0 (Excel 파일 처리)
- openpyxl>=3.1.0 (Excel 파일 지원) 