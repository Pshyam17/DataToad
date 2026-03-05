import json
import redis
from typing import Any
import logging
from src.config import Settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, settings: Settings):
        self.ttl = settings.cache_ttl
        self.enabled = False
        self.client = None
        
        # Try to connect to Redis, but don't crash if unavailable
        try:
            self.client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
            self.client.ping()
            self.enabled = True
            logger.info("✅ Redis cache connected")
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable, running without cache: {e}")
            self.client = None
            self.enabled = False
    
    def get(self, key: str) -> Any | None:
        """Get value from cache, returns None if cache disabled or key not found"""
        if not self.enabled or not self.client:
            return None
        
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache, silently fails if cache disabled"""
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.setex(key, ttl or self.ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    def delete(self, key: str) -> None:
        """Delete value from cache"""
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled or not self.client:
            return False
        
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.warning(f"Cache exists error: {e}")
            return False
    
    def pattern_key(self, filters: dict) -> str:
        """Generate cache key from filters"""
        sorted_items = sorted(filters.items()) if filters else []
        return f"patterns:{hash(tuple(sorted_items))}"
    
    def job_key(self, run_id: str) -> str:
        """Generate cache key for job status"""
        return f"job:{run_id}"