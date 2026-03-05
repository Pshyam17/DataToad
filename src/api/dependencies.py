from functools import lru_cache
from src.config import get_settings
from src.api.services.databricks import DatabricksService
from src.api.services.claude import ClaudeService
from src.api.services.cache import CacheService

@lru_cache
def get_databricks() -> DatabricksService:
    return DatabricksService(get_settings())

@lru_cache
def get_claude() -> ClaudeService:
    return ClaudeService(get_settings())

@lru_cache
def get_cache() -> CacheService:
    return CacheService(get_settings())