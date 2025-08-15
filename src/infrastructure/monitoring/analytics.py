"""Analytics and business metrics tracking."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
from enum import Enum

import structlog

from ...core.config import settings
from .metrics import MetricEvent, MetricType


logger = structlog.get_logger(__name__)


class AnalyticsEvent(Enum):
    """Types of analytics events."""
    
    USER_REGISTERED = "user_registered"
    USER_ONBOARDED = "user_onboarded"
    FIRST_EMOTION_ANALYSIS = "first_emotion_analysis"
    FIRST_CHECKIN = "first_checkin"
    WEEKLY_REPORT_GENERATED = "weekly_report_generated"
    USER_RETURNED = "user_returned"
    FEATURE_DISCOVERED = "feature_discovered"
    HELP_REQUESTED = "help_requested"
    ERROR_ENCOUNTERED = "error_encountered"


@dataclass
class UserJourney:
    """Tracks a user's journey through the application."""
    
    user_id: int
    registration_date: datetime
    onboarding_completed: bool = False
    onboarding_date: Optional[datetime] = None
    first_emotion_analysis: Optional[datetime] = None
    first_checkin: Optional[datetime] = None
    last_active: Optional[datetime] = None
    total_sessions: int = 0
    total_emotion_analyses: int = 0
    total_checkins: int = 0
    weekly_reports_generated: int = 0
    help_requests: int = 0
    errors_encountered: int = 0
    features_used: List[str] = field(default_factory=list)
    children_count: int = 0


@dataclass
class CohortMetrics:
    """Metrics for a user cohort."""
    
    cohort_date: datetime
    initial_users: int
    day_1_retained: int = 0
    day_7_retained: int = 0
    day_30_retained: int = 0
    onboarding_completion_rate: float = 0.0
    first_analysis_rate: float = 0.0
    first_checkin_rate: float = 0.0
    avg_analyses_per_user: float = 0.0
    avg_checkins_per_user: float = 0.0


class AnalyticsService:
    """Analytics and business intelligence service."""
    
    def __init__(self):
        self.user_journeys: Dict[int, UserJourney] = {}
        self.cohorts: Dict[str, CohortMetrics] = {}  # date_string -> metrics
        self.funnel_events: List[Dict[str, Any]] = []
        self._background_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    def start_analytics(self):
        """Start background analytics processing."""
        if self._background_task is None or self._background_task.done():
            self._shutdown = False
            self._background_task = asyncio.create_task(self._process_analytics())
            logger.info("Analytics service started")
    
    async def stop_analytics(self):
        """Stop background analytics processing."""
        self._shutdown = True
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            logger.info("Analytics service stopped")
    
    async def _process_analytics(self):
        """Background task to process analytics."""
        while not self._shutdown:
            try:
                # Update cohort metrics every hour
                await self._update_cohort_metrics()
                
                # Generate insights every 6 hours
                if datetime.now().hour % 6 == 0:
                    await self._generate_insights()
                
                # Clean up old data daily
                if datetime.now().hour == 2:  # 2 AM
                    await self._cleanup_old_data()
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error("Analytics processing error", error=str(e))
                await asyncio.sleep(3600)
    
    async def track_user_event(
        self,
        user_id: int,
        event: AnalyticsEvent,
        properties: Optional[Dict[str, Any]] = None
    ):
        """Track a user analytics event."""
        try:
            # Get or create user journey
            if user_id not in self.user_journeys:
                self.user_journeys[user_id] = UserJourney(
                    user_id=user_id,
                    registration_date=datetime.now()
                )
            
            journey = self.user_journeys[user_id]
            journey.last_active = datetime.now()
            
            # Update journey based on event type
            await self._update_user_journey(journey, event, properties)
            
            # Add to funnel tracking
            self.funnel_events.append({
                'user_id': user_id,
                'event': event.value,
                'timestamp': datetime.now().isoformat(),
                'properties': properties or {}
            })
            
            logger.info(
                "analytics_event_tracked",
                user_id=user_id,
                event=event.value,
                properties=properties
            )
            
        except Exception as e:
            logger.error("Failed to track analytics event", error=str(e))
    
    async def _update_user_journey(
        self,
        journey: UserJourney,
        event: AnalyticsEvent,
        properties: Optional[Dict[str, Any]]
    ):
        """Update user journey based on event."""
        now = datetime.now()
        
        if event == AnalyticsEvent.USER_ONBOARDED:
            journey.onboarding_completed = True
            journey.onboarding_date = now
            if properties:
                journey.children_count = properties.get('children_count', 0)
        
        elif event == AnalyticsEvent.FIRST_EMOTION_ANALYSIS:
            if not journey.first_emotion_analysis:
                journey.first_emotion_analysis = now
            journey.total_emotion_analyses += 1
        
        elif event == AnalyticsEvent.FIRST_CHECKIN:
            if not journey.first_checkin:
                journey.first_checkin = now
            journey.total_checkins += 1
        
        elif event == AnalyticsEvent.WEEKLY_REPORT_GENERATED:
            journey.weekly_reports_generated += 1
        
        elif event == AnalyticsEvent.HELP_REQUESTED:
            journey.help_requests += 1
        
        elif event == AnalyticsEvent.ERROR_ENCOUNTERED:
            journey.errors_encountered += 1
        
        elif event == AnalyticsEvent.FEATURE_DISCOVERED:
            feature_name = properties.get('feature_name') if properties else None
            if feature_name and feature_name not in journey.features_used:
                journey.features_used.append(feature_name)
    
    async def _update_cohort_metrics(self):
        """Update cohort analysis metrics."""
        try:
            # Group users by registration date
            cohorts = defaultdict(list)
            
            for journey in self.user_journeys.values():
                cohort_date = journey.registration_date.date()
                cohorts[cohort_date].append(journey)
            
            # Calculate metrics for each cohort
            for cohort_date, journeys in cohorts.items():
                cohort_key = cohort_date.isoformat()
                
                if cohort_key not in self.cohorts:
                    self.cohorts[cohort_key] = CohortMetrics(
                        cohort_date=datetime.combine(cohort_date, datetime.min.time()),
                        initial_users=len(journeys)
                    )
                
                cohort = self.cohorts[cohort_key]
                cohort.initial_users = len(journeys)
                
                # Calculate retention
                now = datetime.now()
                day_1_cutoff = cohort.cohort_date + timedelta(days=1)
                day_7_cutoff = cohort.cohort_date + timedelta(days=7)
                day_30_cutoff = cohort.cohort_date + timedelta(days=30)
                
                if now >= day_1_cutoff:
                    cohort.day_1_retained = sum(
                        1 for j in journeys
                        if j.last_active and j.last_active >= day_1_cutoff
                    )
                
                if now >= day_7_cutoff:
                    cohort.day_7_retained = sum(
                        1 for j in journeys
                        if j.last_active and j.last_active >= day_7_cutoff
                    )
                
                if now >= day_30_cutoff:
                    cohort.day_30_retained = sum(
                        1 for j in journeys
                        if j.last_active and j.last_active >= day_30_cutoff
                    )
                
                # Calculate conversion rates
                total_users = len(journeys)
                if total_users > 0:
                    cohort.onboarding_completion_rate = sum(
                        1 for j in journeys if j.onboarding_completed
                    ) / total_users
                    
                    cohort.first_analysis_rate = sum(
                        1 for j in journeys if j.first_emotion_analysis
                    ) / total_users
                    
                    cohort.first_checkin_rate = sum(
                        1 for j in journeys if j.first_checkin
                    ) / total_users
                    
                    cohort.avg_analyses_per_user = sum(
                        j.total_emotion_analyses for j in journeys
                    ) / total_users
                    
                    cohort.avg_checkins_per_user = sum(
                        j.total_checkins for j in journeys
                    ) / total_users
            
            logger.debug("Cohort metrics updated", cohort_count=len(self.cohorts))
            
        except Exception as e:
            logger.error("Failed to update cohort metrics", error=str(e))
    
    async def _generate_insights(self):
        """Generate analytical insights."""
        try:
            insights = []
            
            # Overall user insights
            total_users = len(self.user_journeys)
            active_users_24h = sum(
                1 for j in self.user_journeys.values()
                if j.last_active and j.last_active >= datetime.now() - timedelta(days=1)
            )
            
            onboarded_users = sum(
                1 for j in self.user_journeys.values()
                if j.onboarding_completed
            )
            
            insights.append(f"Total users: {total_users}")
            insights.append(f"Active in 24h: {active_users_24h}")
            insights.append(f"Onboarded users: {onboarded_users}")
            
            # Feature adoption
            feature_usage = Counter()
            for journey in self.user_journeys.values():
                for feature in journey.features_used:
                    feature_usage[feature] += 1
            
            if feature_usage:
                top_features = feature_usage.most_common(3)
                insights.append(f"Top features: {', '.join([f'{name} ({count})' for name, count in top_features])}")
            
            # Retention insights
            recent_cohorts = [
                cohort for cohort in self.cohorts.values()
                if cohort.cohort_date >= datetime.now() - timedelta(days=30)
            ]
            
            if recent_cohorts:
                avg_day_7_retention = sum(
                    cohort.day_7_retained / max(cohort.initial_users, 1)
                    for cohort in recent_cohorts
                    if datetime.now() >= cohort.cohort_date + timedelta(days=7)
                ) / len(recent_cohorts)
                
                insights.append(f"Avg 7-day retention: {avg_day_7_retention:.2%}")
            
            logger.info("Analytics insights generated", insights=insights)
            
        except Exception as e:
            logger.error("Failed to generate insights", error=str(e))
    
    async def _cleanup_old_data(self):
        """Clean up old analytics data."""
        try:
            # Keep funnel events for last 30 days
            cutoff = datetime.now() - timedelta(days=30)
            self.funnel_events = [
                event for event in self.funnel_events
                if datetime.fromisoformat(event['timestamp']) >= cutoff
            ]
            
            # Keep cohorts for last 90 days
            cohort_cutoff = datetime.now() - timedelta(days=90)
            old_cohort_keys = [
                key for key, cohort in self.cohorts.items()
                if cohort.cohort_date < cohort_cutoff
            ]
            
            for key in old_cohort_keys:
                del self.cohorts[key]
            
            logger.info(
                "Analytics data cleaned",
                funnel_events_remaining=len(self.funnel_events),
                cohorts_remaining=len(self.cohorts)
            )
            
        except Exception as e:
            logger.error("Failed to cleanup analytics data", error=str(e))
    
    def get_user_journey(self, user_id: int) -> Optional[UserJourney]:
        """Get user journey data."""
        return self.user_journeys.get(user_id)
    
    def get_cohort_analysis(self) -> Dict[str, Any]:
        """Get cohort analysis data."""
        cohort_data = []
        
        for cohort in sorted(self.cohorts.values(), key=lambda c: c.cohort_date):
            cohort_data.append({
                'date': cohort.cohort_date.date().isoformat(),
                'initial_users': cohort.initial_users,
                'day_1_retained': cohort.day_1_retained,
                'day_7_retained': cohort.day_7_retained,
                'day_30_retained': cohort.day_30_retained,
                'onboarding_rate': cohort.onboarding_completion_rate,
                'first_analysis_rate': cohort.first_analysis_rate,
                'first_checkin_rate': cohort.first_checkin_rate,
                'avg_analyses_per_user': cohort.avg_analyses_per_user,
                'avg_checkins_per_user': cohort.avg_checkins_per_user
            })
        
        return {
            'cohorts': cohort_data,
            'total_cohorts': len(cohort_data),
            'last_updated': datetime.now().isoformat()
        }
    
    def get_funnel_analysis(self) -> Dict[str, Any]:
        """Get conversion funnel analysis."""
        if not self.funnel_events:
            return {'stages': [], 'conversion_rates': []}
        
        # Define funnel stages
        stages = [
            AnalyticsEvent.USER_REGISTERED,
            AnalyticsEvent.USER_ONBOARDED,
            AnalyticsEvent.FIRST_EMOTION_ANALYSIS,
            AnalyticsEvent.FIRST_CHECKIN
        ]
        
        # Count users at each stage
        stage_counts = {}
        user_stages = defaultdict(set)
        
        for event in self.funnel_events:
            event_type = event['event']
            user_id = event['user_id']
            
            for stage in stages:
                if stage.value == event_type:
                    user_stages[stage].add(user_id)
        
        # Calculate conversion rates
        funnel_data = []
        previous_count = None
        
        for stage in stages:
            current_count = len(user_stages[stage])
            conversion_rate = None
            
            if previous_count is not None and previous_count > 0:
                conversion_rate = current_count / previous_count
            
            funnel_data.append({
                'stage': stage.value,
                'users': current_count,
                'conversion_rate': conversion_rate
            })
            
            previous_count = current_count
        
        return {
            'funnel': funnel_data,
            'last_updated': datetime.now().isoformat()
        }
    
    def get_feature_usage(self) -> Dict[str, Any]:
        """Get feature usage statistics."""
        feature_stats = defaultdict(int)
        user_feature_counts = defaultdict(lambda: defaultdict(int))
        
        for journey in self.user_journeys.values():
            for feature in journey.features_used:
                feature_stats[feature] += 1
                user_feature_counts[journey.user_id][feature] += 1
        
        # Calculate feature adoption rates
        total_users = len(self.user_journeys)
        feature_adoption = {}
        
        for feature, count in feature_stats.items():
            feature_adoption[feature] = {
                'total_users': count,
                'adoption_rate': count / total_users if total_users > 0 else 0,
                'avg_usage_per_user': sum(
                    counts[feature] for counts in user_feature_counts.values()
                ) / max(count, 1)
            }
        
        return {
            'feature_adoption': feature_adoption,
            'total_features': len(feature_stats),
            'last_updated': datetime.now().isoformat()
        }
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary."""
        total_users = len(self.user_journeys)
        
        if total_users == 0:
            return {
                'total_users': 0,
                'message': 'No user data available'
            }
        
        # User metrics
        onboarded = sum(1 for j in self.user_journeys.values() if j.onboarding_completed)
        analyzed_emotions = sum(1 for j in self.user_journeys.values() if j.first_emotion_analysis)
        completed_checkins = sum(1 for j in self.user_journeys.values() if j.first_checkin)
        
        # Activity metrics
        active_24h = sum(
            1 for j in self.user_journeys.values()
            if j.last_active and j.last_active >= datetime.now() - timedelta(days=1)
        )
        
        active_7d = sum(
            1 for j in self.user_journeys.values()
            if j.last_active and j.last_active >= datetime.now() - timedelta(days=7)
        )
        
        # Engagement metrics
        total_analyses = sum(j.total_emotion_analyses for j in self.user_journeys.values())
        total_checkins = sum(j.total_checkins for j in self.user_journeys.values())
        
        return {
            'user_metrics': {
                'total_users': total_users,
                'onboarded_users': onboarded,
                'onboarding_rate': onboarded / total_users,
                'analyzed_emotions': analyzed_emotions,
                'completed_checkins': completed_checkins
            },
            'activity_metrics': {
                'active_24h': active_24h,
                'active_7d': active_7d,
                'daily_active_rate': active_24h / total_users,
                'weekly_active_rate': active_7d / total_users
            },
            'engagement_metrics': {
                'total_emotion_analyses': total_analyses,
                'total_checkins': total_checkins,
                'avg_analyses_per_user': total_analyses / total_users,
                'avg_checkins_per_user': total_checkins / total_users
            },
            'last_updated': datetime.now().isoformat()
        }


# Global analytics service instance
analytics_service = AnalyticsService()


# Convenience functions
async def track_user_registered(user_id: int, properties: Optional[Dict[str, Any]] = None):
    """Track user registration event."""
    await analytics_service.track_user_event(
        user_id, AnalyticsEvent.USER_REGISTERED, properties
    )


async def track_user_onboarded(
    user_id: int, 
    children_count: int,
    properties: Optional[Dict[str, Any]] = None
):
    """Track user onboarding completion."""
    props = {'children_count': children_count}
    if properties:
        props.update(properties)
    
    await analytics_service.track_user_event(
        user_id, AnalyticsEvent.USER_ONBOARDED, props
    )


async def track_first_emotion_analysis(user_id: int, properties: Optional[Dict[str, Any]] = None):
    """Track first emotion analysis."""
    await analytics_service.track_user_event(
        user_id, AnalyticsEvent.FIRST_EMOTION_ANALYSIS, properties
    )


async def track_first_checkin(user_id: int, properties: Optional[Dict[str, Any]] = None):
    """Track first check-in."""
    await analytics_service.track_user_event(
        user_id, AnalyticsEvent.FIRST_CHECKIN, properties
    )