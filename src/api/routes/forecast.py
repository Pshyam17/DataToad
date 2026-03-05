from fastapi import APIRouter, Depends
from pydantic import BaseModel
import pandas as pd
from src.api.dependencies import get_databricks, get_claude, get_cache
from src.forecast.pattern_based import PatternForecaster
from src.detection.classifier import PatternType

router = APIRouter()

class ForecastRequest(BaseModel):
    product_id: str
    horizon: int = 6

# Map your pattern names to PatternType enum
PATTERN_MAPPING = {
    "slow_trend": PatternType.SLOW_TREND,
    "high_volatility": PatternType.HIGH_VOLATILITY,
    "sudden_spike": PatternType.SUDDEN_SPIKE,
    "sudden_dip": PatternType.SUDDEN_DIP,
    "fixed_seasonality": PatternType.FIXED_SEASONALITY,
    "varying_seasonality": PatternType.VARYING_SEASONALITY,
    "stable_flat": PatternType.STABLE_FLAT,
}

@router.post("/generate")
async def generate_forecast(request: ForecastRequest, db=Depends(get_databricks), claude=Depends(get_claude), cache=Depends(get_cache)):
    cache_key = f"forecast:{request.product_id}:{request.horizon}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    pattern_df = db.get_patterns(filters={"product_id": request.product_id})
    if pattern_df.empty:
        return {"error": f"No pattern found for product {request.product_id}"}
    
    pattern_info = pattern_df.iloc[0].to_dict()
    sales_df = db.get_raw_sales(product_id=request.product_id)
    if sales_df.empty:
        return {"error": "No sales data found"}
    
    sales_df = sales_df.sort_values("sale_date")
    signal = sales_df["sales_volume"].values
    last_date = pd.to_datetime(sales_df["sale_date"].iloc[-1])
    
    detected = pattern_info.get("detected_pattern", "complex")
    pattern_type = PATTERN_MAPPING.get(detected, PatternType.COMPLEX)
    
    forecaster = PatternForecaster()
    forecast = forecaster.forecast(request.product_id, signal, pattern_type, last_date, request.horizon)
    
    interpretation = claude.interpret_forecast(
        {"dates": forecast.dates, "values": forecast.values, "lower_bound": forecast.lower_bound, "upper_bound": forecast.upper_bound, "method": forecast.method},
        pattern_info
    )
    
    result = {
        "product_id": request.product_id,
        "forecast": {"dates": forecast.dates, "values": forecast.values, "lower_bound": forecast.lower_bound, "upper_bound": forecast.upper_bound, "confidence_interval": forecast.confidence_interval, "method": forecast.method},
        "pattern_info": pattern_info, "interpretation": interpretation
    }
    cache.set(cache_key, result, ttl=3600)
    return result

@router.get("/history/{product_id}")
async def get_forecast_history(product_id: str, db=Depends(get_databricks)):
    df = db.get_forecasts(product_id)
    return {"forecasts": df.to_dict(orient="records") if not df.empty else [], "count": len(df)}