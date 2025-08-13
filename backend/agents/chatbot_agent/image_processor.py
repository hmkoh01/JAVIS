import os
import base64
from io import BytesIO
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import google.generativeai as genai
from config.settings import settings
from database.models import ImageMetadata
from sqlalchemy.orm import Session

class ImageProcessor:
    """이미지 처리 및 메타데이터 추출 클래스"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.upload_path = settings.IMAGE_UPLOAD_PATH
        self.processing_size = settings.IMAGE_PROCESSING_SIZE
        self.max_size_mb = settings.MAX_IMAGE_SIZE_MB
        self.supported_formats = settings.SUPPORTED_IMAGE_FORMATS
        
        # Gemini API 설정
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
        else:
            self.gemini_model = None
        
        # 업로드 디렉토리 생성
        os.makedirs(self.upload_path, exist_ok=True)
    
    def validate_image(self, image_data: bytes, filename: str) -> Tuple[bool, str]:
        """이미지 유효성 검사"""
        try:
            # 파일 크기 검사
            if len(image_data) > self.max_size_mb * 1024 * 1024:
                return False, f"이미지 크기가 {self.max_size_mb}MB를 초과합니다."
            
            # 파일 형식 검사
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in self.supported_formats:
                return False, f"지원하지 않는 이미지 형식입니다: {file_ext}"
            
            # 이미지 로드 테스트
            image = Image.open(BytesIO(image_data))
            image.verify()
            
            return True, "유효한 이미지입니다."
            
        except Exception as e:
            return False, f"이미지 검증 실패: {str(e)}"
    
    def save_image(self, image_data: bytes, filename: str) -> str:
        """이미지를 저장하고 경로를 반환"""
        file_path = os.path.join(self.upload_path, filename)
        
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        return file_path
    
    def process_image(self, image_data: bytes, filename: str) -> Dict[str, Any]:
        """이미지 처리 및 메타데이터 추출"""
        # 이미지 로드 및 리사이즈
        image = Image.open(BytesIO(image_data))
        original_size = image.size
        
        # 처리용 이미지 리사이즈
        processed_image = image.resize(self.processing_size, Image.Resampling.LANCZOS)
        
        # 기본 메타데이터
        metadata = {
            'filename': filename,
            'file_size': len(image_data),
            'image_type': image.format,
            'width': original_size[0],
            'height': original_size[1],
            'processed_width': self.processing_size[0],
            'processed_height': self.processing_size[1]
        }
        
        # Gemini API를 사용한 메타데이터 추출
        if self.gemini_model:
            extracted_metadata = self._extract_metadata_with_gemini(processed_image)
            metadata.update(extracted_metadata)
        
        return metadata
    
    def _extract_metadata_with_gemini(self, image: Image.Image) -> Dict[str, Any]:
        """Gemini API를 사용하여 이미지에서 메타데이터 추출"""
        try:
            # 이미지를 base64로 인코딩
            buffer = BytesIO()
            image.save(buffer, format='JPEG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Gemini API 호출
            prompt = """
            이 이미지를 분석하여 다음 정보를 추출해주세요:
            1. 이미지에 포함된 텍스트 (OCR)
            2. 시각적 설명 (이미지가 무엇을 보여주는지)
            3. 감지된 객체들
            4. 이미지 태그 (키워드)
            
            JSON 형식으로 응답해주세요:
            {
                "extracted_text": "추출된 텍스트",
                "visual_description": "시각적 설명",
                "detected_objects": ["객체1", "객체2"],
                "image_tags": ["태그1", "태그2"]
            }
            """
            
            response = self.gemini_model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": image_base64}
            ])
            
            # 응답 파싱 (간단한 JSON 추출)
            response_text = response.text
            # 실제 구현에서는 더 정교한 JSON 파싱이 필요
            return {
                'extracted_text': response_text,
                'visual_description': response_text,
                'detected_objects': [],
                'image_tags': []
            }
            
        except Exception as e:
            print(f"Gemini API 메타데이터 추출 실패: {e}")
            return {
                'extracted_text': '',
                'visual_description': '',
                'detected_objects': [],
                'image_tags': []
            }
    
    def create_image_metadata_record(self, metadata: Dict[str, Any], file_path: str) -> ImageMetadata:
        """데이터베이스에 이미지 메타데이터 레코드 생성"""
        image_metadata = ImageMetadata(
            filename=metadata['filename'],
            file_path=file_path,
            file_size=metadata['file_size'],
            image_type=metadata['image_type'],
            width=metadata['width'],
            height=metadata['height'],
            extracted_text=metadata.get('extracted_text', ''),
            visual_description=metadata.get('visual_description', ''),
            detected_objects=metadata.get('detected_objects', []),
            detected_text=metadata.get('detected_text', []),
            image_tags=metadata.get('image_tags', []),
            processed=True
        )
        
        self.db_session.add(image_metadata)
        self.db_session.commit()
        
        return image_metadata
    
    def get_image_metadata(self, image_id: int) -> Optional[ImageMetadata]:
        """이미지 메타데이터 조회"""
        return self.db_session.query(ImageMetadata).filter(ImageMetadata.id == image_id).first()
    
    def get_all_images(self) -> List[ImageMetadata]:
        """모든 이미지 메타데이터 조회"""
        return self.db_session.query(ImageMetadata).all()
    
    def delete_image(self, image_id: int) -> bool:
        """이미지 및 메타데이터 삭제"""
        try:
            image_metadata = self.get_image_metadata(image_id)
            if image_metadata:
                # 파일 삭제
                if os.path.exists(image_metadata.file_path):
                    os.remove(image_metadata.file_path)
                
                # 데이터베이스 레코드 삭제
                self.db_session.delete(image_metadata)
                self.db_session.commit()
                return True
            return False
        except Exception as e:
            print(f"이미지 삭제 실패: {e}")
            return False
