from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
from datetime import datetime

from agents.chatbot_agent.chatbot_agent import ChatbotAgent
from database.connection import get_db_session
from config.settings import settings

router = APIRouter(prefix="/multimodal", tags=["multimodal"])

# 챗봇 에이전트 인스턴스
chatbot_agent = ChatbotAgent()

@router.post("/chat")
async def chat_with_multimodal_rag(
    message: str = Form(...),
    user_id: Optional[int] = Form(None)
):
    """멀티모달 RAG를 사용한 대화"""
    try:
        response = await chatbot_agent.process(message, user_id)
        
        return JSONResponse(
            status_code=200 if response.success else 400,
            content={
                "success": response.success,
                "message": response.content,
                "agent_type": response.agent_type,
                "metadata": response.metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대화 처리 중 오류가 발생했습니다: {str(e)}")

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    user_id: Optional[int] = Form(None)
):
    """이미지 업로드 및 메타데이터 추출"""
    try:
        # 파일 유효성 검사
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")
        
        # 파일 크기 검사
        file_size = 0
        image_data = b""
        
        # 파일 데이터 읽기
        while chunk := await file.read(8192):
            image_data += chunk
            file_size += len(chunk)
            
            if file_size > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=400, 
                    detail=f"파일 크기가 {settings.MAX_IMAGE_SIZE_MB}MB를 초과합니다."
                )
        
        # 이미지 업로드 처리
        response = await chatbot_agent.upload_image(image_data, file.filename, user_id)
        
        return JSONResponse(
            status_code=200 if response.success else 400,
            content={
                "success": response.success,
                "message": response.content,
                "agent_type": response.agent_type,
                "metadata": response.metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 업로드 중 오류가 발생했습니다: {str(e)}")

@router.get("/search-images")
async def search_images(
    query: str,
    top_k: int = 5,
    user_id: Optional[int] = None
):
    """이미지 검색"""
    try:
        response = await chatbot_agent.search_images(query, top_k, user_id)
        
        return JSONResponse(
            status_code=200 if response.success else 400,
            content={
                "success": response.success,
                "message": response.content,
                "agent_type": response.agent_type,
                "metadata": response.metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 검색 중 오류가 발생했습니다: {str(e)}")

@router.post("/create-content")
async def create_multimodal_content(
    title: str = Form(...),
    description: str = Form(...),
    text_content: str = Form(""),
    image_id: Optional[int] = Form(None),
    tags: Optional[str] = Form(""),  # JSON string
    category: str = Form(""),
    source: str = Form(""),
    user_id: Optional[int] = Form(None)
):
    """멀티모달 콘텐츠 생성"""
    try:
        # 태그 파싱
        tag_list = []
        if tags:
            import json
            try:
                tag_list = json.loads(tags)
            except json.JSONDecodeError:
                tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        response = await chatbot_agent.create_multimodal_content(
            title=title,
            description=description,
            text_content=text_content,
            image_id=image_id,
            tags=tag_list,
            category=category,
            source=source,
            user_id=user_id
        )
        
        return JSONResponse(
            status_code=200 if response.success else 400,
            content={
                "success": response.success,
                "message": response.content,
                "agent_type": response.agent_type,
                "metadata": response.metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"콘텐츠 생성 중 오류가 발생했습니다: {str(e)}")

@router.get("/image/{image_id}")
async def get_image_info(image_id: int, user_id: Optional[int] = None):
    """이미지 정보 조회"""
    try:
        response = await chatbot_agent.get_image_info(image_id, user_id)
        
        return JSONResponse(
            status_code=200 if response.success else 400,
            content={
                "success": response.success,
                "message": response.content,
                "agent_type": response.agent_type,
                "metadata": response.metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 정보 조회 중 오류가 발생했습니다: {str(e)}")

@router.delete("/image/{image_id}")
async def delete_image(image_id: int, user_id: Optional[int] = None):
    """이미지 삭제"""
    try:
        response = await chatbot_agent.delete_image(image_id, user_id)
        
        return JSONResponse(
            status_code=200 if response.success else 400,
            content={
                "success": response.success,
                "message": response.content,
                "agent_type": response.agent_type,
                "metadata": response.metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 삭제 중 오류가 발생했습니다: {str(e)}")

@router.get("/operations")
async def get_available_operations():
    """사용 가능한 작업 목록 조회"""
    try:
        operations = chatbot_agent.get_available_operations()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "operations": operations,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 목록 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/images")
async def list_all_images(user_id: Optional[int] = None):
    """모든 이미지 목록 조회"""
    try:
        db_session = get_db_session()
        from database.models import ImageMetadata
        
        images = db_session.query(ImageMetadata).all()
        
        image_list = []
        for image in images:
            image_list.append({
                "id": image.id,
                "filename": image.filename,
                "file_size": image.file_size,
                "width": image.width,
                "height": image.height,
                "image_type": image.image_type,
                "uploaded_at": image.uploaded_at.isoformat(),
                "processed": image.processed,
                "visual_description": image.visual_description,
                "extracted_text": image.extracted_text[:100] + "..." if len(image.extracted_text) > 100 else image.extracted_text
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "images": image_list,
                "total_count": len(image_list),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 목록 조회 중 오류가 발생했습니다: {str(e)}")
