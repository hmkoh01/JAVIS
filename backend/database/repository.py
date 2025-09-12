import os
import yaml
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import logging
from .qdrant_client import QdrantManager
from .sqlite_meta import SQLiteMeta

logger = logging.getLogger(__name__)

@dataclass
class Hit:
    """검색 결과 히트"""
    doc_id: str
    score: float
    source: str  # "file" | "web" | "screen"
    page: Optional[int] = None
    bbox: Optional[List[int]] = None
    path: Optional[str] = None
    url: Optional[str] = None
    timestamp: Optional[int] = None
    snippet: Optional[str] = None

class Repository:
    """Qdrant + SQLite 통합 Repository"""
    
    def __init__(self, config_path: str = "./backend/configs.yaml"):
        self.config = self._load_config(config_path)
        self.qdrant = QdrantManager(config_path)
        self.sqlite = SQLiteMeta(self.config.get('sqlite', {}).get('path', './sqlite/meta.db'))
        self.collections = self.config['qdrant']['collections']
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            if os.path.exists(config_path):
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
                    'sqlite': {
                        'path': './sqlite/meta.db'
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
                'sqlite': {
                    'path': './sqlite/meta.db'
                }
            }
    
    def index_text_chunks(self, doc_id: str, vectors: np.ndarray, metas: List[Dict[str, Any]]) -> bool:
        """텍스트 청크 인덱싱"""
        try:
            collection = self.collections['text']
            ids = [f"{doc_id}_{i}" for i in range(len(vectors))]
            
            # 메타데이터에 기본 정보 추가
            for i, meta in enumerate(metas):
                meta.update({
                    'source': 'file',
                    'doc_id': doc_id,
                    'chunk_id': i
                })
            
            return self.qdrant.upsert_vectors(collection, ids, vectors, metas)
        except Exception as e:
            logger.error(f"텍스트 청크 인덱싱 오류: {e}")
            return False
    
    def index_image_patches(self, doc_id: str, vectors: np.ndarray, metas: List[Dict[str, Any]]) -> bool:
        """이미지 패치 인덱싱"""
        try:
            collection = self.collections['image']
            ids = [f"{doc_id}_{i}" for i in range(len(vectors))]
            
            # 메타데이터에 기본 정보 추가
            for i, meta in enumerate(metas):
                meta.update({
                    'source': 'file',
                    'doc_id': doc_id,
                    'patch_id': i
                })
            
            return self.qdrant.upsert_vectors(collection, ids, vectors, metas)
        except Exception as e:
            logger.error(f"이미지 패치 인덱싱 오류: {e}")
            return False
    
    def index_screen_patches(self, doc_id: str, vectors: np.ndarray, metas: List[Dict[str, Any]]) -> bool:
        """스크린샷 패치 인덱싱"""
        try:
            collection = self.collections['screen']
            ids = [f"{doc_id}_{i}" for i in range(len(vectors))]
            
            # 메타데이터에 기본 정보 추가
            for i, meta in enumerate(metas):
                meta.update({
                    'source': 'screen',
                    'doc_id': doc_id,
                    'patch_id': i
                })
            
            return self.qdrant.upsert_vectors(collection, ids, vectors, metas)
        except Exception as e:
            logger.error(f"스크린샷 패치 인덱싱 오류: {e}")
            return False
    
    def search_multimodal(self, query_vectors: np.ndarray, source: Optional[str] = None, 
                         limit: int = 10, time_range: Optional[Tuple[int, int]] = None, 
                         filters: Optional[Dict[str, Any]] = None) -> List[Hit]:
        """멀티모달 검색"""
        try:
            all_hits = []
            
            # 검색할 컬렉션 결정
            collections_to_search = []
            if source is None or source == "file":
                collections_to_search.extend([
                    (self.collections['text'], 'file'),
                    (self.collections['image'], 'file')
                ])
            if source is None or source == "web":
                collections_to_search.append((self.collections['text'], 'web'))
            if source is None or source == "screen":
                collections_to_search.append((self.collections['screen'], 'screen'))
            
            # 각 컬렉션에서 검색
            for collection_name, source_type in collections_to_search:
                # 필터 구성
                search_filter = filters.copy() if filters else {}
                if source_type:
                    if 'must' not in search_filter:
                        search_filter['must'] = []
                    search_filter['must'].append({
                        'key': 'source',
                        'match': {'value': source_type}
                    })
                
                # 시간 범위 필터 추가
                if time_range:
                    start_ts, end_ts = time_range
                    if 'must' not in search_filter:
                        search_filter['must'] = []
                    search_filter['must'].extend([
                        {
                            'key': 'timestamp',
                            'range': {'gte': start_ts}
                        },
                        {
                            'key': 'timestamp',
                            'range': {'lte': end_ts}
                        }
                    ])
                
                # 검색 실행
                results = self.qdrant.ann_search(collection_name, query_vectors, limit, search_filter)
                
                # Hit 객체로 변환
                for result in results:
                    hit = self._raw_hit_to_hit(result, source_type)
                    if hit:
                        all_hits.append(hit)
            
            # 점수로 정렬
            all_hits.sort(key=lambda x: x.score, reverse=True)
            
            return all_hits[:limit]
            
        except Exception as e:
            logger.error(f"멀티모달 검색 오류: {e}")
            return []
    
    def _raw_hit_to_hit(self, raw_hit: Dict[str, Any], source_type: str) -> Optional[Hit]:
        """원시 히트를 Hit 객체로 변환"""
        try:
            payload = raw_hit['payload']
            
            hit = Hit(
                doc_id=payload.get('doc_id', ''),
                score=raw_hit['score'],
                source=source_type,
                page=payload.get('page'),
                bbox=payload.get('bbox'),
                path=payload.get('path'),
                url=payload.get('url'),
                timestamp=payload.get('timestamp'),
                snippet=payload.get('snippet')
            )
            
            return hit
        except Exception as e:
            logger.error(f"히트 변환 오류: {e}")
            return None
    
    def resolve_metadata(self, raw_hit: Dict[str, Any]) -> Optional[Hit]:
        """SQLite에서 메타데이터를 조합하여 Hit 완성"""
        try:
            payload = raw_hit['payload']
            doc_id = payload.get('doc_id', '')
            source = payload.get('source', '')
            
            # SQLite에서 추가 정보 조회
            if source == 'file':
                file_info = self.sqlite.get_file(doc_id)
                if file_info:
                    return Hit(
                        doc_id=doc_id,
                        score=raw_hit['score'],
                        source=source,
                        page=payload.get('page'),
                        bbox=payload.get('bbox'),
                        path=file_info.get('path'),
                        url=None,
                        timestamp=file_info.get('updated_at'),
                        snippet=file_info.get('preview')
                    )
            elif source == 'web':
                # 웹 히스토리에서 URL 정보 조회
                return Hit(
                    doc_id=doc_id,
                    score=raw_hit['score'],
                    source=source,
                    page=payload.get('page'),
                    bbox=payload.get('bbox'),
                    path=None,
                    url=payload.get('url'),
                    timestamp=payload.get('timestamp'),
                    snippet=payload.get('snippet')
                )
            elif source == 'screen':
                # 스크린샷 정보 조회
                screenshots = self.sqlite.recent_screenshots(limit=1)
                if screenshots:
                    screenshot = screenshots[0]
                    return Hit(
                        doc_id=doc_id,
                        score=raw_hit['score'],
                        source=source,
                        page=payload.get('page'),
                        bbox=payload.get('bbox'),
                        path=screenshot.get('path'),
                        url=None,
                        timestamp=screenshot.get('captured_at'),
                        snippet=screenshot.get('gemini_desc')
                    )
            
            # 기본 Hit 객체 반환
            return self._raw_hit_to_hit(raw_hit, source)
            
        except Exception as e:
            logger.error(f"메타데이터 해석 오류: {e}")
            return None
    
    # SQLite 메타데이터 메서드들 (위임)
    def upsert_file(self, doc_id: str, path: str, **kwargs) -> bool:
        return self.sqlite.upsert_file(doc_id, path, **kwargs)
    
    def insert_web_history(self, url: str, **kwargs) -> bool:
        return self.sqlite.insert_web_history(url, **kwargs)
    
    def insert_app(self, name: str, **kwargs) -> bool:
        return self.sqlite.insert_app(name, **kwargs)
    
    def insert_screenshot(self, doc_id: str, path: str, **kwargs) -> bool:
        return self.sqlite.insert_screenshot(doc_id, path, **kwargs)
    
    def upsert_interest(self, user_id: str, topic: str, score: float = 1.0) -> bool:
        return self.sqlite.upsert_interest(user_id, topic, score)
    
    def get_file(self, doc_id: str):
        return self.sqlite.get_file(doc_id)
    
    def recent_web_history(self, limit: int = 100, since_ts: int = None):
        return self.sqlite.recent_web_history(limit, since_ts)
    
    def recent_apps(self, limit: int = 100, since_ts: int = None):
        return self.sqlite.recent_apps(limit, since_ts)
    
    def recent_screenshots(self, limit: int = 100, since_ts: int = None):
        return self.sqlite.recent_screenshots(limit, since_ts)
    
    def top_interests(self, user_id: str, limit: int = 10):
        return self.sqlite.top_interests(user_id, limit)
    
    def find_file_by_path(self, path: str):
        return self.sqlite.find_file_by_path(path)
    
    def index_text_chunks_batch(self, doc_ids: List[str], vectors: np.ndarray, metas: List[Dict[str, Any]], batch_size: int = 50) -> bool:
        """텍스트 청크 배치 인덱싱"""
        try:
            collection = self.collections['text']
            
            # 배치로 나누어 처리
            for i in range(0, len(vectors), batch_size):
                batch_vectors = vectors[i:i + batch_size]
                batch_metas = metas[i:i + batch_size]
                batch_doc_ids = doc_ids[i:i + batch_size]
                
                ids = [f"{doc_id}_{j}" for j, doc_id in enumerate(batch_doc_ids)]
                
                # 메타데이터에 기본 정보 추가
                for j, meta in enumerate(batch_metas):
                    meta.update({
                        'source': 'file',
                        'doc_id': batch_doc_ids[j],
                        'chunk_id': j
                    })
                
                success = self.qdrant.upsert_vectors(collection, ids, batch_vectors, batch_metas)
                if not success:
                    print(f"배치 {i//batch_size + 1} 인덱싱 실패")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"텍스트 청크 배치 인덱싱 오류: {e}")
            return False

    def index_image_patches_batch(self, doc_ids: List[str], vectors: np.ndarray, metas: List[Dict[str, Any]], batch_size: int = 50) -> bool:
        """이미지 패치 배치 인덱싱"""
        try:
            collection = self.collections['image']
            
            # 배치로 나누어 처리
            for i in range(0, len(vectors), batch_size):
                batch_vectors = vectors[i:i + batch_size]
                batch_metas = metas[i:i + batch_size]
                batch_doc_ids = doc_ids[i:i + batch_size]
                
                ids = [f"{doc_id}_{j}" for j, doc_id in enumerate(batch_doc_ids)]
                
                # 메타데이터에 기본 정보 추가
                for j, meta in enumerate(batch_metas):
                    meta.update({
                        'source': 'file',
                        'doc_id': batch_doc_ids[j],
                        'patch_id': j
                    })
                
                success = self.qdrant.upsert_vectors(collection, ids, batch_vectors, batch_metas)
                if not success:
                    print(f"배치 {i//batch_size + 1} 인덱싱 실패")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"이미지 패치 배치 인덱싱 오류: {e}")
            return False