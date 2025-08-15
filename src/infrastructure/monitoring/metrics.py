"""Application metrics collection and monitoring."""

import time
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from collections import defaultdict, Counter

import structlog
from prometheus_client import (
    Counter as PrometheusCounter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)

from ...core.config import settings


logger = structlog.get_logger(__name__)


class MetricType(Enum):
    """Types of metrics we track."""
    
    USER_ENGAGEMENT = "user_engagement"
    EMOTION_ANALYSIS = "emotion_analysis"
    CHECKIN_COMPLETION = "checkin_completion"
    API_PERFORMANCE = "api_performance"
    ERROR_TRACKING = "error_tracking"
    FEATURE_USAGE = "feature_usage"
    RETENTION = "retention"


@dataclass
class MetricEvent:
    """A single metric event."""
    
    event_type: MetricType
    user_id: int
    event_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    properties: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[int] = None
    success: bool = True


class PrometheusMetrics:
    """Prometheus metrics collector."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        
        # User engagement metrics
        self.user_messages_total = PrometheusCounter(
            'family_emotions_user_messages_total',
            'Total number of messages from users',
            ['user_id', 'message_type'],
            registry=self.registry
        )
        
        self.user_sessions_total = PrometheusCounter(
            'family_emotions_user_sessions_total',
            'Total number of user sessions',
            ['user_id'],
            registry=self.registry
        )
        
        self.active_users_gauge = Gauge(
            'family_emotions_active_users',
            'Number of currently active users',
            registry=self.registry
        )
        
        # Feature usage metrics
        self.emotion_translations_total = PrometheusCounter(
            'family_emotions_translations_total',
            'Total number of emotion translations',
            ['user_id', 'child_age_group', 'success'],
            registry=self.registry
        )
        
        self.checkins_total = PrometheusCounter(
            'family_emotions_checkins_total',
            'Total number of check-ins',
            ['user_id', 'completion_status'],
            registry=self.registry
        )
        
        self.weekly_reports_total = PrometheusCounter(
            'family_emotions_weekly_reports_total',
            'Total number of weekly reports generated',
            ['user_id'],
            registry=self.registry
        )
        
        # Performance metrics
        self.claude_api_duration = Histogram(
            'family_emotions_claude_api_duration_seconds',
            'Time spent calling Claude API',
            ['endpoint', 'success'],
            registry=self.registry
        )
        
        self.database_query_duration = Histogram(
            'family_emotions_database_query_duration_seconds',
            'Database query execution time',
            ['operation', 'table'],
            registry=self.registry
        )
        
        self.telegram_response_duration = Histogram(
            'family_emotions_telegram_response_duration_seconds',
            'Time to respond to Telegram messages',
            ['handler_type', 'success'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = PrometheusCounter(
            'family_emotions_errors_total',
            'Total number of errors',
            ['error_type', 'service'],
            registry=self.registry
        )
        
        self.claude_api_errors_total = PrometheusCounter(
            'family_emotions_claude_api_errors_total',
            'Claude API errors',
            ['error_code', 'error_type'],
            registry=self.registry
        )
        
        # Business metrics
        self.user_retention_gauge = Gauge(
            'family_emotions_user_retention',
            'User retention rate',
            ['period'],  # day_1, day_7, day_30
            registry=self.registry
        )
        
        self.emotion_analysis_confidence = Histogram(
            'family_emotions_analysis_confidence',
            'Confidence scores of emotion analyses',
            ['child_age_group'],
            registry=self.registry
        )
    
    def record_user_message(self, user_id: int, message_type: str):
        """Record a user message."""
        self.user_messages_total.labels(
            user_id=str(user_id),
            message_type=message_type
        ).inc()
    
    def record_emotion_translation(
        self, 
        user_id: int, 
        child_age: int, 
        success: bool, 
        confidence: Optional[float] = None
    ):
        """Record an emotion translation."""
        age_group = self._get_age_group(child_age)
        
        self.emotion_translations_total.labels(
            user_id=str(user_id),
            child_age_group=age_group,
            success=str(success)
        ).inc()
        
        if confidence is not None:
            self.emotion_analysis_confidence.labels(
                child_age_group=age_group
            ).observe(confidence)
    
    def record_checkin(self, user_id: int, completed: bool):
        """Record a check-in."""
        status = "completed" if completed else "abandoned"
        self.checkins_total.labels(
            user_id=str(user_id),
            completion_status=status
        ).inc()
    
    def record_claude_api_call(self, endpoint: str, duration_seconds: float, success: bool):
        """Record Claude API call metrics."""
        self.claude_api_duration.labels(
            endpoint=endpoint,
            success=str(success)
        ).observe(duration_seconds)
    
    def record_database_query(self, operation: str, table: str, duration_seconds: float):
        """Record database query metrics."""
        self.database_query_duration.labels(
            operation=operation,
            table=table
        ).observe(duration_seconds)
    
    def record_error(self, error_type: str, service: str):
        """Record an error."""
        self.errors_total.labels(
            error_type=error_type,
            service=service
        ).inc()
    
    def update_active_users(self, count: int):
        """Update active users count."""
        self.active_users_gauge.set(count)
    
    def update_retention_rate(self, period: str, rate: float):
        """Update retention rate."""
        self.user_retention_gauge.labels(period=period).set(rate)
    
    def _get_age_group(self, age: int) -> str:
        """Get age group for child."""
        if age <= 3:
            return "toddler"
        elif age <= 6:
            return "preschool"
        elif age <= 10:
            return "elementary"
        elif age <= 14:
            return "middle_school"
        else:
            return "high_school"


class MetricsCollector:
    """Main metrics collection service."""
    
    def __init__(self):
        self.prometheus = PrometheusMetrics()
        self.events: List[MetricEvent] = []
        self.user_sessions: Dict[int, datetime] = {}
        self._active_users_cache = set()
        self._retention_cache: Dict[str, float] = {}
        
        # Start background tasks
        self._background_tasks = []
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background metric processing tasks."""
        # Update active users every minute
        task1 = asyncio.create_task(self._update_active_users_periodically())
        self._background_tasks.append(task1)
        
        # Calculate retention rates every hour
        task2 = asyncio.create_task(self._calculate_retention_periodically())
        self._background_tasks.append(task2)
        
        # Clean up old events every day
        task3 = asyncio.create_task(self._cleanup_old_events_periodically())
        self._background_tasks.append(task3)
    
    async def record_event(self, event: MetricEvent):
        """Record a metric event."""
        try:
            # Store event
            self.events.append(event)
            
            # Update session tracking
            if event.event_type == MetricType.USER_ENGAGEMENT:
                self.user_sessions[event.user_id] = event.timestamp
                self._active_users_cache.add(event.user_id)
            
            # Route to appropriate Prometheus metrics
            await self._route_to_prometheus(event)
            
            # Log structured event
            logger.info(
                "metric_event_recorded",
                event_type=event.event_type.value,
                user_id=event.user_id,
                event_name=event.event_name,
                duration_ms=event.duration_ms,
                success=event.success,
                **event.properties
            )
            
        except Exception as e:
            logger.error("Failed to record metric event", error=str(e), event=event)
    
    async def _route_to_prometheus(self, event: MetricEvent):
        """Route event to appropriate Prometheus metrics."""
        try:
            if event.event_type == MetricType.USER_ENGAGEMENT:
                self.prometheus.record_user_message(
                    event.user_id,
                    event.properties.get('message_type', 'unknown')
                )
            
            elif event.event_type == MetricType.EMOTION_ANALYSIS:
                self.prometheus.record_emotion_translation(
                    event.user_id,
                    event.properties.get('child_age', 8),
                    event.success,
                    event.properties.get('confidence')
                )
                
                # Record API performance
                if event.duration_ms:
                    self.prometheus.record_claude_api_call(
                        'emotion_analysis',
                        event.duration_ms / 1000.0,
                        event.success
                    )
            
            elif event.event_type == MetricType.CHECKIN_COMPLETION:
                self.prometheus.record_checkin(
                    event.user_id,
                    event.success
                )
            
            elif event.event_type == MetricType.ERROR_TRACKING:
                self.prometheus.record_error(
                    event.properties.get('error_type', 'unknown'),
                    event.properties.get('service', 'unknown')
                )
            
        except Exception as e:
            logger.error("Failed to route event to Prometheus", error=str(e))
    
    async def _update_active_users_periodically(self):
        """Update active users count every minute."""
        while True:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                # Count users active in last hour
                now = datetime.now()
                cutoff = now - timedelta(hours=1)
                
                active_count = sum(
                    1 for user_id, last_seen in self.user_sessions.items()
                    if last_seen >= cutoff
                )
                
                self.prometheus.update_active_users(active_count)
                
                # Clean old sessions
                self.user_sessions = {
                    user_id: last_seen
                    for user_id, last_seen in self.user_sessions.items()
                    if last_seen >= cutoff
                }
                
                logger.debug("Updated active users", count=active_count)
                
            except Exception as e:
                logger.error("Failed to update active users", error=str(e))
    
    async def _calculate_retention_periodically(self):
        """Calculate retention rates every hour."""
        while True:
            try:
                await asyncio.sleep(3600)  # Update every hour
                
                # This would typically query the database
                # For now, we'll use placeholder values
                retention_rates = {
                    'day_1': 0.75,  # Would calculate from actual user data
                    'day_7': 0.45,
                    'day_30': 0.25
                }
                
                for period, rate in retention_rates.items():
                    self.prometheus.update_retention_rate(period, rate)
                    self._retention_cache[period] = rate
                
                logger.debug("Updated retention rates", rates=retention_rates)
                
            except Exception as e:
                logger.error("Failed to calculate retention", error=str(e))
    
    async def _cleanup_old_events_periodically(self):
        """Clean up old events every day."""
        while True:
            try:
                await asyncio.sleep(86400)  # Clean up every day
                
                # Keep events for last 7 days
                cutoff = datetime.now() - timedelta(days=7)
                self.events = [
                    event for event in self.events
                    if event.timestamp >= cutoff
                ]
                
                logger.info("Cleaned up old events", events_remaining=len(self.events))
                
            except Exception as e:
                logger.error("Failed to cleanup old events", error=str(e))
    
    def get_prometheus_metrics(self) -> bytes:
        """Get Prometheus metrics in exposition format."""
        return generate_latest(self.prometheus.registry)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics."""
        now = datetime.now()
        
        # Count events by type in last 24 hours
        cutoff = now - timedelta(days=1)
        recent_events = [e for e in self.events if e.timestamp >= cutoff]
        
        event_counts = Counter(e.event_type.value for e in recent_events)
        
        # Count active users
        active_users = len([
            user_id for user_id, last_seen in self.user_sessions.items()
            if last_seen >= now - timedelta(hours=1)
        ])
        
        return {
            'timestamp': now.isoformat(),
            'active_users': active_users,
            'total_events_24h': len(recent_events),
            'events_by_type': dict(event_counts),
            'retention_rates': self._retention_cache.copy(),
            'total_events_stored': len(self.events)
        }
    
    async def shutdown(self):
        """Shutdown metrics collector."""
        logger.info("Shutting down metrics collector")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logger.info("Metrics collector shutdown complete")


# Global metrics collector instance
metrics_collector = MetricsCollector()


# Convenience functions for common metrics
async def track_user_message(user_id: int, message_type: str, properties: Dict[str, Any] = None):
    """Track a user message."""
    event = MetricEvent(
        event_type=MetricType.USER_ENGAGEMENT,
        user_id=user_id,
        event_name="message_received",
        properties={
            'message_type': message_type,
            **(properties or {})
        }
    )
    await metrics_collector.record_event(event)


async def track_emotion_analysis(
    user_id: int,
    child_age: int,
    success: bool,
    confidence: Optional[float] = None,
    duration_ms: Optional[int] = None,
    properties: Dict[str, Any] = None
):
    """Track an emotion analysis."""
    event = MetricEvent(
        event_type=MetricType.EMOTION_ANALYSIS,
        user_id=user_id,
        event_name="emotion_analyzed",
        success=success,
        duration_ms=duration_ms,
        properties={
            'child_age': child_age,
            'confidence': confidence,
            **(properties or {})
        }
    )
    await metrics_collector.record_event(event)


async def track_checkin_completion(user_id: int, completed: bool, properties: Dict[str, Any] = None):
    """Track a check-in completion."""
    event = MetricEvent(
        event_type=MetricType.CHECKIN_COMPLETION,
        user_id=user_id,
        event_name="checkin_completed" if completed else "checkin_abandoned",
        success=completed,
        properties=properties or {}
    )
    await metrics_collector.record_event(event)


async def track_error(
    user_id: int,
    error_type: str,
    service: str,
    error_message: str = "",
    properties: Dict[str, Any] = None
):
    """Track an error."""
    event = MetricEvent(
        event_type=MetricType.ERROR_TRACKING,
        user_id=user_id,
        event_name="error_occurred",
        success=False,
        properties={
            'error_type': error_type,
            'service': service,
            'error_message': error_message,
            **(properties or {})
        }
    )
    await metrics_collector.record_event(event)


async def track_feature_usage(
    user_id: int,
    feature_name: str,
    success: bool = True,
    duration_ms: Optional[int] = None,
    properties: Dict[str, Any] = None
):
    """Track feature usage."""
    event = MetricEvent(
        event_type=MetricType.FEATURE_USAGE,
        user_id=user_id,
        event_name=f"feature_{feature_name}_used",
        success=success,
        duration_ms=duration_ms,
        properties=properties or {}
    )
    await metrics_collector.record_event(event)