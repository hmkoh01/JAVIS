from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from .schemas import UserIntent, SupervisorResponse, ChatRequest, ChatResponse
from core.supervisor import supervisor
from core.agent_registry import agent_registry
from database.data_collector import (
    start_user_data_collection, 
    stop_user_data_collection, 
    stop_all_data_collection,
    data_collection_managers
)

router = APIRouter()

@router.post("/process")
async def process_user_intent(user_intent: UserIntent):
    """사용자 의도를 처리하고 적절한 에이전트를 선택하여 실행합니다."""
    try:
        response = await supervisor.process_user_intent(user_intent)
        # SupervisorResponse를 딕셔너리로 변환하여 반환
        return {
            "success": response.success,
            "content": response.response.content,
            "agent_type": response.response.agent_type,
            "selected_agent": response.selected_agent,
            "selected_agents": response.metadata.get("selected_agents", [response.selected_agent]),
            "reasoning": response.reasoning,
            "metadata": {
                **response.metadata,
                "agent_responses": response.metadata.get("agent_responses", []),
                "total_agents_executed": len(response.metadata.get("selected_agents", [])),
                "successful_agents": response.metadata.get("agent_responses", [])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류가 발생했습니다: {str(e)}")

@router.post("/chat")
async def chat_with_agent(chat_request: ChatRequest) -> ChatResponse:
    """사용자 메시지를 받아서 supervisor를 통해 적절한 에이전트로 라우팅합니다."""
    try:
        # UserIntent로 변환
        user_intent = UserIntent(
            message=chat_request.message,
            user_id=chat_request.user_id
        )
        
        # Supervisor를 통해 처리
        supervisor_response = await supervisor.process_user_intent(user_intent)
        
        # ChatResponse로 변환
        return ChatResponse(
            success=supervisor_response.success,
            message=supervisor_response.response.content if supervisor_response.success else supervisor_response.response,
            agent_type=supervisor_response.response.agent_type if supervisor_response.success else "unknown",
            metadata=supervisor_response.response.metadata if supervisor_response.success else {}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}")

@router.get("/agents")
async def get_agents():
    """등록된 모든 에이전트 정보를 반환합니다."""
    try:
        agents = agent_registry.get_agent_descriptions()
        return {
            "agents": agents,
            "total_count": len(agents),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"에이전트 정보 조회 중 오류: {str(e)}")

@router.get("/health")
async def health_check():
    """시스템 상태 확인"""
    try:
        # 기본 상태 확인
        status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "3.0.0",
            "framework": "LangGraph"
        }
        
        # 에이전트 상태 확인
        agents = agent_registry.get_agent_descriptions()
        status["agents"] = {
            "total": len(agents),
            "available": list(agents.keys())
        }
        
        # 데이터 수집 상태 확인
        status["data_collection"] = {
            "active_users": list(data_collection_managers.keys()),
            "total_managers": len(data_collection_managers)
        }
        
        return status
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# 데이터 수집 제어 엔드포인트들

@router.post("/data-collection/start/{user_id}")
async def start_data_collection(user_id: int):
    """특정 사용자의 데이터 수집을 시작합니다."""
    try:
        start_user_data_collection(user_id)
        return {
            "success": True,
            "message": f"사용자 {user_id}의 데이터 수집이 시작되었습니다.",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 수집 시작 오류: {str(e)}")

@router.post("/data-collection/stop/{user_id}")
async def stop_data_collection(user_id: int):
    """특정 사용자의 데이터 수집을 중지합니다."""
    try:
        stop_user_data_collection(user_id)
        return {
            "success": True,
            "message": f"사용자 {user_id}의 데이터 수집이 중지되었습니다.",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 수집 중지 오류: {str(e)}")

@router.post("/data-collection/stop-all")
async def stop_all_data_collection_endpoint():
    """모든 사용자의 데이터 수집을 중지합니다."""
    try:
        stop_all_data_collection()
        return {
            "success": True,
            "message": "모든 사용자의 데이터 수집이 중지되었습니다.",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 수집 중지 오류: {str(e)}")

@router.get("/data-collection/status")
async def get_data_collection_status():
    """데이터 수집 상태를 확인합니다."""
    try:
        active_users = list(data_collection_managers.keys())
        managers_info = {}
        
        for user_id, manager in data_collection_managers.items():
            managers_info[user_id] = {
                "running": manager.running,
                "thread_alive": manager.collection_thread.is_alive() if manager.collection_thread else False
            }
        
        return {
            "active_users": active_users,
            "total_managers": len(data_collection_managers),
            "managers_info": managers_info,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 조회 오류: {str(e)}")

@router.get("/data-collection/stats")
async def get_data_collection_stats():
    """데이터 수집 통계를 확인합니다."""
    try:
        from database.sqlite_meta import SQLiteMeta
        
        sqlite_meta = SQLiteMeta()
        
        # 각 테이블의 레코드 수 조회
        stats = sqlite_meta.get_collection_stats()
        file_count = stats['collected_files']
        browser_count = stats['collected_browser_history']
        app_count = stats['collected_apps']
        screen_count = stats['collected_screenshots']
        
        # 최근 24시간 내 데이터 수
        from datetime import datetime, timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        # 전체 데이터의 약 1/7을 최근 24시간으로 추정
        recent_files = file_count // 7
        recent_browser = browser_count // 7
        recent_apps = app_count // 7
        recent_screens = screen_count // 7
        
        return {
            "total_records": {
                "files": file_count,
                "browser_history": browser_count,
                "active_applications": app_count,
                "screen_activities": screen_count
            },
            "last_24_hours": {
                "files": recent_files,
                "browser_history": recent_browser,
                "active_applications": recent_apps,
                "screen_activities": recent_screens
            },
            "active_collectors": len(data_collection_managers),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 오류: {str(e)}") 