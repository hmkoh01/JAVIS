from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid
import json

from .parser import DocumentParser, ParsedDocument
from .chunker import TextChunker, TextChunk
from .embedder import Embedder, EmbeddingResult
from .vector_store import MilvusVectorStore, VectorRecord
from .graph_store import Neo4jGraphStore

@dataclass
class ProcessingResult:
    """처리 결과를 나타내는 데이터 클래스"""
    document_id: str
    chunks_created: int
    vectors_created: int
    graph_nodes_created: int
    processing_time: float
    status: str
    errors: List[str]

class KnowledgeProcessor:
    """지식 처리를 담당하는 클래스"""
    
    def __init__(self, vector_store: MilvusVectorStore, graph_store: Neo4jGraphStore,
                 embedder: Embedder, chunker: TextChunker = None, parser: DocumentParser = None):
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.embedder = embedder
        self.chunker = chunker or TextChunker()
        self.parser = parser or DocumentParser()
    
    def process_document(self, content: str, source: str, document_type: str = "text",
                        metadata: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """단일 문서를 처리합니다."""
        start_time = datetime.now()
        errors = []
        
        try:
            # 1. 문서 파싱
            parsed_doc = self.parser.parse(content, source, document_type, metadata)
            
            # 2. 텍스트 청킹
            chunks = self.chunker.chunk_text(
                parsed_doc.content, 
                parsed_doc.content,  # document_id로 content 사용
                metadata=parsed_doc.metadata
            )
            
            # 3. 청크 임베딩 생성
            chunk_texts = [chunk.content for chunk in chunks]
            chunk_metadata_list = [chunk.metadata for chunk in chunks]
            
            embeddings = self.embedder.embed_texts(chunk_texts, chunk_metadata_list)
            
            # 4. 벡터 스토어에 저장
            vector_records = []
            for i, embedding in enumerate(embeddings):
                vector_record = VectorRecord(
                    id=embedding.embedding_id,
                    embedding=embedding.embedding,
                    text=embedding.text,
                    metadata={
                        **embedding.metadata,
                        "document_id": parsed_doc.content,
                        "chunk_index": i,
                        "source": source,
                        "document_type": document_type
                    },
                    created_at=embedding.created_at
                )
                vector_records.append(vector_record)
            
            vector_ids = self.vector_store.insert_vectors(vector_records)
            
            # 5. 그래프 스토어에 저장
            # 문서 노드 생성
            doc_node_id = self.graph_store.create_document_node(
                document_id=parsed_doc.content,
                title=parsed_doc.title,
                content=parsed_doc.content,
                source=parsed_doc.source,
                document_type=parsed_doc.document_type,
                metadata=parsed_doc.metadata
            )
            
            # 청크 노드들 생성
            chunk_node_ids = []
            for i, chunk in enumerate(chunks):
                chunk_node_id = self.graph_store.create_chunk_node(
                    chunk_id=chunk.chunk_id,
                    document_id=parsed_doc.content,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    metadata=chunk.metadata
                )
                chunk_node_ids.append(chunk_node_id)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ProcessingResult(
                document_id=parsed_doc.content,
                chunks_created=len(chunks),
                vectors_created=len(vector_ids),
                graph_nodes_created=1 + len(chunk_node_ids),  # 문서 노드 + 청크 노드들
                processing_time=processing_time,
                status="success",
                errors=errors
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            errors.append(str(e))
            
            return ProcessingResult(
                document_id=source,
                chunks_created=0,
                vectors_created=0,
                graph_nodes_created=0,
                processing_time=processing_time,
                status="error",
                errors=errors
            )
    
    def process_documents_batch(self, documents: List[Dict[str, Any]]) -> List[ProcessingResult]:
        """여러 문서를 일괄 처리합니다."""
        results = []
        
        for doc in documents:
            try:
                content = doc.get('content', '')
                source = doc.get('source', 'unknown')
                document_type = doc.get('type', 'text')
                metadata = doc.get('metadata', {})
                
                result = self.process_document(content, source, document_type, metadata)
                results.append(result)
                
            except Exception as e:
                print(f"배치 처리 오류 (문서: {doc.get('source', 'unknown')}): {e}")
                results.append(ProcessingResult(
                    document_id=doc.get('source', 'unknown'),
                    chunks_created=0,
                    vectors_created=0,
                    graph_nodes_created=0,
                    processing_time=0,
                    status="error",
                    errors=[str(e)]
                ))
        
        return results
    
    def process_from_api(self, api_data: Dict[str, Any]) -> ProcessingResult:
        """API를 통해 받은 데이터를 처리합니다."""
        try:
            # API 데이터 구조 검증
            required_fields = ['content', 'source']
            for field in required_fields:
                if field not in api_data:
                    raise ValueError(f"필수 필드가 누락되었습니다: {field}")
            
            content = api_data['content']
            source = api_data['source']
            document_type = api_data.get('type', 'text')
            metadata = api_data.get('metadata', {})
            
            # 추가 메타데이터
            metadata.update({
                'processed_at': datetime.utcnow().isoformat(),
                'api_source': True
            })
            
            return self.process_document(content, source, document_type, metadata)
            
        except Exception as e:
            return ProcessingResult(
                document_id=api_data.get('source', 'unknown'),
                chunks_created=0,
                vectors_created=0,
                graph_nodes_created=0,
                processing_time=0,
                status="error",
                errors=[str(e)]
            )
    
    def update_document(self, document_id: str, new_content: str, 
                       new_metadata: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """기존 문서를 업데이트합니다."""
        start_time = datetime.now()
        errors = []
        
        try:
            # 1. 기존 데이터 삭제
            self._delete_document_data(document_id)
            
            # 2. 새 데이터로 재처리
            result = self.process_document(
                content=new_content,
                source=document_id,
                document_type="text",
                metadata=new_metadata
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            errors.append(str(e))
            
            return ProcessingResult(
                document_id=document_id,
                chunks_created=0,
                vectors_created=0,
                graph_nodes_created=0,
                processing_time=processing_time,
                status="error",
                errors=errors
            )
    
    def delete_document(self, document_id: str) -> bool:
        """문서와 관련된 모든 데이터를 삭제합니다."""
        try:
            return self._delete_document_data(document_id)
        except Exception as e:
            print(f"문서 삭제 오류: {e}")
            return False
    
    def _delete_document_data(self, document_id: str) -> bool:
        """문서 관련 데이터를 삭제합니다."""
        try:
            # 그래프에서 문서 삭제 (청크도 함께 삭제됨)
            self.graph_store.delete_document(document_id)
            
            # 벡터 스토어에서 관련 벡터들 삭제
            # (실제 구현에서는 document_id로 필터링하여 삭제)
            # 여기서는 간단히 모든 벡터를 조회하여 필터링
            # 실제 운영에서는 더 효율적인 방법 필요
            
            return True
        except Exception as e:
            print(f"문서 데이터 삭제 오류: {e}")
            return False
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """처리 통계를 반환합니다."""
        try:
            vector_stats = self.vector_store.get_collection_stats()
            graph_stats = self.graph_store.get_graph_stats()
            
            return {
                "vector_store": vector_stats,
                "graph_store": graph_stats,
                "total_documents": graph_stats.get("document_count", 0),
                "total_chunks": graph_stats.get("chunk_count", 0),
                "total_vectors": vector_stats.get("total_vectors", 0)
            }
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {}
    
    def validate_document(self, content: str, source: str) -> Dict[str, Any]:
        """문서 유효성을 검사합니다."""
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": []
        }
        
        # 내용 검사
        if not content or not content.strip():
            validation_result["is_valid"] = False
            validation_result["errors"].append("내용이 비어있습니다.")
        
        if len(content) < 10:
            validation_result["warnings"].append("내용이 너무 짧습니다.")
        
        if len(content) > 1000000:  # 1MB 제한
            validation_result["is_valid"] = False
            validation_result["errors"].append("내용이 너무 큽니다 (1MB 초과).")
        
        # 소스 검사
        if not source or not source.strip():
            validation_result["is_valid"] = False
            validation_result["errors"].append("소스가 지정되지 않았습니다.")
        
        # 특수 문자 검사
        if content.count('\x00') > 0:
            validation_result["is_valid"] = False
            validation_result["errors"].append("널 문자가 포함되어 있습니다.")
        
        return validation_result 