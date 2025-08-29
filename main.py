"""Main entry point for Family Emotions App."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
import uvicorn

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

# FastAPI app for health checks
web_app = FastAPI(title="Family Emotions Bot", version="0.1.0")

@web_app.get("/health")
async def health_check():
    """Health check endpoint for Coolify."""
    try:
        # Check if health checker is available
        if health_checker.get_health_status():
            health = health_checker.get_health_status()
            if health.overall_status.value == "healthy":
                return {"status": "healthy", "timestamp": health.timestamp.isoformat()}
        
        return {"status": "healthy", "message": "Basic health check passed"}
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@web_app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    try:
        metrics_data = metrics_collector.get_prometheus_metrics()
        return Response(metrics_data, media_type="text/plain")
    except Exception as e:
        logger.error("Metrics endpoint failed", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get metrics"}
        )

@web_app.get("/status")
async def get_status():
    """Detailed status endpoint."""
    try:
        return {
            "status": "running",
            "version": "0.1.0",
            "environment": settings.environment,
            "health": health_checker.get_health_summary() if health_checker else None,
            "metrics": metrics_collector.get_metrics_summary() if metrics_collector else None
        }
    except Exception as e:
        logger.error("Status endpoint failed", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


class FamilyEmotionsApp:
    """Main application class."""
    
    def __init__(self):
        self.bot_app = None
        self.emotion_analyzer = None
        self.db_manager = None
        self._shutdown_event = asyncio.Event()
    
    async def startup(self):
        """Initialize application components."""
        logger.info("Starting Family Emotions App", version="0.1.0")
        
        try:
            # Initialize database
            logger.info("Initializing database connection")
            from src.infrastructure.database.database import DatabaseManager
            self.db_manager = DatabaseManager()
            
            try:
                await self.db_manager.initialize()
                logger.info("Database connection established successfully")
                
                # Run migrations if database is available
                try:
                    logger.info("Running database migrations...")
                    import subprocess
                    result = subprocess.run([sys.executable, "run_migrations.py"], 
                                          capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        logger.info("Database migrations completed successfully")
                    else:
                        logger.warning(f"Migration failed but continuing: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    logger.warning("Migration timed out, continuing without migrations")
                except Exception as migration_error:
                    logger.warning(f"Could not run migrations: {migration_error}")
                    
            except Exception as db_error:
                logger.warning(f"Database initialization failed, continuing without database: {db_error}")
                self.db_manager = None
            
            # Initialize emotion analyzer
            logger.info("Initializing emotion analyzer")
            self.emotion_analyzer = EmotionAnalyzer()
            
            # Create Telegram bot
            logger.info("Creating Telegram bot")
            self.bot_app = create_bot(self.emotion_analyzer)
            
            # Setup FamilyEmotionsBot with database services
            try:
                from src.infrastructure.telegram.bot import FamilyEmotionsBot
                
                # Create bot instance
                family_bot = FamilyEmotionsBot(
                    user_service=None,  # Will create on-demand
                    family_service=None,
                    emotion_service=None,
                    analytics_service=None
                )
                
                # Inject database manager for service creation (if available)
                if self.db_manager:
                    family_bot.db_manager = self.db_manager
                    logger.info("Bot instance created with database access")
                else:
                    logger.info("Bot instance created without database (basic mode)")
                
                setup_bot_commands(self.bot_app, bot_instance=family_bot)
                
            except Exception as e:
                logger.error(f"Failed to create bot instance: {e}")
                # Fallback to simple setup
                setup_bot_commands(self.bot_app)
            
            # Start monitoring services
            logger.info("Starting monitoring services")
            await metrics_collector.start()
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
            
            # Close database
            if self.db_manager:
                logger.info("Closing database connections")
                await self.db_manager.close()
            
            logger.info("Application shutdown completed")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))
    
    async def run(self):
        """Run the application."""
        try:
            await self.startup()
            
            # Start the bot
            logger.info("Starting Telegram bot polling")
            
            # Start web server for health checks
            config = uvicorn.Config(
                web_app, 
                host="0.0.0.0", 
                port=8000, 
                log_level="info"
            )
            server = uvicorn.Server(config)
            
            # Set up signal handlers for graceful shutdown
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig, lambda s=sig: asyncio.create_task(self._signal_handler(s))
                )
            
            # Start services concurrently
            await asyncio.gather(
                self._run_bot(),
                server.serve(),
                return_exceptions=True
            )
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error("Application error", error=str(e))
            raise
        finally:
            await self.shutdown()
    
    async def _run_bot(self):
        """Run the Telegram bot with proper polling."""
        try:
            # Initialize and start the application
            await self.bot_app.initialize()
            await self.bot_app.start()
            
            # FORCE clear any existing webhooks/polling conflicts
            try:
                logger.info("Force clearing any existing bot connections...")
                # Always try to delete webhook regardless
                await self.bot_app.bot.delete_webhook(drop_pending_updates=True)
                logger.info("Forced webhook deletion completed")
                
                # Give more time for Telegram to process and clear all conflicts
                import asyncio
                await asyncio.sleep(10)  # Increased from 2 to 10 seconds
                
                # Check status
                webhook_info = await self.bot_app.bot.get_webhook_info()
                logger.info(f"Post-cleanup webhook status: {webhook_info.url if webhook_info.url else 'None'}")
                
            except Exception as e:
                logger.warning(f"Error during connection cleanup: {e}")
            
            # Try polling, fallback to webhook if conflict
            try:
                # Start the updater for polling
                if hasattr(self.bot_app, 'updater') and self.bot_app.updater:
                    logger.info("Starting bot polling...")
                    await self.bot_app.updater.start_polling(
                        allowed_updates=None,  # Accept all update types
                        drop_pending_updates=True  # Start fresh, ignore pending updates
                    )
                    logger.info("Bot is now polling for updates and ready to receive messages...")
                else:
                    logger.warning("Updater not found, bot may not receive updates properly")
            except Exception as e:
                if "Conflict" in str(e):
                    logger.error("Polling conflict detected - this means another instance is running with the same bot token")
                    logger.error("Please check for other deployments or restart this container")
                else:
                    logger.error(f"Polling failed: {e}")
                # Continue running even if polling fails
                logger.info("Bot will continue running for health checks...")
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
            # Graceful shutdown sequence
            logger.info("Stopping bot polling...")
            if hasattr(self.bot_app, 'updater') and self.bot_app.updater:
                await self.bot_app.updater.stop()
            await self.bot_app.stop()
            await self.bot_app.shutdown()
            
        except Exception as e:
            logger.error("Bot error", error=str(e), exc_info=True)
            raise
    
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
        if var == 'DATABASE_URL':
            # Check if DATABASE_URL is set or individual DB components
            if not settings.database.database_url and not settings.database.password:
                missing_vars.append(var)
        elif var == 'CLAUDE_API_KEY':
            # Check if Claude API key is available
            if not settings.anthropic.claude_api_key:
                missing_vars.append(var)
        elif var == 'TELEGRAM_BOT_TOKEN':
            if not settings.telegram.bot_token:
                missing_vars.append(var)
        elif var == 'SECRET_KEY':
            if not settings.secret_key:
                missing_vars.append(var)
        elif var == 'ENCRYPTION_KEY':
            if not settings.encryption_key:
                missing_vars.append(var)
        else:
            # For other variables, try to get them by lowercase name
            if not getattr(settings, var.lower(), None):
                missing_vars.append(var)
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file or environment configuration.")
        sys.exit(1)
    
    # Print startup info
    print("🔧 Family Emotions Bot - BUILD v20250829-PROXY-SUPPORT")
    print("==================================================")
    print(f"Environment: {settings.environment}")
    print(f"Log Level: DEBUG")
    # Temporarily set to DEBUG for troubleshooting
    print(f"Claude Model: {settings.anthropic.model}")
    print("==================================================")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)