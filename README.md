# 🦜🕸️ JAVIS - LangGraph 기반 멀티 에이전트 시스템

JAVIS는 LangGraph를 기반으로 한 지능형 멀티 에이전트 시스템입니다. ColQwen2, Milvus, Gemini API, Tavily Search를 활용한 멀티모달 RAG(Retrieval-Augmented Generation) 기능을 제공합니다.

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

### 멀티모달 RAG 파이프라인
```
[사용자 질문]
    ↓
[Tavily Search] → 웹 검색 수행
    ↓
[Milvus 검색] → 관련 이미지 검색
    ↓
[ColQwen2 분석] → 멀티모달 분석
    ↓
[Gemini API] → 최종 응답 생성
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
```

## 🚀 실행 방법

### 전체 시스템 시작
```bash
python start.py
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

## 📊 자동 데이터 수집 시스템

### 개요
JAVIS는 사용자의 디지털 활동을 자동으로 수집하고 분석하는 시스템을 포함합니다. 이 시스템은 사용자의 파일, 브라우저 히스토리, 활성 애플리케이션, 화면 활동을 지속적으로 모니터링하여 개인화된 AI 서비스를 제공합니다.

### 수집되는 데이터

#### 1. 파일 시스템 스캔
- **수집 주기**: 1시간마다
- **수집 범위**: 사용자 드라이브의 모든 파일
- **제외 디렉토리**: Windows, Program Files, 시스템 폴더 등
- **수집 정보**:
  - 파일 경로, 이름, 크기, 타입
  - 생성/수정/접근 시간
  - 파일 카테고리 (문서, 이미지, 비디오, 코드 등)
  - 텍스트 파일의 경우 내용 미리보기

#### 2. 브라우저 히스토리 수집
- **수집 주기**: 30분마다
- **지원 브라우저**: Chrome, Firefox, Edge
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

### 보안 및 개인정보 보호

#### 데이터 보호
- 모든 데이터는 로컬 데이터베이스에만 저장
- 외부 전송 없음
- 사용자 동의 기반 수집

#### 수집 제어
- 언제든지 수집 중지 가능
- 특정 사용자별 수집 제어
- 수집 주기 조정 가능

### 시스템 요구사항

#### 필수 패키지
```bash
pip install psutil pywin32 pillow google-generativeai
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

### 성능 최적화

#### 메모리 사용량
- 스크린샷은 압축하여 저장
- 오래된 데이터는 자동 정리
- 데이터베이스 인덱싱으로 빠른 검색

#### CPU 사용량
- 비동기 처리로 시스템 부하 최소화
- 수집 주기 조정 가능
- 백그라운드 스레드 사용

## 🤖 등록된 에이전트

### 1. Multimodal Chatbot Agent
- **기능**: 멀티모달 RAG 기반 대화
- **도구**: ColQwen2, Milvus, Gemini API, Tavily Search
- **사용법**: 일반적인 질문이나 이미지 관련 질문

### 2. Coding Agent
- **기능**: 코드 생성, 디버깅, 리팩토링
- **도구**: 코드 분석 도구, 디버거
- **사용법**: "코드를 작성해줘", "버그를 찾아줘" 등

### 3. Dashboard Agent
- **기능**: 데이터 시각화, 차트 생성
- **도구**: 차트 라이브러리, 데이터 분석 도구
- **사용법**: "차트를 만들어줘", "데이터를 분석해줘" 등

### 4. Recommendation Agent
- **기능**: 개인화된 추천
- **도구**: 추천 알고리즘, 사용자 프로필 분석
- **사용법**: "추천해줘", "추천해주세요" 등

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

1. **사용자 입력 수신**: 프론트엔드에서 사용자 메시지 전송
2. **LLM 의도 분석**: Gemini API를 사용하여 사용자 의도 분석
3. **에이전트 선택**: LLM 분석 결과를 바탕으로 적절한 에이전트 선택
4. **도구 선택**: LLM이 질문에 맞는 최적의 도구들을 선택
5. **에이전트 실행**: 선택된 에이전트가 선택된 도구들로 작업 수행
6. **응답 생성**: 도구 실행 결과를 바탕으로 최종 응답 생성
7. **사용자에게 전달**: 프론트엔드로 응답 전송

## 🎯 사용 예시

### 멀티모달 질문
```
사용자: "이 이미지에서 무엇을 볼 수 있나요?"
시스템: 
1. Tavily Search로 관련 정보 검색
2. Milvus에서 유사한 이미지 검색
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

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 지원

문제가 있거나 질문이 있으시면 이슈를 생성해주세요.

---

**JAVIS** - Just A Very Intelligent System 🚀 