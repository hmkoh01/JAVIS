import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..base_agent import BaseAgent, AgentResponse
from database.sqlite_meta import SQLiteMeta  # 변경됨: SQLAlchemy 대신 SQLiteMeta 사용

class RecommendationAgent(BaseAgent):
    """추천 및 제안 관련 작업을 처리하는 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_type="recommendation",
            description="추천, 제안, 추천해줘 등의 요청을 처리합니다."
        )
        self.sqlite_meta = SQLiteMeta()  # SQLite 메타데이터 접근
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """상태를 받아서 처리하고 수정된 상태를 반환합니다."""
        question = state.get("question", "")
        user_id = state.get("user_id")
        
        if not question:
            return {**state, "answer": "질문이 제공되지 않았습니다.", "evidence": []}
        
        try:
            # 간단한 추천 관련 응답
            response_content = f"추천 에이전트가 '{question}' 요청을 처리했습니다. 현재는 기본 응답만 제공합니다."
            
            return {
                **state,
                "answer": response_content,
                "evidence": [],
                "agent_type": "recommendation",
                "metadata": {
                    "query": question,
                    "user_id": user_id,
                    "agent_type": "recommendation"
                }
            }
        except Exception as e:
            return {
                **state,
                "answer": f"추천 에이전트 처리 중 오류가 발생했습니다: {str(e)}",
                "evidence": [],
                "agent_type": "recommendation"
            }
    
    async def process_async(self, user_input: str, user_id: Optional[int] = None) -> AgentResponse:
        """사용자 입력을 처리합니다. (기존 호환성을 위한 메서드)"""
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
            # SQLite에서 사용자 데이터 조회
            collected_files = self.sqlite_meta.get_collected_files(user_id)
            collected_browser = self.sqlite_meta.get_collected_browser_history(user_id)
            collected_apps = self.sqlite_meta.get_collected_apps(user_id)
            
            # 사용자 관심사 추출 (간단한 방법)
            interests = self._extract_interests_from_data(collected_files, collected_browser, collected_apps)
            
            # 기본 추천 로직
            recommendations = self._generate_basic_recommendations(interests, user_input)
            
            return AgentResponse(
                success=True,
                content=f"추천 결과: {recommendations}",
                agent_type=self.agent_type,
                metadata={"user_id": user_id, "interests": interests}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"지식 추천 중 오류: {str(e)}",
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
    
    def _extract_interests_from_data(self, collected_files: List[Dict[str, Any]], 
                                   collected_browser: List[Dict[str, Any]], 
                                   collected_apps: List[Dict[str, Any]]) -> List[str]:
        """수집된 데이터에서 사용자 관심사를 추출합니다."""
        interests = []
        
        # 파일명에서 관심사 추출
        for file_info in collected_files:
            file_name = file_info.get('file_name', '').lower()
            file_path = file_info.get('file_path', '').lower()
            
            # 일반적인 관심사 키워드
            interest_keywords = [
                "python", "javascript", "java", "c++", "machine learning", "ai", "data science",
                "web development", "mobile development", "database", "cloud", "devops",
                "프로그래밍", "코딩", "개발", "학습", "프로젝트", "알고리즘", "자료구조"
            ]
            
            for keyword in interest_keywords:
                if keyword in file_name or keyword in file_path:
                    interests.append(keyword)
        
        # 브라우저 히스토리에서 관심사 추출
        for browser_info in collected_browser:
            url = browser_info.get('url', '').lower()
            title = browser_info.get('title', '').lower()
            
            for keyword in interest_keywords:
                if keyword in url or keyword in title:
                    interests.append(keyword)
        
        # 앱 사용에서 관심사 추출
        for app_info in collected_apps:
            app_name = app_info.get('app_name', '').lower()
            window_title = app_info.get('window_title', '').lower()
            
            for keyword in interest_keywords:
                if keyword in app_name or keyword in window_title:
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
            # SQLite에서 사용자 데이터 조회
            collected_files = self.sqlite_meta.get_collected_files(user_id)
            collected_browser = self.sqlite_meta.get_collected_browser_history(user_id)
            collected_apps = self.sqlite_meta.get_collected_apps(user_id)
            
            return self._extract_interests_from_data(collected_files, collected_browser, collected_apps)
        except Exception as e:
            print(f"사용자 관심사 추출 오류: {e}")
            return []
    
    def _calculate_relevance_score(self, item: Dict[str, Any], interests: List[str], user_input: str) -> float:
        """지식 항목의 관련성 점수를 계산합니다."""
        score = 0.0
        
        # 사용자 관심사와의 매칭
        item_content_lower = item.get('content', '').lower()
        item_title_lower = item.get('title', '').lower()
        
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
        tags = item.get('tags', [])
        for tag in tags:
            if tag.lower() in user_input_lower:
                score += 1.0
        
        return score
    
    def _generate_basic_recommendations(self, interests: List[str], user_input: str) -> List[Dict[str, Any]]:
        """기본 추천을 생성합니다."""
        recommendations = []
        
        # 관심사 기반 추천
        for interest in interests[:5]:  # 상위 5개 관심사
            recommendations.append({
                "type": "interest_based",
                "title": f"{interest} 관련 학습 자료",
                "description": f"{interest}에 대한 학습 자료를 추천합니다.",
                "interest": interest,
                "priority": "high"
            })
        
        # 사용자 입력 기반 추천
        if user_input:
            recommendations.append({
                "type": "query_based",
                "title": f"'{user_input}' 관련 추천",
                "description": f"사용자 질문 '{user_input}'에 대한 관련 자료를 추천합니다.",
                "query": user_input,
                "priority": "high"
            })
        
        return recommendations
    
    async def _analyze_user_profile(self, user_id: int) -> Dict[str, Any]:
        """사용자 프로필을 분석합니다."""
        try:
            # SQLite에서 사용자 데이터 조회
            collected_files = self.sqlite_meta.get_collected_files(user_id)
            collected_browser = self.sqlite_meta.get_collected_browser_history(user_id)
            collected_apps = self.sqlite_meta.get_collected_apps(user_id)
            
            # 관심사 추출
            interests = self._extract_interests_from_data(collected_files, collected_browser, collected_apps)
            
            # 간단한 사용자 프로필 생성
            total_interactions = len(collected_files) + len(collected_browser) + len(collected_apps)
            experience_level = self._estimate_experience_level_simple(total_interactions)
            
            return {
                "user_id": user_id,
                "username": f"User_{user_id}",
                "total_interactions": total_interactions,
                "agent_usage": {"general": total_interactions},
                "interests": interests,
                "experience_level": experience_level
            }
        except Exception as e:
            return {
                "user_id": user_id,
                "username": "Unknown",
                "total_interactions": 0,
                "agent_usage": {},
                "interests": [],
                "experience_level": "beginner"
            }
    
    def _estimate_experience_level_simple(self, total_interactions: int) -> str:
        """사용자의 경험 수준을 추정합니다."""
        if total_interactions < 10:
            return "beginner"
        elif total_interactions < 50:
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