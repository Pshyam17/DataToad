from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Environment
    env: str = "development"
    log_level: str = "INFO"
    
    # Databricks Configuration
    databricks_host: str
    databricks_token: str
    databricks_warehouse_id: str
    databricks_catalog: str = "prism_ai"
    databricks_schema: str = "sales"
    transform_job_id: str
    
    # LLM Provider Configuration
    llm_provider: str = "nvidia"  # Options: "nvidia" or "ollama"
    
    # Nvidia NIM API Configuration
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_chat_model: str = "meta/llama-3.1-70b-instruct"
    nvidia_embedding_model: str = "nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1"
    
    # Ollama Configuration (Local LLM)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    
    # Anthropic API
    anthropic_api_key: str
    
    # Redis Cache
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600
    
    # Signal Processing Parameters
    stft_nperseg: int = 12
    stft_noverlap: int = 9
    wavelet_max_scale: int = 24
    hht_max_imfs: int = 5
    min_pattern_months: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()