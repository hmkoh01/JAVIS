import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class ParsedDocument:
    """파싱된 문서를 나타내는 데이터 클래스"""
    content: str
    title: str
    source: str
    document_type: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class DocumentParser:
    """다양한 형식의 문서를 파싱하는 클래스"""
    
    def __init__(self):
        self.supported_types = ['text', 'json', 'markdown', 'html']
    
    def parse(self, content: str, source: str, document_type: str = 'text', 
              metadata: Optional[Dict[str, Any]] = None) -> ParsedDocument:
        """문서를 파싱합니다."""
        
        if document_type == 'json':
            return self._parse_json(content, source, metadata)
        elif document_type == 'markdown':
            return self._parse_markdown(content, source, metadata)
        elif document_type == 'html':
            return self._parse_html(content, source, metadata)
        else:
            return self._parse_text(content, source, metadata)
    
    def _parse_text(self, content: str, source: str, metadata: Optional[Dict[str, Any]]) -> ParsedDocument:
        """일반 텍스트를 파싱합니다."""
        # 제목 추출 (첫 번째 줄 또는 특정 패턴)
        title = self._extract_title_from_text(content)
        
        return ParsedDocument(
            content=content.strip(),
            title=title,
            source=source,
            document_type='text',
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def _parse_json(self, content: str, source: str, metadata: Optional[Dict[str, Any]]) -> ParsedDocument:
        """JSON 형식의 문서를 파싱합니다."""
        try:
            data = json.loads(content)
            
            # JSON에서 제목과 내용 추출
            title = data.get('title', 'Untitled')
            text_content = data.get('content', '')
            
            # JSON 데이터를 텍스트로 변환
            if not text_content:
                text_content = json.dumps(data, ensure_ascii=False, indent=2)
            
            return ParsedDocument(
                content=text_content,
                title=title,
                source=source,
                document_type='json',
                metadata={**metadata or {}, 'json_data': data},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    
    def _parse_markdown(self, content: str, source: str, metadata: Optional[Dict[str, Any]]) -> ParsedDocument:
        """Markdown 형식의 문서를 파싱합니다."""
        # Markdown에서 제목 추출
        title = self._extract_title_from_markdown(content)
        
        return ParsedDocument(
            content=content.strip(),
            title=title,
            source=source,
            document_type='markdown',
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def _parse_html(self, content: str, source: str, metadata: Optional[Dict[str, Any]]) -> ParsedDocument:
        """HTML 형식의 문서를 파싱합니다."""
        # HTML 태그 제거 및 텍스트 추출
        clean_content = self._clean_html(content)
        title = self._extract_title_from_html(content)
        
        return ParsedDocument(
            content=clean_content,
            title=title,
            source=source,
            document_type='html',
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def _extract_title_from_text(self, content: str) -> str:
        """텍스트에서 제목을 추출합니다."""
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) < 100:  # 적당한 길이의 첫 번째 줄을 제목으로 사용
                return line
        return "Untitled"
    
    def _extract_title_from_markdown(self, content: str) -> str:
        """Markdown에서 제목을 추출합니다."""
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            # # 으로 시작하는 제목 찾기
            if line.startswith('#'):
                return line.lstrip('#').strip()
        return "Untitled"
    
    def _extract_title_from_html(self, content: str) -> str:
        """HTML에서 제목을 추출합니다."""
        # <title> 태그 찾기
        title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
        if title_match:
            return title_match.group(1).strip()
        
        # <h1> 태그 찾기
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
        if h1_match:
            return h1_match.group(1).strip()
        
        return "Untitled"
    
    def _clean_html(self, content: str) -> str:
        """HTML 태그를 제거하고 텍스트만 추출합니다."""
        # HTML 태그 제거
        clean = re.sub(r'<[^>]+>', '', content)
        # 여러 공백을 하나로
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()
    
    def parse_batch(self, documents: List[Dict[str, Any]]) -> List[ParsedDocument]:
        """여러 문서를 일괄 파싱합니다."""
        parsed_documents = []
        
        for doc in documents:
            try:
                content = doc.get('content', '')
                source = doc.get('source', 'unknown')
                doc_type = doc.get('type', 'text')
                metadata = doc.get('metadata', {})
                
                parsed_doc = self.parse(content, source, doc_type, metadata)
                parsed_documents.append(parsed_doc)
                
            except Exception as e:
                print(f"Error parsing document {source}: {e}")
                continue
        
        return parsed_documents 