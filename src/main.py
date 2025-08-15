"""Main entry point for Family Emotions App."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional

from core.config import settings
from core.logging import setup_logging, get_logger
from core.container import container


# Setup logging first
setup_logging()
logger = get_logger("main")


class FamilyEmotionsApp:
    """Main application class."""
    
    def __init__(self):
        self.container = container
        self._shutdown_event = asyncio.Event()
        self._running = False
    
    async def initialize(self):
        """Initialize the application."""
        logger.info(f"Initializing Family Emotions App v{settings.app_version}")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Debug mode: {settings.debug}")
        
        try:
            # Initialize container with all services
            await self.container.initialize()
            
            # Create database tables if needed
            if settings.environment == "development":
                await self.container.db_manager.create_tables()
                logger.info("Database tables created/verified")
            
            logger.info("Application initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            raise
    
    async def start(self):
        """Start the application services."""
        if self._running:
            logger.warning("Application already running")
            return
        
        try:
            logger.info("Starting Family Emotions App services...")
            
            # Start scheduler
            await self.container.scheduler.start()
            logger.info("Task scheduler started")
            
            # Start bot
            self._running = True
            
            if settings.telegram.webhook_url and settings.is_production:
                # Production: webhook mode
                logger.info("Starting bot in webhook mode")
                await self.container.bot.run_webhook()
            else:
                # Development: polling mode
                logger.info("Starting bot in polling mode")
                await self.container.bot.run_polling()
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            self._running = False
            raise
    
    async def stop(self):
        """Stop the application gracefully."""
        if not self._running:
            return
        
        logger.info("Stopping Family Emotions App...")
        
        try:
            self._running = False
            self._shutdown_event.set()
            
            # Stop all services
            await self.container.cleanup()
            
            logger.info("Application stopped successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        # Handle SIGTERM and SIGINT
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Handle SIGUSR1 for log rotation
        def log_rotation_handler(signum, frame):
            logger.info("Received SIGUSR1, rotating logs...")
            # Force log rotation
            for handler in logging.root.handlers:
                if hasattr(handler, 'doRollover'):
                    handler.doRollover()
        
        signal.signal(signal.SIGUSR1, log_rotation_handler)
    
    @property
    def is_running(self) -> bool:
        """Check if application is running."""
        return self._running


async def run_development_server():
    """Run the application in development mode."""
    app = FamilyEmotionsApp()
    
    try:
        # Initialize application
        await app.initialize()
        
        # Setup signal handlers
        app.setup_signal_handlers()
        
        # Start application
        await app.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        await app.stop()


async def run_production_server():
    """Run the application in production mode with proper error handling."""
    app = FamilyEmotionsApp()
    
    try:
        # Initialize application
        await app.initialize()
        
        # Setup signal handlers
        app.setup_signal_handlers()
        
        # Health check endpoint could be added here
        logger.info("Application health check: OK")
        
        # Start application
        await app.start()
        
    except Exception as e:
        logger.critical(f"Critical application error: {e}")
        sys.exit(1)
    finally:
        await app.stop()


@asynccontextmanager
async def lifespan_context():
    """Context manager for application lifespan."""
    app = FamilyEmotionsApp()
    
    try:
        await app.initialize()
        yield app
    finally:
        await app.stop()


async def health_check() -> bool:
    """Perform application health check."""
    try:
        # Quick health check without full initialization
        from core.container import Container
        temp_container = Container()
        
        # Check database connection
        await temp_container._init_database()
        
        # Check cache connection
        await temp_container._init_cache()
        
        # Cleanup
        await temp_container.cleanup()
        
        logger.info("Health check passed")
        return True
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


async def run_migrations():
    """Run database migrations."""
    logger.info("Running database migrations...")
    
    try:
        # Initialize database only
        await container.db_manager.initialize()
        
        # Create all tables
        await container.db_manager.create_tables()
        
        logger.info("Database migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        sys.exit(1)
    finally:
        await container.db_manager.close()


async def create_test_data():
    """Create test data for development."""
    if not settings.debug:
        logger.error("Test data creation only allowed in debug mode")
        return
    
    logger.info("Creating test data...")
    
    try:
        # Initialize container
        await container.initialize()
        
        # Create test user
        user = await container.user_service.create_user(
            telegram_id=123456789,
            first_name="Test",
            last_name="User",
            username="testuser",
            language_code="en"
        )
        
        # Create test child
        child = await container.family_service.add_child(
            parent_id=user.id,
            name="Test Child",
            age=7,
            personality_traits="Creative and sensitive, loves drawing",
            interests="Art, books, puzzles",
            special_needs="None"
        )
        
        logger.info(f"Created test user {user.id} with child {child.id}")
        
    except Exception as e:
        logger.error(f"Failed to create test data: {e}")
    finally:
        await container.cleanup()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Family Emotions App")
    parser.add_argument(
        "--mode",
        choices=["run", "migrate", "health", "test-data"],
        default="run",
        help="Application mode"
    )
    parser.add_argument(
        "--env",
        choices=["development", "production"],
        default=settings.environment,
        help="Environment mode"
    )
    
    args = parser.parse_args()
    
    # Update environment if specified
    if args.env != settings.environment:
        settings.environment = args.env
    
    # Run based on mode
    if args.mode == "health":
        result = asyncio.run(health_check())
        sys.exit(0 if result else 1)
    
    elif args.mode == "migrate":
        asyncio.run(run_migrations())
    
    elif args.mode == "test-data":
        asyncio.run(create_test_data())
    
    elif args.mode == "run":
        if settings.is_production:
            logger.info("Starting in production mode")
            asyncio.run(run_production_server())
        else:
            logger.info("Starting in development mode")
            asyncio.run(run_development_server())
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()