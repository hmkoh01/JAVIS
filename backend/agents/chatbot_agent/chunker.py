from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import re

@dataclass
class TextChunk:
    """텍스트 청크를 나타내는 데이터 클래스"""
    content: str
    chunk_id: str
    document_id: str
    chunk_index: int
    metadata: Dict[str, Any]
    created_at: datetime

class TextChunker:
    """텍스트를 청크로 분할하는 클래스"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str, document_id: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        """텍스트를 청크로 분할합니다."""
        if not text.strip():
            return []
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # 청크 크기만큼 텍스트 추출
            end = start + self.chunk_size
            
            if end >= len(text):
                # 마지막 청크
                chunk_text = text[start:].strip()
            else:
                # 문장 경계에서 자르기
                chunk_text = self._split_at_sentence_boundary(text, start, end)
                end = start + len(chunk_text)
            
            if chunk_text.strip():
                chunk = TextChunk(
                    content=chunk_text.strip(),
                    chunk_id=f"{document_id}_chunk_{chunk_index}",
                    document_id=document_id,
                    chunk_index=chunk_index,
                    metadata=metadata or {},
                    created_at=datetime.utcnow()
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # 다음 청크의 시작점 (오버랩 고려)
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _split_at_sentence_boundary(self, text: str, start: int, end: int) -> str:
        """문장 경계에서 텍스트를 자릅니다."""
        chunk_text = text[start:end]
        
        # 문장 끝 패턴들
        sentence_endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
        
        # 가장 가까운 문장 끝 찾기
        best_split = len(chunk_text)
        for ending in sentence_endings:
            pos = chunk_text.rfind(ending)
            if pos > 0 and pos < len(chunk_text) - 2:  # 문장 끝이 청크 중간에 있는 경우
                best_split = pos + len(ending)
                break
        
        return chunk_text[:best_split]
    
    def chunk_by_sentences(self, text: str, document_id: str, 
                          sentences_per_chunk: int = 5, 
                          metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        """문장 단위로 청킹합니다."""
        sentences = self._split_into_sentences(text)
        chunks = []
        chunk_index = 0
        
        for i in range(0, len(sentences), sentences_per_chunk):
            chunk_sentences = sentences[i:i + sentences_per_chunk]
            chunk_text = ' '.join(chunk_sentences)
            
            if chunk_text.strip():
                chunk = TextChunk(
                    content=chunk_text.strip(),
                    chunk_id=f"{document_id}_chunk_{chunk_index}",
                    document_id=document_id,
                    chunk_index=chunk_index,
                    metadata=metadata or {},
                    created_at=datetime.utcnow()
                )
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks
    
    def chunk_by_paragraphs(self, text: str, document_id: str,
                           paragraphs_per_chunk: int = 3,
                           metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        """문단 단위로 청킹합니다."""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []
        chunk_index = 0
        
        for i in range(0, len(paragraphs), paragraphs_per_chunk):
            chunk_paragraphs = paragraphs[i:i + paragraphs_per_chunk]
            chunk_text = '\n\n'.join(chunk_paragraphs)
            
            if chunk_text.strip():
                chunk = TextChunk(
                    content=chunk_text.strip(),
                    chunk_id=f"{document_id}_chunk_{chunk_index}",
                    document_id=document_id,
                    chunk_index=chunk_index,
                    metadata=metadata or {},
                    created_at=datetime.utcnow()
                )
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """텍스트를 문장으로 분할합니다."""
        # 문장 끝 패턴
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk_documents(self, documents: List[Dict[str, Any]], 
                       chunking_strategy: str = 'size') -> List[TextChunk]:
        """여러 문서를 일괄 청킹합니다."""
        all_chunks = []
        
        for doc in documents:
            try:
                content = doc.get('content', '')
                document_id = doc.get('document_id', f"doc_{len(all_chunks)}")
                metadata = doc.get('metadata', {})
                
                if chunking_strategy == 'sentences':
                    chunks = self.chunk_by_sentences(content, document_id, metadata=metadata)
                elif chunking_strategy == 'paragraphs':
                    chunks = self.chunk_by_paragraphs(content, document_id, metadata=metadata)
                else:
                    chunks = self.chunk_text(content, document_id, metadata=metadata)
                
                all_chunks.extend(chunks)
                
            except Exception as e:
                print(f"Error chunking document {document_id}: {e}")
                continue
        
        return all_chunks 