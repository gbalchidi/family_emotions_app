"""Dependency injection container for Family Emotions App."""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .services import UserService, FamilyService, AnalyticsService
from ..infrastructure.database import DatabaseManager
from ..infrastructure.cache import RedisService, CacheService
from ..infrastructure.external import ClaudeService, EmotionService
from ..infrastructure.telegram import FamilyEmotionsBot, setup_handlers
from ..application.checkin_service import CheckinService
from ..application.scheduler import TaskScheduler

logger = logging.getLogger(__name__)


class Container:
    """Dependency injection container."""
    
    def __init__(self):
        # Infrastructure
        self._db_manager: Optional[DatabaseManager] = None
        self._redis_service: Optional[RedisService] = None
        self._cache_service: Optional[CacheService] = None
        
        # External services  
        self._claude_service: Optional[ClaudeService] = None
        
        # Core services
        self._user_service: Optional[UserService] = None
        self._family_service: Optional[FamilyService] = None
        self._analytics_service: Optional[AnalyticsService] = None
        self._emotion_service: Optional[EmotionService] = None
        self._checkin_service: Optional[CheckinService] = None
        
        # Application services
        self._bot: Optional[FamilyEmotionsBot] = None
        self._scheduler: Optional[TaskScheduler] = None
        
        # Session for service initialization
        self._session: Optional[AsyncSession] = None
    
    async def initialize(self):
        """Initialize all services and dependencies."""
        logger.info("Initializing dependency container...")
        
        try:
            # Initialize database
            await self._init_database()
            
            # Initialize cache
            await self._init_cache()
            
            # Initialize external services
            await self._init_external_services()
            
            # Initialize core services
            await self._init_core_services()
            
            # Initialize application services
            await self._init_application_services()
            
            logger.info("Dependency container initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize container: {e}")
            await self.cleanup()
            raise
    
    async def _init_database(self):
        """Initialize database manager."""
        self._db_manager = DatabaseManager()
        await self._db_manager.initialize()
        
        # Get session for service initialization
        self._session = await self._db_manager.get_raw_session()
    
    async def _init_cache(self):
        """Initialize cache services."""
        self._redis_service = RedisService()
        await self._redis_service.connect()
        
        self._cache_service = CacheService(self._redis_service)
        await self._cache_service.connect()
    
    async def _init_external_services(self):
        """Initialize external API services."""
        self._claude_service = ClaudeService()
    
    async def _init_core_services(self):
        """Initialize core domain services."""
        if not self._session:
            raise RuntimeError("Database session not available")
        
        # Analytics service (needed by others)
        self._analytics_service = AnalyticsService(self._session)
        
        # User service
        self._user_service = UserService(self._session)
        
        # Family service
        self._family_service = FamilyService(self._session)
        
        # Emotion service
        self._emotion_service = EmotionService(
            session=self._session,
            claude_service=self._claude_service,
            user_service=self._user_service,
            analytics_service=self._analytics_service
        )
    
    async def _init_application_services(self):
        """Initialize application-level services."""
        if not all([
            self._session, 
            self._user_service, 
            self._analytics_service, 
            self._claude_service
        ]):
            raise RuntimeError("Core services not initialized")
        
        # Check-in service
        self._checkin_service = CheckinService(
            session=self._session,
            user_service=self._user_service,
            analytics_service=self._analytics_service,
            claude_service=self._claude_service
        )
        
        # Telegram bot
        self._bot = FamilyEmotionsBot(
            user_service=self._user_service,
            family_service=self._family_service,
            emotion_service=self._emotion_service,
            analytics_service=self._analytics_service
        )
        
        # Setup bot handlers
        setup_handlers(self._bot)
        
        # Task scheduler
        self._scheduler = TaskScheduler(
            checkin_service=self._checkin_service,
            bot=self._bot
        )
    
    async def cleanup(self):
        """Clean up all resources."""
        logger.info("Cleaning up container...")
        
        try:
            # Stop scheduler
            if self._scheduler:
                await self._scheduler.stop()
            
            # Stop bot
            if self._bot:
                self._bot.stop()
            
            # Close session
            if self._session:
                await self._session.close()
            
            # Close cache
            if self._cache_service:
                await self._cache_service.disconnect()
            
            if self._redis_service:
                await self._redis_service.disconnect()
            
            # Close database
            if self._db_manager:
                await self._db_manager.close()
            
            logger.info("Container cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    # Service getters
    
    @property
    def db_manager(self) -> DatabaseManager:
        """Get database manager."""
        if not self._db_manager:
            raise RuntimeError("Database manager not initialized")
        return self._db_manager
    
    @property
    def cache_service(self) -> CacheService:
        """Get cache service."""
        if not self._cache_service:
            raise RuntimeError("Cache service not initialized")
        return self._cache_service
    
    @property
    def user_service(self) -> UserService:
        """Get user service."""
        if not self._user_service:
            raise RuntimeError("User service not initialized")
        return self._user_service
    
    @property
    def family_service(self) -> FamilyService:
        """Get family service."""
        if not self._family_service:
            raise RuntimeError("Family service not initialized")
        return self._family_service
    
    @property
    def analytics_service(self) -> AnalyticsService:
        """Get analytics service."""
        if not self._analytics_service:
            raise RuntimeError("Analytics service not initialized")
        return self._analytics_service
    
    @property
    def emotion_service(self) -> EmotionService:
        """Get emotion service."""
        if not self._emotion_service:
            raise RuntimeError("Emotion service not initialized")
        return self._emotion_service
    
    @property
    def checkin_service(self) -> CheckinService:
        """Get check-in service."""
        if not self._checkin_service:
            raise RuntimeError("Check-in service not initialized")
        return self._checkin_service
    
    @property
    def bot(self) -> FamilyEmotionsBot:
        """Get Telegram bot."""
        if not self._bot:
            raise RuntimeError("Bot not initialized")
        return self._bot
    
    @property
    def scheduler(self) -> TaskScheduler:
        """Get task scheduler."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        return self._scheduler
    
    @property
    def is_initialized(self) -> bool:
        """Check if container is fully initialized."""
        return all([
            self._db_manager,
            self._cache_service,
            self._user_service,
            self._family_service,
            self._analytics_service,
            self._emotion_service,
            self._checkin_service,
            self._bot,
            self._scheduler
        ])


# Global container instance
container = Container()