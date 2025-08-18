import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..base_agent import BaseAgent, AgentResponse
from database.models import User, UserInteraction, KnowledgeBase
from database.connection import get_db_session

class RecommendationAgent(BaseAgent):
    """추천 및 제안 관련 작업을 처리하는 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_type="recommendation",
            description="추천, 제안, 추천해줘 등의 요청을 처리합니다."
        )
    
    async def process(self, user_input: str, user_id: Optional[int] = None) -> AgentResponse:
        """사용자 입력을 처리합니다."""
        try:
            # 간단한 추천 관련 응답
            response_content = f"추천 에이전트가 '{user_input}' 요청을 처리했습니다. 현재는 기본 응답만 제공합니다."
            
            return AgentResponse(
                success=True,
                content=response_content,
                agent_type=self.agent_type,
                metadata={
                    "query": user_input,
                    "user_id": user_id,
                    "agent_type": "recommendation"
                }
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"추천 에이전트 처리 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    def _analyze_recommendation_type(self, user_input: str) -> str:
        """추천 타입을 분석합니다."""
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ["지식", "knowledge", "정보"]):
            return "knowledge"
        elif any(word in input_lower for word in ["콘텐츠", "content", "자료"]):
            return "content"
        elif any(word in input_lower for word in ["학습", "learning", "경로", "path"]):
            return "learning_path"
        else:
            return "knowledge"
    
    async def _recommend_knowledge(self, user_id: int, user_input: str) -> AgentResponse:
        """지식 기반 추천을 생성합니다."""
        try:
            db = get_db_session()
            
            # 사용자 상호작용 히스토리 분석
            user_interactions = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id
            ).order_by(UserInteraction.timestamp.desc()).limit(50).all()
            
            # 사용자 관심사 추출
            interests = self._extract_user_interests(user_interactions)
            
            # 지식베이스에서 관련 항목 검색
            knowledge_items = db.query(KnowledgeBase).all()
            
            if not knowledge_items:
                return AgentResponse(
                    success=True,
                    content="추천할 지식 항목이 없습니다.",
                    agent_type=self.agent_type
                )
            
            # 관련성 점수 계산
            scored_items = []
            for item in knowledge_items:
                score = self._calculate_relevance_score(item, interests, user_input)
                scored_items.append((item, score))
            
            # 점수순으로 정렬
            scored_items.sort(key=lambda x: x[1], reverse=True)
            
            # 상위 5개 추천
            top_recommendations = scored_items[:5]
            
            recommendations = []
            for item, score in top_recommendations:
                recommendations.append({
                    "title": item.title,
                    "content": item.content[:200] + "..." if len(item.content) > 200 else item.content,
                    "category": item.category,
                    "tags": item.tags,
                    "relevance_score": score,
                    "type": "knowledge"
                })
            
            return AgentResponse(
                success=True,
                content={
                    "recommendations": recommendations,
                    "user_interests": interests,
                    "total_items": len(knowledge_items)
                },
                agent_type=self.agent_type,
                metadata={"recommendation_type": "knowledge"}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"지식 추천 생성 중 오류: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def _recommend_content(self, user_id: int, user_input: str) -> AgentResponse:
        """콘텐츠 추천을 생성합니다."""
        try:
            # 사용자 관심사 기반으로 웹 검색
            interests = await self._get_user_interests(user_id)
            
            if not interests:
                return AgentResponse(
                    success=True,
                    content="사용자 관심사를 파악할 수 없어 추천을 생성할 수 없습니다.",
                    agent_type=self.agent_type
                )
            
            # 관심사별로 웹 검색
            recommendations = []
            for interest in interests[:3]:  # 상위 3개 관심사만 사용
                search_result = await self.execute_tool(
                    "web_search_tool",
                    query=f"{interest} 관련 최신 정보",
                    max_results=2
                )
                
                if search_result.success:
                    for item in search_result.data:
                        recommendations.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("snippet", ""),
                            "interest": interest,
                            "type": "web_content"
                        })
            
            return AgentResponse(
                success=True,
                content={
                    "recommendations": recommendations[:10],  # 최대 10개
                    "user_interests": interests
                },
                agent_type=self.agent_type,
                tools_used=["web_search_tool"],
                metadata={"recommendation_type": "content"}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"콘텐츠 추천 생성 중 오류: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def _recommend_learning_path(self, user_id: int, user_input: str) -> AgentResponse:
        """학습 경로 추천을 생성합니다."""
        try:
            # 사용자 현재 수준과 목표 분석
            user_profile = await self._analyze_user_profile(user_id)
            
            # 학습 경로 생성
            learning_path = self._generate_learning_path(user_profile, user_input)
            
            return AgentResponse(
                success=True,
                content={
                    "learning_path": learning_path,
                    "user_profile": user_profile
                },
                agent_type=self.agent_type,
                metadata={"recommendation_type": "learning_path"}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"학습 경로 추천 생성 중 오류: {str(e)}",
                agent_type=self.agent_type
            )
    
    def _extract_user_interests(self, interactions: List[UserInteraction]) -> List[str]:
        """사용자 상호작용에서 관심사를 추출합니다."""
        interests = []
        
        for interaction in interactions:
            # 질문에서 키워드 추출 (간단한 구현)
            query_lower = interaction.query.lower()
            
            # 일반적인 관심사 키워드
            interest_keywords = [
                "python", "javascript", "java", "c++", "machine learning", "ai", "data science",
                "web development", "mobile development", "database", "cloud", "devops",
                "프로그래밍", "코딩", "개발", "학습", "프로젝트", "알고리즘", "자료구조"
            ]
            
            for keyword in interest_keywords:
                if keyword in query_lower:
                    interests.append(keyword)
        
        # 중복 제거 및 빈도순 정렬
        interest_counts = {}
        for interest in interests:
            interest_counts[interest] = interest_counts.get(interest, 0) + 1
        
        sorted_interests = sorted(interest_counts.items(), key=lambda x: x[1], reverse=True)
        return [interest for interest, count in sorted_interests[:10]]  # 상위 10개
    
    async def _get_user_interests(self, user_id: int) -> List[str]:
        """사용자 관심사를 가져옵니다."""
        try:
            db = next(get_db())
            interactions = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id
            ).order_by(UserInteraction.timestamp.desc()).limit(50).all()
            
            return self._extract_user_interests(interactions)
        except:
            return []
    
    def _calculate_relevance_score(self, item: KnowledgeBase, interests: List[str], user_input: str) -> float:
        """지식 항목의 관련성 점수를 계산합니다."""
        score = 0.0
        
        # 사용자 관심사와의 매칭
        item_content_lower = item.content.lower()
        item_title_lower = item.title.lower()
        
        for interest in interests:
            if interest.lower() in item_content_lower:
                score += 2.0
            if interest.lower() in item_title_lower:
                score += 3.0
        
        # 사용자 입력과의 매칭
        user_input_lower = user_input.lower()
        if user_input_lower in item_content_lower:
            score += 1.5
        if user_input_lower in item_title_lower:
            score += 2.0
        
        # 태그 매칭
        for tag in item.tags:
            if tag.lower() in user_input_lower:
                score += 1.0
        
        return score
    
    async def _analyze_user_profile(self, user_id: int) -> Dict[str, Any]:
        """사용자 프로필을 분석합니다."""
        try:
            db = get_db_session()
            
            # 사용자 정보
            user = db.query(User).filter(User.id == user_id).first()
            
            # 상호작용 분석
            interactions = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id
            ).all()
            
            # 에이전트별 사용 빈도
            agent_usage = {}
            for interaction in interactions:
                agent_type = interaction.agent_type
                agent_usage[agent_type] = agent_usage.get(agent_type, 0) + 1
            
            # 관심사 추출
            interests = self._extract_user_interests(interactions)
            
            return {
                "user_id": user_id,
                "username": user.username if user else "Unknown",
                "total_interactions": len(interactions),
                "agent_usage": agent_usage,
                "interests": interests,
                "experience_level": self._estimate_experience_level(interactions)
            }
        except:
            return {
                "user_id": user_id,
                "username": "Unknown",
                "total_interactions": 0,
                "agent_usage": {},
                "interests": [],
                "experience_level": "beginner"
            }
    
    def _estimate_experience_level(self, interactions: List[UserInteraction]) -> str:
        """사용자의 경험 수준을 추정합니다."""
        if len(interactions) < 10:
            return "beginner"
        elif len(interactions) < 50:
            return "intermediate"
        else:
            return "advanced"
    
    def _generate_learning_path(self, user_profile: Dict[str, Any], user_input: str) -> List[Dict[str, Any]]:
        """학습 경로를 생성합니다."""
        experience_level = user_profile.get("experience_level", "beginner")
        interests = user_profile.get("interests", [])
        
        # 기본 학습 경로 템플릿
        learning_paths = {
            "beginner": [
                {
                    "step": 1,
                    "title": "기초 개념 학습",
                    "description": "프로그래밍의 기본 개념을 이해합니다.",
                    "estimated_time": "2-3주",
                    "resources": ["온라인 튜토리얼", "기초 교재"]
                },
                {
                    "step": 2,
                    "title": "실습 프로젝트",
                    "description": "간단한 프로젝트를 통해 실습합니다.",
                    "estimated_time": "1-2주",
                    "resources": ["미니 프로젝트", "코딩 연습"]
                }
            ],
            "intermediate": [
                {
                    "step": 1,
                    "title": "심화 개념 학습",
                    "description": "고급 프로그래밍 개념을 학습합니다.",
                    "estimated_time": "3-4주",
                    "resources": ["고급 교재", "온라인 강의"]
                },
                {
                    "step": 2,
                    "title": "실무 프로젝트",
                    "description": "실무 수준의 프로젝트를 진행합니다.",
                    "estimated_time": "4-6주",
                    "resources": ["오픈소스 프로젝트", "팀 프로젝트"]
                }
            ],
            "advanced": [
                {
                    "step": 1,
                    "title": "전문 분야 심화",
                    "description": "특정 분야의 전문 지식을 습득합니다.",
                    "estimated_time": "6-8주",
                    "resources": ["전문 서적", "컨퍼런스 참석"]
                },
                {
                    "step": 2,
                    "title": "리더십 및 멘토링",
                    "description": "다른 개발자를 가르치고 리드합니다.",
                    "estimated_time": "지속적",
                    "resources": ["멘토링 프로그램", "기술 블로그 운영"]
                }
            ]
        }
        
        base_path = learning_paths.get(experience_level, learning_paths["beginner"])
        
        # 관심사에 맞게 커스터마이징
        customized_path = []
        for step in base_path:
            customized_step = step.copy()
            if interests:
                customized_step["description"] += f" (관심 분야: {', '.join(interests[:3])})"
            customized_path.append(customized_step)
        
        return customized_path 