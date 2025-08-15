"""Main entry point for Family Emotions App."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from src.infrastructure.telegram.bot import create_bot, setup_bot_commands
from src.application.emotion_analyzer import EmotionAnalyzer
from src.core.config import settings
from src.infrastructure.monitoring.logging import configure_logging, get_logger
from src.infrastructure.monitoring.metrics import metrics_collector
from src.infrastructure.monitoring.health import health_checker
from src.infrastructure.monitoring.analytics import analytics_service


# Configure logging first
configure_logging()
logger = get_logger(__name__)


class FamilyEmotionsApp:
    """Main application class."""
    
    def __init__(self):
        self.bot_app = None
        self.emotion_analyzer = None
        self._shutdown_event = asyncio.Event()
    
    async def startup(self):
        """Initialize application components."""
        logger.info("Starting Family Emotions App", version="0.1.0")
        
        try:
            # Initialize emotion analyzer
            logger.info("Initializing emotion analyzer")
            self.emotion_analyzer = EmotionAnalyzer()
            
            # Create Telegram bot
            logger.info("Creating Telegram bot")
            self.bot_app = create_bot(self.emotion_analyzer)
            setup_bot_commands(self.bot_app)
            
            # Start monitoring services
            logger.info("Starting monitoring services")
            health_checker.start_monitoring()
            analytics_service.start_analytics()
            
            logger.info("Application startup completed successfully")
            
        except Exception as e:
            logger.error("Failed to start application", error=str(e))
            raise
    
    async def shutdown(self):
        """Gracefully shutdown application components."""
        logger.info("Shutting down Family Emotions App")
        
        try:
            # Stop monitoring services
            logger.info("Stopping monitoring services")
            await health_checker.stop_monitoring()
            await analytics_service.stop_analytics()
            await metrics_collector.shutdown()
            
            # Stop bot
            if self.bot_app:
                logger.info("Stopping Telegram bot")
                await self.bot_app.stop()
                await self.bot_app.shutdown()
            
            logger.info("Application shutdown completed")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))
    
    async def run(self):
        """Run the application."""
        try:
            await self.startup()
            
            # Start the bot
            logger.info("Starting Telegram bot polling")
            await self.bot_app.initialize()
            
            # Set up signal handlers for graceful shutdown
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig, lambda s=sig: asyncio.create_task(self._signal_handler(s))
                )
            
            # Start polling
            await self.bot_app.start()
            await self.bot_app.updater.start_polling()
            
            logger.info("Bot is running. Press Ctrl+C to stop.")
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error("Application error", error=str(e))
            raise
        finally:
            await self.shutdown()
    
    async def _signal_handler(self, signal_num):
        """Handle shutdown signals."""
        logger.info("Received signal", signal=signal_num)
        self._shutdown_event.set()


@asynccontextmanager
async def lifespan_context():
    """Application lifespan context manager."""
    app = FamilyEmotionsApp()
    try:
        await app.startup()
        yield app
    finally:
        await app.shutdown()


async def main():
    """Main application entry point."""
    try:
        app = FamilyEmotionsApp()
        await app.run()
    except Exception as e:
        logger.error("Fatal application error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    # Check required environment variables
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'DATABASE_URL',
        'CLAUDE_API_KEY',
        'SECRET_KEY',
        'ENCRYPTION_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var.lower(), None):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file or environment configuration.")
        sys.exit(1)
    
    # Print startup info
    print("🤖 Family Emotions Bot")
    print("=======================")
    print(f"Environment: {settings.environment}")
    print(f"Log Level: {settings.log_level}")
    print(f"Claude Model: {settings.claude_model}")
    print("=======================")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)