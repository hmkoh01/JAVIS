from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

@dataclass
class SearchResult:
    """검색 결과를 나타내는 데이터 클래스"""
    text: str
    score: float
    source: str
    metadata: Dict[str, Any]

@dataclass
class RAGResponse:
    """RAG 응답을 나타내는 데이터 클래스"""
    answer: str
    sources: List[SearchResult]
    context: str
    metadata: Dict[str, Any]

class RAGEngine:
    """RAG (Retrieval-Augmented Generation) 엔진"""
    
    def __init__(self, vector_store, graph_store, embedder, llm_model=None):
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.embedder = embedder
        self.llm_model = llm_model
    
    def search(self, query: str, top_k: int = 5, 
               search_type: str = "vector") -> List[SearchResult]:
        """쿼리를 검색합니다."""
        if search_type == "vector":
            return self._vector_search(query, top_k)
        elif search_type == "graph":
            return self._graph_search(query, top_k)
        elif search_type == "hybrid":
            return self._hybrid_search(query, top_k)
        else:
            return self._vector_search(query, top_k)
    
    def _vector_search(self, query: str, top_k: int) -> List[SearchResult]:
        """벡터 검색을 수행합니다."""
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.embedder.embed_text(query)
            
            # 벡터 스토어에서 검색
            search_results = self.vector_store.search_vectors(
                query_embedding.embedding, top_k=top_k
            )
            
            # 결과 변환
            results = []
            for vector_record, score in search_results:
                result = SearchResult(
                    text=vector_record.text,
                    score=float(score),
                    source=vector_record.metadata.get("source", "unknown"),
                    metadata=vector_record.metadata
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"벡터 검색 오류: {e}")
            return []
    
    def _graph_search(self, query: str, top_k: int) -> List[SearchResult]:
        """그래프 검색을 수행합니다."""
        try:
            # Neo4j에서 텍스트 검색
            documents = self.graph_store.search_documents_by_content(query, limit=top_k)
            
            # 결과 변환
            results = []
            for doc in documents:
                result = SearchResult(
                    text=doc.properties.get("content", ""),
                    score=1.0,  # 그래프 검색은 기본 점수
                    source=doc.properties.get("source", "unknown"),
                    metadata=doc.properties
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"그래프 검색 오류: {e}")
            return []
    
    def _hybrid_search(self, query: str, top_k: int) -> List[SearchResult]:
        """하이브리드 검색을 수행합니다."""
        try:
            # 벡터 검색과 그래프 검색 모두 수행
            vector_results = self._vector_search(query, top_k // 2)
            graph_results = self._graph_search(query, top_k // 2)
            
            # 결과 병합 및 정렬
            all_results = vector_results + graph_results
            all_results.sort(key=lambda x: x.score, reverse=True)
            
            return all_results[:top_k]
            
        except Exception as e:
            print(f"하이브리드 검색 오류: {e}")
            return []
    
    def generate_answer(self, query: str, context: List[SearchResult], 
                       max_context_length: int = 4000) -> str:
        """컨텍스트를 기반으로 답변을 생성합니다."""
        if not self.llm_model:
            return self._generate_simple_answer(query, context)
        
        try:
            # 컨텍스트 준비
            context_text = self._prepare_context(context, max_context_length)
            
            # LLM을 사용한 답변 생성
            prompt = self._create_prompt(query, context_text)
            answer = self._call_llm(prompt)
            
            return answer
            
        except Exception as e:
            print(f"답변 생성 오류: {e}")
            return self._generate_simple_answer(query, context)
    
    def _prepare_context(self, context: List[SearchResult], max_length: int) -> str:
        """컨텍스트를 준비합니다."""
        context_parts = []
        current_length = 0
        
        for result in context:
            text = f"Source: {result.source}\nContent: {result.text}\n"
            if current_length + len(text) > max_length:
                break
            
            context_parts.append(text)
            current_length += len(text)
        
        return "\n".join(context_parts)
    
    def _create_prompt(self, query: str, context: str) -> str:
        """프롬프트를 생성합니다."""
        return f"""
당신은 사용자 맞춤 AI 비서입니다. 다음 컨텍스트를 기반으로 사용자의 질문에 답변하세요:

컨텍스트:
{context}

사용자 질문: {query}

답변할 때는 다음 규칙을 따르세요:
1. 컨텍스트에서 찾은 정보를 기반으로 답변하세요
2. 정보가 부족하면 솔직히 말하세요
3. 친근하고 도움이 되는 톤을 유지하세요
4. 답변은 간결하고 명확하게 작성하세요

답변:
"""
    
    def _call_llm(self, prompt: str) -> str:
        """LLM을 호출합니다."""
        try:
            if hasattr(self.llm_model, 'agenerate'):
                # LangChain 모델
                from langchain.schema import HumanMessage, SystemMessage
                messages = [
                    SystemMessage(content="당신은 도움이 되는 AI 비서입니다."),
                    HumanMessage(content=prompt)
                ]
                response = self.llm_model.agenerate([messages])
                return response.generations[0][0].text
            else:
                # OpenAI 클라이언트
                response = self.llm_model.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "당신은 도움이 되는 AI 비서입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                return response.choices[0].message.content
        except Exception as e:
            print(f"LLM 호출 오류: {e}")
            return "죄송합니다. 답변을 생성하는 중에 오류가 발생했습니다."
    
    def _generate_simple_answer(self, query: str, context: List[SearchResult]) -> str:
        """간단한 답변을 생성합니다."""
        if not context:
            return "죄송합니다. 관련 정보를 찾을 수 없습니다."
        
        # 가장 관련성 높은 결과 사용
        best_result = context[0]
        
        return f"""
질문: {query}

찾은 정보:
{best_result.text}

출처: {best_result.source}
"""
    
    def query(self, query: str, top_k: int = 5, search_type: str = "vector") -> RAGResponse:
        """전체 RAG 파이프라인을 실행합니다."""
        try:
            # 1. 검색
            search_results = self.search(query, top_k, search_type)
            
            if not search_results:
                return RAGResponse(
                    answer="죄송합니다. 관련 정보를 찾을 수 없습니다.",
                    sources=[],
                    context="",
                    metadata={"search_type": search_type, "results_count": 0}
                )
            
            # 2. 답변 생성
            answer = self.generate_answer(query, search_results)
            
            # 3. 컨텍스트 준비
            context = self._prepare_context(search_results, 2000)
            
            return RAGResponse(
                answer=answer,
                sources=search_results,
                context=context,
                metadata={
                    "search_type": search_type,
                    "results_count": len(search_results),
                    "query": query
                }
            )
            
        except Exception as e:
            print(f"RAG 쿼리 오류: {e}")
            return RAGResponse(
                answer=f"오류가 발생했습니다: {str(e)}",
                sources=[],
                context="",
                metadata={"error": str(e)}
            )
    
    def batch_query(self, queries: List[str], top_k: int = 5, 
                   search_type: str = "vector") -> List[RAGResponse]:
        """여러 쿼리를 일괄 처리합니다."""
        responses = []
        
        for query in queries:
            try:
                response = self.query(query, top_k, search_type)
                responses.append(response)
            except Exception as e:
                print(f"배치 쿼리 오류 (쿼리: {query}): {e}")
                responses.append(RAGResponse(
                    answer=f"오류가 발생했습니다: {str(e)}",
                    sources=[],
                    context="",
                    metadata={"error": str(e)}
                ))
        
        return responses 