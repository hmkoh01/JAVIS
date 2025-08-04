from typing import List, Dict, Any, Optional, Union
import numpy as np
from dataclasses import dataclass
from datetime import datetime
import hashlib

@dataclass
class EmbeddingResult:
    """임베딩 결과를 나타내는 데이터 클래스"""
    text: str
    embedding: np.ndarray
    embedding_id: str
    metadata: Dict[str, Any]
    created_at: datetime

class Embedder:
    """텍스트 임베딩을 생성하는 클래스"""
    
    def __init__(self, model_name: str = "text-embedding-ada-002", 
                 openai_api_key: Optional[str] = None,
                 ollama_base_url: Optional[str] = None,
                 ollama_model: str = "llama2"):
        self.model_name = model_name
        self.openai_api_key = openai_api_key
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.embedding_model = None
        self._initialize_embedding_model()
    
    def _initialize_embedding_model(self):
        """임베딩 모델을 초기화합니다."""
        try:
            if self.openai_api_key:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.openai_api_key)
                self.embedding_model = "openai"
            elif self.ollama_base_url:
                # Ollama 임베딩 모델 사용
                self.embedding_model = "ollama"
            else:
                # 기본적으로 sentence-transformers 사용
                try:
                    from sentence_transformers import SentenceTransformer
                    self.model = SentenceTransformer('all-MiniLM-L6-v2')
                    self.embedding_model = "sentence_transformers"
                except ImportError:
                    raise ImportError("sentence-transformers가 설치되지 않았습니다. pip install sentence-transformers")
        except Exception as e:
            print(f"임베딩 모델 초기화 오류: {e}")
    
    def embed_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> EmbeddingResult:
        """단일 텍스트를 임베딩합니다."""
        if not text.strip():
            raise ValueError("빈 텍스트는 임베딩할 수 없습니다.")
        
        embedding = self._generate_embedding(text)
        embedding_id = self._generate_embedding_id(text, metadata)
        
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            embedding_id=embedding_id,
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )
    
    def embed_texts(self, texts: List[str], metadata_list: Optional[List[Dict[str, Any]]] = None) -> List[EmbeddingResult]:
        """여러 텍스트를 임베딩합니다."""
        if not texts:
            return []
        
        if metadata_list is None:
            metadata_list = [{} for _ in texts]
        
        results = []
        for i, text in enumerate(texts):
            try:
                metadata = metadata_list[i] if i < len(metadata_list) else {}
                result = self.embed_text(text, metadata)
                results.append(result)
            except Exception as e:
                print(f"텍스트 임베딩 오류 (인덱스 {i}): {e}")
                continue
        
        return results
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """실제 임베딩을 생성합니다."""
        if self.embedding_model == "openai":
            return self._embed_with_openai(text)
        elif self.embedding_model == "ollama":
            return self._embed_with_ollama(text)
        elif self.embedding_model == "sentence_transformers":
            return self._embed_with_sentence_transformers(text)
        else:
            raise ValueError("임베딩 모델이 초기화되지 않았습니다.")
    
    def _embed_with_openai(self, text: str) -> np.ndarray:
        """OpenAI API를 사용하여 임베딩을 생성합니다."""
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            raise Exception(f"OpenAI 임베딩 오류: {e}")
    
    def _embed_with_ollama(self, text: str) -> np.ndarray:
        """Ollama를 사용하여 임베딩을 생성합니다."""
        try:
            import requests
            response = requests.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={
                    "model": self.ollama_model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            return np.array(embedding)
        except Exception as e:
            raise Exception(f"Ollama 임베딩 오류: {e}")
    
    def _embed_with_sentence_transformers(self, text: str) -> np.ndarray:
        """Sentence Transformers를 사용하여 임베딩을 생성합니다."""
        try:
            embedding = self.model.encode(text)
            return embedding
        except Exception as e:
            raise Exception(f"Sentence Transformers 임베딩 오류: {e}")
    
    def _generate_embedding_id(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """임베딩 ID를 생성합니다."""
        # 텍스트와 메타데이터를 조합하여 고유 ID 생성
        content = text + str(metadata or {})
        return hashlib.md5(content.encode()).hexdigest()
    
    def batch_embed(self, texts: List[str], batch_size: int = 32, 
                   metadata_list: Optional[List[Dict[str, Any]]] = None) -> List[EmbeddingResult]:
        """배치 단위로 임베딩을 생성합니다."""
        all_results = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadata = None
            if metadata_list:
                batch_metadata = metadata_list[i:i + batch_size]
            
            try:
                batch_results = self.embed_texts(batch_texts, batch_metadata)
                all_results.extend(batch_results)
            except Exception as e:
                print(f"배치 임베딩 오류 (배치 {i//batch_size}): {e}")
                continue
        
        return all_results
    
    def get_embedding_dimension(self) -> int:
        """임베딩 차원을 반환합니다."""
        if self.embedding_model == "openai":
            # OpenAI text-embedding-ada-002는 1536차원
            return 1536
        elif self.embedding_model == "sentence_transformers":
            # all-MiniLM-L6-v2는 384차원
            return 384
        elif self.embedding_model == "ollama":
            # Ollama 모델에 따라 다름 (기본값)
            return 4096
        else:
            return 384  # 기본값
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """두 임베딩 간의 코사인 유사도를 계산합니다."""
        return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
    
    def find_most_similar(self, query_embedding: np.ndarray, 
                         candidate_embeddings: List[np.ndarray]) -> tuple[int, float]:
        """가장 유사한 임베딩을 찾습니다."""
        similarities = [self.similarity(query_embedding, emb) for emb in candidate_embeddings]
        max_index = np.argmax(similarities)
        return max_index, similarities[max_index] 