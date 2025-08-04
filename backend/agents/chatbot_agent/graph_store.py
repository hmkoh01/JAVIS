from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import uuid

@dataclass
class GraphNode:
    """그래프 노드를 나타내는 데이터 클래스"""
    id: str
    labels: List[str]
    properties: Dict[str, Any]
    created_at: datetime

@dataclass
class GraphRelationship:
    """그래프 관계를 나타내는 데이터 클래스"""
    start_node_id: str
    end_node_id: str
    relationship_type: str
    properties: Dict[str, Any]
    created_at: datetime

class Neo4jGraphStore:
    """Neo4j 그래프 데이터베이스와 상호작용하는 클래스"""
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 username: str = "neo4j", password: str = "password"):
        self.uri = uri
        self.username = username
        self.password = password
        self.driver = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Neo4j 연결을 초기화합니다."""
        try:
            from neo4j import GraphDatabase
            
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            
            # 연결 테스트
            with self.driver.session() as session:
                session.run("RETURN 1")
            
        except ImportError:
            raise ImportError("neo4j가 설치되지 않았습니다. pip install neo4j")
        except Exception as e:
            print(f"Neo4j 연결 오류: {e}")
    
    def create_document_node(self, document_id: str, title: str, content: str, 
                           source: str, document_type: str, metadata: Dict[str, Any]) -> str:
        """문서 노드를 생성합니다."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    CREATE (d:Document {
                        id: $document_id,
                        title: $title,
                        content: $content,
                        source: $source,
                        document_type: $document_type,
                        metadata: $metadata,
                        created_at: datetime()
                    })
                    RETURN d.id
                """, document_id=document_id, title=title, content=content,
                    source=source, document_type=document_type, metadata=str(metadata))
                
                return result.single()[0]
        except Exception as e:
            print(f"문서 노드 생성 오류: {e}")
            return None
    
    def create_chunk_node(self, chunk_id: str, document_id: str, content: str, 
                         chunk_index: int, metadata: Dict[str, Any]) -> str:
        """청크 노드를 생성합니다."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    CREATE (c:Chunk {
                        id: $chunk_id,
                        content: $content,
                        chunk_index: $chunk_index,
                        metadata: $metadata,
                        created_at: datetime()
                    })
                    WITH c
                    MATCH (d:Document {id: $document_id})
                    CREATE (d)-[:CONTAINS]->(c)
                    RETURN c.id
                """, chunk_id=chunk_id, document_id=document_id, content=content,
                    chunk_index=chunk_index, metadata=str(metadata))
                
                return result.single()[0]
        except Exception as e:
            print(f"청크 노드 생성 오류: {e}")
            return None
    
    def create_entity_node(self, entity_id: str, entity_type: str, name: str, 
                          properties: Dict[str, Any]) -> str:
        """엔티티 노드를 생성합니다."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    CREATE (e:Entity {
                        id: $entity_id,
                        entity_type: $entity_type,
                        name: $name,
                        properties: $properties,
                        created_at: datetime()
                    })
                    RETURN e.id
                """, entity_id=entity_id, entity_type=entity_type, name=name,
                    properties=str(properties))
                
                return result.single()[0]
        except Exception as e:
            print(f"엔티티 노드 생성 오류: {e}")
            return None
    
    def create_relationship(self, start_node_id: str, end_node_id: str, 
                          relationship_type: str, properties: Dict[str, Any]) -> bool:
        """관계를 생성합니다."""
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (a), (b)
                    WHERE a.id = $start_node_id AND b.id = $end_node_id
                    CREATE (a)-[r:RELATES_TO {
                        relationship_type: $relationship_type,
                        properties: $properties,
                        created_at: datetime()
                    }]->(b)
                """, start_node_id=start_node_id, end_node_id=end_node_id,
                    relationship_type=relationship_type, properties=str(properties))
                
                return True
        except Exception as e:
            print(f"관계 생성 오류: {e}")
            return False
    
    def find_document_by_id(self, document_id: str) -> Optional[GraphNode]:
        """ID로 문서를 찾습니다."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (d:Document {id: $document_id})
                    RETURN d
                """, document_id=document_id)
                
                record = result.single()
                if record:
                    node = record["d"]
                    return GraphNode(
                        id=node["id"],
                        labels=list(node.labels),
                        properties=dict(node),
                        created_at=node["created_at"]
                    )
                return None
        except Exception as e:
            print(f"문서 조회 오류: {e}")
            return None
    
    def find_chunks_by_document(self, document_id: str) -> List[GraphNode]:
        """문서의 모든 청크를 찾습니다."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (d:Document {id: $document_id})-[:CONTAINS]->(c:Chunk)
                    RETURN c
                    ORDER BY c.chunk_index
                """, document_id=document_id)
                
                chunks = []
                for record in result:
                    node = record["c"]
                    chunks.append(GraphNode(
                        id=node["id"],
                        labels=list(node.labels),
                        properties=dict(node),
                        created_at=node["created_at"]
                    ))
                
                return chunks
        except Exception as e:
            print(f"청크 조회 오류: {e}")
            return []
    
    def find_related_documents(self, document_id: str, relationship_type: str = None) -> List[GraphNode]:
        """관련 문서들을 찾습니다."""
        try:
            with self.driver.session() as session:
                if relationship_type:
                    query = """
                        MATCH (d1:Document {id: $document_id})-[r:RELATES_TO]->(d2:Document)
                        WHERE r.relationship_type = $relationship_type
                        RETURN d2
                    """
                    result = session.run(query, document_id=document_id, relationship_type=relationship_type)
                else:
                    query = """
                        MATCH (d1:Document {id: $document_id})-[r:RELATES_TO]->(d2:Document)
                        RETURN d2
                    """
                    result = session.run(query, document_id=document_id)
                
                documents = []
                for record in result:
                    node = record["d2"]
                    documents.append(GraphNode(
                        id=node["id"],
                        labels=list(node.labels),
                        properties=dict(node),
                        created_at=node["created_at"]
                    ))
                
                return documents
        except Exception as e:
            print(f"관련 문서 조회 오류: {e}")
            return []
    
    def search_documents_by_content(self, search_term: str, limit: int = 10) -> List[GraphNode]:
        """내용으로 문서를 검색합니다."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (d:Document)
                    WHERE d.content CONTAINS $search_term OR d.title CONTAINS $search_term
                    RETURN d
                    LIMIT $limit
                """, search_term=search_term, limit=limit)
                
                documents = []
                for record in result:
                    node = record["d"]
                    documents.append(GraphNode(
                        id=node["id"],
                        labels=list(node.labels),
                        properties=dict(node),
                        created_at=node["created_at"]
                    ))
                
                return documents
        except Exception as e:
            print(f"문서 검색 오류: {e}")
            return []
    
    def find_entities_by_type(self, entity_type: str) -> List[GraphNode]:
        """타입으로 엔티티를 찾습니다."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (e:Entity {entity_type: $entity_type})
                    RETURN e
                """, entity_type=entity_type)
                
                entities = []
                for record in result:
                    node = record["e"]
                    entities.append(GraphNode(
                        id=node["id"],
                        labels=list(node.labels),
                        properties=dict(node),
                        created_at=node["created_at"]
                    ))
                
                return entities
        except Exception as e:
            print(f"엔티티 조회 오류: {e}")
            return []
    
    def delete_document(self, document_id: str) -> bool:
        """문서와 관련된 모든 노드를 삭제합니다."""
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (d:Document {id: $document_id})
                    OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk)
                    OPTIONAL MATCH (d)-[r]-()
                    DELETE c, r, d
                """, document_id=document_id)
                
                return True
        except Exception as e:
            print(f"문서 삭제 오류: {e}")
            return False
    
    def update_document(self, document_id: str, title: str = None, content: str = None, 
                       metadata: Dict[str, Any] = None) -> bool:
        """문서를 업데이트합니다."""
        try:
            with self.driver.session() as session:
                update_parts = []
                params = {"document_id": document_id}
                
                if title:
                    update_parts.append("d.title = $title")
                    params["title"] = title
                
                if content:
                    update_parts.append("d.content = $content")
                    params["content"] = content
                
                if metadata:
                    update_parts.append("d.metadata = $metadata")
                    params["metadata"] = str(metadata)
                
                if update_parts:
                    query = f"""
                        MATCH (d:Document {{id: $document_id}})
                        SET {', '.join(update_parts)}
                    """
                    session.run(query, **params)
                
                return True
        except Exception as e:
            print(f"문서 업데이트 오류: {e}")
            return False
    
    def get_document_count(self) -> int:
        """문서 개수를 반환합니다."""
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (d:Document) RETURN count(d) as count")
                return result.single()["count"]
        except Exception as e:
            print(f"문서 개수 조회 오류: {e}")
            return 0
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """그래프 통계를 반환합니다."""
        try:
            with self.driver.session() as session:
                stats = {}
                
                # 문서 개수
                result = session.run("MATCH (d:Document) RETURN count(d) as count")
                stats["document_count"] = result.single()["count"]
                
                # 청크 개수
                result = session.run("MATCH (c:Chunk) RETURN count(c) as count")
                stats["chunk_count"] = result.single()["count"]
                
                # 엔티티 개수
                result = session.run("MATCH (e:Entity) RETURN count(e) as count")
                stats["entity_count"] = result.single()["count"]
                
                # 관계 개수
                result = session.run("MATCH ()-[r]-() RETURN count(r) as count")
                stats["relationship_count"] = result.single()["count"]
                
                return stats
        except Exception as e:
            print(f"그래프 통계 조회 오류: {e}")
            return {}
    
    def close(self):
        """연결을 종료합니다."""
        try:
            if self.driver:
                self.driver.close()
        except Exception as e:
            print(f"연결 종료 오류: {e}") 