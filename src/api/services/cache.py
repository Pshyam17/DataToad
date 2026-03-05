import json
import redis
from typing import Any
from src.config import Settings

class CacheService:
    def __init__(self, settings: Settings):
        self.client = redis.from_url(settings.redis_url)
        self.ttl = settings.cache_ttl
    
    def get(self, key: str) -> Any | None:
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        self.client.setex(key, ttl or self.ttl, json.dumps(value, default=str))
    
    def delete(self, key: str) -> None:
        self.client.delete(key)
    
    def exists(self, key: str) -> bool:
        return bool(self.client.exists(key))
    
    def pattern_key(self, filters: dict) -> str:
        sorted_items = sorted(filters.items()) if filters else []
        return f"patterns:{hash(tuple(sorted_items))}"
    
    def job_key(self, run_id: str) -> str:
        return f"job:{run_id}"
