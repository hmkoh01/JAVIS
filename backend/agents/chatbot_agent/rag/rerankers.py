import os
import yaml
from typing import List, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)

def maxsim_score(query_vecs: np.ndarray, doc_vecs: np.ndarray) -> float:
    """ColBERT 방식 MaxSim 점수 계산"""
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

def monovlm_rerank(question: str, images_b64: List[str], top_k: int) -> List[int]:
    """MonoVLM을 사용한 재랭킹"""
    try:
        # rerankers 라이브러리 사용 시도
        try:
            from rerankers import Reranker
            ranker = Reranker("monovlm", device="cuda" if _is_cuda_available() else "cpu")
            
            # 이미지가 있는 항목만 필터링
            valid_images = []
            valid_indices = []
            
            for i, img_b64 in enumerate(images_b64):
                if img_b64 and img_b64.strip():
                    valid_images.append(img_b64)
                    valid_indices.append(i)
            
            if not valid_images:
                logger.warning("재랭킹할 이미지가 없습니다")
                return list(range(min(top_k, len(images_b64))))
            
            # 재랭킹 실행
            results = ranker.rank(question, valid_images)
            
            # 결과를 원래 인덱스로 변환
            reranked_indices = []
            for doc in results.top_k(top_k):
                if hasattr(doc, 'doc_id') and doc.doc_id < len(valid_indices):
                    reranked_indices.append(valid_indices[doc.doc_id])
            
            # 부족한 경우 나머지 인덱스 추가
            while len(reranked_indices) < top_k and len(reranked_indices) < len(images_b64):
                for i in range(len(images_b64)):
                    if i not in reranked_indices:
                        reranked_indices.append(i)
                        break
            
            return reranked_indices[:top_k]
            
        except ImportError:
            logger.warning("rerankers 라이브러리가 설치되지 않았습니다. 기본 순서를 사용합니다.")
            return list(range(min(top_k, len(images_b64))))
            
        except Exception as e:
            logger.error(f"MonoVLM 재랭킹 오류: {e}")
            return list(range(min(top_k, len(images_b64))))
            
    except Exception as e:
        logger.error(f"재랭킹 오류: {e}")
        return list(range(min(top_k, len(images_b64))))

def _is_cuda_available() -> bool:
    """CUDA 사용 가능 여부 확인"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

def simple_rerank_by_score(candidates: List[dict], top_k: int) -> List[dict]:
    """점수 기반 간단한 재랭킹"""
    try:
        # 점수로 정렬
        sorted_candidates = sorted(candidates, key=lambda x: x.get('score', 0), reverse=True)
        return sorted_candidates[:top_k]
    except Exception as e:
        logger.error(f"간단 재랭킹 오류: {e}")
        return candidates[:top_k]
