from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.api.dependencies import get_databricks, get_claude, get_cache

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    filters: dict | None = None

def parse_intent(message: str) -> dict:
    """Extract filters from user message."""
    msg = message.lower()
    filters = {}
    
    # Pattern type detection
    if "seasonal" in msg:
        filters["pattern_type"] = "slow_trend"  # or detect seasonality
    elif "trend" in msg and "up" in msg or "increasing" in msg or "growing" in msg:
        filters["trend_direction"] = "increasing"
    elif "trend" in msg and "down" in msg or "decreasing" in msg or "declining" in msg:
        filters["trend_direction"] = "decreasing"
    elif "spike" in msg:
        filters["pattern_type"] = "sudden_spike"
    elif "dip" in msg or "drop" in msg:
        filters["pattern_type"] = "sudden_dip"
    elif "stable" in msg or "consistent" in msg:
        filters["pattern_type"] = "stable_flat"
    elif "volatile" in msg or "volatility" in msg:
        filters["pattern_type"] = "high_volatility"
    
    # Category detection
    categories = ["clothing", "jacket", "dress", "shirt", "pants", "coat"]
    for cat in categories:
        if cat in msg:
            filters["category"] = cat.capitalize()
            break
    
    # Confidence filter
    if "high confidence" in msg or "confident" in msg:
        filters["min_confidence"] = 0.7
    
    return filters

@router.post("/chat")
async def chat(request: ChatRequest, db=Depends(get_databricks), claude=Depends(get_claude), cache=Depends(get_cache)):
    # Parse user intent to get filters
    intent_filters = parse_intent(request.message)
    
    # Merge with any explicit filters from request
    filters = {**intent_filters, **(request.filters or {})}
    
    cache_key = cache.pattern_key(filters)
    cached = cache.get(cache_key)
    
    if cached:
        patterns = cached
    else:
        df = db.get_patterns(filters=filters if filters else None, limit=50)
        patterns = df.to_dict(orient="records")
        cache.set(cache_key, patterns)
    
    response = claude.interpret_patterns(patterns, request.message)
    return {"response": response, "patterns_count": len(patterns), "filters_applied": filters}

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, db=Depends(get_databricks), claude=Depends(get_claude), cache=Depends(get_cache)):
    intent_filters = parse_intent(request.message)
    filters = {**intent_filters, **(request.filters or {})}
    
    cache_key = cache.pattern_key(filters)
    cached = cache.get(cache_key)
    
    if cached:
        patterns = cached
    else:
        df = db.get_patterns(filters=filters if filters else None, limit=50)
        patterns = df.to_dict(orient="records")
        cache.set(cache_key, patterns)
    
    return StreamingResponse(claude.stream_response(patterns, request.message), media_type="text/event-stream")

@router.get("/patterns")
async def get_patterns(
    product_id: str | None = None, pattern_type: str | None = None,
    category: str | None = None, min_confidence: float | None = None,
    trend_direction: str | None = None,
    limit: int = Query(default=100, le=1000), db=Depends(get_databricks)
):
    filters = {k: v for k, v in {
        "product_id": product_id, 
        "pattern_type": pattern_type, 
        "category": category, 
        "min_confidence": min_confidence,
        "trend_direction": trend_direction
    }.items() if v is not None}
    
    df = db.get_patterns(filters=filters if filters else None, limit=limit)
    return {"patterns": df.to_dict(orient="records"), "count": len(df)}

@router.get("/patterns/{product_id}")
async def get_product_pattern(product_id: str, db=Depends(get_databricks)):
    df = db.get_patterns(filters={"product_id": product_id})
    if df.empty:
        return {"error": "Product not found"}
    return df.to_dict(orient="records")[0]