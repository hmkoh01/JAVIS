import os
import yaml
from typing import List, Dict, Any, Optional
import numpy as np
import logging
from .models.colqwen2_embedder import ColQwen2Embedder
from database.repository import Repository

logger = logging.getLogger(__name__)

def retrieve_local(question: str, repo: Repository, embedder: ColQwen2Embedder, 
                  k_candidates: int = 40, k_final: int = 10, 
                  filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """로컬 RAG 검색"""
    try:
        # 1. 질의 벡터 생성
        query_vectors = embedder.encode_query(question)
        if query_vectors is None or query_vectors.size == 0:
            logger.error("질의 벡터 생성 실패")
            return []
        
        # 2. 각 소스에서 후보 검색
        all_candidates = []
        
        # 파일 소스 검색 (텍스트 + 이미지)
        file_candidates = repo.search_multimodal(
            query_vectors=query_vectors,
            source="file",
            limit=k_candidates,
            filters=filters
        )
        all_candidates.extend(file_candidates)
        
        # 웹 히스토리 검색
        web_candidates = repo.search_multimodal(
            query_vectors=query_vectors,
            source="web",
            limit=k_candidates,
            filters=filters
        )
        all_candidates.extend(web_candidates)
        
        # 스크린샷 검색
        screen_candidates = repo.search_multimodal(
            query_vectors=query_vectors,
            source="screen",
            limit=k_candidates,
            filters=filters
        )
        all_candidates.extend(screen_candidates)
        
        if not all_candidates:
            logger.warning("검색 결과가 없습니다")
            return []
        
        # 3. MaxSim 점수 계산 (ColBERT 스타일)
        scored_candidates = []
        for candidate in all_candidates:
            # 간단한 코사인 유사도 사용 (실제로는 더 복잡한 MaxSim 구현 가능)
            score = candidate.score
            scored_candidates.append({
                'doc_id': candidate.doc_id,
                'score': score,
                'source': candidate.source,
                'page': candidate.page,
                'bbox': candidate.bbox,
                'path': candidate.path,
                'url': candidate.url,
                'timestamp': candidate.timestamp,
                'snippet': candidate.snippet
            })
        
        # 4. 점수로 정렬하고 상위 k_final 반환
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        top_candidates = scored_candidates[:k_final]
        
        logger.info(f"검색 완료: {len(top_candidates)}개 결과 반환")
        return top_candidates
        
    except Exception as e:
        logger.error(f"로컬 검색 오류: {e}")
        return []

def maxsim_score(query_vecs: np.ndarray, doc_vecs: np.ndarray) -> float:
    """ColBERT 스타일 MaxSim 점수 계산"""
    try:
        if query_vecs.size == 0 or doc_vecs.size == 0:
            return 0.0
        
        # 코사인 유사도 계산
        query_norm = np.linalg.norm(query_vecs, axis=1, keepdims=True)
        doc_norm = np.linalg.norm(doc_vecs, axis=1, keepdims=True)
        
        # 정규화
        query_vecs_norm = query_vecs / (query_norm + 1e-8)
        doc_vecs_norm = doc_vecs / (doc_norm + 1e-8)
        
        # 유사도 행렬 계산
        similarity_matrix = np.dot(query_vecs_norm, doc_vecs_norm.T)
        
        # MaxSim: 각 쿼리 벡터에 대해 문서 벡터들과의 최대 유사도 구하기
        max_similarities = np.max(similarity_matrix, axis=1)
        
        # 모든 쿼리 벡터의 최대 유사도 합
        total_score = np.sum(max_similarities)
        
        return float(total_score)
        
    except Exception as e:
        logger.error(f"MaxSim 점수 계산 오류: {e}")
        return 0.0
