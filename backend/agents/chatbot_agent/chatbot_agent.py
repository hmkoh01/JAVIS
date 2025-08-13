from typing import List, Dict, Any, Optional
from datetime import datetime
import os
from ..base_agent import BaseAgent, AgentResponse
from .multimodal_rag_engine import MultimodalRAGEngine
from .image_processor import ImageProcessor
from database.connection import get_db_session
from config.settings import settings

class ChatbotAgent(BaseAgent):
    """멀티모달 RAG 기반 챗봇 에이전트 with Gemini API"""
    
    def __init__(self):
        super().__init__(
            agent_type="multimodal_chatbot",
            description="멀티모달 RAG 기반으로 이미지와 텍스트를 통합하여 답변을 생성합니다."
        )
        self.rag_engine = None
        self.image_processor = None
        self._initialize_components()
    
    def _initialize_components(self):
        """멀티모달 RAG 엔진과 이미지 프로세서를 초기화합니다."""
        try:
            # 데이터베이스 세션 생성
            db_session = get_db_session()
            
            # 멀티모달 RAG 엔진 초기화
            self.rag_engine = MultimodalRAGEngine(db_session)
            
            # 이미지 프로세서 초기화
            self.image_processor = ImageProcessor(db_session)
            
        except Exception as e:
            print(f"멀티모달 챗봇 에이전트 초기화 오류: {e}")
    
    async def process(self, user_input: str, user_id: Optional[int] = None) -> AgentResponse:
        """사용자 입력을 처리합니다."""
        try:
            # 멀티모달 RAG 엔진을 사용하여 쿼리 처리
            result = self.rag_engine.process_query_with_images(user_input, top_k=3)
            
            if result['success']:
                response_content = self._format_response(result)
                
                return AgentResponse(
                    success=True,
                    content=response_content,
                    agent_type=self.agent_type,
                    metadata={
                        "query": user_input,
                        "relevant_images_count": len(result['relevant_images']),
                        "context_text": result['context_text'],
                        "user_id": user_id
                    }
                )
            else:
                return AgentResponse(
                    success=False,
                    content=result['response'],
                    agent_type=self.agent_type
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"처리 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    def _format_response(self, result: Dict[str, Any]) -> str:
        """응답을 사용자 친화적으로 포맷합니다."""
        response_parts = []
        
        # 주요 응답
        response_parts.append(result['response'])
        
        # 관련 이미지 정보 추가
        if result['relevant_images']:
            response_parts.append("\n\n참고 이미지:")
            for i, image in enumerate(result['relevant_images'], 1):
                response_parts.append(f"{i}. {image.filename}")
                if image.visual_description:
                    response_parts.append(f"   설명: {image.visual_description}")
                if image.extracted_text:
                    response_parts.append(f"   추출된 텍스트: {image.extracted_text[:100]}...")
        
        return "\n".join(response_parts)
    
    async def upload_image(self, image_data: bytes, filename: str, user_id: Optional[int] = None) -> AgentResponse:
        """이미지 업로드 및 처리"""
        try:
            # 이미지 유효성 검사
            is_valid, message = self.image_processor.validate_image(image_data, filename)
            if not is_valid:
                return AgentResponse(
                    success=False,
                    content=f"이미지 검증 실패: {message}",
                    agent_type=self.agent_type
                )
            
            # 이미지 처리 및 메타데이터 추출
            metadata = self.image_processor.process_image(image_data, filename)
            
            # 이미지 저장
            file_path = self.image_processor.save_image(image_data, filename)
            
            # 데이터베이스에 메타데이터 저장
            image_metadata = self.image_processor.create_image_metadata_record(metadata, file_path)
            
            return AgentResponse(
                success=True,
                content=f"이미지 '{filename}'이 성공적으로 업로드되고 처리되었습니다.\n"
                       f"파일 크기: {metadata['file_size']} bytes\n"
                       f"이미지 크기: {metadata['width']}x{metadata['height']}\n"
                       f"추출된 텍스트: {metadata.get('extracted_text', '없음')[:100]}...",
                agent_type=self.agent_type,
                metadata={
                    "image_id": image_metadata.id,
                    "filename": filename,
                    "file_path": file_path,
                    "user_id": user_id
                }
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"이미지 업로드 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def search_images(self, query: str, top_k: int = 5, user_id: Optional[int] = None) -> AgentResponse:
        """이미지 검색"""
        try:
            relevant_images = self.rag_engine.search_images(query, top_k)
            
            if relevant_images:
                response_content = f"'{query}'에 대한 검색 결과 ({len(relevant_images)}개):\n\n"
                
                for i, image in enumerate(relevant_images, 1):
                    response_content += f"{i}. {image.filename}\n"
                    response_content += f"   설명: {image.visual_description}\n"
                    if image.extracted_text:
                        response_content += f"   텍스트: {image.extracted_text[:100]}...\n"
                    response_content += f"   태그: {', '.join(image.image_tags)}\n\n"
            else:
                response_content = f"'{query}'에 대한 관련 이미지를 찾을 수 없습니다."
            
            return AgentResponse(
                success=True,
                content=response_content,
                agent_type=self.agent_type,
                metadata={
                    "query": query,
                    "results_count": len(relevant_images),
                    "user_id": user_id
                }
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"이미지 검색 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def create_multimodal_content(self, title: str, description: str, 
                                      text_content: str = "", image_id: int = None,
                                      tags: List[str] = None, category: str = "",
                                      source: str = "", user_id: Optional[int] = None) -> AgentResponse:
        """멀티모달 콘텐츠 생성"""
        try:
            multimodal_content = self.rag_engine.create_multimodal_content(
                title=title,
                description=description,
                text_content=text_content,
                image_id=image_id,
                tags=tags,
                category=category,
                source=source
            )
            
            if multimodal_content:
                return AgentResponse(
                    success=True,
                    content=f"멀티모달 콘텐츠가 성공적으로 생성되었습니다.\n"
                           f"제목: {title}\n"
                           f"타입: {multimodal_content.content_type}\n"
                           f"카테고리: {category}",
                    agent_type=self.agent_type,
                    metadata={
                        "content_id": multimodal_content.id,
                        "content_type": multimodal_content.content_type,
                        "user_id": user_id
                    }
                )
            else:
                return AgentResponse(
                    success=False,
                    content="멀티모달 콘텐츠 생성에 실패했습니다.",
                    agent_type=self.agent_type
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"멀티모달 콘텐츠 생성 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def get_image_info(self, image_id: int, user_id: Optional[int] = None) -> AgentResponse:
        """이미지 정보 조회"""
        try:
            image_metadata = self.rag_engine.get_image_by_id(image_id)
            
            if image_metadata:
                response_content = f"이미지 정보:\n\n"
                response_content += f"파일명: {image_metadata.filename}\n"
                response_content += f"파일 크기: {image_metadata.file_size} bytes\n"
                response_content += f"이미지 크기: {image_metadata.width}x{image_metadata.height}\n"
                response_content += f"이미지 타입: {image_metadata.image_type}\n"
                response_content += f"업로드 시간: {image_metadata.uploaded_at}\n\n"
                
                if image_metadata.visual_description:
                    response_content += f"시각적 설명: {image_metadata.visual_description}\n\n"
                
                if image_metadata.extracted_text:
                    response_content += f"추출된 텍스트: {image_metadata.extracted_text}\n\n"
                
                if image_metadata.detected_objects:
                    response_content += f"감지된 객체: {', '.join(image_metadata.detected_objects)}\n\n"
                
                if image_metadata.image_tags:
                    response_content += f"이미지 태그: {', '.join(image_metadata.image_tags)}\n"
                
                return AgentResponse(
                    success=True,
                    content=response_content,
                    agent_type=self.agent_type,
                    metadata={
                        "image_id": image_id,
                        "user_id": user_id
                    }
                )
            else:
                return AgentResponse(
                    success=False,
                    content=f"ID {image_id}에 해당하는 이미지를 찾을 수 없습니다.",
                    agent_type=self.agent_type
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"이미지 정보 조회 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def delete_image(self, image_id: int, user_id: Optional[int] = None) -> AgentResponse:
        """이미지 삭제"""
        try:
            success = self.image_processor.delete_image(image_id)
            
            if success:
                return AgentResponse(
                    success=True,
                    content=f"이미지 ID {image_id}가 성공적으로 삭제되었습니다.",
                    agent_type=self.agent_type,
                    metadata={
                        "image_id": image_id,
                        "user_id": user_id
                    }
                )
            else:
                return AgentResponse(
                    success=False,
                    content=f"이미지 ID {image_id} 삭제에 실패했습니다.",
                    agent_type=self.agent_type
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"이미지 삭제 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    def get_available_operations(self) -> List[Dict[str, str]]:
        """사용 가능한 작업 목록을 반환합니다."""
        return [
            {
                "operation": "chat",
                "description": "멀티모달 RAG를 사용한 대화",
                "parameters": ["user_input"]
            },
            {
                "operation": "upload_image",
                "description": "이미지 업로드 및 메타데이터 추출",
                "parameters": ["image_data", "filename"]
            },
            {
                "operation": "search_images",
                "description": "이미지 검색",
                "parameters": ["query", "top_k"]
            },
            {
                "operation": "create_multimodal_content",
                "description": "멀티모달 콘텐츠 생성",
                "parameters": ["title", "description", "text_content", "image_id", "tags", "category", "source"]
            },
            {
                "operation": "get_image_info",
                "description": "이미지 정보 조회",
                "parameters": ["image_id"]
            },
            {
                "operation": "delete_image",
                "description": "이미지 삭제",
                "parameters": ["image_id"]
            }
        ] 