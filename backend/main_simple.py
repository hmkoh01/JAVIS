#!/usr/bin/env python3
"""
JAVIS Multimodal RAG System - Simplified Backend
Langchain compatibility issues를 우회하는 간단한 백엔드
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import base64
from datetime import datetime

# FastAPI imports
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Database imports
from database.connection import get_db_session, create_tables
from database.models import ImageMetadata, MultimodalContent

# Settings
from config.settings import settings

# Initialize FastAPI app
app = FastAPI(
    title="JAVIS Multimodal RAG System",
    description="멀티모달 RAG 시스템의 간단한 백엔드",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = None

class ChatResponse(BaseModel):
    success: bool
    message: str
    metadata: Optional[Dict[str, Any]] = None

# Startup event
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    print("JAVIS Multimodal RAG System 시작 중...")
    
    # 데이터베이스 테이블 생성
    try:
        create_tables()
        print("데이터베이스 테이블이 생성되었습니다.")
    except Exception as e:
        print(f"데이터베이스 초기화 실패: {e}")

# Root endpoint
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "JAVIS Multimodal RAG System",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "Multimodal RAG Chat",
            "Image Upload & Processing",
            "Image Search",
            "Content Management"
        ]
    }

# System info endpoint
@app.get("/info")
async def system_info():
    """시스템 정보"""
    return {
        "system": "JAVIS Multimodal RAG System",
        "version": "2.0.0",
        "status": "operational",
        "database": "SQLite",
        "llm": "Gemini API",
        "features": {
            "multimodal_chat": True,
            "image_processing": True,
            "image_search": True,
            "content_management": True
        }
    }

# Chat endpoint
@app.post("/api/v2/multimodal/chat")
async def chat_with_multimodal_rag(message: str = Form(...), user_id: Optional[int] = Form(None)):
    """멀티모달 RAG 채팅"""
    try:
        # 간단한 응답 생성 (실제로는 Gemini API 호출)
        response_text = f"안녕하세요! '{message}'에 대한 답변입니다. 현재는 데모 모드로 작동하고 있습니다."
        
        # 데이터베이스에 상호작용 기록 (선택사항)
        if user_id:
            try:
                db = get_db_session()
                # 여기에 상호작용 기록 로직 추가 가능
                db.close()
            except:
                pass
        
        return ChatResponse(
            success=True,
            message=response_text,
            metadata={
                "query": message,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "mode": "demo"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"채팅 처리 중 오류: {str(e)}")

# Image upload endpoint
@app.post("/api/v2/multimodal/upload-image")
async def upload_image(file: UploadFile = File(...), user_id: Optional[int] = Form(None)):
    """이미지 업로드 및 처리"""
    try:
        # 파일 검증
        if not file.filename:
            raise HTTPException(status_code=400, detail="파일명이 없습니다.")
        
        # 지원 형식 확인
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: {file_ext}")
        
        # 파일 크기 확인 (10MB 제한)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="파일 크기가 10MB를 초과합니다.")
        
        # 업로드 디렉토리 생성
        upload_dir = Path(settings.IMAGE_UPLOAD_PATH)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일 저장
        file_path = upload_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # 데이터베이스에 메타데이터 저장
        db = get_db_session()
        try:
            image_metadata = ImageMetadata(
                filename=file.filename,
                file_path=str(file_path),
                file_size=len(file_content),
                image_type=file_ext[1:],  # 확장자에서 점 제거
                width=0,  # 실제로는 PIL로 이미지 크기 확인
                height=0,
                extracted_text="",  # 실제로는 Gemini API로 텍스트 추출
                visual_description="업로드된 이미지",  # 실제로는 Gemini API로 설명 생성
                detected_objects=[],
                detected_text=[],
                image_tags=[],
                embedding=None,
                processed=True,
                uploaded_at=datetime.now(),
                processed_at=datetime.now()
            )
            
            db.add(image_metadata)
            db.commit()
            db.refresh(image_metadata)
            
            return {
                "success": True,
                "message": f"이미지 '{file.filename}'이 성공적으로 업로드되었습니다.",
                "metadata": {
                    "image_id": image_metadata.id,
                    "filename": image_metadata.filename,
                    "file_path": image_metadata.file_path,
                    "user_id": user_id,
                    "uploaded_at": image_metadata.uploaded_at.isoformat()
                }
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 업로드 중 오류: {str(e)}")

# Image search endpoint
@app.get("/api/v2/multimodal/search-images")
async def search_images(query: str, top_k: int = 5):
    """이미지 검색"""
    try:
        db = get_db_session()
        
        # 간단한 검색 (실제로는 임베딩 기반 검색)
        images = db.query(ImageMetadata).filter(
            ImageMetadata.processed == True
        ).limit(top_k).all()
        
        results = []
        for img in images:
            results.append({
                "id": img.id,
                "filename": img.filename,
                "visual_description": img.visual_description,
                "extracted_text": img.extracted_text,
                "uploaded_at": img.uploaded_at.isoformat(),
                "file_size": img.file_size,
                "width": img.width,
                "height": img.height
            })
        
        db.close()
        
        return {
            "success": True,
            "message": f"'{query}'에 대한 검색 결과입니다.",
            "metadata": {
                "query": query,
                "results_count": len(results),
                "top_k": top_k
            },
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 검색 중 오류: {str(e)}")

# Get all images endpoint
@app.get("/api/v2/multimodal/images")
async def get_all_images():
    """모든 이미지 목록 조회"""
    try:
        db = get_db_session()
        
        images = db.query(ImageMetadata).all()
        
        image_list = []
        for img in images:
            image_list.append({
                "id": img.id,
                "filename": img.filename,
                "file_size": img.file_size,
                "width": img.width,
                "height": img.height,
                "image_type": img.image_type,
                "uploaded_at": img.uploaded_at.isoformat(),
                "processed": img.processed,
                "visual_description": img.visual_description,
                "extracted_text": img.extracted_text
            })
        
        db.close()
        
        return {
            "success": True,
            "total_count": len(image_list),
            "images": image_list
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 목록 조회 중 오류: {str(e)}")

# Get image by ID endpoint
@app.get("/api/v2/multimodal/image/{image_id}")
async def get_image_by_id(image_id: int):
    """이미지 ID로 상세 정보 조회"""
    try:
        db = get_db_session()
        
        image = db.query(ImageMetadata).filter(ImageMetadata.id == image_id).first()
        
        if not image:
            raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
        
        db.close()
        
        return {
            "success": True,
            "image": {
                "id": image.id,
                "filename": image.filename,
                "file_path": image.file_path,
                "file_size": image.file_size,
                "width": image.width,
                "height": image.height,
                "image_type": image.image_type,
                "uploaded_at": image.uploaded_at.isoformat(),
                "processed": image.processed,
                "visual_description": image.visual_description,
                "extracted_text": image.extracted_text,
                "detected_objects": image.detected_objects,
                "image_tags": image.image_tags
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 조회 중 오류: {str(e)}")

# Delete image endpoint
@app.delete("/api/v2/multimodal/image/{image_id}")
async def delete_image(image_id: int):
    """이미지 삭제"""
    try:
        db = get_db_session()
        
        image = db.query(ImageMetadata).filter(ImageMetadata.id == image_id).first()
        
        if not image:
            raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
        
        # 파일 삭제
        try:
            file_path = Path(image.file_path)
            if file_path.exists():
                file_path.unlink()
        except:
            pass  # 파일 삭제 실패는 무시
        
        # 데이터베이스에서 삭제
        db.delete(image)
        db.commit()
        
        db.close()
        
        return {
            "success": True,
            "message": f"이미지 '{image.filename}'이 삭제되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 삭제 중 오류: {str(e)}")

# Create multimodal content endpoint
@app.post("/api/v2/multimodal/create-content")
async def create_multimodal_content(
    title: str = Form(...),
    description: str = Form(...),
    text_content: str = Form(""),
    image_id: Optional[int] = Form(None),
    tags: str = Form("[]"),
    category: str = Form(""),
    source: str = Form(""),
    user_id: Optional[int] = Form(None)
):
    """멀티모달 콘텐츠 생성"""
    try:
        db = get_db_session()
        
        # 태그 파싱
        try:
            tags_list = json.loads(tags)
        except:
            tags_list = []
        
        # 콘텐츠 타입 결정
        content_type = "text"
        if image_id:
            content_type = "mixed"
        
        # 멀티모달 콘텐츠 생성
        multimodal_content = MultimodalContent(
            content_type=content_type,
            title=title,
            description=description,
            text_content=text_content,
            image_metadata_id=image_id,
            tags=tags_list,
            category=category,
            source=source,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(multimodal_content)
        db.commit()
        db.refresh(multimodal_content)
        
        db.close()
        
        return {
            "success": True,
            "message": f"콘텐츠 '{title}'이 성공적으로 생성되었습니다.",
            "metadata": {
                "content_id": multimodal_content.id,
                "content_type": multimodal_content.content_type,
                "user_id": user_id,
                "created_at": multimodal_content.created_at.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"콘텐츠 생성 중 오류: {str(e)}")

# Available operations endpoint
@app.get("/api/v2/multimodal/operations")
async def get_available_operations():
    """사용 가능한 작업 목록"""
    return {
        "success": True,
        "operations": [
            {
                "name": "chat",
                "description": "멀티모달 RAG 채팅",
                "endpoint": "POST /api/v2/multimodal/chat"
            },
            {
                "name": "upload_image",
                "description": "이미지 업로드 및 처리",
                "endpoint": "POST /api/v2/multimodal/upload-image"
            },
            {
                "name": "search_images",
                "description": "이미지 검색",
                "endpoint": "GET /api/v2/multimodal/search-images"
            },
            {
                "name": "get_all_images",
                "description": "모든 이미지 목록 조회",
                "endpoint": "GET /api/v2/multimodal/images"
            },
            {
                "name": "get_image",
                "description": "이미지 상세 정보 조회",
                "endpoint": "GET /api/v2/multimodal/image/{image_id}"
            },
            {
                "name": "delete_image",
                "description": "이미지 삭제",
                "endpoint": "DELETE /api/v2/multimodal/image/{image_id}"
            },
            {
                "name": "create_content",
                "description": "멀티모달 콘텐츠 생성",
                "endpoint": "POST /api/v2/multimodal/create-content"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    print("JAVIS Multimodal RAG System - Simplified Backend")
    print("=" * 60)
    print(f"서버 주소: http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"API 문서: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    print(f"시스템 정보: http://{settings.API_HOST}:{settings.API_PORT}/info")
    print("=" * 60)
    
    uvicorn.run(
        "main_simple:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
