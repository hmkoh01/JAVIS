import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ..base_agent import BaseAgent, AgentResponse
from database.models import User, UserInteraction, UserAnalytics
from database.connection import get_db_session

class DashboardAgent(BaseAgent):
    """대시보드 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_type="dashboard",
            description="사용자 정보를 기반으로 그래프 분석 대시보드를 생성하는 에이전트"
        )
    
    async def process(self, user_input: str, user_id: Optional[int] = None) -> AgentResponse:
        """사용자 입력을 처리합니다."""
        try:
            if not user_id:
                return AgentResponse(
                    success=False,
                    content="사용자 ID가 필요합니다.",
                    agent_type=self.agent_type
                )
            
            # 대시보드 타입 분석
            dashboard_type = self._analyze_dashboard_type(user_input)
            
            if dashboard_type == "interaction_analysis":
                return await self._generate_interaction_dashboard(user_id)
            elif dashboard_type == "usage_patterns":
                return await self._generate_usage_patterns_dashboard(user_id)
            elif dashboard_type == "performance_metrics":
                return await self._generate_performance_dashboard(user_id)
            elif dashboard_type == "comprehensive":
                return await self._generate_comprehensive_dashboard(user_id)
            else:
                return await self._generate_comprehensive_dashboard(user_id)
                
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"대시보드 생성 중 오류가 발생했습니다: {str(e)}",
                agent_type=self.agent_type
            )
    
    def _analyze_dashboard_type(self, user_input: str) -> str:
        """대시보드 타입을 분석합니다."""
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ["상호작용", "interaction", "대화"]):
            return "interaction_analysis"
        elif any(word in input_lower for word in ["사용 패턴", "usage", "패턴"]):
            return "usage_patterns"
        elif any(word in input_lower for word in ["성능", "performance", "메트릭"]):
            return "performance_metrics"
        else:
            return "comprehensive"
    
    async def _generate_interaction_dashboard(self, user_id: int) -> AgentResponse:
        """상호작용 분석 대시보드를 생성합니다."""
        try:
            db = get_db_session()
            
            # 최근 30일간의 상호작용 데이터 조회
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            interactions = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id,
                UserInteraction.timestamp >= thirty_days_ago
            ).all()
            
            if not interactions:
                return AgentResponse(
                    success=True,
                    content="최근 30일간의 상호작용 데이터가 없습니다.",
                    agent_type=self.agent_type
                )
            
            # 데이터프레임 생성
            data = []
            for interaction in interactions:
                data.append({
                    'date': interaction.timestamp.date(),
                    'agent_type': interaction.agent_type,
                    'query_length': len(interaction.query),
                    'response_length': len(interaction.response)
                })
            
            df = pd.DataFrame(data)
            
            # 에이전트별 사용 빈도 차트
            agent_counts = df['agent_type'].value_counts()
            fig1 = go.Figure(data=[
                go.Bar(x=agent_counts.index, y=agent_counts.values)
            ])
            fig1.update_layout(
                title="에이전트별 사용 빈도",
                xaxis_title="에이전트 타입",
                yaxis_title="사용 횟수"
            )
            
            # 일별 상호작용 추이
            daily_interactions = df.groupby('date').size().reset_index(name='count')
            fig2 = go.Figure(data=[
                go.Scatter(x=daily_interactions['date'], y=daily_interactions['count'], mode='lines+markers')
            ])
            fig2.update_layout(
                title="일별 상호작용 추이",
                xaxis_title="날짜",
                yaxis_title="상호작용 수"
            )
            
            # 대화 길이 분포
            fig3 = go.Figure(data=[
                go.Histogram(x=df['query_length'], nbinsx=20, name='질문 길이'),
                go.Histogram(x=df['response_length'], nbinsx=20, name='답변 길이')
            ])
            fig3.update_layout(
                title="대화 길이 분포",
                xaxis_title="문자 수",
                yaxis_title="빈도",
                barmode='overlay'
            )
            
            dashboard_data = {
                "charts": [
                    {
                        "title": "에이전트별 사용 빈도",
                        "type": "bar",
                        "data": fig1.to_dict()
                    },
                    {
                        "title": "일별 상호작용 추이",
                        "type": "line",
                        "data": fig2.to_dict()
                    },
                    {
                        "title": "대화 길이 분포",
                        "type": "histogram",
                        "data": fig3.to_dict()
                    }
                ],
                "summary": {
                    "total_interactions": len(interactions),
                    "most_used_agent": agent_counts.index[0] if len(agent_counts) > 0 else "None",
                    "avg_query_length": df['query_length'].mean(),
                    "avg_response_length": df['response_length'].mean()
                }
            }
            
            return AgentResponse(
                success=True,
                content=dashboard_data,
                agent_type=self.agent_type,
                metadata={"dashboard_type": "interaction_analysis"}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"상호작용 대시보드 생성 중 오류: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def _generate_usage_patterns_dashboard(self, user_id: int) -> AgentResponse:
        """사용 패턴 대시보드를 생성합니다."""
        try:
            db = get_db_session()
            
            # 시간대별 사용 패턴 분석
            interactions = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id
            ).all()
            
            if not interactions:
                return AgentResponse(
                    success=True,
                    content="사용 패턴 데이터가 없습니다.",
                    agent_type=self.agent_type
                )
            
            # 시간대별 데이터
            hourly_data = []
            for interaction in interactions:
                hour = interaction.timestamp.hour
                hourly_data.append({
                    'hour': hour,
                    'agent_type': interaction.agent_type
                })
            
            df_hourly = pd.DataFrame(hourly_data)
            hourly_counts = df_hourly.groupby('hour').size()
            
            # 시간대별 사용 패턴 차트
            fig1 = go.Figure(data=[
                go.Bar(x=hourly_counts.index, y=hourly_counts.values)
            ])
            fig1.update_layout(
                title="시간대별 사용 패턴",
                xaxis_title="시간 (24시간)",
                yaxis_title="사용 횟수"
            )
            
            # 요일별 사용 패턴
            weekday_data = []
            for interaction in interactions:
                weekday = interaction.timestamp.strftime('%A')
                weekday_data.append({
                    'weekday': weekday,
                    'agent_type': interaction.agent_type
                })
            
            df_weekday = pd.DataFrame(weekday_data)
            weekday_counts = df_weekday.groupby('weekday').size()
            
            fig2 = go.Figure(data=[
                go.Bar(x=weekday_counts.index, y=weekday_counts.values)
            ])
            fig2.update_layout(
                title="요일별 사용 패턴",
                xaxis_title="요일",
                yaxis_title="사용 횟수"
            )
            
            dashboard_data = {
                "charts": [
                    {
                        "title": "시간대별 사용 패턴",
                        "type": "bar",
                        "data": fig1.to_dict()
                    },
                    {
                        "title": "요일별 사용 패턴",
                        "type": "bar",
                        "data": fig2.to_dict()
                    }
                ],
                "summary": {
                    "peak_hour": hourly_counts.idxmax() if len(hourly_counts) > 0 else "None",
                    "peak_weekday": weekday_counts.idxmax() if len(weekday_counts) > 0 else "None",
                    "total_usage_sessions": len(interactions)
                }
            }
            
            return AgentResponse(
                success=True,
                content=dashboard_data,
                agent_type=self.agent_type,
                metadata={"dashboard_type": "usage_patterns"}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"사용 패턴 대시보드 생성 중 오류: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def _generate_performance_dashboard(self, user_id: int) -> AgentResponse:
        """성능 메트릭 대시보드를 생성합니다."""
        try:
            db = get_db_session()
            
            # 성능 메트릭 데이터 조회
            analytics = db.query(UserAnalytics).filter(
                UserAnalytics.user_id == user_id
            ).all()
            
            if not analytics:
                return AgentResponse(
                    success=True,
                    content="성능 메트릭 데이터가 없습니다.",
                    agent_type=self.agent_type
                )
            
            # 메트릭별 데이터 정리
            metrics_data = {}
            for analytic in analytics:
                if analytic.metric_name not in metrics_data:
                    metrics_data[analytic.metric_name] = []
                metrics_data[analytic.metric_name].append({
                    'value': analytic.metric_value,
                    'timestamp': analytic.timestamp
                })
            
            charts = []
            for metric_name, data in metrics_data.items():
                df = pd.DataFrame(data)
                df = df.sort_values('timestamp')
                
                fig = go.Figure(data=[
                    go.Scatter(x=df['timestamp'], y=df['value'], mode='lines+markers')
                ])
                fig.update_layout(
                    title=f"{metric_name} 추이",
                    xaxis_title="시간",
                    yaxis_title="값"
                )
                
                charts.append({
                    "title": f"{metric_name} 추이",
                    "type": "line",
                    "data": fig.to_dict()
                })
            
            dashboard_data = {
                "charts": charts,
                "summary": {
                    "total_metrics": len(metrics_data),
                    "metric_names": list(metrics_data.keys())
                }
            }
            
            return AgentResponse(
                success=True,
                content=dashboard_data,
                agent_type=self.agent_type,
                metadata={"dashboard_type": "performance_metrics"}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"성능 메트릭 대시보드 생성 중 오류: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def _generate_comprehensive_dashboard(self, user_id: int) -> AgentResponse:
        """종합 대시보드를 생성합니다."""
        try:
            # 각 대시보드 타입의 요약 정보만 포함
            interaction_summary = await self._get_interaction_summary(user_id)
            usage_summary = await self._get_usage_summary(user_id)
            performance_summary = await self._get_performance_summary(user_id)
            
            dashboard_data = {
                "sections": [
                    {
                        "title": "상호작용 요약",
                        "data": interaction_summary
                    },
                    {
                        "title": "사용 패턴 요약",
                        "data": usage_summary
                    },
                    {
                        "title": "성능 메트릭 요약",
                        "data": performance_summary
                    }
                ]
            }
            
            return AgentResponse(
                success=True,
                content=dashboard_data,
                agent_type=self.agent_type,
                metadata={"dashboard_type": "comprehensive"}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                content=f"종합 대시보드 생성 중 오류: {str(e)}",
                agent_type=self.agent_type
            )
    
    async def _get_interaction_summary(self, user_id: int) -> Dict[str, Any]:
        """상호작용 요약 정보를 반환합니다."""
        try:
            db = get_db_session()
            interactions = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id
            ).all()
            
            if not interactions:
                return {"message": "상호작용 데이터가 없습니다."}
            
            agent_counts = {}
            for interaction in interactions:
                agent_counts[interaction.agent_type] = agent_counts.get(interaction.agent_type, 0) + 1
            
            return {
                "total_interactions": len(interactions),
                "agent_usage": agent_counts,
                "most_used_agent": max(agent_counts, key=agent_counts.get) if agent_counts else "None"
            }
        except:
            return {"error": "상호작용 요약을 가져올 수 없습니다."}
    
    async def _get_usage_summary(self, user_id: int) -> Dict[str, Any]:
        """사용 패턴 요약 정보를 반환합니다."""
        try:
            db = get_db_session()
            interactions = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id
            ).all()
            
            if not interactions:
                return {"message": "사용 패턴 데이터가 없습니다."}
            
            # 최근 사용 시간
            latest_interaction = max(interactions, key=lambda x: x.timestamp)
            
            return {
                "total_sessions": len(interactions),
                "latest_activity": latest_interaction.timestamp.isoformat(),
                "active_days": len(set(i.timestamp.date() for i in interactions))
            }
        except:
            return {"error": "사용 패턴 요약을 가져올 수 없습니다."}
    
    async def _get_performance_summary(self, user_id: int) -> Dict[str, Any]:
        """성능 메트릭 요약 정보를 반환합니다."""
        try:
            db = get_db_session()
            analytics = db.query(UserAnalytics).filter(
                UserAnalytics.user_id == user_id
            ).all()
            
            if not analytics:
                return {"message": "성능 메트릭 데이터가 없습니다."}
            
            metrics = {}
            for analytic in analytics:
                if analytic.metric_name not in metrics:
                    metrics[analytic.metric_name] = []
                metrics[analytic.metric_name].append(analytic.metric_value)
            
            summary = {}
            for metric_name, values in metrics.items():
                summary[metric_name] = {
                    "current": values[-1] if values else 0,
                    "average": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0
                }
            
            return summary
        except:
            return {"error": "성능 메트릭 요약을 가져올 수 없습니다."} 