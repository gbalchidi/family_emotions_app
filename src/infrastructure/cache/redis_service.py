"""Redis caching service for performance optimization."""
from __future__ import annotations

import json
import logging
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, Union, Dict, List
from uuid import UUID

import redis.asyncio as redis
from redis.exceptions import RedisError

from ...core.config import settings
from ...core.exceptions import CacheError

logger = logging.getLogger(__name__)


class RedisService:
    """Low-level Redis service for cache operations."""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        """Connect to Redis server."""
        try:
            self._connection_pool = redis.ConnectionPool.from_url(
                url=settings.redis.url,
                max_connections=settings.redis.max_connections,
                socket_timeout=settings.redis.socket_timeout,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            self._redis = redis.Redis(
                connection_pool=self._connection_pool,
                decode_responses=True
            )
            
            # Test connection
            await self._redis.ping()
            logger.info("Connected to Redis successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise CacheError(f"Redis connection failed: {str(e)}")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        try:
            if self._redis:
                await self._redis.close()
            if self._connection_pool:
                await self._connection_pool.disconnect()
            
            logger.info("Disconnected from Redis")
            
        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {e}")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.get(key)
            
        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            raise CacheError(f"Cache GET failed: {str(e)}")
    
    async def set(
        self, 
        key: str, 
        value: str, 
        expire_seconds: Optional[int] = None
    ) -> bool:
        """Set value with optional expiration."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.set(key, value, ex=expire_seconds)
            
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            raise CacheError(f"Cache SET failed: {str(e)}")
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.delete(*keys)
            
        except RedisError as e:
            logger.error(f"Redis DELETE error for keys {keys}: {e}")
            raise CacheError(f"Cache DELETE failed: {str(e)}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return bool(await self._redis.exists(key))
            
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            raise CacheError(f"Cache EXISTS failed: {str(e)}")
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.expire(key, seconds)
            
        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            raise CacheError(f"Cache EXPIRE failed: {str(e)}")
    
    async def ttl(self, key: str) -> int:
        """Get time-to-live for key."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.ttl(key)
            
        except RedisError as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            raise CacheError(f"Cache TTL failed: {str(e)}")
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.incrby(key, amount)
            
        except RedisError as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            raise CacheError(f"Cache INCREMENT failed: {str(e)}")
    
    async def hash_set(self, name: str, mapping: Dict[str, str]) -> int:
        """Set hash fields."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.hset(name, mapping=mapping)
            
        except RedisError as e:
            logger.error(f"Redis HSET error for hash {name}: {e}")
            raise CacheError(f"Cache HASH_SET failed: {str(e)}")
    
    async def hash_get(self, name: str, key: str) -> Optional[str]:
        """Get hash field value."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.hget(name, key)
            
        except RedisError as e:
            logger.error(f"Redis HGET error for hash {name}, key {key}: {e}")
            raise CacheError(f"Cache HASH_GET failed: {str(e)}")
    
    async def hash_get_all(self, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.hgetall(name)
            
        except RedisError as e:
            logger.error(f"Redis HGETALL error for hash {name}: {e}")
            raise CacheError(f"Cache HASH_GET_ALL failed: {str(e)}")
    
    async def list_push(self, key: str, *values: str) -> int:
        """Push values to list (right side)."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.rpush(key, *values)
            
        except RedisError as e:
            logger.error(f"Redis RPUSH error for key {key}: {e}")
            raise CacheError(f"Cache LIST_PUSH failed: {str(e)}")
    
    async def list_pop(self, key: str) -> Optional[str]:
        """Pop value from list (left side)."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.lpop(key)
            
        except RedisError as e:
            logger.error(f"Redis LPOP error for key {key}: {e}")
            raise CacheError(f"Cache LIST_POP failed: {str(e)}")
    
    async def list_range(self, key: str, start: int = 0, end: int = -1) -> List[str]:
        """Get list range."""
        try:
            if not self._redis:
                raise CacheError("Redis not connected")
            
            return await self._redis.lrange(key, start, end)
            
        except RedisError as e:
            logger.error(f"Redis LRANGE error for key {key}: {e}")
            raise CacheError(f"Cache LIST_RANGE failed: {str(e)}")
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._redis is not None


class CacheService:
    """High-level caching service with serialization support."""
    
    def __init__(self, redis_service: RedisService):
        self._redis = redis_service
        
        # Cache key prefixes
        self.USER_PREFIX = "user:"
        self.CHILD_PREFIX = "child:"
        self.TRANSLATION_PREFIX = "translation:"
        self.CHECKIN_PREFIX = "checkin:"
        self.REPORT_PREFIX = "report:"
        self.SESSION_PREFIX = "session:"
        self.RATE_LIMIT_PREFIX = "rate_limit:"
        self.ANALYTICS_PREFIX = "analytics:"
        
        # Default TTL values (in seconds)
        self.DEFAULT_TTL = 3600  # 1 hour
        self.USER_TTL = 1800     # 30 minutes
        self.TRANSLATION_TTL = 7200  # 2 hours
        self.SESSION_TTL = 86400     # 24 hours
        self.RATE_LIMIT_TTL = 86400  # 24 hours
        self.ANALYTICS_TTL = 300     # 5 minutes
    
    async def connect(self):
        """Connect to cache backend."""
        await self._redis.connect()
    
    async def disconnect(self):
        """Disconnect from cache backend."""
        await self._redis.disconnect()
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage."""
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        elif value is None:
            return ""
        else:
            # Use JSON for complex types
            try:
                return json.dumps(value, default=str)
            except (TypeError, ValueError):
                # Fallback to pickle for non-JSON serializable objects
                return pickle.dumps(value).hex()
    
    def _deserialize_value(self, value: str, value_type: type = str) -> Any:
        """Deserialize value from storage."""
        if not value:
            return None
        
        if value_type == str:
            return value
        elif value_type in (int, float, bool):
            return value_type(value)
        else:
            # Try JSON first
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                # Try pickle
                try:
                    return pickle.loads(bytes.fromhex(value))
                except (ValueError, pickle.UnpicklingError):
                    return value  # Return as string if all else fails
    
    # User caching
    
    async def cache_user(self, user_id: UUID, user_data: Dict[str, Any]) -> bool:
        """Cache user data."""
        key = f"{self.USER_PREFIX}{user_id}"
        value = self._serialize_value(user_data)
        return await self._redis.set(key, value, self.USER_TTL)
    
    async def get_cached_user(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get cached user data."""
        key = f"{self.USER_PREFIX}{user_id}"
        value = await self._redis.get(key)
        if value:
            return self._deserialize_value(value, dict)
        return None
    
    async def invalidate_user_cache(self, user_id: UUID) -> bool:
        """Invalidate user cache."""
        key = f"{self.USER_PREFIX}{user_id}"
        return bool(await self._redis.delete(key))
    
    # Translation caching
    
    async def cache_translation(
        self, 
        translation_id: UUID, 
        translation_data: Dict[str, Any]
    ) -> bool:
        """Cache translation result."""
        key = f"{self.TRANSLATION_PREFIX}{translation_id}"
        value = self._serialize_value(translation_data)
        return await self._redis.set(key, value, self.TRANSLATION_TTL)
    
    async def get_cached_translation(self, translation_id: UUID) -> Optional[Dict[str, Any]]:
        """Get cached translation."""
        key = f"{self.TRANSLATION_PREFIX}{translation_id}"
        value = await self._redis.get(key)
        if value:
            return self._deserialize_value(value, dict)
        return None
    
    # Session management
    
    async def create_session(
        self, 
        user_id: int, 
        session_data: Dict[str, Any]
    ) -> str:
        """Create user session."""
        session_id = f"sess_{user_id}_{datetime.now().timestamp()}"
        key = f"{self.SESSION_PREFIX}{session_id}"
        
        # Add session metadata
        session_data.update({
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        })
        
        value = self._serialize_value(session_data)
        await self._redis.set(key, value, self.SESSION_TTL)
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        key = f"{self.SESSION_PREFIX}{session_id}"
        value = await self._redis.get(key)
        if value:
            session_data = self._deserialize_value(value, dict)
            
            # Update last activity
            session_data["last_activity"] = datetime.now().isoformat()
            updated_value = self._serialize_value(session_data)
            await self._redis.set(key, updated_value, self.SESSION_TTL)
            
            return session_data
        return None
    
    async def update_session(
        self, 
        session_id: str, 
        session_data: Dict[str, Any]
    ) -> bool:
        """Update session data."""
        key = f"{self.SESSION_PREFIX}{session_id}"
        
        # Preserve metadata
        existing_data = await self.get_session(session_id)
        if existing_data:
            session_data.update({
                "user_id": existing_data.get("user_id"),
                "created_at": existing_data.get("created_at"),
                "last_activity": datetime.now().isoformat()
            })
        
        value = self._serialize_value(session_data)
        return await self._redis.set(key, value, self.SESSION_TTL)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        key = f"{self.SESSION_PREFIX}{session_id}"
        return bool(await self._redis.delete(key))
    
    # Rate limiting
    
    async def check_rate_limit(
        self, 
        user_id: int, 
        action: str, 
        limit: int, 
        window_seconds: int = 86400
    ) -> tuple[bool, int, int]:
        """
        Check rate limit for user action.
        
        Returns:
            Tuple of (is_allowed, current_count, reset_time)
        """
        key = f"{self.RATE_LIMIT_PREFIX}{user_id}:{action}"
        
        try:
            current_count = await self._redis.get(key)
            
            if current_count is None:
                # First request
                await self._redis.set(key, "1", window_seconds)
                return True, 1, window_seconds
            
            current_count = int(current_count)
            
            if current_count >= limit:
                # Rate limit exceeded
                ttl = await self._redis.ttl(key)
                return False, current_count, ttl
            
            # Increment counter
            new_count = await self._redis.increment(key)
            ttl = await self._redis.ttl(key)
            
            return True, new_count, ttl
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Allow request on cache error
            return True, 0, 0
    
    # Analytics caching
    
    async def cache_analytics(
        self, 
        key_suffix: str, 
        data: Dict[str, Any]
    ) -> bool:
        """Cache analytics data."""
        key = f"{self.ANALYTICS_PREFIX}{key_suffix}"
        value = self._serialize_value(data)
        return await self._redis.set(key, value, self.ANALYTICS_TTL)
    
    async def get_cached_analytics(self, key_suffix: str) -> Optional[Dict[str, Any]]:
        """Get cached analytics data."""
        key = f"{self.ANALYTICS_PREFIX}{key_suffix}"
        value = await self._redis.get(key)
        if value:
            return self._deserialize_value(value, dict)
        return None
    
    # Utility methods
    
    async def cache_list(
        self, 
        key_suffix: str, 
        items: List[Any], 
        prefix: str = "", 
        ttl: int = None
    ) -> bool:
        """Cache a list of items."""
        key = f"{prefix}{key_suffix}"
        value = self._serialize_value(items)
        return await self._redis.set(key, value, ttl or self.DEFAULT_TTL)
    
    async def get_cached_list(
        self, 
        key_suffix: str, 
        prefix: str = ""
    ) -> Optional[List[Any]]:
        """Get cached list."""
        key = f"{prefix}{key_suffix}"
        value = await self._redis.get(key)
        if value:
            return self._deserialize_value(value, list)
        return None
    
    async def clear_cache_pattern(self, pattern: str) -> int:
        """Clear cache keys matching pattern (use with caution)."""
        # This is potentially dangerous and should be used carefully
        # In production, consider using a more specific approach
        try:
            if not pattern.endswith("*"):
                pattern += "*"
            
            # Note: KEYS command should be avoided in production
            # Consider using SCAN instead for large datasets
            keys = await self._redis._redis.keys(pattern)
            if keys:
                return await self._redis.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            info = await self._redis._redis.info()
            
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0) / 
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                ) * 100
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    @property
    def is_connected(self) -> bool:
        """Check if cache is connected."""
        return self._redis.is_connected