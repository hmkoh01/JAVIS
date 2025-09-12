import os
import yaml
import logging
from typing import Dict, Any, Optional
import threading

# Try to import torch for CUDA availability check
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from .models.colqwen2_embedder import ColQwen2Embedder
from .retrievers import retrieve_local
from .rerankers import monovlm_rerank, simple_rerank_by_score
from .answerer import compose_answer, call_vlm_for_answer, images_to_base64
from database.repository import Repository

logger = logging.getLogger(__name__)

# 싱글톤 인스턴스들
_repository = None
_embedder = None
_config = None
_lock = threading.Lock()

def _load_config(config_path: str = "configs.yaml") -> Dict[str, Any]:
    """설정 로드"""
    try:
        if os.path.exists(config_path):
            logger.info(f"설정 파일 로드: {config_path}")
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            return {
                'qdrant': {
                    'url': 'http://localhost:6333',
                    'collections': {
                        'text': 'text_chunks',
                        'image': 'image_patches',
                        'screen': 'screens_patches'
                    }
                },
                'embedding': {
                    'dim': 128,
                    'batch_size': 32
                },
                'retrieval': {
                    'k_candidates': 40,
                    'k_final': 10
                },
                'vlm': {
                    'enabled': False
                }
            }
    except Exception as e:
        logger.error(f"설정 로드 오류: {e}")
        return {}

def _get_repository() -> Repository:
    """Repository 싱글톤 인스턴스 반환"""
    global _repository
    if _repository is None:
        with _lock:
            if _repository is None:
                _repository = Repository()
    return _repository

def _get_embedder() -> ColQwen2Embedder:
    """임베더 싱글톤 인스턴스 반환"""
    global _embedder
    if _embedder is None:
        with _lock:
            if _embedder is None:
                device = "cuda" if _is_cuda_available() else "cpu"
                _embedder = ColQwen2Embedder(device=device)
    return _embedder

def _get_config() -> Dict[str, Any]:
    """설정 싱글톤 인스턴스 반환"""
    global _config
    if _config is None:
        with _lock:
            if _config is None:
                _config = _load_config()
    return _config

def _is_cuda_available() -> bool:
    """CUDA 사용 가능 여부 확인"""
    if TORCH_AVAILABLE:
        return torch.cuda.is_available()
    return False

def process(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ReAct 에이전트 메인 처리 함수
    
    입력 state: {
        "question": str,
        "user_id": str|None,
        "filters": dict|None,
        "time_hint": tuple[int,int]|None,
        ...
    }
    
    반환 state: 입력에 아래 키 추가
        - "answer": str
        - "evidence": List[dict]
    """
    try:
        # 입력 검증
        question = state.get("question", "")
        if not question:
            return {
                **state,
                "answer": "질문이 제공되지 않았습니다.",
                "evidence": []
            }
        
        # 리소스 로드
        repo = _get_repository()
        embedder = _get_embedder()
        config = _get_config()
        
        # 검색 파라미터 설정
        k_candidates = config.get('retrieval', {}).get('k_candidates', 40)
        k_final = config.get('retrieval', {}).get('k_final', 10)
        
        # 필터 설정 (user_id 필터 제거)
        filters = state.get("filters", {})
        # user_id 필터를 제거하여 모든 데이터에서 검색
        
        # 시간 범위 설정
        time_range = state.get("time_hint")
        
        # 1. 로컬 검색
        logger.info(f"질문 검색 시작: {question}")
        candidates = retrieve_local(
            question=question,
            repo=repo,
            embedder=embedder,
            k_candidates=k_candidates,
            k_final=k_candidates,  # 재랭킹 전에는 더 많은 후보
            filters=filters
        )
        
        if not candidates:
            return {
                **state,
                "answer": "관련 정보를 찾을 수 없습니다.",
                "evidence": []
            }
        
        # 2. 이미지가 있는 후보들 확인
        image_candidates = []
        for candidate in candidates:
            if candidate.get('source') in ['file', 'screen'] and candidate.get('path'):
                path = candidate.get('path')
                # 파일 확장자 확인하여 실제 이미지 파일만 선별
                if path:
                    file_ext = os.path.splitext(path)[1].lower()
                    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.ico'}
                    if file_ext in image_extensions:
                        image_candidates.append(candidate)
        
        # 3. MonoVLM 재랭킹 (이미지가 있는 경우)
        if image_candidates:
            try:
                # 이미지 로드 및 base64 변환
                images = []
                image_paths = []
                for candidate in image_candidates:
                    path = candidate.get('path')
                    if path and os.path.exists(path):
                        # 파일 확장자 확인하여 이미지 파일만 처리
                        file_ext = os.path.splitext(path)[1].lower()
                        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.ico'}
                        
                        if file_ext in image_extensions:
                            try:
                                from PIL import Image
                                img = Image.open(path)
                                images.append(img)
                                image_paths.append(path)
                            except Exception as e:
                                logger.warning(f"이미지 로드 실패 {path}: {e}")
                        else:
                            logger.debug(f"이미지가 아닌 파일 건너뜀: {path} (확장자: {file_ext})")
                
                if images:
                    # base64 변환
                    images_b64 = images_to_base64(images)
                    
                    # MonoVLM 재랭킹
                    reranked_indices = monovlm_rerank(question, images_b64, k_final)
                    
                    # 재랭킹된 결과로 후보 재구성
                    reranked_candidates = []
                    for idx in reranked_indices:
                        if idx < len(image_candidates):
                            reranked_candidates.append(image_candidates[idx])
                    
                    # 나머지 후보들 추가
                    remaining_candidates = [c for c in candidates if c not in image_candidates]
                    reranked_candidates.extend(remaining_candidates[:k_final - len(reranked_candidates)])
                    
                    candidates = reranked_candidates[:k_final]
                    logger.info(f"MonoVLM 재랭킹 완료: {len(candidates)}개 결과")
                
            except Exception as e:
                logger.error(f"MonoVLM 재랭킹 오류: {e}")
                # 재랭킹 실패 시 기본 정렬 사용
                candidates = simple_rerank_by_score(candidates, k_final)
        else:
            # 이미지가 없으면 기본 정렬
            candidates = simple_rerank_by_score(candidates, k_final)
        
        # 4. VLM 응답 생성 시도 (이미지가 있는 경우)
        vlm_answer = None
        if image_candidates and config.get('vlm', {}).get('enabled', False):
            try:
                # 상위 이미지들 수집
                top_images = []
                for candidate in candidates[:3]:  # 상위 3개만
                    if candidate.get('path') and os.path.exists(candidate.get('path')):
                        try:
                            from PIL import Image
                            img = Image.open(candidate['path'])
                            top_images.append(img)
                        except Exception as e:
                            logger.warning(f"VLM용 이미지 로드 실패: {e}")
                
                if top_images:
                    vlm_answer = call_vlm_for_answer(question, top_images)
                    if vlm_answer:
                        logger.info("VLM 응답 생성 완료")
                
            except Exception as e:
                logger.error(f"VLM 응답 생성 오류: {e}")
        
        # 5. 최종 응답 생성
        if vlm_answer:
            answer = vlm_answer
        else:
            answer = compose_answer(question, candidates)
        
        # 6. 결과 반환
        return {
            **state,
            "answer": answer,
            "evidence": candidates
        }
        
    except Exception as e:
        logger.error(f"ReAct 에이전트 처리 오류: {e}")
        return {
            **state,
            "answer": f"처리 중 오류가 발생했습니다: {str(e)}",
            "evidence": []
        }
