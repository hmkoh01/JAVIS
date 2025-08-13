# JAVIS Multi-Agent System - Multimodal RAG Edition

🤖 **JAVIS (Just A Very Intelligent System)** - 멀티모달 RAG를 지원하는 다중 에이전트 시스템

## 🚀 주요 기능

### 멀티모달 RAG 시스템
- **이미지 업로드 및 처리**: 다양한 이미지 형식 지원 (PNG, JPG, JPEG, GIF, BMP, WEBP)
- **메타데이터 추출**: Gemini API를 사용한 OCR, 시각적 설명, 객체 감지
- **이미지 기반 검색**: 텍스트 쿼리로 관련 이미지 검색
- **멀티모달 콘텐츠 생성**: 이미지와 텍스트를 결합한 콘텐츠 생성
- **Gemini API 통합**: Google의 최신 멀티모달 AI 모델 활용

### 다중 에이전트 시스템
- **멀티모달 챗봇 에이전트**: 이미지와 텍스트를 통합한 대화
- **코딩 에이전트**: 프로그래밍 관련 작업 지원
- **대시보드 에이전트**: 데이터 시각화 및 분석
- **추천 에이전트**: 개인화된 추천 시스템

### 기술 스택
- **백엔드**: FastAPI, LangGraph, SQLAlchemy
- **AI/ML**: Google Gemini API, Transformers, PyTorch
- **데이터베이스**: SQLite (확장 가능)
- **프론트엔드**: Streamlit
- **이미지 처리**: Pillow, OpenCV

## 📋 설치 및 설정

### 1. 시스템 요구사항
- Python 3.8 이상
- Gemini API 키 (Google AI Studio에서 발급)

### 2. 저장소 클론
```bash
git clone <repository-url>
cd JAVIS_MAS
```

### 3. 초기 설정
```bash
# 시스템 초기 설정
python setup.py

# 의존성 설치
pip install -r requirements.txt
```

### 4. 환경 변수 설정
`setup.py`가 자동으로 `.env` 파일을 생성합니다. 다음 설정을 확인/수정하세요:

```env
# Gemini API 설정 (필수)
GEMINI_API_KEY=your_gemini_api_key_here

# 데이터베이스 설정
DATABASE_URL=sqlite:///./javis.db

# API 설정
API_HOST=0.0.0.0
API_PORT=8000

# 이미지 업로드 설정
IMAGE_UPLOAD_PATH=./uploads/images
MAX_IMAGE_SIZE_MB=10
```

### 5. 시스템 시작
```bash
# 전체 시스템 시작 (권장)
python start.py

# 또는 개별 시작
# 백엔드만: cd backend && python main.py
# 프론트엔드만: cd frontend && streamlit run front.py
```

## 🏃‍♂️ 빠른 시작

### 1. 시스템 실행
```bash
python start.py
```
- 옵션 3을 선택하여 전체 시스템을 시작하세요
- 웹 인터페이스: http://localhost:8501
- API 문서: http://localhost:8000/docs

### 2. 이미지 업로드
1. 웹 인터페이스에서 "이미지 업로드" 페이지로 이동
2. 이미지 파일 선택 및 업로드
3. 자동으로 OCR, 시각적 설명, 객체 감지 수행

### 3. 멀티모달 대화
1. "대화" 페이지에서 질문 입력
2. 시스템이 관련 이미지를 검색
3. Gemini API를 사용하여 이미지와 텍스트를 결합한 답변 생성

## 📚 API 사용법

### 멀티모달 RAG API

#### 1. 대화
```bash
curl -X POST "http://localhost:8000/api/v2/multimodal/chat" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=이 이미지에서 무엇을 볼 수 있나요?"
```

#### 2. 이미지 업로드
```bash
curl -X POST "http://localhost:8000/api/v2/multimodal/upload-image" \
  -F "file=@your_image.jpg" \
  -F "user_id=1"
```

#### 3. 이미지 검색
```bash
curl -X GET "http://localhost:8000/api/v2/multimodal/search-images?query=차트&top_k=5"
```

#### 4. 멀티모달 콘텐츠 생성
```bash
curl -X POST "http://localhost:8000/api/v2/multimodal/create-content" \
  -F "title=분석 보고서" \
  -F "description=이미지 분석 결과" \
  -F "text_content=분석 내용..." \
  -F "image_id=1" \
  -F "tags=분석,보고서" \
  -F "category=분석"
```

## 🎯 사용 예시

### 1. 이미지 업로드 및 분석
1. Streamlit 프론트엔드에서 "이미지 업로드" 페이지로 이동
2. 이미지 파일 선택 및 업로드
3. 자동으로 OCR, 시각적 설명, 객체 감지 수행
4. 메타데이터가 데이터베이스에 저장

### 2. 이미지 기반 대화
1. "대화" 페이지에서 질문 입력
2. 시스템이 관련 이미지를 검색
3. Gemini API를 사용하여 이미지와 텍스트를 결합한 답변 생성

### 3. 이미지 검색
1. "이미지 검색" 페이지에서 키워드 입력
2. 관련 이미지들을 검색하여 표시
3. 각 이미지의 메타데이터 확인

## 🏗️ 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   FastAPI       │    │   SQLite DB     │
│   Frontend      │◄──►│   Backend       │◄──►│   (Images +     │
│                 │    │                 │    │    Metadata)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Gemini API    │
                       │   (Multimodal)  │
                       └─────────────────┘
```

## 🔧 개발 가이드

### 새로운 에이전트 추가
1. `backend/agents/` 디렉토리에 새 에이전트 클래스 생성
2. `BaseAgent`를 상속받아 구현
3. `agent_registry.py`에 등록

### 이미지 처리 확장
1. `ImageProcessor` 클래스에서 새로운 처리 로직 추가
2. `MultimodalRAGEngine`에서 검색 알고리즘 개선
3. 새로운 메타데이터 필드 추가

## 📊 성능 최적화

### 이미지 처리
- 이미지 크기 자동 조정 (448x448)
- 배치 처리 지원
- 메모리 효율적인 처리

### 검색 성능
- 키워드 기반 검색 (향후 임베딩 기반으로 확장 가능)
- 캐싱 메커니즘
- 인덱싱 최적화

## 🐛 문제 해결

### 일반적인 문제
1. **Gemini API 오류**: API 키가 올바르게 설정되었는지 확인
2. **이미지 업로드 실패**: 파일 크기와 형식 확인
3. **데이터베이스 오류**: SQLite 파일 권한 확인
4. **포트 충돌**: 8000번(백엔드) 또는 8501번(프론트엔드) 포트가 사용 중인지 확인

### 로그 확인
```bash
# 백엔드 로그
tail -f backend/logs/app.log

# 프론트엔드 로그
streamlit run front.py --logger.level debug
```

### 디버깅 모드
```bash
# 백엔드 디버깅
cd backend
python main.py --debug

# 프론트엔드 디버깅
cd frontend
streamlit run front.py --debug
```

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🙏 감사의 말

- Google Gemini API 팀
- LangGraph 개발팀
- FastAPI 커뮤니티
- Streamlit 팀

---

**JAVIS Multi-Agent System** - 멀티모달 AI의 미래를 만들어갑니다! 🚀 