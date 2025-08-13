import os
import base64
from io import BytesIO
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import google.generativeai as genai
import numpy as np
from sqlalchemy.orm import Session
from config.settings import settings
from database.models import ImageMetadata, MultimodalContent
from .image_processor import ImageProcessor

class MultimodalRAGEngine:
    """멀티모달 RAG 엔진 - 이미지와 텍스트를 통합한 검색 및 생성"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.image_processor = ImageProcessor(db_session)
        
        # Gemini API 설정
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
        else:
            self.gemini_model = None
    
    def search_images(self, query: str, top_k: int = 5) -> List[ImageMetadata]:
        """이미지 검색 - 텍스트 쿼리 기반"""
        try:
            # 간단한 키워드 기반 검색 (실제로는 임베딩 기반 검색이 필요)
            query_lower = query.lower()
            
            # 모든 이미지 메타데이터 조회
            all_images = self.db_session.query(ImageMetadata).filter(
                ImageMetadata.processed == True
            ).all()
            
            # 관련성 점수 계산
            scored_images = []
            for image in all_images:
                score = 0
                
                # 추출된 텍스트에서 검색
                if query_lower in image.extracted_text.lower():
                    score += 3
                
                # 시각적 설명에서 검색
                if query_lower in image.visual_description.lower():
                    score += 2
                
                # 이미지 태그에서 검색
                for tag in image.image_tags:
                    if query_lower in tag.lower():
                        score += 1
                
                # 감지된 객체에서 검색
                for obj in image.detected_objects:
                    if query_lower in obj.lower():
                        score += 1
                
                if score > 0:
                    scored_images.append((image, score))
            
            # 점수별 정렬
            scored_images.sort(key=lambda x: x[1], reverse=True)
            
            # 상위 k개 반환
            return [image for image, score in scored_images[:top_k]]
            
        except Exception as e:
            print(f"이미지 검색 실패: {e}")
            return []
    
    def search_multimodal_content(self, query: str, top_k: int = 5) -> List[MultimodalContent]:
        """멀티모달 콘텐츠 검색"""
        try:
            # 텍스트 콘텐츠 검색
            text_results = self.db_session.query(MultimodalContent).filter(
                MultimodalContent.text_content.contains(query)
            ).limit(top_k).all()
            
            # 이미지 기반 검색 결과
            image_results = self.search_images(query, top_k)
            
            # 결과 통합 (실제로는 더 정교한 랭킹이 필요)
            multimodal_results = []
            
            # 텍스트 결과 추가
            for result in text_results:
                multimodal_results.append({
                    'type': 'text',
                    'content': result,
                    'relevance_score': 1.0
                })
            
            # 이미지 결과 추가
            for i, image in enumerate(image_results):
                multimodal_results.append({
                    'type': 'image',
                    'content': image,
                    'relevance_score': 0.8 - (i * 0.1)  # 순위에 따른 점수 감소
                })
            
            # 점수별 정렬
            multimodal_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return multimodal_results[:top_k]
            
        except Exception as e:
            print(f"멀티모달 콘텐츠 검색 실패: {e}")
            return []
    
    def generate_response(self, query: str, context_images: List[ImageMetadata] = None, 
                         context_text: str = "") -> str:
        """Gemini API를 사용하여 멀티모달 응답 생성"""
        try:
            if not self.gemini_model:
                return "Gemini API가 설정되지 않았습니다."
            
            # 컨텍스트 구성
            context_parts = []
            
            # 텍스트 컨텍스트 추가
            if context_text:
                context_parts.append(f"참고 텍스트: {context_text}")
            
            # 이미지 컨텍스트 추가
            if context_images:
                for i, image_meta in enumerate(context_images):
                    context_parts.append(f"이미지 {i+1} 정보:")
                    context_parts.append(f"- 추출된 텍스트: {image_meta.extracted_text}")
                    context_parts.append(f"- 시각적 설명: {image_meta.visual_description}")
                    context_parts.append(f"- 감지된 객체: {', '.join(image_meta.detected_objects)}")
                    context_parts.append(f"- 이미지 태그: {', '.join(image_meta.image_tags)}")
            
            # 프롬프트 구성
            if context_parts:
                context_str = "\n".join(context_parts)
                prompt = f"""
                다음 컨텍스트 정보를 바탕으로 사용자의 질문에 답변해주세요:
                
                컨텍스트:
                {context_str}
                
                사용자 질문: {query}
                
                답변을 한국어로 작성해주세요.
                """
            else:
                prompt = f"다음 질문에 답변해주세요: {query}"
            
            # Gemini API 호출
            response = self.gemini_model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"응답 생성 실패: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"
    
    def process_query_with_images(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """이미지가 포함된 쿼리 처리"""
        try:
            # 1. 이미지 검색
            relevant_images = self.search_images(query, top_k)
            
            # 2. 텍스트 컨텍스트 구성
            context_text = ""
            if relevant_images:
                image_descriptions = []
                for image in relevant_images:
                    desc = f"이미지 '{image.filename}': {image.visual_description}"
                    if image.extracted_text:
                        desc += f" (추출된 텍스트: {image.extracted_text})"
                    image_descriptions.append(desc)
                context_text = "\n".join(image_descriptions)
            
            # 3. 응답 생성
            response = self.generate_response(query, relevant_images, context_text)
            
            return {
                'query': query,
                'response': response,
                'relevant_images': relevant_images,
                'context_text': context_text,
                'success': True
            }
            
        except Exception as e:
            return {
                'query': query,
                'response': f"쿼리 처리 중 오류가 발생했습니다: {str(e)}",
                'relevant_images': [],
                'context_text': "",
                'success': False
            }
    
    def create_multimodal_content(self, title: str, description: str, 
                                text_content: str = "", image_id: int = None,
                                tags: List[str] = None, category: str = "",
                                source: str = "") -> MultimodalContent:
        """멀티모달 콘텐츠 생성"""
        try:
            content_type = "mixed" if text_content and image_id else ("text" if text_content else "image")
            
            multimodal_content = MultimodalContent(
                content_type=content_type,
                title=title,
                description=description,
                text_content=text_content,
                image_metadata_id=image_id,
                tags=tags or [],
                category=category,
                source=source
            )
            
            self.db_session.add(multimodal_content)
            self.db_session.commit()
            
            return multimodal_content
            
        except Exception as e:
            print(f"멀티모달 콘텐츠 생성 실패: {e}")
            return None
    
    def get_image_by_id(self, image_id: int) -> Optional[ImageMetadata]:
        """ID로 이미지 조회"""
        return self.db_session.query(ImageMetadata).filter(ImageMetadata.id == image_id).first()
    
    def get_multimodal_content_by_id(self, content_id: int) -> Optional[MultimodalContent]:
        """ID로 멀티모달 콘텐츠 조회"""
        return self.db_session.query(MultimodalContent).filter(MultimodalContent.id == content_id).first()
