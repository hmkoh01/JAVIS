from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from datetime import datetime
import uuid

@dataclass
class VectorRecord:
    """벡터 레코드를 나타내는 데이터 클래스"""
    id: str
    embedding: np.ndarray
    text: str
    metadata: Dict[str, Any]
    created_at: datetime

class MilvusVectorStore:
    """Milvus 벡터 데이터베이스와 상호작용하는 클래스"""
    
    def __init__(self, host: str = "localhost", port: int = 19530, 
                 collection_name: str = "knowledge_base", dimension: int = 1536):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.dimension = dimension
        self.client = None
        self.collection = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Milvus 연결을 초기화합니다."""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
            
            # Milvus 연결
            connections.connect(host=self.host, port=self.port)
            
            # 컬렉션이 존재하지 않으면 생성
            if not utility.has_collection(self.collection_name):
                self._create_collection()
            
            # 컬렉션 로드
            self.collection = Collection(self.collection_name)
            self.collection.load()
            
        except ImportError:
            raise ImportError("pymilvus가 설치되지 않았습니다. pip install pymilvus")
        except Exception as e:
            print(f"Milvus 연결 오류: {e}")
    
    def _create_collection(self):
        """Milvus 컬렉션을 생성합니다."""
        from pymilvus import Collection, FieldSchema, CollectionSchema, DataType
        
        # 필드 스키마 정의
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=50)
        ]
        
        schema = CollectionSchema(fields=fields, description="Knowledge base vector collection")
        self.collection = Collection(name=self.collection_name, schema=schema)
        
        # 인덱스 생성
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        self.collection.create_index(field_name="embedding", index_params=index_params)
    
    def insert_vectors(self, vectors: List[VectorRecord]) -> List[str]:
        """벡터들을 Milvus에 삽입합니다."""
        if not vectors:
            return []
        
        try:
            # 데이터 준비
            ids = []
            embeddings = []
            texts = []
            metadatas = []
            created_ats = []
            
            for vector in vectors:
                ids.append(vector.id)
                embeddings.append(vector.embedding.tolist())
                texts.append(vector.text)
                metadatas.append(str(vector.metadata))  # JSON 문자열로 변환
                created_ats.append(vector.created_at.isoformat())
            
            # 데이터 삽입
            data = [ids, embeddings, texts, metadatas, created_ats]
            self.collection.insert(data)
            self.collection.flush()
            
            return ids
            
        except Exception as e:
            print(f"벡터 삽입 오류: {e}")
            return []
    
    def search_vectors(self, query_embedding: np.ndarray, top_k: int = 5, 
                      filter_expr: Optional[str] = None) -> List[Tuple[VectorRecord, float]]:
        """유사한 벡터를 검색합니다."""
        try:
            # 검색 파라미터
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # 검색 실행
            results = self.collection.search(
                data=[query_embedding.tolist()],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=["id", "text", "metadata", "created_at"]
            )
            
            # 결과 변환
            vector_records = []
            for hits in results:
                for hit in hits:
                    # 메타데이터 파싱
                    metadata = eval(hit.entity.get("metadata", "{}"))
                    
                    vector_record = VectorRecord(
                        id=hit.entity.get("id"),
                        embedding=np.array(hit.embedding),
                        text=hit.entity.get("text"),
                        metadata=metadata,
                        created_at=datetime.fromisoformat(hit.entity.get("created_at"))
                    )
                    
                    vector_records.append((vector_record, hit.score))
            
            return vector_records
            
        except Exception as e:
            print(f"벡터 검색 오류: {e}")
            return []
    
    def delete_vectors(self, vector_ids: List[str]) -> bool:
        """벡터들을 삭제합니다."""
        try:
            expr = f'id in {vector_ids}'
            self.collection.delete(expr)
            self.collection.flush()
            return True
        except Exception as e:
            print(f"벡터 삭제 오류: {e}")
            return False
    
    def update_vector(self, vector_id: str, new_embedding: np.ndarray, 
                     new_text: str, new_metadata: Dict[str, Any]) -> bool:
        """벡터를 업데이트합니다."""
        try:
            # 기존 벡터 삭제
            self.delete_vectors([vector_id])
            
            # 새 벡터 삽입
            vector_record = VectorRecord(
                id=vector_id,
                embedding=new_embedding,
                text=new_text,
                metadata=new_metadata,
                created_at=datetime.utcnow()
            )
            
            self.insert_vectors([vector_record])
            return True
            
        except Exception as e:
            print(f"벡터 업데이트 오류: {e}")
            return False
    
    def get_vector_count(self) -> int:
        """컬렉션의 벡터 개수를 반환합니다."""
        try:
            return self.collection.num_entities
        except Exception as e:
            print(f"벡터 개수 조회 오류: {e}")
            return 0
    
    def get_vector_by_id(self, vector_id: str) -> Optional[VectorRecord]:
        """ID로 벡터를 조회합니다."""
        try:
            results = self.collection.query(
                expr=f'id == "{vector_id}"',
                output_fields=["id", "embedding", "text", "metadata", "created_at"]
            )
            
            if results:
                result = results[0]
                metadata = eval(result.get("metadata", "{}"))
                
                return VectorRecord(
                    id=result.get("id"),
                    embedding=np.array(result.get("embedding")),
                    text=result.get("text"),
                    metadata=metadata,
                    created_at=datetime.fromisoformat(result.get("created_at"))
                )
            
            return None
            
        except Exception as e:
            print(f"벡터 조회 오류: {e}")
            return None
    
    def create_partition(self, partition_name: str) -> bool:
        """파티션을 생성합니다."""
        try:
            self.collection.create_partition(partition_name)
            return True
        except Exception as e:
            print(f"파티션 생성 오류: {e}")
            return False
    
    def drop_partition(self, partition_name: str) -> bool:
        """파티션을 삭제합니다."""
        try:
            self.collection.drop_partition(partition_name)
            return True
        except Exception as e:
            print(f"파티션 삭제 오류: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계를 반환합니다."""
        try:
            stats = {
                "total_vectors": self.collection.num_entities,
                "collection_name": self.collection_name,
                "dimension": self.dimension
            }
            return stats
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {}
    
    def close(self):
        """연결을 종료합니다."""
        try:
            if self.collection:
                self.collection.release()
        except Exception as e:
            print(f"연결 종료 오류: {e}") 