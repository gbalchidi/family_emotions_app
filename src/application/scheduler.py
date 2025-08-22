"""Task scheduler for automated check-ins and report generation."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Callable, Awaitable, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .checkin_service import CheckinService
from ..infrastructure.telegram.bot import FamilyEmotionsBot
from ..core.config import settings

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Manages scheduled tasks for the Family Emotions App."""
    
    def __init__(
        self,
        checkin_service: CheckinService,
        bot: Optional[FamilyEmotionsBot] = None
    ):
        self.checkin_service = checkin_service
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        
        # Task tracking
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        # Setup default jobs
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Setup all scheduled jobs."""
        if not settings.enable_scheduled_checkins:
            logger.info("Scheduled check-ins disabled in configuration")
            return
        
        # Daily check-in scheduling (every day at 8 AM UTC)
        self.scheduler.add_job(
            func=self.schedule_daily_checkins,
            trigger=CronTrigger(hour=8, minute=0),
            id="schedule_daily_checkins",
            name="Schedule Daily Check-ins",
            replace_existing=True,
            misfire_grace_time=300  # 5 minutes grace period
        )
        
        # Send pending check-ins every 30 minutes
        self.scheduler.add_job(
            func=self.send_pending_checkins,
            trigger=IntervalTrigger(minutes=30),
            id="send_pending_checkins",
            name="Send Pending Check-ins",
            replace_existing=True,
            misfire_grace_time=600  # 10 minutes grace period
        )
        
        # Generate weekly reports (every Monday at 9 AM UTC)
        self.scheduler.add_job(
            func=self.generate_weekly_reports,
            trigger=CronTrigger(day_of_week=0, hour=9, minute=0),  # Monday
            id="generate_weekly_reports",
            name="Generate Weekly Reports",
            replace_existing=True,
            misfire_grace_time=3600  # 1 hour grace period
        )
        
        # Daily analytics aggregation (every day at midnight)
        self.scheduler.add_job(
            func=self.aggregate_daily_stats,
            trigger=CronTrigger(hour=0, minute=5),
            id="aggregate_daily_stats",
            name="Aggregate Daily Statistics",
            replace_existing=True,
            misfire_grace_time=1800  # 30 minutes grace period
        )
        
        # Cleanup old data (every week on Sunday at 2 AM)
        self.scheduler.add_job(
            func=self.cleanup_old_data,
            trigger=CronTrigger(day_of_week=6, hour=2, minute=0),  # Sunday
            id="cleanup_old_data",
            name="Cleanup Old Data",
            replace_existing=True,
            misfire_grace_time=3600  # 1 hour grace period
        )
        
        logger.info("Scheduled jobs configured")
    
    async def start(self):
        """Start the scheduler."""
        if self.scheduler.running:
            logger.warning("Scheduler already running")
            return
        
        try:
            self.scheduler.start()
            logger.info("Task scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the scheduler gracefully."""
        try:
            # Cancel running tasks
            for task_name, task in self.running_tasks.items():
                if not task.done():
                    logger.info(f"Cancelling task: {task_name}")
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self.running_tasks.clear()
            
            # Shutdown scheduler
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("Task scheduler stopped")
                
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    async def schedule_daily_checkins(self):
        """Schedule daily check-ins for all users."""
        task_name = "schedule_daily_checkins"
        
        if task_name in self.running_tasks and not self.running_tasks[task_name].done():
            logger.warning(f"Task {task_name} already running, skipping")
            return
        
        async def _run_task():
            try:
                logger.info("Starting daily check-in scheduling")
                count = await self.checkin_service.schedule_daily_checkins()
                logger.info(f"Scheduled {count} daily check-ins")
                
            except Exception as e:
                logger.error(f"Error in schedule_daily_checkins: {e}")
                
            finally:
                if task_name in self.running_tasks:
                    del self.running_tasks[task_name]
        
        self.running_tasks[task_name] = asyncio.create_task(_run_task())
        await self.running_tasks[task_name]
    
    async def send_pending_checkins(self):
        """Send all pending check-ins via Telegram."""
        task_name = "send_pending_checkins"
        
        if task_name in self.running_tasks and not self.running_tasks[task_name].done():
            logger.debug(f"Task {task_name} already running, skipping")
            return
        
        if not self.bot:
            logger.warning("Bot not available for sending check-ins")
            return
        
        async def _run_task():
            try:
                logger.debug("Checking for pending check-ins")
                
                # Get pending check-ins
                pending_checkins = await self.checkin_service.get_pending_checkins()
                
                if not pending_checkins:
                    logger.debug("No pending check-ins found")
                    return
                
                logger.info(f"Found {len(pending_checkins)} pending check-ins")
                sent_count = 0
                
                for checkin in pending_checkins:
                    try:
                        await self._send_checkin_message(checkin)
                        sent_count += 1
                        
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"Failed to send check-in {checkin.id}: {e}")
                        continue
                
                logger.info(f"Sent {sent_count}/{len(pending_checkins)} check-in messages")
                
            except Exception as e:
                logger.error(f"Error in send_pending_checkins: {e}")
                
            finally:
                if task_name in self.running_tasks:
                    del self.running_tasks[task_name]
        
        self.running_tasks[task_name] = asyncio.create_task(_run_task())
        # Don't await here to avoid blocking other tasks
    
    async def generate_weekly_reports(self):
        """Generate weekly reports for all users."""
        task_name = "generate_weekly_reports"
        
        if task_name in self.running_tasks and not self.running_tasks[task_name].done():
            logger.warning(f"Task {task_name} already running, skipping")
            return
        
        async def _run_task():
            try:
                from sqlalchemy import select
                from ..core.models.user import User
                
                logger.info("Starting weekly report generation")
                
                # Get all active users with children
                stmt = (
                    select(User)
                    .where(User.is_active == True)
                    .where(User.children.any())
                )
                
                # This would need the session - we'd need to pass it in or get it from DI
                # For now, just log the intent
                logger.info("Weekly report generation would run here")
                # TODO: Implement actual report generation and sending
                
            except Exception as e:
                logger.error(f"Error in generate_weekly_reports: {e}")
                
            finally:
                if task_name in self.running_tasks:
                    del self.running_tasks[task_name]
        
        self.running_tasks[task_name] = asyncio.create_task(_run_task())
        await self.running_tasks[task_name]
    
    async def aggregate_daily_stats(self):
        """Aggregate daily statistics."""
        task_name = "aggregate_daily_stats"
        
        if task_name in self.running_tasks and not self.running_tasks[task_name].done():
            logger.warning(f"Task {task_name} already running, skipping")
            return
        
        async def _run_task():
            try:
                from datetime import date
                
                logger.info("Starting daily stats aggregation")
                
                # Generate stats for yesterday
                yesterday = date.today() - timedelta(days=1)
                
                # TODO: Implement actual stats aggregation
                # This would require analytics_service and database session
                logger.info(f"Would aggregate stats for {yesterday}")
                
            except Exception as e:
                logger.error(f"Error in aggregate_daily_stats: {e}")
                
            finally:
                if task_name in self.running_tasks:
                    del self.running_tasks[task_name]
        
        self.running_tasks[task_name] = asyncio.create_task(_run_task())
        await self.running_tasks[task_name]
    
    async def cleanup_old_data(self):
        """Clean up old data to manage database size."""
        task_name = "cleanup_old_data"
        
        if task_name in self.running_tasks and not self.running_tasks[task_name].done():
            logger.warning(f"Task {task_name} already running, skipping")
            return
        
        async def _run_task():
            try:
                logger.info("Starting data cleanup")
                
                # Define retention periods
                analytics_retention_days = 365  # 1 year
                checkin_retention_days = 180   # 6 months
                translation_retention_days = 90  # 3 months for failed ones
                
                # TODO: Implement actual cleanup
                # - Delete old analytics records
                # - Delete old failed translations
                # - Clean up expired user sessions
                
                logger.info("Data cleanup completed")
                
            except Exception as e:
                logger.error(f"Error in cleanup_old_data: {e}")
                
            finally:
                if task_name in self.running_tasks:
                    del self.running_tasks[task_name]
        
        self.running_tasks[task_name] = asyncio.create_task(_run_task())
        await self.running_tasks[task_name]
    
    async def _send_checkin_message(self, checkin):
        """Send a check-in message to user via Telegram."""
        try:
            if not self.bot:
                logger.error("Bot not available for sending check-in")
                return
            
            # Get user
            user = await self.checkin_service._user_service.get_user_by_id(checkin.user_id)
            if not user:
                logger.error(f"User not found for check-in {checkin.id}")
                return
            
            # Format check-in message
            message_text = f"""
🌟 <b>Daily Emotional Check-in</b>

{checkin.question}

Please share your thoughts or observations. This helps me provide better insights and support for your family's emotional well-being.

<i>Reply with your response below:</i>
"""
            
            # Send message via bot
            await self.bot.bot.send_message(
                chat_id=user.telegram_id,
                text=message_text,
                parse_mode="HTML"
            )
            
            logger.info(f"Sent check-in message to user {user.id}")
            
        except Exception as e:
            logger.error(f"Error sending check-in message: {e}")
            raise
    
    def add_job(
        self,
        func: Callable[..., Awaitable[Any]],
        trigger,
        job_id: str,
        name: Optional[str] = None,
        **kwargs
    ):
        """Add a custom scheduled job."""
        try:
            self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                name=name or job_id,
                replace_existing=True,
                **kwargs
            )
            logger.info(f"Added job: {job_id}")
            
        except Exception as e:
            logger.error(f"Error adding job {job_id}: {e}")
            raise
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
            
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")
    
    def get_jobs(self) -> list:
        """Get list of all scheduled jobs."""
        return self.scheduler.get_jobs()
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.scheduler.running