"""Health check and system monitoring."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import psutil
import json

import httpx
import asyncpg
import redis.asyncio as redis
from anthropic import AsyncAnthropic

from ...core.config import settings


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    
    name: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Overall system health status."""
    
    overall_status: HealthStatus
    checks: List[HealthCheck]
    timestamp: datetime = field(default_factory=datetime.now)
    version: str = "0.1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.overall_status.value,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "response_time_ms": check.response_time_ms,
                    "timestamp": check.timestamp.isoformat(),
                    "details": check.details
                }
                for check in self.checks
            ]
        }


class HealthChecker:
    """System health monitoring service."""
    
    def __init__(self):
        self.last_health_check: Optional[SystemHealth] = None
        self.health_check_interval = 30  # seconds
        self._background_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    def start_monitoring(self):
        """Start background health monitoring."""
        if self._background_task is None or self._background_task.done():
            self._shutdown = False
            self._background_task = asyncio.create_task(self._monitor_health())
            logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop background health monitoring."""
        self._shutdown = True
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            logger.info("Health monitoring stopped")
    
    async def _monitor_health(self):
        """Background task to monitor system health."""
        while not self._shutdown:
            try:
                health = await self.check_all()
                self.last_health_check = health
                
                # Log health status changes
                if health.overall_status != HealthStatus.HEALTHY:
                    logger.warning(
                        "System health degraded",
                        status=health.overall_status.value,
                        failed_checks=[
                            check.name for check in health.checks
                            if check.status != HealthStatus.HEALTHY
                        ]
                    )
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error("Health monitoring error", error=str(e))
                await asyncio.sleep(self.health_check_interval)
    
    async def check_all(self) -> SystemHealth:
        """Run all health checks."""
        checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_claude_api(),
            self.check_system_resources(),
            self.check_telegram_api(),
            return_exceptions=True
        )
        
        # Filter out exceptions and convert to HealthCheck objects
        valid_checks = []
        for check in checks:
            if isinstance(check, HealthCheck):
                valid_checks.append(check)
            elif isinstance(check, Exception):
                logger.error("Health check failed with exception", error=str(check))
                valid_checks.append(HealthCheck(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check exception: {str(check)}"
                ))
        
        # Determine overall status
        overall_status = self._determine_overall_status(valid_checks)
        
        return SystemHealth(
            overall_status=overall_status,
            checks=valid_checks
        )
    
    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """Determine overall system health from individual checks."""
        if not checks:
            return HealthStatus.UNKNOWN
        
        unhealthy_count = sum(1 for check in checks if check.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for check in checks if check.status == HealthStatus.DEGRADED)
        
        # If any critical service is unhealthy, system is unhealthy
        critical_services = {"database", "redis", "claude_api"}
        for check in checks:
            if check.name in critical_services and check.status == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY
        
        # If more than 50% of checks are unhealthy/degraded
        if (unhealthy_count + degraded_count) > len(checks) * 0.5:
            return HealthStatus.UNHEALTHY
        
        # If any check is degraded
        if degraded_count > 0 or unhealthy_count > 0:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    async def check_database(self) -> HealthCheck:
        """Check PostgreSQL database connectivity."""
        start_time = datetime.now()
        
        try:
            # Test database connection
            conn = await asyncpg.connect(settings.database_url)
            
            # Simple query to test functionality
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if result == 1:
                return HealthCheck(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful",
                    response_time_ms=response_time
                )
            else:
                return HealthCheck(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Database query returned unexpected result",
                    response_time_ms=response_time
                )
        
        except Exception as e:
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def check_redis(self) -> HealthCheck:
        """Check Redis connectivity."""
        start_time = datetime.now()
        
        try:
            # Test Redis connection
            r = redis.from_url(settings.redis_url)
            await r.ping()
            await r.close()
            
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return HealthCheck(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection successful",
                response_time_ms=response_time
            )
        
        except Exception as e:
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return HealthCheck(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def check_claude_api(self) -> HealthCheck:
        """Check Claude API connectivity."""
        start_time = datetime.now()
        
        try:
            client = AsyncAnthropic(api_key=settings.claude_api_key)
            
            # Simple API test
            response = await client.messages.create(
                model="claude-3-haiku-20240307",  # Use cheaper model for health checks
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response and response.content:
                status = HealthStatus.HEALTHY if response_time < 5000 else HealthStatus.DEGRADED
                return HealthCheck(
                    name="claude_api",
                    status=status,
                    message="Claude API connection successful",
                    response_time_ms=response_time,
                    details={"model_used": "claude-3-haiku-20240307"}
                )
            else:
                return HealthCheck(
                    name="claude_api",
                    status=HealthStatus.UNHEALTHY,
                    message="Claude API returned empty response",
                    response_time_ms=response_time
                )
        
        except Exception as e:
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return HealthCheck(
                name="claude_api",
                status=HealthStatus.UNHEALTHY,
                message=f"Claude API connection failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def check_telegram_api(self) -> HealthCheck:
        """Check Telegram Bot API connectivity."""
        start_time = datetime.now()
        
        try:
            async with httpx.AsyncClient() as client:
                # Test getMe endpoint
                response = await client.get(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe",
                    timeout=10.0
                )
                
                response_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        return HealthCheck(
                            name="telegram_api",
                            status=HealthStatus.HEALTHY,
                            message="Telegram API connection successful",
                            response_time_ms=response_time,
                            details={"bot_username": data.get("result", {}).get("username")}
                        )
                
                return HealthCheck(
                    name="telegram_api",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Telegram API returned error: {response.status_code}",
                    response_time_ms=response_time
                )
        
        except Exception as e:
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return HealthCheck(
                name="telegram_api",
                status=HealthStatus.UNHEALTHY,
                message=f"Telegram API connection failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def check_system_resources(self) -> HealthCheck:
        """Check system resource usage."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
            
            # Determine status based on resource usage
            status = HealthStatus.HEALTHY
            issues = []
            
            if cpu_percent > 90:
                status = HealthStatus.DEGRADED
                issues.append(f"High CPU usage: {cpu_percent}%")
            elif cpu_percent > 95:
                status = HealthStatus.UNHEALTHY
                issues.append(f"Critical CPU usage: {cpu_percent}%")
            
            if memory.percent > 85:
                status = HealthStatus.DEGRADED
                issues.append(f"High memory usage: {memory.percent}%")
            elif memory.percent > 95:
                status = HealthStatus.UNHEALTHY
                issues.append(f"Critical memory usage: {memory.percent}%")
            
            if disk.percent > 85:
                status = HealthStatus.DEGRADED
                issues.append(f"High disk usage: {disk.percent}%")
            elif disk.percent > 95:
                status = HealthStatus.UNHEALTHY
                issues.append(f"Critical disk usage: {disk.percent}%")
            
            message = "System resources normal"
            if issues:
                message = f"Resource issues: {', '.join(issues)}"
            
            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                details=details
            )
        
        except Exception as e:
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check system resources: {str(e)}"
            )
    
    def get_health_status(self) -> Optional[SystemHealth]:
        """Get the last health check result."""
        return self.last_health_check
    
    def get_health_json(self) -> str:
        """Get health status as JSON string."""
        if self.last_health_check:
            return json.dumps(self.last_health_check.to_dict(), indent=2)
        else:
            return json.dumps({
                "status": "unknown",
                "message": "No health checks performed yet",
                "timestamp": datetime.now().isoformat()
            }, indent=2)


# Global health checker instance
health_checker = HealthChecker()


# Convenience functions
async def is_healthy() -> bool:
    """Check if system is currently healthy."""
    health = health_checker.get_health_status()
    if health:
        return health.overall_status == HealthStatus.HEALTHY
    
    # If no recent health check, run one
    health = await health_checker.check_all()
    return health.overall_status == HealthStatus.HEALTHY


async def get_health_summary() -> Dict[str, Any]:
    """Get a simple health summary."""
    health = health_checker.get_health_status()
    
    if not health:
        return {
            "status": "unknown",
            "message": "No health data available"
        }
    
    failed_checks = [
        check.name for check in health.checks
        if check.status != HealthStatus.HEALTHY
    ]
    
    return {
        "status": health.overall_status.value,
        "timestamp": health.timestamp.isoformat(),
        "total_checks": len(health.checks),
        "failed_checks": failed_checks,
        "healthy": health.overall_status == HealthStatus.HEALTHY
    }