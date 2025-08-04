from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from rag.knowledge_processor import KnowledgeProcessor
from rag.rag_engine import RAGEngine
from rag.embedder import Embedder
from rag.vector_store import MilvusVectorStore
from rag.graph_store import Neo4jGraphStore
from config.settings import settings

router = APIRouter(prefix="/rag", tags=["RAG"])

# Pydantic 모델들
class DocumentRequest(BaseModel):
    content: str
    source: str
    document_type: str = "text"
    metadata: Optional[Dict[str, Any]] = None

class DocumentResponse(BaseModel):
    document_id: str
    chunks_created: int
    vectors_created: int
    graph_nodes_created: int
    processing_time: float
    status: str
    errors: List[str]

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    search_type: str = "hybrid"  # "vector", "graph", "hybrid"

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    context: str
    metadata: Dict[str, Any]

class BatchDocumentRequest(BaseModel):
    documents: List[DocumentRequest]

class BatchDocumentResponse(BaseModel):
    results: List[DocumentResponse]
    total_processed: int
    total_success: int
    total_errors: int

# 전역 RAG 컴포넌트들
_embedder = None
_vector_store = None
_graph_store = None
_knowledge_processor = None
_rag_engine = None

def get_rag_components():
    """RAG 컴포넌트들을 초기화하고 반환합니다."""
    global _embedder, _vector_store, _graph_store, _knowledge_processor, _rag_engine
    
    if _embedder is None:
        _embedder = Embedder(
            openai_api_key=settings.OPENAI_API_KEY,
            ollama_base_url=settings.OLLAMA_BASE_URL,
            ollama_model=settings.OLLAMA_MODEL
        )
    
    if _vector_store is None:
        _vector_store = MilvusVectorStore(
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
            collection_name=settings.MILVUS_COLLECTION,
            dimension=_embedder.get_embedding_dimension()
        )
    
    if _graph_store is None:
        _graph_store = Neo4jGraphStore(
            uri=settings.NEO4J_URI,
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD
        )
    
    if _knowledge_processor is None:
        _knowledge_processor = KnowledgeProcessor(
            vector_store=_vector_store,
            graph_store=_graph_store,
            embedder=_embedder
        )
    
    if _rag_engine is None:
        _rag_engine = RAGEngine(
            vector_store=_vector_store,
            graph_store=_graph_store,
            embedder=_embedder
        )
    
    return _knowledge_processor, _rag_engine

@router.post("/documents", response_model=DocumentResponse)
async def add_document(
    request: DocumentRequest,
    knowledge_processor: KnowledgeProcessor = Depends(get_rag_components)[0]
):
    """단일 문서를 추가합니다."""
    try:
        result = knowledge_processor.process_document(
            content=request.content,
            source=request.source,
            document_type=request.document_type,
            metadata=request.metadata
        )
        
        return DocumentResponse(
            document_id=result.document_id,
            chunks_created=result.chunks_created,
            vectors_created=result.vectors_created,
            graph_nodes_created=result.graph_nodes_created,
            processing_time=result.processing_time,
            status=result.status,
            errors=result.errors
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/batch", response_model=BatchDocumentResponse)
async def add_documents_batch(
    request: BatchDocumentRequest,
    knowledge_processor: KnowledgeProcessor = Depends(get_rag_components)[0]
):
    """여러 문서를 일괄 추가합니다."""
    try:
        documents = [
            {
                "content": doc.content,
                "source": doc.source,
                "type": doc.document_type,
                "metadata": doc.metadata
            }
            for doc in request.documents
        ]
        
        results = knowledge_processor.process_documents_batch(documents)
        
        total_processed = len(results)
        total_success = len([r for r in results if r.status == "success"])
        total_errors = len([r for r in results if r.status == "error"])
        
        return BatchDocumentResponse(
            results=[
                DocumentResponse(
                    document_id=r.document_id,
                    chunks_created=r.chunks_created,
                    vectors_created=r.vectors_created,
                    graph_nodes_created=r.graph_nodes_created,
                    processing_time=r.processing_time,
                    status=r.status,
                    errors=r.errors
                )
                for r in results
            ],
            total_processed=total_processed,
            total_success=total_success,
            total_errors=total_errors
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    rag_engine: RAGEngine = Depends(get_rag_components)[1]
):
    """지식베이스를 쿼리합니다."""
    try:
        rag_response = rag_engine.query(
            query=request.query,
            top_k=request.top_k,
            search_type=request.search_type
        )
        
        return QueryResponse(
            answer=rag_response.answer,
            sources=[
                {
                    "text": source.text,
                    "score": source.score,
                    "source": source.source,
                    "metadata": source.metadata
                }
                for source in rag_response.sources
            ],
            context=rag_response.context,
            metadata=rag_response.metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_rag_stats(
    knowledge_processor: KnowledgeProcessor = Depends(get_rag_components)[0]
):
    """RAG 시스템 통계를 반환합니다."""
    try:
        stats = knowledge_processor.get_processing_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    knowledge_processor: KnowledgeProcessor = Depends(get_rag_components)[0]
):
    """문서를 삭제합니다."""
    try:
        success = knowledge_processor.delete_document(document_id)
        if success:
            return {"message": f"문서 {document_id}가 삭제되었습니다."}
        else:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{document_id}")
async def update_document(
    document_id: str,
    request: DocumentRequest,
    knowledge_processor: KnowledgeProcessor = Depends(get_rag_components)[0]
):
    """문서를 업데이트합니다."""
    try:
        result = knowledge_processor.update_document(
            document_id=document_id,
            new_content=request.content,
            new_metadata=request.metadata
        )
        
        return DocumentResponse(
            document_id=result.document_id,
            chunks_created=result.chunks_created,
            vectors_created=result.vectors_created,
            graph_nodes_created=result.graph_nodes_created,
            processing_time=result.processing_time,
            status=result.status,
            errors=result.errors
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate")
async def validate_document(request: DocumentRequest):
    """문서 유효성을 검사합니다."""
    try:
        from rag.knowledge_processor import KnowledgeProcessor
        
        # 임시 KnowledgeProcessor 인스턴스 생성 (검증만을 위해)
        embedder = Embedder(
            openai_api_key=settings.OPENAI_API_KEY,
            ollama_base_url=settings.OLLAMA_BASE_URL,
            ollama_model=settings.OLLAMA_MODEL
        )
        
        vector_store = MilvusVectorStore(
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
            collection_name=settings.MILVUS_COLLECTION,
            dimension=embedder.get_embedding_dimension()
        )
        
        graph_store = Neo4jGraphStore(
            uri=settings.NEO4J_URI,
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD
        )
        
        knowledge_processor = KnowledgeProcessor(
            vector_store=vector_store,
            graph_store=graph_store,
            embedder=embedder
        )
        
        validation_result = knowledge_processor.validate_document(
            content=request.content,
            source=request.source
        )
        
        return validation_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 