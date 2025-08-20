import os
import yaml
from typing import List, Dict, Any, Union, Optional
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
)
import logging

logger = logging.getLogger(__name__)

class QdrantManager:
    """Qdrant 벡터 데이터베이스 관리 클래스"""
    
    def __init__(self, config_path: str = "configs.yaml"):
        self.config = self._load_config(config_path)
        self.client = QdrantClient(url=self.config['qdrant']['url'])
        self.ensure_collections()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                # 기본 설정
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
                    }
                }
        except Exception as e:
            logger.error(f"설정 로드 오류: {e}")
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
                }
            }
    
    def ensure_collections(self):
        """컬렉션 생성/확인"""
        collections = self.config['qdrant']['collections']
        dim = self.config['embedding']['dim']
        
        for collection_name in collections.values():
            try:
                # 컬렉션 존재 확인
                collection_info = self.client.get_collection(collection_name)
                logger.info(f"컬렉션 {collection_name} 이미 존재")
            except Exception:
                # 컬렉션 생성
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=dim,
                        distance=Distance.COSINE,
                        hnsw_config={
                            'm': 32,
                            'ef_construct': 128
                        }
                    )
                )
                logger.info(f"컬렉션 {collection_name} 생성됨")
    
    def upsert_vectors(self, collection: str, ids: List[Union[str, int]], 
                      vectors: Union[List[List[float]], np.ndarray], 
                      payloads: List[Dict[str, Any]]) -> bool:
        """벡터 업서트"""
        try:
            # numpy 배열을 리스트로 변환
            if isinstance(vectors, np.ndarray):
                vectors = vectors.tolist()
            
            # PointStruct 리스트 생성
            points = []
            for i, (id_val, vector, payload) in enumerate(zip(ids, vectors, payloads)):
                point = PointStruct(
                    id=id_val,
                    vector=vector,
                    payload=payload
                )
                points.append(point)
            
            # 배치 크기로 나누어 업서트
            batch_size = self.config['embedding']['batch_size']
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=collection,
                    points=batch
                )
            
            logger.info(f"컬렉션 {collection}에 {len(points)}개 벡터 업서트 완료")
            return True
            
        except Exception as e:
            logger.error(f"벡터 업서트 오류: {e}")
            return False
    
    def ann_search(self, collection: str, query_vec: Union[List[float], np.ndarray], 
                  limit: int, flt: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """ANN 검색"""
        try:
            # numpy 배열을 리스트로 변환
            if isinstance(query_vec, np.ndarray):
                query_vec = query_vec.tolist()
            
            # 필터 변환
            search_filter = None
            if flt:
                search_filter = self._convert_filter(flt)
            
            # 검색 실행
            search_result = self.client.search(
                collection_name=collection,
                query_vector=query_vec,
                limit=limit,
                query_filter=search_filter,
                with_payload=True,
                with_vectors=False,
                score_threshold=0.0
            )
            
            # 결과 변환
            results = []
            for hit in search_result:
                results.append({
                    'id': hit.id,
                    'score': hit.score,
                    'payload': hit.payload
                })
            
            return results
            
        except Exception as e:
            logger.error(f"ANN 검색 오류: {e}")
            return []
    
    def _convert_filter(self, flt: Dict[str, Any]) -> Filter:
        """필터 딕셔너리를 Qdrant Filter로 변환"""
        conditions = []
        
        if 'must' in flt:
            for condition in flt['must']:
                if 'key' in condition and 'match' in condition:
                    field_condition = FieldCondition(
                        key=condition['key'],
                        match=MatchValue(value=condition['match']['value'])
                    )
                    conditions.append(field_condition)
        
        return Filter(must=conditions) if conditions else None
    
    def delete_vectors(self, collection: str, ids: List[Union[str, int]]) -> bool:
        """벡터 삭제"""
        try:
            self.client.delete(
                collection_name=collection,
                points_selector=ids
            )
            logger.info(f"컬렉션 {collection}에서 {len(ids)}개 벡터 삭제 완료")
            return True
        except Exception as e:
            logger.error(f"벡터 삭제 오류: {e}")
            return False
    
    def get_collection_info(self, collection: str) -> Optional[Dict[str, Any]]:
        """컬렉션 정보 조회"""
        try:
            info = self.client.get_collection(collection)
            return {
                'name': info.name,
                'vectors_count': info.vectors_count,
                'points_count': info.points_count,
                'segments_count': info.segments_count,
                'config': {
                    'vector_size': info.config.params.vectors.size,
                    'distance': info.config.params.vectors.distance.value
                }
            }
        except Exception as e:
            logger.error(f"컬렉션 정보 조회 오류: {e}")
            return None
